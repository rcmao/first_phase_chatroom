# 修改2: _perform_llm_conflict_detection 方法 (第2127-2142行)
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
