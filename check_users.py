#!/usr/bin/env python3
"""
检查数据库中的用户
"""

import sys
import os
sys.path.append('/Users/apple/Desktop/first_phase_chatroom/web_app')

from app import app, db, User

def check_users():
    """检查数据库中的用户"""
    with app.app_context():
        users = User.query.all()
        print(f"数据库中共有 {len(users)} 个用户:")
        for user in users:
            print(f"  - {user.username} ({user.email}) - 角色: {user.role}")

if __name__ == "__main__":
    check_users()
