#!/bin/bash

# 服务器端重启脚本
# 在服务器上运行: ./restart.sh

echo "🔄 重启交易系统..."

# 停止旧进程
if [ -f "trading.pid" ]; then
    OLD_PID=$(cat trading.pid)
    if ps -p $OLD_PID > /dev/null 2>&1; then
        echo "停止旧进程: $OLD_PID"
        kill $OLD_PID
        sleep 2
        
        # 强制杀死（如果还在运行）
        if ps -p $OLD_PID > /dev/null 2>&1; then
            echo "强制停止..."
            kill -9 $OLD_PID
        fi
    fi
fi

# 清理旧的PID文件
rm -f trading.pid

# 启动新进程
echo "启动新进程..."
nohup python3.11 main.py > logs/trading_$(date +%Y%m%d_%H%M%S).log 2>&1 &
NEW_PID=$!

# 保存PID
echo $NEW_PID > trading.pid
echo "✓ 新进程已启动: $NEW_PID"

# 等待并验证
sleep 2
if ps -p $NEW_PID > /dev/null 2>&1; then
    echo "✓ 交易系统运行正常"
    echo ""
    echo "查看日志: tail -f logs/trading_$(date +%Y%m%d)*.log"
else
    echo "✗ 启动失败，请检查日志"
    exit 1
fi
