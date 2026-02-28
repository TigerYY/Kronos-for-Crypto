import numpy as np
import pandas as pd

class CryptoTradingEnv:
    """
    A vectorized-friendly custom trading environment for RLHF alignment.
    Actions:
      0: Short (-1)
      1: Flat (0)
      2: Long (+1)
    """
    def __init__(self, df: pd.DataFrame, window_size: int, commission: float = 0.0004):
        # Expected df to have at least ['open', 'high', 'low', 'close', 'volume']
        self.df = df.copy()
        self.window_size = window_size
        self.commission = commission
        
        # Ensure we have required columns
        req_cols = ['open', 'high', 'low', 'close', 'volume', 'amount']
        for col in req_cols:
            if col not in self.df.columns:
                raise ValueError(f"DataFrame must contain column: {col}")
                
        # We also need timestamps for Time Embedding
        if not isinstance(self.df.index, pd.DatetimeIndex):
            raise ValueError("DataFrame index must be a DatetimeIndex")
            
        self.data_values = self.df[req_cols].values
        self.timestamps = self.df.index
        
        self.n_steps = len(self.df)
        self.current_step = self.window_size
        
        self.position = 0 # -1, 0, 1
        self.balance = 1.0 # Normalized initial balance
        self.equity_curve = []
        
    def reset(self, start_idx=None):
        """
        Reset the environment to the beginning or to a random start index.
        """
        if start_idx is None:
            # Randomize start to increase variety, leave enough room to run an episode
            max_start = self.n_steps - 1000
            if max_start <= self.window_size:
                self.current_step = self.window_size
            else:
                self.current_step = np.random.randint(self.window_size, max_start)
        else:
            self.current_step = max(self.window_size, start_idx)
            
        self.position = 0
        self.balance = 1.0
        self.equity_curve = [self.balance]
        
        return self._get_observation()
        
    def _get_observation(self):
        """
        Returns the historical window and timestamps.
        """
        start_idx = self.current_step - self.window_size
        end_idx = self.current_step
        
        obs_data = self.data_values[start_idx:end_idx]
        obs_time = self.timestamps[start_idx:end_idx]
        
        return obs_data, obs_time, self.position
        
    def step(self, action: int):
        """
        Take an action and step the environment forward by 1 bar.
        Action mapping: 0 -> -1 (Short), 1 -> 0 (Flat), 2 -> 1 (Long)
        """
        target_position = action - 1
        
        # Calculate PnL for holding the previous position through this step
        current_price = self.data_values[self.current_step, 3] # 'close'
        prev_price = self.data_values[self.current_step - 1, 3]
        
        # Log return
        step_return = np.log(current_price / prev_price) * self.position
        
        # Calculate Commission
        trade_cost = 0.0
        if target_position != self.position:
            # We assume position sizing is 1x leverage of total equity
            trade_cost = abs(target_position - self.position) * self.commission
            
        # Total step reward (differential equity)
        reward = step_return - trade_cost
        
        # Update state
        self.balance = self.balance * np.exp(reward)
        self.equity_curve.append(self.balance)
        self.position = target_position
        self.current_step += 1
        
        # Check if done
        done = self.current_step >= self.n_steps - 1
        if self.balance <= 0.1: # Went bankrupt (-90%)
            done = True
            reward -= 1.0 # Heavy penalty
            
        obs_data, obs_time, pos = self._get_observation() if not done else (None, None, self.position)
        
        info = {
            'balance': self.balance,
            'price': current_price,
            'position': self.position
        }
        
        return (obs_data, obs_time, pos), reward, done, info
