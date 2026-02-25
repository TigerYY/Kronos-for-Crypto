import os
import argparse
import time
import torch
from torch.utils.data import DataLoader
from peft import LoraConfig, get_peft_model
import sys

# Ensure Kronos modules can be imported
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from model.kronos import KronosTokenizer, Kronos
from crypto_finetune.dataset import CryptoDataset

def train_lora(csv_file, epochs=5, batch_size=16, lr=2e-4, lookback=400, pred_len=12, output_dir="outputs/lora_adapters"):
    print(f"--- Starting Crypto Domain Fine-Tuning (LoRA) ---")
    
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
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True, drop_last=True)
    
    if len(dataloader) == 0:
        raise ValueError("Dataset is too small for the given batch size and window length.")
    print(f"Total Steps per Epoch: {len(dataloader)}")

    # 3. Load Base Model and Tokenizer
    print("Loading Base Framework (Kronos-Tokenizer & Kronos-small)...")
    tokenizer = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base")
    tokenizer.eval().to(device)
    
    model = Kronos.from_pretrained("NeoQuasar/Kronos-small")
    
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
    model.print_trainable_parameters()
    model.to(device)
    
    # 5. Optimizer & Scheduler
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.05)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs * len(dataloader))
    
    # 6. Training Loop
    os.makedirs(output_dir, exist_ok=True)
    best_loss = float('inf')
    
    for epoch in range(epochs):
        model.train()
        total_loss = 0.0
        start_time = time.time()
        
        for step, (x, x_stamp) in enumerate(dataloader):
            x = x.to(device)
            x_stamp = x_stamp.to(device)
            
            # Tokenize on-the-fly (Tokenizer remains frozen)
            with torch.no_grad():
                token_seq_0, token_seq_1 = tokenizer.encode(x, half=True)
                
            # Offset targets for Autoregressive LM prediction
            token_in = [token_seq_0[:, :-1], token_seq_1[:, :-1]]
            token_out = [token_seq_0[:, 1:], token_seq_1[:, 1:]]
            stamp_in = x_stamp[:, :-1, :]
            
            # Forward pass through LoRA model
            s1_logits, s2_logits = model(token_in[0], token_in[1], stamp_in)
            
            # Kronos specific dual-head CE loss 
            # Note: peft wraps the model, so original methods are inside `base_model.model` if not exposed
            base_model = model.base_model.model if hasattr(model, "base_model") else model
            loss, s1_loss, s2_loss = base_model.head.compute_loss(s1_logits, s2_logits, token_out[0], token_out[1])
            
            # Backward
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
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
            market_name = os.path.basename(csv_file).split('_')[0] + "_" + os.path.basename(csv_file).split('_')[1]
            save_path = os.path.join(output_dir, f"lora_{market_name}")
            model.save_pretrained(save_path)
            print(f"--> [Success] Saved new Best LoRA adapter to {save_path} (Loss: {best_loss:.4f})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Performance Balanced LoRA Fine-Tuning for Kronos")
    parser.add_argument("--csv_file", type=str, required=True, help="Path to target OHLCV CSV file")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch", type=int, default=16, help="Optimal for Apple M4 Pro 48G is 16~32")
    parser.add_argument("--lr", type=float, default=2e-4) 
    
    args = parser.parse_args()
    
    train_lora(
        csv_file=args.csv_file,
        epochs=args.epochs,
        batch_size=args.batch,
        lr=args.lr
    )
