"""
Phase 2 Data Fetcher: Multi-Modal Fundamental Factors Extraction

该脚本用于提取指定币种的历史 K 线数据，并同时向历史对齐提取：
1. 恐慌贪婪指数 (Fear & Greed Index)
2. 资金费率 (Funding Rate) 
以此生成融合了多模态基本面因子的 CSV 训练集。
"""

import os
import sys
import time
import requests
import pandas as pd
from datetime import datetime, timedelta

# Ensure parent directory is in sys.path for local imports
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from trading.data_fetcher import DataFetcher, is_crypto

def get_historical_fgi(limit=1000) -> pd.DataFrame:
    """获取历史 FGI 数据并格式化为 DataFrame (日期索引)"""
    print(f"Fetchting historical FGI (Limit: {limit} days)...")
    try:
        url = f"https://api.alternative.me/fng/?limit={limit}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json().get('data', [])
            if not data:
                return pd.DataFrame()
                
            df = pd.DataFrame(data)
            df['timestamps'] = pd.to_datetime(df['timestamp'], unit='s')
            df['fgi_value'] = pd.to_numeric(df['value'])
            
            # 使用日期作为索引，方便对齐 K 线
            df['date'] = df['timestamps'].dt.date
            df = df.set_index('date')
            return df[['fgi_value']]
    except Exception as e:
        print(f"Error fetching historical FGI: {e}")
    return pd.DataFrame()


def get_historical_funding_rate(fetcher: DataFetcher, symbol: str, start_ts: int, end_ts: int) -> pd.DataFrame:
    """获取 Binance 历史资金费率 (每个时间窗口8小时一结)"""
    # 历史资金费率接口 `fapi/v1/fundingRate`
    if not is_crypto(symbol):
        return pd.DataFrame()
        
    base_sym = symbol.replace('/', '') + "T"
    print(f"Fetching historical funding rates for {base_sym}...")
    
    all_data = []
    current_ts = start_ts
    
    try:
        while current_ts < end_ts:
            params = {
                'symbol': base_sym,
                'startTime': current_ts,
                'limit': 1000
            }
            res = fetcher.swap_exchange.fapiPublicGetFundingRate(params)
            if not res:
                break
                
            all_data.extend(res)
            # update current_ts to the last fetched record's timestamp + 1
            last_record_ts = int(res[-1]['fundingTime'])
            if last_record_ts <= current_ts:
                break # prevent infinite loops if API is stuck
            current_ts = last_record_ts + 1
            time.sleep(0.5)
            
    except Exception as e:
         print(f"Error fetching historical funding rate: {e}")
         
    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data)
    df['fundingTime'] = pd.to_datetime(pd.to_numeric(df['fundingTime']), unit='ms')
    df['fundingRate'] = pd.to_numeric(df['fundingRate'])
    df = df.sort_values('fundingTime').set_index('fundingTime')
    return df[['fundingRate']]


def main():
    symbol = "BTC/USDT"
    timeframe = "1h"
    days_to_fetch = 365 # Default to 1 year back
    
    output_dir = os.path.join(ROOT, "data")
    os.makedirs(output_dir, exist_ok=True)
    outfile = os.path.join(output_dir, f"{symbol.replace('/','_')}_{timeframe}_phase2.csv")

    fetcher = DataFetcher()

    end_dt = datetime.utcnow()
    start_dt = end_dt - timedelta(days=days_to_fetch)
    start_str = start_dt.strftime('%Y-%m-%d')
    end_str = end_dt.strftime('%Y-%m-%d')

    print(f"== Phase 2 Data Extraction for {symbol} ==")
    print(f"Period: {start_str} to {end_str}")

    # 1. 获取主 K 线序列
    print("\n1. Fetching OHLCV...")
    ohlcv_df = fetcher.fetch_historical(symbol, timeframe, start_str, end_str)
    if ohlcv_df.empty:
        print("Failed to fetch OHLCV. Exiting.")
        return
        
    # 设置时间戳为索引以便对齐
    ohlcv_df = ohlcv_df.set_index('timestamps')

    # 2. 获取 FGI 历史序列
    print("\n2. Fetching FGI...")
    fgi_df = get_historical_fgi(limit=days_to_fetch + 10)
    
    # 将 K 线的 datetime 提取出 date，用于映射 FGI 的每日值
    if not fgi_df.empty:
        ohlcv_df['date'] = ohlcv_df.index.date
        ohlcv_df = ohlcv_df.join(fgi_df, on='date', how='left')
        ohlcv_df = ohlcv_df.drop(columns=['date'])
        # FGI 每日更新一次，缺失的时段用前序数据填充向前延伸
        ohlcv_df['fgi_value'] = ohlcv_df['fgi_value'].ffill().bfill()
    else:
        ohlcv_df['fgi_value'] = 50.0  # Fallback Neutral

    # 3. 获取资金费率历史序列
    print("\n3. Fetching Funding Rates...")
    start_ts = int(start_dt.timestamp() * 1000)
    end_ts = int(end_dt.timestamp() * 1000)
    fr_df = get_historical_funding_rate(fetcher, symbol, start_ts, end_ts)
    
    if not fr_df.empty:
        # 使用 merge_asof 对齐最接近的时间戳（向后匹配，因为资金费率是在结息点生效）
        ohlcv_df = ohlcv_df.sort_index()
        fr_df = fr_df.sort_index()
        ohlcv_df = pd.merge_asof(
            ohlcv_df, 
            fr_df, 
            left_index=True, 
            right_index=True, 
            direction='backward'
        )
        ohlcv_df['fundingRate'] = ohlcv_df['fundingRate'].ffill().fillna(0.0)
    else:
        ohlcv_df['fundingRate'] = 0.0

    # 恢复 timestamps 为普通列并保存
    ohlcv_df = ohlcv_df.reset_index()
    
    print("\n4. Final Data Preview:")
    print(ohlcv_df.head())
    print(ohlcv_df.tail())
    
    ohlcv_df.to_csv(outfile, index=False)
    print(f"\n=> Phase 2 dataset saved to {outfile}")

if __name__ == "__main__":
    main()
