"""
交易数据库模块 - 使用SQLite存储交易记录
"""
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path


class TradeDatabase:
    """交易数据库管理器"""
    
    def __init__(self, db_path: str = "data/trades.db"):
        """
        初始化数据库
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        
        # 确保数据目录存在
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库
        self._init_database()
        
        print(f"[完成] 交易数据库初始化完成: {db_path}")
    
    def _init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建交易记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            signal TEXT NOT NULL,
            side TEXT,
            entry_price REAL,
            exit_price REAL,
            quantity REAL,
            leverage INTEGER,
            
            -- 时间信息
            open_time TEXT NOT NULL,
            close_time TEXT,
            holding_duration_seconds INTEGER,
            
            -- 盈亏信息
            realized_pnl REAL,
            pnl_percent REAL,
            
            -- 订单信息
            entry_order_id TEXT,
            exit_order_id TEXT,
            stop_loss_price REAL,
            take_profit_price REAL,
            
            -- AI决策信息
            ai_confidence TEXT,
            ai_reason TEXT,
            ai_think TEXT,
            
            -- 市场状态（JSON）
            market_data TEXT,
            
            -- 状态
            status TEXT NOT NULL,
            
            -- 其他信息
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        ''')
        
        # 创建AI对话历史表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_id INTEGER,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            tokens_used INTEGER,
            timestamp TEXT NOT NULL,
            
            FOREIGN KEY (trade_id) REFERENCES trades(id)
        )
        ''')
        
        # 创建账户快照表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS account_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            balance REAL,
            total_value REAL,
            total_return_pct REAL,
            sharpe_ratio REAL,
            open_positions_count INTEGER,
            timestamp TEXT NOT NULL
        )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_open_time ON trades(open_time)')
        
        conn.commit()
        conn.close()
    
    def create_trade(
        self,
        symbol: str,
        signal: str,
        entry_price: float,
        quantity: float,
        leverage: int,
        ai_decision: Dict,
        market_data: Dict
    ) -> int:
        """
        创建新交易记录
        
        Args:
            symbol: 交易对
            signal: 信号（BUY/SELL）
            entry_price: 开仓价
            quantity: 数量
            leverage: 杠杆
            ai_decision: AI决策信息
            market_data: 市场数据
        
        Returns:
            交易ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        side = 'long' if signal == 'BUY' else 'short' if signal == 'SELL' else None
        
        cursor.execute('''
        INSERT INTO trades (
            symbol, signal, side, entry_price, quantity, leverage,
            open_time, stop_loss_price, take_profit_price,
            ai_confidence, ai_reason, ai_think,
            market_data, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            symbol,
            signal,
            side,
            entry_price,
            quantity,
            leverage,
            now,
            ai_decision.get('stop_loss'),
            ai_decision.get('take_profit'),
            ai_decision.get('confidence'),
            ai_decision.get('reason'),
            ai_decision.get('think'),
            json.dumps(market_data),
            'OPEN',
            now,
            now
        ))
        
        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"📝 创建交易记录 #{trade_id}: {signal} {quantity} {symbol} @ ${entry_price:,.2f}")
        
        return trade_id
    
    def close_trade(
        self,
        trade_id: int,
        exit_price: float,
        realized_pnl: float,
        ai_decision: Optional[Dict] = None
    ):
        """
        平仓交易
        
        Args:
            trade_id: 交易ID
            exit_price: 平仓价
            realized_pnl: 实现盈亏
            ai_decision: AI决策信息（可选）
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取开仓时间
        cursor.execute('SELECT open_time, entry_price, quantity FROM trades WHERE id = ?', (trade_id,))
        row = cursor.fetchone()
        
        if not row:
            print(f"[失败] 交易记录 #{trade_id} 不存在")
            conn.close()
            return
        
        open_time_str, entry_price, quantity = row
        open_time = datetime.fromisoformat(open_time_str)
        close_time = datetime.now()
        
        # 计算持仓时长
        duration = (close_time - open_time).total_seconds()
        
        # 计算盈亏百分比
        pnl_percent = (realized_pnl / (entry_price * quantity)) * 100 if entry_price and quantity else 0
        
        # 更新记录
        update_data = {
            'exit_price': exit_price,
            'close_time': close_time.isoformat(),
            'holding_duration_seconds': duration,
            'realized_pnl': realized_pnl,
            'pnl_percent': pnl_percent,
            'status': 'CLOSED',
            'updated_at': close_time.isoformat()
        }
        
        if ai_decision:
            update_data['notes'] = f"AI平仓理由: {ai_decision.get('reason', 'N/A')}"
        
        cursor.execute('''
        UPDATE trades SET
            exit_price = ?,
            close_time = ?,
            holding_duration_seconds = ?,
            realized_pnl = ?,
            pnl_percent = ?,
            status = ?,
            notes = ?,
            updated_at = ?
        WHERE id = ?
        ''', (
            update_data['exit_price'],
            update_data['close_time'],
            update_data['holding_duration_seconds'],
            update_data['realized_pnl'],
            update_data['pnl_percent'],
            update_data['status'],
            update_data.get('notes', ''),
            update_data['updated_at'],
            trade_id
        ))
        
        conn.commit()
        conn.close()
        
        duration_str = self._format_duration(duration)
        pnl_emoji = "💚" if realized_pnl > 0 else "❤️" if realized_pnl < 0 else "💛"
        
        print(f"📝 平仓交易 #{trade_id}: {pnl_emoji} ${realized_pnl:,.2f} ({pnl_percent:+.2f}%) 持仓{duration_str}")
    
    def get_open_trades(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        获取所有未平仓交易
        
        Args:
            symbol: 可选，只获取特定交易对的记录
        
        Returns:
            交易记录列表
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if symbol:
            cursor.execute('SELECT * FROM trades WHERE status = ? AND symbol = ?', ('OPEN', symbol))
        else:
            cursor.execute('SELECT * FROM trades WHERE status = ?', ('OPEN',))
        
        rows = cursor.fetchall()
        trades = [dict(row) for row in rows]
        
        conn.close()
        return trades
    
    def get_trade_by_id(self, trade_id: int) -> Optional[Dict]:
        """获取单个交易记录"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM trades WHERE id = ?', (trade_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        return dict(row) if row else None
    
    def save_ai_conversation(
        self,
        trade_id: Optional[int],
        role: str,
        content: str,
        tokens_used: int = 0
    ):
        """
        保存AI对话记录
        
        Args:
            trade_id: 关联的交易ID（可选）
            role: 角色（user/assistant）
            content: 内容
            tokens_used: 使用的token数
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO ai_conversations (trade_id, role, content, tokens_used, timestamp)
        VALUES (?, ?, ?, ?, ?)
        ''', (trade_id, role, content, tokens_used, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def save_account_snapshot(
        self,
        balance: float,
        total_value: float,
        total_return_pct: float,
        sharpe_ratio: float,
        open_positions_count: int
    ):
        """保存账户快照"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO account_snapshots (
            balance, total_value, total_return_pct, sharpe_ratio,
            open_positions_count, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            balance,
            total_value,
            total_return_pct,
            sharpe_ratio,
            open_positions_count,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_trade_statistics(self) -> Dict:
        """获取交易统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 总交易数
        cursor.execute('SELECT COUNT(*) FROM trades')
        total_trades = cursor.fetchone()[0]
        
        # 已平仓交易数
        cursor.execute('SELECT COUNT(*) FROM trades WHERE status = ?', ('CLOSED',))
        closed_trades = cursor.fetchone()[0]
        
        # 盈利交易数
        cursor.execute('SELECT COUNT(*) FROM trades WHERE status = ? AND realized_pnl > 0', ('CLOSED',))
        winning_trades = cursor.fetchone()[0]
        
        # 总盈亏
        cursor.execute('SELECT SUM(realized_pnl) FROM trades WHERE status = ?', ('CLOSED',))
        total_pnl = cursor.fetchone()[0] or 0
        
        # 平均持仓时长
        cursor.execute('SELECT AVG(holding_duration_seconds) FROM trades WHERE status = ?', ('CLOSED',))
        avg_duration = cursor.fetchone()[0] or 0
        
        conn.close()
        
        win_rate = (winning_trades / closed_trades * 100) if closed_trades > 0 else 0
        
        return {
            'total_trades': total_trades,
            'closed_trades': closed_trades,
            'open_trades': total_trades - closed_trades,
            'winning_trades': winning_trades,
            'losing_trades': closed_trades - winning_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_holding_duration': avg_duration
        }
    
    def get_recent_closed_trades(self, limit: int = 10) -> List[Dict]:
        """
        获取最近的已平仓交易
        
        Args:
            limit: 返回的交易数量
            
        Returns:
            交易记录列表
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM trades 
        WHERE status = 'CLOSED'
        ORDER BY close_time DESC
        LIMIT ?
        ''', (limit,))
        
        trades = []
        for row in cursor.fetchall():
            trade = dict(row)
            # 解析JSON字段
            if trade.get('ai_decision'):
                try:
                    trade['ai_decision'] = json.loads(trade['ai_decision'])
                except:
                    pass
            if trade.get('market_data'):
                try:
                    trade['market_data'] = json.loads(trade['market_data'])
                except:
                    pass
            trades.append(trade)
        
        conn.close()
        return trades
    
    def _format_duration(self, seconds: float) -> str:
        """格式化时长"""
        if seconds < 60:
            return f"{seconds:.0f}秒"
        elif seconds < 3600:
            return f"{seconds/60:.1f}分钟"
        elif seconds < 86400:
            return f"{seconds/3600:.1f}小时"
        else:
            return f"{seconds/86400:.1f}天"


if __name__ == "__main__":
    # 测试代码
    print("=== 测试交易数据库 ===\n")
    
    db = TradeDatabase("data/test_trades.db")
    
    # 创建交易
    trade_id = db.create_trade(
        symbol='BTC/USDT',
        signal='BUY',
        entry_price=114000.0,
        quantity=0.01,
        leverage=10,
        ai_decision={
            'confidence': 'HIGH',
            'reason': '多头趋势明确',
            'think': '技术指标共振',
            'stop_loss': 113000.0,
            'take_profit': 116000.0
        },
        market_data={'price': 114000.0, 'rsi': 65}
    )
    
    # 获取未平仓交易
    open_trades = db.get_open_trades()
    print(f"\n未平仓交易: {len(open_trades)}笔")
    
    # 平仓
    db.close_trade(
        trade_id=trade_id,
        exit_price=115000.0,
        realized_pnl=100.0
    )
    
    # 统计
    stats = db.get_trade_statistics()
    print(f"\n交易统计:")
    print(f"  总交易数: {stats['total_trades']}")
    print(f"  胜率: {stats['win_rate']:.1f}%")
    print(f"  总盈亏: ${stats['total_pnl']:.2f}")
