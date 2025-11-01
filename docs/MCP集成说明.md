# MCP集成说明

## 概述

本文档说明如何为AI交易系统集成MCP（Model Context Protocol）服务器，以增强AI的学习和记忆能力。

## 推荐的MCP服务器

### 1. Memory MCP Server（强烈推荐）

**用途：**
- 记录成功/失败的交易经验
- 存储市场模式识别结果
- 建立币种特征知识图谱
- 策略表现历史记录

**安装：**
```bash
npm install -g @modelcontextprotocol/server-memory
```

**配置示例：**
```json
{
  "mcpServers": {
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    }
  }
}
```

### 2. Filesystem MCP Server

**用途：**
- 读取历史交易日志
- 保存交易报告
- 管理配置文件

**安装：**
```bash
npm install -g @modelcontextprotocol/server-filesystem
```

**配置示例：**
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/Users/Jackymax_1/Desktop/alpha-arena/multi_agent_trading"
      ]
    }
  }
}
```

### 3. SQLite MCP Server

**用途：**
- 复杂的交易数据查询
- 历史数据统计分析
- 生成交易报表

**安装：**
```bash
npm install -g @modelcontextprotocol/server-sqlite
```

**配置示例：**
```json
{
  "mcpServers": {
    "sqlite": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-sqlite",
        "--db-path",
        "/Users/Jackymax_1/Desktop/alpha-arena/multi_agent_trading/data/trades.db"
      ]
    }
  }
}
```

## 集成方案

### 方案1：使用Memory MCP增强AI学习（推荐）

**优势：**
- AI可以从历史交易中学习
- 自动积累交易经验
- 识别成功/失败的模式

**实现步骤：**

1. **在 `pure_ai_trader.py` 中集成MCP Memory：**

```python
from mcp_integration import MCPTradingMemory

class PureAITrader:
    def __init__(self, ai_client, mcp_client=None):
        self.ai_client = ai_client
        self.mcp_memory = MCPTradingMemory(mcp_client)
        # ... 其他初始化
```

2. **在交易完成后记录经验：**

```python
def _record_trade_result(self, trade_info):
    """记录交易结果到MCP Memory"""
    if trade_info['pnl'] > 0:
        self.mcp_memory.record_successful_trade(trade_info)
    else:
        self.mcp_memory.record_failed_trade(trade_info)
```

3. **在决策前查询历史经验：**

```python
def analyze_multi_coins(self, all_coins_data, ...):
    # 获取历史交易洞察
    for coin in all_coins_data.keys():
        insights = self.mcp_memory.get_trading_insights(coin)
        if insights:
            # 将洞察添加到prompt中
            prompt += f"\n{coin}的历史经验: {insights}\n"
```

### 方案2：使用Filesystem MCP管理日志

**用途：**
- 自动保存交易日志
- 读取历史配置
- 生成交易报告

**实现：**
```python
# 使用MCP Filesystem工具保存日志
mcp_client.call_tool("write_file", {
    "path": f"logs/trade_{datetime.now().strftime('%Y%m%d')}.log",
    "content": trade_log
})
```

### 方案3：使用SQLite MCP进行数据分析

**用途：**
- 复杂的SQL查询
- 交易统计分析
- 生成性能报表

**实现：**
```python
# 查询最近30天的胜率
result = mcp_client.call_tool("query", {
    "sql": """
        SELECT 
            symbol,
            COUNT(*) as total_trades,
            SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as win_rate
        FROM trades
        WHERE close_time > datetime('now', '-30 days')
        GROUP BY symbol
    """
})
```

## 具体使用场景

### 场景1：AI从失败中学习

```python
# 当交易亏损时
if pnl < 0:
    mcp_memory.record_failed_trade({
        'symbol': 'BTC',
        'pnl_percent': -2.5,
        'market_state': '震荡市',
        'strategy': '追涨',
        'close_reason': '止损触发',
        'lesson': '震荡市不应该追涨，应该在边界反向操作'
    })

# 下次交易BTC时
insights = mcp_memory.get_trading_insights('BTC')
# AI会看到："上次在震荡市追涨亏损了2.5%，这次要避免"
```

### 场景2：识别最佳交易时段

```python
# 记录每笔交易的时间和结果
mcp_memory.record_market_pattern('BTC', {
    'type': '高波动时段',
    'time_range': '21:00-23:00 UTC',
    'avg_profit': 3.2,
    'win_rate': 65
})

# 查询最佳交易时段
best_time = mcp_memory.get_best_trading_hours('BTC')
```

### 场景3：策略效果评估

```python
# 记录使用不同策略的结果
mcp_memory.record_successful_trade({
    'symbol': 'ETH',
    'strategy': '趋势跟随',
    'pnl_percent': 5.2
})

# 查询策略表现
performance = mcp_memory.get_strategy_performance('趋势跟随')
# 返回：{'avg_profit': 4.5, 'win_rate': 68, 'total_trades': 25}
```

## 配置文件示例

创建 `mcp_config.json`：

```json
{
  "mcpServers": {
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"],
      "env": {}
    },
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/Users/Jackymax_1/Desktop/alpha-arena/multi_agent_trading"
      ]
    },
    "sqlite": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-sqlite",
        "--db-path",
        "/Users/Jackymax_1/Desktop/alpha-arena/multi_agent_trading/data/trades.db"
      ]
    }
  }
}
```

## 下一步

1. **选择要集成的MCP服务器**（推荐从Memory开始）
2. **安装对应的MCP服务器**
3. **修改代码集成MCP客户端**
4. **测试MCP功能**
5. **观察AI的学习效果**

## 注意事项

- MCP服务器需要Node.js环境
- Memory MCP的数据存储在内存中，重启会丢失（可以配置持久化）
- SQLite MCP需要先创建数据库表结构
- 建议先在测试环境验证MCP功能

## 预期效果

集成MCP后，AI将能够：
- ✅ 记住之前的交易经验
- ✅ 避免重复犯错
- ✅ 识别成功的交易模式
- ✅ 根据历史数据优化策略
- ✅ 提供更智能的决策建议
