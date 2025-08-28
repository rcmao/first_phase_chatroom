#!/usr/bin/env python3
"""
调试智能干预引擎的GPT调用问题
"""
import os
import sys
from dotenv import load_dotenv

# 设置路径
web_app_dir = os.path.join(os.path.dirname(__file__), 'web_app')
sys.path.insert(0, web_app_dir)

# 加载环境变量
env_files = ['.env', 'env.example']
for env_file in env_files:
    env_path = os.path.join(web_app_dir, env_file)
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"✅ 加载环境变量文件: {env_file}")
        break

# 导入智能引擎
from smart_intervention_engine import SmartInterventionEngine

def debug_engine():
    """调试智能引擎"""
    print("🔍 调试智能干预引擎...")
    
    # 创建引擎实例
    engine = SmartInterventionEngine()
    
    print(f"\n📋 引擎配置:")
    print(f"   llm_intervention_enabled: {engine.llm_intervention_enabled}")
    print(f"   llm_toxicity_enabled: {engine.llm_toxicity_enabled}")
    print(f"   llm_api_key: {'有 (' + engine.llm_api_key[:10] + '...)' if engine.llm_api_key else '无'}")
    print(f"   llm_base_url: {engine.llm_base_url}")
    print(f"   llm_model: {engine.llm_model}")
    print(f"   llm_message_model: {engine.llm_message_model}")
    print(f"   llm_timeout: {engine.llm_timeout}")
    print(f"   llm_conf_threshold: {engine.llm_conf_threshold}")
    print(f"   LLM连接状态: {engine.llm_connection_status}")
    
    # 测试LLM生成消息
    print(f"\n🤖 测试LLM消息生成...")
    
    # 模拟一些消息
    test_room_id = "1"
    engine.room_recent_messages[test_room_id].append({
        'username': 'Steve',
        'content': '巴萨现在还缺什么拼图',
        'timestamp': 1000,
        'user_id': '5'
    })
    engine.room_recent_messages[test_room_id].append({
        'username': 'Lily', 
        'content': '希望巴萨对我们太子好点',
        'timestamp': 1001,
        'user_id': '2'
    })
    
    # 测试不同类型的消息生成
    test_cases = [
        ('silence', {'user': 'Zack'}),
        ('turn_taking', {}),
        ('topic_pullback', {}),
        ('agenda', {})
    ]
    
    for kind, kwargs in test_cases:
        print(f"\n🧪 测试 {kind} 类型消息生成...")
        result = engine._llm_generate_message(kind, test_room_id, **kwargs)
        if result:
            print(f"   ✅ 成功: '{result}'")
        else:
            print(f"   ❌ 失败: 返回None")
    
    # 测试毒性检测
    print(f"\n🛡️ 测试毒性检测...")
    toxicity_result = engine._llm_classify_toxicity(test_room_id, last_n=5)
    if toxicity_result:
        print(f"   ✅ 毒性检测成功: {toxicity_result}")
    else:
        print(f"   ❌ 毒性检测失败: 返回None")

if __name__ == "__main__":
    try:
        debug_engine()
    except Exception as e:
        print(f"❌ 调试过程中出错: {e}")
        import traceback
        traceback.print_exc()
