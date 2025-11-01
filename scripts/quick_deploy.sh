#!/bin/bash

# 快速部署脚本 - 只同步变更的文件
# 用法: ./quick_deploy.sh <服务器IP>

set -e

REMOTE_HOST="$1"
REMOTE_PATH="${2:-/home/ubuntu/alpha-arena/multi_agent_trading}"
REMOTE_USER="${3:-ubuntu}"

if [ -z "$REMOTE_HOST" ]; then
    echo "用法: ./quick_deploy.sh <服务器IP> [远程路径] [用户名]"
    echo "示例: ./quick_deploy.sh 192.168.1.100"
    exit 1
fi

echo "🚀 快速部署到 ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}"
echo ""

# 只同步Python文件和配置
echo "📦 同步变更文件..."
rsync -avz --progress \
    --include='*.py' \
    --include='*.txt' \
    --include='*.json' \
    --include='*.sh' \
    --include='prompts/***' \
    --include='config/***' \
    --include='core/***' \
    --include='data/***' \
    --include='ai/***' \
    --include='mcp/***' \
    --include='utils/***' \
    --exclude='*' \
    ./ ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/

echo ""
echo "✓ 部署完成！"
echo ""
echo "重启服务: ssh ${REMOTE_USER}@${REMOTE_HOST} 'cd ${REMOTE_PATH} && ./restart.sh'"
