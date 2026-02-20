"""
数据获取模块

支持两种模式：
1. 实时模式（online）：通过 ccxt 从 Binance 拉取最新 OHLCV 数据
2. 离线模式（offline）：读取本地 CSV 文件，用于回测

设计要点：本地缓存机制，避免频繁 API 请求被限速。
"""

import os
import time
import pandas as pd
import ccxt
from typing import Optional, Dict
from datetime import datetime, timedelta, timezone


# 本地缓存目录
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'cache')


class DataFetcher:
    """
    OHLCV 数据获取器

    使用 CCXTBinance 拉取数据，内置内存缓存避免重复请求。
    缓存有效期：5m 数据缓存 30 秒，其他时框缓存 60 秒。
    """

    # 各时框的缓存有效期（秒）
    CACHE_TTL = {
        '5m':  30,
        '15m': 60,
        '1h':  120,
        '4h':  300,
        '1d':  600,
    }

    def __init__(self, exchange_id: str = 'binance'):
        """
        Args:
            exchange_id: ccxt 交易所 ID，默认 'binance'
        """
        # 初始化交易所（公开接口，无需 API Key）
        exchange_class = getattr(ccxt, exchange_id)
        self.exchange = exchange_class({
            'timeout': 30000,
            'enableRateLimit': True,  # 自动遵守频率限制
        })

        # 内存缓存: key=(symbol, timeframe), value=(timestamp, DataFrame)
        self._cache: Dict[tuple, tuple] = {}

        # 确保缓存目录存在
        os.makedirs(CACHE_DIR, exist_ok=True)

    # ------------------------------------------------------------------ #
    # 实时数据获取
    # ------------------------------------------------------------------ #

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 512,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        获取 OHLCV 数据（含缓存机制）

        Args:
            symbol:    交易对，如 'BTC/USDT'
            timeframe: 时间周期，如 '5m', '15m', '1h'
            limit:     K线数量
            use_cache: 是否使用内存缓存

        Returns:
            包含 [timestamps, open, high, low, close, volume, amount] 的 DataFrame
        """
        cache_key = (symbol, timeframe, limit)

        # 检查内存缓存是否仍然有效
        if use_cache and cache_key in self._cache:
            cached_time, cached_df = self._cache[cache_key]
            ttl = self.CACHE_TTL.get(timeframe, 60)
            if time.time() - cached_time < ttl:
                return cached_df.copy()

        # 从交易所拉取数据（额外多拉 20 条，防止数据截断）
        raw = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit + 20)

        df = self._raw_to_df(raw).tail(limit).reset_index(drop=True)

        # 更新内存缓存
        self._cache[cache_key] = (time.time(), df)

        return df.copy()

    def fetch_multi_timeframe(
        self,
        symbol: str,
        timeframes: list,
        limit: int = 512,
    ) -> Dict[str, Optional[pd.DataFrame]]:
        """
        批量获取多时框数据

        Returns:
            dict: {'5m': df, '15m': df, '1h': df}  失败的时框返回 None
        """
        result = {}
        for tf in timeframes:
            try:
                result[tf] = self.fetch_ohlcv(symbol, tf, limit)
            except Exception as e:
                print(f"[DataFetcher] 获取 {symbol} {tf} 失败: {e}")
                result[tf] = None
        return result

    # ------------------------------------------------------------------ #
    # 历史数据（用于回测）
    # ------------------------------------------------------------------ #

    def fetch_historical(
        self,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """
        获取历史 OHLCV 数据（用于回测）

        优先读取本地缓存文件，若不存在则从 Binance 分段拉取并缓存。

        Args:
            symbol:     交易对，如 'BTC/USDT'
            timeframe:  时间周期
            start_date: 开始日期，如 '2024-01-01'
            end_date:   结束日期，如 '2024-06-01'

        Returns:
            历史 OHLCV DataFrame
        """
        cache_file = self._get_cache_filepath(symbol, timeframe, start_date, end_date)

        if os.path.exists(cache_file):
            print(f"[DataFetcher] 读取本地缓存: {cache_file}")
            df = pd.read_csv(cache_file, parse_dates=['timestamps'])
            return df

        print(f"[DataFetcher] 从 Binance 拉取历史数据: {symbol} {timeframe} {start_date}~{end_date}")
        df = self._fetch_historical_from_exchange(symbol, timeframe, start_date, end_date)

        # 保存到本地缓存
        df.to_csv(cache_file, index=False)
        print(f"[DataFetcher] 已缓存到: {cache_file}")

        return df

    def _fetch_historical_from_exchange(
        self,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """分段从 Binance 拉取完整历史数据（每次最多 1000 条）"""
        start_ts = int(pd.Timestamp(start_date, tz='UTC').timestamp() * 1000)
        end_ts = int(pd.Timestamp(end_date, tz='UTC').timestamp() * 1000)

        all_data = []
        current_ts = start_ts

        while current_ts < end_ts:
            try:
                raw = self.exchange.fetch_ohlcv(
                    symbol, timeframe,
                    since=current_ts,
                    limit=1000,
                )
                if not raw:
                    break

                all_data.extend(raw)
                current_ts = raw[-1][0] + 1  # 下一段从最后一条的下一毫秒开始

                # 避免触发频率限制
                time.sleep(self.exchange.rateLimit / 1000)

            except Exception as e:
                print(f"[DataFetcher] 分段拉取失败: {e}")
                break

        if not all_data:
            return pd.DataFrame(columns=['timestamps', 'open', 'high', 'low', 'close', 'volume', 'amount'])

        df = self._raw_to_df(all_data)

        # 过滤到指定时间范围
        df = df[df['timestamps'] <= pd.Timestamp(end_date, tz='UTC').tz_localize(None)]
        return df.reset_index(drop=True)

    # ------------------------------------------------------------------ #
    # 工具方法
    # ------------------------------------------------------------------ #

    def _raw_to_df(self, raw: list) -> pd.DataFrame:
        """将 ccxt 返回的原始列表转为标准 DataFrame"""
        df = pd.DataFrame(raw, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamps'] = pd.to_datetime(df['timestamp'], unit='ms')

        # 将数值列统一为 float
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # 构造 amount 列（成交额 = close × volume）
        df['amount'] = df['close'] * df['volume']

        # 去除重复时间戳，保留最新的
        df = df.drop_duplicates(subset='timestamps', keep='last')
        df = df.sort_values('timestamps').reset_index(drop=True)

        # 只保留有效列
        return df[['timestamps', 'open', 'high', 'low', 'close', 'volume', 'amount']]

    def _get_cache_filepath(
        self,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str,
    ) -> str:
        """生成本地缓存文件路径"""
        safe_symbol = symbol.replace('/', '_')
        filename = f"{safe_symbol}_{timeframe}_{start_date}_{end_date}.csv"
        return os.path.join(CACHE_DIR, filename)

    def get_current_price(self, symbol: str) -> float:
        """获取当前最新价格（ticker）"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return float(ticker['last'])
        except Exception as e:
            print(f"[DataFetcher] 获取 {symbol} 实时价格失败: {e}")
            return 0.0
