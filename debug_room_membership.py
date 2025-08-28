#!/usr/bin/env python3
"""
调试房间成员关系
"""

import sys
import os
sys.path.append('/Users/apple/Desktop/first_phase_chatroom/web_app')

from app import app, db, User, Room, RoomMembership

def debug_room_membership():
    """调试房间成员关系"""
    with app.app_context():
        print("🔍 房间成员关系调试")
        print("=" * 40)
        
        # 获取所有房间
        rooms = Room.query.all()
        print(f"总房间数: {len(rooms)}")
        
        for room in rooms:
            print(f"\n📂 房间: {room.name} (ID: {room.id})")
            
            # 获取房间成员
            memberships = RoomMembership.query.filter_by(room_id=room.id).all()
            print(f"   成员数: {len(memberships)}")
            
            for membership in memberships:
                user = User.query.get(membership.user_id)
                if user:
                    print(f"   - {user.username} ({membership.role}) - 在线: {membership.is_online}")
                else:
                    print(f"   - 用户ID {membership.user_id} (用户不存在)")
        
        print("\n👥 所有用户:")
        users = User.query.all()
        for user in users:
            print(f"   - {user.username} (ID: {user.id}, 角色: {user.role})")
        
        # 检查特定用户是否是房间成员
        print("\n🔎 检查用户房间成员关系:")
        for user in users[:5]:  # 只检查前5个用户
            for room in rooms[:2]:  # 只检查前2个房间
                membership = RoomMembership.query.filter_by(
                    user_id=user.id, room_id=room.id
                ).first()
                status = "✅ 是成员" if membership else "❌ 不是成员"
                print(f"   {user.username} -> {room.name}: {status}")

def auto_add_users_to_room():
    """自动将所有用户加入第一个房间"""
    with app.app_context():
        print("\n🚀 自动加入房间操作")
        print("=" * 40)
        
        # 获取第一个房间
        room = Room.query.first()
        if not room:
            print("❌ 没有找到房间")
            return
        
        print(f"目标房间: {room.name} (ID: {room.id})")
        
        # 获取所有用户
        users = User.query.all()
        added_count = 0
        
        for user in users:
            # 检查是否已经是成员
            existing = RoomMembership.query.filter_by(
                user_id=user.id, room_id=room.id
            ).first()
            
            if not existing:
                # 添加成员关系
                membership = RoomMembership(
                    user_id=user.id,
                    room_id=room.id,
                    role='admin' if user.role == 'admin' else 'member',
                    is_online=False  # 默认离线状态
                )
                db.session.add(membership)
                added_count += 1
                print(f"✅ 添加用户 {user.username} 到房间")
            else:
                print(f"⏭️  用户 {user.username} 已经是房间成员")
        
        if added_count > 0:
            db.session.commit()
            print(f"\n🎉 成功添加 {added_count} 个用户到房间")
        else:
            print("\n📝 所有用户都已经是房间成员")

if __name__ == "__main__":
    debug_room_membership()
    auto_add_users_to_room()
    print("\n重新检查成员关系:")
    debug_room_membership()
