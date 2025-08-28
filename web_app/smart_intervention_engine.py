import re
import os
import random
import time
import json
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum


class InterventionType(Enum):
    SILENCE_INVITATION = "silence_invitation"
    CONFLICT_INTERRUPTION = "conflict_interruption"
    STRUCTURE_GUIDANCE = "structure_guidance"
    SAFETY_WARNING = "safety_warning"
    AGENDA_TRANSITION = "agenda_transition"


class OffenseLevel(Enum):
    MILD = 1
    MODERATE = 2
    SEVERE = 3


@dataclass
class InterventionResult:
    should_intervene: bool
    intervention_type: InterventionType
    message: str
    reason: str
    offense_level: Optional[OffenseLevel] = None
    target_user: Optional[str] = None

    # 2025.8.27 新增：用于渐进式治理
    stage: Optional[int] = None            # 1=提醒, 2=警告, 3=禁言
    action: Optional[str] = None           # 'mute' 表示禁言动作
    mute_seconds: Optional[int] = None     # 禁言时长（秒）
    # === LLM 与可观测性 ===
    via_llm: bool = False
    llm_confidence: Optional[float] = None
    llm_label: Optional[str] = None


class SmartInterventionEngine:
    
    # def __init__(self):
    #     self.user_last_message_time = {}
    #     self.user_message_count = defaultdict(int)
    #     self.user_silence_warnings = defaultdict(int)
    #     self.user_offense_count = defaultdict(int)
        
    #     self.room_recent_messages = defaultdict(lambda: deque(maxlen=20))
    #     self.room_conflict_level = defaultdict(int)
    #     self.room_topic_keywords = defaultdict(set)
        
    #     self.silence_threshold = 180
    #     self.conflict_threshold = 3 

        
    #     self.offense_keywords = {
    #         OffenseLevel.MILD: [
    #             '烂梗', '外号', '梗', '标签'
    #         ],
    #         OffenseLevel.MODERATE: [
    #             '拉踩', '狂妄自大', '单场论', '最讨厌', '恶心', '滚'
    #         ],
    #         OffenseLevel.SEVERE: [
    #             '娜娜', '小丑', '废物', '闭嘴', '没资格', '不懂球', 
    #             '垃圾', '脑残', '智障', '滚蛋', '去死'
    #         ]
    #     }
        
    #     self.invitation_templates = [
    #         "@{user}，你怎么看？",
    #         "@{user}，你有什么想法吗？", 
    #         "@{user}，想听听你的观点",
    #         "大家都说说看，@{user} 你觉得呢？"
    #     ]
        
    #     self.conflict_templates = {
    #         OffenseLevel.MILD: [
    #             "提示：请尽量用客观表达，避免使用梗或标签化词汇。",
    #             "建议大家保持理性讨论。"
    #         ],
    #         OffenseLevel.MODERATE: [
    #             "该说法可能冒犯他人，请尝试换一种表达。",
    #             "讨论有点激烈了，大家冷静一下吧。"
    #         ],
    #         OffenseLevel.SEVERE: [
    #             "讨论变得激烈，请大家冷静一下。",
    #             "请保持基本的尊重，避免人身攻击。",
    #             "暂停一下，让大家都冷静冷静。"
    #         ]
    #     }
        
    #     self.guidance_templates = [
    #         "刚才大家主要提到了{topics}，我们是否可以继续深入讨论？",
    #         "建议大家先都说一遍自己的观点，再进入讨论。",
    #         "让我们回到主题，继续聊聊{topic}吧。"
    #     ]

    #     # 渐进式治理：按房间+用户计数
    #     self.user_violation_count = defaultdict(int)  # key: f"{room_id}_{user_id}"
    #     self.user_mute_until = {}                     # key: f"{room_id}_{user_id}" -> timestamp

    #     # 阈值/时长可自行调整
    #     self.warn_stage_threshold = 2   # 第2次触发 = 严肃警告
    #     self.mute_stage_threshold = 3   # 第3次触发 = 禁言
    #     self.default_mute_seconds = 300 # 默认禁言 5 分钟

    def __init__(self):
        # 用户行为追踪
        self.user_last_message_time = {}
        self.user_message_count = defaultdict(int)
        self.user_silence_warnings = defaultdict(int)
        self.user_offense_count = defaultdict(int)
        self.user_last_reminder_time = {}  # 用户最后被提醒的时间 - 防止重复提醒

        # 房间上下文缓存
        self.room_recent_messages = defaultdict(lambda: deque(maxlen=20))
        self.room_conflict_level = defaultdict(int)
        self.room_topic_keywords = defaultdict(set)
        self.room_last_intervention_ts = defaultdict(float)  # 房间最后干预时间
        self.room_last_agenda_transition = defaultdict(float)  # 房间最后议程转换时间

        # 行为检测参数 - 个人沉默阈值45秒，与实验要求一致
        self.silence_threshold = 45   # 个人沉默多久触发（秒）
        self.conflict_threshold = 3    # 连续冲突消息的阈值

        # 冒犯词库 - 提高检测标准，减少误判
        self.offense_keywords = {
            OffenseLevel.MILD: [
                '烂梗', '黑称', '水货', '笑死', '尬黑', '装逼'
            ],
            OffenseLevel.MODERATE: [
                '拉踩', '拉胯', '狂妄自大', '单场论', '最讨厌', '恶心', '滚', '讨厌死了', '真的烦', 
                '巴狗', '皇马狗', '利物浦狗', '切尔西狗', '曼联狗', '阿森纳狗', '热刺狗',
                '巴萨狗', '拜仁狗', '尤文狗', '米兰狗', '国米狗', '多特狗', '马竞狗',
                '软脚虾', '菜鸡', '菜狗', '废柴', '药厂', '温格滚', '瓜秃',
                '内马滚', '姆巴佩滚', '哈兰德滚', '梅西滚', 'C罗滚',
                '皇屑', '狗马', '渣团', '不止一家俱乐部'
            ],
            OffenseLevel.SEVERE: [
                '娜娜', '小丑', '废物', '闭嘴', '没资格', '不懂球',
                '垃圾', '脑残', '智障', '滚蛋', '去死', '傻逼', '妈的', '操',
                '死妈', '你妈', '草泥马', '日你', '煞笔', '智商有问题', '脑子有病',
                '滚出足球圈', '没脑子', '弱智', '傻逼玩意', '臭傻逼'
            ]
        }

        # 干预模板
        self.invitation_templates = [
            "@{user}，你怎么看？",
            "@{user}，你有什么想法吗？",
            "@{user}，想听听你的观点",
            "大家都说说看，@{user} 你觉得呢？"
        ]

        # 拟人化（温柔、轻松）风格模板，可根据上下文填充 {topic}
        # 通过环境变量 INTERVENTION_TONE=warm 开启
        self.tone = os.getenv('INTERVENTION_TONE', 'warm').lower()
        self.invitation_templates_warm = [
            "@{user}，你觉得呢？",
            "@{user}，也来聊聊吧～",
            "@{user}，你有什么想法？",
            "@{user}，想听听你的看法～",
            "@{user}，期待你的见解！"
        ]

        self.conflict_templates = {
            OffenseLevel.MILD: [
                "请注意用词，保持讨论友好。",
                "建议大家理性讨论，避免情绪化表达。"
            ],
            OffenseLevel.MODERATE: [
                "请注意用词，保持讨论友好。",
                "讨论变得有点激烈，让我们冷静一下吧。"
            ],
            OffenseLevel.SEVERE: [
                "请保持基本的尊重，继续友好讨论。",
                "让我们回到正题，继续理性交流。"
            ]
        }

        self.guidance_templates = [
            "刚才大家主要提到了{topics}，我们是否可以继续深入讨论？",
            "建议大家先都说一遍自己的观点，再进入讨论。",
            "让我们回到主题，继续聊聊{topic}吧。"
        ]

        # 话题转换模板
        self.agenda_transition_templates = [
            "大家聊聊新的话题吧～刚才关于{current_topic}的讨论很精彩！",
            "现在来说说{next_topic}怎么样？",
            "刚才讨论得很热烈，我们聊聊{next_topic}吧！",
            "换个角度，大家对{next_topic}有什么看法？",
            "既然刚才聊了{current_topic}，那{next_topic}你们怎么看？"
        ]

        # 主题守护：足球相关关键词（中英混合，均转为小写对比）
        self.football_keywords = [
            # 中文通用词
            '足球', '球赛', '进球', '射门', '助攻', '联赛', '杯赛', '欧冠', '世俱杯', '世界杯', '点球', '越位', '红牌', '黄牌', '教练', '替补',
            '战术', '阵型', '传球', '移动', '速度', '进攻', '机会', '风格', '哲学', '青训', '俱乐部', '冠军', '统治力', '比赛',
            # 中文球队/绰号
            '皇马', '皇家马德里', '巴萨', '巴塞罗那', '切尔西', '蓝军', '利物浦', '阿森纳', '曼联', '曼城', '热刺', '巴黎', '大巴黎', '巴黎圣日耳曼',
            '拜仁', '多特', '国际米兰', '国米', 'ac米兰', '米兰', '尤文', '那不勒斯', '纽卡', '阿贾克斯', '本菲卡', '马竞', '拉玛西亚',
            '英超', '西甲', '意甲', '德甲', '法甲', 'tiki taka', 'tikitaka', '宇宙队', '梦之队', '西蒙尼', '克洛普',
            # English general words/competitions
            'football', 'soccer', 'goal', 'assist', 'premier league', 'la liga', 'laliga', 'serie a', 'bundesliga', 'ligue 1', 'uefa', 'ucl',
            # English clubs
            'chelsea', 'real madrid', 'barcelona', 'psg', 'paris saint-germain', 'man united', 'manchester united', 'man city', 'manchester city',
            'arsenal', 'liverpool', 'tottenham', 'bayern', 'dortmund', 'inter', 'juventus', 'napoli', 'ajax', 'benfica'
        ]

        # 满足"仍在聊足球"判定的最小占比（最近窗口内至少该比例包含足球关键词）
        self.football_on_topic_ratio = float(os.getenv('FOOTBALL_ON_TOPIC_RATIO', '0.3'))  # 0.3阈值，使用GPT智能检测

        # === 议程过渡参数 ===
        self.agenda_transition_threshold = 45  # 群体沉默多久触发议程过渡（45秒，符合实验要求）
        self.room_last_agenda_transition = {}  # 房间最后一次议程过渡时间
        self.agenda_transition_cooldown = 120   # 议程过渡冷却时间（2分钟） [[memory:7476173]]

        # === 全局冷却与活跃讨论保护 ===
        self.global_cooldown_seconds = int(os.getenv('GLOBAL_COOLDOWN', '30'))  # 降低到30秒
        self.room_last_intervention_ts = {}
        self.active_discussion_window_seconds = 120
        self.active_discussion_min_unique_users = 2
        self.active_discussion_min_msg_per_minute = 1.5
        
        # 消息去重：避免90秒内重复同样的话术
        self.recent_intervention_messages = defaultdict(lambda: deque(maxlen=10))  # 每房间最近的干预消息记录
        self.message_dedup_window_seconds = 90
        
        # 议程过渡模板（根据上下文生成话题引导）
        self.agenda_transition_templates = [
            "这个话题差不多了，我们聊聊{next_topic}怎么样？",
            "刚才关于{current_topic}的讨论很精彩，现在来说说{next_topic}吧。",
            "让我们换个角度，{next_topic}大家怎么看？",
            "顺着刚才的话题，{next_topic}也值得探讨一下。"
        ]
        
        # 破冰主题（可通过环境变量配置），默认采用用户给定主题
        self.icebreaker_theme = os.getenv(
            'ICEBREAKER_THEME',
            '今天的讨论题目是——哪个球队是全世界最好的球队？他们有最伟大的足球哲学吗？'
        ).strip()
        
        # 预设的足球相关话题库（用于议程过渡）
        self.football_agenda_topics = [
            "新援表现", "转会传闻", "战术分析", "历史对战", "球员状态",
            "教练策略", "联赛排名", "欧战前景", "青训发展", "俱乐部文化",
            "经典比赛", "球迷文化", "未来展望", "赛季总结", "伤病情况"
        ]

        # === 渐进式治理参数 ===
        self.user_violation_count = defaultdict(int)   # 按房间+用户累计违规
        self.user_mute_until = {}                      # key: f"{room_id}_{user_id}" -> ts

        self.warn_stage_threshold = 2     # 第2次触发 = 警告
        self.mute_stage_threshold = 3     # 第3次触发 = 禁言
        self.default_mute_seconds = 300   # 默认禁言 5 分钟

        self.violation_window_seconds = 15 * 60  # 违规计数时间窗，默认 15 分钟
        self.user_last_violation_ts = {}         # 记录用户最后一次违规时间

        # === LLM 配置（用于Toxicity识别与文案生成）===
        # 如果有API密钥，自动启用LLM功能
        has_api_key = bool(os.getenv('OPENAI_API_KEY', '').strip())
        self.llm_toxicity_enabled = has_api_key and os.getenv('LLM_TOXICITY_ENABLED', 'true').lower() == 'true'
        self.llm_intervention_enabled = has_api_key and os.getenv('LLM_INTERVENTION_ENABLED', 'true').lower() == 'true'
        self.llm_api_key = os.getenv('OPENAI_API_KEY', '')
        # 兼容两种环境变量名：OPENAI_BASE_URL 和 OPENAI_API_BASE
        self.llm_base_url = os.getenv('OPENAI_BASE_URL') or os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1')
        self.llm_model = os.getenv('LLM_TOXICITY_MODEL', 'gpt-4o-mini')
        self.llm_message_model = os.getenv('LLM_MESSAGE_MODEL', self.llm_model)
        self.llm_timeout = float(os.getenv('LLM_TIMEOUT_SEC', '5.0'))  # 进一步增加超时时间
        self.llm_conf_threshold = float(os.getenv('LLM_CONFIDENCE', '0.5'))  # 降低阈值增加敏感性
        self.llm_result_cache = {}
        self.llm_cache_ttl = 120
        
        # GPT话题检测缓存
        self.topic_detection_cache = {}
        self.topic_cache_ttl = 60  # 话题检测缓存60秒
        
        # LLM连接状态监控
        self.llm_connection_status = {'toxicity': False, 'intervention': False}
        self._test_llm_connection_on_start()

    def _is_duplicate_message(self, room_id: str, message: str) -> bool:
        """检查是否是重复的干预消息（90秒内）"""
        now = time.time()
        recent_messages = self.recent_intervention_messages[room_id]
        
        # 清理过期的消息记录
        while recent_messages and now - recent_messages[0][0] > self.message_dedup_window_seconds:
            recent_messages.popleft()
        
        # 检查是否有相同或相似的消息
        for timestamp, recorded_msg in recent_messages:
            if message == recorded_msg:
                return True
            # 简单的相似度检查：如果前15个字符相同，认为是重复
            if len(message) > 15 and len(recorded_msg) > 15:
                if message[:15] == recorded_msg[:15]:
                    return True
        
        return False
    
    def _record_intervention_message(self, room_id: str, message: str):
        """记录干预消息，用于去重"""
        now = time.time()
        self.recent_intervention_messages[room_id].append((now, message))

    def _test_llm_connection_on_start(self):
        """启动时测试LLM连接状态"""
        if not self.llm_api_key or not self.llm_toxicity_enabled:
            print("⚠️  LLM Toxicity Detection: DISABLED (no API key or feature disabled)")
            return
        
        if not self.llm_intervention_enabled:
            print("⚠️  LLM Intervention Messages: DISABLED")
        
        # 测试连接
        try:
            import openai
            client = openai.Client(
                api_key=self.llm_api_key,
                base_url=self.llm_base_url
            )
            
            # 简单的测试调用
            response = client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=10,
                timeout=5
            )
            
            if response.choices:
                self.llm_connection_status['toxicity'] = True
                print("✅ LLM Toxicity Detection: CONNECTED")
                
                if self.llm_intervention_enabled:
                    self.llm_connection_status['intervention'] = True
                    print("✅ LLM Intervention Messages: CONNECTED")
            else:
                print("❌ LLM Connection: Failed - no response")
                
        except ImportError:
            print("❌ LLM Connection: Failed - openai library not installed")
        except Exception as e:
            print(f"❌ LLM Connection: Failed - {str(e)}")

    def _get_recent_topic(self, room_id: str) -> Optional[str]:
        """尝试从最近消息中抽取一个话题关键词。
        为了轻量实现：优先取最近一条非空消息的前若干字符做为话题展示。
        """
        recent_messages = list(self.room_recent_messages.get(room_id, []))
        for msg in reversed(recent_messages[-5:]):
            content = (msg.get('content') or '').strip()
            if content:
                # 取前12个字符/单词，避免过长
                # 若是英文，尽量取第一个较长的 token
                tokens = re.findall(r'\w{3,}', content)
                if tokens:
                    return tokens[0][:12]
                return content[:12]
        return None

    def _compose_invitation(self, room_id: str, username: str) -> str:
        """根据 tone 与上下文选择更自然的邀请文案。"""
        if self.tone == 'warm':
            candidates = list(self.invitation_templates_warm)
            template = random.choice(candidates)
            topic = self._get_recent_topic(room_id)
            if '{topic}' in template and not topic:
                # 如果模板需要话题但没有，就换一个不需要话题的
                candidates = [t for t in candidates if '{topic}' not in t]
                template = random.choice(candidates) if candidates else self.invitation_templates[0]
            return template.format(user=username, topic=topic or '')
        # 默认回退到原有模板（略机械，但更稳定）
        return random.choice(self.invitation_templates).format(user=username)

    def _llm_generate_message(self, kind: str, room_id: str, **kwargs) -> Optional[str]:
        """生成简短、温和、像人的中文文案。kind in {silence, turn_taking, topic_pullback, agenda}。"""
        print(f"🤖 [LLM调用] 类型: {kind}, 房间: {room_id}, LLM启用: {self.llm_intervention_enabled}, API密钥: {'有' if self.llm_api_key else '无'}")
        if not (self.llm_intervention_enabled and self.llm_api_key):
            print(f"🤖 [LLM调用] 跳过 - LLM未启用或无API密钥")
            return None
        messages = list(self.room_recent_messages.get(room_id, []))[-10:]
        convo = "\n".join([f"{m.get('username')}: {m.get('content')}" for m in messages])
        
        if kind == 'silence':
            user = kwargs.get('user', '大家')
            prompt = (
                f"你是群聊助手Chime，温柔又活泼。基于以下足球讨论，生成一句很自然、很人性化的邀请语，鼓励{user}参与。"
                f"要求：1)结合当前讨论内容 2)像朋友间聊天一样轻松 3)可以用语气词、表情符号 4)15-30字 5)中文\n"
                f"示例风格：\"@{user}，你觉得呢～\" \"@{user}，好奇你的看法😊\" \"@{user}，想听听你怎么说！\"\n"
                f"避免：太正式、命令式语气、重复的套话\n"
                f"对话内容：\n{convo}"
            )
        elif kind == 'turn_taking':
            prompt = (
                "你是群聊助手Chime，很会调节气氛。基于以下对话，生成一句温和的引导语，让大家轮流发言。"
                "要求：1)像朋友间聊天 2)结合当前话题 3)可以用语气词 4)20-35字 5)中文\n"
                "示例风格：\"哈哈大家都很有想法，不如一个个来分享？\" \"讨论得很热烈呢，我们轮流说说想法～\"\n"
                "避免：太严肃、管理员口吻、命令式\n"
                f"对话内容：\n{convo}"
            )
        elif kind == 'topic_pullback':
            prompt = (
                "你是群聊助手Chime，很善于转话题。用户们刚才偏离了足球主题，请生成一句很自然的拉回语。"
                "要求：1)先认可刚才的话题很有趣 2)轻松过渡回足球 3)可以用语气词、表情 4)25-40字 5)中文\n"
                "示例风格：\"刚才讨论得很有意思呢～咱们回到足球吧，你们觉得哪队最有希望？\" \"哈哈聊得不错！不过足球话题也很精彩，大家来说说～\"\n"
                "避免：生硬转换、太正式\n"
                f"对话内容：\n{convo}"
            )
        elif kind == 'agenda':
            prompt = (
                "你是群聊助手Chime，很会引导话题。基于以下足球讨论，生成一句很自然的新话题引导语。"
                "要求：1)先肯定刚才讨论很精彩 2)提出新的足球话题 3)语气轻松有趣 4)可以用语气词 5)25-40字 6)中文\n"
                "话题方向：球员表现、教练策略、转会传闻、比赛预测、历史对比、战术分析、青训等\n"
                "示例风格：\"刚才聊得很棒！咱们聊聊新话题吧～教练的战术你们怎么看？\" \"球队分析得很到位呢，那转会市场有啥想法？\"\n"
                "避免：太正式、生硬过渡\n"
                + (f"优先围绕该主题展开：{self.icebreaker_theme}\n" if getattr(self, 'icebreaker_theme', '') else '')
                + f"对话内容：\n{convo}"
            )
        elif kind == 'icebreaker':
            prompt = (
                "你是群聊助手Chime，很会活跃气氛。现在是聊天室刚开始，还没有人发言，请生成一句很自然的破冰开场白。"
                "要求：1)热情欢迎大家 2)主动提出足球话题 3)语气轻松友好 4)可以用语气词、表情 5)20-35字 6)中文\n"
                + (f"本次破冰请围绕主题：{self.icebreaker_theme}\n" if getattr(self, 'icebreaker_theme', '') else '')
                + "话题方向：球员表现、最近比赛、球队实力、转会传闻、个人喜好、比赛预测等\n"
                "示例风格：\"大家好～我们来聊聊足球吧！最近哪场比赛最精彩？\" \"欢迎大家！说说你们支持的球队怎么样？😊\" \"来来来，大家一起聊足球～哪个球员最厉害？\"\n"
                "避免：太正式、生硬、像机器人\n"
                "注意：这是第一句话，要有破冰效果"
            )
        else:
            return None

        # 增加重试机制确保稳定性
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                # 使用同步的requests库而不是async，避免事件循环冲突
                import requests
                headers = {"Authorization": f"Bearer {self.llm_api_key}", "Content-Type": "application/json"}
                payload = {
                    "model": self.llm_message_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.8,  # 提高温度让回复更自然生动
                    "max_tokens": 120,   # 增加最大token数
                    "presence_penalty": 0.6,  # 增加内容多样性
                    "frequency_penalty": 0.3   # 减少重复内容
                }
                
                response = requests.post(
                    f"{self.llm_base_url}/chat/completions", 
                    headers=headers, 
                    json=payload, 
                    timeout=self.llm_timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                    if text:
                        result = text
                        print(f"🤖 [LLM调用] 成功 (尝试{attempt+1}): '{result}'")
                        return result
                    else:
                        print(f"🤖 [LLM调用] 空响应 (尝试{attempt+1})")
                else:
                    print(f"🤖 [LLM调用] API错误 (尝试{attempt+1}): {response.status_code} - {response.text}")
                    
            except Exception as e:
                print(f"🤖 [LLM调用] 异常 (尝试{attempt+1}): {e}")
                
            # 如果不是最后一次尝试，等待一下再重试
            if attempt < max_retries:
                time.sleep(0.5)
        
        print(f"🤖 [LLM调用] 所有尝试失败，返回None")
        return None

    def _is_active_discussion(self, room_id: str) -> bool:
        """判断房间是否处于活跃讨论（减少打断/点名）。"""
        room_id = str(room_id)  # 确保是字符串类型
        recent_messages = list(self.room_recent_messages.get(room_id, []))
        if not recent_messages:
            return False
        now = time.time()
        window_msgs = [m for m in recent_messages if now - m.get('timestamp', now) <= self.active_discussion_window_seconds]
        if len(window_msgs) < 3:
            return False
        unique_users = len(set(m.get('user_id') for m in window_msgs))
        msgs_per_min = len(window_msgs) / max(1.0, self.active_discussion_window_seconds / 60.0)
        return unique_users >= self.active_discussion_min_unique_users and msgs_per_min >= self.active_discussion_min_msg_per_minute

    def _map_llm_severity(self, sev: Optional[str]) -> Optional[OffenseLevel]:
        if sev == 'severe':
            return OffenseLevel.SEVERE
        if sev == 'moderate':
            return OffenseLevel.MODERATE
        if sev == 'mild':
            return OffenseLevel.MILD
        return None

    def _llm_classify_toxicity(self, room_id: str, last_n: int = 12) -> Optional[Dict]:
        """调用LLM识别中文互联网足球梗/绰号/嘲讽/侮辱。失败返回None。"""
        import time  # 确保time模块在函数开头导入
        
        if not (self.llm_toxicity_enabled and self.llm_api_key):
            return None

        recent_messages = list(self.room_recent_messages.get(room_id, []))[-last_n:]
        if not recent_messages:
            return None

        convo = "\n".join([f"{m.get('username')}: {m.get('content')}" for m in recent_messages])
        cache_key = hash(convo)
        now = time.time()
        cached = self.llm_result_cache.get(cache_key)
        if cached and now - cached[0] < self.llm_cache_ttl:
            return cached[1]

        prompt = (
            "你是群聊内容审核专家，专门识别中文足球讨论中的冒犯性内容。请仔细分析以下对话，重点检测：\n"
            "1. 球队黑称：如'巴狗'、'皇马狗'、'软脚虾'等贬损球队的称呼\n"
            "2. 球员侮辱：如'娜娜'、'菜鸡'、'废柴'等贬损球员的绰号\n"
            "3. 人身攻击：如'不懂球'、'没资格'、'闭嘴'等针对其他用户的攻击\n"
            "4. 粗俗语言：脏话、侮辱性词汇\n"
            "5. 隐含嘲讽：看似中性但带有明显贬损意味的表达\n\n"
            "重要：以下内容不算冒犯，请务必区分：\n"
            "- 正常球队名称：巴萨、皇马、曼联、切尔西、利物浦等\n"
            "- 正常足球术语：进球、助攻、射门、传球、战术等\n"
            "- 友善支持：支持某队、赞美球员、讨论表现等\n"
            "- 客观评价：分析优缺点、预测结果等\n"
            "只有明确的贬损、侮辱、攻击性表达才需要干预。\n\n"
            f"对话内容：\n{convo}\n\n"
            "请输出严格的JSON格式：\n"
            "{\n"
            "  \"should_intervene\": true/false,\n"
            "  \"label\": \"team_slur|player_insult|personal_attack|profanity|subtle_mockery|none\",\n"
            "  \"severity\": \"mild|moderate|severe|none\",\n"
            "  \"escalation_risk\": \"low|high\",\n"
            "  \"offending_terms\": [\"具体的冒犯词汇\"],\n"
            "  \"targets\": [\"被攻击的对象\"],\n"
            "  \"confidence\": 0.0-1.0,\n"
            "  \"suggestion\": \"温和友善的中文提醒，不要说教\"\n"
            "}"
        )

        # 添加重试机制增强稳定性
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                import requests  # 使用同步请求避免事件循环问题
                headers = {"Authorization": f"Bearer {self.llm_api_key}", "Content-Type": "application/json"}
                payload = {
                    "model": self.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,  # 略微提高温度保持一致性的同时更灵活
                    "max_tokens": 250    # 增加响应长度
                }
                
                print(f"🤖 [毒性检测] 发送LLM请求 (尝试{attempt+1}), 模型: {self.llm_model}")
                response = requests.post(
                    f"{self.llm_base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=self.llm_timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                    print(f"🤖 [毒性检测] LLM原始回复: {text}")
                    
                    if text:
                        # 清理markdown代码块格式
                        cleaned_text = text.strip()
                        if cleaned_text.startswith('```json'):
                            cleaned_text = cleaned_text[7:]  # 移除 ```json
                        if cleaned_text.startswith('```'):
                            cleaned_text = cleaned_text[3:]   # 移除 ```
                        if cleaned_text.endswith('```'):
                            cleaned_text = cleaned_text[:-3]  # 移除末尾 ```
                        cleaned_text = cleaned_text.strip()
                        
                        try:
                            result = json.loads(cleaned_text)
                            print(f"🤖 [毒性检测] 解析成功 (尝试{attempt+1}): {result}")
                            self.llm_result_cache[cache_key] = (now, result)
                            return result
                        except json.JSONDecodeError as e:
                            print(f"🤖 [毒性检测] JSON解析失败 (尝试{attempt+1}): {e}")
                            if attempt == max_retries:  # 最后一次尝试才打印详细信息
                                print(f"🤖 [毒性检测] 原始文本: '{text}'")
                                print(f"🤖 [毒性检测] 清理后文本: '{cleaned_text}'")
                    else:
                        print(f"🤖 [毒性检测] 空响应 (尝试{attempt+1})")
                else:
                    print(f"🤖 [毒性检测] API请求失败 (尝试{attempt+1}): {response.status_code}")
                    if attempt == max_retries:  # 最后一次尝试才打印详细错误
                        print(f"🤖 [毒性检测] 错误详情: {response.text}")
                        
            except Exception as e:
                print(f"🤖 [毒性检测] 异常 (尝试{attempt+1}): {e}")
                
            # 如果不是最后一次尝试，等待一下再重试
            if attempt < max_retries:
                time.sleep(0.8)  # 稍长的重试间隔
        
        print(f"🤖 [毒性检测] 所有尝试失败，返回None")
        return None

    def _llm_detect_football_topic(self, messages: List[Dict]) -> Optional[bool]:
        """使用GPT检测对话是否与足球相关"""
        if not (self.llm_intervention_enabled and self.llm_api_key):
            return None
        
        if not messages:
            return None
        
        # 构建对话内容
        convo = "\n".join([f"{m.get('username')}: {m.get('content')}" for m in messages if m.get('content')])
        if not convo.strip():
            return None
        
        # 检查缓存
        cache_key = hash(convo)
        now = time.time()
        if cache_key in self.topic_detection_cache:
            cached_time, cached_result = self.topic_detection_cache[cache_key]
            if now - cached_time < self.topic_cache_ttl:
                print(f"🤖 [GPT话题检测] 使用缓存结果: {cached_result}")
                return cached_result
        
        prompt = (
            "你是一个足球话题检测专家。请判断以下对话是否主要围绕足球相关内容进行讨论。\n"
            "足球相关包括但不限于：球队、球员、教练、战术、比赛、联赛、转会、历史、文化、青训、俱乐部管理等任何与足球运动相关的话题。\n"
            "即使涉及其他话题，只要主要讨论内容与足球相关，就应该判定为足球话题。\n"
            "请只回答 'true' 或 'false'，不要添加任何解释。\n\n"
            f"对话内容：\n{convo}"
        )
        
        try:
            import requests
            headers = {"Authorization": f"Bearer {self.llm_api_key}", "Content-Type": "application/json"}
            payload = {
                "model": self.llm_message_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,  # 低温度确保一致性
                "max_tokens": 10
            }
            
            response = requests.post(
                f"{self.llm_base_url}/chat/completions", 
                headers=headers, 
                json=payload, 
                timeout=self.llm_timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip().lower()
                print(f"🤖 [GPT话题检测] API返回: '{text}'")
                
                result = None
                if 'true' in text:
                    result = True
                elif 'false' in text:
                    result = False
                else:
                    print(f"🤖 [GPT话题检测] 无法解析结果: '{text}'")
                    return None
                
                # 缓存结果
                self.topic_detection_cache[cache_key] = (now, result)
                return result
            else:
                print(f"🤖 [GPT话题检测] API错误: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"🤖 [GPT话题检测] 异常: {e}")
            return None

    def _is_on_topic_football(self, room_id: str, window: int = 3) -> bool:
        """判断最近 window 条消息中，是否仍主要在聊"足球"。
        优先使用GPT智能检测，回退到关键词检测。
        """
        room_id = str(room_id)  # 确保是字符串类型
        recent_messages = list(self.room_recent_messages.get(room_id, []))
        if not recent_messages:
            print(f"🔍 足球话题检测: 无消息历史")
            return False
        
        subset = recent_messages[-max(1, window):]
        
        # 优先使用GPT智能检测
        gpt_result = self._llm_detect_football_topic(subset)
        if gpt_result is not None:
            print(f"🤖 [GPT话题检测] 结果: {gpt_result}")
            return gpt_result
        
        # GPT检测失败时回退到关键词检测
        print(f"🔍 [关键词话题检测] GPT检测失败，使用关键词回退")
        total = len(subset)
        hits = 0
        football_msgs = []
        for msg in subset:
            content = (msg.get('content') or '').lower()
            has_football = any(k in content for k in self.football_keywords)
            if has_football:
                hits += 1
                football_msgs.append(f"'{content[:20]}...'")
        
        ratio = hits / max(1, total)
        print(f"🔍 [关键词话题检测] {hits}/{total}={ratio:.2f}, 阈值={self.football_on_topic_ratio}")
        if football_msgs:
            print(f"   足球相关消息: {football_msgs}")
            
        return ratio >= self.football_on_topic_ratio

    def _extract_current_topic(self, room_id: str) -> Optional[str]:
        """从最近消息中提取当前讨论的主要话题关键词"""
        recent_messages = list(self.room_recent_messages.get(room_id, []))
        if not recent_messages:
            return None
        
        # 优先从最近5条消息中找足球相关话题
        for msg in reversed(recent_messages[-5:]):
            content = (msg.get('content') or '').lower()
            for keyword in self.football_keywords:
                if keyword in content:
                    # 尝试生成更自然的话题描述
                    if any(team in content for team in ['切尔西', '皇马', '巴萨', '利物浦', '曼联', 'chelsea', 'real madrid', 'barcelona']):
                        return "球队表现"
                    elif any(word in content for word in ['转会', '新援', '引援']):
                        return "转会动态"
                    elif any(word in content for word in ['战术', '阵型', '打法']):
                        return "战术分析"
                    elif any(word in content for word in ['比赛', '对战', '交锋']):
                        return "比赛回顾"
                    else:
                        return keyword[:6]  # 截取前6个字符避免过长
        
        # 如果没有足球关键词，返回通用话题
        for msg in reversed(recent_messages[-3:]):
            content = (msg.get('content') or '').strip()
            if content:
                return content[:8] + "..."  # 返回前8个字符作为话题
        
        return None

    def _get_next_topic_suggestion(self, room_id: str, current_topic: Optional[str]) -> str:
        """根据当前话题和历史，智能推荐下一个话题"""
        # 避免重复最近讨论过的话题
        recent_messages = list(self.room_recent_messages.get(room_id, []))
        discussed_topics = set()
        
        for msg in recent_messages[-10:]:  # 检查最近10条消息
            content = (msg.get('content') or '').lower()
            for topic in self.football_agenda_topics:
                if any(word in content for word in topic.split()):
                    discussed_topics.add(topic)
        
        # 筛选出未讨论的话题
        available_topics = [t for t in self.football_agenda_topics if t not in discussed_topics]
        
        # 如果所有话题都讨论过，则随机选择
        if not available_topics:
            available_topics = self.football_agenda_topics
        
        return random.choice(available_topics)


    def analyze_message(self, room_id: str, user_id: str, username: str, 
                       message_content: str, gender: str = 'unknown') -> Optional[InterventionResult]:
        
        # 确保房间ID和用户ID是字符串类型
        room_id = str(room_id)
        user_id = str(user_id)
        
        current_time = time.time()
        print(f"🔍 分析消息: [{username}] {message_content[:30]}...")
        
        # 检查上次干预时间
        last_intervention = self.room_last_intervention_ts.get(room_id, 0)
        time_since_last = current_time - last_intervention
        print(f"⏰ 房间{room_id} - 距离上次干预: {time_since_last:.1f}秒")
        
        # 检查是否在话题内
        is_on_topic = self._is_on_topic_football(room_id)
        print(f"⚽ 是否在足球话题内: {is_on_topic}")
        
        # 检查活跃讨论状态
        is_active = self._is_active_discussion(room_id)
        print(f"💬 是否活跃讨论: {is_active}")
        
        # 检查沉默状态
        if len(self.room_recent_messages.get(room_id, [])) > 0:
            last_msg_time = list(self.room_recent_messages.get(room_id, []))[-1]['timestamp']
            silence_duration = current_time - last_msg_time
            print(f"🤫 房间沉默时长: {silence_duration:.1f}秒")
        
        # 检查全局冷却
        global_cooldown_left = self.global_cooldown_seconds - time_since_last
        print(f"❄️ 全局冷却剩余: {max(0, global_cooldown_left):.1f}秒")
        
        self.user_last_message_time[f"{room_id}_{user_id}"] = current_time
        self.user_message_count[f"{room_id}_{user_id}"] += 1
        
        message_info = {
            'user_id': user_id,
            'username': username,
            'content': message_content,
            'timestamp': current_time,
            'gender': gender
        }
        self.room_recent_messages[room_id].append(message_info)
        print(f"📝 [消息存储] 房间{room_id}: 用户{user_id}({username}) - '{message_content[:30]}...' (总消息数: {len(self.room_recent_messages.get(room_id, []))})")
        
        # 优先检查紧急冲突（不受全局冷却限制）
        conflict_result = self._check_conflict_intervention(room_id, user_id, message_content, username)
        if conflict_result and conflict_result.should_intervene:
            # 对于紧急情况（SEVERE级别或emergency_brake），跳过冷却
            is_emergency = (conflict_result.offense_level == OffenseLevel.SEVERE or 
                          "emergency_brake" in conflict_result.reason.lower())
            
            if is_emergency:
                self.room_last_intervention_ts[room_id] = current_time
                return conflict_result
            
            # 非紧急冲突也要遵守全局冷却
            last_ts = self.room_last_intervention_ts.get(room_id, 0)
            if current_time - last_ts >= self.global_cooldown_seconds:
                # 检查消息去重：避免90秒内重复相同话术
                if not self._is_duplicate_message(room_id, conflict_result.message):
                    self._record_intervention_message(room_id, conflict_result.message)
                    self.room_last_intervention_ts[room_id] = current_time
                    return conflict_result
        
        # 全局冷却检查：非紧急干预需要等待冷却
        last_ts = self.room_last_intervention_ts.get(room_id, 0)
        if current_time - last_ts < self.global_cooldown_seconds:
            return None  # 冷却期内，跳过所有非紧急干预
        
        # 活跃讨论保护：避免在高活跃窗口频繁点名
        silence_result = None
        if not self._is_active_discussion(room_id):
            print(f"🔍 [主流程] 检查沉默干预...")
            silence_result = self._check_silence_intervention(room_id)
            if silence_result:
                print(f"🔍 [主流程] 沉默检测结果: {silence_result.should_intervene}, 类型: {silence_result.intervention_type}, 消息: {silence_result.message[:30]}...")
        else:
            print(f"🔍 [主流程] 跳过沉默检测 - 活跃讨论中")
        if silence_result and silence_result.should_intervene:
            if not self._is_duplicate_message(room_id, silence_result.message):
                self._record_intervention_message(room_id, silence_result.message)
                self.room_last_intervention_ts[room_id] = current_time
                print(f"✅ [主流程] 返回沉默干预结果")
                return silence_result
            else:
                print(f"⚠️ [主流程] 沉默干预消息重复，跳过")
        
        # 议程过渡检测（房间沉默60秒时引导话题）
        print(f"🔍 [主流程] 检查议程过渡...")
        agenda_result = self._check_agenda_transition(room_id)
        if agenda_result:
            print(f"🔍 [主流程] 议程过渡结果: {agenda_result.should_intervene}, 类型: {agenda_result.intervention_type}, 消息: {agenda_result.message[:30]}...")
        if agenda_result and agenda_result.should_intervene:
            if not self._is_duplicate_message(room_id, agenda_result.message):
                self._record_intervention_message(room_id, agenda_result.message)
                self.room_last_intervention_ts[room_id] = current_time
                print(f"✅ [主流程] 返回议程过渡结果")
                return agenda_result
            else:
                print(f"⚠️ [主流程] 议程过渡消息重复，跳过")
            
        # 结构引导需要额外的活跃讨论保护
        if not self._is_active_discussion(room_id):
            structure_result = self._check_structure_guidance(room_id)
            if structure_result and structure_result.should_intervene:
                if not self._is_duplicate_message(room_id, structure_result.message):
                    self._record_intervention_message(room_id, structure_result.message)
                    self.room_last_intervention_ts[room_id] = current_time
                    return structure_result
        
        return None

    # def _check_conflict_intervention(self, room_id: str, message_content: str, 
    #                                username: str) -> Optional[InterventionResult]:
        
    #     offense_level = self._detect_offense_level(message_content)
    #     if offense_level:
    #         user_key = f"{room_id}_{username}"
    #         self.user_offense_count[user_key] += 1
            
    #         if offense_level == OffenseLevel.SEVERE or self.user_offense_count[user_key] >= 3:
    #             template = self.conflict_templates[OffenseLevel.SEVERE][0]
    #             reason = f"检测到严重冒犯性词汇或累计冒犯: {message_content[:50]}"
    #         elif offense_level == OffenseLevel.MODERATE or self.user_offense_count[user_key] >= 2:
    #             template = self.conflict_templates[OffenseLevel.MODERATE][0] 
    #             reason = f"检测到中度冒犯性词汇: {message_content[:50]}"
    #         else:
    #             template = self.conflict_templates[OffenseLevel.MILD][0]
    #             reason = f"检测到轻度不当词汇: {message_content[:50]}"
            
    #         return InterventionResult(
    #             should_intervene=True,
    #             intervention_type=InterventionType.CONFLICT_INTERRUPTION,
    #             message=template,
    #             reason=reason,
    #             offense_level=offense_level
    #         )
        
    #     recent_messages = list(self.room_recent_messages[room_id])
    #     if len(recent_messages) >= 4:
    #         conflict_count = 0
    #         for msg in recent_messages[-4:]:
    #             if self._is_conflict_message(msg['content']):
    #                 conflict_count += 1
            
    #         if conflict_count >= 3:
    #             reason = f"检测到连续冲突消息，冲突等级: {conflict_count}/4"
    #             return InterventionResult(
    #                 should_intervene=True,
    #                 intervention_type=InterventionType.CONFLICT_INTERRUPTION,
    #                 message="讨论变得激烈，请大家冷静一下。",
    #                 reason=reason,
    #                 offense_level=OffenseLevel.MODERATE
    #             )
        
    #     return None



    def _check_conflict_intervention(
        self, room_id: str, user_id: str, message_content: str, username: str
    ) -> Optional[InterventionResult]:

        print(f"🔍 [冲突检测] 分析消息: '{message_content}' from {username}")
        
        # 优先使用 LLM 识别（中文互联网足球梗/嘲讽/侮辱）
        llm_result: Optional[Dict] = self._llm_classify_toxicity(room_id, last_n=12)
        print(f"🤖 [冲突检测] LLM分析结果: {llm_result}")
        
        offense_level = None
        if llm_result and llm_result.get('should_intervene') and llm_result.get('confidence', 0) >= self.llm_conf_threshold:
            mapped = self._map_llm_severity(llm_result.get('severity'))
            if mapped:
                # 紧急刹车：升级风险高
                if llm_result.get('escalation_risk') == 'high':
                    reason = "LLM判定升级风险高，触发紧急降温"
                    return InterventionResult(
                        should_intervene=True,
                        intervention_type=InterventionType.CONFLICT_INTERRUPTION,
                        message=(llm_result.get('suggestion') or "大家先停一下，建议冷静。我们换个角度：这场的数据怎么看？"),
                        reason=reason,
                        offense_level=mapped,
                        stage=2, action=None, mute_seconds=None,
                        via_llm=True, llm_confidence=llm_result.get('confidence'), llm_label=llm_result.get('label')
                    )
                offense_level = mapped
        else:
            # 回退：本地词库识别
            print(f"🔍 [关键词检测] LLM检测失败或未达阈值，使用关键词回退")
            offense_level = self._detect_offense_level(message_content)
            print(f"🔍 [关键词检测] 检测结果: {offense_level}")
            if offense_level:
                print(f"🔍 [关键词检测] 检测到攻击性语言级别: {offense_level.name}")
        if not offense_level:
            # 另外做一个“最近4条里冲突语气很多”的群体级检测
            recent_messages = list(self.room_recent_messages.get(room_id, []))
            if len(recent_messages) >= 4:
                conflict_count = sum(
                    1 for msg in recent_messages[-4:] if self._is_conflict_message(msg['content'])
                )
                if conflict_count >= 3:
                    reason = f"检测到连续冲突消息，冲突等级: {conflict_count}/4"
                    return InterventionResult(
                        should_intervene=True,
                        intervention_type=InterventionType.CONFLICT_INTERRUPTION,
                        message="讨论变得激烈，请大家冷静一下。",
                        reason=reason,
                        offense_level=OffenseLevel.MODERATE,
                        stage=2, action=None, mute_seconds=None
                    )
            return None

        # ------- 渐进式：按“房间+user_id”累计，且带时间窗清零 -------
        now = time.time()
        vkey = f"{room_id}_{user_id}"

        last_ts = self.user_last_violation_ts.get(vkey, 0)
        if now - last_ts > self.violation_window_seconds:
            # 超过时间窗，清零历史计数
            self.user_violation_count[vkey] = 0

        # 是否跳过“首次 MILD 不计数”（需要的话把下一行注释去掉）
        # if offense_level == OffenseLevel.MILD and self.user_violation_count[vkey] == 0:
        #     pass
        # else:
        self.user_violation_count[vkey] += 1

        self.user_last_violation_ts[vkey] = now
        count = self.user_violation_count[vkey]

        # ------- 分级决定 -------
        stage = 1
        action = None
        mute_seconds = None

        # 这里**不**再因为 SEVERE 就直接禁言；只有累计到阈值才禁言
        if count >= self.mute_stage_threshold:
            stage = 3
            action = 'mute'
            mute_seconds = self.default_mute_seconds
        elif count >= self.warn_stage_threshold:
            stage = 2
        else:
            stage = 1

        # # 文案：轻度/中度/重度用不同模板，但禁言时会覆盖为禁言说明
        # if offense_level == OffenseLevel.SEVERE:
        #     template = self.conflict_templates[OffenseLevel.SEVERE][1]  # “请保持基本的尊重...”
        # elif offense_level == OffenseLevel.MODERATE:
        #     template = self.conflict_templates[OffenseLevel.MODERATE][0]
        # else:
        #     template = self.conflict_templates[OffenseLevel.MILD][0]

        # ===== 按“阶段”出文案（与需求一致）=====
        if stage == 3:
            template = f"已对 {username} 进行 {int(self.default_mute_seconds/60)} 分钟禁言。"
        elif stage == 2:
            template = (
                (llm_result.get('suggestion') if isinstance(llm_result, dict) and llm_result.get('suggestion') else None)
                or "多次使用冒犯性称呼，影响讨论氛围，请注意。"
            )
        else:
            template = (
                (llm_result.get('suggestion') if isinstance(llm_result, dict) and llm_result.get('suggestion') else None)
                or "提示：请避免使用可能冒犯的外号。"
            )

        reason = (
            f"渐进式治理 stage={stage}，"
            f"offense={offense_level.name}, "
            f"计数={count}/{self.mute_stage_threshold}，消息: {message_content[:50]}"
        )

        # 真正禁言时，给群里的提示文案交给上层覆盖为“已对@XX禁言N分钟”
        return InterventionResult(
            should_intervene=True,
            intervention_type=InterventionType.CONFLICT_INTERRUPTION,
            message=template,
            reason=reason,
            offense_level=offense_level,
            stage=stage,
            action=action,
            mute_seconds=mute_seconds,
            via_llm=bool(llm_result and llm_result.get('confidence', 0) >= self.llm_conf_threshold),
            llm_confidence=(llm_result.get('confidence') if isinstance(llm_result, dict) else None),
            llm_label=(llm_result.get('label') if isinstance(llm_result, dict) else None)
        )


    def _check_silence_intervention(self, room_id: str) -> Optional[InterventionResult]:
        
        room_id = str(room_id)  # 确保是字符串类型
        current_time = time.time()
        recent_messages = list(self.room_recent_messages.get(room_id, []))
        
        # 过滤掉admin消息，只看普通用户消息
        non_admin_messages = [msg for msg in recent_messages if not self._is_admin_user(str(msg['user_id']))]
        print(f"🔍 [沉默检测] 房间{room_id} 总消息: {len(recent_messages)}, 非admin消息: {len(non_admin_messages)}")
        
        # 需要至少3轮对话后才开始沉默检测
        min_messages_for_detection = 3
        if len(non_admin_messages) < min_messages_for_detection:
            print(f"🔍 [沉默检测] 房间{room_id} 对话不足，需要{min_messages_for_detection}轮对话后才开始检测: {len(non_admin_messages)}/{min_messages_for_detection}")
            return None
        
        # 获取所有在线用户（包括从未发言的用户）
        all_users_in_room = self._get_online_users_in_room(room_id)
        user_last_msg_time = {}
        
        # 从非admin消息历史中获取发言用户的时间
        for msg in non_admin_messages:
            user_id = str(msg['user_id'])
            # 记录每个用户的最后发言时间
            user_last_msg_time[user_id] = max(
                user_last_msg_time.get(user_id, 0), 
                msg['timestamp']
            )
        
        # 从全局记录中获取用户发言时间
        for user_key in self.user_last_message_time:
            if user_key.startswith(f"{room_id}_"):
                user_id = user_key.split(f"{room_id}_", 1)[1]
                if user_id not in user_last_msg_time:
                    # 如果用户在当前消息窗口中没有发言，使用全局记录的时间
                    user_last_msg_time[user_id] = self.user_last_message_time[user_key]
        
        # 对于完全没有发言记录的在线用户，设置一个很早的时间（表示一直沉默）
        for user_id in all_users_in_room:
            if user_id not in user_last_msg_time:
                # 设置为1小时前，表示这个用户一直没有发言
                user_last_msg_time[user_id] = current_time - 3600  # 1小时前
        
        print(f"🔍 [沉默检测] 房间{room_id} 用户发言时间: {[(uid, current_time - last_time) for uid, last_time in user_last_msg_time.items()]}")
        
        # 创建用户沉默时长列表，按沉默时长排序（最长的优先）
        user_silence_list = []
        for user_id in all_users_in_room:
            last_msg_time = user_last_msg_time.get(user_id, 0)
            silence_duration = current_time - last_msg_time
            
            print(f"🤫 [沉默检测] 用户{user_id} 沉默时长: {silence_duration:.1f}秒 (阈值: {self.silence_threshold}秒)")
            
            # 检查是否是管理员用户 - 管理员不需要沉默提醒
            if self._is_admin_user(user_id):
                print(f"👑 [沉默检测] 用户{user_id} 是管理员，跳过沉默检测")
                continue
            
            if silence_duration > self.silence_threshold:
                user_silence_list.append((user_id, silence_duration, last_msg_time))
        
        # 按沉默时长排序，最久沉默的用户优先
        user_silence_list.sort(key=lambda x: x[1], reverse=True)
        
        print(f"🔄 [沉默检测] 沉默用户排序: {[(uid, f'{duration:.1f}s') for uid, duration, _ in user_silence_list]}")
        
        # 🔍 全局沉默检测：如果所有非admin用户都沉默超过阈值，则触发话题转换
        non_admin_users_in_room = [uid for uid in all_users_in_room if not self._is_admin_user(uid)]
        all_silent_users = [uid for uid, _, _ in user_silence_list]
        
        print(f"🔍 [全局沉默检测] 房间{room_id}: 沉默用户数{len(all_silent_users)}, 非admin用户总数{len(non_admin_users_in_room)}")
        print(f"🔍 [全局沉默检测] 沉默用户: {all_silent_users}")
        print(f"🔍 [全局沉默检测] 非admin用户: {non_admin_users_in_room}")
        
        if len(all_silent_users) >= len(non_admin_users_in_room) and len(non_admin_users_in_room) >= 2:
            print(f"🌍 [全局沉默] 房间{room_id} 所有用户({len(all_silent_users)}/{len(non_admin_users_in_room)})都沉默 → 触发话题转换")
            
            # 检查话题转换冷却
            last_transition_time = self.room_last_agenda_transition.get(room_id, 0)
            transition_cooldown = 120  # 2分钟话题转换冷却 [[memory:7476173]]
            if current_time - last_transition_time >= transition_cooldown:
                self.room_last_agenda_transition[room_id] = current_time
                
                llm_msg = self._llm_generate_message('agenda', room_id)
                transition_msg = llm_msg or "大家聊聊新的话题吧，刚才关于球队的讨论很精彩！"
                print(f"🤖 [LLM] 全局沉默 - LLM生成: '{llm_msg}', 最终消息: '{transition_msg}'")
                reason = f"全局沉默检测：{len(all_silent_users)}个用户都沉默超过阈值"
                print(f"✅ [全局沉默] 即将返回话题转换干预：{transition_msg}")
                
                return InterventionResult(
                    should_intervene=True,
                    intervention_type=InterventionType.AGENDA_TRANSITION,
                    message=transition_msg,
                    reason=reason
                )
            else:
                remaining_time = transition_cooldown - (current_time - last_transition_time)
                print(f"🕒 [全局沉默] 话题转换冷却中，剩余{remaining_time:.1f}秒")
                return None
        
        # 🎯 个人沉默检测：优先处理沉默最久的用户
        for user_id, silence_duration, last_msg_time in user_silence_list:
            # 检查用户提醒冷却 (2分钟内不重复提醒同一用户) [[memory:7476173]]
            user_reminder_key = f"{room_id}_{user_id}"
            last_reminder_time = self.user_last_reminder_time.get(user_reminder_key, 0)
            reminder_cooldown = 120  # 2分钟用户提醒冷却
            
            if current_time - last_reminder_time < reminder_cooldown:
                remaining_time = reminder_cooldown - (current_time - last_reminder_time)
                print(f"⏰ [用户冷却] 用户{user_id} 提醒冷却中，剩余{remaining_time:.1f}秒")
                continue  # 跳过这个用户，检查下一个
            
            # 找到用户名 - 先从最近消息中查找，如果找不到则从全局记录或使用默认名
            silent_username = None
            
            # 1. 从最近消息中查找
            for msg in reversed(recent_messages):
                if str(msg['user_id']) == user_id:
                    silent_username = msg['username']
                    break
            
            # 2. 如果找不到，查找从non_admin_messages中找
            if not silent_username:
                for msg in reversed(non_admin_messages):
                    if str(msg['user_id']) == user_id:
                        silent_username = msg['username']
                        break
            
            # 3. 如果还找不到，使用默认用户名映射
            if not silent_username:
                user_mapping = {'2': 'Lily', '4': 'Zack', '5': 'Steve'}
                silent_username = user_mapping.get(user_id, f'User{user_id}')
                print(f"⚠️ [沉默检测] 用户{user_id}未找到用户名，使用默认: {silent_username}")
            
            if silent_username:
                print(f"👋 [沉默检测] 发现沉默用户: {silent_username} (沉默{silence_duration:.1f}秒) - 优先级最高")
                
                # 更新用户提醒时间
                self.user_last_reminder_time[user_reminder_key] = current_time
                
                # LLM生成更自然的点名
                llm_msg = self._llm_generate_message('silence', room_id, user=silent_username)
                invitation_msg = llm_msg or f"@{silent_username}，也来聊聊你的看法吧～"
                print(f"🤖 [LLM] 沉默邀请 - LLM生成: '{llm_msg}', 最终消息: '{invitation_msg}'")
                reason = f"检测到用户 {silent_username} 沉默超过 {int(silence_duration)} 秒（沉默最久）"
                
                return InterventionResult(
                    should_intervene=True,
                    intervention_type=InterventionType.SILENCE_INVITATION,
                    message=invitation_msg,
                    reason=reason,
                    target_user=silent_username
                )
        
        print(f"🔍 [沉默检测] 房间{room_id} 无沉默用户需要干预")
        return None

    def _check_agenda_transition(self, room_id: str) -> Optional[InterventionResult]:
        """检查是否需要议程过渡引导（群体沉默时主动开启话题，无轮数限制）"""
        room_id = str(room_id)  # 确保是字符串类型
        current_time = time.time()
        recent_messages = list(self.room_recent_messages.get(room_id, []))
        
        # 过滤掉admin消息，只看普通用户消息
        non_admin_messages = [msg for msg in recent_messages if not self._is_admin_user(str(msg['user_id']))]
        
        # 群体沉默检测：无轮数限制，只要检测到沉默就主动开启话题
        # 这样可以帮助大家在刚开始聊天时破冰
        print(f"🔍 [群体沉默] 房间{room_id} 当前消息数: {len(non_admin_messages)}")
        
        # 如果没有任何消息，也可以主动开启话题
        if len(non_admin_messages) == 0:
            print(f"🆕 [群体沉默] 房间{room_id} 无消息历史，主动开启破冰话题")
        
        # 检查冷却时间
        last_transition_time = self.room_last_agenda_transition.get(room_id, 0)
        if current_time - last_transition_time < self.agenda_transition_cooldown:
            print(f"⏸️ [群体沉默] 房间{room_id} 仍在冷却中，剩余{self.agenda_transition_cooldown - (current_time - last_transition_time):.1f}秒")
            return None
        
        # 计算房间最后一条消息的时间
        last_message_time = recent_messages[-1]['timestamp'] if recent_messages else 0
        silence_duration = current_time - last_message_time
        
        # 群体沉默检测：针对实验场景的智能破冰逻辑
        should_start_topic = False
        reason = ""
        
        if len(non_admin_messages) == 0:
            # 没有普通用户消息，检查是否是实验开始场景
            if len(recent_messages) > 0:
                # 有消息（通常是admin欢迎消息），从最后一条admin消息开始计算用户沉默时间
                last_admin_msg_time = recent_messages[-1]['timestamp']
                user_silence_since_admin = current_time - last_admin_msg_time
                
                # 如果admin发消息后用户沉默超过阈值，开启破冰话题
                if user_silence_since_admin >= self.agenda_transition_threshold:
                    should_start_topic = True
                    reason = f"实验开始场景：admin消息后用户沉默{int(user_silence_since_admin)}秒，主动开启破冰话题"
                    print(f"🎯 [实验破冰] {reason}")
                else:
                    print(f"🕒 [实验场景] 等待用户响应admin消息，已沉默{int(user_silence_since_admin)}秒/{self.agenda_transition_threshold}秒")
            else:
                # 完全没有消息，直接开启破冰话题
                should_start_topic = True
                reason = "房间无任何消息历史，主动开启破冰话题"
                print(f"🆕 [群体沉默] {reason}")
        else:
            # 有普通用户消息，检查最后一条普通用户消息的沉默时间
            last_non_admin_msg = non_admin_messages[-1]
            user_silence_duration = current_time - last_non_admin_msg['timestamp']
            
            if user_silence_duration >= self.agenda_transition_threshold:
                should_start_topic = True
                reason = f"用户沉默 {int(user_silence_duration)} 秒，主动开启新话题"
                print(f"🤐 [群体沉默] {reason}")
            else:
                print(f"🕒 [沉默监控] 用户最后发言{int(user_silence_duration)}秒前，未达到{self.agenda_transition_threshold}秒阈值")
        
        if should_start_topic:
            current_topic = self._extract_current_topic(room_id)
            next_topic = self._get_next_topic_suggestion(room_id, current_topic)
            
            # 根据不同情况选择合适的话题开启方式
            if len(non_admin_messages) == 0:
                # 完全没有消息历史，使用破冰话题模板
                theme = getattr(self, 'icebreaker_theme', '')
                icebreaker_templates = [
                    (f"{theme}" if theme else f"大家好！我们来聊聊{next_topic}怎么样？"),
                    (f"{theme}" if theme else f"欢迎大家！先从{next_topic}开始聊聊吧～"),
                    (f"{theme}" if theme else f"大家都在吗？我们聊聊{next_topic}如何？"),
                    (f"{theme}" if theme else f"来来来，大家一起讨论一下{next_topic}吧！"),
                    (f"{theme}" if theme else f"开始我们的足球话题吧！{next_topic}大家怎么看？")
                ]
                template = random.choice(icebreaker_templates)
                # LLM生成破冰消息，失败回退模板
                llm_msg = self._llm_generate_message('icebreaker', room_id) 
                message = llm_msg or template
                print(f"🤖 [LLM] 破冰话题 - LLM生成: '{llm_msg}', 最终消息: '{message}'")
            elif current_topic:
                # 有明确当前话题，使用过渡模板
                template = random.choice([
                    t for t in self.agenda_transition_templates 
                    if '{current_topic}' in t
                ])
                # LLM生成自然过渡，失败回退模板
                llm_msg = self._llm_generate_message('agenda', room_id)
                message = (llm_msg or template.format(current_topic=current_topic, next_topic=next_topic))
                print(f"🤖 [LLM] 议程过渡 - LLM生成: '{llm_msg}', 最终消息: '{message}'")
            else:
                # 没有明确当前话题，使用简单引导
                template = random.choice([
                    t for t in self.agenda_transition_templates 
                    if '{current_topic}' not in t
                ])
                llm_msg = self._llm_generate_message('agenda', room_id)
                message = (llm_msg or template.format(next_topic=next_topic))
                print(f"🤖 [LLM] 议程过渡(简单) - LLM生成: '{llm_msg}', 最终消息: '{message}'")
            
            # 记录这次议程过渡时间
            self.room_last_agenda_transition[room_id] = current_time
            return InterventionResult(
                should_intervene=True,
                intervention_type=InterventionType.AGENDA_TRANSITION,
                message=message,
                reason=reason
            )
        
        return None

    def _check_structure_guidance(self, room_id: str) -> Optional[InterventionResult]:
        
        room_id = str(room_id)  # 确保是字符串类型
        recent_messages = list(self.room_recent_messages.get(room_id, []))
        
        # 过滤掉admin消息，只看普通用户消息
        non_admin_messages = [msg for msg in recent_messages if not self._is_admin_user(str(msg['user_id']))]
        
        # 需要至少3轮对话后才考虑结构引导
        min_messages_for_detection = 3
        if len(non_admin_messages) < min_messages_for_detection:
            return None
        
        if len(recent_messages) < 8:
            return None
        
        consecutive_count = 1
        last_user = recent_messages[-1]['user_id']
        last_username = recent_messages[-1]['username']
        consecutive_time_span = 0
        consecutive_total_length = 0
        has_response = False  # 检查是否有其他人回应
        
        # 计算连续发言的时间跨度和内容长度
        last_timestamp = recent_messages[-1]['timestamp']
        
        for i in range(len(recent_messages)-2, max(len(recent_messages)-6, -1), -1):
            if recent_messages[i]['user_id'] == last_user:
                consecutive_count += 1
                consecutive_time_span = last_timestamp - recent_messages[i]['timestamp']
                consecutive_total_length += len(recent_messages[i]['content'])
            else:
                # 检查其他用户是否有及时回应
                if last_timestamp - recent_messages[i]['timestamp'] < 60:  # 1分钟内
                    has_response = True
                break
        
        consecutive_total_length += len(recent_messages[-1]['content'])
        
        # 更智能的判断：需要满足多个条件
        should_remind_turn_taking = (
            consecutive_count >= 4 or  # 连续4条以上
            (consecutive_count >= 3 and consecutive_time_span > 120 and not has_response) or  # 3条且超过2分钟无人回应
            (consecutive_count >= 3 and consecutive_total_length > 200)  # 3条且内容较长
        )
        
        if should_remind_turn_taking:
            reason = f"检测到用户 {last_username} 连续发言 {consecutive_count} 条（{consecutive_time_span:.0f}秒，无及时回应）"
            # LLM 生成更自然的轮次提醒
            llm_msg = self._llm_generate_message('turn_taking', room_id)
            final_msg = llm_msg or "建议大家先都说一遍自己的观点，再进入讨论。"
            print(f"🤖 [LLM] 轮次引导 - LLM生成: '{llm_msg}', 最终消息: '{final_msg}'")
            return InterventionResult(
                should_intervene=True,
                intervention_type=InterventionType.STRUCTURE_GUIDANCE,
                message=final_msg,
                reason=reason
            )
        
        recent_topics = []
        for msg in recent_messages[-5:]:
            words = re.findall(r'\b\w+\b', msg['content'].lower())
            if words:
                recent_topics.extend(words[:3])
        
        if len(set(recent_topics)) > len(recent_topics) * 0.8:
            # 若仍主要聊“足球”，则不认为跑题，避免误触发
            if self._is_on_topic_football(room_id, window=3):
                return None
            reason = "检测到话题跳跃，讨论较分散（且不主要围绕足球）"
            # LLM 生成简短总结+拉回
            llm_msg = self._llm_generate_message('topic_pullback', room_id)
            final_msg = llm_msg or "大家聊得很热烈！我们回到足球话题，继续分享你们的观点吧～"
            print(f"🤖 [LLM] 话题拉回 - LLM生成: '{llm_msg}', 最终消息: '{final_msg}'")
            return InterventionResult(
                should_intervene=True,
                intervention_type=InterventionType.STRUCTURE_GUIDANCE,
                message=final_msg,
                reason=reason
            )
        
        return None

    def _detect_offense_level(self, message: str) -> Optional[OffenseLevel]:
        message_lower = message.lower()
        
        # 检查严重级别
        for keyword in self.offense_keywords[OffenseLevel.SEVERE]:
            if keyword.lower() in message_lower:
                print(f"🚨 [关键词检测] 检测到严重冒犯词汇: '{keyword}' in '{message[:30]}...'")
                return OffenseLevel.SEVERE
        
        # 检查中等级别
        for keyword in self.offense_keywords[OffenseLevel.MODERATE]:
            if keyword.lower() in message_lower:
                print(f"⚠️ [关键词检测] 检测到中等冒犯词汇: '{keyword}' in '{message[:30]}...'")
                return OffenseLevel.MODERATE
        
        # 检查轻微级别
        for keyword in self.offense_keywords[OffenseLevel.MILD]:
            if keyword.lower() in message_lower:
                print(f"💡 [关键词检测] 检测到轻微冒犯词汇: '{keyword}' in '{message[:30]}...'")
                return OffenseLevel.MILD
        
        # 增加变体和模糊匹配检测
        offense_patterns = self._check_offensive_patterns(message_lower)
        if offense_patterns:
            print(f"🔍 [模式检测] 检测到冒犯模式: {offense_patterns}")
            return offense_patterns
        
        return None
    
    def _check_offensive_patterns(self, message_lower: str) -> Optional[OffenseLevel]:
        """检测冒犯性模式和变体"""
        
        # 球队相关贬损模式
        team_slur_patterns = [
            ('狗', ['巴萨', '皇马', '利物浦', '切尔西', '曼联', '阿森纳', '热刺', '拜仁', '尤文', '米兰', '国米', '多特', '马竞']),
            ('废', ['巴萨', '皇马', '球队', '俱乐部']),
            ('菜', ['队', '球队', '这队', '他们']),
        ]
        
        for suffix, prefixes in team_slur_patterns:
            for prefix in prefixes:
                if f"{prefix}{suffix}" in message_lower or f"{prefix}是{suffix}" in message_lower:
                    return OffenseLevel.MODERATE
        
        # 球员贬损模式
        player_insult_patterns = [
            '滚出', '滚蛋', '别踢了', '退役吧', '没天赋', '就这水平'
        ]
        
        for pattern in player_insult_patterns:
            if pattern in message_lower:
                return OffenseLevel.MODERATE
        
        # 人身攻击模式
        personal_attack_patterns = [
            '你懂个', '别说话', '闭嘴吧', '没脑子', '智商', '弱智', '傻'
        ]
        
        for pattern in personal_attack_patterns:
            if pattern in message_lower:
                return OffenseLevel.SEVERE
        
        return None

    def _is_conflict_message(self, content: str) -> bool:
        
        conflict_indicators = [
            '不对', '错了', '胡说', '放屁', '扯淡', '我不同意',
            '你这', '什么鬼', '太离谱', '无语', '服了'
        ]
        
        content_lower = content.lower()
        for indicator in conflict_indicators:
            if indicator in content_lower:
                return True
        
        exclamation_count = content.count('!') + content.count('！')
        question_count = content.count('?') + content.count('？')
        
        if len(content) > 0:
            punctuation_density = (exclamation_count + question_count) / len(content)
            if punctuation_density > 0.1:
                return True
        
        return False

    def reset_room_data(self, room_id: str):
        room_id = str(room_id)  # 确保是字符串类型
        if room_id in self.room_recent_messages:
            self.room_recent_messages[room_id].clear()
        self.room_conflict_level[room_id] = 0
        self.room_topic_keywords[room_id].clear()

    def get_room_stats(self, room_id: str) -> Dict:
        room_id = str(room_id)  # 确保是字符串类型
        recent_messages = list(self.room_recent_messages.get(room_id, []))
        
        user_message_counts = defaultdict(int)
        total_messages = len(recent_messages)
        
        for msg in recent_messages:
            user_message_counts[msg['username']] += 1
        
        return {
            'total_messages': total_messages,
            'active_users': len(user_message_counts),
            'user_message_counts': dict(user_message_counts),
            'conflict_level': self.room_conflict_level[room_id]
        }
    
    # 2025.8.27 新增以下两个接口

    def is_user_muted(self, room_id: str, user_id: str) -> Tuple[bool, int]:
        """返回是否被禁言以及剩余秒数"""
        room_id = str(room_id)  # 确保是字符串类型
        user_id = str(user_id)
        key = f"{room_id}_{user_id}"
        until_ts = self.user_mute_until.get(key, 0)
        now = time.time()
        if until_ts > now:
            return True, int(until_ts - now)
        return False, 0

    def record_mute(self, room_id: str, user_id: str, seconds: int):
        """设置禁言到期时间"""
        room_id = str(room_id)  # 确保是字符串类型
        user_id = str(user_id)
        key = f"{room_id}_{user_id}"
        self.user_mute_until[key] = time.time() + max(1, seconds)

    def _is_admin_user(self, user_id: str) -> bool:
        """检查用户是否是管理员"""
        try:
            # 这里需要查询数据库来检查用户是否是管理员
            # 由于在智能引擎中，我们使用简单的方法：假设user_id >= 8的是管理员
            # 或者可以维护一个管理员ID列表
            admin_user_ids = {'8', '9', '10'}  # 管理员用户ID列表
            return str(user_id) in admin_user_ids
        except Exception:
            return False

    def _get_online_users_in_room(self, room_id: str) -> set:
        """获取房间中的在线用户（需要从应用层传入或查询）"""
        # 这是一个简化版本，实际应该从应用层获取
        # 目前我们从已知的用户消息记录中推断
        online_users = set()
        
        # 从最近的消息中获取活跃用户
        for user_key in self.user_last_message_time:
            if user_key.startswith(f"{room_id}_"):
                user_id = user_key.split(f"{room_id}_", 1)[1]
                online_users.add(user_id)
        
        # 同样从最近消息中获取
        recent_messages = list(self.room_recent_messages.get(room_id, []))
        for msg in recent_messages:
            online_users.add(str(msg['user_id']))
            
        # 假设包括一些已知的测试用户ID（根据你的测试场景调整）
        # 这里可以根据实际情况添加当前房间的在线用户
        test_user_ids = ['2', '4', '5']  # Lily, Zack, Steve的用户ID
        for uid in test_user_ids:
            online_users.add(uid)
            
        return online_users
