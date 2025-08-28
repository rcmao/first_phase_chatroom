#!/usr/bin/env python3
"""
聊天模拟测试
模拟真实用户聊天，检查实时消息同步
"""

import socketio
import time
import threading
import requests
import json

class ChatUser:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.token = None
        self.socket = None
        self.messages_received = []
        
    def login(self):
        """登录获取token"""
        try:
            response = requests.post('http://localhost:8080/api/login', json={
                'username': self.username,
                'password': self.password
            })
            if response.status_code == 200:
                self.token = response.json().get('token')
                print(f"✅ {self.username} 登录成功")
                return True
            else:
                print(f"❌ {self.username} 登录失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ {self.username} 登录出错: {e}")
            return False
    
    def connect_websocket(self):
        """连接WebSocket"""
        if not self.token:
            print(f"❌ {self.username} 没有token，无法连接WebSocket")
            return False
            
        try:
            self.socket = socketio.SimpleClient()
            self.socket.connect('http://localhost:8080', query={'token': self.token})
            
            # 设置消息监听器
            def on_message(data):
                self.messages_received.append(data)
                print(f"📨 {self.username} 收到消息: {data.get('author', '?')}: {data.get('content', '')}")
            
            self.socket.on('message', on_message)
            
            # 加入房间1
            self.socket.emit('join_room', {'room': '1'})
            print(f"🔗 {self.username} WebSocket连接成功并加入房间1")
            return True
            
        except Exception as e:
            print(f"❌ {self.username} WebSocket连接失败: {e}")
            return False
    
    def send_message(self, content):
        """发送消息"""
        if not self.socket:
            print(f"❌ {self.username} WebSocket未连接")
            return False
            
        try:
            message_data = {
                'room': '1',
                'message': {
                    'content': content,
                    'gender': 'unknown',
                    'client_id': f'{self.username}-{int(time.time())}'
                }
            }
            self.socket.emit('send_message', message_data)
            print(f"📤 {self.username} 发送消息: {content}")
            return True
        except Exception as e:
            print(f"❌ {self.username} 发送消息失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.socket:
            self.socket.disconnect()
            print(f"🔌 {self.username} 已断开连接")

def test_real_time_chat():
    """测试实时聊天"""
    print("🚀 开始实时聊天测试")
    print("=" * 50)
    
    # 创建两个用户
    users = [
        ChatUser('admin', 'admin123'),
        ChatUser('tester', 'test123')
    ]
    
    # 登录用户
    for user in users:
        if not user.login():
            print(f"❌ {user.username} 登录失败，跳过测试")
            return
    
    # 连接WebSocket
    for user in users:
        if not user.connect_websocket():
            print(f"❌ {user.username} WebSocket连接失败，跳过测试")
            return
    
    # 等待连接稳定
    time.sleep(2)
    
    # 模拟对话
    conversation = [
        ('admin', '大家好，我是管理员'),
        ('tester', '你好管理员！'),
        ('admin', '今天天气不错'),
        ('tester', '是的，很晴朗'),
        ('admin', '这个聊天室的实时功能怎么样？'),
        ('tester', '看起来工作得很好！')
    ]
    
    print("\n💬 开始模拟对话...")
    print("-" * 30)
    
    for sender_name, message in conversation:
        # 找到发送者
        sender = next((u for u in users if u.username == sender_name), None)
        if sender:
            sender.send_message(message)
            time.sleep(3)  # 等待消息传播
        else:
            print(f"❌ 找不到用户: {sender_name}")
    
    # 等待所有消息处理完成
    print("\n⏳ 等待消息处理完成...")
    time.sleep(5)
    
    # 统计结果
    print("\n📊 测试结果:")
    print("-" * 30)
    
    total_sent = len(conversation)
    for user in users:
        received_count = len(user.messages_received)
        print(f"{user.username}: 收到 {received_count}/{total_sent} 条消息")
        
        if received_count > 0:
            print(f"  最新消息: {user.messages_received[-1].get('content', '')}")
        
        # 检查是否收到了自己发送的消息
        own_messages = [msg for msg in user.messages_received if msg.get('author') == user.username]
        others_messages = [msg for msg in user.messages_received if msg.get('author') != user.username]
        
        print(f"  自己的消息: {len(own_messages)}, 他人的消息: {len(others_messages)}")
    
    # 断开连接
    for user in users:
        user.disconnect()
    
    # 判断测试是否成功
    all_received_all = all(len(user.messages_received) >= total_sent for user in users)
    
    if all_received_all:
        print("\n🎉 实时消息同步测试成功！")
        print("✅ 所有用户都收到了所有消息")
    else:
        print("\n⚠️  实时消息同步存在问题")
        print("❌ 部分用户没有收到所有消息")
        print("💡 建议检查WebSocket连接和房间加入逻辑")

if __name__ == "__main__":
    # 检查服务器状态
    try:
        requests.get("http://localhost:8080/", timeout=5)
        print("✅ 服务器运行正常")
    except:
        print("❌ 服务器未运行")
        exit(1)
    
    test_real_time_chat()
