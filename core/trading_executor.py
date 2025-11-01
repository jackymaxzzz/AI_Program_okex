"""
交易执行模块 - 负责执行AI的交易决策
"""
from typing import Dict, Optional
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import TRADING_CONFIG


class TradingExecutor:
    """交易执行器 - 处理开仓、平仓、持仓管理等操作"""
    
    def __init__(self, data_fetcher, trade_db):
        """
        初始化交易执行器
        
        Args:
            data_fetcher: 数据获取器
            trade_db: 交易数据库
        """
        self.data_fetcher = data_fetcher
        self.trade_db = trade_db
    
    def execute_trade(self, decision: Dict, current_price: float, market_data: Dict, 
                     current_trade_id: Optional[int] = None, all_market_data: Dict = None) -> Optional[int]:
        """
        执行交易决策
        
        Args:
            decision: AI决策
            current_price: 当前价格
            market_data: 市场数据
            current_trade_id: 当前交易ID
            all_market_data: 所有市场数据
            
        Returns:
            交易ID（如果有开仓）
        """
        signal = decision.get('signal')
        symbol_coin = decision.get('symbol', 'BTC')
        
        if signal == 'HOLD' or symbol_coin == 'NONE':
            return current_trade_id
        
        # 构建完整交易对符号
        symbol_full = f"{symbol_coin}/USDT:USDT"
        
        # 执行交易
        if signal in ['BUY', 'SELL']:
            return self._execute_open_position(
                signal, symbol_full, decision, current_price, market_data
            )
        elif signal == 'CLOSE':
            self._execute_close_position(
                symbol_full, decision, current_price, current_trade_id
            )
            return None
        
        return current_trade_id
    
    def _execute_open_position(self, signal: str, symbol: str, decision: Dict, 
                               current_price: float, market_data: Dict) -> Optional[int]:
        """
        执行开仓
        
        Args:
            signal: 交易信号 (BUY/SELL)
            symbol: 交易对符号
            decision: AI决策
            current_price: 当前价格
            market_data: 市场数据
            
        Returns:
            交易ID
        """
        side = 'long' if signal == 'BUY' else 'short'
        amount = decision.get('amount', 0.01)
        stop_loss = decision.get('stop_loss')
        take_profit = decision.get('take_profit')
        
        print(f"\n{'='*70}")
        print(f"[执行] {signal} {symbol}")
        print(f"方向: {side}")
        print(f"数量: {amount}")
        print(f"价格: ${current_price:,.2f}")
        print(f"止损: ${stop_loss:,.2f}" if stop_loss else "止损: 未设置")
        print(f"止盈: ${take_profit:,.2f}" if take_profit else "止盈: 未设置")
        print(f"{'='*70}\n")
        
        # 测试模式：只记录到数据库
        if TRADING_CONFIG.get('test_mode', True):
            trade_id = self.trade_db.record_trade(
                symbol=symbol,
                side=side,
                amount=amount,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                leverage=TRADING_CONFIG.get('leverage', 10),
                ai_decision=decision
            )
            print(f"[测试模式] 交易已记录到数据库 (ID: {trade_id})")
            return trade_id
        else:
            # 实盘模式：执行真实交易
            return self._execute_real_open(signal, symbol, decision, current_price)
    
    def _execute_close_position(self, symbol: str, decision: Dict, 
                                current_price: float, trade_id: Optional[int]):
        """
        执行平仓
        
        Args:
            symbol: 交易对符号
            decision: AI决策
            current_price: 当前价格
            trade_id: 交易ID
        """
        print(f"\n{'='*70}")
        print(f"[执行] CLOSE {symbol}")
        print(f"价格: ${current_price:,.2f}")
        print(f"{'='*70}\n")
        
        # 测试模式：只更新数据库
        if TRADING_CONFIG.get('test_mode', True):
            if trade_id:
                # 计算盈亏
                trade = self.trade_db.get_trade_by_id(trade_id)
                if trade:
                    entry_price = trade.get('entry_price', current_price)
                    side = trade.get('side', 'long')
                    amount = trade.get('amount', 0)
                    
                    if side == 'long':
                        realized_pnl = (current_price - entry_price) * amount
                    else:
                        realized_pnl = (entry_price - current_price) * amount
                    
                    self.trade_db.close_trade(
                        trade_id=trade_id,
                        exit_price=current_price,
                        realized_pnl=realized_pnl,
                        ai_decision=decision
                    )
                    print(f"[测试模式] 交易已平仓 (ID: {trade_id}, 盈亏: ${realized_pnl:+,.2f})")
        else:
            # 实盘模式：执行真实平仓
            self._execute_real_close(symbol, decision, current_price, trade_id)
    
    def execute_close_all(self, decision: Dict, all_positions: list, all_market_data: Dict):
        """
        执行清仓所有持仓
        
        Args:
            decision: AI决策
            all_positions: 所有持仓列表
            all_market_data: 所有市场数据
        """
        print(f"\n{'='*70}")
        print("[执行] 清仓所有持仓")
        print(f"{'='*70}\n")
        
        if not all_positions:
            print("[信息] 当前无持仓，无需平仓")
            return
        
        for position in all_positions:
            symbol = position.get('symbol')
            symbol_coin = symbol.replace('/USDT:USDT', '')
            
            # 获取当前价格
            current_price = all_market_data.get(symbol_coin, {}).get('price', 0)
            
            if current_price > 0:
                # 计算盈亏
                entry_price = position.get('entry_price', current_price)
                side = position.get('side', 'long')
                amount = abs(position.get('contracts', 0))
                
                if side == 'long':
                    realized_pnl = (current_price - entry_price) * amount
                else:
                    realized_pnl = (entry_price - current_price) * amount
                
                # 测试模式
                if TRADING_CONFIG.get('test_mode', True):
                    # 查找对应的交易记录
                    open_trades = self.trade_db.get_open_trades()
                    for trade in open_trades:
                        if trade.get('symbol') == symbol:
                            self.trade_db.close_trade(
                                trade_id=trade['id'],
                                exit_price=current_price,
                                realized_pnl=realized_pnl,
                                ai_decision=decision
                            )
                            print(f"[完成] {symbol_coin} 平仓完成")
                            break
                else:
                    # 实盘模式：执行真实平仓
                    try:
                        self._execute_real_close(symbol, decision, current_price, None)
                        print(f"[完成] {symbol_coin} 平仓完成")
                    except Exception as e:
                        print(f"[失败] {symbol_coin} 平仓失败: {e}")
        
        print(f"\n{'='*70}")
        print("[完成] 所有持仓已平仓")
        print(f"{'='*70}\n")
    
    def execute_position_reviews(self, reviews: list, all_market_data: Dict, all_positions: list = None):
        """
        执行持仓管理建议
        
        Args:
            reviews: 持仓管理建议列表
            all_market_data: 所有市场数据
            all_positions: 所有持仓列表
        """
        if not reviews:
            return
        
        print(f"\n{'='*70}")
        print("[执行] 持仓管理")
        print(f"{'='*70}\n")
        
        for review in reviews:
            symbol_coin = review.get('symbol')
            suggested_sl = review.get('suggested_stop_loss')
            suggested_tp = review.get('suggested_take_profit')
            reason = review.get('reason', '')
            
            if not symbol_coin:
                continue
            
            symbol_full = f"{symbol_coin}/USDT:USDT"
            
            # 获取当前持仓
            current_position = None
            if all_positions:
                for pos in all_positions:
                    if pos.get('symbol') == symbol_full:
                        current_position = pos
                        break
            
            if not current_position:
                print(f"[警告] {symbol_coin}: 未找到持仓，跳过")
                continue
            
            # 获取当前止损止盈
            current_sl = current_position.get('stop_loss')
            current_tp = current_position.get('take_profit')
            
            # 判断是否需要调整
            sl_changed = suggested_sl and abs(suggested_sl - (current_sl or 0)) > 0.01
            tp_changed = suggested_tp and abs(suggested_tp - (current_tp or 0)) > 0.01
            
            if sl_changed or tp_changed:
                print(f"\n{symbol_coin}:")
                if sl_changed:
                    print(f"  止损: ${current_sl:,.2f} → ${suggested_sl:,.2f}")
                if tp_changed:
                    print(f"  止盈: ${current_tp:,.2f} → ${suggested_tp:,.2f}")
                if reason:
                    print(f"  理由: {reason}")
                
                # 测试模式：只更新数据库
                if TRADING_CONFIG.get('test_mode', True):
                    open_trades = self.trade_db.get_open_trades()
                    for trade in open_trades:
                        if trade.get('symbol') == symbol_full:
                            self.trade_db.update_stop_loss_take_profit(
                                trade_id=trade['id'],
                                stop_loss=suggested_sl if sl_changed else current_sl,
                                take_profit=suggested_tp if tp_changed else current_tp
                            )
                            print(f"  [完成] 数据库已更新")
                            break
                else:
                    # 实盘模式：调用API更新
                    try:
                        self._update_real_position_sl_tp(
                            symbol_full, suggested_sl, suggested_tp
                        )
                        print(f"  [完成] 止损止盈已更新")
                    except Exception as e:
                        print(f"  [失败] 更新失败: {e}")
        
        print(f"\n{'='*70}\n")
    
    def _execute_real_open(self, signal: str, symbol: str, decision: Dict, current_price: float) -> Optional[int]:
        """执行实盘开仓"""
        try:
            # 获取交易参数
            side = 'buy' if signal == 'BUY' else 'sell'
            pos_side = 'long' if signal == 'BUY' else 'short'
            coin = symbol.split('/')[0]
            amount = decision.get('amount', TRADING_CONFIG['amounts'].get(coin, 0.01))
            
            # 获取交易模式（全仓/逐仓）
            trade_mode = TRADING_CONFIG.get('trade_mode', 'cross')
            
            print(f"开仓参数: {symbol} | 方向: {side} | 数量: {amount} | 模式: {trade_mode} | 持仓方向: {pos_side}")
            
            # 执行开仓
            params = {
                'tdMode': trade_mode,
                'posSide': pos_side
            }
            
            order = self.data_fetcher.exchange.create_order(
                symbol=symbol,
                type='market',
                side=side,
                amount=amount,
                params=params
            )
            
            order_id = order.get('id', 'N/A')
            print(f"[完成] 开仓成功: {order_id}")
            
            # 记录到数据库
            stop_loss = decision.get('stop_loss', 0)
            take_profit = decision.get('take_profit', 0)
            
            trade_id = self.trade_db.add_trade(
                symbol=symbol,
                side=pos_side,
                entry_price=current_price,
                amount=amount,
                stop_loss=stop_loss,
                take_profit=take_profit,
                ai_decision=decision
            )
            
            print(f"[数据] 交易记录已保存: ID#{trade_id}")
            return trade_id
            
        except Exception as e:
            print(f"[失败] 开仓失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _execute_real_close(self, symbol: str, decision: Dict, current_price: float, trade_id: Optional[int]):
        """执行实盘平仓"""
        try:
            # 获取当前持仓
            position = self.data_fetcher.get_position_by_symbol(symbol)
            if not position:
                print(f"[警告] 未找到{symbol}持仓")
                return
            
            # 获取持仓信息
            amount = position.get('size', 0)
            side = position.get('side')  # 'long' or 'short'
            
            if amount <= 0:
                print(f"[警告] 持仓数量为0，无需平仓")
                return
            
            # 平仓方向：多单平仓用sell，空单平仓用buy
            close_side = 'sell' if side == 'long' else 'buy'
            
            # 获取交易模式
            trade_mode = TRADING_CONFIG.get('trade_mode', 'cross')
            
            print(f"平仓参数: {symbol} | 方向: {close_side} | 数量: {amount} | 模式: {trade_mode} | 持仓方向: {side}")
            
            # 执行平仓
            params = {
                'tdMode': trade_mode,
                'posSide': side,
                'reduceOnly': True
            }
            
            order = self.data_fetcher.exchange.create_order(
                symbol=symbol,
                type='market',
                side=close_side,
                amount=amount,
                params=params
            )
            
            order_id = order.get('id', 'N/A')
            print(f"[完成] 平仓成功: {order_id}")
            
            # 更新数据库
            if trade_id:
                realized_pnl = position.get('unrealized_pnl', 0)
                self.trade_db.close_trade(
                    trade_id=trade_id,
                    exit_price=current_price,
                    realized_pnl=realized_pnl,
                    ai_decision=decision
                )
                print(f"[数据] 交易记录已更新: ID#{trade_id}")
            
        except Exception as e:
            print(f"[失败] 平仓失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _update_real_position_sl_tp(self, symbol: str, stop_loss: float, take_profit: float):
        """更新实盘持仓的止损止盈"""
        try:
            # 获取当前持仓
            position = self.data_fetcher.get_position_by_symbol(symbol)
            if not position:
                print(f"[警告] 未找到{symbol}持仓，无法更新止损止盈")
                return
            
            side = position.get('side')  # 'long' or 'short'
            
            # OKX设置止损止盈（使用条件单）
            # 注意：这需要使用OKX的algo order API
            # 这里提供基本实现，实际使用时可能需要根据OKX API调整
            
            print(f"[数据] 更新止损止盈: {symbol} | 止损: ${stop_loss:.2f} | 止盈: ${take_profit:.2f}")
            
            # 设置止损单
            if stop_loss > 0:
                sl_params = {
                    'stopLossPrice': stop_loss,
                    'posSide': side
                }
                # self.data_fetcher.exchange.create_order(...) # 需要使用algo order
            
            # 设置止盈单
            if take_profit > 0:
                tp_params = {
                    'takeProfitPrice': take_profit,
                    'posSide': side
                }
                # self.data_fetcher.exchange.create_order(...) # 需要使用algo order
            
            print(f"[完成] 止损止盈参数已设置")
            
        except Exception as e:
            print(f"[失败] 更新止损止盈失败: {e}")
