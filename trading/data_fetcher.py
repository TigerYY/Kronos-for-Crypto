"""
数据获取模块（双数据源版）

路由规则（根据 symbol 格式自动判断）：
- 含 '/' 的 symbol（如 'BTC/USDT'）→ ccxt Binance 加密货币 API
- 其他 symbol（如 'ES=F', 'GC=F'）→ yfinance 传统金融数据（延迟约15分钟）

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

# yfinance 时框映射（ccxt 格式 → yfinance interval 格式）
YFINANCE_TF_MAP = {
    '5m':  '5m',
    '15m': '15m',
    '1h':  '60m',   # yfinance 用 60m 而非 1h
    '4h':  '1h',    # yfinance 无 4h，用 1h 采样后 resample 为 4h
    '1d':  '1d',
}

# 非加密货币标的的显示名称（yfinance 路由）
TRADITIONAL_SYMBOL_NAMES = {
    'ES=F':     '标普500期货 (ES)',
    'NQ=F':     '纳指期货 (NQ)',
    'CL=F':     '原油期货 (CL)',
    'EURUSD=X': '欧元/美元',
}

# Binance USDT-M 永续合约映射：用户友好名称 → ccxt swap symbol
# 含 '/' 但非 Binance 现货市场的品种走此路由（实时无延迟）
BINANCE_SWAP_SYMBOLS: dict[str, str] = {
    'XAU/USDT': 'XAU/USDT:USDT',   # 黄金永续合约
}


def is_swap(symbol: str) -> bool:
    """判断是否为 Binance 永续合约 symbol（在 BINANCE_SWAP_SYMBOLS 映射表中）"""
    return symbol in BINANCE_SWAP_SYMBOLS


def is_crypto(symbol: str) -> bool:
    """判断是否为普通加密货币 symbol（含 '/'，且不是永续合约）"""
    return '/' in symbol and not is_swap(symbol)


class DataFetcher:
    """
    OHLCV 数据获取器（双数据源）

    - 加密货币（BTC/USDT 等）：使用 ccxt Binance API
    - 传统金融标的（ES=F 等）：使用 yfinance（数据延迟约 15 分钟）

    内置内存缓存，避免高频请求被限速：
      5m → 30s，15m → 60s，1h/4h → 120~300s，1d → 600s
    """

    CACHE_TTL = {
        '5m':  30,
        '15m': 60,
        '1h':  120,
        '4h':  300,
        '1d':  600,
    }

    def __init__(self, exchange_id: str = 'binance'):
        # 初始化 ccxt Binance 现货交易所（加密货币用）
        exchange_class = getattr(ccxt, exchange_id)
        self.exchange = exchange_class({
            'timeout': 30000,
            'enableRateLimit': True,
        })

        # 初始化 Binance USDT-M 永续合约交易所（黄金等永续合约用，实时无延迟）
        self.swap_exchange = ccxt.binanceusdm({
            'timeout': 30000,
            'enableRateLimit': True,
        })

        # 内存缓存: key=(symbol, timeframe, limit), value=(timestamp, DataFrame)
        self._cache: Dict[tuple, tuple] = {}

        os.makedirs(CACHE_DIR, exist_ok=True)

    # ------------------------------------------------------------------ #
    # 公共接口：自动路由到对应数据源
    # ------------------------------------------------------------------ #

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 512,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        获取 OHLCV 数据，根据 symbol 自动选择数据源。

        Args:
            symbol:    交易标的，如 'BTC/USDT' 或 'ES=F'
            timeframe: 时间周期，如 '15m', '1h', '4h', '1d'
            limit:     K线数量
            use_cache: 是否使用内存缓存
        """
        cache_key = (symbol, timeframe, limit)

        if use_cache and cache_key in self._cache:
            cached_time, cached_df = self._cache[cache_key]
            ttl = self.CACHE_TTL.get(timeframe, 60)
            if time.time() - cached_time < ttl:
                return cached_df.copy()

        if is_swap(symbol):
            # 永续合约路由（binanceusdm），实时无延迟
            df = self._fetch_swap(symbol, timeframe, limit)
        elif is_crypto(symbol):
            df = self._fetch_crypto(symbol, timeframe, limit)
        else:
            df = self._fetch_yfinance(symbol, timeframe, limit)

        df = self._pad_dataframe(df, limit)

        self._cache[cache_key] = (time.time(), df)
        return df.copy()

    def _pad_dataframe(self, df: pd.DataFrame, target_len: int) -> pd.DataFrame:
        """用首行数据反向填补序列长度，满足模型所需的最小 Lookback Context"""
        if df.empty or len(df) >= target_len:
            return df
            
        pad_len = target_len - len(df)
        first_row = df.iloc[[0]].copy()
        
        diff = pd.Timedelta(days=1)
        if len(df) > 1:
            diff = df['timestamps'].iloc[1] - df['timestamps'].iloc[0]
            
        pad_dfs = [first_row] * pad_len
        pad_df = pd.concat(pad_dfs, ignore_index=True)
        
        first_ts = df['timestamps'].iloc[0]
        pad_ts = [first_ts - diff * (pad_len - i) for i in range(pad_len)]
        pad_df['timestamps'] = pad_ts
        
        # 填充数据的成交量归零以降低杂音
        pad_df['volume'] = 0.0
        pad_df['amount'] = 0.0
        
        return pd.concat([pad_df, df], ignore_index=True)

    def fetch_multi_timeframe(
        self,
        symbol: str,
        timeframes: list,
        limit: int = 512,
    ) -> Dict[str, Optional[pd.DataFrame]]:
        """批量获取多时框数据，失败的时框返回 None"""
        result = {}
        for tf in timeframes:
            try:
                result[tf] = self.fetch_ohlcv(symbol, tf, limit)
            except Exception as e:
                import traceback
                print(f"[DataFetcher] 获取 {symbol} {tf} 失败: {e}\n{traceback.format_exc()}")
                result[tf] = None
        return result

    def fetch_historical(
        self,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """获取历史数据（优先本地缓存，否则从对应数据源拉取）"""
        cache_file = self._get_cache_filepath(symbol, timeframe, start_date, end_date)

        if os.path.exists(cache_file):
            print(f"[DataFetcher] 读取本地缓存: {cache_file}")
            df = pd.read_csv(cache_file, parse_dates=['timestamps'])
            return df

        if is_swap(symbol):
            print(f"[DataFetcher] 从 Binance 永续合约拉取历史数据: {symbol} {timeframe}")
            df = self._fetch_historical_swap(symbol, timeframe, start_date, end_date)
        elif is_crypto(symbol):
            print(f"[DataFetcher] 从 Binance 拉取历史数据: {symbol} {timeframe}")
            df = self._fetch_historical_crypto(symbol, timeframe, start_date, end_date)
        else:
            print(f"[DataFetcher] 从 yfinance 拉取历史数据: {symbol} {timeframe}")
            df = self._fetch_historical_yfinance(symbol, timeframe, start_date, end_date)

        df.to_csv(cache_file, index=False)
        print(f"[DataFetcher] 已缓存到: {cache_file}")
        return df

    def get_current_price(self, symbol: str) -> float:
        """获取当前最新价格"""
        try:
            if is_swap(symbol):
                # 永续合约实时价格（无延迟）
                swap_sym = BINANCE_SWAP_SYMBOLS[symbol]
                ticker = self.swap_exchange.fetch_ticker(swap_sym)
                return float(ticker['last'])
            elif is_crypto(symbol):
                ticker = self.exchange.fetch_ticker(symbol)
                return float(ticker['last'])
            else:
                import yfinance as yf
                df = yf.download(symbol, period='1d', interval='1m',
                                 progress=False, auto_adjust=True)
                if not df.empty:
                    close = df['Close']
                    if isinstance(close, pd.DataFrame):
                        close = close.iloc[:, 0]
                    return float(close.iloc[-1])
        except Exception as e:
            print(f"[DataFetcher] 获取 {symbol} 实时价格失败: {e}")
        return 0.0

    def fetch_fgi(self) -> Dict[str, str]:
        """获取实时的恐惧贪婪指数 (Fear & Greed Index)"""
        try:
            import requests
            resp = requests.get('https://api.alternative.me/fng/?limit=1', timeout=5)
            if resp.status_code == 200:
                data = resp.json().get('data', [])
                if data:
                    return {
                        'value': data[0]['value'],
                        'classification': data[0]['value_classification']
                    }
        except Exception as e:
            print(f"[DataFetcher] 获取 FGI 失败: {e}")
        return {'value': '50', 'classification': 'Neutral'}

    def fetch_funding_rate(self, symbol: str) -> float:
        """获取目标币种在 Binance 永续合约的实时资金费率"""
        if is_swap(symbol):
            base_sym = BINANCE_SWAP_SYMBOLS[symbol]
        elif is_crypto(symbol):
            base_sym = symbol.replace('/', '') + "T" # e.g. BTC/USDT -> BTCUSDT
        else:
            return 0.0 # 传统金融无资金费率

        try:
            # 去除冒号后缀(如果是USDT-M的特殊标识)
            base_sym = base_sym.split(':')[0]
            # ccxt 本身支持 fetch_funding_rate，或者直接调用 implicit API
            # 这里调用 implicit API 确保拿到的是确切的实盘挂牌费率
            res = self.swap_exchange.fapiPublicGetPremiumIndex({'symbol': base_sym})
            return float(res.get('lastFundingRate', 0.0))
        except Exception as e:
            print(f"[DataFetcher] 获取 {symbol} 资金费率失败: {e}")
        return 0.0

    # ------------------------------------------------------------------ #
    # 加密货币数据源（ccxt Binance）
    # ------------------------------------------------------------------ #

    def _fetch_swap(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        """从 Binance USDT-M 永续合约拉取 OHLCV（实时，无延迟）"""
        swap_sym = BINANCE_SWAP_SYMBOLS[symbol]
        raw = self.swap_exchange.fetch_ohlcv(swap_sym, timeframe, limit=limit + 20)
        return self._raw_to_df(raw).tail(limit).reset_index(drop=True)

    def _fetch_historical_swap(
        self, symbol: str, timeframe: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """分段从 Binance USDT-M 永续合约拉取完整历史数据"""
        swap_sym = BINANCE_SWAP_SYMBOLS[symbol]
        start_ts = int(pd.Timestamp(start_date, tz='UTC').timestamp() * 1000)
        end_ts   = int(pd.Timestamp(end_date,   tz='UTC').timestamp() * 1000)

        all_data = []
        current_ts = start_ts
        while current_ts < end_ts:
            try:
                raw = self.swap_exchange.fetch_ohlcv(
                    swap_sym, timeframe, since=current_ts, limit=1000)
                if not raw:
                    break
                all_data.extend(raw)
                current_ts = raw[-1][0] + 1
                time.sleep(self.swap_exchange.rateLimit / 1000)
            except Exception as e:
                print(f"[DataFetcher] 永续合约历史分段拉取失败: {e}")
                break

        if not all_data:
            return pd.DataFrame(columns=['timestamps','open','high','low','close','volume','amount'])

        df = self._raw_to_df(all_data)
        df = df[df['timestamps'] <= pd.Timestamp(end_date, tz='UTC').tz_localize(None)]
        return df.reset_index(drop=True)

    def _fetch_crypto(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        """从 Binance 现货拉取加密货币 OHLCV"""
        raw = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit + 20)
        return self._raw_to_df(raw).tail(limit).reset_index(drop=True)

    def _fetch_historical_crypto(
        self, symbol: str, timeframe: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """分段从 Binance 拉取完整历史数据"""
        start_ts = int(pd.Timestamp(start_date, tz='UTC').timestamp() * 1000)
        end_ts   = int(pd.Timestamp(end_date,   tz='UTC').timestamp() * 1000)

        all_data = []
        current_ts = start_ts

        while current_ts < end_ts:
            try:
                raw = self.exchange.fetch_ohlcv(
                    symbol, timeframe, since=current_ts, limit=1000)
                if not raw:
                    break
                all_data.extend(raw)
                current_ts = raw[-1][0] + 1
                time.sleep(self.exchange.rateLimit / 1000)
            except Exception as e:
                print(f"[DataFetcher] 分段拉取失败: {e}")
                break

        if not all_data:
            return pd.DataFrame(columns=['timestamps','open','high','low','close','volume','amount'])

        df = self._raw_to_df(all_data)
        df = df[df['timestamps'] <= pd.Timestamp(end_date, tz='UTC').tz_localize(None)]
        return df.reset_index(drop=True)

    # ------------------------------------------------------------------ #
    # 传统金融数据源（yfinance）
    # ------------------------------------------------------------------ #

    def _fetch_yfinance(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        """
        通过 yfinance 拉取传统金融标的 OHLCV。

        yfinance intraday 数据时长限制：
          5m/15m: 最多 60 天  |  60m: 最多 730 天  |  1d: 无限制
        4h 通过对 1h 数据 resample 实现。
        """
        import yfinance as yf

        yf_interval = YFINANCE_TF_MAP.get(timeframe, '1h')
        period_map = {
            '5m':  '60d',
            '15m': '60d',
            '1h':  '730d',
            '4h':  '730d',
            '1d':  'max',
        }
        period = period_map.get(timeframe, '60d')

        df_raw = yf.download(
            symbol, period=period, interval=yf_interval,
            progress=False, auto_adjust=True,
        )

        if df_raw.empty:
            return pd.DataFrame(columns=['timestamps','open','high','low','close','volume','amount'])

        df = self._yfinance_to_df(df_raw)

        if timeframe == '4h':
            df = self._resample_df(df, '4h')

        return df.tail(limit).reset_index(drop=True)

    def _fetch_historical_yfinance(
        self, symbol: str, timeframe: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """通过 yfinance 拉取指定日期范围的历史数据"""
        import yfinance as yf

        yf_interval = YFINANCE_TF_MAP.get(timeframe, '1d')

        df_raw = yf.download(
            symbol, start=start_date, end=end_date,
            interval=yf_interval, progress=False, auto_adjust=True,
        )

        if df_raw.empty:
            return pd.DataFrame(columns=['timestamps','open','high','low','close','volume','amount'])

        df = self._yfinance_to_df(df_raw)

        if timeframe == '4h':
            df = self._resample_df(df, '4h')

        return df.reset_index(drop=True)

    # ------------------------------------------------------------------ #
    # 工具方法
    # ------------------------------------------------------------------ #

    def _raw_to_df(self, raw: list) -> pd.DataFrame:
        """将 ccxt 返回的原始列表转为标准 DataFrame"""
        df = pd.DataFrame(raw, columns=['timestamp','open','high','low','close','volume'])
        df['timestamps'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open','high','low','close','volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df['amount'] = df['close'] * df['volume']
        df = df.drop_duplicates(subset='timestamps', keep='last')
        df = df.sort_values('timestamps').reset_index(drop=True)
        return df[['timestamps','open','high','low','close','volume','amount']]

    def _yfinance_to_df(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """
        将 yfinance 返回的 DataFrame 转为与 ccxt 统一的标准格式。

        yfinance 新版（>=0.2.x）默认返回 MultiIndex 列：
            Level 0 = Price 字段（Close/High/Low/Open/Volume）
            Level 1 = Ticker（如 ES=F）
        必须用 xs(ticker, level='Ticker') 按 Ticker 切片，
        而不能直接 get_level_values(0)（会按字母排序返回，导致列名混乱）。
        """
        df = df_raw.copy()

        # ── 处理 MultiIndex 列（Price, Ticker 两级）──────────────────
        if isinstance(df.columns, pd.MultiIndex):
            # 取第一个 Ticker 名（单标的下载只有一个）
            ticker = df.columns.get_level_values(1)[0]
            try:
                # xs: 按 Ticker 层切片，得到以 Price 字段名为列的普通 DataFrame
                df = df.xs(ticker, axis=1, level=1)
            except Exception:
                # 备用：直接展开 level 0（可能有重复则取最后一条）
                df = df.loc[:, ~df.columns.get_level_values(0).duplicated(keep='last')]
                df.columns = df.columns.get_level_values(0)

        # ── 统一列名为小写 ─────────────────────────────────
        df = df.rename(columns={
            'Open': 'open', 'High': 'high',
            'Low':  'low',  'Close': 'close',
            'Volume': 'volume',
        })

        # ── 处理时间索引 ───────────────────────────────────
        df.index.name = 'timestamps'
        df = df.reset_index()
        df['timestamps'] = pd.to_datetime(df['timestamps'])

        # 去除时区（统一为 naive datetime，与 ccxt 保持一致）
        if df['timestamps'].dt.tz is not None:
            df['timestamps'] = df['timestamps'].dt.tz_localize(None)

        # ── 补充 amount 列、清洗数据 ───────────────────────────
        df['volume'] = pd.to_numeric(df.get('volume', 0), errors='coerce').fillna(0)
        df['amount'] = df['close'] * df['volume']
        df = df.dropna(subset=['open', 'high', 'low', 'close'])
        df = df.drop_duplicates(subset='timestamps', keep='last')
        df = df.sort_values('timestamps').reset_index(drop=True)

        return df[['timestamps', 'open', 'high', 'low', 'close', 'volume', 'amount']]

    def _resample_df(self, df: pd.DataFrame, rule: str) -> pd.DataFrame:
        """将分钟/小时 DataFrame resample 到更长周期（如 4h）"""
        df = df.set_index('timestamps')
        resampled = df.resample(rule).agg({
            'open':   'first',
            'high':   'max',
            'low':    'min',
            'close':  'last',
            'volume': 'sum',
            'amount': 'sum',
        }).dropna()
        return resampled.reset_index()

    def _get_cache_filepath(
        self, symbol: str, timeframe: str, start_date: str, end_date: str
    ) -> str:
        safe_symbol = symbol.replace('/', '_').replace('=', '_')
        filename = f"{safe_symbol}_{timeframe}_{start_date}_{end_date}.csv"
        return os.path.join(CACHE_DIR, filename)
