# 冲突检测修改指南 - 仅高风险介入

## 需要修改的文件
`web_app/smart_intervention_engine.py`

## 修改内容

### 1. 修改第1972-1987行 (_analyze_llm_conflict 方法)

**原代码：**
```python
        # 检查升级风险等级
        if escalation_risk not in ['medium', 'high']:
            return None
            
        # 检查全局冷却
        if self._is_global_cooldown_active(room_id, current_time):
            return None
            
        # 根据升级风险选择干预类型和消息
        if escalation_risk == 'high':
            intervention_type = InterventionType.EMERGENCY_DEESCALATION
            message = "讨论有点激烈，我们暂停一下，放松心态继续交流。"
            priority = 'high'
        else:  # medium
            intervention_type = InterventionType.CONFLICT_DEESCALATION
            message = "大家讨论挺热烈的，注意保持友善哦～"
            priority = 'contextual'
```

**修改为：**
```python
        # 检查升级风险等级 - 只在高风险时介入
        if escalation_risk != 'high':
            print(f"🤖 [冲突检测] 风险等级为{escalation_risk}，仅在高风险时介入")
            return None
            
        # 检查全局冷却
        if self._is_global_cooldown_active(room_id, current_time):
            return None
            
        # 生成干预决策（仅针对高风险）
        intervention_type = InterventionType.EMERGENCY_DEESCALATION
        message = "讨论有点激烈，我们暂停一下，放松心态继续交流。"
        priority = 'high'
```

### 2. 修改第2127-2142行 (_perform_llm_conflict_detection 方法)

**原代码：**
```python
            if escalation_risk not in ['medium', 'high']:
                return None
                
            # 检查冷却
            if self._is_global_cooldown_active(room_id, current_time):
                return None
                
            # 生成干预决策
            if escalation_risk == 'high':
                intervention_type = InterventionType.EMERGENCY_DEESCALATION
                message = intervention_suggestion or "讨论有点激烈，我们暂停一下，放松心态继续交流。"
                priority = 'high'
            else:  # medium
                intervention_type = InterventionType.CONFLICT_DEESCALATION  
                message = intervention_suggestion or "大家讨论挺热烈的，注意保持友善哦～"
                priority = 'contextual'
```

**修改为：**
```python
            # 只在高风险时才介入，避免过度干预  
            if escalation_risk != 'high':
                print(f"🤖 [冲突检测] 风险等级为{escalation_risk}，仅在高风险时介入")
                return None
                
            # 检查冷却
            if self._is_global_cooldown_active(room_id, current_time):
                return None
                
            # 生成干预决策（仅针对高风险）
            intervention_type = InterventionType.EMERGENCY_DEESCALATION
            message = intervention_suggestion or "讨论有点激烈，我们暂停一下，放松心态继续交流。"
            priority = 'high'
```

### 3. 修改第307-324行 (ConflictDetector.should_intervene 方法)

**原代码：**
```python
    def should_intervene(self, context_analysis: ContextualAnalysis) -> bool:
        """判断是否需要冲突干预"""
        if context_analysis.escalation_risk == 'high':
            return True
        
        if (context_analysis.escalation_risk == 'medium' and 
            context_analysis.interaction_pattern in ['heated_exchange', 'bullying']):
            return True
        
        if not self.proactive_mode:
            return False
        
        # 主动模式下的预防性干预
        if (context_analysis.escalation_risk == 'medium' and 
            context_analysis.emotion_trend == 'rising'):
            return True
        
        return False
```

**修改为：**
```python
    def should_intervene(self, context_analysis: ContextualAnalysis) -> bool:
        """判断是否需要冲突干预 - 仅高风险时介入"""
        # 只在高风险时介入，避免过度干预
        return context_analysis.escalation_risk == 'high'
```

## 修改效果

- ✅ 大幅减少误判：正常的足球讨论不会再触发干预
- ✅ 只处理真正的冲突：仅当LLM判断为"高"风险时才介入
- ✅ 清晰的日志输出：显示为什么不介入的原因
- ✅ 避免过度干预：让用户能够自然交流

## 测试建议

修改后，可以测试以下场景：
1. 正常的足球战术讨论（应该不触发干预）
2. 球队评价和观点表达（应该不触发干预）
3. 真正的人身攻击（应该触发干预）

修改完成后重启应用即可生效。
