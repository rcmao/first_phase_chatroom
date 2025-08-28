#!/usr/bin/env python3
"""
直接WebSocket测试
不依赖HTTP登录，直接测试WebSocket消息传递
"""

import socketio
import time
import threading

def test_websocket_direct():
    """直接测试WebSocket消息传递"""
    print("🔧 直接WebSocket测试")
    print("=" * 40)
    
    # 创建两个WebSocket客户端
    client1 = socketio.SimpleClient()
    client2 = socketio.SimpleClient()
    
    client1_messages = []
    client2_messages = []
    
    def client1_message_handler(data):
        client1_messages.append(data)
        print(f"📨 客户端1收到: {data.get('author', '?')}: {data.get('content', '')}")
    
    def client2_message_handler(data):
        client2_messages.append(data)
        print(f"📨 客户端2收到: {data.get('author', '?')}: {data.get('content', '')}")
    
    try:
        # 连接到WebSocket服务器（不带认证）
        print("1. 连接WebSocket服务器...")
        client1.connect('http://localhost:8080')
        client2.connect('http://localhost:8080')
        print("✅ 两个客户端都连接成功")
        
        # SimpleClient 的事件监听使用不同方式，我们手动检查事件
        
        # 加入房间1
        print("2. 加入房间...")
        client1.emit('join_room', {'room': '1'})
        client2.emit('join_room', {'room': '1'})
        time.sleep(2)
        print("✅ 两个客户端都加入房间1")
        
        # 发送测试消息
        print("3. 发送测试消息...")
        
        test_messages = [
            {
                'room': '1',
                'message': {
                    'content': '这是客户端1的测试消息',
                    'gender': 'unknown',
                    'client_id': f'client1-{int(time.time())}'
                }
            },
            {
                'room': '1', 
                'message': {
                    'content': '这是客户端2的测试消息',
                    'gender': 'unknown',
                    'client_id': f'client2-{int(time.time())}'
                }
            }
        ]
        
        # 客户端1发送消息
        print("📤 客户端1发送消息...")
        result1 = client1.emit('send_message', test_messages[0])
        print(f"发送结果1: {result1}")
        time.sleep(3)
        
        # 尝试接收消息
        try:
            event1 = client1.receive(timeout=2)
            if event1:
                print(f"客户端1收到事件: {event1}")
                client1_messages.append(event1[1] if len(event1) > 1 else event1)
        except:
            print("客户端1没有收到任何事件")
        
        # 客户端2发送消息
        print("📤 客户端2发送消息...")
        result2 = client2.emit('send_message', test_messages[1])
        print(f"发送结果2: {result2}")
        time.sleep(3)
        
        # 尝试接收消息
        try:
            event2 = client2.receive(timeout=2)
            if event2:
                print(f"客户端2收到事件: {event2}")
                client2_messages.append(event2[1] if len(event2) > 1 else event2)
        except:
            print("客户端2没有收到任何事件")
        
        # 发送一些测试事件
        print("4. 发送测试事件...")
        client1.emit('test', {'message': '客户端1测试事件'})
        client2.emit('test', {'message': '客户端2测试事件'})
        
        # 尝试接收测试事件响应
        try:
            test_event1 = client1.receive(timeout=2)
            test_event2 = client2.receive(timeout=2)
            print(f"测试事件响应1: {test_event1}")
            print(f"测试事件响应2: {test_event2}")
        except:
            print("没有收到测试事件响应")
        
        # 统计结果
        print("\n📊 测试结果:")
        print(f"客户端1收到事件数: {len(client1_messages)}")
        print(f"客户端2收到事件数: {len(client2_messages)}")
        
        # 分析问题
        print("\n🔍 问题分析:")
        print("如果没有收到消息，可能是以下原因:")
        print("1. WebSocket身份验证要求token参数")
        print("2. send_message事件处理函数要求用户登录")
        print("3. 房间成员检查阻止了消息发送")
        print("4. 消息处理流程中有错误")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 断开连接
        try:
            client1.disconnect()
            client2.disconnect()
            print("🔌 客户端已断开连接")
        except:
            pass

if __name__ == "__main__":
    # 检查服务器状态
    import requests
    try:
        requests.get("http://localhost:8080/", timeout=5)
        print("✅ 服务器运行正常")
    except:
        print("❌ 服务器未运行")
        exit(1)
    
    test_websocket_direct()
