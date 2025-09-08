#!/usr/bin/env python3
"""
添加新的管理员用户脚本
"""

import os
import sys
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, User
from werkzeug.security import generate_password_hash
from sqlalchemy import text

def add_admin_users():
    """添加新的管理员用户"""
    with app.app_context():
        try:
            # 创建第一个新管理员用户
            admin1_username = 'admin2'
            admin1_user = User.query.filter_by(username=admin1_username).first()
            if not admin1_user:
                admin1_user = User(
                    username=admin1_username,
                    email='admin2@tki.com',
                    password_hash=generate_password_hash('admin123'),
                    role='admin',
                    gender='unknown',
                    display_name='管理员2',
                    bio='系统管理员2',
                    status='online'
                )
                db.session.add(admin1_user)
                print(f"✅ 创建新管理员用户1: {admin1_username}/admin123")
            else:
                print(f"⚠️  用户 {admin1_username} 已存在，跳过创建")

            # 创建第二个新管理员用户
            admin2_username = 'admin3'
            admin2_user = User.query.filter_by(username=admin2_username).first()
            if not admin2_user:
                admin2_user = User(
                    username=admin2_username,
                    email='admin3@tki.com',
                    password_hash=generate_password_hash('admin123'),
                    role='admin',
                    gender='unknown',
                    display_name='管理员3',
                    bio='系统管理员3',
                    status='online'
                )
                db.session.add(admin2_user)
                print(f"✅ 创建新管理员用户2: {admin2_username}/admin123")
            else:
                print(f"⚠️  用户 {admin2_username} 已存在，跳过创建")

            # 提交更改
            db.session.commit()
            print("✅ 新管理员用户添加完成")
            
            # 显示所有管理员用户
            admin_users = User.query.filter_by(role='admin').all()
            print(f"\n📋 当前所有管理员用户 ({len(admin_users)} 个):")
            for i, user in enumerate(admin_users, 1):
                print(f"   {i}. {user.username} ({user.email}) - {user.display_name}")
                
        except Exception as e:
            print(f"❌ 添加管理员用户失败: {e}")
            db.session.rollback()

def main():
    """主函数"""
    print("🔧 添加新的管理员用户")
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
    
    # 添加管理员用户
    add_admin_users()
    
    print("\n📝 新管理员用户信息:")
    print("   - 用户名: admin2, 密码: admin123")
    print("   - 用户名: admin3, 密码: admin123")
    print("\n🔗 登录地址: http://localhost:8080")
    print("=" * 40)

if __name__ == '__main__':
    main()
