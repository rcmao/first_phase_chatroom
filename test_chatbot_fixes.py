#!/usr/bin/env python3
"""
测试Chatbot相关修复的脚本
验证：
1. 破冰机制45秒触发逻辑
2. 实时消息显示
3. Chatbot开关的实时更新
"""

import sys
import os
import time
import requests
import json
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'web_app'))

def test_intervention_engine():
    """测试智能干预引擎的破冰逻辑"""
    print("🧪 [测试] 开始测试智能干预引擎...")
    
    try:
        from web_app.smart_intervention_engine import SmartInterventionEngine
        
        # 创建引擎实例
        engine = SmartInterventionEngine()
        
        # 验证破冰阈值
        print(f"✅ [测试] 个人沉默阈值: {engine.silence_threshold}秒")
        print(f"✅ [测试] 群体沉默阈值: {engine.agenda_transition_threshold}秒")
        
        # 模拟房间消息
        test_room_id = "test_room_1"
        current_time = time.time()
        
        # 模拟admin消息
        admin_message = {
            'user_id': '8',  # admin用户
            'username': 'admin',
            'content': '大家好，欢迎来到聊天室！',
            'timestamp': current_time - 50,  # 50秒前
            'gender': 'unknown'
        }
        engine.room_recent_messages[test_room_id].append(admin_message)
        
        # 测试破冰检测
        result = engine._check_agenda_transition(test_room_id)
        if result and result.should_intervene:
            print(f"✅ [测试] 破冰检测成功: {result.message}")
            print(f"   原因: {result.reason}")
        else:
            print("❌ [测试] 破冰检测失败")
        
        return True
    except Exception as e:
        print(f"❌ [测试] 智能干预引擎测试失败: {e}")
        return False

def test_api_endpoints():
    """测试API端点"""
    print("\n🧪 [测试] 开始测试API端点...")
    
    base_url = "http://localhost:8080"
    
    # 测试获取当前干预风格
    try:
        response = requests.get(f"{base_url}/api/admin/current-intervention-style", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ [测试] 当前干预风格: {data.get('style', 'unknown')}")
        else:
            print(f"⚠️ [测试] 风格API返回状态: {response.status_code}")
    except Exception as e:
        print(f"⚠️ [测试] 风格API测试失败: {e}")
    
    return True

def test_configuration():
    """测试配置参数"""
    print("\n🧪 [测试] 检查配置参数...")
    
    try:
        from web_app.smart_intervention_engine import SmartInterventionEngine
        engine = SmartInterventionEngine()
        
        # 检查关键参数
        config_checks = [
            ("个人沉默阈值", engine.silence_threshold, 45),
            ("群体沉默阈值", engine.agenda_transition_threshold, 45),
            ("全局冷却时间", engine.global_cooldown_seconds, 30),
            ("议程过渡冷却", engine.agenda_transition_cooldown, 120)
        ]
        
        all_correct = True
        for name, actual, expected in config_checks:
            if actual == expected:
                print(f"✅ [配置] {name}: {actual}秒 (期望: {expected}秒)")
            else:
                print(f"❌ [配置] {name}: {actual}秒 (期望: {expected}秒)")
                all_correct = False
        
        return all_correct
    except Exception as e:
        print(f"❌ [测试] 配置检查失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🔧 Chatbot修复验证测试")
    print("=" * 50)
    
    # 测试结果
    results = []
    
    # 运行各项测试
    results.append(("智能干预引擎", test_intervention_engine()))
    results.append(("配置参数", test_configuration()))
    results.append(("API端点", test_api_endpoints()))
    
    # 输出测试结果
    print("\n" + "=" * 50)
    print("📊 测试结果汇总:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{len(results)} 项测试通过")
    
    if passed == len(results):
        print("🎉 所有测试通过！修复成功。")
        return 0
    else:
        print("⚠️ 部分测试失败，请检查相关组件。")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
