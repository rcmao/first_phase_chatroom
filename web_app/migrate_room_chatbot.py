#!/usr/bin/env python3
"""
数据库迁移脚本：为Room表添加chatbot_enabled字段
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Room
import sqlite3

def migrate_database():
    """添加chatbot_enabled字段到Room表"""
    with app.app_context():
        try:
            # 检查字段是否已存在
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('room')]
            
            if 'chatbot_enabled' in columns:
                print("✅ chatbot_enabled字段已存在，无需迁移")
                return
            
            print("🔄 开始数据库迁移：添加chatbot_enabled字段...")
            
            # 使用SQLite的ALTER TABLE添加字段
            db.engine.execute('ALTER TABLE room ADD COLUMN chatbot_enabled BOOLEAN DEFAULT 0')
            
            print("✅ 数据库迁移完成！chatbot_enabled字段已添加")
            
            # 查询现有房间数量
            room_count = Room.query.count()
            print(f"📊 当前共有{room_count}个房间，默认Chatbot状态为关闭")
            
        except Exception as e:
            print(f"❌ 数据库迁移失败: {e}")
            raise

if __name__ == '__main__':
    migrate_database()
