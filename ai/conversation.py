"""
对话监控器 - 实时查看与AI的对话内容
集成MCP文件系统进行持久化
"""
import json
import os
from datetime import datetime
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
from rich import box

console = Console()


class ConversationMonitor:
    """对话监控器 - 实时显示AI对话，集成MCP持久化"""
    
    def __init__(self, log_file: str = "logs/conversation_monitor.log", mcp_filesystem=None):
        """
        初始化监控器
        
        Args:
            log_file: 监控日志文件路径
            mcp_filesystem: MCP文件系统实例
        """
        self.log_file = log_file
        self.mcp_filesystem = mcp_filesystem
        self.ensure_log_dir()
    
    def ensure_log_dir(self):
        """确保日志目录存在"""
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
    
    def log_user_message(self, message: str, metadata: Optional[dict] = None):
        """
        记录用户消息（发送给AI的数据）
        
        Args:
            message: 消息内容
            metadata: 元数据
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        # 控制台显示
        console.print("\n" + "="*80, style="bold blue")
        console.print(f"[bold cyan]📤 发送给AI[/bold cyan] [{timestamp}]", style="bold")
        console.print("="*80, style="bold blue")
        
        # 显示元数据
        if metadata:
            meta_table = Table(show_header=False, box=box.SIMPLE)
            meta_table.add_column("Key", style="cyan")
            meta_table.add_column("Value", style="yellow")
            for key, value in metadata.items():
                meta_table.add_row(str(key), str(value))
            console.print(meta_table)
            console.print()
        
        # 显示消息内容
        panel = Panel(
            message,
            title="[bold cyan]User Message[/bold cyan]",
            border_style="cyan",
            padding=(1, 2)
        )
        console.print(panel)
        
        # 写入日志文件
        log_entry = {
            'timestamp': timestamp,
            'role': 'user',
            'message': message,
            'metadata': metadata,
            'length': len(message)
        }
        self._write_to_log(log_entry)
        
        # 使用MCP持久化
        if self.mcp_filesystem:
            try:
                self.mcp_filesystem.save_trade_log(f"📤 USER: {message[:200]}...")
            except Exception as e:
                console.print(f"[yellow][警告] MCP保存失败: {e}[/yellow]")
    
    def log_assistant_message(self, message: str, metadata: Optional[dict] = None):
        """
        记录AI回复
        
        Args:
            message: AI回复内容
            metadata: 元数据
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        # 控制台显示
        console.print("\n" + "="*80, style="bold green")
        console.print(f"[bold green]📥 AI回复[/bold green] [{timestamp}]", style="bold")
        console.print("="*80, style="bold green")
        
        # 显示元数据
        if metadata:
            meta_table = Table(show_header=False, box=box.SIMPLE)
            meta_table.add_column("Key", style="green")
            meta_table.add_column("Value", style="yellow")
            for key, value in metadata.items():
                meta_table.add_row(str(key), str(value))
            console.print(meta_table)
            console.print()
        
        # 显示消息内容
        panel = Panel(
            message,
            title="[bold green]Assistant Response[/bold green]",
            border_style="green",
            padding=(1, 2)
        )
        console.print(panel)
        
        # 写入日志文件
        log_entry = {
            'timestamp': timestamp,
            'role': 'assistant',
            'message': message,
            'metadata': metadata,
            'length': len(message)
        }
        self._write_to_log(log_entry)
        
        # 使用MCP持久化AI决策
        if self.mcp_filesystem and metadata:
            try:
                # 保存完整的AI决策
                decision_log = {
                    'timestamp': timestamp,
                    'message': message,
                    'signal': metadata.get('signal'),
                    'symbol': metadata.get('symbol'),
                    'confidence': metadata.get('confidence'),
                    'response_time': metadata.get('response_time'),
                    'tokens_used': metadata.get('tokens_used')
                }
                self.mcp_filesystem.save_decision_log(decision_log)
            except Exception as e:
                console.print(f"[yellow][警告] MCP保存决策失败: {e}[/yellow]")
    
    def log_api_call(self, model: str, messages: list, response: dict):
        """
        记录完整的API调用
        
        Args:
            model: 模型名称
            messages: 发送的消息列表
            response: API响应
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        console.print("\n" + "="*80, style="bold magenta")
        console.print(f"[bold magenta]🔌 API调用详情[/bold magenta] [{timestamp}]", style="bold")
        console.print("="*80, style="bold magenta")
        
        # API信息表格
        api_table = Table(show_header=False, box=box.ROUNDED)
        api_table.add_column("Item", style="magenta")
        api_table.add_column("Value", style="yellow")
        
        api_table.add_row("模型", model)
        api_table.add_row("消息数量", str(len(messages)))
        
        if 'usage' in response:
            api_table.add_row("Prompt Tokens", str(response['usage'].get('prompt_tokens', 'N/A')))
            api_table.add_row("Completion Tokens", str(response['usage'].get('completion_tokens', 'N/A')))
            api_table.add_row("Total Tokens", str(response['usage'].get('total_tokens', 'N/A')))
        
        console.print(api_table)
        
        # 显示发送的消息
        console.print("\n[bold]发送的消息:[/bold]")
        for i, msg in enumerate(messages[-3:], 1):  # 只显示最后3条
            role_color = "cyan" if msg['role'] == 'user' else "green" if msg['role'] == 'assistant' else "yellow"
            console.print(f"\n[{role_color}]{i}. {msg['role'].upper()}:[/{role_color}]")
            content_preview = msg['content'][:200] + "..." if len(msg['content']) > 200 else msg['content']
            console.print(f"  {content_preview}")
        
        # 写入日志
        self._write_to_log({
            'timestamp': timestamp,
            'type': 'api_call',
            'model': model,
            'messages_count': len(messages),
            'response': response
        })
    
    def log_decision_trigger(self, should_trigger: bool, reasons: list, signals: dict):
        """
        记录决策触发检查
        
        Args:
            should_trigger: 是否触发
            reasons: 触发原因列表
            signals: 信号字典
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        trigger_style = "bold green" if should_trigger else "bold yellow"
        trigger_emoji = "⚡" if should_trigger else "⏸️"
        
        console.print("\n" + "="*80, style=trigger_style)
        console.print(f"[{trigger_style}]{trigger_emoji} 决策触发检查[/{trigger_style}] [{timestamp}]")
        console.print("="*80, style=trigger_style)
        
        # 信号状态表格
        signal_table = Table(title="触发信号状态", box=box.ROUNDED)
        signal_table.add_column("信号", style="cyan")
        signal_table.add_column("状态", justify="center")
        signal_table.add_column("说明", style="dim")
        
        signal_descriptions = {
            'price_change': '价格大幅变化',
            'rsi_extreme': 'RSI极值',
            'volume_surge': '成交量激增',
            'macd_cross': 'MACD交叉',
            'trend_change': '趋势改变',
            'ai_suggestion': 'AI建议'
        }
        
        for signal_name, is_triggered in signals.items():
            status = "[完成]" if is_triggered else "[失败]"
            status_style = "green" if is_triggered else "red"
            signal_table.add_row(
                signal_descriptions.get(signal_name, signal_name),
                f"[{status_style}]{status}[/{status_style}]",
                signal_name
            )
        
        console.print(signal_table)
        
        # 结果
        result_text = f"\n{'🚀 触发决策流程！' if should_trigger else '⏸️ 继续跟踪'}"
        result_style = "bold green" if should_trigger else "bold yellow"
        console.print(result_text, style=result_style)
        
        if reasons:
            console.print(f"\n触发原因: {', '.join(reasons)}", style="yellow")
        
        # 写入日志
        self._write_to_log({
            'timestamp': timestamp,
            'type': 'decision_trigger',
            'should_trigger': should_trigger,
            'reasons': reasons,
            'signals': signals
        })
    
    def _write_to_log(self, data: dict):
        """写入日志文件"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
        except Exception as e:
            console.print(f"[red]写入日志失败: {e}[/red]")
    
    def show_summary(self):
        """显示对话摘要"""
        console.print("\n" + "="*80, style="bold white")
        console.print("[bold white]📊 对话摘要[/bold white]")
        console.print("="*80, style="bold white")
        
        if not os.path.exists(self.log_file):
            console.print("[yellow]暂无对话记录[/yellow]")
            return
        
        user_count = 0
        assistant_count = 0
        api_calls = 0
        total_tokens = 0
        
        with open(self.log_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if data.get('role') == 'user':
                        user_count += 1
                    elif data.get('role') == 'assistant':
                        assistant_count += 1
                    elif data.get('type') == 'api_call':
                        api_calls += 1
                        if 'response' in data and 'usage' in data['response']:
                            total_tokens += data['response']['usage'].get('total_tokens', 0)
                except:
                    continue
        
        summary_table = Table(show_header=False, box=box.ROUNDED)
        summary_table.add_column("指标", style="cyan")
        summary_table.add_column("数值", style="yellow")
        
        summary_table.add_row("用户消息", str(user_count))
        summary_table.add_row("AI回复", str(assistant_count))
        summary_table.add_row("API调用", str(api_calls))
        summary_table.add_row("总Token消耗", str(total_tokens))
        
        console.print(summary_table)


# 全局监控器实例
_monitor = None

def get_monitor(mcp_filesystem=None) -> ConversationMonitor:
    """
    获取全局监控器实例
    
    Args:
        mcp_filesystem: MCP文件系统实例（可选）
    """
    global _monitor
    if _monitor is None:
        _monitor = ConversationMonitor(mcp_filesystem=mcp_filesystem)
    elif mcp_filesystem and not _monitor.mcp_filesystem:
        # 如果之前没有MCP，现在添加
        _monitor.mcp_filesystem = mcp_filesystem
    return _monitor


if __name__ == "__main__":
    # 测试代码
    monitor = ConversationMonitor()
    
    # 模拟用户消息
    monitor.log_user_message(
        "【市场更新 - 2025-10-28 16:20:26】\n\n当前价格: $114,204.20\nRSI: 58.58\nMACD: 64.72",
        metadata={'price': 114204.2, 'timestamp': '2025-10-28 16:20:26'}
    )
    
    # 模拟AI回复
    monitor.log_assistant_message(
        "市场状态确认重要变化：价格突破$114,200，RSI快速升至58.58。建议启动决策流程。",
        metadata={'analysis_type': 'market_update', 'tokens_used': 150}
    )
    
    # 模拟决策触发检查
    monitor.log_decision_trigger(
        should_trigger=False,
        reasons=[],
        signals={
            'price_change': False,
            'rsi_extreme': False,
            'volume_surge': False,
            'macd_cross': False,
            'trend_change': False,
            'ai_suggestion': True
        }
    )
    
    # 显示摘要
    monitor.show_summary()
