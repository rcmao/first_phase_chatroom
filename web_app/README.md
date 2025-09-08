# TKI性别意识智能干预聊天机器人 - Web应用

基于Thomas-Kilmann冲突管理模型的性别结构性边缘化干预系统的Discord风格网页应用。

## 功能特性

### 核心功能
- 🎨 **Discord风格界面**: 现代化的聊天界面，类似Discord的用户体验
- 👤 **用户系统**: 完整的注册、登录、登出功能，支持用户头像
- 💬 **实时聊天**: 基于WebSocket的实时多人聊天室
- 🤖 **智能干预**: 基于TKI模型的性别意识智能干预系统
- 📊 **分析报告**: 实时对话分析和干预策略统计
- 🔒 **安全认证**: JWT令牌认证和密码加密

### 智能干预功能
- 🔇 **沉默检测**: 自动检测个人和群体沉默，适时破冰
  - **群体沉默**: 60秒无人发言时触发话题延续
  - **个人沉默**: 90秒未发言的用户会被友好邀请参与（60秒冷却）
- ⚡ **冲突中断**: 检测并缓解对话中的冲突情况
- 🎯 **话题引导**: 智能议程转换，保持对话活跃
- 🚫 **恶语检测**: 实时检测并处理不当言论
- 📈 **参与保证**: 确保所有成员都能参与对话

### 系统特性
- 🔄 **实时监控**: 后台实时监控所有聊天室状态
- ⚙️ **灵活配置**: 可调节的干预阈值和策略参数
- 📱 **响应式设计**: 支持桌面和移动设备
- 🌐 **多语言支持**: 支持中文和英文界面
- 🔧 **管理面板**: 完整的管理员控制面板

## 技术栈

### 后端
- **Flask**: Python Web框架
- **SQLAlchemy**: 数据库ORM
- **Flask-Login**: 用户认证
- **bcrypt**: 密码加密
- **PyJWT**: JWT令牌

### 前端
- **HTML5/CSS3**: 现代化界面
- **JavaScript**: 交互逻辑
- **Font Awesome**: 图标库

## ⚡ 快速启动命令

### 最简启动方式
```bash
# 进入项目目录
cd /Users/apple/Desktop/first_phase_chatroom_v1

# 一键启动（推荐）
./start_easy.sh
```

### 手动启动方式
```bash
# 进入项目目录
cd /Users/apple/Desktop/first_phase_chatroom_v1

# 激活虚拟环境
source venv/bin/activate

# 设置Python路径并启动
export PYTHONPATH="$PWD:$PWD/web_app:$PWD/src"
cd web_app
python start_web.py
```

### 停止应用
```bash
# 方法1：在运行终端按 Ctrl+C
# 方法2：新终端执行
pkill -f start_web.py
```

---

## 🚀 详细启动指南

### 🚀 一键启动（推荐）

1. **克隆项目并进入目录**
   ```bash
   cd /Users/apple/Desktop/first_phase_chatroom_v1
   ```

2. **激活虚拟环境**
   ```bash
   source venv/bin/activate
   ```

3. **设置Python路径并启动**
   ```bash
   export PYTHONPATH="$PWD:$PWD/web_app:$PWD/src"
   cd web_app
   python start_web.py
   ```

4. **访问应用**
   - 打开浏览器访问: http://localhost:8080
   - 聊天室: http://localhost:8080/rooms
   - 管理面板: http://localhost:8080/admin

### 📋 详细安装步骤

#### 1. 环境准备

确保已安装Python 3.8+：
```bash
python3 --version
```

#### 2. 虚拟环境设置

项目已包含虚拟环境，直接激活：
```bash
# 在项目根目录下
source venv/bin/activate  # Linux/Mac
# 或者使用
source .venv/bin/activate  # 备用虚拟环境

# Windows用户
# venv\Scripts\activate
```

#### 3. 安装依赖（如果需要）

```bash
# 进入web_app目录
cd web_app

# 安装Python依赖（通常已安装）
pip install -r requirements.txt
```

#### 4. 环境配置

项目已包含 `.env` 配置文件，包含以下关键配置：
```env
# Flask配置
SECRET_KEY=your-secret-key-here-change-this-in-production
FLASK_ENV=development
FLASK_DEBUG=True

# OpenAI配置
OPENAI_API_KEY=sk-XGGe5y0ZvLcQVFp6XnRizs7q47gsVnAbZx0Xr2mfcVlbr99f
OPENAI_BASE_URL=https://api2.aigcbest.top/v1

# LLM功能配置
LLM_TOXICITY_ENABLED=true
LLM_INTERVENTION_ENABLED=true
LLM_CONFIDENCE=0.3
GLOBAL_COOLDOWN=30

# 群体沉默检测配置
AGENDA_TRANSITION_THRESHOLD=60  # 群体沉默触发时间（秒）
AGENDA_TRANSITION_COOLDOWN=120  # 群体沉默干预冷却时间（秒）
SILENCE_THRESHOLD=90            # 个人沉默检测时间（秒）
```

#### 5. 启动应用

**方法一：标准启动（推荐）**
```bash
# 在项目根目录
cd /Users/apple/Desktop/first_phase_chatroom_v1
source venv/bin/activate
export PYTHONPATH="$PWD:$PWD/web_app:$PWD/src"
cd web_app
python start_web.py
```

**方法二：使用启动脚本**
```bash
# 修正启动脚本路径后使用
./start_easy.sh
```

**方法三：直接运行Flask应用**
```bash
# 在web_app目录下
python app.py
```

#### 6. 停止应用

**方法一：键盘快捷键**
- 在运行应用的终端中按 `Ctrl + C`

**方法二：查找并终止进程**
```bash
# 查找进程
lsof -i :8080

# 终止进程
pkill -f start_web.py
# 或者
lsof -ti:8080 | xargs kill -9
```

#### 7. 验证启动

启动成功后，你应该看到类似输出：
```
🟢 [CHATBOT] 系统启动 - Chatbot功能已启用
🚀 实时监控系统已启动
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:8080
 * Running on http://[::1]:8080
```

#### 8. 访问应用

- **主页**: http://localhost:8080
- **房间列表**: http://localhost:8080/rooms  
- **聊天室**: http://localhost:8080/chat/1 （房间ID）
- **管理面板**: http://localhost:8080/admin
- **用户资料**: http://localhost:8080/profile
- **数据统计**: http://localhost:8080/dashboard

#### 9. 默认用户账号

系统包含以下预设账号：

**管理员账号:**
- 用户名: `admin2` 密码: `admin123`
- 用户名: `admin3` 密码: `admin123`

**普通用户账号:**
- 用户名: `user1` 密码: `user123` (张三)
- 用户名: `user2` 密码: `user123` (李四)  
- 用户名: `user3` 密码: `user123` (王五)

## 使用说明

### 注册新用户
1. 访问应用首页
2. 点击"立即注册"
3. 填写用户名、邮箱和密码
4. 点击注册按钮

### 开始对话
1. 登录后进入主界面
2. 点击"新建对话"或选择现有对话
3. 在消息输入框中输入内容
4. 系统会自动分析并可能提供干预建议

### 查看分析
1. 在侧边栏点击"分析报告"
2. 查看对话的详细分析数据

## API接口

### 认证接口
- `POST /api/register` - 用户注册
- `POST /api/login` - 用户登录
- `GET /api/logout` - 用户登出

### 对话接口
- `GET /api/conversations` - 获取对话列表
- `POST /api/conversations` - 创建新对话
- `GET /api/conversations/<id>/messages` - 获取对话消息
- `POST /api/conversations/<id>/messages` - 发送消息

### 分析接口
- `GET /api/analysis/<id>` - 获取对话分析

## 数据库配置

### 🗃️ 数据库类型
**SQLite** - 轻量级文件型数据库，适合开发和小型应用

### 📍 数据库文件位置

**主数据库文件：**
```
/Users/apple/Desktop/first_phase_chatroom_v1/web_app/chatroom_with_intervention.db
```

**备用数据库文件：**
```
/Users/apple/Desktop/first_phase_chatroom_v1/web_app/instance/chatbot.db
/Users/apple/Desktop/first_phase_chatroom_v1/web_app/instance/chatroom.db
```

### ⚙️ 数据库配置信息

**应用配置 (app.py):**
```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chatbot.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
```

**环境变量配置 (env.example):**
```env
DATABASE_URL=sqlite:///chatbot.db
```

**ORM框架：** Flask-SQLAlchemy

### 🔧 数据库管理脚本

| 脚本文件 | 功能描述 |
|---------|---------|
| `create_db.py` | 创建数据库表结构 |
| `add_admin_users.py` | 添加管理员用户账户 |
| `add_regular_users.py` | 添加普通用户账户 |
| `migrate_room_chatbot.py` | 数据库迁移和升级 |
| `check_users.py` | 检查和查看用户账户 |

### 🛠️ 数据库操作命令

**创建数据库：**
```bash
cd web_app
python create_db.py
```

**添加用户：**
```bash
# 添加管理员
python add_admin_users.py

# 添加普通用户
python add_regular_users.py
```

**查看用户：**
```bash
python check_users.py
```

**重置数据库：**
```bash
# 删除数据库文件
rm chatroom_with_intervention.db
rm instance/chatbot.db

# 重新创建
python create_db.py
python add_admin_users.py
python add_regular_users.py
```

### 💾 数据库备份与恢复

**备份数据库：**
```bash
# 备份主数据库
cp chatroom_with_intervention.db chatroom_with_intervention_backup_$(date +%Y%m%d_%H%M%S).db

# 备份到其他位置
cp chatroom_with_intervention.db ~/Desktop/chatroom_backup.db
```

**恢复数据库：**
```bash
# 从备份恢复
cp chatroom_backup.db chatroom_with_intervention.db
```

## 数据库表结构

### 📋 主要数据表

#### User表 - 用户信息
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Integer | 用户ID (主键) |
| `username` | String(80) | 用户名 (唯一) |
| `email` | String(120) | 邮箱 (唯一) |
| `password_hash` | String(128) | 密码哈希 |
| `role` | String(20) | 角色 ('admin'/'member') |
| `is_active` | Boolean | 是否活跃 |
| `gender` | String(10) | 性别 ('male'/'female'/'unknown') |
| `avatar` | String(200) | 头像路径 |
| `display_name` | String(100) | 显示名称 |
| `bio` | Text | 个人简介 |
| `status` | String(20) | 状态 ('online'/'offline'/'busy') |
| `created_at` | DateTime | 创建时间 |
| `last_seen` | DateTime | 最后登录时间 |

#### Room表 - 聊天房间
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Integer | 房间ID (主键) |
| `name` | String(100) | 房间名称 |
| `description` | Text | 房间描述 |
| `created_by` | Integer | 创建者ID (外键) |
| `is_private` | Boolean | 是否私密 |
| `max_members` | Integer | 最大成员数 |
| `chatbot_enabled` | Boolean | 是否启用聊天机器人 |
| `created_at` | DateTime | 创建时间 |

#### Message表 - 聊天消息
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Integer | 消息ID (主键) |
| `content` | Text | 消息内容 |
| `author` | String(100) | 作者名称 |
| `gender` | String(10) | 作者性别 |
| `room_id` | Integer | 房间ID (外键) |
| `user_id` | Integer | 用户ID (外键) |
| `timestamp` | DateTime | 发送时间 |
| `has_interruption` | Boolean | 是否有干预 |
| `interruption_type` | String(50) | 干预类型 |
| `intervention_applied` | Boolean | 是否应用干预 |

#### RoomMembership表 - 房间成员关系
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Integer | 关系ID (主键) |
| `user_id` | Integer | 用户ID (外键) |
| `room_id` | Integer | 房间ID (外键) |
| `role` | String(20) | 房间角色 ('admin'/'member') |
| `joined_at` | DateTime | 加入时间 |
| `is_online` | Boolean | 是否在线 |
| `can_send_messages` | Boolean | 是否可发消息 |
| `can_edit_messages` | Boolean | 是否可编辑消息 |

#### Intervention表 - 干预记录
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Integer | 干预ID (主键) |
| `room_id` | Integer | 房间ID (外键) |
| `trigger_type` | String(50) | 触发类型 |
| `confidence` | Float | 置信度 |
| `message` | Text | 干预消息 |
| `reason` | Text | 干预原因 |
| `timestamp` | DateTime | 干预时间 |
| `success` | Boolean | 是否成功 |

#### InterventionStyle表 - 干预风格
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Integer | 风格ID (主键) |
| `style` | String(50) | 风格类型 |
| `description` | Text | 风格描述 |
| `is_active` | Boolean | 是否激活 |

### 🔗 表关系说明

- **User** ↔ **RoomMembership**: 一对多关系，一个用户可以加入多个房间
- **Room** ↔ **RoomMembership**: 一对多关系，一个房间可以有多个成员  
- **User** ↔ **Message**: 一对多关系，一个用户可以发送多条消息
- **Room** ↔ **Message**: 一对多关系，一个房间包含多条消息
- **Room** ↔ **Intervention**: 一对多关系，一个房间可以有多次干预记录

## 开发说明

### 项目结构
```
web_app/
├── app.py              # Flask主应用
├── requirements.txt    # Python依赖
├── start_web.py       # 启动脚本
├── env.example        # 环境变量示例
├── templates/         # HTML模板
│   └── index.html     # 主页面
└── README.md          # 说明文档
```

### 自定义配置

可以通过修改 `app.py` 中的配置来自定义应用：

```python
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chatbot.db'
```

### 扩展功能

可以轻松扩展以下功能：
- 用户头像上传
- 实时消息推送
- 文件分享
- 群组聊天
- 消息搜索

## 故障排除

### 常见问题

1. **依赖安装失败**
   ```bash
   # 升级pip
   pip install --upgrade pip
   
   # 重新安装依赖
   pip install -r requirements.txt
   
   # 如果仍有问题，尝试清理缓存
   pip cache purge
   pip install -r requirements.txt
   ```

2. **虚拟环境问题**
   ```bash
   # 删除现有虚拟环境
   rm -rf .venv
   
   # 重新创建虚拟环境
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r web_app/requirements.txt
   ```

3. **数据库错误**
   ```bash
   # 删除数据库文件重新创建
   rm web_app/instance/chatbot.db
   rm web_app/chatroom_with_intervention.db
   
   # 重启应用，数据库会自动重建
   ./start_easy.sh
   ```

4. **端口被占用**
   ```bash
   # 查看占用端口的进程
   lsof -i :8080
   
   # 杀死占用进程
   pkill -f start_web.py
   
   # 或者修改端口（在app.py中）
   app.run(debug=True, host='0.0.0.0', port=8081)
   ```

5. **WebSocket连接失败**
   ```bash
   # 检查防火墙设置
   # 确保8080端口没有被阻止
   
   # 尝试重启应用
   ./start_easy.sh
   ```

6. **LLM API连接失败**
   ```bash
   # 检查.env文件配置
   cat web_app/.env
   
   # 确保API密钥和基础URL正确
   # OPENAI_API_KEY=your-api-key
   # OPENAI_API_BASE=https://api2.aigcbest.top/v1
   ```

### 调试模式

启用详细日志输出：
```bash
# 设置环境变量
export FLASK_DEBUG=1
export FLASK_ENV=development

# 启动应用
./start_easy.sh
```

### 日志查看

查看应用日志：
```bash
# 实时查看日志
tail -f web_app/server_8080.log

# 查看最近的错误
grep -i error web_app/server_8080.log | tail -10
```

## 许可证

本项目基于原有TKI项目的许可证。

## 贡献

欢迎提交Issue和Pull Request来改进这个项目。 