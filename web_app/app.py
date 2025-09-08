import os
import sys
import json
import random
import aiohttp
import time
from datetime import datetime, timedelta
from collections import deque

# 加载环境变量
try:
    from dotenv import load_dotenv
    # 查找.env文件
    env_files = ['.env', 'env.example']
    for env_file in env_files:
        env_path = os.path.join(os.path.dirname(__file__), env_file)
        if os.path.exists(env_path):
            load_dotenv(env_path)
            print(f"✅ 加载环境变量文件: {env_file}")
            break
    else:
        print("⚠️ 未找到.env文件，使用系统环境变量")
except ImportError:
    print("⚠️ python-dotenv未安装，使用系统环境变量")

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from functools import wraps
import logging
from flask_cors import CORS
import pytz

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入项目模块
# 修复导入路径（始终生效）
import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

# 始终使用真实的干预引擎（不可降级为占位）
from smart_intervention_engine import SmartInterventionEngine, InterventionType, OffenseLevel

# 可选模块导入失败时使用占位实现，避免影响核心运行
try:
    from src.detectors.gpt4_realtime_context_analyzer import GPT4RealtimeContextAnalyzer
    from core.tki_gender_aware_bot import TKIGenderAwareBot
    from translations import get_text, get_language_list
except ImportError as e:
    logger.error(f"导入项目模块失败: {e}")
    # 创建空的占位符类
    class GPT4RealtimeContextAnalyzer:
        def __init__(self):
            self.conversation_contexts = {}
            self.intervention_history = deque(maxlen=50)
            self.total_analyses = 0
            self.recent_interventions = 0
            self.trigger_counts = {}
        
        def get_analysis_statistics(self):
            return {
                'total_analyses': self.total_analyses,
                'recent_interventions': len(self.intervention_history),
                'active_contexts': len(self.conversation_contexts),
                'trigger_counts': self.trigger_counts
            }
        
        def add_intervention(self, room_id, trigger_type, confidence=0.8):
            """添加干预记录"""
            intervention = {
                'room_id': room_id,
                'trigger_type': trigger_type,
                'confidence': confidence,
                'timestamp': datetime.now()
            }
            self.intervention_history.append(intervention)
            self.recent_interventions += 1
            
            # 更新触发类型统计
            if trigger_type not in self.trigger_counts:
                self.trigger_counts[trigger_type] = 0
            self.trigger_counts[trigger_type] += 1
        
        def add_analysis(self):
            """增加分析次数"""
            self.total_analyses += 1
    
    class TKIGenderAwareBot:
        pass
    
    # 添加get_text和get_language_list的占位符函数
    def get_text(lang='zh'):
        """占位符翻译函数"""
        return {
            'page_title': '聊天房间',
            'welcome': '欢迎',
            'send': '发送'
        }
    
    def get_language_list():
        """占位符语言列表函数"""
        return ['zh', 'en']
    
    # 注意：不要在这里定义 SmartInterventionEngine 的占位实现，避免覆盖真实引擎

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chatbot.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['INTERVENTION_ENABLED'] = True  # ← 默认开启

# 手动房间管理系统 - 用于解决Flask-SocketIO房间加入问题
manual_room_mapping = {}  # {client_id: room_id}
room_clients = {}  # {room_id: [client_id1, client_id2, ...]}

def add_client_to_room(client_id, room_id):
    """手动将客户端添加到房间"""
    room_id = str(room_id)
    
    # 从旧房间移除
    if client_id in manual_room_mapping:
        old_room = manual_room_mapping[client_id]
        if old_room in room_clients and client_id in room_clients[old_room]:
            room_clients[old_room].remove(client_id)
            if not room_clients[old_room]:  # 如果房间空了，删除房间
                del room_clients[old_room]
    
    # 添加到新房间
    manual_room_mapping[client_id] = room_id
    if room_id not in room_clients:
        room_clients[room_id] = []
    if client_id not in room_clients[room_id]:
        room_clients[room_id].append(client_id)
    
    print(f"✅ 手动房间管理：客户端 {client_id} 已加入房间 {room_id}")
    print(f"   房间 {room_id} 现有客户端: {room_clients.get(room_id, [])}")

def remove_client_from_rooms(client_id):
    """手动从所有房间移除客户端"""
    if client_id in manual_room_mapping:
        room_id = manual_room_mapping[client_id]
        if room_id in room_clients and client_id in room_clients[room_id]:
            room_clients[room_id].remove(client_id)
            if not room_clients[room_id]:
                del room_clients[room_id]
        del manual_room_mapping[client_id]
        print(f"✅ 手动房间管理：客户端 {client_id} 已从房间 {room_id} 移除")

def get_room_clients(room_id):
    """获取房间中的所有客户端"""
    room_id = str(room_id)
    return room_clients.get(room_id, [])

def manual_emit_to_room(event, data, room_id):
    """手动发送消息到房间中的所有客户端"""
    room_id = str(room_id)
    clients = get_room_clients(room_id)
    if clients:
        print(f"📡 手动广播到房间 {room_id}，客户端数: {len(clients)}")
        for client_id in clients:
            try:
                socketio.emit(event, data, to=client_id)
                print(f"   ✅ 发送到客户端 {client_id}")
            except Exception as e:
                print(f"   ❌ 发送到客户端 {client_id} 失败: {e}")
    else:
        print(f"⚠️  房间 {room_id} 没有客户端")

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# 初始化SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

CORS(app)

# 设置时区
def get_local_time():
    tz = pytz.timezone('Asia/Shanghai')
    return datetime.now(tz)

# 数据库模型定义
class User(UserMixin, db.Model):
    """用户模型 - 简化权限系统"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='member')  # 'admin' 或 'member'
    is_active = db.Column(db.Boolean, default=True)
    gender = db.Column(db.String(10), default='unknown')  # 'male', 'female', 'unknown'
    avatar = db.Column(db.String(200), default='')
    display_name = db.Column(db.String(100), default='')  # 显示名称
    bio = db.Column(db.Text, default='')  # 个人简介
    status = db.Column(db.String(20), default='online')  # 'online', 'offline', 'busy'
    created_at = db.Column(db.DateTime, default=get_local_time)
    last_seen = db.Column(db.DateTime, default=get_local_time)
    
    # 关系
    conversations = db.relationship('Conversation', backref='user', lazy=True)
    messages = db.relationship('Message', backref='user', lazy=True)
    room_memberships = db.relationship('RoomMembership', backref='user', lazy=True)
    
    def is_admin(self):
        """检查是否为管理员"""
        return self.role == 'admin'
    
    def is_member(self):
        """检查是否为普通成员"""
        return self.role == 'member'
    
    def can_access_user_data(self, user_id):
        """检查是否可以访问指定用户的数据"""
        return self.is_admin() or self.id == user_id
    
    def can_manage_rooms(self):
        """检查是否可以管理群组"""
        return self.is_admin()
    
    def can_manage_members(self):
        """检查是否可以管理成员"""
        return self.is_admin()
    
    def can_view_statistics(self):
        """检查是否可以查看统计信息"""
        return self.is_admin()
    
    def can_export_data(self):
        """检查是否可以导出数据"""
        return self.is_admin()
    
    def can_manage_tests(self):
        """检查是否可以管理测试"""
        return self.is_admin()

class Room(db.Model):
    """房间模型"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    max_members = db.Column(db.Integer, default=10)
    is_private = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=get_local_time)
    updated_at = db.Column(db.DateTime, default=get_local_time, onupdate=get_local_time)
    chatbot_enabled = db.Column(db.Boolean, default=False)  # 按房间控制Chatbot
    
    # 关系
    members = db.relationship('RoomMembership', backref='room', lazy=True)
    messages = db.relationship('Message', backref='room', lazy=True)
    interventions = db.relationship('Intervention', backref='room', lazy=True)

class RoomMembership(db.Model):
    """房间成员关系 - 支持角色管理"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    role = db.Column(db.String(20), default='member')  # 'admin' 或 'member'
    joined_at = db.Column(db.DateTime, default=get_local_time)
    is_online = db.Column(db.Boolean, default=False)
    can_send_messages = db.Column(db.Boolean, default=True)
    can_edit_messages = db.Column(db.Boolean, default=True)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'room_id', name='unique_user_room'),)
    
    def is_room_admin(self):
        """检查是否为房间管理员"""
        return self.role == 'admin'
    
    def is_room_member(self):
        """检查是否为房间普通成员"""
        return self.role == 'member'

class Conversation(db.Model):
    """对话模型（保留原有）"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=get_local_time)
    updated_at = db.Column(db.DateTime, default=get_local_time, onupdate=get_local_time)
    messages = db.relationship('Message', backref='conversation', lazy=True)

class Message(db.Model):
    """消息模型"""
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(80), nullable=False)
    gender = db.Column(db.String(10), default='unknown')
    timestamp = db.Column(db.DateTime, default=get_local_time)
    
    # 关联字段
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'))
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'))
    
    has_interruption = db.Column(db.Boolean, default=False)
    interruption_type = db.Column(db.String(50))
    intervention_applied = db.Column(db.Boolean, default=False)

class Intervention(db.Model):
    """干预记录模型"""
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    message_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=False)
    strategy = db.Column(db.String(50), nullable=False)  # TKI策略类型
    intervention_text = db.Column(db.Text, nullable=False)
    trigger_type = db.Column(db.String(50))  # 触发类型
    trigger_reason = db.Column(db.Text)  # 触发原因（管理员可见）
    intervention_type = db.Column(db.String(50))
    offense_level = db.Column(db.String(20))  # 冒犯等级
    target_user = db.Column(db.String(100))  # 目标用户
    effectiveness = db.Column(db.Integer)  # 效果评分 1-5
    is_visible_to_admin_only = db.Column(db.Boolean, default=False)  # 是否仅管理员可见原因
    created_at = db.Column(db.DateTime, default=get_local_time)

class Statistics(db.Model):
    """统计数据模型"""
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    total_messages = db.Column(db.Integer, default=0)
    male_messages = db.Column(db.Integer, default=0)
    female_messages = db.Column(db.Integer, default=0)
    interruptions_detected = db.Column(db.Integer, default=0)
    interventions_applied = db.Column(db.Integer, default=0)
    strategy_counts = db.Column(db.Text)  # JSON格式存储策略统计
    created_at = db.Column(db.DateTime, default=get_local_time)

class InterventionStyle(db.Model):
    """干预风格设置模型"""
    id = db.Column(db.Integer, primary_key=True)
    style = db.Column(db.String(50), nullable=False, default='none')  # 当前风格
    description = db.Column(db.Text)  # 风格描述
    is_active = db.Column(db.Boolean, default=True)  # 是否激活
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))  # 创建者
    created_at = db.Column(db.DateTime, default=get_local_time)
    updated_at = db.Column(db.DateTime, default=get_local_time, onupdate=get_local_time)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 管理员权限装饰器
def jwt_required(f):
    """JWT认证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': '缺少认证token'}), 401
        
        token = auth_header.split(' ')[1]
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            user_id = payload['user_id']
            user = User.query.get(user_id)
            if not user:
                return jsonify({'error': '用户不存在'}), 401
            # 将用户设置为当前用户
            from flask_login import login_user
            login_user(user)
            # 将用户ID存储到session中，供WebSocket使用
            session['user_id'] = user.id
            return f(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token已过期'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': '无效的Token'}), 401
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            try:
                payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
                user_id = payload['user_id']
                user = User.query.get(user_id)
                if user and user.is_admin():
                    return f(*args, **kwargs)
                else:
                    return jsonify({'error': '需要管理员权限'}), 403
            except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
                return jsonify({'error': '无效的Token'}), 401
        elif current_user.is_authenticated and current_user.is_admin():
            return f(*args, **kwargs)
        else:
            return jsonify({'error': '需要管理员权限'}), 403
    return decorated_function

# 创建数据库表
with app.app_context():
    db.create_all()

# 机器人实例（Chime）
tki_bot = TKIGenderAwareBot()

# 初始化GPT-4实时上下文分析器
gpt4_context_analyzer = GPT4RealtimeContextAnalyzer()

# 初始化智能干预引擎 - 强制重新导入以获取最新版本
import importlib
import smart_intervention_engine as sie_module
importlib.reload(sie_module)
smart_intervention_engine = sie_module.SmartInterventionEngine()

# 初始化实时监控系统
from realtime_monitor import RealtimeMonitor
realtime_monitor = RealtimeMonitor(smart_intervention_engine, socketio, app)

# 路由定义
@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/test')
def test_register():
    """注册功能测试页面"""
    return render_template('test_register.html')

@app.route('/test-links')
def test_links():
    """链接功能测试页面"""
    return render_template('test_links.html')

@app.route('/register')
def register_page():
    """用户注册页面"""
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    """数据统计仪表板"""
    return render_template('dashboard.html')

@app.route('/rooms')
def rooms():
    """房间管理页面"""
    return render_template('rooms.html')

@app.route('/chat/<room_id>')
def chat_room(room_id):
    """聊天房间页面"""
    # 检查房间是否存在
    room = Room.query.get(room_id)
    if not room:
        return render_template('error.html', 
                             error_message='房间不存在或已被删除',
                             back_url='/rooms')
    
    return render_template('chat_room.html', room_id=room_id)

# API路由
@app.route('/api/language', methods=['GET'])
def get_languages():
    """获取支持的语言列表"""
    return jsonify(get_language_list())

@app.route('/api/translations/<lang>', methods=['GET'])
def get_translations(lang):
    """获取指定语言的翻译"""
    return jsonify(get_text(lang))

@app.route('/api/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({'error': '缺少必要字段'}), 400
    
    # 检查用户是否已存在
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': '用户名已存在'}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': '邮箱已存在'}), 400
    
    # 处理邀请码
    invite_code = data.get('invite_code', '')
    role = 'user'  # 默认为普通用户
    
    if invite_code == 'ADMIN2024':
        role = 'admin'
    elif invite_code and invite_code != 'PUBLIC':
        return jsonify({'error': '邀请码无效'}), 400
    
    # 创建用户
    password_hash = generate_password_hash(data['password'])
    user = User(
        username=data['username'],
        email=data['email'],
        password_hash=password_hash,
        role=role,
        gender=data.get('gender', 'unknown')
    )
    
    db.session.add(user)
    db.session.commit()
    
    # 生成JWT token
    token = jwt.encode(
                    {'user_id': user.id, 'exp': get_local_time() + timedelta(days=7)},
        app.config['SECRET_KEY'],
        algorithm='HS256'
    )
    
    return jsonify({
        'message': '注册成功',
        'token': token,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'gender': user.gender
        }
    }), 201

@app.route('/api/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': '缺少必要字段'}), 400
    
    user = User.query.filter_by(username=data['username']).first()
    
    if user and check_password_hash(user.password_hash, data['password']):
        # 更新最后在线时间
        user.last_seen = get_local_time()
        user.status = 'online'
        db.session.commit()
        
        # 生成JWT token
        token = jwt.encode(
            {'user_id': user.id, 'exp': get_local_time() + timedelta(days=7)},
            app.config['SECRET_KEY'],
            algorithm='HS256'
        )
        
        return jsonify({
            'message': '登录成功',
            'token': token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'gender': user.gender
            }
        })
    else:
        return jsonify({'error': '用户名或密码错误'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    """用户登出"""
    # 更新用户状态
    if current_user.is_authenticated:
        current_user.status = 'offline'
        current_user.last_seen = get_local_time()
        db.session.commit()
    
    return jsonify({'message': '登出成功'})

# 房间相关API
@app.route('/api/rooms', methods=['GET'])
def get_rooms():
    """获取房间列表"""
    rooms = Room.query.all()
    room_list = [{
        'id': room.id,
        'name': room.name,
        'description': room.description,
        'member_count': len(room.members),
        'max_members': room.max_members,
        'created_at': room.created_at.isoformat()
    } for room in rooms]
    
    print(f'返回房间列表: {room_list}')
    return jsonify(room_list)

@app.route('/api/rooms', methods=['POST'])
def create_room():
    """创建新房间"""
    data = request.get_json()
    
    if not data or not data.get('name'):
        return jsonify({'error': '房间名称不能为空'}), 400
    
    room = Room(
        name=data['name'],
        description=data.get('description', ''),
        max_members=data.get('max_members', 10),
        is_private=data.get('is_private', False),
        created_by=current_user.id if current_user.is_authenticated else 1
    )
    
    db.session.add(room)
    db.session.commit()
    
    return jsonify({
        'id': room.id,
        'name': room.name,
        'description': room.description,
        'created_at': room.created_at.isoformat()
    }), 201

@app.route('/api/rooms/<int:room_id>/join', methods=['POST'])
@jwt_required
def join_room(room_id):
    """加入房间"""
    room = Room.query.get_or_404(room_id)
    
    # 检查是否已经是成员
    existing_membership = RoomMembership.query.filter_by(
        user_id=current_user.id, room_id=room_id
    ).first()
    
    if existing_membership:
        existing_membership.is_online = True
        db.session.commit()
        return jsonify({'message': '已重新加入房间'})
    
    # 检查房间是否已满
    if len(room.members) >= room.max_members:
        return jsonify({'error': '房间已满'}), 400
    
    membership = RoomMembership(user_id=current_user.id, room_id=room_id, is_online=True)
    db.session.add(membership)
    db.session.commit()
    
    return jsonify({'message': '成功加入房间'})

@app.route('/api/rooms/<int:room_id>/leave', methods=['POST'])
@jwt_required
def leave_room(room_id):
    """离开房间"""
    room = Room.query.get_or_404(room_id)
    
    # 查找用户的成员关系
    membership = RoomMembership.query.filter_by(
        user_id=current_user.id, room_id=room_id
    ).first()
    
    if membership:
        # 设置用户在该房间为离线状态
        membership.is_online = False
        db.session.commit()
        
        return jsonify({'message': '已离开房间'})
    else:
        return jsonify({'error': '您不是该房间的成员'}), 400

@app.route('/api/rooms/<int:room_id>', methods=['GET'])
@jwt_required
def get_room(room_id):
    """获取房间信息"""
    room = Room.query.get_or_404(room_id)
    return jsonify({
        'id': room.id,
        'name': room.name,
        'description': room.description,
        'max_members': room.max_members,
        'member_count': len(room.members),
        'created_at': room.created_at.isoformat()
    })

@app.route('/api/rooms/<int:room_id>', methods=['PUT'])
def update_room(room_id):
    """更新房间信息"""
    room = Room.query.get_or_404(room_id)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': '缺少数据'}), 400
    
    try:
        if 'name' in data:
            room.name = data['name']
        if 'description' in data:
            room.description = data['description']
        if 'max_members' in data:
            room.max_members = data['max_members']
        if 'is_private' in data:
            room.is_private = data['is_private']
        
        room.updated_at = get_local_time()
        db.session.commit()
        
        return jsonify({
            'message': '房间更新成功',
            'room': {
                'id': room.id,
                'name': room.name,
                'description': room.description,
                'max_members': room.max_members,
                'is_private': room.is_private,
                'created_by': room.created_by,
                'created_at': room.created_at.isoformat(),
                'member_count': len(room.members)
            }
        })
    except Exception as e:
        db.session.rollback()
        print(f"更新房间失败: {e}")
        return jsonify({'error': '更新失败'}), 500

@app.route('/api/rooms/<int:room_id>', methods=['DELETE'])
def delete_room(room_id):
    """删除房间"""
    room = Room.query.get_or_404(room_id)
    
    try:
        # 删除房间相关的所有数据
        # 删除房间成员关系
        RoomMembership.query.filter_by(room_id=room_id).delete()
        
        # 删除房间消息
        Message.query.filter_by(room_id=room_id).delete()
        
        # 删除干预记录
        Intervention.query.filter_by(room_id=room_id).delete()
        
        # 删除统计数据
        Statistics.query.filter_by(room_id=room_id).delete()
        
        # 删除房间本身
        db.session.delete(room)
        db.session.commit()
        
        return jsonify({'message': '房间删除成功'})
    except Exception as e:
        db.session.rollback()
        print(f"删除房间失败: {e}")
        return jsonify({'error': '删除失败'}), 500

@app.route('/api/rooms/<int:room_id>/messages', methods=['GET'])
@jwt_required
def get_room_messages(room_id):
    """获取房间消息"""
    messages = Message.query.filter_by(room_id=room_id).order_by(Message.timestamp).all()
    message_list = []
    
    for msg in messages:
        # 获取用户头像
        user_avatar = ''
        if msg.user_id:
            user = User.query.get(msg.user_id)
            if user:
                user_avatar = user.avatar
        
        message_list.append({
            'id': msg.id,
            'content': msg.content,
            'author': msg.author,
            'avatar': user_avatar,
            'timestamp': msg.timestamp.isoformat(),
            'has_interruption': msg.has_interruption,
            'interruption_type': msg.interruption_type,
            'intervention_applied': msg.intervention_applied,
            # 统一字段，便于前端过滤与去重
            'room': str(room_id),
            'client_id': f'history-{msg.id}'
        })
    
    return jsonify(message_list)

@app.route('/api/rooms/<int:room_id>/messages', methods=['POST'])
@jwt_required
def send_message(room_id):
    """发送消息到房间"""
    data = request.get_json()
    
    if not data or not data.get('content'):
        return jsonify({'error': '消息内容不能为空'}), 400
    
    # 检查用户是否有权限发送消息到此房间
    # 管理员可以向任何房间发送消息
    if not current_user.is_admin():
        # 非管理员用户需要检查房间成员资格
        membership = RoomMembership.query.filter_by(
            user_id=current_user.id, room_id=room_id
        ).first()
        if not membership:
            return jsonify({'error': '您不是该房间的成员'}), 403
    else:
        # 管理员如果不是房间成员，自动加入
        membership = RoomMembership.query.filter_by(
            user_id=current_user.id, room_id=room_id
        ).first()
        if not membership:
            admin_membership = RoomMembership(
                user_id=current_user.id,
                room_id=room_id,
                role='admin',
                is_online=True
            )
            db.session.add(admin_membership)
            db.session.commit()
            print(f'管理员 {current_user.id} 自动加入房间 {room_id}')
    
    # === 移除禁言检查，取消渐进式治理 ===
    muted, remain = (False, 0)
    if False:  # 禁言功能已移除
        return jsonify({'error': f'你已被禁言，还有 {remain} 秒后解除。'}), 403

    suppress_user_message = False  # 触发禁言且目标为当前用户时，不广播本条

    # 创建消息
    message = Message(
        content=data['content'],
        author=current_user.display_name or current_user.username,
        gender=current_user.gender,
        room_id=room_id,
        user_id=current_user.id
    )
    
    db.session.add(message)
    db.session.commit()

    # === 新增：如果关闭了干预，直接广播并返回 ===
    if not app.config.get('INTERVENTION_ENABLED', False):
        message_data = {
            'id': message.id,
            'content': message.content,
            'author': message.author,
            'avatar': current_user.avatar,
            'timestamp': message.timestamp.isoformat(),
            'has_interruption': False,
            'interruption_type': None,
            'intervention_applied': False,
            'room': str(room_id)
        }
        socketio.emit('message', message_data, room=str(room_id))
        return jsonify(message_data), 201
    # =========================================

    intervention_message = None
    intervention_reason = None
    try:
        intervention_result = smart_intervention_engine.analyze_message(
            room_id=str(room_id),
            user_id=str(current_user.id),
            username=current_user.display_name or current_user.username,
            message_content=message.content,
            gender=current_user.gender
        )
        
        
        if intervention_result and intervention_result.should_intervene:
            message.has_interruption = True
            message.interruption_type = intervention_result.intervention_type.value
            message.intervention_applied = True
            
            # 保存干预消息和原因
            intervention_message = intervention_result.message
            intervention_reason = intervention_result.reason
            
            # 创建干预记录
            intervention_record = Intervention(
                room_id=room_id,
                message_id=message.id,
                strategy=intervention_result.intervention_type.value,
                intervention_text=intervention_result.message,
                trigger_type=intervention_result.intervention_type.value,
                trigger_reason=intervention_result.reason,
                intervention_type=intervention_result.intervention_type.value,
                offense_level=intervention_result.offense_level.value if intervention_result.offense_level else None,
                target_user=intervention_result.target_user,
                is_visible_to_admin_only=False
            )
            
            db.session.add(intervention_record)

            # 触发禁言时（当前策略已不禁言，此逻辑保留兼容，若未来开启禁言则生效）
            if getattr(intervention_result, 'action', None) == 'mute':
                seconds = getattr(intervention_result, 'mute_seconds', 300)
                target_name = getattr(intervention_result, 'target_user', None)
                mute_user_id = current_user.id
                mute_user_name = current_user.display_name or current_user.username

                try:
                    if target_name and target_name != mute_user_name:
                        last_target_msg = Message.query.filter_by(
                            room_id=int(room_id), author=target_name
                        ).order_by(Message.timestamp.desc()).first()
                        if last_target_msg and last_target_msg.user_id:
                            mute_user_id = last_target_msg.user_id
                            mute_user = User.query.get(mute_user_id)
                            mute_user_name = mute_user.display_name or mute_user.username if mute_user else target_name
                        else:
                            mute_user = User.query.filter((User.display_name == target_name) | (User.username == target_name)).first()
                            if mute_user:
                                mute_user_id = mute_user.id
                                mute_user_name = mute_user.display_name or mute_user.username
                except Exception:
                    pass

                # 当前不执行禁言，仅保留兼容代码路径
                # smart_intervention_engine.record_mute(str(room_id), str(mute_user_id), seconds)
                suppress_user_message = False
            
    except Exception as e:
        # 如果智能干预失败，继续处理消息
        pass
    
    db.session.commit()
    
    # 通过WebSocket广播消息到房间
    message_data = {
        'id': message.id,
        'content': message.content,
        'author': message.author,
        'avatar': current_user.avatar,  # 添加用户头像
        'timestamp': message.timestamp.isoformat(),
        'has_interruption': message.has_interruption,
        'interruption_type': message.interruption_type,
        'intervention_applied': message.intervention_applied,
        'room': str(room_id)
    }
    
    # 发送消息到房间（如被禁言且对象就是当前用户，则不广播本条）
    if not suppress_user_message:
        try:
            from app import manual_emit_to_room
            manual_emit_to_room('message', message_data, str(room_id))
        except Exception:
            pass
        socketio.emit('message', message_data, room=str(room_id))
    
    # 如果有干预，发送干预消息
    if message.intervention_applied and intervention_message:
        intervention_data = {
            'type': 'intervention',
            'message': intervention_message,
            'strategy': message.interruption_type,
            'timestamp': get_local_time().isoformat(),
            'room': str(room_id)
        }
        
        intervention_data_admin = intervention_data.copy()
        intervention_data_admin['reason'] = intervention_reason
        intervention_data_admin['is_admin_info'] = True
        
        socketio.emit('intervention', intervention_data, room=str(room_id))
        
        # Fallback：将干预也作为一条普通机器人消息保存并广播，避免前端漏显
        try:
            bot_message = Message(
                content=intervention_message,
                author='Chime',
                gender='unknown',
                room_id=room_id,
                user_id=None
            )
            db.session.add(bot_message)
            db.session.commit()

            bot_payload = {
                'id': bot_message.id,
                'content': bot_message.content,
                'author': bot_message.author,
                'avatar': '',
                'timestamp': bot_message.timestamp.isoformat(),
                'has_interruption': False,
                'interruption_type': intervention_result.intervention_type.value if intervention_result else None,
                'intervention_applied': True,
                'room': str(room_id),
                'client_id': f"chatbot-{int(time.time() * 1000)}"
            }
            socketio.emit('message', bot_payload, room=str(room_id))
        except Exception as _:
            pass

        # 单独给管理员发送包含原因的干预消息
        # socketio.emit('intervention_admin', intervention_data_admin, room=str(room_id))
        socketio.emit('intervention_admin', intervention_data_admin, room='admin_room')

    
    return jsonify(message_data), 201

@app.route('/api/user/info', methods=['GET'])
def get_user_info():
    """获取当前用户信息"""
    # 检查JWT token
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            user_id = payload['user_id']
            user = User.query.get(user_id)
            if user:
                return jsonify({
                    'id': user.id,
                    'username': user.username,
                    'display_name': user.display_name,
                    'email': user.email,
                    'gender': user.gender,
                    'bio': user.bio,
                    'avatar': user.avatar,
                    'role': user.role,
                    'status': user.status,
                    'created_at': user.created_at.isoformat(),
                    'message_count': len(user.messages),
                    'room_count': len(user.room_memberships)
                })
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token已过期'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': '无效的Token'}), 401
    
    # 如果JWT token无效，检查session认证
    if not current_user.is_authenticated:
        return jsonify({'error': '未登录'}), 401
    
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'display_name': current_user.display_name,
        'email': current_user.email,
        'gender': current_user.gender,
        'bio': current_user.bio,
        'avatar': current_user.avatar,
        'role': current_user.role,
        'status': current_user.status,
        'created_at': current_user.created_at.isoformat(),
        'message_count': len(current_user.messages),
        'room_count': len(current_user.room_memberships)
    })

@app.route('/api/stats/<int:room_id>', methods=['GET'])
def get_room_stats(room_id):
    """获取房间统计数据"""
    room = Room.query.get_or_404(room_id)
    
    # 获取今日统计
    today = get_local_time().date()
    stats = Statistics.query.filter_by(room_id=room_id, date=today).first()
    
    if not stats:
        # 创建新的统计记录
        stats = Statistics(room_id=room_id, date=today)
        db.session.add(stats)
        db.session.commit()
    
    # 计算实时统计
    messages = Message.query.filter_by(room_id=room_id).all()
    total_messages = len(messages)
    male_messages = len([m for m in messages if m.gender == 'male'])
    female_messages = len([m for m in messages if m.gender == 'female'])
    interruptions = len([m for m in messages if m.has_interruption])
    interventions = len([m for m in messages if m.intervention_applied])
    
    return jsonify({
        'total_messages': total_messages,
        'male_messages': male_messages,
        'female_messages': female_messages,
        'interruptions': interruptions,
        'interventions': interventions,
        'male_percentage': round(male_messages / total_messages * 100, 1) if total_messages > 0 else 0,
        'female_percentage': round(female_messages / total_messages * 100, 1) if total_messages > 0 else 0
    })

@app.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    """获取仪表板统计数据"""
    # 计算总体统计
    total_messages = Message.query.count()
    total_interruptions = Message.query.filter_by(has_interruption=True).count()
    total_interventions = Message.query.filter_by(intervention_applied=True).count()
    
    # 性别分布
    male_messages = Message.query.filter_by(gender='male').count()
    female_messages = Message.query.filter_by(gender='female').count()
    unknown_messages = Message.query.filter_by(gender='unknown').count()
    
    # TKI策略分布
    interventions = Intervention.query.all()
    strategy_counts = {}
    for intervention in interventions:
        strategy = intervention.strategy
        strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
    
    # 计算干预效果（简化计算）
    effectiveness = 85  # 默认值，实际应该基于用户反馈计算
    
    return jsonify({
        'totalMessages': total_messages,
        'totalInterruptions': total_interruptions,
        'totalInterventions': total_interventions,
        'effectiveness': effectiveness,
        'messageChange': '+12',
        'interruptionChange': '-5',
        'interventionChange': '+8',
        'effectivenessChange': '+3',
        'genderDistribution': {
            'male': male_messages,
            'female': female_messages,
            'unknown': unknown_messages
        },
        'strategyDistribution': strategy_counts
    })

@app.route('/api/dashboard/activity', methods=['GET'])
def get_dashboard_activity():
    """获取最近活动"""
    # 获取最近的消息和干预
    recent_messages = Message.query.order_by(Message.timestamp.desc()).limit(10).all()
    recent_interventions = Intervention.query.order_by(Intervention.created_at.desc()).limit(5).all()
    
    activities = []
    
    # 添加消息活动
    for msg in recent_messages:
        activities.append({
            'type': 'message',
            'text': f'{msg.author} 发送了消息',
            'timestamp': msg.timestamp.isoformat()
        })
    
    # 添加干预活动
    for intervention in recent_interventions:
        activities.append({
            'type': 'intervention',
            'text': f'Chime 应用了 {intervention.strategy} 策略',
            'timestamp': intervention.created_at.isoformat()
        })
    
    # 按时间排序
    activities.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return jsonify(activities[:15])  # 返回最近15个活动

@app.route('/api/users', methods=['GET'])
def get_users():
    """获取用户列表"""
    users = User.query.filter_by(is_active=True).all()
    return jsonify([{
        'id': user.id,
        'username': user.username,
        'display_name': user.display_name,
        'gender': user.gender,
        'status': user.status,
        'role': user.role,
        'avatar': user.avatar
    } for user in users])

@app.route('/api/rooms/<int:room_id>/members', methods=['GET'])
@jwt_required
def get_room_members(room_id):
    """获取房间成员列表"""
    room = Room.query.get_or_404(room_id)
    members = []
    
    for membership in room.members:
        user = User.query.get(membership.user_id)
        if user:
            # 简化逻辑：只要在房间中就显示为在线
            is_online = membership.is_online
            
            members.append({
                'user_id': user.id,
                'id': user.id,
                'username': user.username,
                'display_name': user.display_name,
                'gender': user.gender,
                'avatar': user.avatar,
                'role': membership.role,
                'is_online': is_online,
                'joined_at': membership.joined_at.isoformat()
            })
    
    return jsonify(members)

@app.route('/api/user/profile', methods=['PUT'])
def update_user_profile():
    """更新用户资料"""
    # 检查JWT token
    auth_header = request.headers.get('Authorization')
    user = None
    
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            user_id = payload['user_id']
            user = User.query.get(user_id)
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token已过期'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': '无效的Token'}), 401
    
    # 如果JWT token无效，检查session认证
    if not user and not current_user.is_authenticated:
        return jsonify({'error': '未登录'}), 401
    
    if not user:
        user = current_user
    
    try:
        # 获取表单数据
        display_name = request.form.get('display_name', '')
        gender = request.form.get('gender', 'unknown')
        
        # 允许修改显示名称、性别和头像，其他字段保持不变
        
        # 处理头像上传
        avatar_path = user.avatar  # 保持原头像
        if 'avatar' in request.files:
            avatar_file = request.files['avatar']
            if avatar_file and avatar_file.filename:
                # 创建上传目录
                upload_dir = os.path.join(app.root_path, 'static', 'avatars')
                os.makedirs(upload_dir, exist_ok=True)
                
                # 生成文件名
                filename = f"avatar_{user.id}_{int(get_local_time().timestamp())}.jpg"
                filepath = os.path.join(upload_dir, filename)
                
                # 保存文件
                avatar_file.save(filepath)
                avatar_path = f"/static/avatars/{filename}"
        
        # 更新用户信息（更新显示名称、性别和头像）
        user.display_name = display_name
        user.gender = gender
        user.avatar = avatar_path
        
        db.session.commit()
        
        return jsonify({
            'message': '资料更新成功',
            'user': {
                'id': user.id,
                'username': user.username,
                'display_name': user.display_name,
                'email': user.email,
                'gender': user.gender,
                'bio': user.bio,
                'avatar': user.avatar,
                'role': user.role,
                'created_at': user.created_at.isoformat(),
                'message_count': len(user.messages),
                'room_count': len(user.room_memberships)
            }
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"更新用户资料失败: {e}")
        return jsonify({'error': '更新失败'}), 500


@app.route('/profile')
def profile():
    """用户资料页面"""
    return render_template('profile.html')

def _emit_intervention_to_room(intervention_result, room_id):
    """发送干预消息到指定房间"""
    try:
        if not intervention_result or not intervention_result.should_intervene:
            return
            
        intervention_data = {
            'type': 'intervention',
            'message': intervention_result.message,
            'strategy': intervention_result.intervention_type.value if hasattr(intervention_result.intervention_type, 'value') else str(intervention_result.intervention_type),
            'timestamp': get_local_time().isoformat()
        }
        
        # 发送给房间所有用户
        socketio.emit('intervention', intervention_data, room=str(room_id))
        
        # 如果有调试信息，发送给管理员
        if hasattr(intervention_result, 'reason') and intervention_result.reason:
            admin_data = dict(intervention_data)
            admin_data['reason'] = intervention_result.reason
            admin_data['is_admin_info'] = True
            socketio.emit('intervention_admin', admin_data, room='admin_room')
            
        print(f"✅ [干预发送] 房间{room_id}干预消息已发送: {intervention_result.message[:50]}...")
        
    except Exception as e:
        print(f"❌ [干预发送] 房间{room_id}发送失败: {e}")

def _trigger_icebreaker_for_room(room_id):
    """为指定房间触发破冰检查"""
    try:
        room_id = str(room_id)
        print(f"🎯 [破冰触发] 开始检查房间{room_id}...")
        
        if room_id not in realtime_monitor.active_rooms:
            print(f"📊 [破冰触发] 房间{room_id}不在活跃状态")
            return
        
        current_time = time.time()
        
        # 检查房间是否需要破冰
        recent_messages = list(smart_intervention_engine.room_recent_messages.get(room_id, []))
        non_admin_messages = [msg for msg in recent_messages if not smart_intervention_engine._is_admin_user(str(msg['user_id']))]
        
        # 破冰策略：确保给用户足够时间响应
        should_trigger = False
        if not non_admin_messages:
            if recent_messages:
                # 有admin消息但用户未响应，需要等待45秒后才破冰
                last_admin_msg_time = recent_messages[-1]['timestamp']
                admin_silence = current_time - last_admin_msg_time
                if admin_silence >= 45:  # 确保45秒后才触发破冰
                    should_trigger = True
                    reason = f"admin消息后用户沉默{int(admin_silence)}秒，触发破冰"
            else:
                # 完全没有消息，也需要等待45秒，让监控系统处理
                should_trigger = False
                reason = "房间无消息历史，等待监控系统处理"
        else:
            last_user_msg_time = non_admin_messages[-1]['timestamp']
            silence_duration = current_time - last_user_msg_time
            if silence_duration >= 45:  # 45秒首次破冰触发
                should_trigger = True
                reason = f"用户沉默{int(silence_duration)}秒"
        
        if should_trigger:
            print(f"🎯 [破冰触发] 房间{room_id}需要破冰: {reason}")
            result = smart_intervention_engine._check_agenda_transition(room_id)
            if result and result.should_intervene:
                _emit_intervention_to_room(result, room_id)
                print(f"✅ [破冰触发] 房间{room_id}破冰消息已发送")
            else:
                print(f"❌ [破冰触发] 房间{room_id}未生成破冰消息")
        else:
            print(f"📊 [破冰触发] 房间{room_id}暂不需要破冰")
                
    except Exception as e:
        print(f"❌ [破冰触发] 房间{room_id}处理失败: {e}")

def _trigger_icebreaker_for_all_rooms():
    """当Chatbot开关启用时，为所有活跃房间触发破冰检查"""
    try:
        print("🎯 [破冰触发] 开始检查所有活跃房间...")
        
        # 获取所有活跃房间
        active_rooms = list(realtime_monitor.active_rooms)
        if not active_rooms:
            print("📊 [破冰触发] 当前无活跃房间")
            return
        
        print(f"📊 [破冰触发] 发现{len(active_rooms)}个活跃房间: {active_rooms}")
        
        current_time = time.time()
        triggered_rooms = []
        
        for room_id in active_rooms:
            try:
                room_id = str(room_id)
                
                # 检查房间是否需要破冰
                recent_messages = list(smart_intervention_engine.room_recent_messages.get(room_id, []))
                non_admin_messages = [msg for msg in recent_messages if not smart_intervention_engine._is_admin_user(str(msg['user_id']))]
                
                # 如果没有用户消息，或者用户沉默时间较长，触发破冰
                needs_icebreaker = False
                if len(non_admin_messages) == 0 and len(recent_messages) > 0:
                    # 有admin消息但没有用户响应，需要检查时间间隔
                    last_admin_msg_time = recent_messages[-1]['timestamp']
                    admin_silence = current_time - last_admin_msg_time
                    if admin_silence >= 45:  # 确保45秒后才触发破冰
                        needs_icebreaker = True
                        reason = f"admin消息后用户沉默{int(admin_silence)}秒"
                elif len(recent_messages) == 0:
                    # 完全没有消息，让监控系统处理
                    needs_icebreaker = False
                    reason = "房间无消息历史，等待监控系统处理"
                elif len(non_admin_messages) > 0:
                    # 检查用户沉默时间
                    last_user_msg_time = non_admin_messages[-1]['timestamp']
                    silence_duration = current_time - last_user_msg_time
                    if silence_duration >= 45:  # 45秒首次破冰触发
                        needs_icebreaker = True
                        reason = f"用户沉默{int(silence_duration)}秒"
                
                if needs_icebreaker:
                    print(f"🚀 [破冰触发] 房间{room_id}: {reason}，立即触发破冰")
                    
                    # 重置冷却时间，确保可以立即执行
                    smart_intervention_engine.room_last_agenda_transition[room_id] = 0
                    smart_intervention_engine.room_last_intervention_ts[room_id] = 0
                    
                    # 检查并执行破冰
                    agenda_result = smart_intervention_engine._check_agenda_transition(room_id)
                    if agenda_result and agenda_result.should_intervene:
                        # 手动触发干预执行
                        realtime_monitor._execute_intervention(room_id, agenda_result)
                        triggered_rooms.append(room_id)
                        print(f"✅ [破冰触发] 房间{room_id}破冰成功: {agenda_result.message[:40]}...")
                    else:
                        print(f"⚠️ [破冰触发] 房间{room_id}破冰检查未通过")
                else:
                    print(f"✅ [破冰触发] 房间{room_id}无需破冰")
                    
            except Exception as e:
                print(f"❌ [破冰触发] 房间{room_id}处理失败: {e}")
        
        if triggered_rooms:
            print(f"🎉 [破冰触发] 总计为{len(triggered_rooms)}个房间触发了破冰: {triggered_rooms}")
        else:
            print("📝 [破冰触发] 所有房间均无需破冰")
            
    except Exception as e:
        print(f"❌ [破冰触发] 全局处理失败: {e}")
        import traceback
        print(f"详细错误: {traceback.format_exc()}")

@app.route('/admin')
@admin_required
def admin_dashboard():
    """管理员控制面板"""
    return render_template('admin_dashboard.html')


# @socketio.on('connect')
# def handle_connect():
#     print(f'客户端连接: {request.sid}')
    
#     # 尝试从查询参数获取JWT token
#     token = request.args.get('token')
#     if token:
#         try:
#             payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
#             user_id = payload['user_id']
#             session['user_id'] = user_id
#             print(f'WebSocket连接用户ID: {user_id}')
#         except jwt.ExpiredSignatureError:
#             print('JWT token已过期')
#         except jwt.InvalidTokenError:
#             print('无效的JWT token')

@socketio.on('connect')
def handle_connect():
    print(f'客户端连接: {request.sid}')
    token = request.args.get('token')
    if token:
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            user_id = payload['user_id']
            session['user_id'] = user_id
            print(f'WebSocket连接用户ID: {user_id}')

            # === 新增：管理员加入 admin_room ===
            user = User.query.get(user_id)
            if user and user.is_admin():
                session['is_admin'] = True
                join_room('admin_room')
                print(f'管理员 {user.username} 已加入 admin_room')
            else:
                session['is_admin'] = False

        except jwt.ExpiredSignatureError:
            print('JWT token已过期')
        except jwt.InvalidTokenError:
            print('无效的JWT token')



@socketio.on('disconnect')
def handle_disconnect():
    print(f'客户端断开: {request.sid}')
    # 从手动房间管理系统中移除客户端
    remove_client_from_rooms(request.sid)

@socketio.on('echo')
def handle_echo(data):
    """简单的echo测试"""
    print(f'收到echo事件: {data}')
    emit('echo', {'response': '服务器收到echo', 'data': data})

@socketio.on('test')
def handle_test(data):
    """测试WebSocket连接"""
    print(f'收到测试消息: {data}')
    # 回复测试消息
    emit('test', {'message': '服务器收到测试消息', 'data': data})

@socketio.on('join_room')
def handle_join_room(data):
    print(f'=== 收到加入房间事件 ===')
    print(f'事件数据: {data}')
    print(f'当前session: {session}')
    print(f'客户端ID: {request.sid}')
    
    room = data.get('room')
    if room:
        print(f'用户请求加入房间: {room}')
        # 确保房间是字符串类型
        room = str(room)
        
        # 先离开所有之前的房间（除了默认房间）
        from flask_socketio import rooms
        current_rooms = rooms(request.sid)
        for old_room in current_rooms:
            if old_room != request.sid:  # 不离开默认房间
                leave_room(old_room)
                print(f'用户离开旧房间: {old_room}')
        
        # 使用手动房间管理系统
        add_client_to_room(request.sid, room)
        
        # 也尝试使用Flask-SocketIO的原生方法（作为备用）
        try:
            join_room(room)
            print(f'Flask-SocketIO: 用户已加入房间 {room}')
        except Exception as e:
            print(f'Flask-SocketIO加入房间失败: {e}')
        
        # 房间加入成功，不再发送系统消息给用户
        print(f'✅ 用户已成功加入房间 {room}，手动房间管理系统工作正常')
        
        # 更新用户状态
        user_id = session.get('user_id')
        print(f'从session获取的用户ID: {user_id}')
        
        if user_id:
            try:
                # 更新房间成员状态
                membership = RoomMembership.query.filter_by(
                    user_id=user_id, room_id=int(room)
                ).first()
                
                user = User.query.get(user_id)
                
                if membership:
                    membership.is_online = True
                    db.session.commit()
                    print(f'用户 {user_id} 在房间 {room} 中状态已更新为在线')
                elif user and user.is_admin():
                    # 管理员即使不是房间成员也允许加入，自动创建成员关系
                    admin_membership = RoomMembership(
                        user_id=user_id, 
                        room_id=int(room), 
                        role='admin',
                        is_online=True
                    )
                    db.session.add(admin_membership)
                    db.session.commit()
                    print(f'管理员 {user_id} 自动加入房间 {room} 并设置为在线')
                else:
                    print(f'警告: 用户 {user_id} 不是房间 {room} 的成员')
            except Exception as e:
                print(f'更新用户状态失败: {e}')
        
        # 通知其他用户有新用户加入
        print(f'广播user_joined事件到房间 {room}')
        socketio.emit('user_joined', {
            'room': room,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat()
        }, room=room)
        
        # 将房间添加到实时监控
        realtime_monitor.add_active_room(room)
        
        print(f'=== 加入房间事件处理完成 ===')
    else:
        print(f'错误: 房间ID为空')

@socketio.on('leave_room')
def handle_leave_room(data):
    print(f'收到离开房间事件: {data}')
    room = data.get('room')
    if room:
        leave_room(room)
        print(f'用户已离开房间: {room}')
        
        # 更新用户状态
        user_id = session.get('user_id')
        if user_id:
            try:
                # 更新房间成员状态
                membership = RoomMembership.query.filter_by(
                    user_id=user_id, room_id=int(room)
                ).first()
                if membership:
                    membership.is_online = False
                    db.session.commit()
                    print(f'用户 {user_id} 在房间 {room} 中状态已更新为离线')
            except Exception as e:
                print(f'更新用户状态失败: {e}')
        
        # 通知其他用户有用户离开
        socketio.emit('user_left', {
            'room': room,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat()
        }, room=room)

@socketio.on('tki_style_change')
def handle_tki_style_change(data):
    print(f'收到TKI风格选择: {data}')
    room = data.get('room')
    style = data.get('style')
    
    if not room or not style:
        print('房间或风格数据为空')
        return
    
    # 验证风格是否有效
    valid_styles = ['none', 'collaborating', 'accommodating', 'competing', 'compromising', 'avoiding']
    if style not in valid_styles:
        print(f'无效的TKI风格: {style}')
        return
    
    try:
        # 更新数据库中的干预风格设置
        # 首先将所有现有设置设为非激活
        InterventionStyle.query.update({'is_active': False})
        
        # 查找是否已有该风格的记录
        existing_style = InterventionStyle.query.filter_by(style=style).first()
        if existing_style:
            # 更新现有记录
            existing_style.is_active = True
            existing_style.description = get_tki_style_description(style)
            existing_style.updated_at = get_local_time()
        else:
            # 创建新记录
            new_style = InterventionStyle(
                style=style,
                description=get_tki_style_description(style),
                is_active=True
            )
            db.session.add(new_style)
        
        db.session.commit()
        
        # 更新应用配置缓存
        app.config['CURRENT_INTERVENTION_STYLE'] = style
        
        print(f'TKI风格已保存到数据库: {style}')
        
    except Exception as e:
        print(f'保存TKI风格到数据库失败: {e}')
        db.session.rollback()
    
    # 广播风格选择到房间
    emit('tki_style_updated', {
        'room': room,
        'style': style,
        'description': get_tki_style_description(style)
    }, room=room)
    
    # 同时向所有客户端广播（确保所有用户都能收到）
    socketio.emit('intervention_style_updated', {
        'style': style,
        'description': get_tki_style_description(style)
    })
    
    print(f'TKI风格已更新为: {style}')

def get_tki_style_description(style):
    """获取TKI风格的描述"""
    descriptions = {
        'none': '无插话 - AI不会进行任何干预',
        'collaborating': '协作型 - 整合各方观点，推动共识，平衡支持女性表达与维护群体和谐',
        'accommodating': '迁就型 - 优先维护和谐，用温和语气为女性缓颊，避免冲突',
        'competing': '竞争型 - 强势捍卫女性表达权，正面对抗偏见，可能激化冲突',
        'compromising': '妥协型 - 设置公平讨论机制，保障发言机会，不参与观点评价',
        'avoiding': '回避型 - 岔开矛盾话题，表面轻松，实则削弱女性表达机会'
    }
    return descriptions.get(style, '未知风格')

# @socketio.on('send_message')
# def handle_send_message(data):
#     print(f'=== 开始处理send_message事件 ===')
#     print(f'收到WebSocket消息: {data}')
#     print(f'数据类型: {type(data)}')
#     print(f'数据内容: {json.dumps(data, default=str) if data else "None"}')
    
#     room = data.get('room')
#     message_data = data.get('message')
    
#     print(f'房间: {room}, 消息数据: {message_data}')
    
#     if not room or not message_data:
#         print('房间或消息数据为空，退出处理')
#         return
    
#     print(f'=== 数据验证通过，继续处理 ===')
    
#     # 获取用户信息
#     user_id = session.get('user_id')
#     print(f'从session获取的用户ID: {user_id}')
    
#     if not user_id and current_user.is_authenticated:
#         user_id = current_user.id
#         print(f'从current_user获取的用户ID: {user_id}')
    
#     print(f'最终用户ID: {user_id}')
    
#     # 如果没有用户ID（测试页面），使用默认用户
#     if not user_id:
#         print('无法获取用户ID，使用默认用户')
#         user = User.query.first()  # 获取第一个用户作为默认用户
#         if not user:
#             # 如果没有用户，创建一个默认用户
#             user = User(
#                 username='test_user',
#                 email='test@example.com',
#                 password_hash='test',
#                 display_name='测试用户',
#                 gender='unknown'
#             )
#             db.session.add(user)
#             db.session.commit()
#             print(f'创建默认用户: {user.username}')
#         else:
#             print(f'使用现有用户: {user.username}')
#     else:
#         user = User.query.get(user_id)
#         if not user:
#             print('用户不存在')
#             return
    
#     print(f'用户信息: {user.username}')
    
#     # 创建消息记录
#     message = Message(
#         content=message_data['content'],
#         author=user.display_name or user.username,
#         gender=user.gender,
#         room_id=int(room),
#         user_id=user.id
#     )
    
#     print(f'创建消息: {message.content}')
    
#     db.session.add(message)
#     db.session.commit()
    
#     print(f'消息已保存到数据库，ID: {message.id}')
    
#     intervention_message = None
#     intervention_reason = None
#     try:
#         intervention_result = smart_intervention_engine.analyze_message(
#             room_id=room,
#             user_id=str(user.id),
#             username=user.display_name or user.username,
#             message_content=message.content,
#             gender=user.gender
#         )
        
        
#         if intervention_result and intervention_result.should_intervene:
#             message.has_interruption = True
#             message.interruption_type = intervention_result.intervention_type.value
#             message.intervention_applied = True
            
#             # 保存干预消息和原因
#             intervention_message = intervention_result.message
#             intervention_reason = intervention_result.reason
            
#             # 创建干预记录
#             intervention_record = Intervention(
#                 room_id=int(room),
#                 message_id=message.id,
#                 strategy=intervention_result.intervention_type.value,
#                 intervention_text=intervention_result.message,
#                 trigger_type=intervention_result.intervention_type.value,
#                 trigger_reason=intervention_result.reason,
#                 intervention_type=intervention_result.intervention_type.value,
#                 offense_level=intervention_result.offense_level.value if intervention_result.offense_level else None,
#                 target_user=intervention_result.target_user,
#                 is_visible_to_admin_only=False
#             )
            
#             db.session.add(intervention_record)
#             db.session.commit()
            
            
#     except Exception as e:
#         # 如果智能干预失败，继续处理消息
#         pass
    
#     # 构建消息数据
#     message_info = {
#         'id': message.id,
#         'content': message.content,
#         'author': message.author,
#         'avatar': user.avatar,  # 添加用户头像
#         'timestamp': message.timestamp.isoformat(),
#         'has_interruption': message.has_interruption,
#         'interruption_type': message.interruption_type,
#         'intervention_applied': message.intervention_applied,
#         'client_id': message_data.get('client_id'),
#         'room': room
#     }
    
#     print(f'准备广播消息: {message_info}')
#     print(f'广播到房间: {room}')
    
#     # 确保room是字符串类型
#     room = str(room)
    
#     # 获取房间内当前连接的客户端数量
#     from flask_socketio import rooms
#     room_clients = rooms(room)
#     print(f'房间 {room} 内当前连接的客户端: {room_clients}')
#     print(f'当前客户端ID: {request.sid}')
    
#     # 使用更可靠的广播方法
#     try:
#         # 方法1：使用socketio.emit到房间
#         socketio.emit('message', message_info, room=room)
#         print(f'消息已广播到房间 {room}')
        
#         # 方法2：如果房间为空，广播给所有连接的客户端（备用方案）
#         if not room_clients:
#             print(f'房间 {room} 为空，广播给所有客户端')
#             socketio.emit('message', message_info)
#             print(f'消息已广播给所有客户端')
            
#     except Exception as e:
#         print(f'广播消息时出错: {e}')
#         # 备用方案：广播给所有客户端
#         socketio.emit('message', message_info)
#         print(f'使用备用方案广播消息')
    
#     print(f'=== send_message事件处理完成 ===')


#   2025.08.27 新增 完整替换上方接口：handle_send_message

@socketio.on('send_message')
def handle_send_message(data):
    print(f'=== 开始处理send_message事件 ===')
    print(f'收到WebSocket消息: {data}')
    print(f'数据类型: {type(data)}')
    print(f'数据内容: {json.dumps(data, default=str) if data else "None"}')
    
    # 旧版干预广播方法已由后台任务替代
    
    room = data.get('room')
    message_data = data.get('message')
    
    print(f'房间: {room}, 消息数据: {message_data}')
    
    if not room or not message_data:
        print('房间或消息数据为空，退出处理')
        return
    
    print(f'=== 数据验证通过，继续处理 ===')
    
    # 获取用户信息
    user_id = session.get('user_id')
    print(f'从session获取的用户ID: {user_id}')
    
    if not user_id and current_user.is_authenticated:
        user_id = current_user.id
        print(f'从current_user获取的用户ID: {user_id}')
    
    print(f'最终用户ID: {user_id}')
    
    # 如果没有用户ID（测试页面），使用默认用户
    if not user_id:
        print('无法获取用户ID，使用默认用户')
        user = User.query.first()  # 获取第一个用户作为默认用户
        if not user:
            user = User(
                username='test_user',
                email='test@example.com',
                password_hash='test',
                display_name='测试用户',
                gender='unknown'
            )
            db.session.add(user)
            db.session.commit()
            print(f'创建默认用户: {user.username}')
        else:
            print(f'使用现有用户: {user.username}')
    else:
        user = User.query.get(user_id)
        if not user:
            print('用户不存在')
            return
    
    print(f'用户信息: {user.username}')

    # ===2025.8.27  新增：检查用户权限和房间成员资格 ===
    # 检查用户是否有权限发送消息到此房间
    # 管理员可以向任何房间发送消息
    if not user.is_admin():
        # 非管理员用户需要检查房间成员资格
        membership = RoomMembership.query.filter_by(
            user_id=user.id, room_id=int(room)
        ).first()
        if not membership:
            print(f'用户 {user.username} 不是房间 {room} 的成员，拒绝发送消息')
            notice = {
                'id': -1,
                'content': '您不是该房间的成员，无法发送消息。',
                'author': 'System',
                'avatar': '',
                'timestamp': get_local_time().isoformat(),
                'has_interruption': False,
                'interruption_type': None,
                'intervention_applied': False,
                'room': str(room)
            }
            socketio.emit('message', notice, to=request.sid)
            return
    else:
        # 管理员如果不是房间成员，自动加入
        membership = RoomMembership.query.filter_by(
            user_id=user.id, room_id=int(room)
        ).first()
        if not membership:
            admin_membership = RoomMembership(
                user_id=user.id,
                room_id=int(room),
                role='admin',
                is_online=True
            )
            db.session.add(admin_membership)
            db.session.commit()
            print(f'管理员 {user.username} 自动加入房间 {room}')

    # === 移除禁言检查，取消渐进式治理 ===
    muted, remain = (False, 0)
    if False:  # 禁言功能已移除
        # 只给本人一个提示，不影响他人（发到当前连接的 socket 会话）
        notice = {
            'id': -1,
            'content': f'你已被禁言，还有 {remain} 秒后解除。',
            'author': 'Chime',
            'avatar': '',
            'timestamp': get_local_time().isoformat(),
            'has_interruption': False,
            'interruption_type': None,
            'intervention_applied': False,
            'room': str(room)
        }
        # socketio.emit('message', notice, room=request.sid)
        socketio.emit('message', notice, to=request.sid)
        print(f'[拦截] 用户({user.id}) 在房间({room})处于禁言中，拦截消息。')
        return

    
    # 创建消息记录
    message = Message(
        content=message_data['content'],
        author=user.display_name or user.username,
        gender=user.gender,
        room_id=int(room),
        user_id=user.id
    )
    
    print(f'创建消息: {message.content}')
    
    db.session.add(message)
    db.session.commit()

    print(f'消息已保存到数据库，ID: {message.id}')
    
    # === 立即广播用户原消息（不等待智能干预） ===
    immediate_message_info = {
        'id': message.id,
        'content': message.content,
        'author': user.display_name or user.username,
        'avatar': user.avatar or '',
        'timestamp': message.timestamp.isoformat(),
        'has_interruption': False,
        'interruption_type': None,
        'intervention_applied': False,
        'client_id': (message_data.get('client_id') if isinstance(message_data, dict) else None),
        'room': str(room)
    }
    manual_emit_to_room('message', immediate_message_info, str(room))
    print(f"⚡ [即时广播] 用户消息已发送到房间 {room}")

    # === 在后台执行智能干预分析并推送Chatbot消息 ===
    def _process_intervention_background(room_str: str, user_obj_id: int, user_display_name: str, user_gender: str, message_obj_id: int):
        try:
            with app.app_context():
                room_obj_local = Room.query.get(int(room_str))
                if not room_obj_local or not room_obj_local.chatbot_enabled:
                    print(f"🔕 [后台干预] 房间{room_str}未启用Chatbot，跳过干预分析")
                    return

                # 重新获取message，确保在应用上下文中
                msg = Message.query.get(message_obj_id)
                if not msg:
                    return

                print(f"🧠 [后台干预] 开始分析: 用户{user_obj_id} - '{msg.content[:30]}...'")
                # --- 干预分析前的轻量白名单/放宽处理 ---
                original_content = msg.content or ''
                content_for_analysis = original_content
                # 1) 拉回话题白名单：这些语句倾向于正向引导，避免被当作冲突
                topic_pullback_whitelist = ['回到主题', '回到足球', '聊回足球', '回到正题']
                is_topic_pullback = any(kw in original_content for kw in topic_pullback_whitelist)
                # 2) 放宽允许的昵称：例如“胖虎”不触发毒性（仅用于判定，不改存储）
                allowed_nicknames = ['胖虎']
                for _nick in allowed_nicknames:
                    content_for_analysis = content_for_analysis.replace(_nick, '【昵称】')

                try:
                    intervention_result = None if is_topic_pullback else smart_intervention_engine.analyze_message(
                        room_id=room_str,
                        user_id=str(user_obj_id),
                        username=user_display_name,
                        message_content=content_for_analysis,
                        gender=user_gender
                    )
                except Exception as e:
                    print(f"❌ [后台干预] 分析失败: {e}")
                    return

                if intervention_result and intervention_result.should_intervene:
                    # 记录干预
                    intervention_record = Intervention(
                        room_id=int(room_str),
                        message_id=msg.id,
                        strategy=intervention_result.intervention_type.value,
                        intervention_text=intervention_result.message,
                        trigger_type=intervention_result.intervention_type.value,
                        trigger_reason=intervention_result.reason,
                        intervention_type=intervention_result.intervention_type.value,
                        offense_level=intervention_result.offense_level.value if intervention_result.offense_level else None,
                        target_user=intervention_result.target_user,
                        is_visible_to_admin_only=False
                    )
                    db.session.add(intervention_record)

                    # 保存机器人消息
                    bot_message = Message(
                        content=intervention_result.message,
                        author='Chime',
                        gender='unknown',
                        room_id=int(room_str),
                        user_id=None
                    )
                    db.session.add(bot_message)
                    db.session.commit()

                    bot_payload = {
                        'id': bot_message.id,
                        'content': bot_message.content,
                        'author': bot_message.author,
                        'avatar': '',
                        'timestamp': bot_message.timestamp.isoformat(),
                        'has_interruption': False,
                        'interruption_type': intervention_result.intervention_type.value if intervention_result else None,
                        # 标记为干预消息，前端可直接显示并在刷新后保留
                        'intervention_applied': True,
                        'room': room_str,
                        'client_id': f"bot_{bot_message.id}_{int(time.time() * 1000)}"
                    }

                    # 发送到手动房间里的所有客户端（单通道）
                    clients = get_room_clients(room_str)
                    if clients:
                        manual_emit_to_room('message', bot_payload, room_str)
                        print(f"🤖 [后台干预] 机器人消息已发送到房间 {room_str}（手动房间广播）")
                    else:
                        # 无客户端时，兜底使用房间广播一次
                        try:
                            socketio.emit('message', bot_payload, room=room_str)
                            print(f"🤖 [后台干预] 机器人消息兜底发送到房间 {room_str}（room广播）")
                        except Exception as _:
                            pass

                    # 同步发送干预事件（管理员/普通用户）
                    payload = {
                        'type': 'intervention',
                        'message': intervention_result.message,
                        'strategy': intervention_result.intervention_type.value,
                        'timestamp': get_local_time().isoformat()
                    }
                    admin_payload = dict(payload)
                    if intervention_result.reason:
                        admin_payload['reason'] = intervention_result.reason
                        admin_payload['is_admin_info'] = True
                    manual_emit_to_room('intervention', payload, room_str)
                    manual_emit_to_room('intervention_admin', admin_payload, room_str)

                    # 提醒前端回补历史，防止偶发漏收
                    try:
                        socketio.emit('refresh_messages', {
                            'room_id': room_str,
                            'reason': 'chatbot_message_sync'
                        }, room=room_str)
                    except Exception as _:
                        pass

        except Exception as e:
            print(f"❌ [后台干预] 任务错误: {e}")

    socketio.start_background_task(_process_intervention_background, str(room), int(user.id), (user.display_name or user.username), user.gender, int(message.id))
    print(f"🚀 [后台干预] 任务已启动 (房间{room}, 消息{message.id})")

    print(f'=== send_message事件处理完成 ===')
    return




# @socketio.on('chat_message')
# async def handle_chat_message(data):
#     print(f'=== 开始处理chat_message事件 ===')
#     print(f'收到WebSocket消息: {data}')
#     print(f'数据类型: {type(data)}')
#     print(f'数据内容: {json.dumps(data, default=str) if data else "None"}')
    
#     room = data.get('room')
#     message_data = data.get('message')
    
#     print(f'房间: {room}, 消息数据: {message_data}')
    
#     if not room or not message_data:
#         print('房间或消息数据为空，退出处理')
#         return
    
#     print(f'=== 数据验证通过，继续处理 ===')
    
#     # 获取用户信息
#     user_id = session.get('user_id')
#     print(f'从session获取的用户ID: {user_id}')
    
#     if not user_id and current_user.is_authenticated:
#         user_id = current_user.id
#         print(f'从current_user获取的用户ID: {user_id}')
    
#     print(f'最终用户ID: {user_id}')
    
#     # 如果没有用户ID（测试页面），使用默认用户
#     if not user_id:
#         print('无法获取用户ID，使用默认用户')
#         user = User.query.first()  # 获取第一个用户作为默认用户
#         if not user:
#             # 如果没有用户，创建一个默认用户
#             user = User(
#                 username='test_user',
#                 email='test@example.com',
#                 password_hash='test',
#                 display_name='测试用户',
#                 gender='unknown'
#             )
#             db.session.add(user)
#             db.session.commit()
#             print(f'创建默认用户: {user.username}')
#         else:
#             print(f'使用现有用户: {user.username}')
#     else:
#         user = User.query.get(user_id)
#         if not user:
#             print('用户不存在')
#             return
    
#     print(f'用户信息: {user.username}')
    
#     # 创建消息记录
#     message = Message(
#         content=message_data['content'],
#         author=user.display_name or user.username,
#         gender=user.gender,
#         room_id=int(room),
#         user_id=user.id
#     )
    
#     print(f'创建消息: {message.content}')
    
#     db.session.add(message)
#     db.session.commit()
    
#     print(f'消息已保存到数据库，ID: {message.id}')
    
#     # 构建消息数据
#     message_info = {
#         'id': message.id,
#         'content': message.content,
#         'author': message.author,
#         'avatar': user.avatar,  # 添加用户头像
#         'timestamp': message.timestamp.isoformat(),
#         'has_interruption': message.has_interruption,
#         'interruption_type': message.interruption_type,
#         'intervention_applied': message.intervention_applied,
#         'client_id': message_data.get('client_id'),
#         'room': room
#     }
    
#     print(f'准备广播消息: {message_info}')
#     print(f'广播到房间: {room}')
    
#     # 确保room是字符串类型
#     room = str(room)
    
#     # 获取房间内当前连接的客户端数量
#     from flask_socketio import rooms
#     room_clients = rooms(room)
#     print(f'房间 {room} 内当前连接的客户端: {room_clients}')
#     print(f'当前客户端ID: {request.sid}')
    
#     # 使用更可靠的广播方法
#     try:
#         # 方法1：使用socketio.emit到房间
#         socketio.emit('message', message_info, room=room)
#         print(f'消息已广播到房间 {room}')
        
#         # 方法2：如果房间为空，广播给所有连接的客户端（备用方案）
#         if not room_clients:
#             print(f'房间 {room} 为空，广播给所有客户端')
#             socketio.emit('message', message_info)
#             print(f'消息已广播给所有客户端')
            
#     except Exception as e:
#         print(f'广播消息时出错: {e}')
#         # 备用方案：广播给所有客户端
#         socketio.emit('message', message_info)
#         print(f'使用备用方案广播消息')
    
#     print(f'=== chat_message事件处理完成 ===')


#   2025.08.27 新增 完整替换上方接口：handle_chat_message

@socketio.on('chat_message')
async def handle_chat_message(data):
    print(f'=== 开始处理chat_message事件 ===')
    print(f'收到WebSocket消息: {data}')
    print(f'数据类型: {type(data)}')
    print(f'数据内容: {json.dumps(data, default=str) if data else "None"}')
    
    room = data.get('room')
    message_data = data.get('message')
    
    print(f'房间: {room}, 消息数据: {message_data}')
    
    if not room or not message_data:
        print('房间或消息数据为空，退出处理')
        return
    
    # 获取用户信息
    user_id = session.get('user_id')
    if not user_id and current_user.is_authenticated:
        user_id = current_user.id
    if not user_id:
        user = User.query.first()
        if not user:
            user = User(
                username='test_user',
                email='test@example.com',
                password_hash='test',
                display_name='测试用户',
                gender='unknown'
            )
            db.session.add(user)
            db.session.commit()
    else:
        user = User.query.get(user_id)
        if not user:
            print('用户不存在')
            return

    print(f'用户信息: {user.username}')

    # ===2025.8.27  新增：检查用户权限和房间成员资格 ===
    # 检查用户是否有权限发送消息到此房间
    # 管理员可以向任何房间发送消息
    if not user.is_admin():
        # 非管理员用户需要检查房间成员资格
        membership = RoomMembership.query.filter_by(
            user_id=user.id, room_id=int(room)
        ).first()
        if not membership:
            print(f'用户 {user.username} 不是房间 {room} 的成员，拒绝发送消息')
            notice = {
                'id': -1,
                'content': '您不是该房间的成员，无法发送消息。',
                'author': 'System',
                'avatar': '',
                'timestamp': get_local_time().isoformat(),
                'has_interruption': False,
                'interruption_type': None,
                'intervention_applied': False,
                'room': str(room)
            }
            socketio.emit('message', notice, to=request.sid)
            return
    else:
        # 管理员如果不是房间成员，自动加入
        membership = RoomMembership.query.filter_by(
            user_id=user.id, room_id=int(room)
        ).first()
        if not membership:
            admin_membership = RoomMembership(
                user_id=user.id,
                room_id=int(room),
                role='admin',
                is_online=True
            )
            db.session.add(admin_membership)
            db.session.commit()
            print(f'管理员 {user.username} 自动加入房间 {room}')
        
    # === 移除禁言检查，取消渐进式治理 ===
    muted, remain = (False, 0)
    if False:  # 禁言功能已移除
        # 只给本人一个提示，不影响他人（发到当前连接的 socket 会话）
        notice = {
            'id': -1,
            'content': f'你已被禁言，还有 {remain} 秒后解除。',
            'author': 'Chime',
            'avatar': '',
            'timestamp': get_local_time().isoformat(),
            'has_interruption': False,
            'interruption_type': None,
            'intervention_applied': False,
            'room': str(room)
        }
        socketio.emit('message', notice, to=request.sid)
        print(f'[拦截] 用户({user.id}) 在房间({room})处于禁言中，拦截消息。')
        return

    # 保存消息
    message = Message(
        content=message_data['content'],
        author=user.display_name or user.username,
        gender=user.gender,
        room_id=int(room),
        user_id=user.id
    )
    db.session.add(message)
    db.session.commit()

    # === 新增：开关关闭则直接广播原消息并返回 ===
    if not app.config.get('INTERVENTION_ENABLED', False):
        message_info = {
            'id': message.id,
            'content': message.content,
            'author': user.display_name or user.username,
            'avatar': user.avatar,
            'timestamp': message.timestamp.isoformat(),
            'has_interruption': False,
            'interruption_type': None,
            'intervention_applied': False,
            'client_id': message_data.get('client_id'),
            'room': str(room)
        }
        socketio.emit('message', message_info, room=str(room))
        return
    # =========================================

    
    # ===== 干预分析 =====
    intervention_message = None
    intervention_reason = None
    bot_payload = None
    suppress_user_message = False          # <=== 新增

    # Debug: 追踪消息处理
    print(f"💬 [SocketIO2] 收到消息: 用户{user.id}({user.display_name}) - '{message.content[:30]}...'")

    # === 房间开关：关闭时只转发消息，不做智能干预 ===
    room_obj = Room.query.get(int(room))
    intervention_enabled = room_obj.chatbot_enabled if room_obj else False
    print(f"🔧 [SocketIO2] 房间{room}干预开关状态: {intervention_enabled}")
    if not intervention_enabled:
        message_info = {
            'id': message.id,
            'content': message.content,
            'author': user.display_name or user.username,
            'avatar': user.avatar or '',
            'timestamp': message.timestamp.isoformat(),
            'has_interruption': False,
            'interruption_type': None,
            'intervention_applied': False,
            'client_id': (message_data.get('client_id') if isinstance(message_data, dict) else None),
            'room': str(room)
        }
        manual_emit_to_room('message', message_info, str(room))
        print(f'[INFO] 房间{room}的Chatbot已关闭：仅转发消息，不做干预。已通过手动系统广播')
        return


    try:
        intervention_result = smart_intervention_engine.analyze_message(
            room_id=room,
            user_id=str(user.id),
            username=user.display_name or user.username,
            message_content=message.content,
            gender=user.gender
        )
        if intervention_result and intervention_result.should_intervene:
            message.has_interruption = True
            message.interruption_type = intervention_result.intervention_type.value
            message.intervention_applied = True

            intervention_message = intervention_result.message
            intervention_reason = intervention_result.reason

            # ====== 触发禁言 → 找到真正的目标用户并执行禁言 ======
            if getattr(intervention_result, 'action', None) == 'mute':
                seconds = getattr(intervention_result, 'mute_seconds', 300)
                target_name = getattr(intervention_result, 'target_user', None)
                mute_user_id = user.id
                mute_user_name = user.display_name or user.username

                try:
                    # 优先根据房间内最近消息定位该昵称对应的 user_id（更可靠）
                    if target_name and target_name != mute_user_name:
                        last_target_msg = Message.query.filter_by(
                            room_id=int(room), author=target_name
                        ).order_by(Message.timestamp.desc()).first()
                        if last_target_msg and last_target_msg.user_id:
                            mute_user_id = last_target_msg.user_id
                            mute_user = User.query.get(mute_user_id)
                            mute_user_name = mute_user.display_name or mute_user.username if mute_user else target_name
                        else:
                            # 回退：直接查用户表（可能存在重名风险）
                            mute_user = User.query.filter((User.display_name == target_name) | (User.username == target_name)).first()
                            if mute_user:
                                mute_user_id = mute_user.id
                                mute_user_name = mute_user.display_name or mute_user.username
                except Exception:
                    pass

                # 移除禁言功能，保留提醒消息
                intervention_message = intervention_result.message
                suppress_user_message = False  # 不再压制用户消息
            # ========================================================

            intervention_record = Intervention(
                room_id=int(room),
                message_id=message.id,
                strategy=intervention_result.intervention_type.value,
                intervention_text=intervention_result.message,
                trigger_type=intervention_result.intervention_type.value,
                trigger_reason=intervention_result.reason,
                intervention_type=intervention_result.intervention_type.value,
                offense_level=intervention_result.offense_level.value if intervention_result.offense_level else None,
                target_user=intervention_result.target_user,
                is_visible_to_admin_only=False
            )
            db.session.add(intervention_record)

            # === 新增：把“干预提示”也保存为普通消息（机器人）===
            bot_message = Message(
                content=intervention_message,
                author='Chime',
                gender='unknown',
                room_id=int(room),
                user_id=None
            )
            db.session.add(bot_message)
            db.session.commit()

            bot_payload = {
                'id': bot_message.id,
                'content': bot_message.content,
                'author': bot_message.author,
                'avatar': '',
                'timestamp': bot_message.timestamp.isoformat(),
                'has_interruption': False,
                'interruption_type': intervention_result.intervention_type.value if intervention_result else None,
                'intervention_applied': False,
                'room': room,
                'client_id': f"bot_{bot_message.id}_{int(time.time() * 1000)}"  # 确保唯一性和前端去重
            }
    except Exception as e:
        print(f'干预分析失败: {e}')
    db.session.commit()
    
    # ===== 构建消息数据 =====
    message_info = {
        'id': message.id,
        'content': message.content,
        'author': message.author,
        'avatar': user.avatar,
        'timestamp': message.timestamp.isoformat(),
        'has_interruption': message.has_interruption,
        'interruption_type': message.interruption_type,
        'intervention_applied': message.intervention_applied,
        'client_id': message_data.get('client_id'),
        'room': room
    }
    
    room = str(room)
    from flask_socketio import rooms
    room_clients = rooms(room)
    
    # ===== 广播消息 + 插话 =====
    try:
        if not suppress_user_message:
            socketio.emit('message', message_info, room=room)
        if bot_payload:
            socketio.emit('message', bot_payload, room=room)

        if not room_clients:
            if not suppress_user_message:
                socketio.emit('message', message_info)
            if bot_payload:
                socketio.emit('message', bot_payload)
    except Exception as e:
        print(f'广播消息时出错: {e}')
        if not suppress_user_message:
            socketio.emit('message', message_info)
        if bot_payload:
            socketio.emit('message', bot_payload)

    print(f'=== chat_message事件处理完成 ===')



@app.route('/test_broadcast')
def test_broadcast():
    """测试广播消息"""
    return "测试广播功能"

@app.route('/test_chat')
def test_chat():
    """测试聊天页面"""
    return render_template('test_chat_simple.html')

@app.route('/test_send_message', methods=['POST'])
def test_send_message():
    """测试消息发送端点"""
    try:
        data = request.get_json()
        room_id = data.get('room_id', 1)
        content = data.get('content', '测试消息')
        author = data.get('author', '测试用户')
        
        print(f'测试发送消息: 房间={room_id}, 内容={content}, 作者={author}')
        
        # 创建消息记录
        message = Message(
            content=content,
            author=author,
            gender='unknown',
            room_id=room_id,
            user_id=1  # 使用默认用户ID
        )
        
        db.session.add(message)
        db.session.commit()
        
        # 构建消息数据
        message_info = {
            'id': message.id,
            'content': message.content,
            'author': message.author,
            'avatar': '',
            'timestamp': message.timestamp.isoformat(),
            'has_interruption': message.has_interruption,
            'interruption_type': message.interruption_type,
            'intervention_applied': message.intervention_applied
        }
        
        # 广播消息 - 使用socketio.emit而不是emit
        room = str(room_id)
        socketio.emit('message', message_info, room=room)
        
        print(f'测试消息已广播: {message_info}')
        
        return jsonify({'success': True, 'message': message_info})
    except Exception as e:
        print(f'测试消息发送失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

# 新增：实时冲突检测API端点
@app.route('/api/admin/detection-status', methods=['GET'])
def get_detection_status():
    """获取检测系统状态"""
    try:
        # 获取GPT-4分析器统计信息
        stats = gpt4_context_analyzer.get_analysis_statistics()
        
        return jsonify({
            'status': 'active',
            'detector_type': 'gpt4_realtime_context',
            'gpt_analysis_enabled': True,
            'last_update': datetime.now().isoformat(),
            'total_analyses': stats.get('total_analyses', 0),
            'recent_interventions': stats.get('recent_interventions', 0),
            'active_contexts': stats.get('active_contexts', 0),
            'trigger_counts': stats.get('trigger_counts', {})
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/admin/intervention-style', methods=['POST'])
@admin_required
def update_intervention_style():
    """更新干预风格"""
    try:
        data = request.get_json()
        style = data.get('style', 'collaborating')
        
        # 验证风格类型
        valid_styles = ['none', 'auto', 'collaborating', 'accommodating', 'competing', 'compromising', 'avoiding']
        if style not in valid_styles:
            return jsonify({'success': False, 'error': '无效的风格类型'}), 400
        
        # 获取或创建风格设置记录
        style_setting = InterventionStyle.query.filter_by(is_active=True).first()
        if not style_setting:
            style_setting = InterventionStyle(
                style=style,
                description=f'当前设置为{style}风格',
                created_by=current_user.id if current_user.is_authenticated else None
            )
            db.session.add(style_setting)
        else:
            style_setting.style = style
            style_setting.description = f'当前设置为{style}风格'
            style_setting.updated_at = get_local_time()
        
        db.session.commit()
        
        # 同时更新app.config作为缓存
        app.config['CURRENT_INTERVENTION_STYLE'] = style
        
        # 广播风格更新
        socketio.emit('intervention_style_updated', {
            'style': style,
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info(f"干预风格已更新为: {style}")
        return jsonify({'success': True, 'style': style})
    except Exception as e:
        logger.error(f"更新干预风格失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/current-intervention-style', methods=['GET'])
def get_current_intervention_style():
    """获取当前干预风格"""
    try:
        # 首先从数据库获取
        style_setting = InterventionStyle.query.filter_by(is_active=True).first()
        if style_setting:
            style = style_setting.style
        else:
            # 如果没有数据库记录，使用默认值
            style = 'none'
            # 创建默认记录
            default_setting = InterventionStyle(
                style=style,
                description='默认无插话风格',
                is_active=True
            )
            db.session.add(default_setting)
            db.session.commit()
        
        # 更新app.config缓存
        app.config['CURRENT_INTERVENTION_STYLE'] = style
        
        return jsonify({'style': style})
    except Exception as e:
        logger.error(f"获取当前干预风格失败: {e}")
        return jsonify({'style': 'none', 'error': str(e)})

@app.route('/api/admin/conflict-detection-live', methods=['GET'])
def get_live_conflict_detection():
    """获取实时冲突检测数据"""
    try:
        stats = gpt4_context_analyzer.get_analysis_statistics()
        
        # 获取最近的干预记录
        recent_interventions = []
        for intervention in list(gpt4_context_analyzer.intervention_history)[-10:]:
            recent_interventions.append({
                'room_id': intervention.get('room_id', 'unknown'),
                'trigger_type': intervention.get('trigger_type', 'unknown'),
                'confidence': intervention.get('confidence', 0.8),
                'timestamp': intervention.get('timestamp', datetime.now()).isoformat()
            })
        
        # 添加一些模拟数据用于测试
        if stats.get('total_analyses', 0) == 0:
            # 模拟一些数据
            gpt4_context_analyzer.add_analysis()
            gpt4_context_analyzer.add_intervention('room_1', 'interruption', 0.85)
            gpt4_context_analyzer.add_intervention('room_2', 'bias_detection', 0.92)
            stats = gpt4_context_analyzer.get_analysis_statistics()
        
        return jsonify({
            'status': 'active',
            'total_analyses': stats.get('total_analyses', 0),
            'recent_interventions': stats.get('recent_interventions', 0),
            'active_contexts': stats.get('active_contexts', 0),
            'trigger_counts': stats.get('trigger_counts', {}),
            'recent_interventions_list': recent_interventions,
            'last_update': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"获取实时冲突检测数据失败: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


# —— Chatbot 房间开关：查询 —— 
@app.route('/api/admin/chatbot/enabled', methods=['GET'])
@admin_required
def get_chatbot_enabled():
    room_id = request.args.get('room_id')
    if not room_id:
        return jsonify({'error': 'room_id is required'}), 400
    
    room = Room.query.get(int(room_id))
    if not room:
        return jsonify({'error': 'Room not found'}), 404
        
    return jsonify({'enabled': bool(room.chatbot_enabled)})

# —— Chatbot 房间开关：设置 —— 
@app.route('/api/admin/chatbot/enabled', methods=['POST'])
@admin_required
def set_chatbot_enabled():
    data = request.get_json() or {}
    enabled = bool(data.get('enabled', False))
    room_id = data.get('room_id')
    
    if not room_id:
        return jsonify({'error': 'room_id is required'}), 400
    
    room = Room.query.get(int(room_id))
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    
    old_status = room.chatbot_enabled
    room.chatbot_enabled = enabled
    db.session.commit()

    # 后台日志提示
    if enabled != old_status:
        if enabled:
            print(f"🟢 [CHATBOT] 管理员已启用房间{room_id}的Chatbot - 开始智能监控和干预")
            print(f"⏰ [CHATBOT] 房间{room_id}破冰将在检测到沉默时自动触发，不会立即破冰")
        else:
            print(f"🔴 [CHATBOT] 管理员已禁用房间{room_id}的Chatbot - 停止监控和干预")
    
    print(f"🔧 [CHATBOT] 房间{room_id}开关状态更新: {old_status} → {enabled}")

    # 广播给该房间的前端
    socketio.emit('chatbot_enabled_updated', {
        'enabled': enabled,
        'room_id': room_id,
        'timestamp': datetime.now().isoformat()
    }, room=str(room_id))
    
    # 同时使用手动房间管理系统确保消息到达
    manual_emit_to_room('chatbot_enabled_updated', {
        'enabled': enabled,
        'room_id': room_id,
        'timestamp': datetime.now().isoformat()
    }, str(room_id))

    return jsonify({'success': True, 'enabled': enabled})

@app.route('/api/admin/monitor/status', methods=['GET'])
@admin_required
def get_monitor_status():
    """获取实时监控状态"""
    try:
        stats = realtime_monitor.get_monitor_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/api/admin/interventions', methods=['GET'])
@admin_required
def get_interventions():
    try:
        room_id = request.args.get('room_id')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        query = Intervention.query
        if room_id:
            query = query.filter_by(room_id=room_id)
        
        interventions = query.order_by(Intervention.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        result = []
        for intervention in interventions.items:
            # 获取关联的消息信息
            message = Message.query.get(intervention.message_id)
            
            result.append({
                'id': intervention.id,
                'room_id': intervention.room_id,
                'message_id': intervention.message_id,
                'message_content': message.content if message else '',
                'message_author': message.author if message else '',
                'intervention_text': intervention.intervention_text,
                'intervention_type': intervention.intervention_type,
                'trigger_reason': intervention.trigger_reason,
                'offense_level': intervention.offense_level,
                'target_user': intervention.target_user,
                'created_at': intervention.created_at.isoformat()
            })
        
        return jsonify({
            'interventions': result,
            'total': interventions.total,
            'pages': interventions.pages,
            'current_page': page
        })
        
    except Exception as e:
        logger.error(f"获取干预记录失败: {e}")
        return jsonify({'error': '获取失败'}), 500

@app.route('/api/admin/interventions/export', methods=['GET'])
@admin_required
def export_interventions():
    try:
        room_id = request.args.get('room_id')
        format_type = request.args.get('format', 'json')  # json, csv
        
        query = Intervention.query
        if room_id:
            query = query.filter_by(room_id=room_id)
        
        interventions = query.order_by(Intervention.created_at.desc()).all()
        
        export_data = []
        for intervention in interventions:
            message = Message.query.get(intervention.message_id)
            room = Room.query.get(intervention.room_id)
            
            export_data.append({
                'intervention_id': intervention.id,
                'room_name': room.name if room else '未知房间',
                'room_id': intervention.room_id,
                'trigger_time': intervention.created_at.isoformat(),
                'message_content': message.content if message else '',
                'message_author': message.author if message else '',
                'intervention_type': intervention.intervention_type,
                'intervention_text': intervention.intervention_text,
                'trigger_reason': intervention.trigger_reason,
                'offense_level': intervention.offense_level,
                'target_user': intervention.target_user
            })
        
        if format_type == 'csv':
            # 返回CSV格式
            import csv
            import io
            output = io.StringIO()
            
            if export_data:
                writer = csv.DictWriter(output, fieldnames=export_data[0].keys())
                writer.writeheader()
                writer.writerows(export_data)
            
            response = app.response_class(
                output.getvalue(),
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment; filename=interventions_{room_id or "all"}.csv'}
            )
            return response
        else:
            # 返回JSON格式
            return jsonify({
                'data': export_data,
                'total_count': len(export_data),
                'export_time': get_local_time().isoformat()
            })
        
    except Exception as e:
        logger.error(f"导出干预记录失败: {e}")
        return jsonify({'error': '导出失败'}), 500

@app.route('/api/admin/intervention/stats', methods=['GET'])  
@admin_required
def get_intervention_stats():
    try:
        room_id = request.args.get('room_id')
        days = int(request.args.get('days', 7))  # 默认最近7天
        
        # 计算日期范围
        end_date = get_local_time()
        start_date = end_date - timedelta(days=days)
        
        query = Intervention.query.filter(
            Intervention.created_at >= start_date,
            Intervention.created_at <= end_date
        )
        
        if room_id:
            query = query.filter_by(room_id=room_id)
        
        interventions = query.all()
        
        # 按类型统计
        type_stats = {}
        offense_stats = {}
        daily_stats = {}
        
        for intervention in interventions:
            # 按干预类型统计
            itype = intervention.intervention_type
            type_stats[itype] = type_stats.get(itype, 0) + 1
            
            # 按冒犯等级统计
            if intervention.offense_level:
                offense_stats[intervention.offense_level] = offense_stats.get(intervention.offense_level, 0) + 1
            
            # 按日期统计
            date_key = intervention.created_at.strftime('%Y-%m-%d')
            daily_stats[date_key] = daily_stats.get(date_key, 0) + 1
        
        return jsonify({
            'total_interventions': len(interventions),
            'intervention_types': type_stats,
            'offense_levels': offense_stats,
            'daily_stats': daily_stats,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': days
            }
        })
        
    except Exception as e:
        logger.error(f"获取干预统计失败: {e}")
        return jsonify({'error': '获取统计失败'}), 500
def generate_style_based_intervention(context_messages, trigger_type, style):
    """根据风格生成干预消息"""
    
    # 导入GPT风格干预生成器
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
    
    from src.interventions.gpt_style_intervention_generator import (
        GPTStyleInterventionGenerator, 
        GPTInterventionContext, 
        AdminInterventionStyle, 
        InterventionTrigger
    )
    
    # 初始化生成器
    generator = GPTStyleInterventionGenerator()
    
    # 转换触发类型
    trigger_mapping = {
        'female_interrupted': InterventionTrigger.FEMALE_INTERRUPTED,
        'female_ignored': InterventionTrigger.FEMALE_IGNORED,
        'male_dominance': InterventionTrigger.MALE_DOMINANCE,
        'male_consecutive': InterventionTrigger.MALE_CONSECUTIVE,
        'gender_imbalance': InterventionTrigger.GENDER_IMBALANCE,
        'expression_difficulty': InterventionTrigger.EXPRESSION_DIFFICULTY,
        'aggressive_context': InterventionTrigger.AGGRESSIVE_CONTEXT
    }
    
    trigger_type_enum = trigger_mapping.get(trigger_type, InterventionTrigger.GENDER_IMBALANCE)
    
    # 转换风格
    style_mapping = {
        'collaborating': AdminInterventionStyle.COLLABORATING,
        'accommodating': AdminInterventionStyle.ACCOMMODATING,
        'competing': AdminInterventionStyle.COMPETING,
        'compromising': AdminInterventionStyle.COMPROMISING,
        'avoiding': AdminInterventionStyle.AVOIDING,
        'auto': AdminInterventionStyle.AUTO
    }
    
    admin_style = style_mapping.get(style, AdminInterventionStyle.AUTO)
    
    # 分析参与者性别
    female_participants = []
    male_participants = []
    
    for msg in context_messages:
        author = msg.get('author', '')
        gender = msg.get('gender', 'unknown')
        if gender == 'female' and author not in female_participants:
            female_participants.append(author)
        elif gender == 'male' and author not in male_participants:
            male_participants.append(author)
    
    # 创建GPT干预上下文
    context = GPTInterventionContext(
        trigger_type=trigger_type_enum,
        urgency_level=4,  # 默认中等紧急程度
        confidence=0.8,   # 默认高置信度
        recent_messages=context_messages,
        female_participants=female_participants,
        male_participants=male_participants,
        admin_style=admin_style
    )
    
    # 生成干预消息
    import asyncio
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        intervention = loop.run_until_complete(generator.generate_intervention(context))
        loop.close()
        return intervention
    except Exception as e:
        # 返回备用消息
        return "让我们继续建设性的讨论。"


if __name__ == '__main__':
    # 显示Chatbot开关初始状态
    enabled = app.config.get('INTERVENTION_ENABLED', False)
    if enabled:
        print("🟢 [CHATBOT] 系统启动 - Chatbot功能已启用")
    else:
        print("🔴 [CHATBOT] 系统启动 - Chatbot功能已禁用")
    
    # 启动实时监控系统
    realtime_monitor.start_monitoring()
    print("🚀 实时监控系统已启动")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=8081)