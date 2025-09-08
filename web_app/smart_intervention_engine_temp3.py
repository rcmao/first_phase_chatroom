# 修改3: ConflictDetector.should_intervene 方法 (第307-324行)
    def should_intervene(self, context_analysis: ContextualAnalysis) -> bool:
        """判断是否需要冲突干预 - 仅高风险时介入"""
        # 只在高风险时介入，避免过度干预
        return context_analysis.escalation_risk == 'high'
