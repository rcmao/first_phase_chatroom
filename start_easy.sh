#!/bin/bash

# TKI智能干预聊天机器人 - 快速启动脚本
# 修正版本 - 适配正确的项目路径

# 确保在正确的项目目录
cd /Users/apple/Desktop/first_phase_chatroom_v1

# 激活虚拟环境（优先使用venv）
if [ -d "venv" ]; then
    echo "🔧 激活虚拟环境: venv"
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "🔧 激活虚拟环境: .venv"
    source .venv/bin/activate
else
    echo "❌ 未找到虚拟环境，请先创建虚拟环境"
    exit 1
fi

# 设置Python路径
export PYTHONPATH="$PWD:$PWD/web_app:$PWD/src"

# 设置OpenAI配置（从.env文件读取，或使用默认值）
if [ -f "web_app/.env" ]; then
    echo "📁 加载环境变量文件: web_app/.env"
    export $(cat web_app/.env | grep -v '^#' | xargs)
else
    echo "⚠️  未找到.env文件，使用默认配置"
    export OPENAI_API_KEY="sk-XGGe5y0ZvLcQVFp6XnRizs7q47gsVnAbZx0Xr2mfcVlbr99f"
    export OPENAI_BASE_URL="https://api2.aigcbest.top/v1"
    export OPENAI_API_BASE="https://api2.aigcbest.top/v1"
fi

# 显示启动信息
echo ""
echo "🚀 启动TKI智能干预聊天机器人..."
echo "📂 项目路径: $PWD"
echo "🐍 Python路径: $PYTHONPATH"
echo "🔑 OpenAI API: ${OPENAI_BASE_URL:-https://api2.aigcbest.top/v1}"
echo "🤖 LLM功能: 自动启用"
echo ""

# 检查依赖
echo "🔍 检查依赖..."
cd web_app
if ! python -c "import flask" 2>/dev/null; then
    echo "⚠️  Flask未安装，正在安装依赖..."
    pip install -r requirements.txt
fi

# 启动应用
echo "🎯 启动Web应用..."
python start_web.py
