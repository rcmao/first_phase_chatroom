import time
import asyncio
import threading
import logging
from typing import Dict, Optional
from datetime import datetime
from smart_intervention_engine import SmartInterventionEngine, InterventionResult, InterventionType
from flask_socketio import emit

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealtimeMonitor:
    """
    实时监控系统 - 独立于消息触发的主动监控
    功能：
    1. 每10秒扫描所有活跃房间
    2. 检测沉默、话题偏离、需要干预的情况
    3. 主动触发干预，而不是被动等待消息
    """
    
    def __init__(self, intervention_engine: SmartInterventionEngine, socketio, app):
        self.intervention_engine = intervention_engine
        self.socketio = socketio
        self.app = app
        self.is_running = False
        self.monitor_thread = None
        
        # 监控配置
        self.scan_interval = 10  # 每10秒扫描一次
        self.max_silence_before_action = 45  # 45秒群体沉默触发第一次破冰
        self.active_rooms = set()  # 活跃房间列表
        
        # 统计信息
        self.total_scans = 0
        self.total_interventions = 0
        self.last_scan_time = 0
        
        # 显示控制
        self.last_status_display_time = {}  # 每个房间最后显示状态的时间
        self.status_display_interval = 30   # 每30秒显示一次详细状态
        # 记录每个房间chatbot启用的时间，避免启用后立刻破冰
        self.room_enable_time: Dict[str, float] = {}
        
    def add_active_room(self, room_id: str):
        """添加需要监控的房间"""
        room_id = str(room_id)  # 确保是字符串类型
        self.active_rooms.add(room_id)
        logger.info(f"📊 开始监控房间: {room_id}")
        # 如果房间启用了chatbot，则记录启用时间
        if room_id not in self.room_enable_time:
            self.room_enable_time[room_id] = time.time()
        
    def remove_active_room(self, room_id: str):
        """移除房间监控"""
        room_id = str(room_id)  # 确保是字符串类型
        self.active_rooms.discard(room_id)
        logger.info(f"📊 停止监控房间: {room_id}")
        
    def start_monitoring(self):
        """启动实时监控"""
        if self.is_running:
            return
            
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("🎯 实时监控循环开始")
        
    def stop_monitoring(self):
        """停止实时监控"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("🛑 实时监控循环停止")
        
    def _monitor_loop(self):
        """主监控循环"""
        logger.info("🔄 实时聊天室监控已启动")
        
        while self.is_running:
            try:
                self._scan_all_rooms()
                time.sleep(self.scan_interval)
            except Exception as e:
                logger.error(f"❌ 监控循环错误: {e}")
                time.sleep(self.scan_interval)
                
    def _scan_all_rooms(self):
        """扫描所有活跃房间"""
        self.total_scans += 1
        self.last_scan_time = time.time()
        
        with self.app.app_context():
            # 检查是否有任何房间启用了Chatbot
            from app import Room
            enabled_rooms = Room.query.filter_by(chatbot_enabled=True).all()
            enabled_room_ids = {str(room.id) for room in enabled_rooms}
            
            # 过滤活跃房间，只监控启用了Chatbot的房间
            active_enabled_rooms = [room_id for room_id in self.active_rooms if room_id in enabled_room_ids]
            
            if not active_enabled_rooms:
                # 每30秒提醒一次没有启用Chatbot的房间
                if hasattr(self, '_last_disabled_log') and time.time() - self._last_disabled_log < 30:
                    return
                self._last_disabled_log = time.time()
                print("🔕 [监控] 当前无房间启用Chatbot，暂停监控")
                return
            
            # 发送监控状态给管理员
            self._send_monitoring_status()
            
            # 显示总体监控状态
            self._display_overall_status()
                
            for room_id in active_enabled_rooms:
                try:
                    self._check_room_conditions(room_id)
                except Exception as e:
                    logger.error(f"❌ 房间{room_id}监控错误: {type(e).__name__}: {e}")
                    import traceback
                    logger.debug(f"房间{room_id}监控详细错误信息: {traceback.format_exc()}")
                    # 如果房间连续出错太多次，暂时移除监控
                    error_key = f"room_{room_id}_errors"
                    if not hasattr(self, '_room_error_counts'):
                        self._room_error_counts = {}
                    self._room_error_counts[error_key] = self._room_error_counts.get(error_key, 0) + 1
                    if self._room_error_counts[error_key] >= 5:
                        logger.warning(f"⚠️ 房间{room_id}连续错误5次，暂时移除监控")
                        self.active_rooms.discard(room_id)
                        self._room_error_counts[error_key] = 0
                    
    def _check_room_conditions(self, room_id: str):
        """检查单个房间的各种条件"""
        try:
            # 确保房间ID是字符串类型
            room_id = str(room_id)
            current_time = time.time()
            
            # 新启用保护：启用后的前 self.max_silence_before_action 秒不触发任何破冰
            enable_ts = self.room_enable_time.get(room_id)
            if enable_ts and (current_time - enable_ts) < self.max_silence_before_action:
                remaining = int(self.max_silence_before_action - (current_time - enable_ts))
                print(f"⏳ [监控] 房间{room_id} 刚启用，等待{remaining}s后再开始破冰检测")
                return

            # 检查房间是否有消息历史
            if room_id not in self.intervention_engine.room_recent_messages:
                # 无消息历史时，基于启用时间进行沉默计时，超过阈值后触发破冰
                enable_ts = self.room_enable_time.get(room_id)
                if not enable_ts:
                    # 首次记录启用时间
                    self.room_enable_time[room_id] = current_time
                    print(f"🆕 [监控] 房间{room_id} 无消息历史，开始计时等待破冰阈值 {self.max_silence_before_action}s")
                    return
                elapsed = current_time - enable_ts
                remaining = int(max(0, self.max_silence_before_action - elapsed))
                if elapsed >= self.max_silence_before_action:
                    print(f"❄️ [监控] 房间{room_id} 无消息且已沉默 {int(elapsed)}s，尝试触发破冰")
                    agenda_result = self._check_agenda_needs(room_id, current_time)
                    if agenda_result:
                        self._execute_intervention(room_id, agenda_result)
                    else:
                        print(f"ℹ️ [监控] 房间{room_id} 议程过渡检查未返回干预")
                    return
                else:
                    print(f"⏳ [监控] 房间{room_id} 无消息历史，等待 {remaining}s 后再检测破冰")
                    return
            
            # 智能显示检测状态（避免刷屏）
            self._smart_display_detection_status(room_id, current_time)
            
            # 1. 检查房间沉默状态
            silence_result = self._check_room_silence(room_id, current_time)
            if silence_result:
                self._execute_intervention(room_id, silence_result)
                return
                
            # 2. 检查议程过渡需要
            agenda_result = self._check_agenda_needs(room_id, current_time)
            if agenda_result:
                self._execute_intervention(room_id, agenda_result)
                return
                
            # 3. 检查话题偏离
            topic_result = self._check_topic_drift(room_id, current_time)
            if topic_result:
                self._execute_intervention(room_id, topic_result)
                return
        except Exception as e:
            logger.error(f"❌ 房间{room_id}条件检查失败: {type(e).__name__}: {e}")
            import traceback
            logger.debug(f"详细错误信息: {traceback.format_exc()}")
            raise  # 重新抛出异常让上层处理
        else:
            # 成功执行，重置错误计数
            if hasattr(self, '_room_error_counts'):
                error_key = f"room_{room_id}_errors"
                if error_key in self._room_error_counts:
                    self._room_error_counts[error_key] = 0
            
    def _check_room_silence(self, room_id: str, current_time: float) -> Optional[InterventionResult]:
        """检查房间沉默状态和用户沉默状态"""
        recent_messages = list(self.intervention_engine.room_recent_messages.get(room_id, []))
        
        if not recent_messages:
            print(f"🔍 [监控] 房间{room_id} 无消息历史")
            return None
            
        # 计算房间最后活动时间（忽略admin发言）
        non_admin_messages = [m for m in recent_messages if not self.intervention_engine._is_admin_user(str(m.get('user_id')))]
        last_message_time = non_admin_messages[-1]['timestamp'] if non_admin_messages else 0
        room_silence_duration = current_time - last_message_time
        
        print(f"🔍 [监控] 房间{room_id} 最后(非admin)消息: {room_silence_duration:.1f}秒前")
        
        # 检查全局冷却
        last_intervention = self.intervention_engine.room_last_intervention_ts.get(room_id, 0)
        cooldown_remaining = self.intervention_engine.global_cooldown_seconds - (current_time - last_intervention)
        
        if cooldown_remaining > 0:
            print(f"⏸️ [监控] 房间{room_id} 冷却中，剩余{cooldown_remaining:.1f}秒")
            return None
        
        # 1. 首先检查用户沉默（无论房间是否沉默）
        print(f"👥 [监控] 检查房间{room_id}的沉默用户...")
        silence_result = self.intervention_engine._check_silence_intervention(room_id)
        if silence_result and silence_result.should_intervene:
            print(f"👋 [监控] 房间{room_id} 检测到沉默用户，准备邀请: {silence_result.target_user}")
            return silence_result
            
        # 2. 检查房间整体沉默（需要议程过渡）
        if room_silence_duration >= self.max_silence_before_action:
            print(f"📋 [监控] 房间{room_id} 整体沉默{room_silence_duration:.1f}秒，检查议程过渡...")
            agenda_result = self.intervention_engine._check_agenda_transition(room_id)
            if agenda_result and agenda_result.should_intervene:
                print(f"📋 [监控] 房间{room_id} 需要议程过渡")
                return agenda_result
                
        return None
        
    def _check_agenda_needs(self, room_id: str, current_time: float) -> Optional[InterventionResult]:
        """检查是否需要议程引导"""
        # 调用智能干预引擎的议程过渡检测
        return self.intervention_engine._check_agenda_transition(room_id)
        
    def _check_topic_drift(self, room_id: str, current_time: float) -> Optional[InterventionResult]:
        """检查话题偏离情况"""
        # 检查最近的讨论是否偏离足球主题
        is_on_topic = self.intervention_engine._is_on_topic_football(room_id, window=3)

        if not is_on_topic:
            recent_messages = list(self.intervention_engine.room_recent_messages.get(room_id, []))
            if len(recent_messages) >= 3:  # 至少3条再考虑跑题
                # 冲突窗口内禁止拉回，优先降温
                try:
                    last6 = [m for m in recent_messages[-6:] if m.get('content')]
                    conflict_hits = sum(1 for m in last6 if self.intervention_engine._is_conflict_message(m.get('content', '')))
                    if conflict_hits >= 2:
                        return None
                except Exception:
                    pass

                # 共享引导冷却：若未到冷却，跳过
                try:
                    if not self.intervention_engine._shared_guidance_cooldown_ok(room_id):
                        return None
                except Exception:
                    pass

                print(f"⚽ [监控] 房间{room_id} 检测到话题偏离")

                # 检查全局冷却
                last_intervention = self.intervention_engine.room_last_intervention_ts.get(room_id, 0)
                if current_time - last_intervention >= self.intervention_engine.global_cooldown_seconds:
                    # 先尝试结构化引导
                    result = self.intervention_engine._check_structure_guidance(room_id)
                    if result:
                        return result
                    # 兜底：生成轻量“话题拉回”
                    try:
                        if not self.intervention_engine._topic_cooldown_ok(room_id):
                            return None
                    except Exception:
                        pass
                    try:
                        fallback_msg = self.intervention_engine._compose_topic_pullback(room_id, reason="off_topic")
                    except Exception:
                        fallback_msg = "稍作提醒：讨论有点发散，我们回到足球主题聊聊～"
                    try:
                        self.intervention_engine._mark_topic_pullback(room_id)
                        self.intervention_engine._mark_shared_guidance(room_id)
                    except Exception:
                        pass
                    return InterventionResult(
                        should_intervene=True,
                        intervention_type=InterventionType.STRUCTURE_GUIDANCE,
                        message=fallback_msg,
                        reason="topic_drift_detected"
                    )

        return None
        
    def _execute_intervention(self, room_id: str, result: InterventionResult):
        """执行干预操作"""
        try:
            self.total_interventions += 1
            current_time = time.time()
            
            # 记录干预时间
            self.intervention_engine.room_last_intervention_ts[room_id] = current_time
            self.intervention_engine._record_intervention_message(room_id, result.message)
            
            # 保存chatbot消息到数据库，让所有人看到
            with self.app.app_context():
                try:
                    from app import Message, Intervention, db
                    from datetime import datetime as dt
                except ImportError as e:
                    logger.error(f"❌ 导入失败: {e}")
                    return
                
                # 服务端统一语气净化，移除多余标点/轻佻口吻/侮辱词，修正开头逗号
                try:
                    clean_text = self.intervention_engine._sanitize_tone(result.message)
                except Exception:
                    clean_text = result.message

                # 创建chatbot消息记录
                bot_message = Message(
                    content=clean_text,
                    author='Chime',
                    gender='unknown',
                    room_id=int(room_id),
                    user_id=None,  # chatbot没有user_id
                    timestamp=dt.now()
                )
                db.session.add(bot_message)
                db.session.commit()
                
                # 创建干预记录
                intervention_record = Intervention(
                    room_id=int(room_id),
                    message_id=bot_message.id,
                    strategy=result.intervention_type.value,
                    intervention_text=result.message,
                    trigger_type=result.intervention_type.value,
                    trigger_reason=result.reason,
                    intervention_type=result.intervention_type.value,
                    offense_level=result.offense_level.value if result.offense_level else None,
                    target_user=result.target_user,
                    is_visible_to_admin_only=False  # 让所有人看到
                )
                db.session.add(intervention_record)
                db.session.commit()
                
                # 发送正常聊天消息，所有人都能看到
                message_data = {
                    'id': bot_message.id,
                    'content': bot_message.content,
                    'author': bot_message.author,
                    'avatar': '',
                    'timestamp': bot_message.timestamp.isoformat(),
                    'has_interruption': False,
                    'interruption_type': None,
                    'intervention_applied': True,  # 标记这是干预消息
                    'client_id': f'chatbot-{int(time.time() * 1000)}',  # 添加Chatbot的client_id
                    'room': str(room_id)  # 确保房间ID是字符串格式，与用户消息一致
                }
                
                # 发送给房间所有成员
                logger.info(f"📡 [WebSocket] 发送消息到房间{room_id}: {result.message[:30]}...")
                logger.info(f"📡 [WebSocket] 消息数据: {message_data}")
                
                # 使用应用上下文和手动房间管理系统确保正确发送
                with self.app.app_context():
                    # 导入手动房间管理函数
                    from app import manual_emit_to_room, get_room_clients
                    
                    # 使用手动房间管理系统发送消息（与用户消息相同的方式）
                    clients = get_room_clients(room_id)
                    if clients:
                        # 仅手动房间广播（单通道）
                        manual_emit_to_room('message', message_data, room_id)
                        logger.info(f"📡 [WebSocket] 已发送到房间{room_id}（手动房间广播），客户端数: {len(clients)}")
                    else:
                        # 无客户端时，尝试房间广播一次
                        logger.warning(f"⚠️ [WebSocket-手动] 房间{room_id}没有客户端，使用room广播兜底")
                        self.socketio.emit('message', message_data, room=str(room_id))
                        logger.info(f"📡 [WebSocket-传统] 兜底发送到房间{room_id}")

                    # 冗余兜底：再发送一次干预事件，前端也会将其渲染成普通消息
                    try:
                        intervention_payload = {
                            'id': bot_message.id,
                            'message': bot_message.content,
                            'strategy': result.intervention_type.value,
                            'reason': result.reason,
                            'room_id': str(room_id),
                            'timestamp': bot_message.timestamp.isoformat(),
                            'client_id': message_data.get('client_id')
                        }
                        self.socketio.emit('intervention', intervention_payload, room=str(room_id))
                    except Exception as _:
                        pass

                    # 提醒前端回补历史，避免极端情况下漏收（轻量触发一次）
                    try:
                        self.socketio.emit('refresh_messages', {
                            'room_id': str(room_id),
                            'reason': 'chatbot_message_sync'
                        }, room=str(room_id))
                    except Exception as _:
                        pass
                
                # 给管理员发送详细的干预信息
                admin_data = {
                    'type': 'intervention_admin',
                    'message': result.message,
                    'strategy': result.intervention_type.value,
                    'reason': result.reason,
                    'room_id': room_id,
                    'timestamp': dt.now().isoformat(),
                    'via_monitor': True,
                    'target_user': result.target_user
                }
                self.socketio.emit('intervention_admin', admin_data, room='admin_room')
                
                logger.info(f"🤖 [监控干预] 房间{room_id}: {result.intervention_type.value} - {result.message[:50]}...")
                logger.info(f"💾 [数据库] 消息ID: {bot_message.id}, 内容: {bot_message.content[:30]}...")
                logger.info(f"📡 [WebSocket] 已发送到房间{room_id}和所有客户端")
            
        except Exception as e:
            logger.error(f"❌ 执行干预失败: {e}")
            
    def _send_monitoring_status(self):
        """发送监控状态给管理员"""
        try:
            from datetime import datetime
            current_time = time.time()
            
            # 收集每个房间的详细状态
            room_statuses = []
            for room_id in self.active_rooms:
                room_status = self._get_room_status(room_id, current_time)
                if room_status:
                    room_statuses.append(room_status)
            
            # 发送监控状态给管理员
            monitoring_data = {
                'type': 'monitoring_status',
                'timestamp': datetime.now().isoformat(),
                'scan_count': self.total_scans,
                'intervention_count': self.total_interventions,
                'active_rooms_count': len(self.active_rooms),
                'room_statuses': room_statuses,
                'scan_interval': self.scan_interval,
                'silence_threshold': self.max_silence_before_action
            }
            
            self.socketio.emit('monitoring_status', monitoring_data, room='admin_room')
            
        except Exception as e:
            logger.error(f"❌ 发送监控状态失败: {e}")

    def _display_overall_status(self):
        """显示总体监控状态"""
        try:
            # 只在特定条件下显示总体状态，避免过于频繁
            if self.total_scans % 6 == 1:  # 每6次扫描显示一次（约1分钟）
                timestamp = time.strftime('%H:%M:%S')
                print(f"\n🎯 [{timestamp}] 实时监控总览 - 扫描#{self.total_scans}")
                print(f"   📊 活跃房间: {len(self.active_rooms)}个")
                print(f"   🤖 总干预次数: {self.total_interventions}次")
                print(f"   ⏱️ 扫描间隔: {self.scan_interval}秒")
                print(f"   🎚️ 沉默阈值: {self.max_silence_before_action}秒")
                print()
        except Exception as e:
            logger.error(f"❌ 显示总体状态失败: {e}")

    def _get_room_status(self, room_id: str, current_time: float) -> Dict:
        """获取单个房间的状态信息"""
        try:
            room_id = str(room_id)
            
            # 获取房间消息历史
            recent_messages = list(self.intervention_engine.room_recent_messages.get(room_id, []))
            non_admin_messages = [msg for msg in recent_messages if not self.intervention_engine._is_admin_user(str(msg['user_id']))]
            
            # 计算沉默时间
            silence_duration = 0
            user_silence_duration = 0
            last_message_type = "无消息"
            
            if recent_messages:
                last_msg_time = recent_messages[-1]['timestamp']
                silence_duration = current_time - last_msg_time
                last_message_type = "admin消息" if self.intervention_engine._is_admin_user(str(recent_messages[-1]['user_id'])) else "用户消息"
            
            if non_admin_messages:
                last_user_msg_time = non_admin_messages[-1]['timestamp']
                user_silence_duration = current_time - last_user_msg_time
            elif recent_messages:
                # 有admin消息但没有用户消息，从最后一条admin消息开始计算
                user_silence_duration = silence_duration
            else:
                # 完全没有消息
                user_silence_duration = current_time
            
            # 检查是否需要干预
            needs_intervention = user_silence_duration >= self.max_silence_before_action
            
            # 检查冷却状态
            last_intervention_time = self.intervention_engine.room_last_intervention_ts.get(room_id, 0)
            cooldown_remaining = max(0, self.intervention_engine.global_cooldown_seconds - (current_time - last_intervention_time))
            
            last_agenda_time = self.intervention_engine.room_last_agenda_transition.get(room_id, 0)
            agenda_cooldown_remaining = max(0, self.intervention_engine.agenda_transition_cooldown - (current_time - last_agenda_time))
            
            return {
                'room_id': room_id,
                'total_messages': len(recent_messages),
                'user_messages': len(non_admin_messages),
                'silence_duration': int(silence_duration),
                'user_silence_duration': int(user_silence_duration),
                'last_message_type': last_message_type,
                'needs_intervention': needs_intervention,
                'silence_threshold': self.max_silence_before_action,
                'cooldown_remaining': int(cooldown_remaining),
                'agenda_cooldown_remaining': int(agenda_cooldown_remaining),
                'status': self._get_room_status_text(user_silence_duration, needs_intervention, cooldown_remaining, agenda_cooldown_remaining)
            }
            
        except Exception as e:
            logger.error(f"❌ 获取房间{room_id}状态失败: {e}")
            return None

    def _get_room_status_text(self, user_silence_duration: float, needs_intervention: bool, 
                             cooldown_remaining: float, agenda_cooldown_remaining: float) -> str:
        """获取房间状态文本描述"""
        if agenda_cooldown_remaining > 0:
            return f"⏸️ 议程冷却中 ({int(agenda_cooldown_remaining)}s)"
        elif cooldown_remaining > 0:
            return f"❄️ 全局冷却中 ({int(cooldown_remaining)}s)"
        elif needs_intervention:
            return f"🚨 需要破冰干预 ({int(user_silence_duration)}s沉默)"
        elif user_silence_duration >= self.max_silence_before_action * 0.7:
            return f"⚠️ 接近干预阈值 ({int(user_silence_duration)}/{self.max_silence_before_action}s)"
        else:
            return f"✅ 正常 ({int(user_silence_duration)}s沉默)"

    def get_monitor_stats(self) -> Dict:
        """获取监控统计信息"""
        return {
            'is_running': self.is_running,
            'active_rooms': len(self.active_rooms),
            'total_scans': self.total_scans,
            'total_interventions': self.total_interventions,
            'last_scan_time': self.last_scan_time,
            'scan_interval': self.scan_interval
        }

    def _smart_display_detection_status(self, room_id: str, current_time: float):
        """智能显示检测状态，避免频繁刷屏"""
        try:
            # 检查是否需要显示详细状态
            last_display_time = self.last_status_display_time.get(room_id, 0)
            time_since_last_display = current_time - last_display_time
            
            # 计算关键状态
            recent_messages = list(self.intervention_engine.room_recent_messages.get(room_id, []))
            non_admin_messages = [msg for msg in recent_messages if not self.intervention_engine._is_admin_user(str(msg['user_id']))]
            
            user_silence_duration = 0
            if non_admin_messages:
                last_user_msg_time = non_admin_messages[-1]['timestamp']
                user_silence_duration = current_time - last_user_msg_time
            elif recent_messages:
                last_admin_msg_time = recent_messages[-1]['timestamp']
                user_silence_duration = current_time - last_admin_msg_time
            else:
                user_silence_duration = current_time
            
            # 决定是否显示详细状态
            needs_intervention = user_silence_duration >= self.max_silence_before_action
            approaching_threshold = user_silence_duration >= self.max_silence_before_action * 0.8
            
            should_display_full = (
                time_since_last_display >= self.status_display_interval or  # 定时显示
                needs_intervention or  # 需要干预时
                approaching_threshold or  # 接近阈值时
                last_display_time == 0  # 首次显示
            )
            
            if should_display_full:
                self._display_room_detection_status(room_id, current_time)
                self.last_status_display_time[room_id] = current_time
            else:
                # 显示简化状态
                self._display_simple_status(room_id, current_time, user_silence_duration)
                
        except Exception as e:
            logger.error(f"❌ 智能显示失败: {e}")

    def _display_simple_status(self, room_id: str, current_time: float, user_silence_duration: float):
        """显示简化的监控状态"""
        try:
            timestamp = time.strftime('%H:%M:%S')
            status_icon = "🚨" if user_silence_duration >= self.max_silence_before_action else "⚠️" if user_silence_duration >= self.max_silence_before_action * 0.8 else "✅"
            
            print(f"🔍 [{timestamp}] 房间{room_id} {status_icon} 用户沉默: {int(user_silence_duration)}s/{self.max_silence_before_action}s")
            
        except Exception as e:
            logger.error(f"❌ 简化状态显示失败: {e}")

    def _display_room_detection_status(self, room_id: str, current_time: float):
        """在terminal显示房间的详细检测状态"""
        try:
            room_id = str(room_id)
            
            # 获取房间基本信息
            recent_messages = list(self.intervention_engine.room_recent_messages.get(room_id, []))
            non_admin_messages = [msg for msg in recent_messages if not self.intervention_engine._is_admin_user(str(msg['user_id']))]
            
            # 计算沉默时间
            user_silence_duration = 0
            if non_admin_messages:
                last_user_msg_time = non_admin_messages[-1]['timestamp']
                user_silence_duration = current_time - last_user_msg_time
            elif recent_messages:
                # 有admin消息但没有用户消息
                last_admin_msg_time = recent_messages[-1]['timestamp']
                user_silence_duration = current_time - last_admin_msg_time
            else:
                user_silence_duration = current_time
            
            # 打印分隔线和标题
            print("=" * 80)
            print(f"🔍 房间 {room_id} - 实时检测状态 [{time.strftime('%H:%M:%S')}]")
            print("=" * 80)
            
            # 1. 基本状态
            print(f"📊 基本信息:")
            print(f"   总消息数: {len(recent_messages)}")
            print(f"   用户消息: {len(non_admin_messages)}")
            print(f"   用户沉默: {int(user_silence_duration)}秒")
            print(f"   沉默阈值: {self.max_silence_before_action}秒")
            
            # 2. 沉默检测
            print(f"\n🤫 沉默检测:")
            try:
                silence_result = self.intervention_engine._check_silence_intervention(room_id, dry_run=True)
                if silence_result and silence_result.should_intervene:
                    print(f"   状态: 🚨 检测到沉默用户")
                    print(f"   目标: {silence_result.target_user}")
                    print(f"   类型: {silence_result.intervention_type.value}")
                    print(f"   消息: {silence_result.message[:60]}...")
                else:
                    print(f"   状态: ✅ 用户参与正常")
            except Exception as e:
                print(f"   状态: ❌ 检测失败: {e}")
            
            # 3. 议程过渡检测（展示使用 dry_run，避免消耗冷却却不发送）
            print(f"\n🎯 议程过渡:")
            try:
                agenda_result = self.intervention_engine._check_agenda_transition(room_id, dry_run=True)
                if agenda_result and agenda_result.should_intervene:
                    print(f"   状态: 🚨 需要话题引导")
                    print(f"   原因: {agenda_result.reason}")
                    print(f"   消息: {agenda_result.message[:60]}...")
                else:
                    print(f"   状态: ✅ 话题流畅")
                    # 显示冷却状态
                    last_agenda_time = self.intervention_engine.room_last_agenda_transition.get(room_id, 0)
                    agenda_cooldown = max(0, self.intervention_engine.agenda_transition_cooldown - (current_time - last_agenda_time))
                    if agenda_cooldown > 0:
                        print(f"   冷却: ⏸️ 剩余{int(agenda_cooldown)}秒")
            except Exception as e:
                print(f"   状态: ❌ 检测失败: {e}")
            
            # 4. 活跃讨论状态
            print(f"\n💬 活跃讨论:")
            try:
                is_active = self.intervention_engine._is_active_discussion(room_id)
                print(f"   状态: {'🔥 讨论活跃' if is_active else '😴 讨论较少'}")
            except Exception as e:
                print(f"   状态: ❌ 检测失败: {e}")
            
            # 5. 话题相关性
            print(f"\n⚽ 话题检测:")
            try:
                if len(recent_messages) >= 3:
                    is_on_topic = self.intervention_engine._is_on_topic_football(room_id)
                    print(f"   状态: {'⚽ 在足球话题内' if is_on_topic else '🔄 偏离主题'}")
                    
                    if not is_on_topic:
                        # 仅展示预期文案，不触发实际检测/冷却
                        try:
                            preview = self.intervention_engine._compose_topic_pullback(room_id, reason="off_topic")
                            print(f"   引导: 🔄 需要话题拉回")
                            print(f"   消息: {preview[:60]}...")
                        except Exception:
                            print(f"   引导: 🔄 需要话题拉回 (预览生成失败)")
                else:
                    print(f"   状态: ⏳ 消息不足 (需要3条以上)")
            except Exception as e:
                print(f"   状态: ❌ 检测失败: {e}")
            
            # 6. 冲突检测
            print(f"\n⚠️ 冲突检测:")
            try:
                if recent_messages:
                    last_message = recent_messages[-1]
                    conflict_keywords = ['讨厌', '愚蠢', '垃圾', '恶心', '烂', '差劲', '拉踩']
                    has_conflict = any(keyword in last_message.get('content', '') for keyword in conflict_keywords)
                    print(f"   状态: {'⚠️ 检测到冲突语言' if has_conflict else '✅ 氛围良好'}")
                    if has_conflict:
                        print(f"   最近: {last_message.get('content', '')[:40]}...")
                else:
                    print(f"   状态: ⏳ 无消息记录")
            except Exception as e:
                print(f"   状态: ❌ 检测失败: {e}")
            
            # 7. 全局状态
            print(f"\n🔧 系统状态:")
            last_intervention_time = self.intervention_engine.room_last_intervention_ts.get(room_id, 0)
            global_cooldown = max(0, self.intervention_engine.global_cooldown_seconds - (current_time - last_intervention_time))
            if global_cooldown > 0:
                print(f"   全局冷却: ❄️ 剩余{int(global_cooldown)}秒")
            else:
                print(f"   全局冷却: ✅ 可以干预")
            
            print(f"   扫描次数: {self.total_scans}")
            print(f"   干预次数: {self.total_interventions}")
            
            print("=" * 80)
            print()  # 空行分隔
            
        except Exception as e:
            logger.error(f"❌ 显示检测状态失败: {e}")
            print(f"❌ 房间{room_id}状态显示失败: {e}")
            print("=" * 80)
            print()