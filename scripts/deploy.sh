#!/bin/bash

# 自动部署脚本
# 用法: ./deploy.sh [remote_host] [remote_path]

set -e  # 遇到错误立即退出

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Alpha Arena 交易系统自动部署${NC}"
echo -e "${GREEN}========================================${NC}\n"

# 默认配置
REMOTE_HOST="${1:-your_server_ip}"
REMOTE_PATH="${2:-/home/ubuntu/alpha-arena/multi_agent_trading}"
REMOTE_USER="${3:-ubuntu}"

# 检查参数
if [ "$REMOTE_HOST" = "your_server_ip" ]; then
    echo -e "${RED}错误: 请提供服务器地址${NC}"
    echo "用法: ./deploy.sh <服务器IP> [远程路径] [用户名]"
    echo "示例: ./deploy.sh 192.168.1.100 /home/ubuntu/trading ubuntu"
    exit 1
fi

echo -e "${YELLOW}[1/6] 检查Git状态...${NC}"
if [ -d ".git" ]; then
    git status
    echo ""
    read -p "是否提交当前更改? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "提交信息: " commit_msg
        git add -A
        git commit -m "$commit_msg" || echo "没有需要提交的更改"
        git push origin main || echo "推送失败，请检查远程仓库"
    fi
else
    echo -e "${YELLOW}警告: 不是Git仓库，将直接同步文件${NC}"
fi

echo -e "\n${YELLOW}[2/6] 同步文件到服务器...${NC}"
# 排除不需要同步的文件
rsync -avz --progress \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.DS_Store' \
    --exclude='logs/' \
    --exclude='*.log' \
    --exclude='data/trades.db' \
    --exclude='data/mcp_memory_*.json' \
    --exclude='.env' \
    ./ ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 文件同步成功${NC}"
else
    echo -e "${RED}✗ 文件同步失败${NC}"
    exit 1
fi

echo -e "\n${YELLOW}[3/6] 检查远程环境...${NC}"
ssh ${REMOTE_USER}@${REMOTE_HOST} << 'ENDSSH'
cd ${REMOTE_PATH}
echo "当前目录: $(pwd)"
echo "Python版本: $(python3 --version)"
echo "文件列表:"
ls -lh
ENDSSH

echo -e "\n${YELLOW}[4/6] 安装/更新依赖...${NC}"
ssh ${REMOTE_USER}@${REMOTE_HOST} << ENDSSH
cd ${REMOTE_PATH}
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt --quiet
    echo "依赖安装完成"
else
    echo "警告: 未找到requirements.txt"
fi
ENDSSH

echo -e "\n${YELLOW}[5/6] 重启交易系统...${NC}"
ssh ${REMOTE_USER}@${REMOTE_HOST} << ENDSSH
cd ${REMOTE_PATH}

# 查找并停止旧进程
OLD_PID=\$(ps aux | grep "python.*main.py" | grep -v grep | awk '{print \$2}')
if [ ! -z "\$OLD_PID" ]; then
    echo "停止旧进程: \$OLD_PID"
    kill \$OLD_PID
    sleep 2
fi

# 启动新进程（后台运行）
nohup python3.11 main.py > logs/trading_\$(date +%Y%m%d_%H%M%S).log 2>&1 &
NEW_PID=\$!
echo "新进程已启动: \$NEW_PID"

# 保存PID
echo \$NEW_PID > trading.pid
ENDSSH

echo -e "\n${YELLOW}[6/6] 验证部署...${NC}"
sleep 3
ssh ${REMOTE_USER}@${REMOTE_HOST} << ENDSSH
cd ${REMOTE_PATH}
if [ -f "trading.pid" ]; then
    PID=\$(cat trading.pid)
    if ps -p \$PID > /dev/null; then
        echo "✓ 交易系统运行中 (PID: \$PID)"
        echo ""
        echo "查看日志: tail -f logs/trading_*.log"
        echo "停止系统: kill \$PID"
    else
        echo "✗ 交易系统未运行"
        exit 1
    fi
else
    echo "✗ 未找到PID文件"
    exit 1
fi
ENDSSH

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  部署完成！${NC}"
echo -e "${GREEN}========================================${NC}\n"

echo "远程服务器: ${REMOTE_USER}@${REMOTE_HOST}"
echo "部署路径: ${REMOTE_PATH}"
echo ""
echo "常用命令:"
echo "  查看日志: ssh ${REMOTE_USER}@${REMOTE_HOST} 'tail -f ${REMOTE_PATH}/logs/trading_*.log'"
echo "  停止系统: ssh ${REMOTE_USER}@${REMOTE_HOST} 'kill \$(cat ${REMOTE_PATH}/trading.pid)'"
echo "  查看状态: ssh ${REMOTE_USER}@${REMOTE_HOST} 'ps aux | grep python.*main.py'"
