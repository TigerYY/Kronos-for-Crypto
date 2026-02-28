import os
import torch
import numpy as np
import pandas as pd
from torch.utils.data import Dataset

class CryptoDataset(Dataset):
    """
    Lightweight, native PyTorch Dataset for cryptocurrency CSV files.
    Extracts rolling OHLCV windows for Kronos LoRA fine-tuning.
    """
    def __init__(self, csv_file: str, lookback: int = 400, pred_len: int = 12):
        self.lookback = lookback
        self.pred_len = pred_len
        self.window = lookback + pred_len + 1  # +1 because we need autoregressive targets
        
        if not os.path.exists(csv_file):
            raise FileNotFoundError(f"Dataset CSV not found: {csv_file}")
            
        print(f"Loading {csv_file} into memory...")
        df = pd.read_csv(csv_file)
        
        # Parse timestamp safely whether it's int ms or string
        if 'timestamp' in df.columns:
            df['datetime'] = pd.to_datetime(df['timestamp'])
        elif 'timestamps' in df.columns:
            df['datetime'] = pd.to_datetime(df['timestamps'])
        elif 'datetime' not in df.columns:
            df['datetime'] = pd.to_datetime(df.index)
            
        # Generate essential time features matching Kronos pre-training
        df['minute'] = df['datetime'].dt.minute
        df['hour'] = df['datetime'].dt.hour
        df['weekday'] = df['datetime'].dt.weekday
        df['day'] = df['datetime'].dt.day
        df['month'] = df['datetime'].dt.month
        
        # Required Kronos numerical features
        self.feature_list = ['open', 'high', 'low', 'close', 'volume']
        self.time_feature_list = ['minute', 'hour', 'weekday', 'day', 'month']
        
        # Check for external fundamental features (Phase 2)
        self.ext_feature_list = []
        if 'fgi_value' in df.columns and 'fundingRate' in df.columns:
            self.ext_feature_list = ['fgi_value', 'fundingRate']
            print(f"Detected Multi-Modal External Features: {self.ext_feature_list}")
        
        # In case 'amount' is missing in standard OHLCV, approximate it
        if 'amount' not in df.columns:
            df['amount'] = df['volume'] * df['close']
        self.feature_list.append('amount')
            
        # Clean data (Forward fill external features just in case of daily sparse updates)
        df = df[self.feature_list + self.time_feature_list + self.ext_feature_list].ffill().fillna(0)
            
        self.data_x = df[self.feature_list].values.astype(np.float32)
        self.data_stamp = df[self.time_feature_list].values.astype(np.float32)
        
        if self.ext_feature_list:
            self.data_ext = df[self.ext_feature_list].values.astype(np.float32)
        else:
            self.data_ext = None
        
        self.n_samples = max(0, len(df) - self.window + 1)
        print(f"Loaded {self.n_samples} valid sliding windows of length {self.window}.")
        
    def __len__(self) -> int:
        return self.n_samples
        
    def __getitem__(self, idx: int) -> tuple:
        x = self.data_x[idx : idx + self.window].copy()
        x_stamp = self.data_stamp[idx : idx + self.window].copy()
        
        # Instance-level Normalization (Crucial for Kronos Tokenization)
        x_mean = np.mean(x, axis=0)
        x_std = np.std(x, axis=0)
        
        # Prevent zero-division & noise blowup in low liquidity assets
        x_std[x_std < 1.0] = 1.0 
        
        x = (x - x_mean) / (x_std + 1e-5)
        
        # Hard clip to prevent extreme outlier hallucination during training
        x = np.clip(x, -5.0, 5.0)
        
        if self.data_ext is not None:
            x_ext = self.data_ext[idx : idx + self.window].copy()
            x_ext_mean = np.mean(x_ext, axis=0)
            x_ext_std = np.std(x_ext, axis=0)
            x_ext_std[x_ext_std < 1e-5] = 1.0
            x_ext = (x_ext - x_ext_mean) / (x_ext_std + 1e-5)
            return torch.from_numpy(x), torch.from_numpy(x_stamp), torch.from_numpy(x_ext)
            
        return torch.from_numpy(x), torch.from_numpy(x_stamp)
