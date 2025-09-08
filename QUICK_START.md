# 🚀 TKI智能干预聊天机器人 - 快速启动

## ⚡ 最简启动（推荐）

```bash
# 1. 进入项目目录
cd /Users/apple/Desktop/first_phase_chatroom_v1

# 2. 一键启动
./start_easy.sh
```

## 🌐 访问应用

启动成功后，在浏览器中访问：

- **主页**: http://localhost:8080
- **聊天室**: http://localhost:8080/rooms
- **管理面板**: http://localhost:8080/admin

## 👤 默认账号

**管理员账号:**
- 用户名: `admin2` 密码: `admin123`
- 用户名: `admin3` 密码: `admin123`

**普通用户:**
- 用户名: `user1` 密码: `user123` (张三)
- 用户名: `user2` 密码: `user123` (李四)
- 用户名: `user3` 密码: `user123` (王五)

## 🛑 停止应用

```bash
# 方法1：在运行终端按 Ctrl+C
# 方法2：新终端执行
pkill -f start_web.py
```

## 🔧 手动启动（如果脚本失败）

```bash
# 进入项目目录
cd /Users/apple/Desktop/first_phase_chatroom_v1

# 激活虚拟环境
source venv/bin/activate

# 设置Python路径
export PYTHONPATH="$PWD:$PWD/web_app:$PWD/src"

# 进入web_app目录并启动
cd web_app
python start_web.py
```

## 🐛 常见问题

### 端口被占用
```bash
# 查看占用8080端口的进程
lsof -i :8080

# 杀死占用进程
lsof -ti:8080 | xargs kill -9
```

### 依赖缺失
```bash
cd web_app
pip install -r requirements.txt
```

### 权限问题
```bash
# 给启动脚本执行权限
chmod +x start_easy.sh
```

---

📖 **详细文档**: 查看 `web_app/README.md` 获取完整的安装和配置说明
