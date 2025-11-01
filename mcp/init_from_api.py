"""
从OKX API初始化MCP记忆系统
"""
from datetime import datetime, timedelta
from typing import Dict, List
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import TRADING_CONFIG


def init_mcp_from_okx_trades(mcp_memory, data_fetcher, days: int = 30):
    """
    从OKX历史成交记录初始化MCP
    
    Args:
        mcp_memory: MCP记忆对象
        data_fetcher: 数据获取器
        days: 获取最近多少天的数据
    """
    try:
        print(f"\n[MCP初始化] 开始从OKX API获取最近{days}天的历史交易...")
        
        # 从配置文件获取交易对
        symbols = TRADING_CONFIG['symbols']
        
        total_trades = 0
        successful_count = 0
        failed_count = 0
        
        for symbol in symbols:
            try:
                # 获取历史成交
                since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
                trades = data_fetcher.exchange.fetch_my_trades(
                    symbol=symbol,
                    since=since,
                    limit=100
                )
                
                if not trades:
                    continue
                
                # 按时间排序
                trades.sort(key=lambda x: x.get('timestamp', 0))
                
                # 分析交易对（开仓-平仓）
                open_trades = {}  # {side: trade_info}
                
                for trade in trades:
                    info = trade.get('info', {})
                    fill_pnl = float(info.get('fillPnl', '0'))
                    side = trade.get('side')  # buy/sell
                    pos_side = info.get('posSide', 'long')  # long/short
                    price = trade.get('price', 0)
                    amount = trade.get('amount', 0)
                    timestamp = trade.get('timestamp', 0)
                    
                    # 开仓交易（fillPnl为0）
                    if fill_pnl == 0:
                        open_trades[pos_side] = {
                            'entry_price': price,
                            'amount': amount,
                            'timestamp': timestamp,
                            'side': pos_side
                        }
                    # 平仓交易（fillPnl不为0）
                    elif fill_pnl != 0 and pos_side in open_trades:
                        entry_info = open_trades[pos_side]
                        entry_price = entry_info['entry_price']
                        
                        # 计算盈亏百分比
                        if pos_side == 'long':
                            pnl_percent = ((price - entry_price) / entry_price) * 100
                        else:  # short
                            pnl_percent = ((entry_price - price) / entry_price) * 100
                        
                        # 计算持仓时长
                        holding_seconds = (timestamp - entry_info['timestamp']) / 1000
                        if holding_seconds < 3600:
                            holding_duration = f"{holding_seconds/60:.0f}分钟"
                        elif holding_seconds < 86400:
                            holding_duration = f"{holding_seconds/3600:.1f}小时"
                        else:
                            holding_duration = f"{holding_seconds/86400:.1f}天"
                        
                        # 构建详细的交易信息
                        trade_info = {
                            'symbol': symbol.split('/')[0],
                            'side': pos_side,
                            'entry_price': entry_price,
                            'exit_price': price,
                            'amount': entry_info['amount'],
                            'pnl_percent': pnl_percent,
                            'realized_pnl': fill_pnl,
                            'entry_time': datetime.fromtimestamp(entry_info['timestamp'] / 1000).isoformat(),
                            'exit_time': datetime.fromtimestamp(timestamp / 1000).isoformat(),
                            'holding_duration': holding_duration,
                            'holding_seconds': holding_seconds,
                            'strategy': 'historical',
                            'reason': f"历史交易：{'做多' if pos_side == 'long' else '做空'} {symbol.split('/')[0]}，持仓{holding_duration}，{'盈利' if pnl_percent > 0 else '亏损'}{abs(pnl_percent):.2f}%",
                            'observation': f"{'✅ 成功' if pnl_percent > 0 else '❌ 失败'}: {symbol.split('/')[0]} {pos_side} 入场${entry_price:.2f} 出场${price:.2f} 持仓{holding_duration} {'盈利' if pnl_percent > 0 else '亏损'}{abs(pnl_percent):.2f}% (${fill_pnl:.2f})"
                        }
                        
                        # 记录到MCP
                        if pnl_percent > 0:
                            mcp_memory.record_successful_trade(trade_info)
                            successful_count += 1
                            print(f"  ✅ {trade_info['observation']}")
                        else:
                            mcp_memory.record_failed_trade(trade_info)
                            failed_count += 1
                            print(f"  ❌ {trade_info['observation']}")
                        
                        total_trades += 1
                        
                        # 清除已配对的开仓记录
                        del open_trades[pos_side]
                
            except Exception as e:
                print(f"[警告] {symbol} 历史数据获取失败: {e}")
                continue
        
        print(f"[MCP初始化] 完成！")
        print(f"  总交易: {total_trades}笔")
        print(f"  成功: {successful_count}笔")
        print(f"  失败: {failed_count}笔")
        
        if total_trades > 0:
            win_rate = (successful_count / total_trades) * 100
            print(f"  历史胜率: {win_rate:.1f}%")
        
        return total_trades
        
    except Exception as e:
        print(f"[失败] MCP初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return 0
