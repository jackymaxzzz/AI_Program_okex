#本人菜鸡，只是纯粹对代码和AI的热爱,编写这个项目，有问题请大家多多指教

# 🤖 AI驱动的加密货币交易系统

基于DeepSeek AI的全自动加密货币交易系统，支持OKX交易所，具备MCP记忆系统和模块化架构。

## ✨ 主要特性

- 🧠 **AI驱动决策** - 使用DeepSeek AI进行交易决策
- 💾 **MCP记忆系统** - 学习历史交易经验，持续优化
- 📊 **多币种支持** - BTC, ETH, SOL, BNB, XRP等
- 🔄 **自动化交易** - 15分钟周期自动分析和交易
- 📈 **技术指标分析** - MA, RSI, MACD, 布林带等
- 🎯 **策略切换** - 支持多种交易策略（激进、平衡、稳健）
- 🚀 **一键部署** - 提供完整的部署脚本

## 📁 项目结构

```
multi_agent_trading/
├── config/          # 配置管理
│   ├── settings.py  # 主配置文件
│   └── mcp_config.json
├── core/            # 交易核心逻辑
│   ├── trading_executor.py   # 交易执行
│   ├── position_manager.py   # 持仓管理
│   └── order_sync.py         # 订单同步
├── data/            # 数据层
│   ├── database.py   # 交易数据库
│   ├── fetcher.py    # 数据获取
│   └── indicators.py # 技术指标
├── ai/              # AI决策层
│   ├── trader.py     # AI交易员
│   └── conversation.py
├── mcp/             # MCP记忆系统
│   ├── integration.py
│   └── sync.py
├── scripts/         # 部署脚本
│   ├── deploy.sh
│   ├── quick_deploy.sh
│   └── restart.sh
├── prompts/         # AI提示词
├── utils/           # 工具函数
└── main.py          # 主入口
```

## 🚀 快速开始

### 1. 环境要求

- Python 3.11+
- OKX账户（支持模拟盘）
- DeepSeek API Key

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

创建 `.env` 文件：

```bash
# DeepSeek API
DEEPSEEK_API_KEY=your_deepseek_api_key

# OKX API (实盘)
OKX_API_KEY=your_okx_api_key
OKX_SECRET=your_okx_secret
OKX_PASSWORD=your_okx_password

# OKX API (模拟盘)
OKX_TESTNET_API_KEY=your_testnet_api_key
OKX_TESTNET_SECRET=your_testnet_secret
OKX_TESTNET_PASSWORD=your_testnet_password
```

### 4. 运行

```bash
# 测试模式（不实际交易）
python3.11 main.py

# 实盘模式（需要在config/settings.py中设置test_mode=False）
python3.11 main.py
```

## 📊 交易配置

在 `config/settings.py` 中配置：

```python
TRADING_CONFIG = {
    'test_mode': True,  # 测试模式开关
    'symbols': ['BTC/USDT:USDT', 'ETH/USDT:USDT', ...],
    'leverage': 10,     # 杠杆倍数
    'amounts': {        # 交易数量
        'BTC': 0.01,
        'ETH': 0.1,
        ...
    }
}
```

## 🎯 策略切换

系统支持多种交易策略：

- **balanced** (默认) - 平衡策略，5%止盈，2%止损
- **aggressive** - 激进策略，7%止盈，2.5%止损
- **stable_profit** - 稳健策略，3%止盈，1.5%止损

切换策略：

```python
trader.switch_strategy('aggressive')
```

## 🧠 MCP记忆系统

系统会自动记录和学习：

- ✅ 成功交易的经验
- ❌ 失败交易的教训
- 📊 各币种的历史表现
- 🎯 最佳交易策略
- ⚠️ 关键错误记录

记忆数据保存在 `data/mcp_memory_*.json`

## 🚀 服务器部署

### 方式1: 快速部署

```bash
# 从本地推送到服务器
./scripts/quick_deploy.sh <服务器IP>

# 在服务器上重启
ssh user@server 'cd /path/to/project && ./scripts/restart.sh'
```

### 方式2: 完整部署

```bash
# 完整的自动化部署流程
./scripts/deploy.sh <服务器IP> [远程路径] [用户名]
```

### 方式3: Git拉取

```bash
# 在服务器上
git clone https://github.com/jackymaxzzz/AI_Program_okex.git
cd AI_Program_okex
pip3 install -r requirements.txt

# 配置.env文件
cp .env.example .env
vim .env

# 后台运行
nohup python3.11 main.py > logs/trading.log 2>&1 &
```

## 📈 监控和日志

### 查看日志

```bash
# 实时日志
tail -f logs/trading_*.log

# 查看决策日志
tail -f logs/decisions_*.jsonl
```

### 查看运行状态

```bash
# 查看进程
ps aux | grep python.*main.py

# 查看PID
cat trading.pid
```

### 停止系统

```bash
# 使用PID停止
kill $(cat trading.pid)

# 或直接停止
pkill -f "python.*main.py"
```

## 📊 性能统计

系统会自动统计：

- 总交易次数
- 胜率
- 总盈亏
- 各币种表现
- 策略效果

查看统计：程序停止时会自动显示

## ⚠️ 风险提示

1. **加密货币交易有风险，投资需谨慎**
2. 建议先在**模拟盘**测试
3. 设置合理的**止损止盈**
4. 不要投入超过承受范围的资金
5. 定期检查系统运行状态

## 🔧 故障排查

### 导入错误

```bash
# 确保在项目根目录运行
cd /path/to/AI_Program_okex
python3.11 main.py
```

### 网络连接问题

```bash
# 设置代理（如果需要）
export https_proxy=http://127.0.0.1:7890
export http_proxy=http://127.0.0.1:7890
```

### API错误

- 检查 `.env` 文件配置
- 确认API密钥有效
- 检查IP白名单设置

## 📝 更新日志

### v2.0.0 (2025-11-01)

- ✅ 完成项目重构
- ✅ 模块化架构（config/, core/, data/, ai/, mcp/）
- ✅ main.py从1563行减少到377行（-76%）
- ✅ 清理所有emoji，提升兼容性
- ✅ 添加部署脚本
- ✅ 修复所有导入路径问题

### v1.0.0

- 初始版本
- 基础交易功能
- MCP记忆系统

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

## 📧 联系方式

- GitHub: [@jackymaxzzz](https://github.com/jackymaxzzz)
- 项目地址: https://github.com/jackymaxzzz/AI_Program_okex



---

⚡ **Powered by DeepSeek AI & OKX**
