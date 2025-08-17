# 💬 智能聊天室系统

一个基于Flask的现代化聊天室应用，提供实时消息传递和用户管理功能。

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🌟 功能特性

- 💬 **实时聊天**: 基于WebSocket的实时消息传递
- 👥 **房间管理**: 创建和管理多个聊天房间
- 👤 **用户系统**: 完整的用户注册、登录、个人资料管理
- 🎨 **现代化界面**: Discord风格的聊天界面
- 📱 **响应式设计**: 支持桌面和移动设备
- 🔒 **安全认证**: 安全的用户认证和会话管理
- 📊 **用户统计**: 聊天统计和用户活跃度分析

## 🚀 快速开始

### 环境要求
- Python 3.8+
- pip

### 安装步骤

1. **克隆仓库**
   ```bash
   git clone https://github.com/rcmao/interruptive_chatbot-2.git
   cd interruptive_chatbot-2
   ```

2. **安装依赖**
   ```bash
   cd web_app
   pip install -r requirements.txt
   ```

3. **启动应用**
   ```bash
   python start_web.py
   ```

4. **访问聊天室**
   
   打开浏览器访问：**http://localhost:8080**

### 默认用户账号

系统会自动创建以下测试账号：

- **管理员**: `admin` / `admin123`
- **测试用户**: `tester` / `test123`
- **测试用户1**: `test1_m` / `test123` (男性)
- **测试用户2**: `test2_m` / `test123` (男性)

## 📱 使用指南

### 1. 注册/登录
- 访问 http://localhost:8080
- 点击"立即注册"创建新账号，或使用默认账号登录

### 2. 进入聊天室
- 登录后点击"房间列表"查看可用房间
- 选择房间进入聊天界面

### 3. 开始聊天
- 在消息输入框中输入内容
- 按回车键发送消息
- 实时查看其他用户的消息

### 4. 房间管理
- 创建新房间
- 管理房间成员
- 查看房间统计信息

## 🛠️ 技术栈

### 后端
- **Flask**: Python Web框架
- **SQLAlchemy**: 数据库ORM
- **Flask-Login**: 用户认证
- **Flask-SocketIO**: WebSocket支持
- **SQLite**: 轻量级数据库

### 前端
- **HTML5/CSS3**: 现代化界面
- **JavaScript**: 交互逻辑
- **Socket.IO**: 实时通信
- **Font Awesome**: 图标库

## 📁 项目结构

```
web_app/
├── app.py                 # Flask主应用
├── start_web.py          # 启动脚本
├── requirements.txt      # Python依赖
├── templates/            # HTML模板
│   ├── index.html       # 首页
│   ├── chat_room.html   # 聊天界面
│   ├── rooms.html       # 房间列表
│   └── dashboard.html   # 用户仪表板
├── static/              # 静态文件
│   ├── css/            # 样式表
│   ├── js/             # JavaScript文件
│   └── avatars/        # 用户头像
└── instance/           # 数据库文件
    ├── chatbot.db      # 用户数据库
    └── chatroom.db     # 聊天记录数据库
```

## 🔧 配置说明

### 环境变量
复制 `web_app/env.example` 到 `web_app/.env` 并配置：

```env
SECRET_KEY=your-secret-key-here
```

### 端口配置
默认端口为8080，可在 `start_web.py` 中修改：

```python
socketio.run(app, debug=True, host='0.0.0.0', port=8080)
```

## 📊 功能截图

### 聊天界面
- 实时消息显示
- 用户在线状态
- 消息时间戳
- 响应式布局

### 房间管理
- 房间列表
- 创建新房间
- 房间成员管理
- 房间统计

### 用户系统
- 用户注册/登录
- 个人资料管理
- 用户权限控制
- 活跃度统计

## 🐛 故障排除

### 常见问题

1. **端口被占用**
   ```bash
   # 修改端口号
   python start_web.py
   # 或直接修改代码中的端口
   ```

2. **依赖安装失败**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **数据库错误**
   ```bash
   # 删除数据库文件重新创建
   rm web_app/instance/*.db
   python start_web.py
   ```

## 📄 许可证

本项目采用MIT许可证 - 详情请参阅 [LICENSE](LICENSE) 文件。

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个项目！

### 贡献方式
1. **报告Bug** - 在Issues中报告问题
2. **建议改进** - 在Discussions中提出改进建议
3. **提交代码** - Fork项目并提交Pull Requests
4. **改进文档** - 帮助改进文档和示例

---

⭐ 如果这个项目对您有帮助，请给我们一个星标！

**让每一次对话都成为连接和分享的空间** 💬 