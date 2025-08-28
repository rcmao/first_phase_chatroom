#!/usr/bin/env python3
"""
测试破冰触发修复
验证点击Chatbot按钮是否能正确触发破冰，即使按钮之前已经是启用状态
"""

import sys
import os
import time
import requests
import json

def test_chatbot_button_trigger():
    """测试Chatbot按钮触发破冰"""
    print("🧪 测试Chatbot按钮触发破冰...")
    
    base_url = "http://127.0.0.1:5000"
    
    try:
        # 1. 检查当前Chatbot状态
        response = requests.get(f"{base_url}/api/admin/chatbot/enabled")
        if response.status_code == 200:
            current_status = response.json()
            print(f"  当前Chatbot状态: {current_status}")
        else:
            print(f"  ❌ 无法获取Chatbot状态: {response.status_code}")
            return
        
        # 2. 模拟点击按钮 - 发送当前相同的状态（应该触发破冰）
        enabled_value = current_status.get('enabled', True)
        
        print(f"  📤 发送Chatbot状态: enabled={enabled_value}")
        response = requests.post(
            f"{base_url}/api/admin/chatbot/enabled",
            json={'enabled': enabled_value},
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"  ✅ Chatbot按钮请求成功: {result}")
            print("  🎯 检查服务器日志以确认是否触发了破冰...")
        else:
            print(f"  ❌ Chatbot按钮请求失败: {response.status_code}")
            print(f"  错误内容: {response.text}")
        
        # 3. 测试切换状态
        print(f"\n  🔄 测试状态切换...")
        
        # 先设为false
        response = requests.post(
            f"{base_url}/api/admin/chatbot/enabled",
            json={'enabled': False},
            headers={'Content-Type': 'application/json'}
        )
        if response.status_code == 200:
            print("  📴 Chatbot已禁用")
            time.sleep(1)
            
            # 再设为true（应该触发破冰）
            response = requests.post(
                f"{base_url}/api/admin/chatbot/enabled",
                json={'enabled': True},
                headers={'Content-Type': 'application/json'}
            )
            if response.status_code == 200:
                print("  🟢 Chatbot已重新启用，应该触发破冰")
            else:
                print(f"  ❌ 重新启用失败: {response.status_code}")
        
        print("  ✅ 测试完成，请检查服务器日志中的破冰触发信息")
        
    except requests.exceptions.ConnectionError:
        print("  ❌ 无法连接到服务器，请确保服务器正在运行 (http://127.0.0.1:5000)")
    except Exception as e:
        print(f"  ❌ 测试异常: {e}")

if __name__ == "__main__":
    print("🚀 开始测试Chatbot按钮破冰触发...")
    print("=" * 60)
    
    test_chatbot_button_trigger()
    
    print("=" * 60)
    print("💡 修复说明:")
    print("   ✅ 即使Chatbot按钮之前已经是启用状态")
    print("   ✅ 点击按钮时也会主动触发破冰检查")
    print("   ✅ 破冰触发会重置所有冷却时间")
    print("   🔍 请查看服务器终端日志确认触发结果")

