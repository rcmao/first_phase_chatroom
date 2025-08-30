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

## 快速开始

### 1. 环境准备

确保已安装Python 3.8+：
```bash
python3 --version
```

### 2. 虚拟环境设置

创建并激活虚拟环境：
```bash
# 在项目根目录下
python3 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate     # Windows
```

### 3. 安装依赖

```bash
# 进入web_app目录
cd web_app

# 安装Python依赖
pip install -r requirements.txt
```

### 4. 配置环境变量

复制环境变量示例文件：
```bash
cp env.example .env
```

编辑 `.env` 文件，设置必要的配置：
```env
SECRET_KEY=your-secret-key-here
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_API_BASE=https://api2.aigcbest.top/v1
```

### 5. 启动应用

#### 方法一：使用快速启动脚本（推荐）
```bash
# 在项目根目录下
./start_easy.sh
```

#### 方法二：使用启动脚本
```bash
# 在web_app目录下
python start_web.py
```

#### 方法三：直接启动
```bash
# 在web_app目录下
python app.py
```

### 6. 访问应用

启动成功后，打开浏览器访问：
- **主应用**: http://localhost:8080
- **聊天室**: http://localhost:8080/rooms
- **管理面板**: http://localhost:8080/admin

### 7. 初始化数据

首次启动时，系统会自动：
- 创建数据库表
- 添加默认用户和房间
- 启动实时监控系统

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

## 数据库结构

### User表
- `id`: 用户ID
- `username`: 用户名
- `email`: 邮箱
- `password_hash`: 密码哈希
- `created_at`: 创建时间

### Conversation表
- `id`: 对话ID
- `user_id`: 用户ID
- `title`: 对话标题
- `created_at`: 创建时间

### Message表
- `id`: 消息ID
- `conversation_id`: 对话ID
- `content`: 消息内容
- `author`: 作者
- `gender`: 性别
- `timestamp`: 时间戳
- `intervention`: 干预内容
- `strategy`: 策略类型

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