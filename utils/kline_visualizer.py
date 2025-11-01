"""
K线可视化模块 - 将K线数据转换为ASCII图表，让AI直观理解
"""
from typing import List, Dict


def visualize_klines(klines: List[Dict], width: int = 50) -> str:
    """
    将K线数据转换为ASCII可视化图表
    
    Args:
        klines: K线数据列表，每个元素包含 open, high, low, close
        width: 图表宽度
        
    Returns:
        ASCII图表字符串
    """
    if not klines or len(klines) == 0:
        return "无K线数据"
    
    # 获取价格范围
    all_prices = []
    for k in klines:
        all_prices.extend([k.get('high', 0), k.get('low', 0)])
    
    if not all_prices or max(all_prices) == 0:
        return "价格数据无效"
    
    max_price = max(all_prices)
    min_price = min(all_prices)
    price_range = max_price - min_price
    
    if price_range == 0:
        return "价格无变化"
    
    # 构建图表
    height = 15  # 图表高度
    chart = []
    
    # 创建空白画布
    for _ in range(height):
        chart.append([' '] * width)
    
    # 绘制每根K线
    kline_width = width // len(klines)
    
    for i, kline in enumerate(klines):
        open_price = kline.get('open', 0)
        close_price = kline.get('close', 0)
        high_price = kline.get('high', 0)
        low_price = kline.get('low', 0)
        
        if not all([open_price, close_price, high_price, low_price]):
            continue
        
        # 计算位置
        x = i * kline_width + kline_width // 2
        if x >= width:
            x = width - 1
        
        # 转换价格到Y坐标（倒置，因为高价在上）
        def price_to_y(price):
            normalized = (price - min_price) / price_range
            y = int((1 - normalized) * (height - 1))
            return max(0, min(height - 1, y))
        
        open_y = price_to_y(open_price)
        close_y = price_to_y(close_price)
        high_y = price_to_y(high_price)
        low_y = price_to_y(low_price)
        
        # 判断阴阳线
        is_bullish = close_price >= open_price
        body_char = '█' if is_bullish else '▓'
        wick_char = '│'
        
        # 绘制上影线
        for y in range(high_y, min(open_y, close_y)):
            if 0 <= y < height and 0 <= x < width:
                chart[y][x] = wick_char
        
        # 绘制实体
        body_top = min(open_y, close_y)
        body_bottom = max(open_y, close_y)
        for y in range(body_top, body_bottom + 1):
            if 0 <= y < height and 0 <= x < width:
                chart[y][x] = body_char
        
        # 绘制下影线
        for y in range(max(open_y, close_y) + 1, low_y + 1):
            if 0 <= y < height and 0 <= x < width:
                chart[y][x] = wick_char
    
    # 转换为字符串
    result = []
    result.append("┌" + "─" * width + "┐")
    
    # 添加价格标签
    for i, row in enumerate(chart):
        # 计算当前行对应的价格
        price_at_row = max_price - (i / (height - 1)) * price_range
        price_label = f"{price_at_row:>8.2f}"
        
        # 每隔几行显示一次价格
        if i % 3 == 0:
            result.append(f"{price_label}│{''.join(row)}│")
        else:
            result.append(f"        │{''.join(row)}│")
    
    result.append("        └" + "─" * width + "┘")
    
    return '\n'.join(result)


def format_kline_pattern(klines: List[Dict], count: int = 7) -> str:
    """
    格式化K线形态描述
    
    Args:
        klines: K线数据列表
        count: 显示最近几根K线
        
    Returns:
        K线形态描述
    """
    if not klines or len(klines) == 0:
        return "无K线数据"
    
    # 取最近N根
    recent = klines[-count:] if len(klines) >= count else klines
    
    patterns = []
    for i, k in enumerate(recent):
        open_price = k.get('open', 0)
        close_price = k.get('close', 0)
        high_price = k.get('high', 0)
        low_price = k.get('low', 0)
        
        if not all([open_price, close_price, high_price, low_price]):
            patterns.append("?")
            continue
        
        # 判断阴阳
        is_bullish = close_price >= open_price
        candle_type = "阳" if is_bullish else "阴"
        
        # 计算实体大小
        body_size = abs(close_price - open_price)
        total_range = high_price - low_price
        body_ratio = (body_size / total_range * 100) if total_range > 0 else 0
        
        # 判断K线类型
        if body_ratio < 10:
            candle_desc = f"十字星"
        elif body_ratio < 30:
            candle_desc = f"小{candle_type}"
        elif body_ratio < 70:
            candle_desc = f"中{candle_type}"
        else:
            candle_desc = f"大{candle_type}"
        
        # 判断上下影线
        if is_bullish:
            upper_wick = high_price - close_price
            lower_wick = open_price - low_price
        else:
            upper_wick = high_price - open_price
            lower_wick = close_price - low_price
        
        upper_ratio = (upper_wick / total_range * 100) if total_range > 0 else 0
        lower_ratio = (lower_wick / total_range * 100) if total_range > 0 else 0
        
        if upper_ratio > 40:
            candle_desc += "长上影"
        if lower_ratio > 40:
            candle_desc += "长下影"
        
        patterns.append(candle_desc)
    
    return " → ".join(patterns)


def analyze_trend(klines: List[Dict]) -> str:
    """
    分析K线趋势
    
    Args:
        klines: K线数据列表
        
    Returns:
        趋势描述
    """
    if not klines or len(klines) < 3:
        return "数据不足"
    
    # 取最近的收盘价
    closes = [k.get('close', 0) for k in klines[-7:]]
    
    if len(closes) < 3:
        return "数据不足"
    
    # 计算趋势
    ups = 0
    downs = 0
    
    for i in range(1, len(closes)):
        if closes[i] > closes[i-1]:
            ups += 1
        elif closes[i] < closes[i-1]:
            downs += 1
    
    total = ups + downs
    if total == 0:
        return "横盘"
    
    up_ratio = ups / total
    
    if up_ratio >= 0.7:
        return "强势上涨"
    elif up_ratio >= 0.6:
        return "温和上涨"
    elif up_ratio >= 0.4:
        return "震荡整理"
    elif up_ratio >= 0.3:
        return "温和下跌"
    else:
        return "强势下跌"


# 测试代码
if __name__ == "__main__":
    # 模拟K线数据
    test_klines = [
        {'open': 100, 'high': 105, 'low': 98, 'close': 103},
        {'open': 103, 'high': 108, 'low': 102, 'close': 107},
        {'open': 107, 'high': 110, 'low': 105, 'close': 106},
        {'open': 106, 'high': 109, 'low': 103, 'close': 104},
        {'open': 104, 'high': 106, 'low': 100, 'close': 101},
        {'open': 101, 'high': 103, 'low': 97, 'close': 98},
        {'open': 98, 'high': 100, 'low': 95, 'close': 96},
    ]
    
    print("K线可视化:")
    print(visualize_klines(test_klines))
    print("\nK线形态:")
    print(format_kline_pattern(test_klines))
    print("\n趋势分析:")
    print(analyze_trend(test_klines))
