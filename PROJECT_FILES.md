# 📁 项目文件说明

本文档详细说明了项目中每个文件的功能和作用。

## 🏗️ 项目结构概览

```
interruptive_chatbot/
├── src/                          # 源代码目录
│   ├── core/                     # 核心模块
│   ├── detectors/                # 检测器模块
│   ├── interventions/            # 干预模块
│   ├── models/                   # 模型目录
│   └── utils/                    # 工具目录
├── web_app/                      # Web应用
├── config/                       # 配置文件
├── examples/                     # 示例代码
├── scripts/                      # 脚本
└── docs/                         # 文档
```

## 🔧 核心模块 (src/core/)

### 主要文件

#### `tki_gender_aware_bot.py` - 核心机器人实现
- **功能**: Chime（基于TKI模型的性别意识智能干预机器人）
- **主要类**: `TKIGenderAwareBot`
- **作用**: 整合检测器和干预生成器，处理消息并决定是否需要干预
- **关键方法**: 
  - `process_message()`: 处理消息并决定干预
  - `_select_tki_strategy()`: 选择TKI策略
  - `get_detailed_analysis()`: 获取详细分析

#### `main.py` - 主入口点
- **功能**: 应用程序的主入口
- **作用**: 启动核心机器人功能

#### `unified_coordinator.py` - 统一协调器
- **功能**: 协调多个检测器和生成器
- **主要类**: `UnifiedInterruptionCoordinator`
- **作用**: 统一管理检测和干预流程，提供缓存和性能优化
- **关键特性**:
  - 多检测器协调
  - 结果缓存
  - 性能监控
  - 配置管理

#### `workflow_manager.py` - 工作流管理器
- **功能**: 管理工作流程和对话历史
- **主要类**: `WorkflowManager`
- **作用**: 管理对话流程，处理消息历史，生成干预
- **关键方法**:
  - `process_message()`: 处理消息
  - `_generate_intervention_with_gpt()`: 使用GPT生成干预

### 统一接口文件

#### `unified_detection_result.py` - 统一检测结果
- **功能**: 定义统一的检测结果数据结构
- **主要类**: `UnifiedDetectionResult`
- **作用**: 标准化不同检测器的输出格式

#### `unified_detector_interface.py` - 统一检测器接口
- **功能**: 定义检测器的统一接口
- **主要类**: `UnifiedDetector`, `DetectorManager`
- **作用**: 提供检测器的注册、管理和执行框架

#### `unified_intervention_interface.py` - 统一干预接口
- **功能**: 定义干预生成器的统一接口
- **主要类**: `UnifiedInterventionGenerator`, `InterventionManager`
- **作用**: 提供干预生成器的注册、管理和执行框架

#### `unified_intervention_generator.py` - 统一干预生成器
- **功能**: 实现统一的干预生成逻辑
- **主要类**: `GPTUnifiedInterventionGenerator`, `TemplateUnifiedInterventionGenerator`
- **作用**: 根据检测结果生成相应的干预消息

#### `unified_mapping.py` - 统一映射
- **功能**: 提供触发类型和策略的映射关系
- **主要类**: `UnifiedMapping`
- **作用**: 将不同检测器的触发类型映射到统一的TKI策略

#### `prompt_templates.py` - 提示模板
- **功能**: 管理各种TKI策略的提示模板
- **主要类**: `PromptTemplateLibrary`
- **作用**: 为不同策略提供标准化的提示模板

## 🔍 检测器模块 (src/detectors/)

### 核心检测器

#### `gender_based_interruption_detector.py` - 性别打断检测器
- **功能**: 检测性别结构性边缘化行为
- **主要类**: `GenderBasedInterruptionDetector`
- **检测类型**:
  - 结构性边缘化行为
  - 表达困难信号
  - 潜在攻击性语境
- **关键方法**:
  - `detect_interruption_triggers()`: 检测打断时机
  - `_detect_structural_marginalization()`: 检测结构性边缘化
  - `_detect_expression_difficulty()`: 检测表达困难

#### `when_to_interrupt.py` - 何时打断检测器
- **功能**: 决定何时进行干预
- **主要类**: `WhenToInterruptDetector`
- **检测类型**:
  - 性别不平衡
  - 表达困难
  - 对话主导
  - 女性被打断
- **关键方法**:
  - `analyze_message()`: 分析消息
  - `_detect_gender_imbalance()`: 检测性别不平衡

#### `enhanced_interruption_detector.py` - 增强打断检测器
- **功能**: 增强的打断检测，结合规则和GPT分析
- **主要类**: `EnhancedInterruptionDetector`, `GPTContextAnalyzer`
- **特性**:
  - 规则基础检测
  - GPT上下文分析
  - 决策融合
- **关键方法**:
  - `analyze_message()`: 分析消息
  - `_rule_based_detection()`: 规则基础检测

#### `context_optimized_detector.py` - 上下文优化检测器
- **功能**: 基于上下文的冲突检测
- **主要类**: `ContextOptimizedDetector`
- **特性**:
  - 上下文感知
  - 动态阈值调整
  - 优化性能

#### `gpt4_realtime_context_analyzer.py` - GPT4实时上下文分析器
- **功能**: 使用GPT4进行实时上下文分析
- **主要类**: `GPT4RealtimeContextAnalyzer`
- **特性**:
  - 实时分析
  - 上下文感知
  - 多维度评估
- **关键方法**:
  - `analyze_context_and_decide()`: 分析上下文并决策
  - `_call_gpt4_context_analysis()`: 调用GPT4分析

#### `optimized_monitor.py` - 优化监控器
- **功能**: 高性能的冲突监控
- **主要类**: `OptimizedConflictMonitorFixed`
- **特性**:
  - 并行信号处理
  - 轻量级检测
  - 智能触发逻辑
- **关键方法**:
  - `process_message()`: 处理消息
  - `process_signals_parallel()`: 并行处理信号

#### `realtime_detector.py` - 实时检测器
- **功能**: 超快速的冲突检测
- **主要类**: `UltraFastConflictDetector`
- **特性**:
  - 预编译正则表达式
  - 极速检测
  - 低延迟

#### `scenario_detector.py` - 场景检测器
- **功能**: 团队协作场景的冲突检测
- **主要类**: `TeamCollaborationConflictDetector`
- **特性**:
  - 场景特定检测
  - 角色感知
  - 团队动态分析

## 🧩 干预模块 (src/interventions/)

### 核心干预生成器

#### `tki_gender_aware_intervention.py` - TKI性别意识干预
- **功能**: 基于TKI模型的性别意识干预策略
- **主要类**: `TKIGenderAwareInterventionGenerator`
- **策略类型**:
  - 协作型 (Collaborating)
  - 迁就型 (Accommodating)
  - 竞争型 (Competing)
  - 妥协型 (Compromising)
  - 回避型 (Avoiding)
- **关键方法**:
  - `generate_intervention()`: 生成干预
  - `select_strategy()`: 选择策略

#### `enhanced_intervention_generator.py` - 增强干预生成器
- **功能**: 增强的干预生成，支持管理员风格选择
- **主要类**: `EnhancedInterventionGenerator`
- **特性**:
  - 多种干预风格
  - 管理员可配置
  - 上下文感知
- **关键方法**:
  - `generate_intervention()`: 生成干预
  - `_determine_style()`: 确定风格

#### `gpt_style_intervention_generator.py` - GPT风格干预生成器
- **功能**: 使用GPT生成干预消息
- **主要类**: `GPTStyleInterventionGenerator`
- **特性**:
  - GPT生成
  - 风格定制
  - 上下文理解

## 📊 模型模块 (src/models/)

#### `prompt_templates.py` - 提示模板
- **功能**: 管理各种提示模板
- **作用**: 为不同场景提供标准化的提示模板

## 🛠️ 工具模块 (src/utils/)

### 核心工具

#### `data_collector.py` - 数据收集器
- **功能**: 收集和分析对话数据
- **作用**: 为系统优化提供数据支持

#### `monitoring_dashboard.py` - 监控仪表板
- **功能**: 提供系统监控和可视化
- **作用**: 实时监控系统性能和干预效果

#### `performance_optimizer.py` - 性能优化器
- **功能**: 优化系统性能
- **作用**: 提高检测和干预的响应速度

## 🌐 Web应用 (web_app/)

### 核心文件

#### `app.py` - Flask应用主文件
- **功能**: Web应用的主要入口
- **主要特性**:
  - 用户认证和授权
  - 房间管理
  - 实时聊天
  - 干预系统集成
  - 管理面板
- **关键路由**:
  - `/`: 首页
  - `/chat/<room_id>`: 聊天房间
  - `/admin`: 管理面板
  - `/api/*`: API接口

#### `create_db.py` - 数据库创建
- **功能**: 创建和初始化数据库
- **作用**: 设置数据库表结构和初始数据

#### `start_web.py` - Web启动脚本
- **功能**: 启动Web应用
- **作用**: 配置和启动Flask应用

#### `translations.py` - 翻译文件
- **功能**: 多语言支持
- **作用**: 提供国际化功能

### 模板文件 (templates/)

#### `index.html` - 首页
- **功能**: 应用首页
- **作用**: 用户登录和注册入口

#### `chat_room.html` - 聊天房间
- **功能**: 实时聊天界面
- **特性**:
  - WebSocket实时通信
  - 干预消息显示
  - 用户状态管理

#### `dashboard.html` - 用户仪表板
- **功能**: 用户个人仪表板
- **作用**: 显示用户统计和活动

#### `admin_dashboard.html` - 管理面板
- **功能**: 管理员控制面板
- **特性**:
  - 系统监控
  - 用户管理
  - 干预风格配置

#### `rooms.html` - 房间列表
- **功能**: 显示所有聊天房间
- **作用**: 房间管理和加入

#### `profile.html` - 用户资料
- **功能**: 用户资料管理
- **作用**: 编辑个人信息

#### `register.html` - 注册页面
- **功能**: 用户注册
- **作用**: 新用户注册

#### `error.html` - 错误页面
- **功能**: 错误显示
- **作用**: 统一的错误处理

### 静态文件 (static/)

#### `avatars/` - 头像目录
- **功能**: 存储用户头像
- **作用**: 用户头像管理

## ⚙️ 配置文件 (config/)

#### `settings.yaml` - 系统设置
- **功能**: 系统配置参数
- **作用**: 控制系统的各种行为

#### `requirements.txt` - 依赖列表
- **功能**: Python包依赖
- **作用**: 安装所需的Python包

#### `logging.conf` - 日志配置
- **功能**: 日志系统配置
- **作用**: 控制日志输出格式和级别

## 📚 示例和脚本

#### `examples/` - 示例代码
- **功能**: 使用示例
- **作用**: 帮助用户理解如何使用系统

#### `scripts/` - 脚本目录
- **功能**: 各种实用脚本
- **作用**: 自动化部署和维护任务

## 📖 文档

#### `docs/` - 文档目录
- **功能**: 项目文档
- **作用**: 提供详细的使用和开发文档

## 🔄 文件依赖关系

### 核心依赖链
1. `main.py` → `tki_gender_aware_bot.py`
2. `tki_gender_aware_bot.py` → `detectors/` + `interventions/`
3. `unified_coordinator.py` → 所有检测器和生成器
4. `web_app/app.py` → 核心模块

### 数据流
1. 消息输入 → 检测器 → 统一协调器 → 干预生成器 → 输出
2. Web界面 → WebSocket → 后端处理 → 实时响应

## 🎯 系统设计原则

### 模块化设计
- 每个模块职责单一
- 接口标准化
- 易于扩展和维护

### 统一接口
- 所有检测器实现统一接口
- 所有生成器实现统一接口
- 便于系统集成

### 性能优化
- 并行处理
- 缓存机制
- 轻量级检测

### 可扩展性
- 插件式架构
- 配置驱动
- 支持新检测器和生成器

这个文件结构设计确保了系统的模块化、可维护性和可扩展性，同时提供了完整的性别意识智能干预功能。 