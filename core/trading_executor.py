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
    
    def __init__(self, data_fetcher, trade_db, mcp_memory=None):
        """
        初始化交易执行器
        
        Args:
            data_fetcher: 数据获取器
            trade_db: 交易数据库
            mcp_memory: MCP记忆系统（可选）
        """
        self.data_fetcher = data_fetcher
        self.trade_db = trade_db
        self.mcp_memory = mcp_memory
        self.pending_open_decisions = {}  # 待确认的开仓决策
        self.current_cycle = 0  # 当前周期号
        self.trade_decisions = {}  # 记录每笔交易的决策信息 {trade_id: decision_info}
    
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
        
        # 清理symbol格式，只保留币种名称
        # 处理可能的格式：BTC, BTC/USDT, BTC/USDT:USDT
        if ':' in symbol_coin:
            symbol_coin = symbol_coin.split(':')[0]  # 移除:USDT
        if '/' in symbol_coin:
            symbol_coin = symbol_coin.split('/')[0]  # 只保留币种名
        
        # 构建完整交易对符号
        symbol_full = f"{symbol_coin}/USDT:USDT"
        
        # 执行交易
        if signal in ['BUY', 'SELL']:
            # 检查是否需要二次确认
            if TRADING_CONFIG.get('require_double_confirmation', True):
                return self._execute_with_confirmation(
                    signal, symbol_coin, symbol_full, decision, current_price, market_data
                )
            else:
                return self._execute_open_position(
                    signal, symbol_full, decision, current_price, market_data
                )
        elif signal == 'CLOSE':
            self._execute_close_position(
                symbol_full, decision, current_price, current_trade_id
            )
            return None
        
        return current_trade_id
    
    def _execute_with_confirmation(self, signal: str, symbol_coin: str, symbol_full: str,
                                   decision: Dict, current_price: float, market_data: Dict) -> Optional[int]:
        """
        执行带二次确认的开仓
        
        Args:
            signal: 交易信号
            symbol_coin: 币种名称（如BTC）
            symbol_full: 完整交易对（如BTC/USDT:USDT）
            decision: AI决策
            current_price: 当前价格
            market_data: 市场数据
            
        Returns:
            交易ID（如果确认开仓）
        """
        # 检查是否有待确认的决策
        if symbol_coin in self.pending_open_decisions:
            pending = self.pending_open_decisions[symbol_coin]
            pending_signal = pending.get('signal')
            pending_cycle = pending.get('cycle', 0)
            
            # 如果信号一致，执行开仓
            if pending_signal == signal:
                print(f"\n[确认] {symbol_coin} 二次确认通过")
                print(f"   第一次: 周期#{pending_cycle} {pending_signal}")
                print(f"   第二次: 周期#{self.current_cycle} {signal}")
                print(f"   执行开仓...\n")
                
                # 清除待确认记录
                del self.pending_open_decisions[symbol_coin]
                
                # 执行开仓
                return self._execute_open_position(
                    signal, symbol_full, decision, current_price, market_data
                )
            else:
                # 信号不一致，更新待确认记录
                print(f"\n[取消] {symbol_coin} 信号不一致")
                print(f"   第一次: {pending_signal}")
                print(f"   第二次: {signal}")
                print(f"   更新为新信号，等待下次确认\n")
                
                self.pending_open_decisions[symbol_coin] = {
                    'signal': signal,
                    'cycle': self.current_cycle,
                    'decision': decision
                }
                return None
        else:
            # 第一次出现开仓信号，记录待确认
            coin = symbol_coin
            amount = decision.get('amount', TRADING_CONFIG['amounts'].get(coin, 0.01))
            stop_loss = decision.get('stop_loss', 0)
            take_profit = decision.get('take_profit', 0)
            confidence = decision.get('confidence', 0)
            
            print(f"\n[待确认] {symbol_coin} 开仓信号")
            print(f"   信号: {signal}")
            print(f"   数量: {amount}")
            print(f"   价格: ${current_price:.2f}")
            print(f"   止损: ${stop_loss:.2f}")
            print(f"   止盈: ${take_profit:.2f}")
            print(f"   信心度: {confidence}")
            print(f"   等待下一周期确认...\n")
            
            self.pending_open_decisions[symbol_coin] = {
                'signal': signal,
                'cycle': self.current_cycle,
                'decision': decision
            }
            return None
    
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
            
            # 清理symbol格式，只保留币种名称
            # 处理可能的格式：BTC, BTC/USDT, BTC/USDT:USDT
            if ':' in symbol_coin:
                symbol_coin = symbol_coin.split(':')[0]  # 移除:USDT
            if '/' in symbol_coin:
                symbol_coin = symbol_coin.split('/')[0]  # 只保留币种名
            
            # 构建完整交易对符号
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
                    current_sl_str = f"${current_sl:,.2f}" if current_sl else "未设置"
                    suggested_sl_str = f"${suggested_sl:,.2f}" if suggested_sl else "未设置"
                    print(f"  止损: {current_sl_str} → {suggested_sl_str}")
                if tp_changed:
                    current_tp_str = f"${current_tp:,.2f}" if current_tp else "未设置"
                    suggested_tp_str = f"${suggested_tp:,.2f}" if suggested_tp else "未设置"
                    print(f"  止盈: {current_tp_str} → {suggested_tp_str}")
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
            
            trade_id = self.trade_db.create_trade(
                symbol=symbol,
                signal=signal,
                entry_price=current_price,
                quantity=amount,
                leverage=TRADING_CONFIG.get('leverage', 10),
                ai_decision=decision,
                market_data={}
            )
            
            print(f"[数据] 交易记录已保存: ID#{trade_id}")
            
            # 设置止损止盈
            if stop_loss > 0 or take_profit > 0:
                try:
                    self._update_real_position_sl_tp(symbol, stop_loss, take_profit)
                except Exception as e:
                    print(f"[警告] 设置止损止盈失败: {e}")
            
            # 调试信息
            print(f"[调试] 开仓 - mcp_memory={self.mcp_memory is not None}, trade_id={trade_id}")
            
            # 记录到MCP记忆系统（详细的决策信息供AI学习）
            if self.mcp_memory and trade_id:
                self.trade_decisions[trade_id] = {
                    # 基本信息
                    'symbol': coin,
                    'signal': signal,
                    'entry_price': current_price,
                    'amount': amount,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    
                    # AI决策信息
                    'confidence': decision.get('confidence', 'UNKNOWN'),
                    'reason': decision.get('reason', ''),
                    'think': decision.get('think', ''),  # AI的完整思考过程
                    'market_state': decision.get('market_state', 'unknown'),
                    'strategy': decision.get('strategy', 'unknown'),
                    
                    # 技术指标（开仓时的市场状态）
                    'technical_indicators': decision.get('technical_indicators', {}),
                    
                    # 时间信息
                    'cycle': self.current_cycle,
                    'entry_time': order.get('datetime', ''),
                    'timestamp': order.get('timestamp', None),
                    
                    # 市场环境（供AI学习什么样的市场环境容易成功）
                    'market_trend': decision.get('market_trend', 'unknown'),
                    'volume_ratio': decision.get('volume_ratio', 0),
                    
                    # 订单信息
                    'order_id': order.get('id', ''),
                    'leverage': TRADING_CONFIG.get('leverage', 10)
                }
                print(f"[记忆] 决策信息已记录到MCP（含完整think过程）")
            
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
                
                # 调试信息
                print(f"[调试] trade_id={trade_id}, mcp_memory={self.mcp_memory is not None}, trade_decisions包含={trade_id in self.trade_decisions}")
                
                # 记录到MCP记忆系统
                if self.mcp_memory and trade_id in self.trade_decisions:
                    entry_info = self.trade_decisions[trade_id]
                    entry_price = entry_info['entry_price']
                    
                    # 计算盈亏百分比
                    if side == 'long':
                        pnl_percent = ((current_price - entry_price) / entry_price) * 100
                    else:  # short
                        pnl_percent = ((entry_price - current_price) / entry_price) * 100
                    
                    # 构建完整的交易信息
                    trade_info = {
                        'symbol': entry_info['symbol'],
                        'side': side,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'amount': entry_info['amount'],
                        'pnl_percent': pnl_percent,
                        'realized_pnl': realized_pnl,
                        'stop_loss': entry_info['stop_loss'],
                        'take_profit': entry_info['take_profit'],
                        'confidence': entry_info['confidence'],
                        'reason': entry_info['reason'],
                        'market_state': entry_info['market_state'],
                        'technical_indicators': entry_info['technical_indicators'],
                        'entry_cycle': entry_info['cycle'],
                        'exit_cycle': self.current_cycle,
                        'close_reason': decision.get('reason', ''),
                        'strategy': decision.get('strategy', 'unknown')
                    }
                    
                    # 记录到MCP
                    if pnl_percent > 0:
                        self.mcp_memory.record_successful_trade(trade_info)
                        print(f"[记忆] 成功交易已记录到MCP: 盈利{pnl_percent:.2f}%")
                    else:
                        self.mcp_memory.record_failed_trade(trade_info)
                        print(f"[记忆] 失败交易已记录到MCP: 亏损{abs(pnl_percent):.2f}%")
                    
                    # 清除决策记录
                    del self.trade_decisions[trade_id]
            
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
            amount = position.get('size', 0)
            
            if amount <= 0:
                print(f"[警告] 持仓数量为0，无法设置止损止盈")
                return
            
            print(f"[数据] 设置止损止盈: {symbol} | 止损: ${stop_loss:.2f} | 止盈: ${take_profit:.2f}")
            
            # 先取消该币种的所有现有algo订单
            inst_id = symbol.replace('/', '-').replace(':USDT', '-SWAP')
            try:
                pending_algos = self.data_fetcher.exchange.private_get_trade_orders_algo_pending({
                    'instId': inst_id,
                    'ordType': 'conditional'
                })
                
                if pending_algos.get('code') == '0' and pending_algos.get('data'):
                    for algo in pending_algos['data']:
                        algo_id = algo.get('algoId')
                        if algo_id:
                            cancel_result = self.data_fetcher.exchange.private_post_trade_cancel_algos([{
                                'instId': inst_id,
                                'algoId': algo_id
                            }])
                            if cancel_result.get('code') == '0':
                                print(f"  [取消] 已取消旧的algo订单: {algo_id}")
            except Exception as e:
                print(f"  [警告] 取消旧订单失败: {e}")
            
            # OKX使用algo order设置止损止盈
            # 参考: https://www.okx.com/docs-v5/zh/#order-book-trading-algo-trading-post-place-algo-order
            
            # 使用OKX的create_order设置止损止盈
            # 参考ccxt文档，使用stopLoss和takeProfit参数
            if stop_loss > 0 or take_profit > 0:
                try:
                    close_side = 'sell' if side == 'long' else 'buy'
                    trade_mode = TRADING_CONFIG.get('trade_mode', 'cross')
                    
                    # 构建订单参数
                    # 注意：全仓模式(cross)不使用posSide，逐仓模式(isolated)才使用
                    params = {
                        'tdMode': trade_mode,
                        'reduceOnly': True
                    }
                    
                    # 只有逐仓模式才需要posSide
                    if trade_mode == 'isolated':
                        params['posSide'] = side
                    
                    # 设置止损单（使用OKX原生API）
                    if stop_loss > 0:
                        try:
                            # 转换symbol格式：SOL/USDT:USDT -> SOL-USDT-SWAP
                            inst_id = symbol.replace('/', '-').replace(':USDT', '-SWAP')
                            
                            # 直接使用OKX的algo order API
                            # 注意：algo order API总是需要posSide参数
                            sl_params = {
                                'instId': inst_id,
                                'tdMode': trade_mode,
                                'side': close_side,
                                'posSide': side,  # 全仓模式也需要posSide
                                'ordType': 'conditional',  # 条件单
                                'sz': str(amount),
                                'slTriggerPx': str(stop_loss),  # 止损触发价
                                'slOrdPx': '-1'  # 市价单
                            }
                            
                            # print(f"  [调试] 止损单参数: {sl_params}")
                            
                            # 使用OKX原生API
                            result = self.data_fetcher.exchange.private_post_trade_order_algo(sl_params)
                            
                            if result.get('code') == '0':
                                algo_id = result.get('data', [{}])[0].get('algoId', 'N/A')
                                print(f"  [完成] 止损单已设置: ${stop_loss:.2f} (AlgoID: {algo_id})")
                            else:
                                print(f"  [失败] 止损单设置失败: {result}")
                        except Exception as e:
                            print(f"  [失败] 止损单设置失败: {e}")
                    
                    # 设置止盈单（使用OKX原生API）
                    if take_profit > 0:
                        try:
                            # 转换symbol格式：SOL/USDT:USDT -> SOL-USDT-SWAP
                            inst_id = symbol.replace('/', '-').replace(':USDT', '-SWAP')
                            
                            # 直接使用OKX的algo order API
                            # 注意：algo order API总是需要posSide参数
                            tp_params = {
                                'instId': inst_id,
                                'tdMode': trade_mode,
                                'side': close_side,
                                'posSide': side,  # 全仓模式也需要posSide
                                'ordType': 'conditional',  # 条件单
                                'sz': str(amount),
                                'tpTriggerPx': str(take_profit),  # 止盈触发价
                                'tpOrdPx': '-1'  # 市价单
                            }
                            
                            # print(f"  [调试] 止盈单参数: {tp_params}")
                            
                            # 使用OKX原生API
                            result = self.data_fetcher.exchange.private_post_trade_order_algo(tp_params)
                            
                            if result.get('code') == '0':
                                algo_id = result.get('data', [{}])[0].get('algoId', 'N/A')
                                print(f"  [完成] 止盈单已设置: ${take_profit:.2f} (AlgoID: {algo_id})")
                            else:
                                print(f"  [完成] 止盈单已设置: ${take_profit:.2f} (AlgoID: {tp_order.get('id', 'N/A')})")
                        except Exception as e:
                            print(f"  [失败] 止盈单设置失败: {e}")
                        
                except Exception as e:
                    print(f"  [失败] 止损止盈设置失败: {e}")
                    import traceback
                    traceback.print_exc()
            
        except Exception as e:
            print(f"[失败] 更新止损止盈失败: {e}")
            import traceback
            traceback.print_exc()
