import os
import sys
import argparse
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions.categorical import Categorical
from tqdm import tqdm, trange

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from model.kronos import Kronos, KronosTokenizer, calc_time_stamps
from finetune_rlhf.env import CryptoTradingEnv

def compute_gae(rewards, values, gamma=0.99, lam=0.95):
    """
    Generalized Advantage Estimation.
    """
    advantages = torch.zeros_like(rewards)
    returns = torch.zeros_like(rewards)
    last_gae = 0
    next_value = 0 # Assume end of episode value is 0 for simplicity

    for t in reversed(range(len(rewards))):
        delta = rewards[t] + gamma * next_value - values[t]
        advantages[t] = last_gae = delta + gamma * lam * last_gae
        next_value = values[t]
        
    returns = advantages + values
    return advantages, returns

def process_observation(tokenizer, obs_data, obs_time, device, max_context=400):
    """
    Tokens prep for Kronos forward pass.
    """
    # Z-score normalize the data
    obs_mean = np.mean(obs_data, axis=0)
    obs_std = np.std(obs_data, axis=0)
    
    tiny_std_mask = obs_std < 1.0
    obs_std[tiny_std_mask] = 1.0
    obs_mean[tiny_std_mask] = 0.0
    
    obs_norm = (obs_data - obs_mean) / (obs_std + 1e-5)
    obs_norm = np.clip(obs_norm, -5.0, 5.0)

    # obs_norm is shape (seq_len, feature_dim)
    # obs_time is shape (seq_len, time_dim)
    x = torch.tensor(obs_norm, dtype=torch.float32).unsqueeze(0).to(device)
    # calculate timestamp features
    x_time_series = pd.Series(obs_time)
    x_time_df = calc_time_stamps(x_time_series)
    x_stamp = torch.tensor(x_time_df.values, dtype=torch.float32).unsqueeze(0).to(device)
    
    # Tokenize
    with torch.no_grad():
        x_token = tokenizer.encode(x, half=True)
        s1_ids = x_token[0]
        s2_ids = x_token[1]
        
    # sequence length management
    if s1_ids.size(1) > max_context:
        s1_ids = s1_ids[:, -max_context:]
        s2_ids = s2_ids[:, -max_context:]
        x_stamp = x_stamp[:, -max_context:, :]
        
    return s1_ids, s2_ids, x_stamp

def train_ppo():
    # RL Hyperparameters
    learning_rate = 1e-5
    gamma = 0.99
    gae_lambda = 0.95
    clip_epsilon = 0.2
    c_value = 0.5
    c_entropy = 0.01
    num_episodes = 500       # SCALED UP from 50
    steps_per_episode = 2048 # SCALED UP from 512 (Extended trajectory simulation)
    ppo_epochs = 4
    mini_batch_size = 64
    max_context = 400
    
    device = torch.device('mps' if torch.backends.mps.is_available() else 'cuda' if torch.cuda.is_available() else 'cpu')
    print(f"🚀 Using device: {device}")

    # 1. Load Model and Tokenizer
    print("Loading Base Framework (Kronos-Tokenizer & Kronos-small)...")
    tokenizer = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base").to(device)
    model = Kronos.from_pretrained("NeoQuasar/Kronos-small").to(device)
    
    # Freeze the base transformer, only train the Actor and Value heads for MVP stability
    for param in model.parameters():
        param.requires_grad = False
        
    # Unfreeze the heads we just added
    for param in model.actor_head.parameters():
        param.requires_grad = True
    for param in model.value_head.parameters():
        param.requires_grad = True

    optimizer = optim.Adam([
        {'params': model.actor_head.parameters(), 'lr': learning_rate},
        {'params': model.value_head.parameters(), 'lr': learning_rate * 5} # Critic usually needs higher LR
    ])

    # 2. Load Environment Data
    # For Phase 4 we use Phase 2's dataset logic or load a standard BTC CSV
    csv_path = "data/BTC_USDT_1h_phase2.csv" # Adjusted to existing data
    if not os.path.exists(csv_path):
        print(f"⚠️ {csv_path} not found. Ensure historical data is fetched.")
        return
        
    print(f"📊 Loading environment data from: {csv_path}")
    df = pd.read_csv(csv_path)
    df['timestamps'] = pd.to_datetime(df['timestamps'])
    df.set_index('timestamps', inplace=True)
    df.sort_index(inplace=True)
    
    env = CryptoTradingEnv(df=df, window_size=max_context)
    
    print("🥊 Starting PPO Alignment...")
    for episode in range(num_episodes):
        obs_tuple = env.reset()
        
        states_s1, states_s2, states_stamp = [], [], []
        actions, log_probs, rewards, values = [], [], [], []
        
        # --- Rollout Phase ---
        model.eval()
        for step in trange(steps_per_episode, desc=f"Episode {episode+1} Rollout"):
            obs_data, obs_time, pos = obs_tuple
            s1_ids, s2_ids, stamp = process_observation(tokenizer, obs_data, obs_time, device, max_context)
            
            with torch.no_grad():
                # We only need the prediction for the last token to decide the action
                actor_logits, value_pred = model.forward_rl(s1_ids, s2_ids, stamp)
                
                step_logits = actor_logits[0, -1, :] # Last seq step
                step_val = value_pred[0, -1]
                
                dist = Categorical(logits=step_logits)
                action = dist.sample()
                log_prob = dist.log_prob(action)
                
            obs_tuple, reward, done, info = env.step(action.item())
            
            states_s1.append(s1_ids)
            states_s2.append(s2_ids)
            states_stamp.append(stamp)
            actions.append(action)
            log_probs.append(log_prob)
            rewards.append(reward)
            values.append(step_val)
            
            if done:
                break
                
        # --- Optimization Phase ---
        # Convert to tensors
        actions_t = torch.stack(actions).to(device)
        log_probs_t = torch.stack(log_probs).to(device)
        rewards_t = torch.tensor(rewards, dtype=torch.float32).to(device)
        values_t = torch.stack(values).to(device)
        
        advantages, returns = compute_gae(rewards_t, values_t, gamma, gae_lambda)
        # Normalize advantages
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        
        model.train()
        dataset_size = len(actions)
        indices = np.arange(dataset_size)
        
        epoch_v_loss = 0
        epoch_p_loss = 0
        
        for _ in range(ppo_epochs):
            np.random.shuffle(indices)
            for start in range(0, dataset_size, mini_batch_size):
                end = start + mini_batch_size
                mb_indices = indices[start:end]
                
                # We need to re-forward batch
                # Since sequence lengths are strictly max_context, we can stack them
                mb_s1 = torch.cat([states_s1[i] for i in mb_indices], dim=0)
                mb_s2 = torch.cat([states_s2[i] for i in mb_indices], dim=0)
                mb_stamp = torch.cat([states_stamp[i] for i in mb_indices], dim=0)
                
                mb_actions = actions_t[mb_indices]
                mb_advantages = advantages[mb_indices]
                mb_returns = returns[mb_indices]
                mb_old_log_probs = log_probs_t[mb_indices]
                
                new_actor_logits, new_values = model.forward_rl(mb_s1, mb_s2, mb_stamp)
                # extract last token outputs
                new_actor_logits = new_actor_logits[:, -1, :]
                new_values = new_values[:, -1]
                
                dist = Categorical(logits=new_actor_logits)
                new_log_probs = dist.log_prob(mb_actions)
                entropy = dist.entropy().mean()
                
                ratio = torch.exp(new_log_probs - mb_old_log_probs)
                
                # Clipped Surrogate Objective
                surr1 = ratio * mb_advantages
                surr2 = torch.clamp(ratio, 1.0 - clip_epsilon, 1.0 + clip_epsilon) * mb_advantages
                actor_loss = -torch.min(surr1, surr2).mean()
                
                # Value Loss
                value_loss = F.mse_loss(new_values, mb_returns)
                
                # Total Loss
                loss = actor_loss + c_value * value_loss - c_entropy * entropy
                
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=0.5)
                optimizer.step()
                
                epoch_p_loss += actor_loss.item()
                epoch_v_loss += value_loss.item()
                
        print(f"Episode {episode+1} | PnL: {info['balance']:.4f} | R: {sum(rewards):.4f} | Actor Loss: {epoch_p_loss/ppo_epochs:.4f} | Value Loss: {epoch_v_loss/ppo_epochs:.4f}")

    # 3. Save PPO RL Heads
    print("💾 Saving PPO checkpoint...")
    os.makedirs("outputs/rl_heads", exist_ok=True)
    torch.save(model.actor_head.state_dict(), "outputs/rl_heads/actor_head.pth")
    torch.save(model.value_head.state_dict(), "outputs/rl_heads/value_head.pth")
    print("✅ RLHF Phase Complete.")

if __name__ == "__main__":
    import torch.nn.functional as F
    train_ppo()
