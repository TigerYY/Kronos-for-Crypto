import os
import argparse
import time
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from peft import LoraConfig, get_peft_model
import sys

# Ensure Kronos modules can be imported
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from model.kronos import KronosTokenizer, Kronos
from crypto_finetune.dataset import CryptoDataset

class FundamentalProjector(nn.Module):
    """
    MLP that projects external features (FGI, Funding Rate) into the 
    Transformer's hidden dimension space (d_model).
    """
    def __init__(self, num_features=2, d_model=256, dropout=0.1):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(num_features, d_model),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model, d_model)
        )
        
    def forward(self, x):
        # x shape: [batch_size, seq_len, num_features]
        # output shape: [batch_size, seq_len, d_model]
        return self.net(x)

def train_lora_phase2(csv_file, epochs=5, batch_size=16, lr=2e-4, lookback=400, pred_len=12, output_dir="outputs/lora_adapters"):
    print(f"--- Starting Phase 2 Multi-Modal Fine-Tuning ---")
    
    # 1. Device Setup for Apple Silicon or NVIDIA
    if torch.backends.mps.is_available():
        device = torch.device("mps")
        print("Hardware Acceleration: Apple Silicon MPS detected.")
    elif torch.cuda.is_available():
        device = torch.device("cuda")
        print("Hardware Acceleration: CUDA detected.")
    else:
        device = torch.device("cpu")
        print("Hardware Acceleration: Warning! CPU fallback.")

    # 2. Dataset and Dataloader
    dataset = CryptoDataset(csv_file, lookback=lookback, pred_len=pred_len)
    
    # Safety Check: Did the dataset actually detect external features?
    if not dataset.ext_feature_list:
        raise ValueError("No external features (FGI, fundingRate) found in CSV! Please run `fetch_train_data_phase2.py` first.")
        
    num_ext_features = len(dataset.ext_feature_list)
    print(f"Multi-Modal Injection Active: {num_ext_features} features {dataset.ext_feature_list}")
    
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True, drop_last=True)
    
    if len(dataloader) == 0:
        raise ValueError("Dataset is too small for the given batch size and window length.")
    print(f"Total Steps per Epoch: {len(dataloader)}")

    # 3. Load Base Model and Tokenizer
    print("Loading Base Framework (Kronos-Tokenizer & Kronos-small)...")
    tokenizer = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base")
    tokenizer.eval().to(device)
    
    model = Kronos.from_pretrained("NeoQuasar/Kronos-small")
    d_model = model.d_model if hasattr(model, 'd_model') else 512
    
    # 4. Inject LoRA Adapters into Transformer Attention layers
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "out_proj"],
        lora_dropout=0.05,
        bias="none"
    )
    
    print("Injecting LoRA Hooks into Main Backbone...")
    model = get_peft_model(model, lora_config)
    
    # 5. Initialize the Multi-Modal Projector
    ext_projector = FundamentalProjector(num_features=num_ext_features, d_model=d_model)
    
    # Move models to device
    model.to(device)
    ext_projector.to(device)
    
    model.print_trainable_parameters()
    print("External Projector Trainable Parameters: ", sum(p.numel() for p in ext_projector.parameters() if p.requires_grad))
    
    # 6. Optimizer & Scheduler (Joint Optimization)
    optimizer = torch.optim.AdamW(
        list(model.parameters()) + list(ext_projector.parameters()), 
        lr=lr, 
        weight_decay=0.05
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs * len(dataloader))
    
    # 7. Training Loop
    os.makedirs(output_dir, exist_ok=True)
    best_loss = float('inf')
    
    for epoch in range(epochs):
        model.train()
        ext_projector.train()
        total_loss = 0.0
        start_time = time.time()
        
        for step, batch in enumerate(dataloader):
            # Parse Phase 2 Batch
            x = batch[0].to(device)
            x_stamp = batch[1].to(device)
            x_ext = batch[2].to(device)
            
            # Tokenize on-the-fly (Tokenizer remains frozen)
            with torch.no_grad():
                token_seq_0, token_seq_1 = tokenizer.encode(x, half=True)
                
            # Offset targets for Autoregressive LM prediction
            token_in = [token_seq_0[:, :-1], token_seq_1[:, :-1]]
            token_out = [token_seq_0[:, 1:], token_seq_1[:, 1:]]
            stamp_in = x_stamp[:, :-1, :]
            ext_in = x_ext[:, :-1, :]
            
            # Project multi-modal features to d_model space
            ext_embeds = ext_projector(ext_in)
            
            # Forward pass through LoRA model WITH Phase 2 Injection
            s1_logits, s2_logits = model(
                s1_ids=token_in[0], 
                s2_ids=token_in[1], 
                stamp=stamp_in,
                ext_embeds=ext_embeds
            )
            
            # Kronos specific dual-head CE loss 
            base_model = model.base_model.model if hasattr(model, "base_model") else model
            loss, s1_loss, s2_loss = base_model.head.compute_loss(s1_logits, s2_logits, token_out[0], token_out[1])
            
            # Backward
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(list(model.parameters()) + list(ext_projector.parameters()), 1.0)
            optimizer.step()
            scheduler.step()
            
            total_loss += loss.item()
            
            if (step + 1) % 10 == 0:
                print(f"Epoch [{epoch+1}/{epochs}] Step [{step+1}/{len(dataloader)}] - Loss: {loss.item():.4f} (S1: {s1_loss.item():.4f}, S2: {s2_loss.item():.4f}) | LR: {scheduler.get_last_lr()[0]:.2e}")
                
        avg_loss = total_loss / len(dataloader)
        epoch_time = time.time() - start_time
        print(f"=== Epoch {epoch+1} Complete | Avg Loss: {avg_loss:.4f} | Time: {epoch_time:.2f}s ===")
        
        # Checkpoint Saver
        if avg_loss < best_loss:
            best_loss = avg_loss
            # Derive specific save path based on data name
            market_name = os.path.basename(csv_file).split('_')[0] + "_" + os.path.basename(csv_file).split('_')[1] + "_phase2"
            save_path = os.path.join(output_dir, f"lora_{market_name}")
            
            # Save Base LoRA Model Weight
            model.save_pretrained(save_path)
            
            # Save the new Multi-Modal Projector Weight separately
            torch.save(ext_projector.state_dict(), os.path.join(save_path, "ext_projector.pth"))
            
            print(f"--> [Success] Saved new Best Multi-Modal LoRA adapter & Projector to {save_path} (Loss: {best_loss:.4f})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Modal LoRA Fine-Tuning for Kronos Phase 2")
    parser.add_argument("--csv_file", type=str, required=True, help="Path to target multi-modal OHLCV CSV file")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch", type=int, default=16, help="Optimal for Apple M4 Pro 48G is 16~32")
    parser.add_argument("--lr", type=float, default=2e-4) 
    
    args = parser.parse_args()
    
    train_lora_phase2(
        csv_file=args.csv_file,
        epochs=args.epochs,
        batch_size=args.batch,
        lr=args.lr
    )
