#!/usr/bin/env python3
"""
测试消息显示功能
"""

import time
import requests
import json

def test_message_display():
    """测试消息发送和显示"""
    base_url = "http://localhost:8080"
    
    # 测试用户登录（这里需要有效的用户凭据）
    print("🧪 测试消息显示功能...")
    
    # 1. 检查服务状态
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            print("✅ 服务运行正常")
        else:
            print(f"❌ 服务响应异常: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ 无法连接到服务: {e}")
        return
    
    # 2. 测试房间API
    try:
        response = requests.get(f"{base_url}/api/rooms", timeout=5)
        if response.status_code == 200:
            rooms = response.json()
            print(f"✅ 房间API正常，共{len(rooms)}个房间")
            if rooms:
                room_id = rooms[0]['id']
                print(f"📝 测试房间ID: {room_id}")
        else:
            print(f"❌ 房间API响应异常: {response.status_code}")
    except Exception as e:
        print(f"❌ 房间API错误: {e}")
    
    print("\n🎯 建议手动测试：")
    print("1. 打开浏览器访问 http://localhost:8080/")
    print("2. 登录并进入任一聊天室")
    print("3. 发送几条消息观察是否立即显示")
    print("4. 检查浏览器控制台的WebSocket日志")
    print("5. 验证新的沉默阈值设置（个人60秒，群体45秒）")

if __name__ == '__main__':
    test_message_display()
