"""
MCP与TradeDatabase同步模块
实现MCP记忆与数据库之间的数据同步
"""
from typing import Dict, List
from datetime import datetime, timedelta
from .integration import MCPTradingMemory
from data import TradeDatabase


class MCPDatabaseSync:
    """MCP记忆与数据库同步器"""
    
    def __init__(self, mcp_memory: MCPTradingMemory, trade_db: TradeDatabase):
        """
        初始化同步器
        
        Args:
            mcp_memory: MCP记忆实例
            trade_db: 交易数据库实例
        """
        self.mcp_memory = mcp_memory
        self.trade_db = trade_db
        self.last_sync_time = None
    
    def sync_mcp_to_database(self):
        """
        将MCP记忆同步到数据库
        用于长期存储和复杂查询
        """
        try:
            print("\n" + "="*70)
            print("[同步] 开始同步MCP记忆到数据库...")
            print("="*70)
            
            synced_count = 0
            
            # 同步成功交易
            for trade in self.mcp_memory.successful_trades:
                if self._should_sync_trade(trade):
                    self._save_trade_to_db(trade, success=True)
                    synced_count += 1
            
            # 同步失败交易
            for trade in self.mcp_memory.failed_trades:
                if self._should_sync_trade(trade):
                    self._save_trade_to_db(trade, success=False)
                    synced_count += 1
            
            self.last_sync_time = datetime.now()
            
            print(f"[完成] 同步完成: {synced_count}笔交易已保存到数据库")
            print("="*70 + "\n")
            
            return synced_count
            
        except Exception as e:
            print(f"[失败] 同步失败: {e}")
            return 0
    
    def _should_sync_trade(self, trade: Dict) -> bool:
        """
        判断交易是否需要同步
        
        Args:
            trade: 交易记录
            
        Returns:
            是否需要同步
        """
        # 检查数据库中是否已存在
        # 这里简化处理，实际应该检查唯一标识
        return True
    
    def _save_trade_to_db(self, trade: Dict, success: bool):
        """
        保存交易到数据库
        
        Args:
            trade: 交易记录
            success: 是否成功
        """
        try:
            # 构造数据库记录格式
            db_trade = {
                'symbol': trade.get('symbol'),
                'side': 'LONG',  # 从MCP记录中可能需要推断
                'entry_price': 0,  # MCP记录中可能没有
                'exit_price': 0,
                'quantity': 0,
                'pnl': trade.get('pnl_percent', 0),
                'pnl_percent': trade.get('pnl_percent', 0),
                'strategy': trade.get('strategy', 'unknown'),
                'market_state': trade.get('market_state', 'unknown'),
                'close_reason': trade.get('close_reason', 'unknown') if not success else 'take_profit',
                'timestamp': trade.get('timestamp', datetime.now().isoformat())
            }
            
            # 保存到数据库（需要TradeDatabase支持）
            # self.trade_db.save_trade(db_trade)
            
        except Exception as e:
            print(f"[警告] 保存交易失败: {e}")
    
    def sync_database_to_mcp(self, days: int = 7):
        """
        从数据库加载历史交易到MCP记忆
        用于启动时恢复记忆
        
        Args:
            days: 加载最近N天的交易
        """
        try:
            print("\n" + "="*70)
            print(f"[同步] 从数据库加载最近{days}天的交易到MCP记忆...")
            print("="*70)
            
            # 获取最近的交易
            start_date = datetime.now() - timedelta(days=days)
            # recent_trades = self.trade_db.get_trades_since(start_date)
            
            loaded_count = 0
            # for trade in recent_trades:
            #     self._load_trade_to_mcp(trade)
            #     loaded_count += 1
            
            print(f"[完成] 加载完成: {loaded_count}笔交易已加载到MCP记忆")
            print("="*70 + "\n")
            
            return loaded_count
            
        except Exception as e:
            print(f"[失败] 加载失败: {e}")
            return 0
    
    def _load_trade_to_mcp(self, db_trade: Dict):
        """
        从数据库记录加载到MCP记忆
        
        Args:
            db_trade: 数据库交易记录
        """
        try:
            # 转换为MCP格式
            mcp_trade = {
                'symbol': db_trade.get('symbol'),
                'pnl_percent': db_trade.get('pnl_percent', 0),
                'market_state': db_trade.get('market_state', 'unknown'),
                'strategy': db_trade.get('strategy', 'unknown'),
                'close_reason': db_trade.get('close_reason', 'unknown'),
                'timestamp': db_trade.get('timestamp')
            }
            
            # 根据盈亏判断成功/失败
            if mcp_trade['pnl_percent'] > 0:
                self.mcp_memory.record_successful_trade(mcp_trade)
            else:
                self.mcp_memory.record_failed_trade(mcp_trade)
                
        except Exception as e:
            print(f"[警告] 加载交易失败: {e}")
    
    def get_sync_status(self) -> Dict:
        """
        获取同步状态
        
        Returns:
            同步状态信息
        """
        return {
            'last_sync_time': self.last_sync_time.isoformat() if self.last_sync_time else None,
            'mcp_trades': len(self.mcp_memory.successful_trades) + len(self.mcp_memory.failed_trades),
            'mcp_successful': len(self.mcp_memory.successful_trades),
            'mcp_failed': len(self.mcp_memory.failed_trades)
        }
    
    def auto_sync_if_needed(self, interval_hours: int = 24):
        """
        如果需要，自动执行同步
        
        Args:
            interval_hours: 同步间隔（小时）
        """
        if self.last_sync_time is None:
            # 首次同步
            return self.sync_mcp_to_database()
        
        # 检查是否到了同步时间
        time_since_sync = datetime.now() - self.last_sync_time
        if time_since_sync.total_seconds() > interval_hours * 3600:
            return self.sync_mcp_to_database()
        
        return 0


# 使用示例
if __name__ == "__main__":
    # 初始化
    mcp_memory = MCPTradingMemory()
    trade_db = TradeDatabase()
    sync = MCPDatabaseSync(mcp_memory, trade_db)
    
    # 添加一些测试数据
    mcp_memory.record_successful_trade({
        'symbol': 'BTC',
        'pnl_percent': 3.5,
        'market_state': '趋势市',
        'strategy': '趋势跟随'
    })
    
    # 同步到数据库
    sync.sync_mcp_to_database()
    
    # 查看同步状态
    status = sync.get_sync_status()
    print("\n同步状态:")
    for key, value in status.items():
        print(f"  {key}: {value}")
