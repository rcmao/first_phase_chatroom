#!/usr/bin/env python3
"""
TKI智能干预聊天机器人 Web应用启动脚本
"""

import os
import sys
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, User, Room, RoomMembership
from werkzeug.security import generate_password_hash

def create_default_data():
    """创建默认数据"""
    with app.app_context():
        # 创建默认管理员用户
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@tki.com',
                password_hash=generate_password_hash('admin123'),
                role='admin',
                gender='unknown'
            )
            db.session.add(admin_user)
            print("✅ 创建默认管理员用户: admin/admin123")

        # 创建默认测试用户
        test_user = User.query.filter_by(username='tester').first()
        if not test_user:
            test_user = User(
                username='tester',
                email='tester@tki.com',
                password_hash=generate_password_hash('test123'),
                role='member',
                gender='unknown'
            )
            db.session.add(test_user)
            print("✅ 创建默认测试用户: tester/test123")

        # 创建test1_m用户
        test1_user = User.query.filter_by(username='test1_m').first()
        if not test1_user:
            test1_user = User(
                username='test1m',
                email='test1_m@tki.com',
                password_hash=generate_password_hash('test123'),
                role='member',
                gender='male'
            )
            db.session.add(test1_user)
            print("✅ 创建测试用户1: test1_m/test123 (男)")

        # 创建test2_m用户
        test2_user = User.query.filter_by(username='test2_m').first()
        if not test2_user:
            test2_user = User(
                username='test2_m',
                email='test2_m@tki.com',
                password_hash=generate_password_hash('test123'),
                role='member',
                gender='male'
            )
            db.session.add(test2_user)
            print("✅ 创建测试用户2: test2_m/test123 (男)")

        # 只在数据库完全为空时创建默认房间
        room_count = Room.query.count()
        if room_count == 0:
            # 创建默认房间
            default_room = Room(
                name='通用聊天',
                description='TKI智能干预聊天机器人的默认测试房间',
                max_members=20,
                is_private=False,
                created_by=1
            )
            db.session.add(default_room)
            print("✅ 创建默认房间: 通用聊天")

            # 创建测试房间1
            test_room1 = Room(
                name='测试房间1',
                description='用于测试TKI干预策略的房间',
                max_members=10,
                is_private=False,
                created_by=1
            )
            db.session.add(test_room1)
            print("✅ 创建测试房间1")

            # 创建测试房间2
            test_room2 = Room(
                name='测试房间2',
                description='用于对比测试的房间',
                max_members=10,
                is_private=False,
                created_by=1
            )
            db.session.add(test_room2)
            print("✅ 创建测试房间2")
        else:
            print(f"📊 数据库中已有 {room_count} 个房间，跳过默认房间创建")

        try:
            db.session.commit()
            print("✅ 默认数据创建完成")
        except Exception as e:
            print(f"❌ 创建默认数据失败: {e}")
            db.session.rollback()

def main():
    if not os.environ.get('SECRET_KEY'):
        os.environ['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
    
    with app.app_context():
        db.create_all()
    
    create_default_data()
    
    try:
        from app import socketio, realtime_monitor
        
        # 启动实时监控系统
        realtime_monitor.start_monitoring()
        print("🚀 实时监控系统已启动")
        
        socketio.run(app, debug=True, host='0.0.0.0', port=8080)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        pass

if __name__ == '__main__':
    main() 