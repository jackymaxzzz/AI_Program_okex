"""
MCP集成模块 - 为AI交易系统提供记忆和学习能力
"""
from typing import Dict, List, Optional
from datetime import datetime
import json


__all__ = [
    'MCPTradingMemory',
    'MCPFileSystem',
    'MCPAnalytics',
    'MCPIntelligence',
    'MarketStateAnalyzer'
]


class MCPTradingMemory:
    """
    使用MCP管理交易记忆
    保存最近的交易经验，供AI学习
    支持长期记忆和短期记忆
    """
    
    def __init__(self, max_trades: int = 50, max_long_term: int = 200):
        """
        初始化交易记忆
        
        Args:
            max_trades: 短期记忆的最大交易数量（每种类型）
            max_long_term: 长期记忆的最大交易数量
        """
        self.max_trades = max_trades
        self.max_long_term = max_long_term
        
        # 短期记忆（最近的交易，用于快速学习）
        self.successful_trades = []  # 成功的交易
        self.failed_trades = []  # 失败的交易
        
        # 长期记忆（重要的经验教训）
        self.long_term_lessons = []  # 长期经验教训
        self.critical_mistakes = []  # 关键错误记录
        self.best_practices = []  # 最佳实践
        
        # 统计记忆
        self.market_patterns = {}  # 市场形态记忆
        self.strategy_stats = {}  # 策略统计
        self.symbol_performance = {}  # 各币种表现
        
        self.enabled = True
    
    def record_successful_trade(self, trade_info: Dict):
        """
        记录成功的交易，提取经验
        
        Args:
            trade_info: 交易信息字典
        """
        if not self.enabled:
            return
            
        try:
            symbol = trade_info.get('symbol', 'UNKNOWN')
            pnl_pct = trade_info.get('pnl_percent', 0)
            market_state = trade_info.get('market_state', 'unknown')
            strategy = trade_info.get('strategy', 'unknown')
            
            # 创建成功交易记录
            record = {
                'symbol': symbol,
                'pnl_percent': pnl_pct,
                'market_state': market_state,
                'strategy': strategy,
                'timestamp': datetime.now().isoformat(),
                'observation': (
                    f"[完成] {symbol}成功交易: 盈利{pnl_pct:.2f}%, "
                    f"市场状态={market_state}, 策略={strategy}"
                )
            }
            
            # 存储到本地（模拟MCP）
            self.successful_trades.append(record)
            
            # 更新策略统计
            if strategy not in self.strategy_stats:
                self.strategy_stats[strategy] = {
                    'total': 0,
                    'wins': 0,
                    'losses': 0,
                    'total_pnl': 0
                }
            self.strategy_stats[strategy]['total'] += 1
            self.strategy_stats[strategy]['wins'] += 1
            self.strategy_stats[strategy]['total_pnl'] += pnl_pct
            
            # 保持最近50条记录
            if len(self.successful_trades) > 50:
                self.successful_trades = self.successful_trades[-50:]
            
        except Exception as e:
            print(f"[警告] MCP记录成功交易失败: {e}")
    
    def record_failed_trade(self, trade_info: Dict):
        """
        记录失败的交易，提取教训
        
        Args:
            trade_info: 交易信息字典
        """
        if not self.enabled:
            return
            
        try:
            symbol = trade_info.get('symbol', 'UNKNOWN')
            pnl_pct = trade_info.get('pnl_percent', 0)
            market_state = trade_info.get('market_state', 'unknown')
            strategy = trade_info.get('strategy', 'unknown')
            reason = trade_info.get('close_reason', 'unknown')
            
            # 创建失败交易记录
            record = {
                'symbol': symbol,
                'pnl_percent': pnl_pct,
                'market_state': market_state,
                'strategy': strategy,
                'reason': reason,
                'timestamp': datetime.now().isoformat(),
                'observation': (
                    f"❌ {symbol}失败交易: 亏损{abs(pnl_pct):.2f}%, "
                    f"市场状态={market_state}, 策略={strategy}, 原因={reason}"
                )
            }
            
            # 存储到本地（模拟MCP）
            self.failed_trades.append(record)
            
            # 更新策略统计
            if strategy not in self.strategy_stats:
                self.strategy_stats[strategy] = {
                    'total': 0,
                    'wins': 0,
                    'losses': 0,
                    'total_pnl': 0
                }
            self.strategy_stats[strategy]['total'] += 1
            self.strategy_stats[strategy]['losses'] += 1
            self.strategy_stats[strategy]['total_pnl'] += pnl_pct
            
            # 保持最近50条记录
            if len(self.failed_trades) > 50:
                self.failed_trades = self.failed_trades[-50:]
            
        except Exception as e:
            print(f"[警告] MCP记录失败交易失败: {e}")
    
    def add_long_term_lesson(self, lesson: Dict):
        """
        添加长期经验教训
        
        Args:
            lesson: 经验教训字典，包含type, content, importance等
        """
        if not self.enabled:
            return
        
        try:
            lesson_record = {
                'type': lesson.get('type', 'general'),  # general, strategy, risk, market
                'content': lesson.get('content', ''),
                'importance': lesson.get('importance', 'medium'),  # low, medium, high, critical
                'timestamp': datetime.now().isoformat(),
                'related_trades': lesson.get('related_trades', []),
                'conditions': lesson.get('conditions', '')  # 适用条件
            }
            
            self.long_term_lessons.append(lesson_record)
            
            # 保持最重要的记忆
            if len(self.long_term_lessons) > self.max_long_term:
                # 按重要性排序，保留最重要的
                importance_order = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
                self.long_term_lessons.sort(
                    key=lambda x: importance_order.get(x.get('importance', 'medium'), 2),
                    reverse=True
                )
                self.long_term_lessons = self.long_term_lessons[:self.max_long_term]
            
        except Exception as e:
            print(f"[警告] 添加长期教训失败: {e}")
    
    def add_critical_mistake(self, mistake: Dict):
        """
        记录关键错误（永久记忆）
        
        Args:
            mistake: 错误信息字典
        """
        if not self.enabled:
            return
        
        try:
            mistake_record = {
                'description': mistake.get('description', ''),
                'loss_percent': mistake.get('loss_percent', 0),
                'what_went_wrong': mistake.get('what_went_wrong', ''),
                'how_to_avoid': mistake.get('how_to_avoid', ''),
                'timestamp': datetime.now().isoformat()
            }
            
            self.critical_mistakes.append(mistake_record)
            
            # 关键错误永久保留，但限制数量
            if len(self.critical_mistakes) > 50:
                self.critical_mistakes = self.critical_mistakes[-50:]
                
        except Exception as e:
            print(f"[警告] 记录关键错误失败: {e}")
    
    def add_best_practice(self, practice: Dict):
        """
        记录最佳实践（永久记忆）
        
        Args:
            practice: 最佳实践字典
        """
        if not self.enabled:
            return
        
        try:
            practice_record = {
                'title': practice.get('title', ''),
                'description': practice.get('description', ''),
                'success_rate': practice.get('success_rate', 0),
                'avg_profit': practice.get('avg_profit', 0),
                'conditions': practice.get('conditions', ''),
                'timestamp': datetime.now().isoformat()
            }
            
            self.best_practices.append(practice_record)
            
            # 保留最有效的实践
            if len(self.best_practices) > 30:
                self.best_practices.sort(
                    key=lambda x: x.get('success_rate', 0) * x.get('avg_profit', 0),
                    reverse=True
                )
                self.best_practices = self.best_practices[:30]
                
        except Exception as e:
            print(f"[警告] 记录最佳实践失败: {e}")
    
    def record_market_pattern(self, symbol: str, pattern: Dict):
        """
        记录识别到的市场模式
        
        Args:
            symbol: 币种
            pattern: 模式信息
        """
        if not self.enabled:
            return
            
        try:
            pattern_type = pattern.get('type', 'unknown')
            indicators = pattern.get('indicators', {})
            
            observation = (
                f"市场模式: {symbol}, 类型={pattern_type}, "
                f"指标={indicators}, "
                f"时间={datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            
            # 存储到MCP Memory
            # self.mcp_client.add_observation(...)
            
        except Exception as e:
            print(f"[警告] MCP记录市场模式失败: {e}")
    
    def get_trading_insights(self, symbol: str) -> Optional[str]:
        """
        获取针对特定币种的交易洞察
        
        Args:
            symbol: 币种
            
        Returns:
            交易洞察文本
        """
        if not self.enabled:
            return None
            
        try:
            insights = []
            
            # 统计该币种的交易记录
            symbol_wins = [t for t in self.successful_trades if t['symbol'] == symbol]
            symbol_losses = [t for t in self.failed_trades if t['symbol'] == symbol]
            
            total = len(symbol_wins) + len(symbol_losses)
            if total == 0:
                return None
            
            win_rate = len(symbol_wins) / total * 100
            avg_win = sum(t['pnl_percent'] for t in symbol_wins) / len(symbol_wins) if symbol_wins else 0
            avg_loss = sum(t['pnl_percent'] for t in symbol_losses) / len(symbol_losses) if symbol_losses else 0
            
            insights.append(f"\n🧠 {symbol}的历史交易经验:")
            insights.append(f"   总交易: {total}笔, 胜率: {win_rate:.1f}%")
            if symbol_wins:
                insights.append(f"   平均盈利: {avg_win:.2f}%")
            if symbol_losses:
                insights.append(f"   平均亏损: {avg_loss:.2f}%")
            
            # 最近的失败教训
            recent_losses = symbol_losses[-3:] if len(symbol_losses) > 0 else []
            if recent_losses:
                insights.append(f"   [警告] 最近失败:")
                for loss in recent_losses:
                    insights.append(f"      - {loss['observation']}")
            
            # 成功经验
            recent_wins = symbol_wins[-3:] if len(symbol_wins) > 0 else []
            if recent_wins:
                insights.append(f"   [完成] 最近成功:")
                for win in recent_wins:
                    insights.append(f"      - {win['observation']}")
            
            return "\n".join(insights)
            
        except Exception as e:
            print(f"[警告] MCP获取交易洞察失败: {e}")
            return None
    
    def get_long_term_insights(self) -> Optional[str]:
        """
        获取长期记忆洞察
        
        Returns:
            长期记忆洞察文本
        """
        if not self.enabled:
            return None
        
        try:
            insights = []
            
            # 关键错误提醒
            if self.critical_mistakes:
                insights.append("\n[重要] 关键错误记录（永远不要重复）:")
                for mistake in self.critical_mistakes[-5:]:  # 最近5个
                    insights.append(f"   ❌ {mistake['description']}")
                    insights.append(f"      原因: {mistake['what_went_wrong']}")
                    insights.append(f"      避免方法: {mistake['how_to_avoid']}")
            
            # 最佳实践
            if self.best_practices:
                insights.append("\n[完成] 最佳实践（优先使用）:")
                for practice in self.best_practices[:5]:  # 前5个最好的
                    insights.append(f"   📌 {practice['title']}")
                    insights.append(f"      {practice['description']}")
                    insights.append(f"      成功率: {practice['success_rate']:.1f}%, 平均盈利: {practice['avg_profit']:.2f}%")
                    if practice['conditions']:
                        insights.append(f"      适用条件: {practice['conditions']}")
            
            # 长期教训
            if self.long_term_lessons:
                # 按重要性分类
                critical_lessons = [l for l in self.long_term_lessons if l['importance'] == 'critical']
                high_lessons = [l for l in self.long_term_lessons if l['importance'] == 'high']
                
                if critical_lessons:
                    insights.append("\n[警告] 关键教训:")
                    for lesson in critical_lessons[:3]:
                        insights.append(f"   [错误] {lesson['content']}")
                        if lesson['conditions']:
                            insights.append(f"      条件: {lesson['conditions']}")
                
                if high_lessons:
                    insights.append("\n[建议] 重要经验:")
                    for lesson in high_lessons[:3]:
                        insights.append(f"   🟡 {lesson['content']}")
            
            return "\n".join(insights) if insights else None
            
        except Exception as e:
            print(f"[警告] 获取长期洞察失败: {e}")
            return None
    
    def get_strategy_performance(self, strategy: str) -> Optional[Dict]:
        """
        获取特定策略的历史表现
        
        Args:
            strategy: 策略名称（如"趋势跟随"、"震荡高抛低吸"）
            
        Returns:
            策略表现统计
        """
        if not self.enabled:
            return None
            
        try:
            if strategy not in self.strategy_stats:
                return None
            
            stats = self.strategy_stats[strategy]
            win_rate = (stats['wins'] / stats['total'] * 100) if stats['total'] > 0 else 0
            avg_pnl = (stats['total_pnl'] / stats['total']) if stats['total'] > 0 else 0
            
            return {
                'strategy': strategy,
                'total_trades': stats['total'],
                'wins': stats['wins'],
                'losses': stats['losses'],
                'win_rate': win_rate,
                'avg_pnl': avg_pnl,
                'total_pnl': stats['total_pnl']
            }
            
        except Exception as e:
            print(f"[警告] MCP获取策略表现失败: {e}")
            return None
    
    def get_all_insights(self) -> str:
        """
        获取所有交易洞察的总结
        
        Returns:
            洞察总结文本
        """
        if not self.enabled:
            return ""
        
        try:
            insights = []
            
            # 总体统计
            total_trades = len(self.successful_trades) + len(self.failed_trades)
            if total_trades == 0:
                return ""
            
            win_rate = len(self.successful_trades) / total_trades * 100
            
            insights.append("\n" + "="*50)
            insights.append("🧠 MCP记忆系统 - 交易经验总结")
            insights.append("="*50)
            insights.append(f"总交易记录: {total_trades}笔")
            insights.append(f"总体胜率: {win_rate:.1f}%")
            
            # 策略表现
            if self.strategy_stats:
                insights.append("\n[数据] 策略表现:")
                for strategy, stats in self.strategy_stats.items():
                    s_win_rate = (stats['wins'] / stats['total'] * 100) if stats['total'] > 0 else 0
                    insights.append(f"   {strategy}: {stats['total']}笔, 胜率{s_win_rate:.1f}%, 累计{stats['total_pnl']:+.2f}%")
            
            return "\n".join(insights)
            
        except Exception as e:
            print(f"[警告] MCP获取总体洞察失败: {e}")
            return ""


class MCPFileSystem:
    """
    使用MCP Filesystem Server管理交易日志和数据文件
    """
    
    def __init__(self, base_path: str = None):
        """
        初始化MCP文件系统
        
        Args:
            base_path: 基础路径
        """
        self.base_path = base_path or "/Users/Jackymax_1/Desktop/alpha-arena/multi_agent_trading"
        self.enabled = True
        
    def save_trade_log(self, log_content: str, filename: str = None):
        """
        保存交易日志
        
        Args:
            log_content: 日志内容
            filename: 文件名（可选，默认使用日期）
        """
        if not self.enabled:
            return
        
        try:
            import os
            from datetime import datetime
            
            # 确保logs目录存在
            logs_dir = os.path.join(self.base_path, 'logs')
            os.makedirs(logs_dir, exist_ok=True)
            
            # 生成文件名
            if not filename:
                filename = f"trade_{datetime.now().strftime('%Y%m%d')}.log"
            
            filepath = os.path.join(logs_dir, filename)
            
            # 追加写入日志
            with open(filepath, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"\n[{timestamp}]\n{log_content}\n")
            
            print(f"📝 日志已保存: {filename}")
            
        except Exception as e:
            print(f"[警告] 保存日志失败: {e}")
    
    def save_decision_log(self, decision: Dict):
        """
        保存AI决策日志
        
        Args:
            decision: AI决策字典
        """
        if not self.enabled:
            return
        
        try:
            import os
            from datetime import datetime
            
            # 确保logs目录存在
            logs_dir = os.path.join(self.base_path, 'logs')
            os.makedirs(logs_dir, exist_ok=True)
            
            # 生成文件名
            filename = f"decisions_{datetime.now().strftime('%Y%m%d')}.jsonl"
            filepath = os.path.join(logs_dir, filename)
            
            # 追加写入决策（JSONL格式）
            with open(filepath, 'a', encoding='utf-8') as f:
                decision['timestamp'] = datetime.now().isoformat()
                f.write(json.dumps(decision, ensure_ascii=False) + '\n')
            
        except Exception as e:
            print(f"[警告] 保存决策日志失败: {e}")
    
    def save_daily_report(self, report_content: str):
        """
        保存每日交易报告
        
        Args:
            report_content: 报告内容
        """
        if not self.enabled:
            return
        
        try:
            import os
            from datetime import datetime
            
            # 确保reports目录存在
            reports_dir = os.path.join(self.base_path, 'reports')
            os.makedirs(reports_dir, exist_ok=True)
            
            # 生成文件名
            filename = f"report_{datetime.now().strftime('%Y%m%d')}.md"
            filepath = os.path.join(reports_dir, filename)
            
            # 写入报告
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            print(f"[数据] 报告已保存: {filename}")
            
        except Exception as e:
            print(f"[警告] 保存报告失败: {e}")
    
    def load_recent_logs(self, days: int = 7) -> List[str]:
        """
        加载最近N天的日志
        
        Args:
            days: 天数
            
        Returns:
            日志内容列表
        """
        if not self.enabled:
            return []
        
        try:
            import os
            from datetime import datetime, timedelta
            
            logs_dir = os.path.join(self.base_path, 'logs')
            if not os.path.exists(logs_dir):
                return []
            
            logs = []
            start_date = datetime.now() - timedelta(days=days)
            
            for filename in os.listdir(logs_dir):
                if filename.startswith('trade_') and filename.endswith('.log'):
                    filepath = os.path.join(logs_dir, filename)
                    file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                    
                    if file_time >= start_date:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            logs.append(f.read())
            
            return logs
            
        except Exception as e:
            print(f"[警告] 加载日志失败: {e}")
            return []
    
    def export_mcp_memory(self, memory: MCPTradingMemory):
        """
        导出MCP记忆到文件
        
        Args:
            memory: MCP记忆实例
        """
        if not self.enabled:
            return
        
        try:
            import os
            from datetime import datetime
            
            # 确保data目录存在
            data_dir = os.path.join(self.base_path, 'data')
            os.makedirs(data_dir, exist_ok=True)
            
            # 导出数据（包含长期记忆）
            export_data = {
                'export_time': datetime.now().isoformat(),
                'successful_trades': memory.successful_trades,
                'failed_trades': memory.failed_trades,
                'long_term_lessons': memory.long_term_lessons,
                'critical_mistakes': memory.critical_mistakes,
                'best_practices': memory.best_practices,
                'market_patterns': memory.market_patterns,
                'strategy_stats': memory.strategy_stats,
                'symbol_performance': memory.symbol_performance
            }
            
            filename = f"mcp_memory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(data_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            print(f"💾 MCP记忆已导出: {filename}")
            
        except Exception as e:
            print(f"[警告] 导出MCP记忆失败: {e}")
    
    def import_mcp_memory(self, memory: MCPTradingMemory, filename: str = None):
        """
        从文件导入MCP记忆
        
        Args:
            memory: MCP记忆实例
            filename: 文件名（可选，默认使用最新的）
        """
        if not self.enabled:
            return
        
        try:
            import os
            
            data_dir = os.path.join(self.base_path, 'data')
            if not os.path.exists(data_dir):
                # 首次运行，数据目录不存在是正常的
                print("📂 首次运行，将创建新的MCP记忆")
                return
            
            # 如果没有指定文件名，使用最新的
            if not filename:
                files = [f for f in os.listdir(data_dir) if f.startswith('mcp_memory_') and f.endswith('.json')]
                if not files:
                    # 没有历史记忆文件，这也是正常的
                    print("📂 没有找到历史记忆，将创建新的MCP记忆")
                    return
                files.sort(reverse=True)
                filename = files[0]
            
            filepath = os.path.join(data_dir, filename)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # 导入数据（包含长期记忆）
            memory.successful_trades = import_data.get('successful_trades', [])
            memory.failed_trades = import_data.get('failed_trades', [])
            memory.long_term_lessons = import_data.get('long_term_lessons', [])
            memory.critical_mistakes = import_data.get('critical_mistakes', [])
            memory.best_practices = import_data.get('best_practices', [])
            memory.market_patterns = import_data.get('market_patterns', {})
            memory.strategy_stats = import_data.get('strategy_stats', {})
            memory.symbol_performance = import_data.get('symbol_performance', {})
            
            total_trades = len(memory.successful_trades) + len(memory.failed_trades)
            total_long_term = len(memory.long_term_lessons) + len(memory.critical_mistakes) + len(memory.best_practices)
            
            if total_trades > 0 or total_long_term > 0:
                print(f"MCP记忆已导入: {filename}")
                print(f"   [完成] 成功交易: {len(memory.successful_trades)}笔")
                print(f"   失败交易: {len(memory.failed_trades)}笔")
                print(f"   [数据] 总计: {total_trades}笔交易经验已加载")
                if total_long_term > 0:
                    print(f"   🧠 长期记忆: {len(memory.long_term_lessons)}条教训, {len(memory.critical_mistakes)}个关键错误, {len(memory.best_practices)}个最佳实践")
            
        except Exception as e:
            print(f"[警告] 导入MCP记忆失败: {e}")


class MCPDataAnalyzer:
    """
    使用MCP进行数据分析和查询
    """
    
    def __init__(self, mcp_client=None):
        self.mcp_client = mcp_client
        self.enabled = mcp_client is not None
    
    def analyze_trading_patterns(self, timeframe: str = "24h") -> Optional[Dict]:
        """
        分析交易模式
        
        Args:
            timeframe: 时间范围
            
        Returns:
            分析结果
        """
        if not self.enabled:
            return None
            
        # 使用MCP进行复杂的数据分析
        # 例如：胜率分析、最佳交易时段、币种相关性等
        pass
    
    def get_market_correlation(self, symbol1: str, symbol2: str) -> Optional[float]:
        """
        获取两个币种的相关性
        
        Args:
            symbol1: 币种1
            symbol2: 币种2
            
        Returns:
            相关系数
        """
        if not self.enabled:
            return None
            
        # 使用MCP查询历史数据并计算相关性
        pass


class MarketStateAnalyzer:
    """
    市场状态分析器 - 判断趋势方向和强度
    """
    
    @staticmethod
    def analyze_market_state(price_data: Dict) -> Dict:
        """
        分析市场状态，明确判断是上涨、下跌还是震荡
        
        Args:
            price_data: 价格数据字典
            
        Returns:
            市场状态分析结果
        """
        try:
            result = {
                'state': '震荡市',  # 默认震荡
                'direction': 'NEUTRAL',  # UP/DOWN/NEUTRAL
                'strength': 'WEAK',  # STRONG/MEDIUM/WEAK
                'should_long': False,
                'should_short': False,
                'confidence': 0,
                'reasons': []
            }
            
            tech = price_data.get('technical_data', {})
            series = price_data.get('time_series', {})
            
            # 获取技术指标
            price = price_data.get('price', 0)
            ma5 = tech.get('sma_5', 0)
            ma20 = tech.get('sma_20', 0)
            ma50 = tech.get('sma_50', 0)
            rsi = tech.get('rsi', 50)
            macd = tech.get('macd', 0)
            macd_signal = tech.get('macd_signal', 0)
            macd_hist = tech.get('macd_histogram', 0)
            bb_upper = tech.get('bb_upper', 0)
            bb_lower = tech.get('bb_lower', 0)
            volume_ratio = tech.get('volume_ratio', 1.0)
            
            # 获取K线数据
            close_prices = series.get('close_prices', [])
            open_prices = series.get('open_prices', [])
            
            if not close_prices or len(close_prices) < 3:
                return result
            
            # 1. 均线排列分析（最重要）
            ma_score = 0
            if ma5 > 0 and ma20 > 0 and ma50 > 0:
                # 多头排列
                if ma5 > ma20 > ma50 and price > ma5:
                    ma_score = 3
                    result['reasons'].append('[完成] 完美多头排列(MA5>MA20>MA50)，价格在均线上方')
                elif ma5 > ma20 and price > ma20:
                    ma_score = 2
                    result['reasons'].append('[完成] 多头趋势(MA5>MA20)，价格在MA20上方')
                # 空头排列
                elif ma5 < ma20 < ma50 and price < ma5:
                    ma_score = -3
                    result['reasons'].append('[错误] 完美空头排列(MA5<MA20<MA50)，价格在均线下方')
                elif ma5 < ma20 and price < ma20:
                    ma_score = -2
                    result['reasons'].append('[错误] 空头趋势(MA5<MA20)，价格在MA20下方')
                # 均线粘合（震荡）
                elif abs(ma5 - ma20) / ma20 < 0.01 and abs(ma20 - ma50) / ma50 < 0.01:
                    ma_score = 0
                    result['reasons'].append('[警告] 均线粘合，震荡市')
            
            # 2. K线形态分析
            kline_score = 0
            if len(close_prices) >= 3:
                # 最近3根K线
                recent_closes = close_prices[-3:]
                recent_opens = open_prices[-3:] if len(open_prices) >= 3 else [0, 0, 0]
                
                # 统计阴阳线
                bullish = sum(1 for i in range(3) if recent_closes[i] > recent_opens[i])
                bearish = 3 - bullish
                
                # 价格趋势
                if recent_closes[-1] > recent_closes[0]:
                    price_trend = (recent_closes[-1] - recent_closes[0]) / recent_closes[0] * 100
                    if price_trend > 2:
                        kline_score = 2
                        result['reasons'].append(f'[完成] 近3根K线上涨{price_trend:.1f}%')
                    elif price_trend > 0.5:
                        kline_score = 1
                else:
                    price_trend = (recent_closes[0] - recent_closes[-1]) / recent_closes[0] * 100
                    if price_trend > 2:
                        kline_score = -2
                        result['reasons'].append(f'[错误] 近3根K线下跌{price_trend:.1f}%')
                    elif price_trend > 0.5:
                        kline_score = -1
                
                # 连续阴阳线
                if bullish >= 2:
                    result['reasons'].append(f'[完成] 近3根K线中{bullish}根阳线')
                elif bearish >= 2:
                    result['reasons'].append(f'[错误] 近3根K线中{bearish}根阴线')
            
            # 3. RSI分析
            rsi_score = 0
            if rsi < 30:
                rsi_score = 1  # 超卖，可能反弹
                result['reasons'].append(f'[完成] RSI={rsi:.0f}严重超卖，可能反弹做多')
            elif rsi < 40:
                rsi_score = 0.5
                result['reasons'].append(f'[完成] RSI={rsi:.0f}偏低，接近超卖')
            elif rsi > 70:
                rsi_score = -1  # 超买，可能回调
                result['reasons'].append(f'[错误] RSI={rsi:.0f}严重超买，可能回调做空')
            elif rsi > 60:
                rsi_score = -0.5
                result['reasons'].append(f'[错误] RSI={rsi:.0f}偏高，接近超买')
            
            # 4. MACD分析
            macd_score = 0
            if macd_hist > 0 and macd > macd_signal:
                macd_score = 1
                result['reasons'].append('[完成] MACD金叉，柱状图为正')
            elif macd_hist < 0 and macd < macd_signal:
                macd_score = -1
                result['reasons'].append('[错误] MACD死叉，柱状图为负')
            
            # 5. 布林带位置
            bb_score = 0
            if bb_lower > 0 and bb_upper > 0:
                bb_mid = (bb_upper + bb_lower) / 2
                if price < bb_lower:
                    bb_score = 1
                    result['reasons'].append('[完成] 价格跌破布林带下轨，超卖')
                elif price > bb_upper:
                    bb_score = -1
                    result['reasons'].append('[错误] 价格突破布林带上轨，超买')
                elif price < bb_mid:
                    result['reasons'].append('价格在布林带下半部')
                else:
                    result['reasons'].append('价格在布林带上半部')
            
            # 6. 成交量分析
            volume_score = 0
            if volume_ratio > 1.5:
                volume_score = 0.5  # 放量增强信号
                result['reasons'].append(f'[完成] 成交量放大{volume_ratio:.1f}倍')
            elif volume_ratio < 0.5:
                volume_score = -0.5  # 缩量减弱信号
                result['reasons'].append(f'[警告] 成交量萎缩{volume_ratio:.1f}倍')
            
            # 综合评分
            total_score = ma_score + kline_score + rsi_score + macd_score + bb_score + volume_score
            
            # 判断市场状态
            if total_score >= 4:
                result['state'] = '上涨趋势'
                result['direction'] = 'UP'
                result['strength'] = 'STRONG'
                result['should_long'] = True
                result['confidence'] = min(90, 60 + total_score * 5)
            elif total_score >= 2:
                result['state'] = '上涨趋势'
                result['direction'] = 'UP'
                result['strength'] = 'MEDIUM'
                result['should_long'] = True
                result['confidence'] = min(70, 50 + total_score * 5)
            elif total_score <= -4:
                result['state'] = '下跌趋势'
                result['direction'] = 'DOWN'
                result['strength'] = 'STRONG'
                result['should_short'] = True
                result['confidence'] = min(90, 60 + abs(total_score) * 5)
            elif total_score <= -2:
                result['state'] = '下跌趋势'
                result['direction'] = 'DOWN'
                result['strength'] = 'MEDIUM'
                result['should_short'] = True
                result['confidence'] = min(70, 50 + abs(total_score) * 5)
            else:
                result['state'] = '震荡市'
                result['direction'] = 'NEUTRAL'
                result['strength'] = 'WEAK'
                result['confidence'] = 40
                
                # 震荡市的做多做空判断
                if rsi < 35 and price < bb_lower:
                    result['should_long'] = True
                    result['reasons'].append('[建议] 震荡市超卖，可考虑做多')
                elif rsi > 65 and price > bb_upper:
                    result['should_short'] = True
                    result['reasons'].append('[建议] 震荡市超买，可考虑做空')
            
            return result
            
        except Exception as e:
            print(f"[警告] 市场状态分析失败: {e}")
            return {
                'state': '未知',
                'direction': 'NEUTRAL',
                'strength': 'WEAK',
                'should_long': False,
                'should_short': False,
                'confidence': 0,
                'reasons': [f'分析失败: {str(e)}']
            }


class MCPIntelligence:
    """
    MCP智能分析模块 - 提供高级分析和建议
    """
    
    def __init__(self, memory: MCPTradingMemory):
        """
        初始化智能分析模块
        
        Args:
            memory: MCP交易记忆实例
        """
        self.memory = memory
        self.market_analyzer = MarketStateAnalyzer()
    
    def analyze_symbol_performance(self, symbol: str) -> Dict:
        """
        分析特定币种的历史表现
        
        Args:
            symbol: 币种符号
            
        Returns:
            分析结果字典
        """
        try:
            # 统计成功和失败交易
            successful = [t for t in self.memory.successful_trades if t['symbol'] == symbol]
            failed = [t for t in self.memory.failed_trades if t['symbol'] == symbol]
            
            total = len(successful) + len(failed)
            if total == 0:
                return {'symbol': symbol, 'message': '暂无交易记录'}
            
            win_rate = len(successful) / total * 100
            avg_profit = sum(t['pnl_percent'] for t in successful) / len(successful) if successful else 0
            avg_loss = sum(t['pnl_percent'] for t in failed) / len(failed) if failed else 0
            
            # 分析最佳策略
            strategy_performance = {}
            for trade in successful + failed:
                strategy = trade.get('strategy', 'unknown')
                if strategy not in strategy_performance:
                    strategy_performance[strategy] = {'wins': 0, 'losses': 0, 'total_pnl': 0}
                
                if trade in successful:
                    strategy_performance[strategy]['wins'] += 1
                else:
                    strategy_performance[strategy]['losses'] += 1
                strategy_performance[strategy]['total_pnl'] += trade['pnl_percent']
            
            best_strategy = max(strategy_performance.items(), 
                              key=lambda x: x[1]['wins'] / (x[1]['wins'] + x[1]['losses']) 
                              if (x[1]['wins'] + x[1]['losses']) > 0 else 0)
            
            return {
                'symbol': symbol,
                'total_trades': total,
                'win_rate': round(win_rate, 2),
                'avg_profit': round(avg_profit, 2),
                'avg_loss': round(avg_loss, 2),
                'best_strategy': best_strategy[0],
                'best_strategy_winrate': round(
                    best_strategy[1]['wins'] / (best_strategy[1]['wins'] + best_strategy[1]['losses']) * 100, 2
                ) if (best_strategy[1]['wins'] + best_strategy[1]['losses']) > 0 else 0
            }
            
        except Exception as e:
            print(f"[警告] 分析币种表现失败: {e}")
            return {'symbol': symbol, 'error': str(e)}
    
    def get_smart_recommendation(self, symbol: str, market_state: str, current_indicators: Dict) -> str:
        """
        基于历史数据生成智能建议
        
        Args:
            symbol: 币种符号
            market_state: 当前市场状态
            current_indicators: 当前技术指标
            
        Returns:
            智能建议文本
        """
        try:
            # 分析历史表现
            perf = self.analyze_symbol_performance(symbol)
            
            if 'error' in perf or 'message' in perf:
                return f"[建议] {symbol}暂无历史数据，建议谨慎交易"
            
            recommendations = []
            
            # 基于胜率的建议
            if perf['win_rate'] < 40:
                recommendations.append(f"[警告] {symbol}历史胜率仅{perf['win_rate']}%，建议谨慎或避免交易")
            elif perf['win_rate'] > 60:
                recommendations.append(f"[完成] {symbol}历史胜率{perf['win_rate']}%，表现良好")
            
            # 基于最佳策略的建议
            if perf['best_strategy'] != 'unknown':
                recommendations.append(f"[建议] 最佳策略: {perf['best_strategy']} (胜率{perf['best_strategy_winrate']}%)")
            
            # 基于市场状态的建议
            similar_trades = [t for t in self.memory.successful_trades 
                            if t['symbol'] == symbol and t.get('market_state') == market_state]
            if similar_trades:
                avg_similar_profit = sum(t['pnl_percent'] for t in similar_trades) / len(similar_trades)
                recommendations.append(
                    f"[数据] 在{market_state}下，{symbol}历史平均盈利{avg_similar_profit:.2f}%"
                )
            
            # 检查关键错误
            relevant_mistakes = [m for m in self.memory.critical_mistakes 
                               if symbol in m.get('description', '')]
            if relevant_mistakes:
                recommendations.append(
                    f"[重要] 注意: {symbol}曾有{len(relevant_mistakes)}次关键错误，请避免重复"
                )
            
            return "\n".join(recommendations) if recommendations else f"[建议] {symbol}可以考虑交易"
            
        except Exception as e:
            print(f"[警告] 生成智能建议失败: {e}")
            return "[建议] 建议基于当前市场情况谨慎决策"
    
    def evaluate_risk(self, symbol: str, position_size: float, leverage: int = 1) -> Dict:
        """
        评估交易风险
        
        Args:
            symbol: 币种符号
            position_size: 仓位大小
            leverage: 杠杆倍数
            
        Returns:
            风险评估结果
        """
        try:
            perf = self.analyze_symbol_performance(symbol)
            
            if 'error' in perf or 'message' in perf:
                return {
                    'risk_level': 'HIGH',
                    'reason': '缺乏历史数据',
                    'recommendation': '建议使用最小仓位测试'
                }
            
            # 计算风险等级
            risk_score = 0
            
            # 胜率因素
            if perf['win_rate'] < 40:
                risk_score += 3
            elif perf['win_rate'] < 50:
                risk_score += 2
            elif perf['win_rate'] < 60:
                risk_score += 1
            
            # 平均亏损因素
            if abs(perf['avg_loss']) > 3:
                risk_score += 2
            elif abs(perf['avg_loss']) > 2:
                risk_score += 1
            
            # 杠杆因素
            if leverage > 5:
                risk_score += 2
            elif leverage > 3:
                risk_score += 1
            
            # 确定风险等级
            if risk_score >= 5:
                risk_level = 'HIGH'
                recommendation = '建议减小仓位或不交易'
            elif risk_score >= 3:
                risk_level = 'MEDIUM'
                recommendation = '建议使用标准仓位，严格止损'
            else:
                risk_level = 'LOW'
                recommendation = '风险可控，可以正常交易'
            
            return {
                'risk_level': risk_level,
                'risk_score': risk_score,
                'win_rate': perf['win_rate'],
                'avg_loss': perf['avg_loss'],
                'recommendation': recommendation
            }
            
        except Exception as e:
            print(f"[警告] 风险评估失败: {e}")
            return {
                'risk_level': 'UNKNOWN',
                'error': str(e),
                'recommendation': '建议谨慎交易'
            }
    
    def detect_patterns(self, symbol: str, lookback: int = 20) -> List[str]:
        """
        检测重复出现的交易模式
        
        Args:
            symbol: 币种符号
            lookback: 回看交易数量
            
        Returns:
            检测到的模式列表
        """
        try:
            patterns = []
            
            # 获取最近的交易
            recent_trades = (self.memory.successful_trades + self.memory.failed_trades)[-lookback:]
            symbol_trades = [t for t in recent_trades if t['symbol'] == symbol]
            
            if len(symbol_trades) < 5:
                return ['数据不足，无法检测模式']
            
            # 检测连续亏损模式
            consecutive_losses = 0
            max_consecutive_losses = 0
            for trade in symbol_trades:
                if trade in self.memory.failed_trades:
                    consecutive_losses += 1
                    max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
                else:
                    consecutive_losses = 0
            
            if max_consecutive_losses >= 3:
                patterns.append(f'[警告] 检测到连续{max_consecutive_losses}次亏损，可能策略不适合当前市场')
            
            # 检测盈亏比模式
            profits = [t['pnl_percent'] for t in symbol_trades if t in self.memory.successful_trades]
            losses = [t['pnl_percent'] for t in symbol_trades if t in self.memory.failed_trades]
            
            if profits and losses:
                avg_profit = sum(profits) / len(profits)
                avg_loss = sum(losses) / len(losses)
                profit_loss_ratio = abs(avg_profit / avg_loss) if avg_loss != 0 else 0
                
                if profit_loss_ratio < 1:
                    patterns.append(f'[警告] 盈亏比不佳({profit_loss_ratio:.2f}:1)，平均盈利小于平均亏损')
                elif profit_loss_ratio > 2:
                    patterns.append(f'[完成] 盈亏比优秀({profit_loss_ratio:.2f}:1)，继续保持')
            
            # 检测市场状态偏好
            market_states = {}
            for trade in symbol_trades:
                state = trade.get('market_state', 'unknown')
                if state not in market_states:
                    market_states[state] = {'wins': 0, 'losses': 0}
                
                if trade in self.memory.successful_trades:
                    market_states[state]['wins'] += 1
                else:
                    market_states[state]['losses'] += 1
            
            for state, stats in market_states.items():
                total = stats['wins'] + stats['losses']
                if total >= 3:
                    win_rate = stats['wins'] / total * 100
                    if win_rate > 70:
                        patterns.append(f'[完成] 在{state}下表现优秀(胜率{win_rate:.0f}%)')
                    elif win_rate < 30:
                        patterns.append(f'[警告] 在{state}下表现不佳(胜率{win_rate:.0f}%)，建议避免')
            
            return patterns if patterns else ['未检测到明显模式']
            
        except Exception as e:
            print(f"[警告] 模式检测失败: {e}")
            return [f'模式检测失败: {str(e)}']
    
    def suggest_optimal_strategy(self, symbol: str, market_state: str) -> Optional[str]:
        """
        建议最优策略
        
        Args:
            symbol: 币种符号
            market_state: 市场状态
            
        Returns:
            建议的策略名称
        """
        try:
            # 筛选相关交易
            relevant_trades = [
                t for t in self.memory.successful_trades 
                if t['symbol'] == symbol and t.get('market_state') == market_state
            ]
            
            if not relevant_trades:
                return None
            
            # 统计各策略表现
            strategy_stats = {}
            for trade in relevant_trades:
                strategy = trade.get('strategy', 'unknown')
                if strategy not in strategy_stats:
                    strategy_stats[strategy] = {
                        'count': 0,
                        'total_pnl': 0
                    }
                strategy_stats[strategy]['count'] += 1
                strategy_stats[strategy]['total_pnl'] += trade['pnl_percent']
            
            # 选择平均收益最高的策略
            best_strategy = max(
                strategy_stats.items(),
                key=lambda x: x[1]['total_pnl'] / x[1]['count']
            )
            
            return best_strategy[0]
            
        except Exception as e:
            print(f"[警告] 建议最优策略失败: {e}")
            return None


# 使用示例
if __name__ == "__main__":
    # 初始化MCP记忆系统
    memory = MCPTradingMemory()
    
    # 记录成功交易
    memory.record_successful_trade({
        'symbol': 'BTC',
        'pnl_percent': 3.5,
        'market_state': '趋势市',
        'strategy': '趋势跟随'
    })
    
    # 获取交易洞察
    insights = memory.get_trading_insights('BTC')
    print(insights)
    
    # 使用智能分析
    intelligence = MCPIntelligence(memory)
    recommendation = intelligence.get_smart_recommendation('BTC', '趋势市', {})
    print(recommendation)
