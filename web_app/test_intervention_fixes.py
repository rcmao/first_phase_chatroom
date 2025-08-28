#!/usr/bin/env python3
"""
测试干预引擎修复效果的脚本
模拟之前出现问题的聊天场景
"""

import sys
import os
import time
from smart_intervention_engine import SmartInterventionEngine

def test_overcall_prevention():
    """测试过度干预的修复"""
    print("=== 测试过度干预修复 ===")
    
    engine = SmartInterventionEngine()
    room_id = "test_room"
    
    # 模拟正常的足球讨论（应该不被频繁打断）
    messages = [
        ("lily", "Lily", "我是椰子树_切尔西"),
        ("zack", "Zack", "我是慕捷君巴黎圣日耳曼"),
        ("lily", "Lily", "有皇马怎么玩儿呀。。。但是我还是觉得切尔西是全世界最好的球队"),
        ("lily", "Lily", "真的有巴黎球迷，宝你是什么时候喜欢上大巴黎的呀"),
        ("zack", "Zack", "切尔西虽然拿了世俱杯冠军  但是我还是支持皇马"),
        ("steve", "Steve", "要是只按现在来说的话都有资格成为最好的球队"),
        ("lily", "Lily", "要是按现在说的话，咱们仨的球队就是欧洲前三"),
        ("lily", "Lily", "那你真的看法甲吗，法甲时间那么阴间"),
        ("zack", "Zack", "法甲不精彩呀"),
        ("lily", "Lily", "其实西甲的时间也很阴间哈哈哈，那从这点上还是英超比较好，切尔西秒了"),
    ]
    
    intervention_count = 0
    for i, (user_id, username, content) in enumerate(messages):
        print(f"\n消息 {i+1}: {username}: {content}")
        
        # 模拟时间间隔
        time.sleep(0.1)
        
        result = engine.analyze_message(room_id, user_id, username, content)
        if result and result.should_intervene:
            intervention_count += 1
            print(f"  🤖 干预: {result.message}")
            print(f"  原因: {result.reason}")
            
            # 检查是否是重复干预（90秒内相同消息）
            if intervention_count > 1:
                print(f"  ⚠️  可能的重复干预！")
        else:
            print(f"  ✅ 无干预")
    
    print(f"\n总干预次数: {intervention_count}")
    return intervention_count

def test_turn_taking_threshold():
    """测试有序轮次阈值优化"""
    print("\n=== 测试有序轮次阈值优化 ===")
    
    engine = SmartInterventionEngine()
    room_id = "test_room2"
    
    # Lily的连续短句（之前会被误判）
    messages = [
        ("lily", "Lily", "要是按现在说的话，咱们仨的球队就是欧洲前三"),
        ("lily", "Lily", "哇哦好早"),
        ("lily", "Lily", "那你真的看法甲吗，法甲时间那么阴间"),
        ("steve", "Steve", "有时候看"),  # 有人回应
        ("lily", "Lily", "其实西甲的时间也很阴间哈哈哈"),
    ]
    
    turn_taking_triggered = False
    for i, (user_id, username, content) in enumerate(messages):
        print(f"\n消息 {i+1}: {username}: {content}")
        result = engine.analyze_message(room_id, user_id, username, content)
        
        if result and result.should_intervene and "轮次" in result.reason:
            turn_taking_triggered = True
            print(f"  🤖 轮次提醒: {result.message}")
            print(f"  原因: {result.reason}")
        else:
            print(f"  ✅ 无轮次干预")
    
    print(f"\n是否触发轮次提醒: {turn_taking_triggered}")
    return turn_taking_triggered

def test_football_topic_protection():
    """测试足球话题保护（避免误判跑题）"""
    print("\n=== 测试足球话题保护 ===")
    
    engine = SmartInterventionEngine()
    room_id = "test_room3"
    
    # 仍在聊足球但话题略有跳跃的对话
    messages = [
        ("lily", "Lily", "切尔西虽然拿了世俱杯冠军"),
        ("zack", "Zack", "法甲不精彩呀"),
        ("steve", "Steve", "西甲的时间也很阴间哈哈哈"),
        ("lily", "Lily", "英超比较好"),
        ("zack", "Zack", "大巴黎落寞了"),
        ("steve", "Steve", "法国的联赛一直搞不起来"),
    ]
    
    topic_pullback_triggered = False
    for i, (user_id, username, content) in enumerate(messages):
        print(f"\n消息 {i+1}: {username}: {content}")
        result = engine.analyze_message(room_id, user_id, username, content)
        
        if result and result.should_intervene and "话题" in result.reason:
            topic_pullback_triggered = True
            print(f"  🤖 话题引导: {result.message}")
            print(f"  原因: {result.reason}")
        else:
            print(f"  ✅ 无话题干预")
    
    print(f"\n是否触发话题拉回: {topic_pullback_triggered}")
    return topic_pullback_triggered

def main():
    print("🔧 测试智能干预引擎修复效果\n")
    
    # 测试1: 过度干预修复
    intervention_count = test_overcall_prevention()
    
    # 测试2: 有序轮次阈值优化  
    turn_taking_triggered = test_turn_taking_threshold()
    
    # 测试3: 足球话题保护
    topic_pullback_triggered = test_football_topic_protection()
    
    print("\n" + "="*50)
    print("📊 测试结果总结:")
    print(f"1. 干预频率控制: {intervention_count} 次干预 {'✅ 合理' if intervention_count <= 2 else '❌ 仍过多'}")
    print(f"2. 轮次提醒优化: {'❌ 仍误触发' if turn_taking_triggered else '✅ 未误触发'}")
    print(f"3. 足球话题保护: {'❌ 仍误判跑题' if topic_pullback_triggered else '✅ 未误判'}")
    
    overall_success = (intervention_count <= 2 and 
                      not turn_taking_triggered and 
                      not topic_pullback_triggered)
    
    print(f"\n总体评估: {'✅ 修复成功' if overall_success else '❌ 需要进一步调整'}")

if __name__ == "__main__":
    main()
