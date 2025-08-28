#!/bin/bash

# 简单启动脚本 - 永远不会出现LLM配置错误
cd /Users/apple/Desktop/first_phase_chatroom

# 激活虚拟环境
source .venv/bin/activate

# 设置Python路径
export PYTHONPATH="$PWD:$PWD/web_app:$PWD/src"

# 设置OpenAI配置（兼容多种变量名）
export OPENAI_API_KEY="sk-KCBDPG5Lv8hTCrArnkFSXY77wdJbLGzk0gkisq8T8IbjvfJb"
export OPENAI_BASE_URL="https://api2.aigcbest.top/v1"
export OPENAI_API_BASE="https://api2.aigcbest.top/v1"  # 备用兼容

# LLM功能会自动启用（有API密钥就启用）
echo "🚀 启动聊天室应用..."
echo "✅ OpenAI API: $OPENAI_BASE_URL"
echo "✅ LLM功能: 自动启用"

# 启动应用
python3 web_app/start_web.py
