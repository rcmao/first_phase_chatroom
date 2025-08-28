#!/usr/bin/env python3
"""
实时WebSocket监听器
用于监听房间中的实时消息
"""

import socketio
import time
import requests

def test_websocket_listening():
    """测试WebSocket实时监听"""
    
    print("🎧 启动WebSocket实时监听器...")
    
    # 创建SocketIO客户端
    sio = socketio.SimpleClient()
    
    # 消息计数器
    message_count = 0
    
    def on_message(data):
        nonlocal message_count
        message_count += 1
        print(f"📨 [消息 #{message_count}] {data.get('author', '未知')}: {data.get('content', '')}")
        print(f"    时间: {data.get('timestamp', '')}")
        print(f"    房间: {data.get('room', '')}")
        print(f"    Client ID: {data.get('client_id', '')}")
        print()
    
    def on_connect():
        print("🔗 WebSocket连接成功")
        # 尝试加入房间1 (假设这是测试房间)
        sio.emit('join_room', {'room': '1'})
        print("📍 已请求加入房间1")
    
    def on_disconnect():
        print("❌ WebSocket连接断开")
    
    def on_user_joined(data):
        print(f"👋 用户加入: {data}")
    
    def on_user_left(data):
        print(f"👋 用户离开: {data}")
    
    def on_intervention(data):
        print(f"🤖 干预消息: {data}")
    
    def on_test(data):
        print(f"🧪 测试事件: {data}")
    
    # 注册事件处理器
    sio.on('connect', on_connect)
    sio.on('disconnect', on_disconnect)
    sio.on('message', on_message)
    sio.on('user_joined', on_user_joined)
    sio.on('user_left', on_user_left)
    sio.on('intervention', on_intervention)
    sio.on('test', on_test)
    
    try:
        # 连接到WebSocket服务器
        print("🔌 正在连接到 http://localhost:8080...")
        sio.connect('http://localhost:8080')
        
        print("✅ 连接成功，开始监听消息...")
        print("💡 现在请到聊天室发送消息，或者按 Ctrl+C 退出")
        print("=" * 50)
        
        # 保持连接并监听
        start_time = time.time()
        while True:
            time.sleep(1)
            
            # 每30秒显示一次统计
            if int(time.time() - start_time) % 30 == 0:
                elapsed = int(time.time() - start_time)
                print(f"📊 运行时间: {elapsed}秒，收到消息: {message_count}条")
    
    except KeyboardInterrupt:
        print("\n🛑 用户中断，正在断开连接...")
        sio.disconnect()
    
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        
    finally:
        if sio.connected:
            sio.disconnect()
        print(f"📋 监听结束，共收到 {message_count} 条消息")

def check_server_status():
    """检查服务器状态"""
    try:
        response = requests.get("http://localhost:8080/", timeout=5)
        print("✅ 服务器运行正常")
        return True
    except:
        print("❌ 服务器未运行，请先启动: python web_app/start_web.py")
        return False

if __name__ == "__main__":
    print("🎯 WebSocket实时消息监听器")
    print("=" * 40)
    
    if not check_server_status():
        exit(1)
    
    test_websocket_listening()
