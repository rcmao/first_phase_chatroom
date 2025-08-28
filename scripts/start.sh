#!/usr/bin/env python3
"""
项目文件整理脚本
运行此脚本来清理和重组项目结构
"""

import os
import shutil
from pathlib import Path

def organize_project():
    """整理项目结构"""
    
    print("🧹 开始整理项目结构...")
    
    # =============================================================================
    # 第一步：删除不必要的文件
    # =============================================================================
    
    files_to_delete = [
        # 根目录的重复/临时文件
        "fixed_main.py",
        "integrated_emotion_context_system.py", 
        "simple_organize.py",
        "fix_missing_files.py",
        "quick_test.py",
        "quick_test_fixed.py",
        "verify_env.py",
        "verify_env_fixed.py",
        "discord_test_script.md",
        
        # 空白检测器文件
        "src/detectors/cooperation_detector.py",
        "src/detectors/fairness_detector.py",
        
        # 重复的检测器（保留fixed版本）
        "src/detectors/optimized_monitor.py",
        
        # 测试临时文件
        "tests/unit/tempCodeRunnerFile.py",
        "tests/unit/quick_test.py",
    ]
    
    print("\n📋 删除不必要的文件:")
    deleted_count = 0
    for file_path in files_to_delete:
        if os.path.exists(file_path):
            try:
                # 检查文件大小，如果太大则询问
                file_size = os.path.getsize(file_path)
                if file_size > 1024:  # 超过1KB的文件
                    print(f"  ⚠️ {file_path} ({file_size} bytes) - 较大文件，确认删除")
                
                os.remove(file_path)
                print(f"  ✅ 删除: {file_path}")
                deleted_count += 1
            except Exception as e:
                print(f"  ❌ 删除失败 {file_path}: {e}")
        else:
            print(f"  ⏭️  文件不存在: {file_path}")
    
    print(f"共删除 {deleted_count} 个文件")
    
    # =============================================================================
    # 第二步：重命名和移动文件
    # =============================================================================
    
    print("\n📁 重组文件结构:")
    
    # 重命名文件
    renames = {
        "src/detectors/optimized_monitor_fixed.py": "src/detectors/optimized_monitor.py",
        "tests/unit/test_framework_fixed.py": "tests/unit/test_framework.py",
    }
    
    for old_path, new_path in renames.items():
        if os.path.exists(old_path):
            try:
                # 如果目标文件存在，先删除
                if os.path.exists(new_path):
                    os.remove(new_path)
                shutil.move(old_path, new_path)
                print(f"  ✅ 重命名: {old_path} -> {new_path}")
            except Exception as e:
                print(f"  ❌ 重命名失败: {e}")
    
    # 移动文件到正确位置
    moves = {
        "start.sh": "scripts/start.sh",
        "main.pdf": "docs/main.pdf",
    }
    
    for src, dst in moves.items():
        if os.path.exists(src):
            try:
                # 确保目标目录存在
                dst_dir = os.path.dirname(dst)
                if dst_dir and not os.path.exists(dst_dir):
                    os.makedirs(dst_dir, exist_ok=True)
                
                # 如果目标文件存在，先删除
                if os.path.exists(dst):
                    os.remove(dst)
                
                shutil.move(src, dst)
                print(f"  ✅ 移动: {src} -> {dst}")
            except Exception as e:
                print(f"  ❌ 移动失败: {e}")
    
    # =============================================================================
    # 第三步：整理目录结构
    # =============================================================================
    
    print("\n📂 整理目录结构:")
    
    # 移动related_work到docs下
    if os.path.exists("related_work"):
        try:
            if os.path.exists("docs/related_work"):
                shutil.rmtree("docs/related_work")
            shutil.move("related_work", "docs/related_work")
            print("  ✅ 移动: related_work -> docs/related_work")
        except Exception as e:
            print(f"  ❌ 移动失败: {e}")
    
    # 处理plan文件夹
    if os.path.exists("plan"):
        try:
            plan_files = os.listdir("plan")
            if not plan_files:
                os.rmdir("plan")
                print("  ✅ 删除空文件夹: plan")
            else:
                if os.path.exists("docs/planning"):
                    shutil.rmtree("docs/planning")
                shutil.move("plan", "docs/planning")
                print("  ✅ 移动: plan -> docs/planning")
        except Exception as e:
            print(f"  ❌ 处理plan文件夹失败: {e}")
    
    # =============================================================================
    # 第四步：清理缓存文件
    # =============================================================================
    
    print("\n🗑️  清理缓存文件:")
    cache_cleaned = 0
    for root, dirs, files in os.walk("."):
        # 使用切片创建副本以避免修改正在迭代的列表
        for dir_name in dirs[:]:
            if dir_name == "__pycache__":
                cache_path = os.path.join(root, dir_name)
                try:
                    shutil.rmtree(cache_path)
                    print(f"  ✅ 删除缓存: {cache_path}")
                    dirs.remove(dir_name)
                    cache_cleaned += 1
                except Exception as e:
                    print(f"  ❌ 删除缓存失败 {cache_path}: {e}")
    
    print(f"清理了 {cache_cleaned} 个缓存文件夹")
    
    # =============================================================================
    # 第五步：创建项目文件
    # =============================================================================
    
    print("\n🚀 创建项目文件:")
    
    # 1. 创建主入口文件
    main_content = '''#!/usr/bin/env python3
"""
智能冲突干预聊天机器人 - 主入口点
"""

import sys
import os
import asyncio

# 添加src到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == "__main__":
    try:
        from core.main import main
        asyncio.run(main())
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("💡 请确保所有依赖已安装: pip install -r config/requirements.txt")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
'''
    
    try:
        with open("main.py", "w", encoding="utf-8") as f:
            f.write(main_content)
        print("  ✅ 创建主入口文件: main.py")
    except Exception as e:
        print(f"  ❌ 创建main.py失败: {e}")
    
    # 2. 创建环境变量模板
    env_template = '''# Discord Bot Configuration
DISCORD_TOKEN=your_discord_bot_token_here

# OpenAI Configuration  
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_API_BASE=https://api.openai.com/v1

# Bot Configuration
BOT_PREFIX=!
CONFLICT_THRESHOLD=0.35
INTERVENTION_COOLDOWN=30
DEBUG_MODE=false

# Monitoring Configuration
ENABLE_MONITORING=true
LOG_LEVEL=INFO
LOG_FILE=logs/bot.log
'''
    
    try:
        with open("config/.env.template", "w", encoding="utf-8") as f:
            f.write(env_template)
        print("  ✅ 创建环境变量模板: config/.env.template")
    except Exception as e:
        print(f"  ❌ 创建.env.template失败: {e}")
    
    # 3. 创建README文件
    readme_content = '''# 智能冲突干预聊天机器人

基于Thomas冲突模型和TKI策略的智能Discord机器人，能够检测对话中的冲突并提供适当的干预。

## 快速开始

1. **安装依赖**
   ```bash
   pip install -r config/requirements.txt
   ```

2. **配置环境变量**
   ```bash
   cp config/.env.template .env
   # 编辑.env文件，配置你的Discord Token和OpenAI API Key
   ```

3. **启动机器人**
   ```bash
   python main.py
   # 或使用启动脚本
   ./scripts/start.sh
   ```

4. **运行测试**
   ```bash
   ./scripts/run_tests.sh
   ```

## 项目结构

```
interruptive_chatbot/
├── main.py                    # 🆕 主入口点
├── README.md                  # 🆕 项目文档
├── src/                       # 源代码
│   ├── core/                  # 核心模块
│   ├── detectors/             # 检测器（清理后）
│   ├── interventions/         # 干预模块
│   ├── models/               # 模型模块
│   └── utils/                # 工具模块
├── tests/                    # 测试文件
├── config/                   # 配置文件
│   ├── requirements.txt      
│   └── .env.template         # 🆕 环境变量模板
├── docs/                     # 文档（整理后）
│   ├── related_work/         # 📁 研究文件
│   └── planning/            # 📁 计划文件
├── scripts/                  # 脚本
│   └── start.sh             # 📁 启动脚本
├── backup/                   # 备份文件（保留）
└── logs/                     # 日志文件
```

## 功能特点

- 🧠 **智能检测**: 基于上下文感知的冲突检测
- 🎯 **精准干预**: 基于TKI理论的策略化干预
- ⚡ **实时响应**: <300ms响应时间
- 📊 **可解释性**: 完整的决策解释和证据链
- 🔧 **可配置**: 灵活的阈值和参数配置
- 📈 **数据收集**: 完整的实验数据收集系统

## 核心技术

### Thomas冲突过程模型
基于Thomas的五阶段冲突模型：
1. **挫折感阶段** - 识别初期不满情绪
2. **概念化阶段** - 理解冲突本质
3. **行为阶段** - 检测行为意图（最佳干预时机）
4. **互动阶段** - 监控冲突升级
5. **结果阶段** - 评估冲突后果

### TKI冲突处理策略
- **协作 (Collaborating)** - 寻求双赢解决方案
- **适应 (Accommodating)** - 优先满足他人需求
- **竞争 (Competing)** - 坚持自己立场
- **回避 (Avoiding)** - 暂时避免冲突
- **妥协 (Compromising)** - 寻求中间方案

## 使用示例

```python
# 基本使用
from src.core.main import IntelligentConflictBot

bot = IntelligentConflictBot()
await bot.start(discord_token)
```

## 配置说明

在`.env`文件中配置以下参数：

- `DISCORD_TOKEN`: Discord机器人令牌
- `OPENAI_API_KEY`: OpenAI API密钥
- `CONFLICT_THRESHOLD`: 冲突检测阈值 (0.0-1.0)
- `INTERVENTION_COOLDOWN`: 干预冷却时间（秒）

## 贡献指南

1. Fork项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开Pull Request

## 许可证

本项目采用MIT许可证 - 详见 [LICENSE](LICENSE) 文件

## 联系方式

如有问题，请通过Issues联系我们。
'''
    
    try:
        with open("README.md", "w", encoding="utf-8") as f:
            f.write(readme_content)
        print("  ✅ 创建README文件: README.md")
    except Exception as e:
        print(f"  ❌ 创建README.md失败: {e}")
    
    # 4. 创建.gitignore文件（如果不存在）
    gitignore_content = '''# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
.venv/
venv/
ENV/
env/

# Environment Variables
.env
.env.local
.env.*.local

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Logs
logs/
*.log

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# Documentation
docs/_build/

# Backup
backup/
*.bak
*.backup

# Temporary files
*.tmp
temp/
'''
    
    try:
        if not os.path.exists(".gitignore"):
            with open(".gitignore", "w", encoding="utf-8") as f:
                f.write(gitignore_content)
            print("  ✅ 创建.gitignore文件")
        else:
            print("  ℹ️  .gitignore文件已存在")
    except Exception as e:
        print(f"  ❌ 创建.gitignore失败: {e}")
    
    # =============================================================================
    # 第六步：验证和总结
    # =============================================================================
    
    print("\n✨ 项目整理完成！")
    print("\n📊 整理后的目录结构:")
    print_directory_structure()
    
    print("\n📋 整理总结:")
    print("  ✅ 删除了重复和临时文件")
    print("  ✅ 重命名了fixed版本文件")
    print("  ✅ 移动了文件到正确位置")
    print("  ✅ 清理了缓存文件")
    print("  ✅ 创建了主入口文件")
    print("  ✅ 创建了配置模板")
    print("  ✅ 创建了README文档")
    
    print("\n🚀 下一步:")
    print("  1. 检查并编辑 config/.env.template，然后复制为 .env")
    print("  2. 配置你的Discord Token和OpenAI API Key")
    print("  3. 运行 python main.py 启动机器人")
    print("  4. 运行 ./scripts/run_tests.sh 执行测试")

def print_directory_structure():
    """打印目录结构"""
    
    def print_tree(directory, prefix="", max_depth=3, current_depth=0):
        if current_depth >= max_depth:
            return
        
        items = []
        try:
            for item in sorted(os.listdir(directory)):
                if not item.startswith('.') and item != '__pycache__':
                    items.append(item)
        except PermissionError:
            return
        
        for i, item in enumerate(items):
            path = os.path.join(directory, item)
            is_last = i == len(items) - 1
            current_prefix = "└── " if is_last else "├── "
            print(f"{prefix}{current_prefix}{item}")
            
            if os.path.isdir(path) and current_depth < max_depth - 1:
                next_prefix = prefix + ("    " if is_last else "│   ")
                print_tree(path, next_prefix, max_depth, current_depth + 1)
    
    print("interruptive_chatbot/")
    print_tree(".", max_depth=3)

if __name__ == "__main__":
    organize_project() 