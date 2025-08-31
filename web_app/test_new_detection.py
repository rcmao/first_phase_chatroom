#!/usr/bin/env python3
"""
测试新的毒性检测和冲突检测系统
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from smart_intervention_engine import (
    SmartInterventionEngine, 
    ContentAnalyzer, 
    ToxicityDetector, 
    ConflictDetector,
    ToxicityLevel,
    ConflictLevel,
    InterventionType
)

def test_content_analyzer():
    """测试内容分析器"""
    print("🧪 测试ContentAnalyzer...")
    
    analyzer = ContentAnalyzer()
    
    # 测试毒性内容
    test_cases = [
        ("你这个垃圾", "应该检测到SEVERE毒性"),
        ("你不懂球", "应该检测到MODERATE毒性"), 
        ("你说得不对", "应该检测到冲突信号"),
        ("巴萨狗真恶心", "应该检测到领域特定违规"),
        ("我觉得皇马很强", "应该是正常内容")
    ]
    
    for message, expected in test_cases:
        result = analyzer.analyze_content(message)
        print(f"  消息: '{message}'")
        print(f"  期望: {expected}")
        print(f"  结果: 毒性={result.toxicity_level.name}, 冲突信号={len(result.conflict_signals)}, 领域违规={len(result.domain_violations)}")
        print(f"  置信度: {result.confidence:.2f}")
        print()

def test_toxicity_detector():
    """测试毒性检测器"""
    print("🧪 测试ToxicityDetector...")
    
    analyzer = ContentAnalyzer()
    detector = ToxicityDetector(analyzer)
    
    test_cases = [
        "你这个垃圾",  # 应该触发干预
        "你不懂球",    # 应该触发干预
        "我不同意",    # 不应该触发干预
    ]
    
    for message in test_cases:
        content_analysis = analyzer.analyze_content(message)
        should_intervene = detector.should_intervene(content_analysis)
        intervention_msg = detector.get_intervention_message(content_analysis, "TestUser") if should_intervene else "无需干预"
        
        print(f"  消息: '{message}'")
        print(f"  是否干预: {should_intervene}")
        print(f"  干预消息: {intervention_msg}")
        print()

def test_conflict_detector():
    """测试冲突检测器"""
    print("🧪 测试ConflictDetector...")
    
    analyzer = ContentAnalyzer()
    detector = ConflictDetector(analyzer)
    
    # 模拟对话历史
    conversation_history = [
        {'user_id': '1', 'username': 'Alice', 'content': '我觉得皇马更强', 'timestamp': 1000},
        {'user_id': '2', 'username': 'Bob', 'content': '你说得不对，巴萨才是最强的', 'timestamp': 1010},
        {'user_id': '1', 'username': 'Alice', 'content': '你懂个屁，皇马明显更厉害', 'timestamp': 1020},
        {'user_id': '2', 'username': 'Bob', 'content': '你就你懂，巴萨的传控无人能敌', 'timestamp': 1030},
    ]
    
    context_analysis = detector.analyze_escalation_risk(conversation_history)
    should_intervene = detector.should_intervene(context_analysis)
    intervention_type = detector.get_intervention_type(context_analysis) if should_intervene else None
    intervention_msg = detector.get_intervention_message(context_analysis) if should_intervene else "无需干预"
    
    print(f"  升级风险: {context_analysis.escalation_risk}")
    print(f"  交互模式: {context_analysis.interaction_pattern}")
    print(f"  情绪趋势: {context_analysis.emotion_trend}")
    print(f"  是否干预: {should_intervene}")
    print(f"  干预类型: {intervention_type.value if intervention_type else 'None'}")
    print(f"  干预消息: {intervention_msg}")
    print()

def test_unified_engine():
    """测试统一干预引擎"""
    print("🧪 测试SmartInterventionEngine...")
    
    # 设置测试环境变量
    os.environ['DETECTION_MODE'] = 'hybrid'
    os.environ['TOXICITY_ZERO_TOLERANCE'] = 'true'
    os.environ['CONFLICT_MODE'] = 'proactive'
    
    engine = SmartInterventionEngine()
    
    test_cases = [
        ("你这个垃圾", "应该触发毒性警告"),
        ("你说得不对", "可能触发冲突检测"),
        ("巴萨狗恶心死了", "应该触发毒性警告"),
        ("我觉得皇马很强", "应该无需干预")
    ]
    
    room_id = "test_room"
    user_id = "test_user"
    username = "TestUser"
    
    for i, (message, expected) in enumerate(test_cases):
        print(f"  测试 {i+1}: '{message}' ({expected})")
        result = engine.analyze_message(room_id, user_id, username, message)
        
        if result:
            print(f"    ✅ 触发干预: {result.intervention_type.value}")
            print(f"    消息: {result.message}")
            print(f"    原因: {result.reason}")
            print(f"    等级: {result.offense_level.name if result.offense_level else 'None'}")
            print(f"    通过LLM: {result.via_llm}")
        else:
            print(f"    ✅ 无需干预")
        print()

def main():
    """运行所有测试"""
    print("🚀 开始测试新的检测系统\n")
    
    test_content_analyzer()
    test_toxicity_detector()
    test_conflict_detector()
    test_unified_engine()
    
    print("✅ 所有测试完成!")

if __name__ == "__main__":
    main()
