"""
数据格式化模块 - 将市场数据格式化为AI可理解的格式
"""
from typing import Dict, List, Optional
from datetime import datetime


class MarketDataFormatter:
    """市场数据格式化器"""
    
    @staticmethod
    def format_comprehensive_market_data(
        account_info: Dict,
        btc_data: Dict,
        eth_data: Optional[Dict] = None,
        sol_data: Optional[Dict] = None,
        other_coins: Optional[List[Dict]] = None,
        positions: Optional[List[Dict]] = None,
        trading_stats: Optional[Dict] = None
    ) -> str:
        """
        格式化综合市场数据
        
        Args:
            account_info: 账户信息
            btc_data: BTC数据
            eth_data: ETH数据（可选）
            sol_data: SOL数据（可选）
            other_coins: 其他币种数据（可选）
            positions: 当前持仓（可选）
            trading_stats: 交易统计（可选）
        
        Returns:
            格式化的文本
        """
        sections = []
        
        # 1. 时间和调用信息
        sections.append(MarketDataFormatter._format_header(trading_stats))
        
        # 2. 账户信息
        sections.append(MarketDataFormatter._format_account_info(account_info))
        
        # 3. BTC数据（主要币种）
        sections.append(MarketDataFormatter._format_coin_data("BTC", btc_data))
        
        # 4. 其他币种数据
        if eth_data:
            sections.append(MarketDataFormatter._format_coin_data("ETH", eth_data))
        if sol_data:
            sections.append(MarketDataFormatter._format_coin_data("SOL", sol_data))
        if other_coins:
            for coin_data in other_coins:
                sections.append(MarketDataFormatter._format_coin_data(
                    coin_data['symbol'], 
                    coin_data
                ))
        
        # 5. 当前持仓
        if positions:
            sections.append(MarketDataFormatter._format_positions(positions))
        
        return "\n\n".join(sections)
    
    @staticmethod
    def _format_header(stats: Optional[Dict] = None) -> str:
        """格式化头部信息"""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if stats:
            minutes_elapsed = stats.get('minutes_elapsed', 0)
            call_count = stats.get('call_count', 0)
            return f"""【交易会话信息】
当前时间: {current_time}
交易时长: {minutes_elapsed} 分钟
AI调用次数: {call_count} 次

[警告] 重要说明：
- 所有价格和信号数据按时间顺序排列：最旧 → 最新
- 时间框架：日内数据以3分钟为间隔（除非特别说明）
"""
        else:
            return f"""【市场分析】
分析时间: {current_time}
"""
    
    @staticmethod
    def _format_account_info(account: Dict) -> str:
        """格式化账户信息"""
        return f"""【账户信息与表现】
💰 总回报率: {account.get('total_return_pct', 0):.2f}%
💵 可用现金: ${account.get('available_cash', 0):,.2f}
[数据] 账户总价值: ${account.get('total_value', 0):,.2f}
📈 夏普比率: {account.get('sharpe_ratio', 0):.3f}
"""
    
    @staticmethod
    def _format_coin_data(symbol: str, data: Dict) -> str:
        """格式化单个币种数据"""
        # 当前价格和指标
        current = data.get('current', {})
        
        # 日内序列
        intraday = data.get('intraday', {})
        
        # 长期背景
        longterm = data.get('longterm', {})
        
        # 未平仓合约和融资利率
        oi = data.get('open_interest', {})
        funding = data.get('funding_rate', 0)
        
        text = f"""【{symbol} 市场数据】

[数据] 当前状态:
- 价格: ${current.get('price', 0):,.4f}
- EMA20: ${current.get('ema20', 0):,.4f}
- MACD: {current.get('macd', 0):.4f}
- RSI(7): {current.get('rsi_7', 0):.2f}
- RSI(14): {current.get('rsi_14', 0):.2f}

📈 未平仓合约与融资:
- 未平仓合约: 最新 {oi.get('latest', 0):,.2f} | 平均 {oi.get('average', 0):,.2f}
- 融资利率: {funding:.6f}

📉 日内序列（3分钟，最早→最新）:
"""
        
        # 添加时间序列数据
        if intraday:
            if 'prices' in intraday:
                prices_str = ', '.join([f"{p:.2f}" for p in intraday['prices'][-10:]])
                text += f"- 价格: [{prices_str}]\n"
            
            if 'ema20' in intraday:
                ema_str = ', '.join([f"{e:.2f}" for e in intraday['ema20'][-10:]])
                text += f"- EMA20: [{ema_str}]\n"
            
            if 'macd' in intraday:
                macd_str = ', '.join([f"{m:.3f}" for m in intraday['macd'][-10:]])
                text += f"- MACD: [{macd_str}]\n"
            
            if 'rsi_7' in intraday:
                rsi7_str = ', '.join([f"{r:.2f}" for r in intraday['rsi_7'][-10:]])
                text += f"- RSI(7): [{rsi7_str}]\n"
            
            if 'rsi_14' in intraday:
                rsi14_str = ', '.join([f"{r:.2f}" for r in intraday['rsi_14'][-10:]])
                text += f"- RSI(14): [{rsi14_str}]\n"
        
        # 长期背景
        if longterm:
            text += f"""
🔭 长期背景（4小时时间框架）:
- EMA20: {longterm.get('ema20', 0):.2f} vs EMA50: {longterm.get('ema50', 0):.2f}
- ATR(3): {longterm.get('atr_3', 0):.3f} vs ATR(14): {longterm.get('atr_14', 0):.3f}
- 当前成交量: {longterm.get('current_volume', 0):,.2f} vs 平均: {longterm.get('avg_volume', 0):,.2f}
"""
            
            if 'macd_series' in longterm:
                macd_str = ', '.join([f"{m:.3f}" for m in longterm['macd_series'][-10:]])
                text += f"- MACD序列: [{macd_str}]\n"
            
            if 'rsi_series' in longterm:
                rsi_str = ', '.join([f"{r:.2f}" for r in longterm['rsi_series'][-10:]])
                text += f"- RSI序列: [{rsi_str}]\n"
        
        return text
    
    @staticmethod
    def _format_positions(positions: List[Dict]) -> str:
        """格式化持仓信息"""
        if not positions:
            return "【当前持仓】\n无持仓"
        
        text = "【当前持仓与表现】\n\n"
        
        for i, pos in enumerate(positions, 1):
            pnl_emoji = "📈" if pos.get('unrealized_pnl', 0) > 0 else "📉"
            
            text += f"""{i}. {pos.get('symbol', 'N/A')} {pnl_emoji}
   - 数量: {pos.get('quantity', 0)}
   - 开仓价: ${pos.get('entry_price', 0):,.4f}
   - 当前价: ${pos.get('current_price', 0):,.4f}
   - 未实现盈亏: ${pos.get('unrealized_pnl', 0):,.2f}
   - 杠杆: {pos.get('leverage', 1)}x
   - 名义价值: ${pos.get('notional_usd', 0):,.2f}
   - 清算价: ${pos.get('liquidation_price', 0):,.4f}
   - 止盈目标: ${pos.get('exit_plan', {}).get('profit_target', 0):,.4f}
   - 止损价: ${pos.get('exit_plan', {}).get('stop_loss', 0):,.4f}
   - 失效条件: {pos.get('exit_plan', {}).get('invalidation_condition', 'N/A')}
   - 信心度: {pos.get('confidence', 0):.0%}
   - 风险金额: ${pos.get('risk_usd', 0):,.2f}

"""
        
        return text.strip()
    
    @staticmethod
    def create_analysis_prompt(formatted_data: str, question: str = None) -> str:
        """
        创建分析提示
        
        Args:
            formatted_data: 格式化的市场数据
            question: 具体问题（可选）
        
        Returns:
            完整的提示文本
        """
        base_prompt = f"""{formatted_data}

【分析任务】
请基于以上市场数据，进行全面分析并回答以下问题：
"""
        
        if question:
            base_prompt += f"\n{question}\n"
        else:
            base_prompt += """
1. 当前市场整体趋势如何？各币种之间是否有相关性？
2. 现有持仓的风险如何？是否需要调整？
3. 是否有新的交易机会？如果有，请给出具体建议（币种、方向、入场价、止损、止盈）
4. 基于技术指标和市场结构，未来1-4小时的市场预测？

请给出清晰、可执行的建议。
"""
        
        return base_prompt


# 示例使用
if __name__ == "__main__":
    # 模拟数据
    account_info = {
        'total_return_pct': 116.86,
        'available_cash': 13654.1,
        'total_value': 21686.45,
        'sharpe_ratio': 0.469
    }
    
    btc_data = {
        'current': {
            'price': 114283.5,
            'ema20': 114144.951,
            'macd': 88.79,
            'rsi_7': 65.889,
            'rsi_14': 61.234
        },
        'intraday': {
            'prices': [114245.0, 114248.5, 114199.5, 114255.0, 114187.5, 114144.5, 114132.5, 114149.0, 114255.0, 114283.5],
            'ema20': [114059.596, 114077.635, 114089.288, 114105.166, 114106.864, 114109.925, 114112.218, 114116.768, 114130.314, 114144.951],
            'macd': [127.879, 128.286, 123.233, 122.338, 109.632, 99.705, 90.392, 84.139, 86.179, 88.79],
            'rsi_7': [65.123, 65.123, 57.174, 63.168, 45.516, 47.572, 46.926, 50.964, 63.35, 65.889],
            'rsi_14': [62.09, 62.09, 58.434, 61.243, 52.217, 53.113, 52.78, 54.38, 59.948, 61.234]
        },
        'longterm': {
            'ema20': 113270.82,
            'ema50': 111844.96,
            'atr_3': 392.748,
            'atr_14': 563.173,
            'current_volume': 29.931,
            'avg_volume': 4682.793,
            'macd_series': [889.972, 961.709, 1082.258, 1206.811, 1325.662, 1391.865, 1399.553, 1374.151, 1277.883, 1172.022],
            'rsi_series': [69.947, 68.424, 72.327, 74.258, 75.761, 74.188, 70.412, 68.365, 60.885, 59.065]
        },
        'open_interest': {
            'latest': 29952.18,
            'average': 29944.57
        },
        'funding_rate': 0.0000125
    }
    
    positions = [
        {
            'symbol': 'BTC',
            'quantity': 0.12,
            'entry_price': 107343.0,
            'current_price': 114283.5,
            'unrealized_pnl': 832.86,
            'leverage': 10,
            'notional_usd': 13714.02,
            'liquidation_price': 98128.63,
            'exit_plan': {
                'profit_target': 118136.15,
                'stop_loss': 102026.675,
                'invalidation_condition': '如果价格在3分钟蜡烛上收于105000以下'
            },
            'confidence': 0.75,
            'risk_usd': 619.23
        }
    ]
    
    trading_stats = {
        'minutes_elapsed': 8319,
        'call_count': 3274
    }
    
    # 格式化数据
    formatter = MarketDataFormatter()
    formatted = formatter.format_comprehensive_market_data(
        account_info=account_info,
        btc_data=btc_data,
        positions=positions,
        trading_stats=trading_stats
    )
    
    # 创建分析提示
    prompt = formatter.create_analysis_prompt(formatted)
    
    print(prompt)
    print("\n" + "="*70)
    print(f"提示长度: {len(prompt)} 字符")
