#!/usr/bin/env python3
"""
简单消息发送测试
创建测试用户并测试消息发送流程
"""

import sys
import os
sys.path.append('/Users/apple/Desktop/first_phase_chatroom/web_app')

from app import app, db, User, Room, Message
from werkzeug.security import generate_password_hash
import requests
import time

def create_test_user():
    """创建测试用户"""
    with app.app_context():
        # 检查是否已存在测试用户
        test_user = User.query.filter_by(username='testuser').first()
        if test_user:
            print("✅ 测试用户已存在")
            return
        
        # 创建测试用户
        test_user = User(
            username='testuser',
            email='test@example.com',
            password_hash=generate_password_hash('test123'),
            role='member',
            gender='unknown'
        )
        db.session.add(test_user)
        
        # 检查是否有房间，如果没有则创建一个
        room = Room.query.first()
        if not room:
            room = Room(
                name='测试房间',
                description='用于测试的房间',
                max_members=10,
                is_private=False,
                created_by=1
            )
            db.session.add(room)
        
        db.session.commit()
        print("✅ 测试用户创建成功: testuser/test123")

def test_message_flow():
    """测试消息发送流程"""
    
    # 1. 登录
    print("1. 登录测试用户...")
    login_response = requests.post('http://localhost:8080/api/login', json={
        'username': 'admin',
        'password': 'admin123'
    })
    
    if login_response.status_code != 200:
        print(f"❌ 登录失败: {login_response.status_code} - {login_response.text}")
        return
    
    token = login_response.json().get('token')
    print(f"✅ 登录成功")
    
    # 2. 获取房间列表
    print("2. 获取房间列表...")
    rooms_response = requests.get(
        'http://localhost:8080/api/rooms',
        headers={'Authorization': f'Bearer {token}'}
    )
    
    if rooms_response.status_code != 200:
        print(f"❌ 获取房间失败: {rooms_response.status_code}")
        return
    
    rooms = rooms_response.json()
    if not rooms:
        print("❌ 没有找到房间")
        return
    
    room_id = rooms[0]['id']
    print(f"✅ 找到房间: {rooms[0]['name']} (ID: {room_id})")
    
    # 3. 加入房间
    print("3. 加入房间...")
    join_response = requests.post(
        f'http://localhost:8080/api/rooms/{room_id}/join',
        headers={'Authorization': f'Bearer {token}'}
    )
    
    if join_response.status_code not in [200, 201]:
        print(f"加入房间状态: {join_response.status_code} - {join_response.text}")
    else:
        print("✅ 成功加入房间")
    
    # 4. 发送消息
    print("4. 发送测试消息...")
    message_data = {
        'content': f'测试消息 - {int(time.time())}',
        'gender': 'unknown'
    }
    
    send_response = requests.post(
        f'http://localhost:8080/api/rooms/{room_id}/messages',
        json=message_data,
        headers={'Authorization': f'Bearer {token}'}
    )
    
    if send_response.status_code == 201:
        print("✅ 消息发送成功")
        sent_message = send_response.json()
        print(f"发送的消息: {sent_message}")
    else:
        print(f"❌ 消息发送失败: {send_response.status_code} - {send_response.text}")
        return
    
    # 5. 获取消息历史
    print("5. 获取消息历史...")
    time.sleep(1)  # 等待一秒确保消息已保存
    
    messages_response = requests.get(
        f'http://localhost:8080/api/rooms/{room_id}/messages',
        headers={'Authorization': f'Bearer {token}'}
    )
    
    if messages_response.status_code == 200:
        messages = messages_response.json()
        print(f"✅ 获取到 {len(messages)} 条消息")
        
        # 检查刚才发送的消息是否在历史中
        latest_message = messages[-1] if messages else None
        if latest_message and latest_message['content'] == message_data['content']:
            print("✅ 刚发送的消息已在历史记录中")
        else:
            print("⚠️  刚发送的消息不在历史记录中")
            if latest_message:
                print(f"最新消息: {latest_message['content']}")
    else:
        print(f"❌ 获取消息历史失败: {messages_response.status_code}")

def check_database_directly():
    """直接检查数据库中的消息"""
    print("\n6. 直接检查数据库...")
    with app.app_context():
        messages = Message.query.order_by(Message.timestamp.desc()).limit(5).all()
        print(f"数据库中最新的 {len(messages)} 条消息:")
        for msg in messages:
            print(f"  - {msg.author}: {msg.content} ({msg.timestamp})")

if __name__ == "__main__":
    print("🔍 简单消息发送测试")
    print("=" * 40)
    
    # 检查服务器状态
    try:
        requests.get("http://localhost:8080/", timeout=5)
        print("✅ 服务器运行正常")
    except:
        print("❌ 服务器未运行")
        sys.exit(1)
    
    # 创建测试用户
    create_test_user()
    
    # 测试消息流程
    test_message_flow()
    
    # 检查数据库
    check_database_directly()
    
    print("\n📋 测试完成！")
