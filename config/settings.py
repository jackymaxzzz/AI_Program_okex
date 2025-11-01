"""
配置文件 - 多轮对话AI交易机器人
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ==================== API配置 ====================
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

OKX_API_KEY = os.getenv('OKX_API_KEY')
OKX_SECRET = os.getenv('OKX_SECRET')
OKX_PASSWORD = os.getenv('OKX_PASSWORD')

# 模拟盘API密钥（需要单独申请）
OKX_TESTNET_API_KEY = os.getenv('OKX_TESTNET_API_KEY')
OKX_TESTNET_SECRET = os.getenv('OKX_TESTNET_SECRET')
OKX_TESTNET_PASSWORD = os.getenv('OKX_TESTNET_PASSWORD')

# ==================== 交易配置 ====================
TRADING_CONFIG = {
    'symbols': ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'XRP/USDT:USDT', 'SOL/USDT:USDT', 'BNB/USDT:USDT'],  # 交易对列表（移除DOGE）
    'amounts': {
        'BTC': 0.01,                 # BTC交易数量（最小0.01）
        'ETH': 0.1,                  # ETH交易数量（最小0.1）
        'XRP': 0.1,                  # XRP交易数量（1张合约=100 XRP，0.1张=10 XRP）
        'SOL': 0.1,                  # SOL交易数量（最小0.1）
        'BNB': 1,                    # BNB交易数量（最小1）
    },
    'min_amounts': {                 # 最小交易数量限制
        'BTC': 0.01,
        'ETH': 0.1,
        'XRP': 0.1,                  # XRP最小0.1张（1张合约=100 XRP）
        'SOL': 0.1,
        'BNB': 1,
    },
    'leverage': 10,                  # 杠杆倍数
    'test_mode': False,              # 测试模式
    'use_testnet': False,            # 是否使用模拟盘（True=模拟盘，False=实盘）[警告] 暂时用实盘
    'initial_balance': 200.0,        # 初始资金 (USDT)
    'cycle_interval': 120,           # 循环间隔（秒），默认300秒=5分钟
    
    # 指数退避配置
    'backoff_enabled': True,         # 是否启用指数退避
    'backoff_threshold': 3,          # 连续HOLD多少次后启动退避
    'backoff_max_skip': 1,           # 最多跳过多少个周期
    
    # AI学习配置
    'history_trades_limit': 5,       # 显示最近多少笔交易给AI学习
    
    # 安全机制配置
    'require_double_confirmation': True,  # 是否需要二次确认才开仓
}

# ==================== 时间周期配置 ====================
TIMEFRAME_CONFIG = {
    'primary': '15m',       # 主周期：15分钟
    'long': '4H',           # 长周期：4小时（注意：OKX要求大写H）
    'daily': '1D',          # 日线：1天（注意：OKX要求大写D）
}

# ==================== 数据点数配置 ====================
DATA_POINTS = {
    'primary': 96,          # 15分钟：96根 = 24小时
    'long': 168,            # 4小时：168根 = 28天
    'daily': 7,             # 日线：7根 = 7天
}

# ==================== 对话管理配置 ====================
CONVERSATION_CONFIG = {
    # 市场跟踪对话
    'tracker': {
        'max_history': 20,              # 最多保留20轮对话
        'summary_interval': 10,         # 每10轮总结一次
        'save_interval': 5,             # 每5轮保存一次
    },
    
    # 决策链对话
    'decision': {
        'steps': 4,                     # 决策步骤数
        'max_retry': 2,                 # 每步最多重试2次
        'timeout': 30,                  # 超时时间（秒）
    },
    
    # 对话存储
    'storage': {
        'tracker_file': 'logs/conversation_tracker.json',
        'decision_file': 'logs/conversation_decision.json',
        'archive_days': 7,              # 归档7天前的对话
    }
}

# ==================== AI配置 ====================
AI_CONFIG = {
    'temperature': 0.7,                 # 创造性参数
    'max_tokens': 2000,                 # 最大输出token
    'top_p': 0.9,                       # 采样参数
    
}

# ==================== 风险控制配置 ====================
RISK_CONFIG = {
    'max_position_size': 0.05,          # 最大持仓（BTC）
    'max_leverage': 10,                 # 最大杠杆
    'stop_loss_atr_multiplier': 2.0,    # 止损：2倍ATR
    'take_profit_atr_multiplier': 4.0,  # 止盈：4倍ATR
    'max_daily_trades': None,           # 每日最多交易次数（None=不限制）
    'min_confidence': 'MEDIUM',         # 最低信心度要求
}

# ==================== 日志配置 ====================
LOG_CONFIG = {
    'log_dir': 'logs',
    'files': {
        'main': 'trading_main.log',
        'tracker': 'market_tracker.log',
        'decision': 'decision_chain.log',
        'execution': 'trade_execution.log',
        'ai_think': 'ai_thinking.log',
    },
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
}

# ==================== 验证配置 ====================
def validate_config():
    """验证配置是否完整"""
    errors = []
    
    if not DEEPSEEK_API_KEY:
        errors.append("[失败] DEEPSEEK_API_KEY未设置")
    
    if not OKX_API_KEY or not OKX_SECRET or not OKX_PASSWORD:
        errors.append("[失败] OKX API配置不完整")
    
    if errors:
        for error in errors:
            print(error)
        raise ValueError("配置验证失败！请检查.env文件")
    
    print("[完成] 配置验证通过")
    return True

if __name__ == "__main__":
    validate_config()
