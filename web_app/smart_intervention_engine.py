import re
import os
import random
import time
import json
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union
from enum import Enum


class InterventionType(Enum):
    SILENCE_INVITATION = "silence_invitation"
    TOXICITY_WARNING = "toxicity_warning"
    CONFLICT_DEESCALATION = "conflict_deescalation"
    STRUCTURE_GUIDANCE = "structure_guidance"
    SAFETY_WARNING = "safety_warning"
    AGENDA_TRANSITION = "agenda_transition"
    GENTLE_REDIRECT = "gentle_redirect"
    EMERGENCY_DEESCALATION = "emergency_deescalation"


class ToxicityLevel(Enum):
    NONE = 0
    MILD = 1
    MODERATE = 2
    SEVERE = 3


class ConflictLevel(Enum):
    NONE = 0
    DISAGREEMENT = 1
    HEATED = 2
    HOSTILE = 3


class DetectionType(Enum):
    TOXICITY = "toxicity"
    CONFLICT = "conflict"
    DOMAIN_SPECIFIC = "domain_specific"


# 向后兼容的别名
OffenseLevel = ToxicityLevel


@dataclass
class ContentAnalysis:
    """基础内容分析结果"""
    toxicity_level: ToxicityLevel
    toxicity_keywords: List[str]
    conflict_signals: List[str]
    domain_violations: List[str]
    confidence: float = 0.0


@dataclass
class ContextualAnalysis:
    """上下文分析结果"""
    escalation_risk: str  # 'low', 'medium', 'high'
    interaction_pattern: str  # 'normal', 'heated_exchange', 'bullying'
    participant_dynamics: Dict
    emotion_trend: str  # 'stable', 'rising', 'volatile'


@dataclass
class LLMAnalysis:
    """LLM增强分析结果"""
    toxicity_assessment: Dict
    conflict_assessment: Dict
    context_understanding: Dict
    confidence: float = 0.0


@dataclass
class InterventionDecision:
    """干预决策结果"""
    should_intervene: bool
    intervention_type: Optional[InterventionType] = None
    priority: str = 'normal'  # 'immediate', 'contextual', 'normal'
    reason: str = ''
    message: str = ''
    target_user: Optional[str] = None
    detection_source: str = ''  # 'toxicity', 'conflict', 'hybrid'
    confidence: float = 0.0


@dataclass
class InterventionResult:
    """保持向后兼容的干预结果"""
    should_intervene: bool
    intervention_type: InterventionType
    message: str
    reason: str
    offense_level: Optional[Union[ToxicityLevel, ConflictLevel]] = None
    target_user: Optional[str] = None
    via_llm: bool = False
    llm_confidence: Optional[float] = None
    llm_label: Optional[str] = None


class ContentAnalyzer:
    """内容分析器 - 基础分类检测"""
    
    def __init__(self):
        # 🔴 毒性词库 - 绝对不当言论
        self.toxicity_keywords = {
            ToxicityLevel.SEVERE: [
                '垃圾', '脑残', '智障', '滚蛋', '去死', '傻逼', '妈的', '操',
                '死妈', '你妈', '草泥马', '日你', '煞笔', '智商有问题', '脑子有病',
                '滚出足球圈', '没脑子', '弱智', '傻逼玩意', '臭傻逼'
            ],
            ToxicityLevel.MODERATE: [
                '废物', '闭嘴', '没资格', '不懂球', '小丑'
            ],
            ToxicityLevel.MILD: [
                '傻', '蠢', '笨'
            ]
        }
        
        # 🟡 冲突指示词 - 争论升级信号
        self.conflict_indicators = {
            'disagreement': ['不对', '错了', '胡说', '放屁', '扯淡'],
            'dismissive': ['别说了', '够了', '无语', '服了', '我不同意'],
            'escalation': ['你就你懂', '懂王', '你这', '什么鬼', '太离谱'],
            'personal_challenge': ['你懂个', '别说话', '闭嘴吧', '你懂球吗', '你最懂']
        }
        
        # ⚽ 足球领域特定词汇
        self.domain_specific = {
            'team_slur': [
                '巴狗', '皇马狗', '利物浦狗', '切尔西狗', '曼联狗', '阿森纳狗', 
                '热刺狗', '巴萨狗', '拜仁狗', '尤文狗', '米兰狗', '国米狗', 
                '多特狗', '马竞狗', '软脚虾', '菜鸡', '菜狗', '废柴'
            ],
            'player_insult': [
                '娜娜', '瓜秃', '内马滚', '姆巴佩滚', '哈兰德滚', '梅西滚', 'C罗滚'
            ],
            'fan_mockery': [
                '伪球迷', '云球迷', '皇屑', '狗马', '渣团'
            ]
        }
    
    def analyze_content(self, message: str) -> ContentAnalysis:
        """分析消息内容，返回基础分析结果"""
        message_lower = message.lower()
        
        # 检测毒性
        toxicity_level, toxicity_keywords = self._detect_toxicity(message_lower)
        
        # 检测冲突信号
        conflict_signals = self._detect_conflict_signals(message_lower)
        
        # 检测领域违规
        domain_violations = self._detect_domain_violations(message_lower)
        
        # 计算总体置信度
        confidence = self._calculate_confidence(toxicity_level, conflict_signals, domain_violations)
        
        return ContentAnalysis(
            toxicity_level=toxicity_level,
            toxicity_keywords=toxicity_keywords,
            conflict_signals=conflict_signals,
            domain_violations=domain_violations,
            confidence=confidence
        )
    
    def _detect_toxicity(self, message_lower: str) -> Tuple[ToxicityLevel, List[str]]:
        """检测毒性等级和关键词"""
        found_keywords = []
        max_level = ToxicityLevel.NONE
        
        for level, keywords in self.toxicity_keywords.items():
            for keyword in keywords:
                if keyword.lower() in message_lower:
                    found_keywords.append(keyword)
                    if level.value > max_level.value:
                        max_level = level
        
        return max_level, found_keywords
    
    def _detect_conflict_signals(self, message_lower: str) -> List[str]:
        """检测冲突信号"""
        signals = []
        for category, indicators in self.conflict_indicators.items():
            for indicator in indicators:
                if indicator.lower() in message_lower:
                    signals.append(f"{category}:{indicator}")
        return signals
    
    def _detect_domain_violations(self, message_lower: str) -> List[str]:
        """检测领域特定违规"""
        violations = []
        for category, terms in self.domain_specific.items():
            for term in terms:
                if term.lower() in message_lower:
                    violations.append(f"{category}:{term}")
        return violations
    
    def _calculate_confidence(self, toxicity_level: ToxicityLevel, 
                            conflict_signals: List[str], 
                            domain_violations: List[str]) -> float:
        """计算检测置信度"""
        confidence = 0.0
        
        if toxicity_level != ToxicityLevel.NONE:
            confidence += 0.3 + (toxicity_level.value * 0.2)
        
        if conflict_signals:
            confidence += min(0.3, len(conflict_signals) * 0.1)
        
        if domain_violations:
            confidence += min(0.2, len(domain_violations) * 0.05)
        
        return min(1.0, confidence)


class ToxicityDetector:
    """毒性检测器 - 专门处理有害言论"""
    
    def __init__(self, content_analyzer: ContentAnalyzer):
        self.content_analyzer = content_analyzer
        self.zero_tolerance_mode = os.getenv('TOXICITY_ZERO_TOLERANCE', 'true').lower() == 'true'
        self.immediate_severe = os.getenv('TOXICITY_IMMEDIATE_SEVERE', 'true').lower() == 'true'
    
    def should_intervene(self, analysis: ContentAnalysis) -> bool:
        """判断是否需要毒性干预"""
        if analysis.toxicity_level == ToxicityLevel.SEVERE:
            return True
        
        if analysis.toxicity_level == ToxicityLevel.MODERATE and self.zero_tolerance_mode:
            return True
        
        # 领域特定的严重违规也视为毒性
        severe_domain_violations = any('team_slur' in v or 'player_insult' in v 
                                     for v in analysis.domain_violations)
        if severe_domain_violations and analysis.toxicity_level != ToxicityLevel.NONE:
            return True
        
        return False
    
    def get_intervention_message(self, analysis: ContentAnalysis, target_user: str) -> str:
        """生成毒性干预消息"""
        if analysis.toxicity_level == ToxicityLevel.SEVERE:
            return f"@{target_user} 请避免使用攻击性言语，保持友好讨论环境。"
        elif analysis.toxicity_level == ToxicityLevel.MODERATE:
            return f"@{target_user} 注意用词，让我们保持理性交流。"
        else:
            return f"@{target_user} 建议用更友善的方式表达观点。"


class ConflictDetector:
    """冲突检测器 - 专门处理争论升级"""
    
    def __init__(self, content_analyzer: ContentAnalyzer):
        self.content_analyzer = content_analyzer
        self.escalation_threshold = int(os.getenv('CONFLICT_ESCALATION_THRESHOLD', '3'))
        self.proactive_mode = os.getenv('CONFLICT_MODE', 'proactive') == 'proactive'
    
    def analyze_escalation_risk(self, conversation_history: List[Dict]) -> ContextualAnalysis:
        """分析对话升级风险"""
        if len(conversation_history) < 2:
            return ContextualAnalysis(
                escalation_risk='low',
                interaction_pattern='normal',
                participant_dynamics={},
                emotion_trend='stable'
            )
        
        # 分析最近的交互模式
        recent_messages = conversation_history[-6:]
        
        # 检测情绪升级趋势
        emotion_scores = []
        participants = set()
        
        for msg in recent_messages:
            content_analysis = self.content_analyzer.analyze_content(msg.get('content', ''))
            
            # 情绪强度评分
            emotion_score = 0
            emotion_score += len(content_analysis.conflict_signals) * 0.2
            emotion_score += content_analysis.toxicity_level.value * 0.3
            emotion_score += len(content_analysis.domain_violations) * 0.1
            
            emotion_scores.append(emotion_score)
            participants.add(msg.get('user_id'))
        
        # 判断升级风险
        escalation_risk = self._assess_escalation_risk(emotion_scores)
        
        # 判断交互模式
        interaction_pattern = self._assess_interaction_pattern(recent_messages, participants)
        
        # 判断情绪趋势
        emotion_trend = self._assess_emotion_trend(emotion_scores)
        
        return ContextualAnalysis(
            escalation_risk=escalation_risk,
            interaction_pattern=interaction_pattern,
            participant_dynamics={'active_participants': len(participants)},
            emotion_trend=emotion_trend
        )
    
    def should_intervene(self, context_analysis: ContextualAnalysis) -> bool:
        """判断是否需要冲突干预"""
        if context_analysis.escalation_risk == 'high':
            return True
        
        if (context_analysis.escalation_risk == 'medium' and 
            context_analysis.interaction_pattern in ['heated_exchange', 'bullying']):
            return True
        
        if not self.proactive_mode:
            return False
        
        # 主动模式下的预防性干预
        if (context_analysis.escalation_risk == 'medium' and 
            context_analysis.emotion_trend == 'rising'):
            return True
        
        return False
    
    def get_intervention_type(self, context_analysis: ContextualAnalysis) -> InterventionType:
        """根据上下文选择干预类型"""
        if context_analysis.escalation_risk == 'high':
            return InterventionType.EMERGENCY_DEESCALATION
        elif context_analysis.interaction_pattern == 'heated_exchange':
            return InterventionType.CONFLICT_DEESCALATION
        else:
            return InterventionType.GENTLE_REDIRECT
    
    def get_intervention_message(self, context_analysis: ContextualAnalysis, 
                                llm_analyzer: Optional['LLMEnhancedAnalyzer'] = None,
                                room_id: str = '', conversation_history: List[Dict] = None) -> str:
        """生成冲突干预消息 - 优先使用LLM生成自然消息"""
        
        # 尝试使用LLM生成自然的冲突调节消息
        if llm_analyzer and llm_analyzer.enabled and conversation_history:
            try:
                # 构建简单的上下文
                context_str = "\n".join([
                    f"{msg.get('username', 'User')}: {msg.get('content', '')}" 
                    for msg in conversation_history[-4:]  # 只取最近4条消息
                ])
                
                # 简化的提示词
                prompt = f"""你是群聊助手Chime，请为以下足球讨论生成一句友好的调节消息。

对话内容：
{context_str}

要求：
1. 15-30字，语气温和友善
2. 像朋友间的劝说，避免说教
3. 可以用语气词（如～、呢、吧）
4. 引导回到理性足球讨论

只输出调节消息，不要解释："""
                
                response = llm_analyzer._call_llm(prompt)
                if response:
                    message = response.strip().strip('"\'')
                    if message and len(message) <= 40:
                        print(f"🤖 [冲突LLM] 生成成功: '{message}'")
                        return message
                        
            except Exception as e:
                print(f"🤖 [冲突LLM] 生成失败: {e}")
        
        # 回退到固定模板
        if context_analysis.escalation_risk == 'high':
            return "大家先暂停一下，让我们回到理性讨论的轨道上。"
        elif context_analysis.interaction_pattern == 'heated_exchange':
            return "讨论有点激烈，我们放平心态，尊重不同观点。"
        else:
            return "建议大家保持友好的讨论氛围。"
    
    def _generate_conflict_message_with_llm(self, llm_analyzer: 'LLMEnhancedAnalyzer',
                                          context_analysis: ContextualAnalysis,
                                          room_id: str, conversation_history: List[Dict]) -> Optional[str]:
        """使用LLM生成冲突调节消息"""
        if not conversation_history:
            return None
        
        # 构建上下文
        context_str = "\n".join([
            f"{msg.get('username', 'User')}: {msg.get('content', '')}" 
            for msg in conversation_history[-6:]  # 最近6条消息
        ])
        
        # 根据冲突情况选择提示词
        if context_analysis.escalation_risk == 'high':
            style = "紧急降温"
            tone = "坚定但温和"
            goal = "立即缓解激烈情绪，引导回归理性"
        elif context_analysis.interaction_pattern == 'heated_exchange':
            style = "友好调节"
            tone = "轻松友善"
            goal = "缓解争论气氛，促进理解"
        elif context_analysis.interaction_pattern == 'bullying':
            style = "保护干预"
            tone = "公正坚定"
            goal = "制止不当行为，维护讨论秩序"
        else:
            style = "轻柔提醒"
            tone = "温和建议"
            goal = "预防冲突升级"
        
        prompt = f"""你是群聊助手Chime，擅长化解冲突。请根据以下足球讨论情况，生成一句{style}的中文调节消息。

当前情况：
- 升级风险: {context_analysis.escalation_risk}
- 交互模式: {context_analysis.interaction_pattern}  
- 情绪趋势: {context_analysis.emotion_trend}

对话内容：
{context_str}

要求：
1. 语气{tone}，像朋友间的劝说
2. 目标：{goal}
3. 15-35字，简洁有效
4. 可以用轻度语气词（如～、呢、吧）
5. 结合足球话题，引导回到理性讨论
6. 避免说教口吻，要自然亲切

示例风格：
- 高风险："哎呀大家别急～咱们好好聊足球，理性一点更有意思"
- 激烈争论："讨论挺热烈的呢，不如各自说说支持的理由？"
- 轻度冲突："来来来，足球观点本来就多样，咱们心平气和地聊～"

只输出调节消息本身，不要解释。"""
        
        # 调用LLM
        try:
            response = llm_analyzer._call_llm(prompt)
            if response:
                # 清理响应
                message = response.strip()
                # 移除可能的引号
                if message.startswith('"') and message.endswith('"'):
                    message = message[1:-1]
                if message.startswith("'") and message.endswith("'"):
                    message = message[1:-1]
                
                # 应用内容净化
                message = self._sanitize_tone_for_conflict(message)
                
                if message and len(message) <= 50:  # 确保长度合理
                    print(f"🤖 [冲突LLM] 生成成功: '{message}'")
                    return message
                else:
                    print(f"🤖 [冲突LLM] 消息过长或为空: '{message}'")
            
        except Exception as e:
            print(f"🤖 [冲突LLM] 异常: {e}")
        
        return None
    
    def _sanitize_tone_for_conflict(self, text: str) -> str:
        """专门为冲突调节消息净化语气"""
        if not text:
            return ''
        
        s = str(text).strip()
        
        # 移除过于严厉的词汇
        harsh_words = ['警告', '严肃', '命令', '必须', '禁止', '不允许']
        for word in harsh_words:
            s = s.replace(word, '')
        
        # 移除重复标点
        s = re.sub(r'([，。！？!?～~])\1+', r'\1', s)
        
        # 清理开头多余标点
        s = re.sub(r'^[，。！？!?～~\s]+', '', s)
        
        # 确保友好结尾
        if s and not s.endswith(('～', '。', '！', '？', '呢', '吧', '哦')):
            if '?' in s or '？' in s:
                s = s.rstrip('.,，。') + '？'
            else:
                s = s.rstrip('.,，。') + '～'
        
        return s.strip()
    
    def _assess_escalation_risk(self, emotion_scores: List[float]) -> str:
        """评估升级风险"""
        if not emotion_scores:
            return 'low'
        
        avg_score = sum(emotion_scores) / len(emotion_scores)
        max_score = max(emotion_scores)
        
        if max_score > 0.8 or avg_score > 0.5:
            return 'high'
        elif max_score > 0.5 or avg_score > 0.3:
            return 'medium'
        else:
            return 'low'
    
    def _assess_interaction_pattern(self, messages: List[Dict], participants: set) -> str:
        """评估交互模式"""
        if len(participants) <= 1:
            return 'normal'
        
        if len(participants) == 2 and len(messages) >= 4:
            # 检测两人对线
            user_counts = {}
            for msg in messages:
                user_id = msg.get('user_id')
                user_counts[user_id] = user_counts.get(user_id, 0) + 1
            
            if max(user_counts.values()) >= 3:
                return 'heated_exchange'
        
        # 检测是否有集体针对某人的情况
        target_mentions = {}
        for msg in messages:
            content = msg.get('content', '').lower()
            for participant in participants:
                if f"@{participant}" in content or "你" in content:
                    target_mentions[participant] = target_mentions.get(participant, 0) + 1
        
        if target_mentions and max(target_mentions.values()) >= 3:
            return 'bullying'
        
        return 'normal'
    
    def _assess_emotion_trend(self, emotion_scores: List[float]) -> str:
        """评估情绪趋势"""
        if len(emotion_scores) < 3:
            return 'stable'
        
        # 比较前半段和后半段的平均分
        mid = len(emotion_scores) // 2
        early_avg = sum(emotion_scores[:mid]) / mid if mid > 0 else 0
        late_avg = sum(emotion_scores[mid:]) / (len(emotion_scores) - mid)
        
        if late_avg > early_avg + 0.2:
            return 'rising'
        elif abs(late_avg - early_avg) <= 0.1:
            return 'stable'
        else:
            return 'volatile'


class LLMEnhancedAnalyzer:
    """LLM增强分析器 - 处理复杂语境"""
    
    def __init__(self, api_key: str, base_url: str, model: str, timeout: float):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.enabled = bool(api_key)
    
    def get_enhanced_analysis(self, message: str, conversation_history: List[Dict]) -> Optional[LLMAnalysis]:
        """获取LLM增强分析"""
        if not self.enabled:
            return None
        
        try:
            prompt = self._build_analysis_prompt(message, conversation_history)
            response = self._call_llm(prompt)
            
            if response:
                return self._parse_llm_response(response)
        except Exception as e:
            print(f"🤖 [LLM分析] 失败: {e}")
        
        return None
    
    def _build_analysis_prompt(self, message: str, context: List[Dict]) -> str:
        """构建分析提示词"""
        context_str = "\n".join([
            f"{msg.get('username', 'User')}: {msg.get('content', '')}" 
            for msg in context[-5:]
        ])
        
        return f"""你是聊天内容分析专家。请分析以下足球讨论中的最新消息，明确区分毒性内容和冲突情况。

对话上下文：
{context_str}

最新消息：{message}

请按以下JSON格式返回分析结果：
{{
  "toxicity_assessment": {{
    "is_toxic": true/false,
    "toxicity_type": "personal_attack|hate_speech|profanity|none",
    "severity": "mild|moderate|severe",
    "confidence": 0.0-1.0
  }},
  "conflict_assessment": {{
    "is_conflictual": true/false,
    "conflict_type": "disagreement|escalation|hostility|none",
    "escalation_risk": "low|medium|high",
    "participants": ["user1", "user2"]
  }},
  "context_understanding": {{
    "intent": "aggressive|defensive|neutral|constructive",
    "emotional_tone": "angry|frustrated|dismissive|calm",
    "requires_intervention": true/false
  }}
}}

注意区分：
- 毒性内容：人身攻击、仇恨言论、脏话等绝对不当言论
- 冲突情况：观点分歧、争论升级、情绪化表达等相对性问题"""
    
    def _call_llm(self, prompt: str) -> Optional[str]:
        """调用LLM API"""
        try:
            import requests
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 300
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception as e:
            print(f"🤖 [LLM调用] 异常: {e}")
        
        return None
    
    def _parse_llm_response(self, response: str) -> LLMAnalysis:
        """解析LLM响应"""
        try:
            # 清理响应格式
            cleaned = response.strip()
            if cleaned.startswith('```json'):
                cleaned = cleaned[7:]
            if cleaned.startswith('```'):
                cleaned = cleaned[3:]
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            result = json.loads(cleaned)
            
            return LLMAnalysis(
                toxicity_assessment=result.get('toxicity_assessment', {}),
                conflict_assessment=result.get('conflict_assessment', {}),
                context_understanding=result.get('context_understanding', {}),
                confidence=result.get('toxicity_assessment', {}).get('confidence', 0.0)
            )
        except json.JSONDecodeError as e:
            print(f"🤖 [LLM解析] JSON错误: {e}")
            return LLMAnalysis(
                toxicity_assessment={}, 
                conflict_assessment={}, 
                context_understanding={},
                confidence=0.0
            )


class SmartInterventionEngine:
    """统一干预引擎 - 整合毒性检测和冲突检测"""

    def __init__(self):
        # === 初始化检测器组件 ===
        self.content_analyzer = ContentAnalyzer()
        self.toxicity_detector = ToxicityDetector(self.content_analyzer)
        self.conflict_detector = ConflictDetector(self.content_analyzer)
        
        # === LLM增强分析器 ===
        api_key = os.getenv('OPENAI_API_KEY', '')
        base_url = os.getenv('OPENAI_BASE_URL') or os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1')
        model = os.getenv('LLM_MODEL', 'gpt-4o-mini')
        timeout = float(os.getenv('LLM_TIMEOUT_SEC', '10.0'))
        
        # 保持向后兼容的属性
        self.llm_api_key = api_key
        self.llm_model = model
        self.llm_message_model = os.getenv('LLM_MESSAGE_MODEL', model)
        self.llm_base_url = base_url
        self.llm_timeout = timeout
        
        self.llm_analyzer = LLMEnhancedAnalyzer(api_key, base_url, model, timeout) if api_key else None
        
        # === 检测配置 ===
        self.detection_mode = os.getenv('DETECTION_MODE', 'hybrid').lower()  # 'toxicity', 'conflict', 'hybrid'
        self.llm_enabled = bool(api_key) and os.getenv('LLM_ENABLED', 'true').lower() == 'true'
        # 兼容老配置项：是否启用基于LLM的干预文案生成（默认与llm_enabled一致，可用 LLM_INTERVENTION_ENABLED 覆盖）
        self.llm_intervention_enabled = (
            os.getenv('LLM_INTERVENTION_ENABLED', 'true').lower() == 'true'
        ) and self.llm_enabled
        # LLM连接状态（启动自检和运行期更新时写入）
        self.llm_connection_status = {
            'toxicity': False,
            'intervention': False,
        }
        self.llm_confidence_threshold = float(os.getenv('LLM_CONFIDENCE_THRESHOLD', '0.7'))
        
        # === 用户行为追踪 ===
        self.user_last_message_time = {}
        self.user_message_count = defaultdict(int)
        self.user_silence_warnings = defaultdict(int)
        self.user_last_reminder_time = {}

        # === 房间上下文缓存 ===
        self.room_recent_messages = defaultdict(lambda: deque(maxlen=20))
        self.room_conflict_level = defaultdict(int)
        self.room_topic_keywords = defaultdict(set)
        self.room_last_intervention_ts = defaultdict(float)
        self.room_last_agenda_transition = defaultdict(float)
        
        # === 行为检测参数 ===
        self.silence_threshold = int(os.getenv('SILENCE_THRESHOLD', '60'))
        self.global_cooldown_seconds = int(os.getenv('GLOBAL_COOLDOWN', '30'))
        self.agenda_transition_threshold = int(os.getenv('AGENDA_TRANSITION_THRESHOLD', '30'))
        self.agenda_transition_cooldown = int(os.getenv('AGENDA_TRANSITION_COOLDOWN', '60'))
        
        # === 干预模板 ===
        self.tone = os.getenv('INTERVENTION_TONE', 'warm').lower()
        self.invitation_templates = [
            "@{user}，你怎么看？",
            "@{user}，你有什么想法吗？",
            "@{user}，想听听你的观点",
            "大家都说说看，@{user} 你觉得呢？"
        ]

        self.invitation_templates_warm = [
            "@{user}，你觉得呢？",
            "@{user}，也来聊聊吧～",
            "@{user}，你有什么想法？",
            "@{user}，想听听你的看法～",
            "@{user}，期待你的见解！"
        ]

        # === 足球话题相关 ===
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

        self.football_on_topic_ratio = float(os.getenv('FOOTBALL_ON_TOPIC_RATIO', '0.2'))
        
        # === 预设话题库 ===
        self.football_agenda_topics = [
            "新援表现", "转会传闻", "战术分析", "历史对战", "球员状态",
            "教练策略", "联赛排名", "欧战前景", "青训发展", "俱乐部文化",
            "经典比赛", "球迷文化", "未来展望", "赛季总结", "伤病情况"
        ]
        
        # === 话题转换模板 ===
        self.agenda_transition_templates = [
            "大家聊聊新的话题吧～刚才关于{current_topic}的讨论很精彩！",
            "现在来说说{next_topic}怎么样？",
            "刚才讨论得很热烈，我们聊聊{next_topic}吧！",
            "换个角度，大家对{next_topic}有什么看法？",
            "既然刚才聊了{current_topic}，那{next_topic}你们怎么看？",
            "这个话题差不多了，我们聊聊{next_topic}怎么样？",
            "让我们换个角度，{next_topic}大家怎么看？",
            "顺着刚才的话题，{next_topic}也值得探讨一下。"
        ]
        
        self.icebreaker_theme = os.getenv(
            'ICEBREAKER_THEME',
            '今天的讨论题目是——哪个球队是全世界最好的球队？他们有最伟大的足球哲学吗？'
        ).strip()
        
        # === 消息去重和节流 ===
        self.recent_intervention_messages = defaultdict(lambda: deque(maxlen=10))
        self.message_dedup_window_seconds = 90
        self.user_last_conflict_reminder_ts = {}
        self.per_user_conflict_throttle_seconds = 30
        
        # === 活跃讨论保护 ===
        self.active_discussion_window_seconds = 120
        self.active_discussion_min_unique_users = 2
        self.active_discussion_min_msg_per_minute = 1.5
        
        # === 话题拉回冷却 ===
        self.room_last_generic_pullback_ts = {}
        self.generic_pullback_cooldown = int(os.getenv('GENERIC_PULLBACK_COOLDOWN', '90'))
        self.room_last_topic_pullback_ts = {}
        self.topic_pullback_cooldown = int(os.getenv('TOPIC_PULLBACK_COOLDOWN', '120'))

        # === 结构化引导类消息共享冷却（话题拉回 / 议程过渡 / 轮次引导） ===
        self.room_last_guidance_ts = {}
        self.guidance_cooldown_seconds = int(os.getenv('GUIDANCE_COOLDOWN', '180'))
        
        # === 最小检测门槛 ===
        self.min_rounds_for_conflict = int(os.getenv('MIN_CONFLICT_ROUNDS', '3'))
        self.min_messages_for_conflict = self.min_rounds_for_conflict * 2
        
        # === LLM相关缓存 ===
        self.llm_result_cache = {}
        self.llm_cache_ttl = 120
        self.topic_detection_cache = {}
        self.topic_cache_ttl = 60
        
        # === 初始化完成日志 ===
        print(f"🚀 [干预引擎] 初始化完成")
        print(f"   🔍 检测模式: {self.detection_mode}")
        print(f"   🤖 LLM启用: {self.llm_enabled}")
        print(f"   🎯 毒性零容忍: {self.toxicity_detector.zero_tolerance_mode}")
        print(f"   ⚡ 冲突主动模式: {self.conflict_detector.proactive_mode}")
        
        if self.llm_enabled:
            self._test_llm_connection_on_start()

    def _test_llm_connection_on_start(self):
        """测试LLM连接状态"""
        if not self.llm_analyzer:
            print("⚠️  LLM分析器未启用 (无API密钥)")
            return
        
        try:
            print("🔍 测试LLM连接...")
            test_analysis = self.llm_analyzer.get_enhanced_analysis("测试", [])
            if test_analysis:
                print("✅ LLM连接测试成功")
            else:
                print("⚠️  LLM连接测试失败 - 无响应")
        except Exception as e:
            print(f"❌ LLM连接测试失败: {e}")

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
        """测试LLM连接状态"""
        if not self.llm_analyzer:
            print("⚠️  LLM分析器未启用 (无API密钥)")
            return
        
        try:
            print("🔍 测试LLM连接...")
            test_analysis = self.llm_analyzer.get_enhanced_analysis("测试", [])
            if test_analysis:
                print("✅ LLM连接测试成功")
            else:
                print("⚠️  LLM连接测试失败 - 无响应")
        except Exception as e:
            print(f"❌ LLM连接测试失败: {e}")

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

    def _sanitize_tone(self, text: Optional[str]) -> str:
        """对 LLM/模板输出做语气与内容净化，避免前端渲染问题与不当语气。
        - 去除轻佻口吻与表情（如 哈哈/呵呵/emoji）
        - 清理重复标点与异常标点（如 ，， / 。。 / ？！?!）
        - 过滤常见侮辱/挑衅词片段，确保不会复述用户的不当用语
        - 修剪首尾空白
        """
        if not text:
            return ''
        s = str(text)

        try:
            # 1) 去除轻佻用语与常见表情符
            playful_tokens = [
                '哈哈', '呵呵', '嘿嘿', '哈～', '哈呀',
                '😂', '🤣', '😉', '😊', '😅', '🙂', '😄', '🙃', '😜', '😝', '😆', '😸', '😺'
            ]
            for tok in playful_tokens:
                s = s.replace(tok, '')

            # 2) 过滤常见侮辱/挑衅词片段（最小侵入，只做静态替换）
            rude_tokens = [
                '你懂个屁', '傻逼', '傻B', '傻b', '傻x', '傻X', '垃圾', '滚', '废物', '闭嘴', '弱智', '狗东西',
                'sb', 'SB', 's b', 'S B', 'bb', '黑哨', '你瞎了吧'
            ]
            for tok in rude_tokens:
                s = s.replace(tok, '')

            # 3) 归一化重复标点：连续同类标点压缩为1个
            #   支持中英文常见标点：，。！？!?,～~；;：:
            s = re.sub(r'([，。！？!\?～~；;：:])\1+', r'\1', s)

            # 4) 清理开头多余标点与空白
            s = re.sub(r'^[，。！？!\?～~；;：:\s]+', '', s)

            # 5) 修正易见的「，。」顺序错误
            s = s.replace('，。', '。').replace('。。', '。').replace('，，', '，')

            # 6) 压缩多余空白
            s = re.sub(r'\s+', ' ', s).strip()

            # 7) 太短时补一处礼貌语尾（避免空字符串）
            if not s:
                s = '也来聊聊你的看法吧'
        except Exception:
            # 容错：任何异常都返回原文，避免阻断流程
            return text

        return s

    def _llm_generate_message(self, kind: str, room_id: str, **kwargs) -> Optional[str]:
        """生成简短、温和、像人的中文文案。kind in {silence, turn_taking, topic_pullback, agenda, emergency_brake, gentle_conflict, gentle_toxic}。"""
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
        elif kind == 'gentle_conflict':
            # 温柔冲突提醒：不复述冒犯词，结尾落在具体足球问题
            user = kwargs.get('user') or kwargs.get('target') or '大家'
            prompt = (
                "你是群聊助手Chime。基于以下对话，生成一句温柔、克制、非指责的提醒，"
                "用中文引导@" + str(user) + " 回到足球观点本身，并在句末给一个具体可回答的问题，"
                "问题需围绕'最伟大的球队/足球哲学'，例如传控/反击/青训、代表比赛等。"
                "要求：1) 不复述敏感/冒犯词 2) 不用'警告/严肃'等词 3) 20-40字 4) 口吻自然像朋友。\n"
                f"对话内容：\n{convo}"
            )
        elif kind == 'gentle_toxic':
            # 温柔毒性提醒：基于触发消息，输出极简友好提醒，不复述冒犯词
            user = kwargs.get('user') or kwargs.get('target') or '大家'
            offending_terms = kwargs.get('offending_terms') or []
            snippet = (kwargs.get('original_content') or '')[:30]
            prompt = (
                "你是群聊助手Chime。根据下面触发的这条消息，生成一句非常简短、温柔的中文提醒，"
                "提醒对方避免使用可能冒犯的用语或外号，语气友好，像朋友。"
                "要求：1) 不能复述冒犯词 2) 不使用'警告/严肃'等词 3) 12-24字 4) 可用轻度语气词。"
                f"@对象：{user}\n"
                f"触发消息片段：{snippet}\n"
                f"可能的冒犯词（不要复述，仅参考判断）：{','.join(offending_terms)}\n"
                "只输出提醒句子本身。"
            )
        elif kind == 'emergency_brake':
            # 面向激烈冲突的"紧急刹车"，禁止玩笑语气，要求转向数据视角
            messages = list(self.room_recent_messages.get(room_id, []))[-10:]
            convo = "\n".join([f"{m.get('username')}: {m.get('content')}" for m in messages])
            target_users = kwargs.get('target_users', [])
            tag = ("@" + " @".join(target_users)) if target_users else "大家"
            prompt = (
                "你是群聊助手Chime。现在对话正在激烈争吵，请立刻用严肃、克制、明确的中文发一条'紧急刹车'消息。\n"
                "要求：\n"
                "1) 不使用任何玩笑、调侃、拟声（如 哈哈、嘿、表情）。\n"
                "2) 先叫停（如：先停一下/请暂停一下），再转数据视角（射门、xG、控球、关键传球等）。\n"
                "3) 给出明确的下一步：每人≤1句话给出结论+1条数据依据（可贴来源）。\n"
                "4) 字数20-40字，口吻中立且不带评价。\n"
                f"对象：{tag}\n"
                f"对话：\n{convo}"
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
                        # 统一使用服务端净化逻辑，去除开头逗号/轻佻口吻/侮辱词/重复标点
                        result = self._sanitize_tone(text)
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

    def _is_discouraging_offense(self, content: str) -> bool:
        """判断句子是否是在劝阻/避免使用冒犯措辞，而非主动使用。
        例如："先别用××这个词"、"不要说外号"、"别用那个称呼"。"""
        if not content:
            return False
        s = content.strip().lower()
        discourage_patterns = [
            "别用", "不要用", "先别用", "别说", "不要说", "别叫", "不要叫", "不要提", "别提", "别带", "不要带"
        ]
        if any(p in s for p in discourage_patterns):
            return True
        return False

    def _classify_offense_bucket(self, message_lower: str,
                                  llm_label: Optional[str] = None,
                                  offending_terms: Optional[List[str]] = None) -> Optional[str]:
        """将毒性/冲突语句归入固定的短提醒桶。
        返回: one of {banter_nick, denigrate, extreme_negative, insult_label, escalation}
        """
        offending_terms = offending_terms or []
        text = message_lower or ""
        check_any = lambda words: any(w in text for w in words) or any(w in (" ".join(offending_terms)) for w in words)

        # 冲突升级提示
        if check_any(['闭嘴', '没资格', '不懂球']):
            return 'escalation'
        # 侮辱/歧视性标签
        if check_any(['小丑', '废物', '垃圾', '智障', '脑残', '傻逼']):
            return 'insult_label'
        # 极端负面情绪
        if check_any(['最讨厌', '恶心', '滚']):
            return 'extreme_negative'
        # 拉踩贬低
        if check_any(['拉踩', '狂妄自大', '单场论']):
            return 'denigrate'
        # 烂梗/外号
        if check_any(['烂梗', '外号', '娜娜', '胖虎']):
            return 'banter_nick'
        # 结合llm_label兜底
        if llm_label:
            if 'personal_attack' in llm_label or 'profanity' in llm_label:
                return 'insult_label'
            if 'team_slur' in llm_label or 'player_insult' in llm_label:
                return 'banter_nick'
            if 'subtle_mockery' in llm_label:
                return 'denigrate'
        return None

    def _compose_simple_toxic_reminder(self, room_id: str, target_username: str,
                                       offending_terms: Optional[List[str]] = None,
                                       original_content: Optional[str] = None) -> str:
        """生成极简的毒性提醒文案；LLM失败或过长则回退到固定短句。"""
        room_id = str(room_id)
        offending_terms = offending_terms or []
        llm_msg = self._llm_generate_message(
            'gentle_toxic', room_id,
            user=target_username,
            offending_terms=offending_terms,
            original_content=original_content or ''
        )
        candidate = self._sanitize_tone(llm_msg or '')
        # 过长或为空则回退到固定短句
        fallback_pool = [
            f"@{target_username} 请避免使用可能冒犯的外号～",
            f"@{target_username} 咱们语气平和一点哦～",
            f"@{target_username} 请用客观表达，我们聊聊具体观点～"
        ]
        if not candidate or len(candidate) > 26:
            return random.choice(fallback_pool)
        return candidate

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
        
        if not (self.llm_enabled and self.llm_api_key):
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

    def _is_on_topic_football(self, room_id: str, window: int = 5) -> bool:
        """判断最近 window 条消息中，是否仍主要在聊"足球"。
        优先使用GPT智能检测，回退到关键词检测。
        """
        room_id = str(room_id)  # 确保是字符串类型
        recent_messages = list(self.room_recent_messages.get(room_id, []))
        if not recent_messages:
            print(f"🔍 足球话题检测: 无消息历史")
            return False
        
        # 仅取非管理员的最近 window 条消息
        non_admin_messages = [m for m in recent_messages if not self._is_admin_user(str(m.get('user_id')))]
        subset = non_admin_messages[-max(1, window):]
        
        # 优先使用GPT智能检测（仅作为条件之一，不单独决定偏题）
        gpt_result = self._llm_detect_football_topic(subset)
        if gpt_result is not None:
            print(f"🤖 [GPT话题检测] 结果: {gpt_result}")
        
        # 关键词占比
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
        
        # 优先：活跃讨论且关键词占比达标 → 视为在题内，避免误触发
        try:
            is_active = self._is_active_discussion(room_id)
        except Exception:
            is_active = False
        if total >= 3 and ratio >= self.football_on_topic_ratio and is_active:
            return True

        # 同一窗口内若检测到明显冲突，避免误判为跑题（让上层冲突逻辑先处理）
        try:
            conflict_hits = sum(1 for m in subset if self._is_conflict_message(m.get('content', '')))
            if conflict_hits >= 2:
                return True
        except Exception:
            pass

        # 稳健判定：仅当同时满足 GPT 判定为 False 且 关键词占比低于阈值（且消息数≥3）时，认为偏题
        if total >= 3 and (gpt_result is False) and (ratio < self.football_on_topic_ratio):
            return False

        # 其他情况一律视为在题内
        return True

    def _is_generic_chitchat(self, content: str) -> bool:
        """检测是否为与足球无关的泛聊词（简单关键词）"""
        try:
            text = (content or '').lower()
        except Exception:
            text = (content or '').strip().lower()
        generic_keywords = [
            # 饮食
            '吃', '吃饭', '晚饭', '早餐', '午饭', '中饭', '饭', '外卖', '饿', '好饿',
            '面', '面条', '泡面', '炒面', '拉面', '米饭', '米线', '馄饨', '饺子', '香菜', '奶茶', '咖啡', '茶', '水果',
            # 轻松语气
            '哈哈', '哈哈哈', 'hhh', 'lol',
            # 日常
            '上班', '下班', '工作', '学习', '作业', '加班',
            # 娱乐/其它
            '电影', '音乐', '游戏', '追剧', '天气', '旅游', '逛街'
        ]
        # 过滤掉包含明显足球词的内容
        if any(k in text for k in self.football_keywords):
            return False
        return any(k in text for k in generic_keywords)

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


    def _compose_topic_pullback(self, room_id: str, reason: str = "off_topic") -> str:
        """统一"提醒+总结+话题引导"的偏题提醒文案：
        - 1-2句客观小结（不评价输赢，不复述冒犯词）
        - 收束到"最伟大的球队/足球哲学"的具体问题
        """
        room_id = str(room_id)
        summary = self._summarize_recent_discussion(room_id, window=6) or (self._extract_current_topic(room_id) or "刚才的话题")
        next_topic = self._get_next_topic_suggestion(room_id, summary) or "足球哲学"
        msg = (
            f"稍作提醒：讨论有点发散。小结一下：{summary}。"
            f"回到主题——若从'足球哲学'看，你认为什么因素更关键：传控体系、反击效率，还是青训输血？"
            f"各自举一场你心中的代表作，说明为什么它能代表'最伟大的球队'。"
        )
        return self._sanitize_tone(msg)

    def _topic_cooldown_ok(self, room_id: str) -> bool:
        room_id = str(room_id)
        last_ts = self.room_last_topic_pullback_ts.get(room_id, 0)
        import time as _t
        return (_t.time() - last_ts) >= self.topic_pullback_cooldown

    def _mark_topic_pullback(self, room_id: str):
        room_id = str(room_id)
        import time as _t
        self.room_last_topic_pullback_ts[room_id] = _t.time()

    def _shared_guidance_cooldown_ok(self, room_id: str) -> bool:
        """话题拉回/议程过渡/轮次引导共享冷却，避免短时多次引导刷屏。"""
        room_id = str(room_id)
        last_ts = self.room_last_guidance_ts.get(room_id, 0)
        import time as _t
        return (_t.time() - last_ts) >= self.guidance_cooldown_seconds

    def _mark_shared_guidance(self, room_id: str):
        room_id = str(room_id)
        import time as _t
        self.room_last_guidance_ts[room_id] = _t.time()

    def _summarize_recent_discussion(self, room_id: str, window: int = 6) -> str:
        """从最近若干条非管理员消息中提炼1-2句客观小结。
        尽量抓取常见球队/概念关键词，避免复述争执性/冒犯性措辞。"""
        room_id = str(room_id)
        recent = [m for m in list(self.room_recent_messages.get(room_id, [])) if not self._is_admin_user(str(m.get('user_id')))]
        if not recent:
            return "刚才的话题"
        subset = [m.get('content', '') for m in recent[-max(3, window):] if m.get('content')]
        text = " \n".join(subset).lower()
        # 轻量关键词集合（可按需扩展）
        teams = ["皇马", "皇家马德里", "巴萨", "巴塞罗那", "曼城", "拜仁", "利物浦", "AC米兰", "国际米兰", "尤文", "阿森纳", "切尔西"]
        concepts = ["传控", "反击", "哲学", "统治力", "逆转", "青训", "欧冠", "联赛", "防守", "进攻"]
        hits = []
        for t in teams:
            if t in text:
                hits.append(t)
        for c in concepts:
            if c in text:
                hits.append(c)
        hits = list(dict.fromkeys(hits))[:4]
        if hits:
            # 构造客观小结句式
            joined = "、".join(hits)
            return f"大家提到了 {joined} 等角度"
        # 兜底：用最近一句非空内容抽象化
        last = subset[-1].strip()
        last = re.sub(r"[，。！？,.!]{2,}", "，", last)
        last = re.sub(r"@\w+", "", last)
        last = self._sanitize_tone(last)
        # 避免在小结中回显可能的冒犯词，若净化后为空或仍含疑似词，退回通用描述
        if not last or any(k in last for k in ['傻', 'sb', '黑哨', '滚', '弱智']):
            return "大家刚才围绕球队与比赛角度展开"
        return f"大家提到了 {last[:8]} 等角度"

    def analyze_message(self, room_id: str, user_id: str, username: str, 
                       message_content: str, gender: str = 'unknown') -> Optional[InterventionResult]:
        """统一消息分析入口 - 集成毒性检测和冲突检测"""
        
        # 确保房间ID和用户ID是字符串类型
        room_id = str(room_id)
        user_id = str(user_id)
        current_time = time.time()
        
        print(f"🔍 [统一分析] 分析消息: [{username}] {message_content[:30]}...")
        
        # 更新用户状态和消息历史
        self._update_user_state(room_id, user_id, username, message_content, gender, current_time)
        
        # 获取对话历史
        conversation_history = list(self.room_recent_messages.get(room_id, []))
        
        # === 🔴 第一层：基础内容分析 ===
        content_analysis = self.content_analyzer.analyze_content(message_content)
        print(f"🔍 [内容分析] 毒性等级: {content_analysis.toxicity_level.name}, 冲突信号: {len(content_analysis.conflict_signals)}, 置信度: {content_analysis.confidence:.2f}")
        
        # === 🟡 第二层：上下文分析 ===
        context_analysis = self.conflict_detector.analyze_escalation_risk(conversation_history)
        print(f"🔍 [上下文分析] 升级风险: {context_analysis.escalation_risk}, 交互模式: {context_analysis.interaction_pattern}")
        
        # === 🤖 第三层：LLM增强分析（可选）===
        llm_analysis = None
        if self.llm_enabled and self._should_use_llm_analysis(content_analysis, context_analysis):
            llm_analysis = self.llm_analyzer.get_enhanced_analysis(message_content, conversation_history)
            if llm_analysis:
                print(f"🤖 [LLM分析] 毒性: {llm_analysis.toxicity_assessment.get('is_toxic', False)}, 冲突: {llm_analysis.conflict_assessment.get('is_conflictual', False)}")
        
        # === 🎯 决策融合 ===
        intervention_decision = self._make_intervention_decision(
            content_analysis, context_analysis, llm_analysis, 
            room_id, user_id, username, current_time, message_content
        )
        
        if intervention_decision.should_intervene:
            print(f"✅ [决策结果] 需要干预: {intervention_decision.intervention_type.value}, 优先级: {intervention_decision.priority}")
            # 全通路启用房间级去重与全局冷却
            if not self._is_duplicate_message(room_id, intervention_decision.message):
                self._record_intervention_message(room_id, intervention_decision.message)
                self.room_last_intervention_ts[room_id] = current_time
                return self._convert_to_intervention_result(intervention_decision)
            else:
                print("⏸️ [去重] 干预消息重复，跳过发送")
                return None
        
        # === 其他检测（沉默、议程过渡等）===
        other_result = self._check_other_interventions(room_id, current_time)
        if other_result:
            return other_result
        
        print(f"✅ [决策结果] 无需干预")
        return None
    
    def _update_user_state(self, room_id: str, user_id: str, username: str, 
                          message_content: str, gender: str, current_time: float):
        """更新用户状态和消息历史"""
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
        
    def _should_use_llm_analysis(self, content_analysis: ContentAnalysis, 
                                context_analysis: ContextualAnalysis) -> bool:
        """判断是否需要LLM增强分析"""
        # 复杂情况下启用LLM
        if content_analysis.confidence < 0.6:  # 基础分析置信度低
            return True
        if context_analysis.escalation_risk == 'high':  # 高风险情况
            return True
        if content_analysis.toxicity_level == ToxicityLevel.MODERATE:  # 中等毒性需要确认
            return True
        if len(content_analysis.conflict_signals) >= 2:  # 多个冲突信号
            return True
        return False
    
    def _make_intervention_decision(self, content_analysis: ContentAnalysis,
                                  context_analysis: ContextualAnalysis,
                                  llm_analysis: Optional[LLMAnalysis],
                                  room_id: str, user_id: str, username: str,
                                  current_time: float,
                                  message_content: str) -> InterventionDecision:
        """统一干预决策逻辑"""
        
        # === 🔴 优先级1：毒性检测（立即处理）===
        if self.detection_mode in ['toxicity', 'hybrid']:
            if self.toxicity_detector.should_intervene(content_analysis):
                # 检查节流
                if not self._is_user_throttled(room_id, user_id, current_time, 'toxicity'):
                    return InterventionDecision(
                        should_intervene=True,
                        intervention_type=InterventionType.TOXICITY_WARNING,
                        priority='immediate',
                        reason=f'检测到{content_analysis.toxicity_level.name}级毒性内容',
                        message=self.toxicity_detector.get_intervention_message(content_analysis, username),
                        target_user=username,
                        detection_source='toxicity',
                        confidence=content_analysis.confidence
                    )
        
        # LLM毒性检测补充
        if llm_analysis and llm_analysis.toxicity_assessment.get('is_toxic'):
            severity = llm_analysis.toxicity_assessment.get('severity', 'mild')
            confidence = llm_analysis.toxicity_assessment.get('confidence', 0.0)
            
            if confidence >= self.llm_confidence_threshold and severity in ['moderate', 'severe']:
                if not self._is_user_throttled(room_id, user_id, current_time, 'toxicity'):
                    return InterventionDecision(
                        should_intervene=True,
                        intervention_type=InterventionType.TOXICITY_WARNING,
                        priority='immediate',
                        reason=f'LLM检测到{severity}级毒性内容 (置信度: {confidence:.2f})',
                        message=f"@{username} 请注意用词，保持友好讨论环境。",
                        target_user=username,
                        detection_source='llm_toxicity',
                        confidence=confidence
                    )
        
        # === 🟡 优先级2：冲突检测（上下文相关）===
        if self.detection_mode in ['conflict', 'hybrid']:
            if self.conflict_detector.should_intervene(context_analysis):
                # 仅允许“当前或最近两条消息”触发的冲突进入（避免误报）
                if not self._recent_conflict_triggered(room_id, window=2):
                    return InterventionDecision(should_intervene=False)
                # 检查冷却
                if not self._is_global_cooldown_active(room_id, current_time):
                    # 优先尝试定向、温和的短提醒
                    targeted = self._check_conflict_intervention(room_id, user_id, message_content, username)
                    if targeted and targeted.should_intervene:
                        return InterventionDecision(
                            should_intervene=True,
                            intervention_type=targeted.intervention_type,
                            priority='contextual',
                            reason=targeted.reason or f'检测到冲突升级: {context_analysis.escalation_risk}风险, {context_analysis.interaction_pattern}模式',
                            message=targeted.message,
                            detection_source='conflict',
                            confidence=0.8
                        )
                    # 否则回退到上下文型调解消息
                    intervention_type = self.conflict_detector.get_intervention_type(context_analysis)
                    conflict_message = self.conflict_detector.get_intervention_message(
                        context_analysis, 
                        llm_analyzer=self.llm_analyzer,
                        room_id=room_id,
                        conversation_history=list(self.room_recent_messages.get(room_id, []))
                    )
                    return InterventionDecision(
                        should_intervene=True,
                        intervention_type=intervention_type,
                        priority='contextual',
                        reason=f'检测到冲突升级: {context_analysis.escalation_risk}风险, {context_analysis.interaction_pattern}模式',
                        message=conflict_message,
                        detection_source='conflict',
                        confidence=0.8
                    )
        
        # LLM冲突检测补充
        if llm_analysis and llm_analysis.conflict_assessment.get('is_conflictual'):
            escalation_risk = llm_analysis.conflict_assessment.get('escalation_risk', 'low')
            if escalation_risk in ['medium', 'high']:
                if not self._is_global_cooldown_active(room_id, current_time):
                    return InterventionDecision(
                        should_intervene=True,
                        intervention_type=InterventionType.CONFLICT_DEESCALATION,
                        priority='contextual',
                        reason=f'LLM检测到{escalation_risk}级冲突风险',
                        message="讨论有点激烈，我们放平心态，尊重不同观点。",
                        detection_source='llm_conflict',
                        confidence=llm_analysis.confidence
                    )
        
        # === ✅ 无需干预 ===
        return InterventionDecision(should_intervene=False)
    
    def _is_user_throttled(self, room_id: str, user_id: str, current_time: float, 
                          intervention_type: str) -> bool:
        """检查用户是否在节流期内"""
        throttle_key = f"{room_id}_{user_id}_{intervention_type}"
        last_time = self.user_last_conflict_reminder_ts.get(throttle_key, 0)
        
        if current_time - last_time < self.per_user_conflict_throttle_seconds:
            return True
        
        # 更新节流时间
        self.user_last_conflict_reminder_ts[throttle_key] = current_time
        return False
    
    def _is_global_cooldown_active(self, room_id: str, current_time: float) -> bool:
        """检查全局冷却是否激活"""
        last_intervention = self.room_last_intervention_ts.get(room_id, 0)
        return current_time - last_intervention < self.global_cooldown_seconds
    
    def _convert_to_intervention_result(self, decision: InterventionDecision) -> InterventionResult:
        """将决策转换为兼容的干预结果"""
        # 映射offense_level
        offense_level = None
        if 'toxicity' in decision.detection_source:
            if 'severe' in decision.reason.lower():
                offense_level = ToxicityLevel.SEVERE
            elif 'moderate' in decision.reason.lower():
                offense_level = ToxicityLevel.MODERATE
            else:
                offense_level = ToxicityLevel.MILD
        elif 'conflict' in decision.detection_source:
            if 'high' in decision.reason.lower():
                offense_level = ConflictLevel.HOSTILE
            elif 'medium' in decision.reason.lower():
                offense_level = ConflictLevel.HEATED
            else:
                offense_level = ConflictLevel.DISAGREEMENT
        else:
            offense_level = ToxicityLevel.MILD
        
        return InterventionResult(
            should_intervene=decision.should_intervene,
            intervention_type=decision.intervention_type,
            message=decision.message,
            reason=decision.reason,
            offense_level=offense_level,
            target_user=decision.target_user,
            via_llm='llm' in decision.detection_source,
            llm_confidence=decision.confidence if 'llm' in decision.detection_source else None,
            llm_label=decision.detection_source
        )
    
    def _check_other_interventions(self, room_id: str, current_time: float) -> Optional[InterventionResult]:
        """检查其他类型的干预（沉默、议程过渡等）"""
        # 检查全局冷却
        if self._is_global_cooldown_active(room_id, current_time):
            return None
        
        # 沉默检测
        if not self._is_active_discussion(room_id):
            silence_result = self._check_silence_intervention(room_id)
        if silence_result and silence_result.should_intervene:
            if not self._is_duplicate_message(room_id, silence_result.message):
                self._record_intervention_message(room_id, silence_result.message)
                self.room_last_intervention_ts[room_id] = current_time
                return silence_result
        
        # 议程过渡检测
        agenda_result = self._check_agenda_transition(room_id)
        if agenda_result and agenda_result.should_intervene:
            if not self._is_duplicate_message(room_id, agenda_result.message):
                self._record_intervention_message(room_id, agenda_result.message)
                self.room_last_intervention_ts[room_id] = current_time
                return agenda_result
        
        # 结构引导
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
        self, room_id: str, user_id: str, message_content: str, username: str,
        count_violation: bool = True
    ) -> Optional[InterventionResult]:

        print(f"🔍 [冲突检测] 分析消息: '{message_content}' from {username}")

        # —— 辅助：非攻击性的应和/笑声类发言，避免误归责 ——
        def _is_acknowledgement(text: str) -> bool:
            try:
                t = (text or '').strip().lower()
            except Exception:
                t = (text or '').strip()
            if not t:
                return False
            ack_tokens = [
                '哈哈', '哈哈哈', 'hhhh', 'hhh', 'lol', '同意', '赞同', 'ok', '好的', '嗯', '嗯嗯', '啊这', '有点意思'
            ]
            # 短且仅含这些词的，视为非攻击性应和
            if len(t) <= 20 and any(tok in t for tok in ack_tokens):
                # 不包含明显侮辱词
                return self._detect_offense_level(t) is None
            return False

        # —— 辅助：从最近消息中按"冒犯关键词/强度"回溯真正的冒犯者 ——
        def _resolve_offender_from_recent(room_id_str: str, offending_terms: Optional[list] = None, lookback: int = 10) -> Optional[dict]:
            msgs = list(self.room_recent_messages.get(room_id_str, []))
            if not msgs:
                return None
            candidates = list(reversed([m for m in msgs[-lookback:] if not self._is_admin_user(str(m.get('user_id')))]))
            # 1) 优先：匹配 LLM 抽取的 offending_terms
            if offending_terms:
                lowered_terms = [str(x).lower() for x in offending_terms if isinstance(x, str)]
                for m in candidates:
                    c = (m.get('content') or '').lower()
                    if any(term in c for term in lowered_terms):
                        return {'user_id': str(m.get('user_id')), 'username': m.get('username')}
            # 2) 次优：按本地强度（SEVERE/MODERATE）回溯
            for m in candidates:
                lvl = self._detect_offense_level(m.get('content', '') or '')
                if lvl in (OffenseLevel.SEVERE, OffenseLevel.MODERATE):
                    return {'user_id': str(m.get('user_id')), 'username': m.get('username')}
            # 3) 兜底：返回最近一条轻度冒犯
            for m in candidates:
                lvl = self._detect_offense_level(m.get('content', '') or '')
                if lvl == OffenseLevel.MILD:
                    return {'user_id': str(m.get('user_id')), 'username': m.get('username')}
            return None

        # 0) 劝阻语识别：如"请避免/别/不要 + 外号/冒犯/攻击/用词/语气"等
        def _is_defensive_utterance(text: str) -> bool:
            try:
                t = (text or '').strip().lower()
            except Exception:
                t = (text or '').strip()
            patterns = [
                r"(请|請|别|別|不要|别动不动|不要老是|避免).*(外号|外號|冒犯|攻击|攻擊|用词|用詞|语气|語氣|侮辱)",
                r"(注意|缓一下|缓一缓|温和点|和气).*语气",
            ]
            for pat in patterns:
                if re.search(pat, t):
                    return True
            return False

        def _find_last_offender(room_id_str: str, lookback: int = 8) -> Optional[dict]:
            msgs = list(self.room_recent_messages.get(room_id_str, []))
            if not msgs:
                return None
            for m in reversed(msgs[-lookback:]):
                if self._is_admin_user(str(m.get('user_id'))):
                    continue
                lvl = self._detect_offense_level(m.get('content', '') or '')
                if lvl in (OffenseLevel.MODERATE, OffenseLevel.SEVERE):
                    return {'user_id': str(m.get('user_id')), 'username': m.get('username')}
            # 次优：若找不到中重度，找最近含轻度冒犯的用户
            for m in reversed(msgs[-lookback:]):
                if self._is_admin_user(str(m.get('user_id'))):
                    continue
                lvl = self._detect_offense_level(m.get('content', '') or '')
                if lvl == OffenseLevel.MILD:
                    return {'user_id': str(m.get('user_id')), 'username': m.get('username')}
            return None

        if _is_defensive_utterance(message_content):
            offender = _find_last_offender(room_id)
            if offender and offender.get('username'):
                msg = self._sanitize_tone(f"@{offender['username']} 提醒一下：请避免冒犯性称呼，一起友好讨论～")
                return InterventionResult(
                    should_intervene=True,
                    intervention_type=InterventionType.CONFLICT_DEESCALATION,
                    message=msg,
                    reason="defensive_utterance_redirect_to_offender",
                    offense_level=OffenseLevel.MILD,
                    target_user=offender['username']
                )
            else:
                # 找不到明确冒犯者 → 给全局轻量降温，不@劝阻者
                msg = self._sanitize_tone("先稍微缓一下，我们尊重彼此观点，继续平和交流～")
                return InterventionResult(
                    should_intervene=True,
                    intervention_type=InterventionType.CONFLICT_DEESCALATION,
                    message=msg,
                    reason="defensive_utterance_global_nudge",
                    offense_level=OffenseLevel.MILD
                )
        
        # === 🔍 双通道并行检测：LLM + 关键词，结果融合 ===
        print(f"🐛 [DEBUG] 检测模式: {self.conflict_detection_mode}")
        print(f"🐛 [DEBUG] LLM启用: {self.llm_enabled}")
        print(f"🐛 [DEBUG] 消息内容: '{message_content}'")
        
        llm_result: Optional[Dict] = None
        llm_offense_level = None
        current_msg_offense = None
        
        # 1️⃣ LLM检测通道
        if self.conflict_detection_mode in ('hybrid', 'llm'):
            llm_result = self._llm_classify_toxicity(room_id, last_n=12)
            print(f"🤖 [LLM检测] 原始结果: {llm_result}")
            
            if llm_result:
                print(f"🤖 [LLM检测] should_intervene: {llm_result.get('should_intervene', False)}")
                print(f"🤖 [LLM检测] 置信度: {llm_result.get('confidence', 0):.2f} (阈值: {self.llm_conf_threshold})")
                print(f"🤖 [LLM检测] 严重程度: {llm_result.get('severity', 'none')}")
                
                if llm_result.get('should_intervene') and llm_result.get('confidence', 0) >= self.llm_conf_threshold:
                    llm_offense_level = self._map_llm_severity(llm_result.get('severity'))
                    print(f"🤖 [LLM检测] ✅ 检测到冒犯等级: {llm_offense_level.name if llm_offense_level else None}")
                # 紧急刹车：升级风险高时立即返回
                if llm_result.get('escalation_risk') == 'high':
                    reason = "LLM判定升级风险高，触发紧急降温"
                    print(f"🚨 [紧急刹车] {reason}")
                    return InterventionResult(
                        should_intervene=True,
                        intervention_type=InterventionType.CONFLICT_DEESCALATION,
                        message=self._sanitize_tone(
                            ("先暂停一下。请放松语气，尊重彼此观点，我们继续平和交流。")
                        ),
                        reason=reason,
                        offense_level=llm_offense_level,
                        via_llm=True, llm_confidence=llm_result.get('confidence'), llm_label=llm_result.get('label')
                    )
            else:
                print(f"🤖 [LLM检测] ❌ 未通过检测 (置信度不足或should_intervene=false)")
        else:
            print(f"🤖 [LLM检测] ❌ LLM调用失败")
        
        # 2️⃣ 关键词检测通道 (始终执行，除非是LLM-only且不允许回退)
        should_run_keywords = (
            self.conflict_detection_mode in ('hybrid', 'keywords') or
            (self.conflict_detection_mode == 'llm' and self.llm_only_conflict_fallback)
        )
        
        if should_run_keywords:
            current_msg_offense = self._detect_offense_level(message_content)
            print(f"🔍 [关键词检测] 检测结果: {current_msg_offense.name if current_msg_offense else 'None'}")
        else:
            print(f"🚫 [关键词检测] 跳过 (LLM-only模式且不允许回退)")
        
        # 3️⃣ 结果融合：取两者中更高的冒犯等级
        offense_level = None
        detection_source = []
        via_llm = False
        
        if llm_offense_level and current_msg_offense:
            # 两个都有结果，取更严重的
            if llm_offense_level.value >= current_msg_offense.value:
                offense_level = llm_offense_level
                detection_source = ["LLM主导", f"关键词:{current_msg_offense.name}"]
                via_llm = True
            else:
                offense_level = current_msg_offense
                detection_source = ["关键词主导", f"LLM:{llm_offense_level.name}"]
                via_llm = False
            print(f"🔗 [结果融合] LLM:{llm_offense_level.name} + 关键词:{current_msg_offense.name} → {detection_source[0]} 最终:{offense_level.name}")
        elif llm_offense_level:
            offense_level = llm_offense_level
            detection_source = ["LLM检测"]
            via_llm = True
            print(f"🤖 [单一来源] LLM检测: {offense_level.name}")
        elif current_msg_offense:
            offense_level = current_msg_offense
            detection_source = ["关键词检测"]
            via_llm = False
            print(f"🔍 [单一来源] 关键词检测: {offense_level.name}")
        else:
            print(f"✅ [检测结果] 无冒犯内容检测到")
        
        # 4️⃣ LLM-only模式的特殊处理
        if self.conflict_detection_mode == 'llm' and not self.llm_only_conflict_fallback and not llm_offense_level:
            print(f"🚫 [LLM-only] 无LLM检测结果且不允许回退，跳过干预")
            # 继续执行群体检测逻辑，不直接返回None
        if not offense_level:
            # 另外做一个"最近4条里冲突语气很多"的群体级检测
            recent_messages = list(self.room_recent_messages.get(room_id, []))
            if len(recent_messages) >= 4:
                conflict_count = sum(
                    1 for msg in recent_messages[-4:] if self._is_conflict_message(msg['content'])
                )
                # 仅当非admin消息达到最小轮数门槛时启用
                non_admin_recent = [m for m in recent_messages if not self._is_admin_user(str(m.get('user_id')))]
                if len(non_admin_recent) >= self.min_messages_for_conflict and conflict_count >= 3:
                    reason = f"检测到连续冲突消息，冲突等级: {conflict_count}/4"
                    return InterventionResult(
                        should_intervene=True,
                        intervention_type=InterventionType.CONFLICT_DEESCALATION,
                        # 不要求贴数据，仅做降温
                        message=self._sanitize_tone("讨论有点激烈，大家先放松一下，理性沟通～"),
                        reason=reason,
                        offense_level=OffenseLevel.MODERATE
                    )
            # 检测"二人激烈争吵"：最近6条消息由两个人来回对线且有攻击性词汇
            if len(recent_messages) >= 6:
                last6 = recent_messages[-6:]
                users = [m['user_id'] for m in last6]
                unique_users = list(set(users))
                if len(unique_users) == 2 and len([m for m in last6 if not self._is_admin_user(str(m.get('user_id')))]) >= self.min_messages_for_conflict:
                    # 仅当出现≥2条攻击性语句时认为"比较激烈"
                    attack_count = sum(1 for m in last6 if self._is_conflict_message(m['content']))
                    if attack_count >= 2:
                        # 使用LLM生成"紧急刹车"话术，并跳过冷却
                        usernames = list({m['username'] for m in last6})
                        # 改为温和劝导，不要求贴数据
                        msg = self._sanitize_tone(
                            f"@{' @'.join(usernames[:2])} 先别急，我们放平语气，尊重彼此观点，继续好好聊。"
                        )
                        return InterventionResult(
                            should_intervene=True,
                            intervention_type=InterventionType.CONFLICT_DEESCALATION,
                            message=msg,
                            reason="heated_two_person_argument",
                            offense_level=OffenseLevel.MODERATE
                        )
            return None

        # ------- 归责：将违规归到真正冒犯者（若当前消息非冒犯或仅为应和） -------
        target_user_id = str(user_id)
        target_username = username
        if (_is_acknowledgement(message_content) or current_msg_offense is None) and llm_result and llm_result.get('should_intervene'):
            offender = _resolve_offender_from_recent(room_id, llm_result.get('offending_terms'))
            if offender and offender.get('user_id'):
                target_user_id = offender['user_id']
                target_username = offender['username'] or target_username

        # ------- 简化为每次即时提醒，仅保留节流机制避免刷屏 -------
        now = time.time()
        throttle_key = f"{room_id}_{target_user_id}"
        last_conflict_ts = self.user_last_conflict_reminder_ts.get(throttle_key, 0)
        is_critical_offense = (
            offense_level == OffenseLevel.SEVERE or
            (current_msg_offense == OffenseLevel.SEVERE if 'current_msg_offense' in locals() else False)
        )
        # 对严重词（脏话/人身攻击）绕开节流，确保必显示
        if (not is_critical_offense) and ((now - last_conflict_ts) < self.per_user_conflict_throttle_seconds):
            return None
        # 优先尝试 LLM 温柔提醒：若为毒性场景，改用更简短的 gentle_toxic
        llm_msg = None
        # 若当前消息实为"劝阻/提醒别人不要用外号"，则不发毒性提醒，避免误伤
        if not self._is_discouraging_offense(message_content) and (
            offense_level == OffenseLevel.SEVERE or (current_msg_offense == OffenseLevel.SEVERE if 'current_msg_offense' in locals() else False)
        ):
            llm_msg = self._llm_generate_message(
                'gentle_toxic', room_id,
                user=target_username,
                original_content=message_content,
                offending_terms=(llm_result.get('offending_terms') if isinstance(llm_result, dict) else None)
            )
        if not llm_msg:
            llm_msg = self._llm_generate_message('gentle_conflict', room_id, user=target_username)

        # 根据语义归类使用固定极简提醒，失败再回退到llm/通用模板
        msg_lower = (message_content or '').lower()
        llm_label = (llm_result.get('label') if isinstance(llm_result, dict) else None)
        offending_terms = (llm_result.get('offending_terms') if isinstance(llm_result, dict) else [])
        bucket = self._classify_offense_bucket(msg_lower, llm_label, offending_terms)

        bucket_templates = {
            'banter_nick': [f"@{target_username} 请避免使用可能冒犯的外号哦～"],
            'denigrate': [f"@{target_username} 咱们别拉踩，专注观点本身吧～"],
            'extreme_negative': [f"@{target_username} 语气放松点，我们理性聊会更高效～"],
            'insult_label': [f"@{target_username} 别用带侮辱的称呼，我们就事论事～"],
            'escalation': [f"@{target_username} 先别上火，尊重彼此更有收获～"],
        }
        template = None
        if bucket and bucket in bucket_templates:
            template = random.choice(bucket_templates[bucket])
        if not template:
            # 通用短句回退
            generic_pool = [
                f"@{target_username} 我们就观点不就人，一起好好聊～",
                f"@{target_username} 放轻松～用更友好的措辞更易交流哦",
            ]
            template = llm_msg or random.choice(generic_pool)
        template = self._sanitize_tone(template)
        # 记录节流时间
        self.user_last_conflict_reminder_ts[throttle_key] = now

        reason = (
            f"即时提醒，offense={offense_level.name}，"
            f"消息: {message_content[:50]}"
        )

        return InterventionResult(
            should_intervene=True,
            intervention_type=InterventionType.CONFLICT_DEESCALATION,
            message=template,
            reason=reason,
            offense_level=offense_level,
            via_llm=via_llm,
            llm_confidence=(llm_result.get('confidence') if isinstance(llm_result, dict) else None),
            llm_label=(llm_result.get('label') if isinstance(llm_result, dict) else None),
            target_user=target_username
        )


    def _check_silence_intervention(self, room_id: str, dry_run: bool = False, neutral_mode: bool = False) -> Optional[InterventionResult]:
        
        room_id = str(room_id)  # 确保是字符串类型
        current_time = time.time()
        recent_messages = list(self.room_recent_messages.get(room_id, []))
        
        # 过滤掉admin消息，只看普通用户消息
        non_admin_messages = [msg for msg in recent_messages if not self._is_admin_user(str(msg['user_id']))]
        print(f"🔍 [沉默检测] 房间{room_id} 总消息: {len(recent_messages)}, 非admin消息: {len(non_admin_messages)}")
        
        # 需要至少3轮对话后才开始沉默检测（约等于≥6条非admin消息）
        min_messages_for_detection = getattr(self, 'min_messages_for_conflict', 6)
        if len(non_admin_messages) < min_messages_for_detection:
            print(f"🔍 [沉默检测] 房间{room_id} 对话不足，需要{int(min_messages_for_detection/2)}轮对话后才开始检测: {len(non_admin_messages)}/{min_messages_for_detection}")
            return None
        
        # 获取所有在线用户（包括从未发言的用户），并排除管理员
        all_users_in_room = [
            uid for uid in self._get_online_users_in_room(room_id)
            if not self._is_admin_user(str(uid))
        ]
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
            transition_cooldown = self.agenda_transition_cooldown
            if current_time - last_transition_time >= transition_cooldown:
                self.room_last_agenda_transition[room_id] = current_time
                
                llm_msg = self._llm_generate_message('agenda', room_id)
                # 群体沉默：总结+新视角引导
                transition_msg = (
                    self._compose_topic_pullback(room_id, reason="group_silence")
                )
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
        
        # === 冲突感知：若最近窗口存在明显冲突/辱骂，则仍可点名，但必须使用中性、不引用上下文的文案 ===
        def _recent_conflict(messages: List[Dict], window: int = 6) -> bool:
            subset = [m for m in messages[-window:] if m.get('content')]
            if not subset:
                return False
            offensive_hits = 0
            for m in subset:
                if self._is_conflict_message(m.get('content', '')):
                    offensive_hits += 1
            # 若窗口内≥2条冲突用语，认为当前不宜点名沉默用户
            return offensive_hits >= 2

        recent_conflict = _recent_conflict(non_admin_messages, window=6)
        if recent_conflict:
            print(f"⛔ [沉默检测] 最近对话存在冲突语气，将使用中性邀请文案（不引用上下文）")
            neutral_mode = True

        # 偏题检测：偏题时也使用中性邀请文案
        try:
            off_topic_now = (self._is_on_topic_football(room_id, window=3) is False)
        except Exception:
            off_topic_now = False
        if off_topic_now:
            print(f"🔄 [沉默检测] 最近对话偏题，将使用中性邀请文案（不引用上下文）")
            neutral_mode = True

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
                
                # 更新用户提醒时间（仅在真实执行时更新，dry_run不改状态）
                if not dry_run:
                    self.user_last_reminder_time[user_reminder_key] = current_time
                
                # 根据上下文选择文案：
                # - neutral_mode=True 时，使用固定中性短句，不引用上下文
                # - 否则，尝试 LLM 生成邀请
                if neutral_mode:
                    invitation_msg = f"@{silent_username}，也来聊聊你的看法吧～"
                else:
                    llm_msg = self._llm_generate_message('silence', room_id, user=silent_username)
                    invitation_msg = llm_msg or f"@{silent_username}，也来聊聊你的看法吧～"
                # 语气与内容净化：移除侮辱词和多余标点，避免在冲突场景火上浇油
                invitation_msg = self._sanitize_tone(invitation_msg)
                print(f"🤖 [LLM] 沉默邀请 - LLM生成: '{llm_msg}', 最终消息: '{invitation_msg}'")
                reason = f"检测到用户 {silent_username} 沉默超过 {int(silence_duration)} 秒（沉默最久）"
                
                return InterventionResult(
                    should_intervene=True,
                    intervention_type=InterventionType.SILENCE_INVITATION,
                    message=invitation_msg,
                    reason=(reason + (" | neutral" if neutral_mode else "")),
                    target_user=silent_username
                )
        
        print(f"🔍 [沉默检测] 房间{room_id} 无沉默用户需要干预")
        return None

    def _check_agenda_transition(self, room_id: str, dry_run: bool = False) -> Optional[InterventionResult]:
        """检查是否需要议程过渡引导（群体沉默时主动开启话题，无轮数限制）
        dry_run=True 时不更新冷却时间，不改变内部状态，仅返回可能的文案。
        """
        room_id = str(room_id)  # 确保是字符串类型
        current_time = time.time()
        recent_messages = list(self.room_recent_messages.get(room_id, []))
        
        # 过滤掉admin消息，只看普通用户消息
        non_admin_messages = [msg for msg in recent_messages if not self._is_admin_user(str(msg['user_id']))]
        
        # 群体沉默（与破冰不同）：需要至少2条非admin用户消息后才进入"群体沉默引导"判定
        min_msgs_for_group_silence = 2
        print(f"🔍 [群体沉默] 房间{room_id} 当前消息数: {len(non_admin_messages)} (要求≥{min_msgs_for_group_silence}才判定群体沉默)")
        
        # 如果没有任何消息，也可以主动开启话题
        if len(non_admin_messages) == 0:
            print(f"🆕 [群体沉默] 房间{room_id} 无消息历史，主动开启破冰话题")
        
        # 检查冷却时间
        last_transition_time = self.room_last_agenda_transition.get(room_id, 0)
        if current_time - last_transition_time < self.agenda_transition_cooldown:
            print(f"⏸️ [群体沉默] 房间{room_id} 仍在冷却中，剩余{self.agenda_transition_cooldown - (current_time - last_transition_time):.1f}秒")
            return None
        
        # 仅基于"非管理员消息"计算最后发言时间（不计入admin）
        last_non_admin_time = non_admin_messages[-1]['timestamp'] if non_admin_messages else 0
        silence_duration = current_time - last_non_admin_time if last_non_admin_time else float('inf')
        
        # 群体沉默检测：针对实验场景的智能破冰逻辑
        should_start_topic = False
        reason = ""
        
        if len(non_admin_messages) == 0:
            # 视作"无用户消息历史"，不使用admin消息计时；依靠冷却与阈值控制
            if current_time - last_transition_time >= self.agenda_transition_cooldown and self.agenda_transition_threshold <= self.agenda_transition_threshold:
                should_start_topic = True
                reason = "房间无用户消息历史，主动开启破冰话题"
                print(f"🆕 [群体沉默] {reason}")
            else:
                remaining = max(0, self.agenda_transition_cooldown - (current_time - last_transition_time))
                print(f"⏸️ [群体沉默] 冷却中或尚未到触发条件，剩余{remaining:.1f}秒")
        elif len(non_admin_messages) >= min_msgs_for_group_silence:
            # 有普通用户消息，检查最后一条普通用户消息的沉默时间
            last_non_admin_msg = non_admin_messages[-1]
            user_silence_duration = current_time - last_non_admin_msg['timestamp']
            
            if user_silence_duration >= self.agenda_transition_threshold:
                should_start_topic = True
                reason = f"用户沉默 {int(user_silence_duration)} 秒，主动开启新话题"
                print(f"🤐 [群体沉默] {reason}")
            else:
                print(f"🕒 [沉默监控] 非管理员最后发言{int(user_silence_duration)}秒前，未达到{self.agenda_transition_threshold}秒阈值")
        else:
            # 非admin消息不足3条 → 不进行群体沉默引导（避免和破冰混淆）
            print(f"ℹ️ [群体沉默] 非admin消息不足{min_msgs_for_group_silence}条，暂不进行群体沉默引导")
        
        if should_start_topic:
            current_topic = self._extract_current_topic(room_id)
            next_topic = self._get_next_topic_suggestion(room_id, current_topic)
            
            # 根据不同情况选择合适的话题开启方式
            if len(non_admin_messages) == 0:
                # 完全没有消息历史，使用破冰话题模板
                theme = getattr(self, 'icebreaker_theme', '')
                icebreaker_templates = [
                    (f"{theme}" if theme else "我们先轻松开个头：最近哪支球队的表现最打动你？说说为什么～"),
                    (f"{theme}" if theme else "先聊聊个人感受吧：你最喜欢的踢法或战术是什么？"),
                    (f"{theme}" if theme else "如果用一句话形容你最欣赏的球队/球员，会怎么说？"),
                    (f"{theme}" if theme else "不妨先从你最在意的一个点聊起，比如球队文化、风格或精神～"),
                    (f"{theme}" if theme else "来个小热身：你觉得哪支球队最能代表'有想法的足球'，为什么？")
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
            
            # 记录这次议程过渡时间（dry_run时不消耗冷却）
            if not dry_run:
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
        
        if len(recent_messages) < 3:
            return None

        # 活跃且在题内时，不做"话题拉回"类结构引导，避免误触发
        try:
            on_topic_now = self._is_on_topic_football(room_id, window=3)
        except Exception:
            on_topic_now = True
        try:
            active_now = self._is_active_discussion(room_id)
        except Exception:
            active_now = False
        # 活跃且在题内 → 不做结构引导
        if on_topic_now and active_now:
            return None
        # 冲突窗口内（最近6条包含≥2条冲突语）→ 禁止话题拉回，优先降温
        try:
            recent = list(self.room_recent_messages.get(room_id, []))
            last6 = [m for m in recent[-6:] if m.get('content')]
            conflict_hits = sum(1 for m in last6 if self._is_conflict_message(m.get('content', '')))
            if conflict_hits >= 2:
                return None
        except Exception:
            pass
        # 共享冷却：若未到共享冷却，不触发
        if not self._shared_guidance_cooldown_ok(room_id):
            return None
        
        # 连续发言统计：忽略管理员与Chatbot消息
        # 找到最后一条非管理员且非Chatbot的消息作为最近发言者
        def _is_chatbot(msg: Dict) -> bool:
            uname = (msg.get('username') or '').strip()
            return uname.lower() == 'chime' or msg.get('user_id') in (None, '')

        last_non_admin_idx = None
        for idx in range(len(recent_messages)-1, -1, -1):
            m = recent_messages[idx]
            if not self._is_admin_user(str(m.get('user_id'))) and not _is_chatbot(m):
                last_non_admin_idx = idx
                break

        if last_non_admin_idx is None:
            return None

        consecutive_count = 1
        last_user = recent_messages[last_non_admin_idx]['user_id']
        last_username = recent_messages[last_non_admin_idx]['username']
        consecutive_time_span = 0
        consecutive_total_length = len(recent_messages[last_non_admin_idx]['content'])
        has_response = False  # 检查是否有其他人回应

        last_timestamp = recent_messages[last_non_admin_idx]['timestamp']

        # 回看最多5条之前的消息，忽略admin/Chatbot，不打断连续统计
        looked = 0
        for i in range(last_non_admin_idx - 1, -1, -1):
            if looked >= 5:
                break
            m = recent_messages[i]
            # 忽略管理员与Chatbot消息
            if self._is_admin_user(str(m.get('user_id'))) or _is_chatbot(m):
                continue
            looked += 1
            if m.get('user_id') == last_user:
                consecutive_count += 1
                consecutive_time_span = last_timestamp - m.get('timestamp')
                consecutive_total_length += len(m.get('content', ''))
            else:
                # 其他普通用户在1分钟内的插话，视作有回应
                if last_timestamp - m.get('timestamp', last_timestamp) < 60:
                    has_response = True
                break
        
        # 已在上方累计最近一条
        
        # 触发条件：同一用户连续≥4条（简化，降低误报）
        should_remind_turn_taking = consecutive_count >= 4
        
        if should_remind_turn_taking:
            reason = f"检测到用户 {last_username} 连续发言 {consecutive_count} 条"
            # 轮次提醒：具体分配口径
            llm_msg = self._llm_generate_message('turn_taking', room_id)
            final_msg = (
                llm_msg or 
                "我们按顺序来一轮：每人用一句话说'最伟大的球队是谁'，并给一个最能体现其'足球哲学'的例子。"
            )
            print(f"🤖 [LLM] 轮次引导 - LLM生成: '{llm_msg}', 最终消息: '{final_msg}'")
            self._mark_shared_guidance(room_id)
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
            # 若仍主要聊"足球"，则不认为跑题，避免误触发
            if self._is_on_topic_football(room_id, window=3):
                return None
            reason = "检测到话题跳跃，讨论较分散（且不主要围绕足球）"
            # LLM 生成简短总结+拉回
            llm_msg = self._llm_generate_message('topic_pullback', room_id)
            # 统一为提醒+总结+引导
            final_msg = self._compose_topic_pullback(room_id, reason="off_topic")
            # 话题拉回冷却：未到冷却则跳过
            if not self._topic_cooldown_ok(room_id):
                return None
            self._mark_topic_pullback(room_id)
            self._mark_shared_guidance(room_id)
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
            '你懂个', '别说话', '闭嘴吧', '没脑子', '智商', '弱智', '傻',
            '你懂球吗', '你就你懂', '你最懂', '懂王'
        ]
        
        for pattern in personal_attack_patterns:
            if pattern in message_lower:
                return OffenseLevel.SEVERE
        
        return None

    def _is_conflict_message(self, content: str) -> bool:
        # 拉回话题/缓和白名单（命中则不判冲突）
        whitelist_tokens = [
            '回到主题', '回到足球', '聊回足球', '不要吵', '别吵了', '还是聊正题', '我们聊战术', '我们聊比赛',
            # 缓和/中性描述，降低误报
            '机制', '配置', '匹配', '分组优秀', '匹配机制', '分组机制', '阵容配置', '人员配置', '轮换机制'
        ]
        try:
            for w in whitelist_tokens:
                if w in content:
                    return False
        except Exception:
            pass

        conflict_indicators = [
            '不对', '错了', '胡说', '放屁', '扯淡', '我不同意',
            '你这', '什么鬼', '太离谱', '无语', '服了',
            '闭嘴', '没资格', '不懂球'
        ]
        
        content_lower = content.lower()
        for indicator in conflict_indicators:
            if indicator in content_lower:
                return True
        
        # 弱化标点密度对冲突判断的影响，降低误报
        exclamation_count = content.count('!') + content.count('！')
        question_count = content.count('?') + content.count('？')
        if len(content) > 20:
            punctuation_density = (exclamation_count + question_count) / max(1, len(content))
            if punctuation_density > 0.2:
                return True
        
        return False

    def _recent_conflict_triggered(self, room_id: str, window: int = 2) -> bool:
        """仅允许最近window条内出现明显冲突词时触发群体降温，避免历史余波导致误报。"""
        msgs = list(self.room_recent_messages.get(str(room_id), []))
        if not msgs:
            return False
        recent = [m for m in msgs if m.get('content')][-max(1, window):]
        return any(self._is_conflict_message(m.get('content', '')) for m in recent)

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
    
    # 移除禁言相关接口

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
