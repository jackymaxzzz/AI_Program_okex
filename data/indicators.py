"""
技术指标计算模块
"""
import pandas as pd
import numpy as np
from typing import Dict

def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算所有技术指标
    
    Args:
        df: OHLCV DataFrame
    
    Returns:
        添加了技术指标的DataFrame
    """
    try:
        # 移动平均线
        df['sma_5'] = df['close'].rolling(window=5, min_periods=1).mean()
        df['sma_20'] = df['close'].rolling(window=20, min_periods=1).mean()
        df['sma_50'] = df['close'].rolling(window=50, min_periods=1).mean()
        
        # 指数移动平均线
        df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
        
        # MACD
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 布林带
        df['bb_middle'] = df['close'].rolling(20).mean()
        bb_std = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # ATR (平均真实波幅)
        df['tr'] = df[['high', 'low', 'close']].apply(
            lambda x: max(
                x['high'] - x['low'],
                abs(x['high'] - x['close']),
                abs(x['low'] - x['close'])
            ), axis=1
        )
        df['atr_14'] = df['tr'].rolling(14).mean()
        
        # 成交量指标
        df['volume_ma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        # 支撑阻力位
        df['resistance'] = df['high'].rolling(20).max()
        df['support'] = df['low'].rolling(20).min()
        
        # 填充NaN值
        df = df.bfill().ffill()
        
        return df
        
    except Exception as e:
        print(f"[失败] 技术指标计算失败: {e}")
        return df


def get_market_trend(df: pd.DataFrame) -> Dict:
    """
    判断市场趋势
    
    Args:
        df: 包含技术指标的DataFrame
    
    Returns:
        趋势分析字典
    """
    try:
        current_price = df['close'].iloc[-1]
        
        # 多时间框架趋势分析
        trend_short = "上涨" if current_price > df['sma_20'].iloc[-1] else "下跌"
        trend_medium = "上涨" if current_price > df['sma_50'].iloc[-1] else "下跌"
        
        # MACD趋势
        macd_trend = "bullish" if df['macd'].iloc[-1] > df['macd_signal'].iloc[-1] else "bearish"
        
        # 综合趋势判断
        if trend_short == "上涨" and trend_medium == "上涨":
            overall_trend = "强势上涨"
        elif trend_short == "下跌" and trend_medium == "下跌":
            overall_trend = "强势下跌"
        else:
            overall_trend = "震荡整理"
        
        return {
            'short_term': trend_short,
            'medium_term': trend_medium,
            'macd': macd_trend,
            'overall': overall_trend,
            'rsi_level': df['rsi'].iloc[-1]
        }
    except Exception as e:
        print(f"[失败] 趋势分析失败: {e}")
        return {}


def get_support_resistance_levels(df: pd.DataFrame, lookback: int = 20) -> Dict:
    """
    计算支撑阻力位
    
    Args:
        df: 包含技术指标的DataFrame
        lookback: 回看周期
    
    Returns:
        支撑阻力位字典
    """
    try:
        recent_high = df['high'].tail(lookback).max()
        recent_low = df['low'].tail(lookback).min()
        current_price = df['close'].iloc[-1]
        
        resistance_level = recent_high
        support_level = recent_low
        
        # 动态支撑阻力（基于布林带）
        bb_upper = df['bb_upper'].iloc[-1]
        bb_lower = df['bb_lower'].iloc[-1]
        
        return {
            'static_resistance': resistance_level,
            'static_support': support_level,
            'dynamic_resistance': bb_upper,
            'dynamic_support': bb_lower,
            'price_vs_resistance': ((resistance_level - current_price) / current_price) * 100,
            'price_vs_support': ((current_price - support_level) / support_level) * 100
        }
    except Exception as e:
        print(f"[失败] 支撑阻力计算失败: {e}")
        return {}


def format_market_data(df: pd.DataFrame) -> Dict:
    """
    格式化市场数据为标准字典
    
    Args:
        df: 包含技术指标的DataFrame
    
    Returns:
        格式化的市场数据字典
    """
    try:
        current_data = df.iloc[-1]
        previous_data = df.iloc[-2]
        # 动态获取可用的数据量（最多10根）
        available_rows = min(len(df), 10)
        recent_10 = df.tail(available_rows)
        
        # 获取趋势和支撑阻力
        trend_analysis = get_market_trend(df)
        levels_analysis = get_support_resistance_levels(df)
        
        return {
            'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
            'price': current_data['close'],
            'open': current_data['open'],
            'high': current_data['high'],
            'low': current_data['low'],
            'volume': current_data['volume'],
            'price_change': ((current_data['close'] - previous_data['close']) / previous_data['close']) * 100,
            
            'technical_data': {
                'sma_5': current_data.get('sma_5', 0),
                'sma_20': current_data.get('sma_20', 0),
                'sma_50': current_data.get('sma_50', 0),
                'rsi': current_data.get('rsi', 0),
                'macd': current_data.get('macd', 0),
                'macd_signal': current_data.get('macd_signal', 0),
                'macd_histogram': current_data.get('macd_histogram', 0),
                'bb_upper': current_data.get('bb_upper', 0),
                'bb_lower': current_data.get('bb_lower', 0),
                'bb_position': current_data.get('bb_position', 0),
                'atr_14': current_data.get('atr_14', 0),
                'volume_ratio': current_data.get('volume_ratio', 0),
            },
            
            'trend_analysis': trend_analysis,
            'levels_analysis': levels_analysis,
            
            'time_series': {
                'open_prices': recent_10['open'].round(2).tolist(),
                'high_prices': recent_10['high'].round(2).tolist(),
                'low_prices': recent_10['low'].round(2).tolist(),
                'close_prices': recent_10['close'].round(2).tolist(),
                'rsi': recent_10['rsi'].round(2).tolist(),
                'macd': recent_10['macd'].round(3).tolist(),
                # 成交额格式化为M/K单位，更易读
                'volume': [f"{v/1e6:.2f}M" if v >= 1e6 else f"{v/1e3:.2f}K" if v >= 1e3 else f"{v:.2f}" for v in recent_10['volume'].tolist()],
            }
        }
    except Exception as e:
        print(f"[失败] 数据格式化失败: {e}")
        return {}


if __name__ == "__main__":
    # 测试代码
    print("=== 测试技术指标计算 ===\n")
    
    # 创建模拟数据
    dates = pd.date_range('2025-01-01', periods=100, freq='5min')
    np.random.seed(42)
    
    # 生成模拟价格数据（随机游走）
    price = 67000
    prices = [price]
    for _ in range(99):
        price += np.random.randn() * 100
        prices.append(price)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p + np.random.rand() * 50 for p in prices],
        'low': [p - np.random.rand() * 50 for p in prices],
        'close': prices,
        'volume': np.random.rand(100) * 1000
    })
    
    # 计算指标
    df = calculate_technical_indicators(df)
    
    print("技术指标计算完成！")
    print(f"\n最新数据:")
    print(f"价格: ${df['close'].iloc[-1]:,.2f}")
    print(f"RSI: {df['rsi'].iloc[-1]:.2f}")
    print(f"MACD: {df['macd'].iloc[-1]:.4f}")
    print(f"布林带位置: {df['bb_position'].iloc[-1]:.2%}")
    
    # 测试趋势分析
    trend = get_market_trend(df)
    print(f"\n趋势分析: {trend}")
    
    # 测试格式化
    market_data = format_market_data(df)
    print(f"\n格式化数据: 包含{len(market_data)}个字段")
