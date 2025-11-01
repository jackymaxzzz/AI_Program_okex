"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

持仓管理模块 - 负责持仓同步和管理
"""
from typing import Dict, Optional, List
from datetime import datetime


class PositionManager:
    """持仓管理器 - 处理持仓同步、验证等操作"""
    
    def __init__(self, data_fetcher, trade_db):
        """
        初始化持仓管理器
        
        Args:
            data_fetcher: 数据获取器
            trade_db: 交易数据库
        """
        self.data_fetcher = data_fetcher
        self.trade_db = trade_db
    
    def get_position_trade_mode(self, symbol: str) -> str:
        """
        获取持仓的交易模式（逐仓或全仓）
        
        Args:
            symbol: 交易对符号
            
        Returns:
            'isolated' 或 'cross'
        """
        try:
            # 从API获取持仓信息
            positions = self.data_fetcher.get_all_positions()
            if positions:
                for pos in positions:
                    if pos.get('symbol') == symbol:
                        margin_mode = pos.get('marginMode', 'cross')
                        return 'isolated' if margin_mode == 'isolated' else 'cross'
        except Exception as e:
            print(f"[警告] 获取持仓交易模式失败: {e}")
        
        # 默认返回全仓模式
        return 'cross'
    
    def sync_database_with_positions(self, current_position: Optional[Dict]):
        """
        同步数据库与实际持仓
        关闭所有在数据库中标记为open但实际已平仓的交易
        
        Args:
            current_position: 当前持仓信息
        """
        try:
            # 获取数据库中所有未平仓的交易
            open_trades = self.trade_db.get_open_trades()
            
            if not open_trades:
                return
            
            # 如果没有实际持仓，关闭所有数据库中的open交易
            if not current_position:
                for trade in open_trades:
                    # 获取当前价格作为平仓价
                    symbol_coin = trade.get('symbol', '').replace('/USDT:USDT', '')
                    try:
                        current_price_data = self.data_fetcher.get_current_price(symbol_coin)
                        exit_price = current_price_data.get('price', trade.get('entry_price', 0))
                        
                        # 计算盈亏
                        entry_price = trade.get('entry_price', exit_price)
                        side = trade.get('side', 'long')
                        amount = trade.get('amount', 0)
                        
                        if side == 'long':
                            realized_pnl = (exit_price - entry_price) * amount
                        else:
                            realized_pnl = (entry_price - exit_price) * amount
                        
                        print(f"[同步] 关闭交易 #{trade['id']} ({trade['symbol']}) - 平仓价${exit_price:,.2f}")
                    except Exception as e:
                        print(f"[警告] 获取平仓价失败: {e}")
                        exit_price = trade.get('entry_price', 0)
                        realized_pnl = 0
                    
                    self.trade_db.close_trade(
                        trade_id=trade['id'],
                        exit_price=exit_price,
                        realized_pnl=realized_pnl,
                        ai_decision={'reason': '系统同步：实际无持仓'}
                    )
                return
            
            # 如果有持仓，检查币种是否匹配
            current_symbol = current_position.get('symbol')
            
            for trade in open_trades:
                trade_symbol = trade.get('symbol')
                
                # 如果数据库中的交易币种与当前持仓不匹配，关闭该交易
                if trade_symbol != current_symbol:
                    symbol_coin = trade_symbol.replace('/USDT:USDT', '')
                    try:
                        current_price_data = self.data_fetcher.get_current_price(symbol_coin)
                        exit_price = current_price_data.get('price', trade.get('entry_price', 0))
                        
                        # 计算盈亏
                        entry_price = trade.get('entry_price', exit_price)
                        side = trade.get('side', 'long')
                        amount = trade.get('amount', 0)
                        
                        if side == 'long':
                            realized_pnl = (exit_price - entry_price) * amount
                        else:
                            realized_pnl = (entry_price - exit_price) * amount
                        
                        print(f"[同步] 关闭交易 #{trade['id']} ({trade['symbol']}) - 平仓价${exit_price:,.2f}")
                    except Exception as e:
                        print(f"[警告] 获取平仓价失败: {e}")
                        exit_price = trade.get('entry_price', 0)
                        realized_pnl = 0
                    
                    self.trade_db.close_trade(
                        trade_id=trade['id'],
                        exit_price=exit_price,
                        realized_pnl=realized_pnl,
                        ai_decision={'reason': '系统同步：币种不匹配'}
                    )
        except Exception as e:
            print(f"[警告] 数据库同步失败: {e}")
    
    def validate_position_consistency(self, db_position: Optional[Dict], 
                                     api_position: Optional[Dict]) -> bool:
        """
        验证数据库持仓与API持仓的一致性
        
        Args:
            db_position: 数据库中的持仓
            api_position: API返回的持仓
            
        Returns:
            是否一致
        """
        if not db_position and not api_position:
            return True
        
        if not db_position or not api_position:
            return False
        
        # 检查币种
        if db_position.get('symbol') != api_position.get('symbol'):
            return False
        
        # 检查方向
        if db_position.get('side') != api_position.get('side'):
            return False
        
        # 检查数量（允许小误差）
        db_amount = abs(db_position.get('amount', 0))
        api_amount = abs(api_position.get('contracts', 0))
        if abs(db_amount - api_amount) > 0.0001:
            return False
        
        return True
    
    def get_position_summary(self, positions: List[Dict]) -> Dict:
        """
        获取持仓摘要信息
        
        Args:
            positions: 持仓列表
            
        Returns:
            摘要信息字典
        """
        if not positions:
            return {
                'total_positions': 0,
                'total_unrealized_pnl': 0,
                'long_positions': 0,
                'short_positions': 0
            }
        
        summary = {
            'total_positions': len(positions),
            'total_unrealized_pnl': sum(p.get('unrealized_pnl', 0) for p in positions),
            'long_positions': sum(1 for p in positions if p.get('side') == 'long'),
            'short_positions': sum(1 for p in positions if p.get('side') == 'short'),
            'positions': []
        }
        
        for pos in positions:
            summary['positions'].append({
                'symbol': pos.get('symbol'),
                'side': pos.get('side'),
                'amount': pos.get('contracts'),
                'entry_price': pos.get('entry_price'),
                'current_price': pos.get('mark_price'),
                'unrealized_pnl': pos.get('unrealized_pnl'),
                'pnl_percent': pos.get('percentage')
            })
        
        return summary
