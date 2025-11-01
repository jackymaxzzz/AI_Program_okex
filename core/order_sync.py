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
        """从API同步最近的成交订单到数据库"""
        try:
            # 获取最近7天的成交订单
            synced_count = 0
            
            # 获取所有交易对的历史订单
            symbols = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT', 
                      'BNB/USDT:USDT', 'DOGE/USDT:USDT', 'XRP/USDT:USDT']
            
            for symbol in symbols:
                try:
                    # 获取该币种的历史订单
                    orders = self.data_fetcher.exchange.fetch_my_trades(
                        symbol=symbol,
                        since=int((datetime.now() - timedelta(days=7)).timestamp() * 1000)
                    )
                    
                    if not orders:
                        continue
                    
                    # 按时间排序
                    orders.sort(key=lambda x: x.get('timestamp', 0))
                    
                    # 获取数据库中所有未平仓的交易
                    open_trades = self.trade_db.get_open_trades()
                    
                    # 处理每个订单
                    for order in orders:
                        order_side = order.get('side')  # 'buy' or 'sell'
                        order_price = order.get('price', 0)
                        order_amount = order.get('amount', 0)
                        order_time = datetime.fromtimestamp(order.get('timestamp', 0) / 1000)
                        
                        # 查找匹配的数据库交易
                        for db_trade in open_trades:
                            if db_trade.get('symbol') != symbol:
                                continue
                            
                            db_side = db_trade.get('side')  # 'long' or 'short'
                            entry_price = db_trade.get('entry_price', 0)
                            entry_time_str = db_trade.get('entry_time', '')
                            if not entry_time_str:
                                continue  # 跳过没有entry_time的记录
                            entry_time = datetime.fromisoformat(entry_time_str)
                            
                            # 判断是否为平仓订单
                            is_close_order = (
                                (db_side == 'long' and order_side == 'sell') or
                                (db_side == 'short' and order_side == 'buy')
                            )
                            
                            if is_close_order and order_time > entry_time:
                                # 这是一个平仓订单
                                api_price = order_price
                                
                                # 计算实际盈亏
                                if db_side == 'long':
                                    realized_pnl = (api_price - entry_price) * order_amount
                                else:
                                    realized_pnl = (entry_price - api_price) * order_amount
                                
                                # 更新数据库
                                import sqlite3
                                conn = sqlite3.connect(self.trade_db.db_path)
                                cursor = conn.cursor()
                                
                                cursor.execute("""
                                    UPDATE trades 
                                    SET status = 'closed',
                                        exit_price = ?,
                                        exit_time = ?,
                                        realized_pnl = ?
                                    WHERE id = ?
                                """, (api_price, order_time.isoformat(), realized_pnl, db_trade['id']))
                                
                                conn.commit()
                                conn.close()
                                
                                print(f"  [完成] 同步成功 ID#{db_trade['id']}: 开仓${entry_price:,.2f} → 平仓${api_price:,.2f} 盈亏${realized_pnl:+,.2f}")
                                synced_count += 1
                                break
                
                except Exception as e:
                    # 单个币种失败不影响其他币种
                    print(f"  [警告] {symbol} 同步失败: {e}")
            
            if synced_count > 0:
                print(f"[完成] 同步完成，更新了{synced_count}笔交易\n")
                    
        except Exception as e:
            # 同步失败不影响主流程
            print(f"[警告] API同步失败: {e}\n")
    
    def get_recent_filled_orders(self, symbol: str, days: int = 7) -> List[Dict]:
        """
        获取最近N天的成交订单
        
        Args:
            symbol: 交易对符号
            days: 天数
            
        Returns:
            订单列表
        """
        try:
            since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
            orders = self.data_fetcher.exchange.fetch_my_trades(symbol=symbol, since=since)
            return orders if orders else []
        except Exception as e:
            print(f"[警告] 获取成交订单失败: {e}")
            return []
    
    def match_orders_to_trades(self, orders: List[Dict], trades: List[Dict]) -> Dict:
        """
        匹配订单和交易记录
        
        Args:
            orders: API订单列表
            trades: 数据库交易列表
            
        Returns:
            匹配结果
        """
        matched = []
        unmatched_orders = []
        unmatched_trades = []
        
        for order in orders:
            found = False
            for trade in trades:
                if self._is_matching_order(order, trade):
                    matched.append({
                        'order': order,
                        'trade': trade
                    })
                    found = True
                    break
            
            if not found:
                unmatched_orders.append(order)
        
        # 找出未匹配的交易
        matched_trade_ids = {m['trade']['id'] for m in matched}
        unmatched_trades = [t for t in trades if t['id'] not in matched_trade_ids]
        
        return {
            'matched': matched,
            'unmatched_orders': unmatched_orders,
            'unmatched_trades': unmatched_trades
        }
    
    def _is_matching_order(self, order: Dict, trade: Dict) -> bool:
        """
        判断订单是否匹配交易记录
        
        Args:
            order: API订单
            trade: 数据库交易
            
        Returns:
            是否匹配
        """
        # 检查币种
        if order.get('symbol') != trade.get('symbol'):
            return False
        
        # 检查时间（订单时间应该在交易开仓时间之后）
        order_time = datetime.fromtimestamp(order.get('timestamp', 0) / 1000)
        entry_time_str = trade.get('entry_time', '')
        if not entry_time_str:
            return False  # 没有entry_time，无法判断
        
        entry_time = datetime.fromisoformat(entry_time_str)
        if order_time <= entry_time:
            return False
        
        # 检查方向（平仓订单应该与持仓方向相反）
        order_side = order.get('side')
        trade_side = trade.get('side')
        
        is_close_order = (
            (trade_side == 'long' and order_side == 'sell') or
            (trade_side == 'short' and order_side == 'buy')
        )
        
        return is_close_order
