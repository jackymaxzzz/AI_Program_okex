"""
纯AI交易器 - 完全信任AI的判断，不做任何预处理
"""
from typing import Dict, Optional
from datetime import datetime
from openai import OpenAI
from .conversation import get_monitor
from config import TRADING_CONFIG
from mcp import MCPTradingMemory, MCPFileSystem, MCPIntelligence, MarketStateAnalyzer
from utils.kline_visualizer import visualize_klines, format_kline_pattern, analyze_trend
import json
import re


# 默认策略名称
DEFAULT_STRATEGY = 'balanced'


class PureAITrader:
    """纯AI交易器 - 只负责数据投喂和执行AI决策"""
    
    def __init__(self, ai_client: OpenAI, system_prompt: str = None, strategy: str = None):
        """
        初始化纯AI交易器
        
        Args:
            ai_client: OpenAI客户端
            system_prompt: 系统提示词（可自定义）
            strategy: 策略名称（对应prompts目录下的txt文件名，如'stable_profit', 'aggressive', 'balanced'）
        """
        self.ai_client = ai_client
        
        # 初始化MCP系统（需要在monitor之前）
        self.mcp_memory = MCPTradingMemory()
        self.mcp_filesystem = MCPFileSystem()
        self.mcp_intelligence = MCPIntelligence(self.mcp_memory)
        
        # 初始化监控器，传入MCP文件系统
        self.monitor = get_monitor(mcp_filesystem=self.mcp_filesystem)
        
        # 对话历史
        self.conversation_history = []
        
        # 待确认的开仓决策（由main.py传入）
        self.pending_decisions = {}
        
        # 当前周期号（由main.py传入）
        self.current_cycle = 0
        
        # 当前策略名称
        self.current_strategy = strategy or DEFAULT_STRATEGY
        
        # Token优化：记录上次发送详细指南的周期
        self.last_detailed_guide_cycle = -1
        self.detailed_guide_interval = 20  # 每20个周期发送一次详细指南（静态内容）
        
        # Token优化：记录上次发送格式说明的周期
        self.last_format_guide_cycle = -10  # 错开发送时机，避免第一次同时发送
        self.format_guide_interval = 30  # 每30个周期发送一次格式说明（静态内容）
        
        # Token优化：记录上次发送交易历史的周期
        self.last_trade_history_cycle = -1
        self.trade_history_interval = 10  # 每10个周期发送一次交易历史（除非有新交易）
        self.last_trade_count = 0  # 记录上次的交易数量
        
        # 注意：时间序列数据是实时数据，应该每次都发送
        # 只优化显示方式（精简格式）而不是跳过发送
        
        # 交易统计信息
        self.start_time = None  # 开始交易时间
        self.invocation_count = 0  # 调用次数
        
        # MCP已在上面初始化，这里导入历史记忆
        print("[记忆] MCP记忆系统已初始化")
        print("[文件] MCP文件系统已初始化")
        self.mcp_filesystem.import_mcp_memory(self.mcp_memory)
        
        # 加载系统提示词
        if strategy:
            self.system_prompt = self._load_prompt_from_file(strategy)
            print(f"📋 使用策略: {strategy}")
        elif system_prompt:
            self.system_prompt = system_prompt
        else:
            self.system_prompt = self._load_prompt_from_file(DEFAULT_STRATEGY)
        
        # 初始化对话
        self.conversation_history.append({
            'role': 'system',
            'content': self.system_prompt
        })
        
        print("纯AI交易器初始化完成")
        print(f"系统提示词长度: {len(self.system_prompt)} 字符")
    
    def analyze_multi_coins(
        self,
        all_coins_data: Dict,
        account_balance: float,
        all_positions: Optional[list] = None
    ) -> Dict:
        """
        分析多个币种并做出决策
        
        Args:
            all_coins_data: 所有币种的数据 {'BTC': {...}, 'ETH': {...}}
            account_balance: 账户余额
            all_positions: 所有持仓列表
        
        Returns:
            AI决策结果
        """
        import time
        from datetime import datetime
        start_time = time.time()
        
        # 更新统计信息
        if self.start_time is None:
            self.start_time = datetime.now()
        self.invocation_count += 1
        
        # 构建prompt
        user_message = self._build_multi_coins_prompt(
            all_coins_data,
            account_balance,
            all_positions
        )
        
        # 监控：显示发送的数据
        self.monitor.log_user_message(
            user_message,
            metadata={
                'coins': list(all_coins_data.keys()),
                'timestamp': datetime.now().isoformat()
            }
        )
        
        # 添加到对话历史
        self.conversation_history.append({
            'role': 'user',
            'content': user_message
        })
        
        # 调用AI
        ai_response = self._call_ai()
        
        # 解析AI回复
        decision = self._parse_ai_response(ai_response)
        
        # 计算耗时
        elapsed_time = time.time() - start_time
        decision['response_time'] = elapsed_time
        
        # 保存决策日志到文件
        if hasattr(self, 'mcp_filesystem'):
            self.mcp_filesystem.save_decision_log(decision)
        
        # 监控：显示AI回复
        self.monitor.log_assistant_message(
            ai_response,
            metadata={
                'signal': decision.get('signal'),
                'symbol': decision.get('symbol'),
                'confidence': decision.get('confidence'),
                'tokens_used': decision.get('tokens_used', 0),
                'response_time': elapsed_time
            }
        )
        
        # 保存AI回复到历史
        self.conversation_history.append({
            'role': 'assistant',
            'content': ai_response
        })
        
        # 管理对话历史长度
        self._manage_conversation_history()
        
        return decision
    
    def analyze_and_decide(
        self,
        price_data: Dict,
        account_balance: float,
        current_position: Optional[Dict] = None
    ) -> Dict:
        """
        分析市场并做出决策
        
        Args:
            price_data: 价格和技术指标数据（原始数据）
            account_balance: 账户余额
            current_position: 当前持仓
            
        
        Returns:
            AI决策结果
        """
        # 1. 构建纯数据prompt
        user_message = self._build_pure_data_prompt(
            price_data,
            account_balance,
            current_position
        )
        
        # 2. 监控：显示发送的数据
        self.monitor.log_user_message(
            user_message,
            metadata={
                'price': price_data.get('price'),
                'timestamp': datetime.now().isoformat()
            }
        )
        
        # 3. 添加到对话历史
        self.conversation_history.append({
            'role': 'user',
            'content': user_message
        })
        
        # 4. 调用AI
        ai_response = self._call_ai()
        
        # 5. 解析AI回复
        decision = self._parse_ai_response(ai_response)
        
        # 6. 监控：显示AI回复
        self.monitor.log_assistant_message(
            ai_response,
            metadata={
                'signal': decision.get('signal'),
                'confidence': decision.get('confidence'),
                'tokens_used': decision.get('tokens_used', 0)
            }
        )
        
        # 7. 保存AI回复到历史
        self.conversation_history.append({
            'role': 'assistant',
            'content': ai_response
        })
        
        # 8. 管理对话历史长度
        self._manage_conversation_history()
        
        return decision
    
    def _build_multi_coins_prompt(
        self,
        all_coins_data: Dict,
        balance: float,
        all_positions: Optional[list]
    ) -> str:
        """构建多币种数据prompt"""
        from datetime import datetime as dt
        timestamp = dt.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 计算交易统计信息
        trading_stats = ""
        if self.start_time:
            elapsed_minutes = int((dt.now() - self.start_time).total_seconds() / 60)
            trading_stats = f"""
【第一人称视角提醒】
这是你的真实交易账户！你已经交易了 {elapsed_minutes} 分钟，当前时间是 {timestamp}，这是你第 {self.invocation_count} 次做决策。
下面是各种市场数据、技术指标和预测信号，帮助你（我）发现交易机会。
随后是你（我）的账户信息、资金状况、持仓表现等。

请用第一人称思考：这是"我的"资金，"我"要为每笔交易负责。

"""
        
        # 账户总览和历史交易
        account_overview = ""
        if hasattr(self, 'account_stats'):
            stats = self.account_stats
            account_overview = f"""
这是你的账户信息和表现
当前总回报率: {stats.get('total_return_pct', 0):.2f}%
可用资金: {stats.get('available_cash', balance):,.2f}
当前账户价值: {stats.get('total_value', 0):,.2f}
"""
            # 添加所有持仓列表
            positions = stats.get('all_positions', [])
            if positions:
                account_overview += "当前持仓及表现:\n"
                for pos in positions:
                    pnl = pos.get('unrealized_pnl', 0)
                    # 计算持仓时长
                    holding_duration = ""
                    if pos.get('entry_time'):
                        from datetime import datetime
                        entry_time = pos.get('entry_time')
                        if isinstance(entry_time, str):
                            entry_time = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
                        duration = datetime.now() - entry_time
                        hours = int(duration.total_seconds() / 3600)
                        minutes = int((duration.total_seconds() % 3600) / 60)
                        if hours > 0:
                            holding_duration = f"{hours}小时{minutes}分钟"
                        else:
                            holding_duration = f"{minutes}分钟"
                    
                    account_overview += f"{pos.get('symbol')}: 数量={pos.get('quantity')}, 入场价={pos.get('entry_price', 0):,.2f}, 当前价={pos.get('current_price', 0):,.2f}, 清算价={pos.get('liquidation_price', 0):,.2f}, 未实现盈亏={pnl:+,.2f}, 杠杆={pos.get('leverage', 10)}x, 持仓时长={holding_duration if holding_duration else 'N/A'}, 止盈={pos.get('exit_plan', {}).get('profit_target', 0):,.2f}, 止损={pos.get('exit_plan', {}).get('stop_loss', 0):,.2f}\n"
        else:
            # 如果没有设置账户统计，显示基本信息
            initial_balance = TRADING_CONFIG.get('initial_balance', 200.0)
            
            # balance参数是账户权益（equity），包含所有盈亏
            total_value = balance
            
            # 获取可用余额
            avail_balance = getattr(self, 'available_balance', balance)
            
            pnl = total_value - initial_balance
            pnl_pct = (pnl / initial_balance) * 100 if initial_balance > 0 else 0
            
            # 风险警告
            risk_warning = ""
            if pnl_pct < -50:
                risk_warning = f"\n高风险警告\n当前账户已亏损 {abs(pnl_pct):.2f}%！必须更加谨慎！\n"
            elif pnl_pct < -30:
                risk_warning = f"\n风险警告\n当前账户已亏损 {abs(pnl_pct):.2f}%，需要谨慎操作\n"
            
            # Token优化：只在需要时发送详细指南
            should_send_detailed_guide = (
                self.current_cycle - self.last_detailed_guide_cycle >= self.detailed_guide_interval
                or self.last_detailed_guide_cycle == -1  # 第一次
            )
            
            if should_send_detailed_guide:
                self.last_detailed_guide_cycle = self.current_cycle
                detailed_guide = f"""
开仓指南：最大数量=(余额×0.7×10)/(价格×1.05)
XRP: 1张=100个，amount=0.1代表10个XRP
"""
            else:
                detailed_guide = ""
            
            account_overview = f"""
=== 账户总览 ===
初始: ${initial_balance:,.2f} | 可用: ${avail_balance:,.2f} | 账户金额: ${total_value:,.2f}
盈亏: ${pnl:+,.2f} ({pnl_pct:+.2f}%)
{risk_warning}{detailed_guide}
"""
        
        # Token优化：判断是否需要发送交易历史
        should_send_trade_history = False
        try:
            from data import TradeDatabase
            db = TradeDatabase()
            
            # 获取当前持仓的symbol列表（用于过滤）
            current_symbols = [pos.get('symbol') for pos in (all_positions or [])]
            
            # 直接从API获取最近的成交记录
            limit = TRADING_CONFIG.get('history_trades_limit', 5)
            try:
                recent_trades = self._fetch_recent_trades_from_api(limit=limit, current_symbols=current_symbols)
            except Exception as e:
                recent_trades = []
            
            # 判断是否需要发送交易历史
            current_trade_count = len(recent_trades) if recent_trades else 0
            
            # 如果有新交易，或者距离上次发送超过间隔，就发送
            if current_trade_count > self.last_trade_count:
                # 有新交易，必须发送
                should_send_trade_history = True
                self.last_trade_count = current_trade_count
                self.last_trade_history_cycle = self.current_cycle
            elif (self.current_cycle - self.last_trade_history_cycle >= self.trade_history_interval
                  or self.last_trade_history_cycle == -1):
                # 距离上次发送超过间隔，发送一次
                should_send_trade_history = True
                self.last_trade_history_cycle = self.current_cycle
            
            if should_send_trade_history and recent_trades:
                # 从API获取所有平仓成交并计算统计
                try:
                    all_closed_trades = self._fetch_recent_trades_from_api(limit=1000, current_symbols=current_symbols)
                    
                    if all_closed_trades and len(all_closed_trades) > 0:
                        total_trades = len(all_closed_trades)
                        winning_trades = len([t for t in all_closed_trades if t.get('realized_pnl', 0) > 0])
                        losing_trades = len([t for t in all_closed_trades if t.get('realized_pnl', 0) < 0])
                        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
                        total_pnl = sum([t.get('realized_pnl', 0) for t in all_closed_trades])
                        
                        account_overview += f"""
=== 你的交易统计（最近{total_trades}笔）===
胜率: {win_rate:.1f}% ({winning_trades}胜 / {losing_trades}负)
累计盈亏: ${total_pnl:+,.2f} USDT

重要：请认真分析你自己的交易表现
- 如果胜率低于50%，说明你的策略需要调整
- 如果亏损较多，需要反思是否过于激进或判断错误
- 成功的交易有什么共同特征？失败的交易哪里出了问题？
- 从你的历史交易中学习，不断优化你的决策
"""
                except:
                    pass
                account_overview += f"\n=== 你最近{len(recent_trades)}笔平仓交易详情 ===\n（认真分析每笔交易，找出成功和失败的原因）\n"
                for i, trade in enumerate(recent_trades, 1):
                    pnl = trade.get('realized_pnl', 0)
                    pnl_pct = trade.get('pnl_percent', 0)
                    duration = trade.get('holding_duration_seconds', 0)
                    
                    
                    # 格式化时长
                    if duration < 3600:
                        duration_str = f"{duration/60:.0f}分钟"
                    elif duration < 86400:
                        duration_str = f"{duration/3600:.1f}小时"
                    else:
                        duration_str = f"{duration/86400:.1f}天"
                    
                    # 格式化时间
                    close_time = trade.get('close_time')
                    if close_time:
                        close_time_str = close_time.strftime('%m-%d %H:%M')
                    else:
                        close_time_str = 'N/A'
                    
                    result_symbol = "盈利" if pnl > 0 else "亏损"
                    
                    # 格式化盈亏（保留更多小数位）
                    if abs(pnl) < 0.01:
                        pnl_str = f"${pnl:+.4f}"
                    else:
                        pnl_str = f"${pnl:+,.2f}"
                    
                    # 提取币种名称
                    coin = trade.get('symbol', '').split('/')[0]
                    entry_price = trade.get('entry_price', 0)
                    exit_price = trade.get('exit_price', 0)
                    
                    account_overview += f"""
{i}. {coin} | {result_symbol} {pnl_pct:+.2f}% | 持仓时长: {duration_str}
   开仓: ${entry_price:,.2f} -> 平仓: ${exit_price:,.2f} | 盈亏: {pnl_str}
   平仓时间: {close_time_str}
"""
                    # 添加AI的决策理由（如果有）
                    ai_decision = trade.get('ai_decision')
                    if ai_decision and isinstance(ai_decision, dict):
                        reason = ai_decision.get('reason', '')
                        if reason and len(reason) < 100:  # 只显示简短的理由
                            account_overview += f"   理由: {reason}\n"
        except Exception as e:
            # 如果获取历史失败，不影响主流程
            pass
        
        # 即使没有账户统计，也显示当前持仓（如果有）
        if all_positions and len(all_positions) > 0:
            account_overview += f"\n当前持仓列表:({len(all_positions)}个)\n"
            
            for position in all_positions:
                # 获取持仓详细信息
                from data import TradeDatabase
                db = TradeDatabase()
                
                # 查找交易记录
                trade = None
                if self.current_trade_id:
                    trade = db.get_trade_by_id(self.current_trade_id)
                else:
                    symbol = position.get('symbol')
                    if symbol:
                        open_trades = db.get_open_trades(symbol)
                        if open_trades:
                            trade = open_trades[0]  # 取第一个未平仓交易
                
                # 格式化数量
                amount = position.get('btc_amount', 0)
                if amount < 1:
                    amount_str = f"{amount:.4f}"
                else:
                    amount_str = f"{amount:.2f}"
                
                # 计算持仓时长（使用持仓本身的创建时间）
                holding_duration = "N/A"
                open_time_for_db = None
                
                # 从API获取开仓时间
                try:
                    from datetime import datetime, timedelta
                    
                    symbol = position.get('symbol')
                    
                    # 使用position自带的时间戳（OKX返回cTime创建时间）
                    pos_timestamp = position.get('cTime') or position.get('uTime') or position.get('timestamp')
                    
                    if pos_timestamp:
                        # OKX的时间戳是毫秒
                        open_time = datetime.fromtimestamp(int(pos_timestamp) / 1000)
                        open_time_for_db = open_time.isoformat()
                        duration_seconds = (datetime.now() - open_time).total_seconds()
                        
                        if duration_seconds < 3600:
                            holding_duration = f"{duration_seconds/60:.0f}分钟"
                        elif duration_seconds < 86400:
                            holding_duration = f"{duration_seconds/3600:.1f}小时"
                        else:
                            holding_duration = f"{duration_seconds/86400:.1f}天"
                        
                except Exception as e:
                    # 如果获取失败，静默处理
                    pass
                
                # 备用方案：使用数据库
                if holding_duration == "N/A":
                    trade = None
                    try:
                        from data import TradeDatabase
                        db = TradeDatabase()
                        if self.current_trade_id:
                            trade = db.get_trade_by_id(self.current_trade_id)
                    except:
                        pass
                    
                    if trade:
                        # 备用：使用数据库记录的时间
                        try:
                            open_time = datetime.fromisoformat(trade['open_time'])
                            duration_seconds = (datetime.now() - open_time).total_seconds()
                            if duration_seconds < 3600:
                                holding_duration = f"{duration_seconds/60:.0f}分钟"
                            elif duration_seconds < 86400:
                                holding_duration = f"{duration_seconds/3600:.1f}小时"
                            else:
                                holding_duration = f"{duration_seconds/86400:.1f}天"
                        except:
                            pass
                
                
                # 获取止损止盈（优先使用API返回的实际值）
                stop_loss = position.get('stop_loss')
                take_profit = position.get('take_profit')
                
                # 如果API没有返回，从数据库获取
                if not stop_loss and not take_profit and trade:
                    ai_decision = trade.get('ai_decision', {})
                    if isinstance(ai_decision, str):
                        import json
                        try:
                            ai_decision = json.loads(ai_decision)
                        except:
                            ai_decision = {}
                    stop_loss = stop_loss or ai_decision.get('stop_loss')
                    take_profit = take_profit or ai_decision.get('take_profit')
                
                # 获取持仓ID
                pos_id = position.get('pos_id', 'N/A')
                
                account_overview += f"""
- {position.get('symbol', 'N/A')} {position.get('side', 'N/A').upper()}
  持仓ID: {pos_id} | 数量: {amount_str} | 持仓时长: {holding_duration}
  开仓价: ${position.get('entry_price', 0):,.2f} | 未实现盈亏: ${position.get('unrealized_pnl', 0):,.2f}
  清算价: ${position.get('liquidation_price', 0):,.2f} | 杠杆: {position.get('leverage', 10)}x"""
                
                # 显示止损止盈（包括未设置的情况）
                account_overview += "\n  "
                if stop_loss:
                    account_overview += f"止损: ${stop_loss:,.2f}"
                else:
                    account_overview += "止损: 未设置"
                
                account_overview += " | "
                
                if take_profit:
                    account_overview += f"止盈: ${take_profit:,.2f}"
                else:
                    account_overview += "止盈: 未设置"
                
                account_overview += "\n"
        
        # 不再单独显示持仓信息（已经在账户总览中显示）
        position_info = ""
        if False:  # 禁用这部分代码
            # 从API获取开仓时间并计算持仓时长
            holding_duration = ""
            if position:
                try:
                    from utils.data_fetcher import DataFetcher
                    from datetime import datetime, timedelta
                    
                    data_fetcher = DataFetcher()
                    symbol = position.get('symbol')
                    
                    # 获取最近的成交记录
                    trades = data_fetcher.exchange.fetch_my_trades(
                        symbol=symbol,
                        since=int((datetime.now() - timedelta(days=7)).timestamp() * 1000),
                        limit=100
                    )
                    
                    # 找到最近的开仓成交（fillPnl为0的）
                    for trade in reversed(trades):  # 从最新的开始找
                        fill_pnl = trade.get('info', {}).get('fillPnl', '0')
                        if fill_pnl == '0':  # 开仓成交
                            open_time = datetime.fromtimestamp(trade['timestamp'] / 1000)
                            duration_seconds = (datetime.now() - open_time).total_seconds()
                            
                            if duration_seconds < 3600:
                                holding_duration = f"{duration_seconds/60:.0f}分钟"
                            elif duration_seconds < 86400:
                                holding_duration = f"{duration_seconds/3600:.1f}小时"
                            else:
                                holding_duration = f"{duration_seconds/86400:.1f}天"
                            break
                except Exception as e:
                    pass  # 忽略持仓时长计算错误
            
            # 格式化数量
            amount = position.get('btc_amount', 0)
            if amount < 1:
                amount_str = f"{amount:.4f}"
            else:
                amount_str = f"{amount:.2f}"
            
            # 获取止损止盈信息（从数据库）
            sl_tp_info = ""
            if trade:
                ai_decision = trade.get('ai_decision', {})
                if isinstance(ai_decision, str):
                    import json
                    try:
                        ai_decision = json.loads(ai_decision)
                    except:
                        ai_decision = {}
                
                stop_loss = ai_decision.get('stop_loss')
                take_profit = ai_decision.get('take_profit')
                
                if stop_loss or take_profit:
                    sl_tp_info = "\n"
                    if stop_loss:
                        sl_tp_info += f"止损: ${stop_loss:,.2f}\n"
                    if take_profit:
                        sl_tp_info += f"止盈: ${take_profit:,.2f}\n"
            
            position_info = f"""
=== 当前持仓 ===
币种: {position.get('symbol', 'N/A')}
方向: {position.get('side', 'N/A').upper()}
数量: {amount_str}
开仓价: ${position.get('entry_price', 0):,.2f}
未实现盈亏: ${position.get('unrealized_pnl', 0):,.2f}
清算价: ${position.get('liquidation_price', 0):,.2f}
杠杆: {position.get('leverage', 10)}x
持仓时长: {holding_duration if holding_duration else 'N/A'}{sl_tp_info}
"""
        
        # Token优化：历史决策提醒只在前几次发送
        history_reminder = ""
        if len(self.conversation_history) > 2 and self.current_cycle <= 3:
            history_reminder = "\n注意：如改变观点请说明原因\n"
        
        # 添加待确认的开仓决策提示（包含上次决策的详细信息）
        pending_reminder = ""
        if hasattr(self, 'pending_decisions') and self.pending_decisions:
            pending_reminder = "\n[提醒] 待确认的开仓信号：\n"
            for symbol, info in self.pending_decisions.items():
                signal = info.get('signal')
                cycle = info.get('cycle')
                decision = info.get('decision', {})
                
                # 显示上次的完整决策信息
                pending_reminder += f"\n{symbol} {signal}（周期#{cycle}首次建议）：\n"
                pending_reminder += f"  信心度: {decision.get('confidence', 'N/A')}\n"
                pending_reminder += f"  理由: {decision.get('reason', 'N/A')}\n"
                
                # 显示当时的价格（从市场数据中获取）
                current_price = 0
                if symbol in all_coins_data:
                    current_price = all_coins_data[symbol].get('price', 0)
                if current_price > 0:
                    pending_reminder += f"  当时价格: ${current_price:,.2f}\n"
                
                pending_reminder += f"  止损: ${decision.get('stop_loss', 0):.2f}\n"
                pending_reminder += f"  止盈: ${decision.get('take_profit', 0):.2f}\n"
                pending_reminder += f"  数量: {decision.get('amount', 0)}\n"
            
            pending_reminder += """
这些是首次信号，需要本轮再次确认才会执行：
- 如果你仍然认为应该开仓，请在本轮决策中再次给出相同的信号
- 如果市场情况变化，可以改变决策（观望则symbol填NONE，signal填HOLD）
- 每个币种的决策是独立的
"""
        
        # 获取当前周期号
        cycle_info = f"周期#{self.current_cycle}" if hasattr(self, 'current_cycle') and self.current_cycle > 0 else ""
        
        # 获取MCP记忆洞察（包含长期记忆）
        mcp_insights = ""
        if hasattr(self, 'mcp_memory') and self.mcp_memory.enabled:
            # 调试：显示MCP记录数量
            success_count = len(self.mcp_memory.successful_trades)
            failed_count = len(self.mcp_memory.failed_trades)
            print(f"[MCP] 历史记录: 成功{success_count}笔, 失败{failed_count}笔")
            
            # 获取短期交易洞察
            all_insights = self.mcp_memory.get_all_insights()
            if all_insights:
                mcp_insights = all_insights + "\n"
            
            # 获取长期记忆洞察
            long_term_insights = self.mcp_memory.get_long_term_insights()
            if long_term_insights:
                mcp_insights += long_term_insights + "\n"
        
        prompt = f"""{trading_stats}【多币种市场分析 - {timestamp} {cycle_info}】
{account_overview}
{position_info}
{history_reminder}
{pending_reminder}
{mcp_insights}

=== 实时行情数据 ===
"""
        
        # 为每个币种添加数据（时间序列数据每次都发送，但使用精简格式）
        for coin, coin_data in all_coins_data.items():
            prompt += self._format_coin_section(coin, coin_data)
            
            # 添加该币种的历史交易洞察（仅提供历史数据，不做建议）
            if hasattr(self, 'mcp_memory') and self.mcp_memory.enabled:
                coin_insights = self.mcp_memory.get_trading_insights(coin)
                if coin_insights:
                    prompt += coin_insights + "\n"
            
            prompt += "\n" + "="*70 + "\n\n"
        
        # Token优化：格式说明只在需要时发送
        should_send_format_guide = (
            self.current_cycle - self.last_format_guide_cycle >= self.format_guide_interval
            or self.last_format_guide_cycle == -1
        )
        
        if should_send_format_guide:
            self.last_format_guide_cycle = self.current_cycle
            format_guide = """
请分析以上数据并给出决策。

信号定义：
- BUY/SELL: 开多/空单
- HOLD: 观望(symbol=NONE)
- CLOSE_ALL: 清仓(symbol=ALL)

持仓管理(仅评估"当前持仓列表"中的仓位)：
对于每个持仓，只需提供：
- symbol: 币种
- suggested_stop_loss: 建议的止损价格
- suggested_take_profit: 建议的止盈价格

重要规则：
1. 只为"当前持仓列表"中的币种提供建议
2. 没有持仓的币种不要包含在position_reviews中
3. 系统会自动检测并调整止损止盈

信心度：HIGH(80%+)/MEDIUM(50-80%)/LOW(<50%)

JSON格式：
{
  "primary_action": {"symbol": "币种/NONE/ALL", "signal": "BUY/SELL/HOLD/CLOSE_ALL", "confidence": "HIGH/MEDIUM/LOW", "reason": "理由", "stop_loss": 价格, "take_profit": 价格, "amount": 数量},
  "position_reviews": [{"symbol": "币种", "suggested_stop_loss": 价格, "suggested_take_profit": 价格}],
  "think": "简短分析"
}
"""
        else:
            format_guide = "\n请给出JSON决策。position_reviews只为当前持仓提供建议！\n"
        
        prompt += format_guide
        return prompt
    
    def _build_klines_from_series(self, series: Dict, count: int) -> list:
        """
        从时间序列数据构建K线列表
        
        Args:
            series: 时间序列数据字典
            count: 需要的K线数量
            
        Returns:
            K线数据列表
        """
        close_prices = series.get('close_prices', [])
        open_prices = series.get('open_prices', [])
        high_prices = series.get('high_prices', [])
        low_prices = series.get('low_prices', [])
        
        if not all([close_prices, open_prices, high_prices, low_prices]):
            return []
        
        max_count = min(count, len(close_prices), len(open_prices), len(high_prices), len(low_prices))
        if max_count < count:
            return []
        
        klines = []
        for i in range(-max_count, 0):
            klines.append({
                'open': open_prices[i],
                'high': high_prices[i],
                'low': low_prices[i],
                'close': close_prices[i]
            })
        return klines
    
    def _format_coin_section(self, coin: str, price_data: Dict) -> str:
        """格式化单个币种的数据 - 精简但完整的实时数据"""
        try:
            # 数据验证
            if not price_data or not isinstance(price_data, dict):
                return f"[{coin}/USDT]\n数据异常：无法获取有效数据"
            
            tech = price_data.get('technical_data', {})
            series = price_data.get('time_series', {})
            
            # 验证关键数据
            price = price_data.get('price', 0)
            if price == 0 or price is None:
                return f"[{coin}/USDT]\n数据异常：价格数据无效"
            
            # 获取价格变化
            close_prices = series.get('close_prices', [])
            price_change = price_data.get('price_change', 0)
            
            # 根据价格大小动态调整显示精度
            if price < 0.01:
                price_fmt = f"${price:.6f}"  # 小于0.01显示6位小数
            elif price < 1:
                price_fmt = f"${price:.4f}"  # 小于1显示4位小数
            elif price < 100:
                price_fmt = f"${price:,.2f}"  # 小于100显示2位小数
            else:
                price_fmt = f"${price:,.0f}"  # 大于100显示整数
            
            # 获取MA值并动态格式化
            ma5 = tech.get('sma_5', 0)
            ma20 = tech.get('sma_20', 0)
            ma50 = tech.get('sma_50', 0)
            bb_lower = tech.get('bb_lower', 0)
            bb_upper = tech.get('bb_upper', 0)
            
            # 根据价格范围格式化MA和布林带
            if price < 1:
                ma_fmt = lambda x: f"${x:.4f}" if x > 0 else "$0"
            elif price < 100:
                ma_fmt = lambda x: f"${x:,.2f}" if x > 0 else "$0"
            else:
                ma_fmt = lambda x: f"${x:,.0f}" if x > 0 else "$0"
            
            # 计算K线形态（阴阳线）
            current_open = price_data.get('open', price)
            current_close = price
            candle_type = "阳线" if current_close >= current_open else "阴线"
            body_pct = abs(current_close - current_open) / current_open * 100 if current_open > 0 else 0
            
            # 精简格式：单行显示关键指标
            section = f"""[{coin}/USDT]
价格: {price_fmt} (涨跌{price_change:+.2f}%) | 15分钟K线: {candle_type}({body_pct:.2f}%)
15分钟技术: MA5={ma_fmt(ma5)} MA20={ma_fmt(ma20)} MA50={ma_fmt(ma50)}
           RSI={tech.get('rsi', 0):.1f} MACD={tech.get('macd', 0):.4f} 柱={tech.get('macd_histogram', 0):.4f}
           布林带: {ma_fmt(bb_lower)} - {ma_fmt(ma20)} - {ma_fmt(bb_upper)}
           ATR={tech.get('atr_14', 0):.2f} 成交额比率={tech.get('volume_ratio', 0):.1f}x"""
            
            # 添加K线可视化和形态分析
            if close_prices and len(close_prices) >= 3:
                open_prices = series.get('open_prices', [])
                high_prices = series.get('high_prices', [])
                low_prices = series.get('low_prices', [])
                
                # 检查数据完整性
                has_open = open_prices and len(open_prices) >= 3
                has_high = high_prices and len(high_prices) >= 3
                has_low = low_prices and len(low_prices) >= 3
                
                if not has_open or not has_high or not has_low:
                    missing = []
                    if not has_open:
                        missing.append("开盘价")
                    if not has_high:
                        missing.append("最高价")
                    if not has_low:
                        missing.append("最低价")
                    section += f"\n15分钟: K线数据不完整(缺少{', '.join(missing)})"
                else:
                    # 使用公共方法构建K线
                    klines = self._build_klines_from_series(series, 7)
                    
                    if len(klines) >= 3:
                        pattern = format_kline_pattern(klines, count=len(klines))
                        trend = analyze_trend(klines)
                        section += f"\n15分钟K线形态(最近{len(klines)}根，从旧到新): {pattern}"
                        section += f"\n趋势判断: {trend}"
                    else:
                        section += f"\n15分钟: 可用K线数据不足({len(klines)}根)"
            else:
                section += f"\n15分钟: 收盘价数据不足(仅{len(close_prices) if close_prices else 0}根)"
            
            # 4小时趋势
            long_tf = price_data.get('long_timeframe')
            if long_tf and isinstance(long_tf, dict):
                long_tech = long_tf.get('technical_data', {})
                long_series = long_tf.get('time_series', {})
                long_klines = self._build_klines_from_series(long_series, 3)
                
                if len(long_klines) >= 3:
                    long_pattern = format_kline_pattern(long_klines, count=3)
                    long_trend = analyze_trend(long_klines)
                    section += f"\n4小时K线形态(最近3根，从旧到新): {long_pattern}"
                    section += f"\n4小时趋势: {long_trend} | MA20={ma_fmt(long_tech.get('sma_20', 0))} MA50={ma_fmt(long_tech.get('sma_50', 0))} RSI={long_tech.get('rsi', 0):.1f}"
                else:
                    section += "\n4小时: 数据不足"
            
            # 日线趋势
            daily_tf = price_data.get('daily_timeframe')
            if daily_tf and isinstance(daily_tf, dict):
                daily_tech = daily_tf.get('technical_data', {})
                daily_series = daily_tf.get('time_series', {})
                daily_klines = self._build_klines_from_series(daily_series, 7)
                
                if len(daily_klines) >= 7:
                    daily_pattern = format_kline_pattern(daily_klines, count=7)
                    daily_trend = analyze_trend(daily_klines)
                    section += f"\n日线K线形态(最近7根，从旧到新): {daily_pattern}"
                    
                    # RSI可能为NaN
                    daily_rsi = daily_tech.get('rsi', 0)
                    rsi_str = f"{daily_rsi:.1f}" if daily_rsi and not (isinstance(daily_rsi, float) and daily_rsi != daily_rsi) else "N/A"
                    section += f"\n日线趋势: {daily_trend} | MA20={ma_fmt(daily_tech.get('sma_20', 0))} MA50={ma_fmt(daily_tech.get('sma_50', 0))} RSI={rsi_str}"
            
            return section
            
        except Exception as e:
            return f"[{coin}/USDT]\n数据格式化失败: {str(e)}"
    
    def _build_pure_data_prompt(
        self,
        price_data: Dict,
        balance: float,
        position: Optional[Dict]
    ) -> str:
        """
        构建纯数据prompt - 只提供原始数据，不做任何分析
        """
        # 当前时间
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 持仓信息
        if position:
            pos_info = f"""当前持仓:
- 方向: {position.get('side', 'N/A').upper()}
- 数量: {position.get('btc_amount', 0)} BTC
- 开仓价: ${position.get('entry_price', 0):,.2f}
- 当前盈亏: ${position.get('unrealized_pnl', 0):,.2f}"""
        else:
            pos_info = "当前持仓: 无"
        
        # 技术指标（原始数据）
        tech = price_data.get('technical_data', {})
        
        # 时间序列（原始数据）
        series = price_data.get('time_series', {})
        
        # 格式化持仓详情
        position_details = ""
        if position:
            position_details = f"""
持仓详情:
- 开仓订单ID: {position.get('entry_oid', 'N/A')}
- 止盈订单ID: {position.get('tp_oid', 'N/A')}
- 止损订单ID: {position.get('sl_oid', 'N/A')}
- 清算价: ${position.get('liquidation_price', 0):,.2f}
- 杠杆: {position.get('leverage', 10)}x
- 名义价值: ${position.get('notional_usd', 0):,.2f}
- 风险金额: ${position.get('risk_usd', 0):,.2f}
- 退出计划:
  * 止盈目标: ${position.get('exit_plan', {}).get('profit_target', 0):,.2f}
  * 止损价: ${position.get('exit_plan', {}).get('stop_loss', 0):,.2f}
  * 失效条件: {position.get('exit_plan', {}).get('invalidation_condition', 'N/A')}
- 信心度: {position.get('confidence', 0):.0%}"""
        
        # 账户总览（如果有的话）
        account_overview = ""
        if hasattr(self, 'account_stats'):
            stats = self.account_stats
            account_overview = f"""
=== 账户总览 ===
总回报率: {stats.get('total_return_pct', 0):.2f}%
账户总价值: ${stats.get('total_value', 0):,.2f}
夏普比率: {stats.get('sharpe_ratio', 0):.3f}
"""
        
        prompt = f"""【BTC/USDT 永续合约 - {timestamp}】
{account_overview}
账户余额: ${balance:,.2f} USDT
{pos_info}{position_details}

=== 当前K线数据 ===
BTC价格: ${price_data.get('price', 0):,.2f}
最高: ${price_data.get('high', 0):,.2f}
最低: ${price_data.get('low', 0):,.2f}
成交量: {price_data.get('volume', 0):,.2f}
价格变化: {price_data.get('price_change', 0):+.2f}%

=== 技术指标 ===
MA5: ${tech.get('sma_5', 0):,.2f}
MA20: ${tech.get('sma_20', 0):,.2f}
MA50: ${tech.get('sma_50', 0):,.2f}
RSI(14): {tech.get('rsi', 0):.2f}
MACD: {tech.get('macd', 0):.4f}
MACD信号线: {tech.get('macd_signal', 0):.4f}
MACD柱: {tech.get('macd_histogram', 0):.4f}
布林带上轨: ${tech.get('bb_upper', 0):,.2f}
布林带中轨: ${tech.get('sma_20', 0):,.2f}
布林带下轨: ${tech.get('bb_lower', 0):,.2f}
ATR(14): {tech.get('atr_14', 0):.2f}
成交额比率: {tech.get('volume_ratio', 0):.2f}x (USDT计价)

=== 15分钟序列数据（最近10个周期，从旧到新）===
收盘价: {series.get('close_prices', [])[-10:]}
RSI(14): {series.get('rsi', [])[-10:]}
MACD: {series.get('macd', [])[-10:]}
成交额(USDT): {series.get('volume', [])[-10:]}"""
        
        # 添加4小时数据（如果有）
        long_tf = price_data.get('long_timeframe')
        if long_tf:
            long_tech = long_tf.get('technical_data', {})
            long_series = long_tf.get('time_series', {})
            
            prompt += f"""

=== 4小时K线数据（长期趋势）===
当前价格: ${long_tf.get('price', 0):,.2f}
MA20: ${long_tech.get('sma_20', 0):,.2f}
MA50: ${long_tech.get('sma_50', 0):,.2f}
RSI(14): {long_tech.get('rsi', 0):.2f}
MACD: {long_tech.get('macd', 0):.4f}
MACD信号线: {long_tech.get('macd_signal', 0):.4f}
布林带上轨: ${long_tech.get('bb_upper', 0):,.2f}
布林带下轨: ${long_tech.get('bb_lower', 0):,.2f}
ATR(14): {long_tech.get('atr_14', 0):.2f}

4小时序列数据（最近10个周期）:
收盘价: {long_series.get('close_prices', [])[-10:]}
RSI(14): {long_series.get('rsi', [])[-10:]}
MACD: {long_series.get('macd', [])[-10:]}
"""
        
        prompt += """

请给出交易决策（JSON格式）。
"""
        return prompt
    
    def _refresh_system_prompt(self):
        """
        重新加载提示词文件（每次调用AI前执行）
        这样可以在不重启程序的情况下，修改提示词文件后立即生效
        """
        new_prompt = self._load_prompt_from_file(self.current_strategy, silent=True)
        
        # 只有当提示词内容发生变化时才更新
        if new_prompt != self.system_prompt:
            self.system_prompt = new_prompt
            # 更新对话历史中的system消息
            self.conversation_history[0]['content'] = new_prompt
            print(f"🔄 提示词已更新（{len(new_prompt)} 字符）")
    
    def _call_ai(self) -> str:
        """调用AI"""
        try:
            # 每次调用前重新加载提示词（确保使用最新的提示词文件）
            # 注意：这会增加IO开销，但确保提示词实时更新
            self._refresh_system_prompt()
            
            # 只发送最近的对话（避免token过多）
            # DeepSeek建议：保持对话历史在合理范围内（10-15轮）
            messages_to_send = self._get_recent_messages(max_messages=15)
            
            response = self.ai_client.chat.completions.create(
                model="deepseek-chat",
                messages=messages_to_send,
                temperature=0.7,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            
            # 记录token使用
            if hasattr(response, 'usage'):
                self._last_tokens = response.usage.total_tokens
            
            return content
            
        except Exception as e:
            print(f"AI调用失败: {e}")
            return '{"primary_action": {"symbol": "NONE", "signal": "HOLD", "confidence": "LOW", "reason": "AI调用失败"}, "position_reviews": [], "think": "AI调用异常"}'
    
    def _parse_ai_response(self, response: str) -> Dict:
        """解析AI回复，支持新旧格式"""
        try:
            # 尝试提取JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                raw_decision = json.loads(json_match.group())
            else:
                # 如果没有JSON，返回HOLD
                return {
                    'symbol': 'NONE',
                    'signal': 'HOLD',
                    'confidence': 'LOW',
                    'reason': 'AI未返回有效JSON',
                    'tokens_used': getattr(self, '_last_tokens', 0),
                    'raw_response': response
                }
            
            # 兼容新旧格式
            if 'primary_action' in raw_decision:
                # 新格式：有primary_action和position_reviews
                primary = raw_decision.get('primary_action', {})
                decision = {
                    'symbol': primary.get('symbol', 'NONE'),
                    'signal': primary.get('signal', 'HOLD'),
                    'confidence': primary.get('confidence', 'LOW'),
                    'reason': primary.get('reason', ''),
                    'stop_loss': primary.get('stop_loss'),
                    'take_profit': primary.get('take_profit'),
                    'amount': primary.get('amount'),
                    'position_reviews': raw_decision.get('position_reviews', []),
                    'think': raw_decision.get('think', '')
                }
            else:
                # 旧格式：直接使用
                decision = raw_decision
            
            # 添加token信息
            decision['tokens_used'] = getattr(self, '_last_tokens', 0)
            decision['raw_response'] = response
            
            return decision
            
        except Exception as e:
            print(f"解析AI回复失败: {e}")
            return {
                'symbol': 'NONE',
                'signal': 'HOLD',
                'confidence': 'LOW',
                'reason': f'解析失败: {str(e)}',
                'raw_response': response,
                'tokens_used': getattr(self, '_last_tokens', 0)
            }
    
    def _get_recent_messages(self, max_messages: int = 15) -> list:
        """
        获取最近的消息（避免token过多）
        
        根据DeepSeek最佳实践：
        - System消息始终包含（包含全局规则和策略）
        - 保留最近10-15轮对话（足够AI理解上下文）
        - 每轮对话 = user + assistant 两条消息
        
        Args:
            max_messages: 最多保留多少条user/assistant消息（不含system）
        """
        # 始终包含system消息
        system_msg = [self.conversation_history[0]]
        
        # 加上最近的对话（max_messages条user/assistant消息）
        recent = self.conversation_history[1:][-max_messages:]
        
        return system_msg + recent
    
    def _manage_conversation_history(self):
        """管理对话历史长度"""
        # 如果对话太长，保留system + 最近30轮
        if len(self.conversation_history) > 62:  # system + 30轮 * 2
            print("📦 对话历史过长，进行压缩...")
            system_msg = self.conversation_history[0]
            recent_msgs = self.conversation_history[-60:]  # 保留最近30轮
            self.conversation_history = [system_msg] + recent_msgs
            print(f"压缩完成，保留{len(self.conversation_history)}条消息")
    
    def _get_default_system_prompt(self) -> str:
        """
        获取默认系统提示词（备用）
        当提示词文件不存在时使用这个内置提示词
        """
        return """
你是一个专业的加密货币交易AI助手。

你的任务是分析市场数据并做出交易决策。

请根据提供的市场数据、技术指标和历史交易记录，给出你的交易建议。

注意：
1. 每笔交易都有约0.3-0.4%的成本（手续费+滑点）
2. 止盈目标必须至少1.5%才能覆盖成本
3. 不要频繁交易，避免过度交易
4. 严格遵守风险管理原则
"""
    
    def _load_prompt_from_file(self, strategy_name: str, silent: bool = False) -> str:
        """
        从prompts目录加载提示词文件
        
        Args:
            strategy_name: 策略名称（对应txt文件名）
            silent: 是否静默模式（不打印日志）
        
        Returns:
            提示词内容
        """
        import os
        
        # 全局交易成本说明（所有策略共享）
        global_context = """[全局交易规则]

交易成本说明（必须严格遵守）：
每笔交易都有手续费和滑点成本，这是真实的资金损耗！
- 开仓手续费：约0.05%（Taker）
- 平仓手续费：约0.05%（Taker）
- 滑点成本：约0.2%（市场波动导致）
- 总成本：单次完整交易约0.3-0.4%

止盈目标必须覆盖成本（这是硬性要求）：
- 最小止盈：1.5%（覆盖0.3%成本后，净利润1.2%）
- 震荡市止盈：2-3%（覆盖成本后，净利润1.7-2.7%）
- 趋势市止盈：5-10%（覆盖成本后，净利润4.7-9.7%）

持仓评估规则（重要！必读！）：
对于已有持仓，必须理解：
1. 开仓时已支付手续费0.05%，这是沉没成本
2. 当前价格即使高于开仓价，也可能是亏损状态！
3. 只有当前价格 > 开仓价 * 1.005（覆盖开仓手续费）才开始盈利
4. 如果要平仓，还需支付0.05%手续费，所以需要涨幅>0.1%才能保本
5. 加上滑点0.2%，实际需要涨幅>0.4%才能真正保本

错误示例（必须避免）：
- 开仓价$185.72，当前价$186.46
- 涨幅：(186.46-185.72)/185.72 = 0.40%
- 但已支付开仓费0.05%，实际浮盈仅0.35%
- 如果平仓，还要付0.05%手续费 + 0.2%滑点 = 0.25%
- 最终：0.35% - 0.25% = 0.10%（几乎没有利润）
- 所以虽然价格涨了0.4%，但实际利润微薄！

正确示例：
- 开仓价$185.72，当前价$188.50
- 涨幅：(188.50-185.72)/185.72 = 1.50%
- 扣除开仓费0.05% + 平仓费0.05% + 滑点0.2% = 0.3%
- 净利润：1.50% - 0.3% = 1.2%（值得交易）

调整止盈规则：
- 如果当前涨幅<1.5%，说明还未真正盈利，止盈必须设在开仓价+1.5%以上
- 如果当前涨幅>1.5%，可以移动止盈，但必须保证至少锁定1.2%净利润
- 不要为了0.1-0.2%的微薄利润平仓，这样扣除成本后几乎白做

---

"""
        
        # 构建文件路径（项目根目录的prompts文件夹）
        current_dir = os.path.dirname(__file__)  # ai/
        project_root = os.path.dirname(current_dir)  # 项目根目录
        prompts_dir = os.path.join(project_root, 'prompts')
        prompt_file = os.path.join(prompts_dir, f'{strategy_name}.txt')
        
        # if not silent:
        #     # print(f"[调试] DEBUG: 尝试加载文件: {prompt_file}")
        #     # print(f"[调试] DEBUG: 文件是否存在: {os.path.exists(prompt_file)}")
        
        try:
            if os.path.exists(prompt_file):
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    prompt = f.read()
                if not silent:
                    print(f"已加载提示词文件: prompts/{strategy_name}.txt")
                    # print(f"[调试] DEBUG: 文件内容长度: {len(prompt)} 字符")
                # 在策略提示词前添加全局上下文
                return global_context + prompt
            else:
                if not silent:
                    print(f"警告：提示词文件不存在: {prompt_file}")
                    print(f"   使用内置默认提示词")
                return self._get_default_system_prompt()
        except Exception as e:
            if not silent:
                print(f"加载提示词文件失败: {e}")
                print(f"   使用内置默认提示词")
            return self._get_default_system_prompt()
    
    def switch_strategy(self, strategy_name: str):
        """
        切换交易策略（从prompts目录加载）
        
        Args:
            strategy_name: 策略名称（对应txt文件名）
        """
        print(f"\n🔄 切换策略: {strategy_name}")
        
        new_prompt = self._load_prompt_from_file(strategy_name)
        self.system_prompt = new_prompt
        self.current_strategy = strategy_name
        
        # 更新对话历史中的system消息
        self.conversation_history[0]['content'] = new_prompt
        
        print(f"策略已切换: {strategy_name}")
        print(f"新提示词长度: {len(new_prompt)} 字符\n")
    
    def list_available_strategies(self):
        """列出prompts目录中所有可用的策略"""
        import os
        
        prompts_dir = os.path.join(os.path.dirname(__file__), 'prompts')
        
        if not os.path.exists(prompts_dir):
            print(f"提示词目录不存在: {prompts_dir}")
            return
        
        print("\n" + "="*70)
        print("📋 可用AI交易策略")
        print("="*70)
        
        # 策略描述
        descriptions = {
            'default': '默认策略 - 平衡风险收益（5-10%止盈，2-3%止损）',
            'stable_profit': '稳定盈利 - 小资金稳定增长（3%止盈，1.5%止损）',
            'aggressive': '激进策略 - 追求高收益（7%止盈，2.5%止损）',
            'balanced': '平衡策略 - 稳健增长（5%止盈，2%止损）',
        }
        
        # 列出所有.txt文件
        files = [f for f in os.listdir(prompts_dir) if f.endswith('.txt')]
        
        if not files:
            print("\n警告：没有找到任何提示词文件")
            print("="*70 + "\n")
            return
        
        for filename in sorted(files):
            strategy_name = filename[:-4]  # 去掉.txt后缀
            desc = descriptions.get(strategy_name, '自定义策略')
            filepath = os.path.join(prompts_dir, filename)
            
            # 读取文件大小
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    size = len(content)
                
                # 标记当前策略
                current_mark = " ← 当前" if strategy_name == self.current_strategy else ""
                
                print(f"\n[{strategy_name}]{current_mark}")
                print(f"   描述: {desc}")
                print(f"   文件: prompts/{filename}")
                print(f"   大小: {size} 字符")
            except:
                print(f"\n[{strategy_name}]")
                print(f"   文件: prompts/{filename}")
                print(f"   警告：无法读取文件")
        
        print("\n" + "="*70)
        print("使用方法：")
        print("  trader = PureAITrader(ai_client, strategy='stable_profit')")
        print("  或运行时切换: trader.switch_strategy('aggressive')")
        print("="*70 + "\n")
    
    def get_current_strategy(self) -> str:
        """获取当前策略名称"""
        return self.current_strategy
    
    def update_system_prompt(self, new_prompt: str):
        """更新系统提示词"""
        self.system_prompt = new_prompt
        self.conversation_history[0]['content'] = new_prompt
        self.current_strategy = 'custom'
        print(f"系统提示词已更新（{len(new_prompt)}字符）")
    
    def _fetch_recent_trades_from_api(self, limit: int = 5, current_symbols: list = None) -> list:
        """从API获取最近的成交记录（使用fetch_my_trades）
        
        Args:
            limit: 返回的交易数量
            current_symbols: 当前持仓的symbol列表，这些币种的历史交易也会被包含
        """
        try:
            from utils.data_fetcher import DataFetcher
            from datetime import datetime, timedelta
            
            data_fetcher = DataFetcher()
            all_trades_list = []
            current_symbols = current_symbols or []
            
            # 获取所有币种的成交记录
            for symbol in TRADING_CONFIG['symbols']:
                try:
                    # 使用fetch_my_trades获取实际成交
                    trades = data_fetcher.exchange.fetch_my_trades(
                        symbol=symbol,
                        since=int((datetime.now() - timedelta(days=7)).timestamp() * 1000),
                        limit=100
                    )
                    
                    if not trades:
                        continue
                    
                    # 分离开仓和平仓成交
                    open_trades = []  # fillPnl为0的是开仓
                    close_trades = []  # fillPnl不为0的是平仓
                    
                    for trade in trades:
                        fill_pnl = trade.get('info', {}).get('fillPnl', '0')
                        if not fill_pnl or fill_pnl == '0':
                            open_trades.append(trade)
                        else:
                            close_trades.append(trade)
                    
                    # 处理平仓成交
                    for close_trade in close_trades:
                        try:
                            pnl = float(close_trade.get('info', {}).get('fillPnl', '0'))
                        except:
                            continue
                        
                        close_price = close_trade['price']
                        amount = close_trade['amount']
                        pos_side = close_trade.get('info', {}).get('posSide')
                        side = 'BUY' if pos_side == 'long' else 'SELL'
                        close_time = datetime.fromtimestamp(close_trade['timestamp'] / 1000)
                        
                        # 尝试找到对应的开仓成交（最近的、同方向的）
                        entry_price = 0
                        open_time = None
                        for open_trade in reversed(open_trades):
                            if (open_trade.get('info', {}).get('posSide') == pos_side and
                                open_trade['timestamp'] < close_trade['timestamp']):
                                entry_price = open_trade['price']
                                open_time = datetime.fromtimestamp(open_trade['timestamp'] / 1000)
                                break
                        
                        # 计算持仓时长
                        duration_seconds = 0
                        if open_time:
                            duration_seconds = (close_time - open_time).total_seconds()
                        
                        # 计算百分比
                        if entry_price > 0:
                            if pos_side == 'long':
                                pnl_pct = ((close_price - entry_price) / entry_price) * 100
                            else:
                                pnl_pct = ((entry_price - close_price) / entry_price) * 100
                        else:
                            # 如果没有开仓价，用名义价值估算
                            nominal_value = close_price * amount * 10
                            pnl_pct = (pnl / nominal_value) * 100 if nominal_value > 0 else 0
                        
                        all_trades_list.append({
                            'symbol': symbol,
                            'signal': side,
                            'entry_price': entry_price,
                            'exit_price': close_price,
                            'realized_pnl': pnl,
                            'pnl_percent': pnl_pct,
                            'holding_duration_seconds': duration_seconds,
                            'close_time': close_time,
                            'quantity': amount
                        })
                
                except Exception as e:
                    continue
            
            # 按平仓时间排序，返回最近的N笔
            all_trades_list.sort(key=lambda x: x['close_time'], reverse=True)
            return all_trades_list[:limit]
            
        except Exception as e:
            return []
    
    
    def _format_duration(self, seconds: float) -> str:
        """格式化持仓时长"""
        if not seconds or seconds <= 0:
            return "N/A"
        if seconds < 60:
            return f"{seconds:.0f}秒"
        elif seconds < 3600:
            return f"{seconds/60:.1f}分钟"
        elif seconds < 86400:
            return f"{seconds/3600:.1f}小时"
        else:
            return f"{seconds/86400:.1f}天"
    
    def set_account_stats(
        self, 
        total_return_pct: float,
        available_cash: float,
        total_value: float,
        all_positions: list = None
    ):
        """设置账户统计信息"""
        self.account_stats = {
            'total_return_pct': total_return_pct,
            'available_cash': available_cash,
            'total_value': total_value,
            'all_positions': all_positions or []
        }
    
    def get_conversation_stats(self) -> Dict:
        """获取对话统计"""
        return {
            'total_messages': len(self.conversation_history),
            'total_rounds': (len(self.conversation_history) - 1) // 2,
            'system_prompt_length': len(self.system_prompt)
        }


if __name__ == "__main__":
    # 测试代码
    from openai import OpenAI
    from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
    
    print("=== 测试纯AI交易器 ===\n")
    
    # 初始化
    ai_client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL
    )
    
    trader = PureAITrader(ai_client)
    
    # 执行分析
    decision = trader.analyze_and_decide(
        price_data=price_data,
        account_balance=13654.1,
        current_position=None
    )
    
    print("\n" + "="*70)
    print("AI决策结果:")
    print(f"信号: {decision.get('signal')}")
    print(f"信心度: {decision.get('confidence')}")
    print(f"理由: {decision.get('reason')}")
    print(f"止损: {decision.get('stop_loss')}")
    print(f"止盈: {decision.get('take_profit')}")
    print(f"数量: {decision.get('amount')}")
    
    # 统计
    stats = trader.get_conversation_stats()
    print(f"\n对话统计: {stats}")
