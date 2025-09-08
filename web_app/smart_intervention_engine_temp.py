# 这是需要修改的代码片段，请手动复制到 smart_intervention_engine.py 的对应位置

# 修改1: _analyze_llm_conflict 方法 (第1972-1987行)
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
