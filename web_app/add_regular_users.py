#!/usr/bin/env python3
"""
添加新的普通用户账号脚本
"""

import os
import sys
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, User
from werkzeug.security import generate_password_hash
from sqlalchemy import text

def add_regular_users():
    """添加新的普通用户"""
    with app.app_context():
        try:
            # 创建第一个普通用户
            user1_username = 'user1'
            user1_user = User.query.filter_by(username=user1_username).first()
            if not user1_user:
                user1_user = User(
                    username=user1_username,
                    email='user1@example.com',
                    password_hash=generate_password_hash('user123'),
                    role='member',
                    gender='male',
                    display_name='张三',
                    bio='普通用户1',
                    status='online'
                )
                db.session.add(user1_user)
                print(f"✅ 创建普通用户1: {user1_username}/user123")
            else:
                print(f"⚠️  用户 {user1_username} 已存在，跳过创建")

            # 创建第二个普通用户
            user2_username = 'user2'
            user2_user = User.query.filter_by(username=user2_username).first()
            if not user2_user:
                user2_user = User(
                    username=user2_username,
                    email='user2@example.com',
                    password_hash=generate_password_hash('user123'),
                    role='member',
                    gender='female',
                    display_name='李四',
                    bio='普通用户2',
                    status='online'
                )
                db.session.add(user2_user)
                print(f"✅ 创建普通用户2: {user2_username}/user123")
            else:
                print(f"⚠️  用户 {user2_username} 已存在，跳过创建")

            # 创建第三个普通用户
            user3_username = 'user3'
            user3_user = User.query.filter_by(username=user3_username).first()
            if not user3_user:
                user3_user = User(
                    username=user3_username,
                    email='user3@example.com',
                    password_hash=generate_password_hash('user123'),
                    role='member',
                    gender='unknown',
                    display_name='王五',
                    bio='普通用户3',
                    status='online'
                )
                db.session.add(user3_user)
                print(f"✅ 创建普通用户3: {user3_username}/user123")
            else:
                print(f"⚠️  用户 {user3_username} 已存在，跳过创建")

            # 提交更改
            db.session.commit()
            print("✅ 新普通用户添加完成")
            
            # 显示所有普通用户
            member_users = User.query.filter_by(role='member').all()
            print(f"\n📋 当前所有普通用户 ({len(member_users)} 个):")
            for i, user in enumerate(member_users, 1):
                print(f"   {i}. {user.username} ({user.email}) - {user.display_name}")
                
        except Exception as e:
            print(f"❌ 添加普通用户失败: {e}")
            db.session.rollback()

def main():
    """主函数"""
    print("🔧 添加新的普通用户账号")
    print("=" * 40)
    
    # 检查数据库连接 - SQLAlchemy 2.0语法
    with app.app_context():
        try:
            with db.engine.connect() as conn:
                conn.execute(text('SELECT 1'))
            print("✅ 数据库连接正常")
        except Exception as e:
            print(f"❌ 数据库连接失败: {e}")
            return
    
    # 添加普通用户
    add_regular_users()
    
    print("\n📝 新普通用户信息:")
    print("   - 用户名: user1, 密码: user123, 显示名: 张三")
    print("   - 用户名: user2, 密码: user123, 显示名: 李四")
    print("   - 用户名: user3, 密码: user123, 显示名: 王五")
    print("\n🔗 登录地址: http://localhost:8080")
    print("=" * 40)

if __name__ == '__main__':
    main()
