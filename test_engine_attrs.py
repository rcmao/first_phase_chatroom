#!/usr/bin/env python3
"""
测试SmartInterventionEngine的属性
"""

import sys
import os
sys.path.append('/Users/apple/Desktop/first_phase_chatroom/web_app')

from smart_intervention_engine import SmartInterventionEngine

def test_engine_attributes():
    """测试SmartInterventionEngine是否有所需的属性"""
    
    print("🔍 测试SmartInterventionEngine属性...")
    
    # 创建实例
    engine = SmartInterventionEngine()
    
    # 检查必需的属性
    required_attrs = [
        'room_last_intervention_ts',
        'room_last_agenda_transition',
        '_check_agenda_transition'
    ]
    
    print(f"✅ SmartInterventionEngine实例创建成功")
    
    for attr in required_attrs:
        if hasattr(engine, attr):
            print(f"✅ 属性 {attr} 存在")
            if callable(getattr(engine, attr)):
                print(f"  └─ {attr} 是方法")
            else:
                print(f"  └─ {attr} 是属性，值: {getattr(engine, attr)}")
        else:
            print(f"❌ 属性 {attr} 缺失")
    
    # 测试方法调用
    try:
        result = engine._check_agenda_transition("1")
        print(f"✅ _check_agenda_transition方法调用成功，返回: {result}")
    except Exception as e:
        print(f"❌ _check_agenda_transition方法调用失败: {e}")

if __name__ == "__main__":
    test_engine_attributes()
