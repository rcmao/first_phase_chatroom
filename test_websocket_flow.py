#!/usr/bin/env python3
"""
WebSocket消息流程测试脚本
用于诊断为什么发送消息后需要刷新页面才能看到的问题
"""

import requests
import time
import json
import sys
from socketio import SimpleClient

def test_websocket_flow():
    """测试WebSocket消息发送和接收流程"""
    
    print("🔍 开始测试WebSocket消息流程...")
    
    # 1. 先登录获取token
    login_url = "http://localhost:8080/api/login"
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        print("1. 尝试登录...")
        response = requests.post(login_url, json=login_data)
        if response.status_code != 200:
            print(f"❌ 登录失败: {response.status_code} - {response.text}")
            return
        
        token = response.json().get('token')
        print(f"✅ 登录成功，获取到token: {token[:20]}...")
        
    except Exception as e:
        print(f"❌ 登录请求失败: {e}")
        return
    
    # 2. 获取房间列表
    try:
        print("2. 获取房间列表...")
        rooms_response = requests.get(
            "http://localhost:8080/api/rooms",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if rooms_response.status_code != 200:
            print(f"❌ 获取房间列表失败: {rooms_response.status_code}")
            return
        
        rooms = rooms_response.json()
        if not rooms:
            print("❌ 没有找到任何房间")
            return
        
        room_id = rooms[0]['id']
        print(f"✅ 找到房间，使用房间ID: {room_id}")
        
    except Exception as e:
        print(f"❌ 获取房间列表失败: {e}")
        return
    
    # 3. 连接WebSocket
    try:
        print("3. 连接WebSocket...")
        sio = SimpleClient()
        
        # 连接到WebSocket服务器
        sio.connect(f'http://localhost:8080', headers={'Authorization': f'Bearer {token}'})
        print("✅ WebSocket连接成功")
        
        # 加入房间
        print(f"4. 加入房间 {room_id}...")
        sio.emit('join_room', {'room': str(room_id)})
        time.sleep(1)  # 等待加入房间
        
        print("5. 发送测试消息...")
        test_message = {
            'room': str(room_id),
            'message': {
                'content': f'WebSocket测试消息 - {int(time.time())}',
                'gender': 'unknown',
                'client_id': f'test-{int(time.time())}'
            }
        }
        
        print(f"发送消息数据: {test_message}")
        sio.emit('send_message', test_message)
        
        # 等待响应
        print("6. 等待消息响应...")
        time.sleep(3)
        
        # 检查是否收到消息
        received_events = []
        
        def message_handler(data):
            print(f"📨 收到消息事件: {data}")
            received_events.append(('message', data))
        
        sio.on('message', message_handler)
        
        # 再次发送消息进行测试
        print("7. 发送第二条测试消息...")
        test_message2 = {
            'room': str(room_id),
            'message': {
                'content': f'第二条WebSocket测试消息 - {int(time.time())}',
                'gender': 'unknown',
                'client_id': f'test2-{int(time.time())}'
            }
        }
        
        sio.emit('send_message', test_message2)
        time.sleep(3)
        
        # 8. 通过HTTP API获取消息历史
        print("8. 通过HTTP API获取消息历史...")
        messages_response = requests.get(
            f"http://localhost:8080/api/rooms/{room_id}/messages",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if messages_response.status_code == 200:
            messages = messages_response.json()
            print(f"✅ 获取到 {len(messages)} 条历史消息")
            
            # 显示最后几条消息
            for msg in messages[-3:]:
                print(f"  📝 {msg['author']}: {msg['content']} ({msg['timestamp']})")
        else:
            print(f"❌ 获取消息历史失败: {messages_response.status_code}")
        
        # 断开连接
        sio.disconnect()
        print("✅ WebSocket连接已断开")
        
        # 分析结果
        print("\n📊 测试结果分析:")
        print(f"- 收到的WebSocket事件数量: {len(received_events)}")
        if received_events:
            for event_type, data in received_events:
                print(f"  - {event_type}: {data}")
        else:
            print("  ⚠️  没有收到任何WebSocket事件，这可能是问题所在")
        
    except Exception as e:
        print(f"❌ WebSocket测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_http_message_sending():
    """测试HTTP API发送消息"""
    
    print("\n🔍 测试HTTP API消息发送...")
    
    # 登录
    login_url = "http://localhost:8080/api/login"
    login_data = {"username": "admin", "password": "admin123"}
    
    try:
        response = requests.post(login_url, json=login_data)
        token = response.json().get('token')
        
        # 获取房间
        rooms_response = requests.get(
            "http://localhost:8080/api/rooms",
            headers={"Authorization": f"Bearer {token}"}
        )
        room_id = rooms_response.json()[0]['id']
        
        # 通过HTTP API发送消息
        message_data = {
            'content': f'HTTP API测试消息 - {int(time.time())}',
            'gender': 'unknown'
        }
        
        print(f"通过HTTP API发送消息到房间 {room_id}...")
        send_response = requests.post(
            f"http://localhost:8080/api/rooms/{room_id}/messages",
            json=message_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if send_response.status_code == 201:
            print("✅ HTTP API消息发送成功")
            print(f"响应: {send_response.json()}")
        else:
            print(f"❌ HTTP API消息发送失败: {send_response.status_code} - {send_response.text}")
            
    except Exception as e:
        print(f"❌ HTTP API测试失败: {e}")

if __name__ == "__main__":
    print("🚀 WebSocket消息流程诊断工具")
    print("=" * 50)
    
    # 检查服务器是否运行
    try:
        health_check = requests.get("http://localhost:8080/", timeout=5)
        print("✅ 服务器运行正常")
    except:
        print("❌ 服务器未运行或无法连接，请先启动 python web_app/start_web.py")
        sys.exit(1)
    
    # 运行测试
    test_websocket_flow()
    test_http_message_sending()
    
    print("\n📋 诊断完成！")
    print("如果WebSocket事件没有正确接收，可能的原因:")
    print("1. 前端WebSocket连接问题")
    print("2. 服务端事件发送时机问题")
    print("3. 房间加入/离开逻辑问题")
    print("4. CORS或认证问题")
