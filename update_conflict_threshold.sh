#!/bin/bash

# 更新LLM冲突检测置信度阈值脚本
# 用途：将置信度阈值从0.6提高到0.85，减少误报

echo "🔧 正在更新LLM冲突检测置信度阈值..."

# 检查环境配置文件
ENV_FILE="web_app/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "📄 未找到.env文件，创建新的配置文件..."
    cp web_app/env.example "$ENV_FILE"
fi

# 更新或添加LLM_CONFLICT_THRESHOLD配置
if grep -q "^LLM_CONFLICT_THRESHOLD=" "$ENV_FILE"; then
    # 如果存在，则更新
    sed -i.bak 's/^LLM_CONFLICT_THRESHOLD=.*/LLM_CONFLICT_THRESHOLD=0.85/' "$ENV_FILE"
    echo "✅ 已更新现有配置: LLM_CONFLICT_THRESHOLD=0.85"
else
    # 如果不存在，则添加
    echo "" >> "$ENV_FILE"
    echo "# LLM冲突检测置信度阈值（减少误报）" >> "$ENV_FILE"
    echo "LLM_CONFLICT_THRESHOLD=0.85" >> "$ENV_FILE"
    echo "✅ 已添加新配置: LLM_CONFLICT_THRESHOLD=0.85"
fi

echo ""
echo "🎯 配置更新完成！新的配置将："
echo "   - 将冲突检测置信度阈值从0.6提高到0.85"
echo "   - 大幅减少正常足球讨论被误判为冲突的情况"
echo "   - 只有非常明确的冲突才会触发干预"
echo ""
echo "⚠️  请重启应用以使配置生效："
echo "   cd web_app && python app.py"
echo ""

# 显示当前配置
echo "📋 当前相关配置："
grep -E "^(LLM_CONFLICT_THRESHOLD|CONFLICT_DETECTION_STRATEGY|LLM_CONFLICT_FALLBACK)=" "$ENV_FILE" || echo "   (配置项不存在)"
