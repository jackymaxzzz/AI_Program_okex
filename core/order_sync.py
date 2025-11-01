"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

订单同步模块 - 负责从API同步历史成交订单
"""
from typing import Dict, List
from datetime import datetime, timedelta


class OrderSync:
    """订单同步器 - 从API同步历史成交到数据库"""
    
    def __init__(self, data_fetcher, trade_db):
        """
        初始化订单同步器
        
        Args:
            data_fetcher: 数据获取器
            trade_db: 交易数据库
        """
        self.data_fetcher = data_fetcher
        self.trade_db = trade_db
    
    def sync_filled_orders_from_api(self):
        """
        从OKX API同步已平仓的历史订单到数据库
        
        流程：
        1. 从OKX API获取历史成交记录
        2. 只处理平仓订单（fillPnl != '0'）
        3. 写入数据库（避免重复）
        4. 返回同步数量
        """
        try:
            import sqlite3
            import json
            synced_count = 0
            
            # 获取所有交易对的历史订单
            symbols = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT', 
                      'BNB/USDT:USDT', 'DOGE/USDT:USDT', 'XRP/USDT:USDT']
            
            print(f"[同步] 开始从OKX API同步历史订单...")
            
            for symbol in symbols:
                try:
                    # 获取该币种最近7天的历史订单
                    orders = self.data_fetcher.exchange.fetch_my_trades(
                        symbol=symbol,
                        since=int((datetime.now() - timedelta(days=7)).timestamp() * 1000)
                    )
                    
                    if not orders:
                        continue
                    
                    # 只处理平仓订单（fillPnl != '0'）
                    close_orders = [o for o in orders if o.get('info', {}).get('fillPnl', '0') != '0']
                    
                    if not close_orders:
                        continue
                    
                    print(f"  {symbol}: 找到{len(close_orders)}笔平仓订单")
                    
                    # 处理每笔平仓订单
                    for order in close_orders:
                        try:
                            # 从OKX info中获取详细信息
                            info = order.get('info', {})
                            fill_pnl = float(info.get('fillPnl', 0))
                            order_id = info.get('ordId', '')
                            
                            # 检查是否已存在（避免重复）
                            conn = sqlite3.connect(self.trade_db.db_path)
                            cursor = conn.cursor()
                            cursor.execute('SELECT id FROM trades WHERE exit_order_id = ?', (order_id,))
                            existing = cursor.fetchone()
                            
                            if existing:
                                conn.close()
                                continue  # 已存在，跳过
                            
                            # 构建交易记录
                            side = 'long' if info.get('posSide') == 'long' else 'short'
                            signal = 'BUY' if side == 'long' else 'SELL'
                            price = float(order.get('price', 0))
                            quantity = float(order.get('amount', 0))
                            order_time = datetime.fromtimestamp(order.get('timestamp', 0) / 1000)
                            
                            # 计算盈亏百分比（使用杠杆10倍）
                            pnl_percent = (fill_pnl / (price * quantity)) * 100 * 10
                            
                            # 插入数据库（作为已完成的交易）
                            cursor.execute('''
                            INSERT INTO trades (
                                symbol, signal, side, entry_price, exit_price, quantity, leverage,
                                open_time, close_time, realized_pnl, pnl_percent,
                                exit_order_id, status, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                symbol, signal, side, price, price, quantity, 10,
                                order_time.isoformat(), order_time.isoformat(),
                                fill_pnl, pnl_percent, order_id, 'CLOSED',
                                order_time.isoformat(), order_time.isoformat()
                            ))
                            
                            conn.commit()
                            conn.close()
                            synced_count += 1
                            
                        except Exception as e:
                            print(f"    [警告] 处理订单失败: {e}")
                            continue
                    
                except Exception as e:
                    print(f"  [警告] {symbol} 同步失败: {e}")
                    continue
            
            if synced_count > 0:
                print(f"[同步] 完成！共同步{synced_count}笔历史交易")
            else:
                print(f"[同步] 没有新的历史交易需要同步")
            
            return synced_count
            
        except Exception as e:
            print(f"[失败] 同步失败: {e}")
            return 0
    
