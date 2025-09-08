# LLM优先冲突检测配置说明

## 🎯 概述

冲突检测已升级为**LLM优先**架构，能够更准确地识别隐含的冲突、讽刺和情绪化表达。

## 📊 新架构特点

### 1. **检测优先级**
```
🔴 优先级1: 毒性检测 (词库优先) -> 立即处理明确违规
🟡 优先级2: 冲突检测 (LLM优先)  -> 智能识别争论升级
```

### 2. **冲突检测策略**
- **LLM优先** (推荐): LLM主导，关键词fallback
- **关键词优先**: 关键词主导，LLM补充
- **混合模式**: 平衡两种方法

## ⚙️ 配置选项

```bash
# 冲突检测策略配置
CONFLICT_DETECTION_STRATEGY=llm_primary  # 'llm_primary', 'keyword_primary', 'hybrid'
LLM_CONFLICT_THRESHOLD=0.85              # LLM冲突检测置信度阈值 (减少误报)
LLM_CONFLICT_FALLBACK=true               # LLM失败时是否回退到关键词检测

# LLM增强配置
LLM_ENABLED=true                         # 启用LLM功能
LLM_CONFIDENCE_THRESHOLD=0.7             # LLM毒性检测置信度阈值
LLM_MODEL=gpt-4o-mini                    # 使用的LLM模型
```

## 🚀 新功能特性

### 1. **智能冲突识别**
- **讽刺挖苦**: "哦，你最懂了"
- **隐含攻击**: "就你这种水平"
- **情绪升级**: 检测争论激化趋势
- **语境理解**: 考虑对话历史和参与者关系

### 2. **多重保障机制**
- **LLM失败**: 自动fallback到关键词检测
- **置信度过滤**: 避免误报
- **缓存机制**: 提高响应速度，降低成本
- **错误处理**: 完善的异常处理

### 3. **灵活配置**
- **策略切换**: 可在不同检测策略间切换
- **阈值调节**: 根据需要调整敏感度
- **Fallback控制**: 可选择是否启用备选方案

## 📈 检测效果对比

| 场景 | 传统关键词检测 | LLM优先检测 |
|------|---------------|-------------|
| 明确冲突词 | ✅ 准确 | ✅ 准确 |
| 隐含讽刺 | ❌ 遗漏 | ✅ 识别 |
| 语境相关 | ❌ 误报 | ✅ 准确 |
| 新网络用语 | ❌ 遗漏 | ✅ 识别 |

## 🔧 使用建议

### 推荐配置 (生产环境)
```bash
CONFLICT_DETECTION_STRATEGY=llm_primary
LLM_CONFLICT_THRESHOLD=0.85
LLM_CONFLICT_FALLBACK=true
```

### 保守配置 (测试环境)
```bash
CONFLICT_DETECTION_STRATEGY=keyword_primary
LLM_CONFLICT_THRESHOLD=0.8
LLM_CONFLICT_FALLBACK=false
```

## 📝 日志示例

成功检测：
```
🤖 [冲突检测] ✅ 检测到medium级冲突风险 (置信度: 0.80)
```

Fallback触发：
```
🤖 [冲突检测] API调用失败，触发fallback
🤖 [Fallback检测] ✅ 关键词检测到冲突: high风险
```

置信度过滤：
```
🤖 [冲突检测] 置信度不足: 0.3 < 0.6
```

## 🎯 监控建议

1. **关注指标**:
   - LLM调用成功率
   - Fallback触发频率
   - 检测准确率
   - 响应时间

2. **调优建议**:
   - 根据误报率调整阈值
   - 定期审查检测结果
   - 监控成本使用情况

## 🚀 升级完成

冲突检测已成功升级为LLM优先架构，在保持原有稳定性的基础上，大幅提升了复杂语境下的检测准确性！

