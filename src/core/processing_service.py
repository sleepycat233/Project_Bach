#!/usr/bin/env python3.11
"""
处理状态跟踪服务
负责管理音频和YouTube内容的处理状态，提供实时进度更新
"""

import time
import uuid
import logging
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


class ProcessingStage(Enum):
    """处理阶段枚举"""
    UPLOADED = "uploaded"
    TRANSCRIBING = "transcribing"
    ANONYMIZING = "anonymizing"
    AI_GENERATING = "ai_generating"
    PUBLISHING = "publishing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingStatus:
    """处理状态类"""
    
    def __init__(self, processing_id: str, content_type: str, privacy_level: str = 'public'):
        self.processing_id = processing_id
        self.content_type = content_type  # 'audio' or 'youtube'
        self.privacy_level = privacy_level
        self.stage = ProcessingStage.UPLOADED
        self.progress = 0  # 0-100
        self.message = "处理已开始"
        self.created_time = datetime.now()
        self.updated_time = datetime.now()
        self.metadata = {}
        self.error_message = None
        self.result_url = None
        self.processing_logs = []  # 新增：处理日志列表
        
    def add_log(self, message: str, level: str = 'info'):
        """添加处理日志"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message
        }
        self.processing_logs.append(log_entry)
        # 保留最新100条日志
        if len(self.processing_logs) > 100:
            self.processing_logs = self.processing_logs[-100:]
        
    def update_stage(self, stage: ProcessingStage, progress: int = None, message: str = None):
        """更新处理阶段"""
        self.stage = stage
        if progress is not None:
            self.progress = progress
        if message:
            self.message = message
            self.add_log(f"[{stage.value}] {message}", 'info')
        self.updated_time = datetime.now()
        
    def set_error(self, error_message: str):
        """设置错误状态"""
        self.stage = ProcessingStage.FAILED
        self.error_message = error_message
        self.message = f"处理失败: {error_message}"
        self.add_log(f"❌ 处理失败: {error_message}", 'error')
        self.updated_time = datetime.now()
        
    def set_completed(self, result_url: str = None):
        """设置完成状态"""
        self.stage = ProcessingStage.COMPLETED
        self.progress = 100
        self.result_url = result_url
        self.message = "Processing completed" + (f" - {result_url}" if result_url else "")
        self.add_log(f"✅ Processing completed" + (f" - {result_url}" if result_url else ""), 'success')
        self.updated_time = datetime.now()
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'processing_id': self.processing_id,
            'content_type': self.content_type,
            'privacy_level': self.privacy_level,
            'stage': self.stage.value,
            'progress': self.progress,
            'message': self.message,
            'created_time': self.created_time.isoformat(),
            'updated_time': self.updated_time.isoformat(),
            'metadata': self.metadata,
            'error_message': self.error_message,
            'result_url': self.result_url,
            'processing_logs': self.processing_logs
        }


class ProcessingService:
    """处理状态跟踪服务"""
    
    def __init__(self):
        self.logger = logging.getLogger('project_bach.processing_service')
        self._statuses: Dict[str, ProcessingStatus] = {}
        self._lock = threading.Lock()
        
    def create_processing_session(self, content_type: str, privacy_level: str = 'public', 
                                 metadata: Dict[str, Any] = None) -> str:
        """创建新的处理会话
        
        Args:
            content_type: 内容类型 ('audio' 或 'youtube')
            privacy_level: 隐私级别
            metadata: 额外元数据
            
        Returns:
            处理ID
        """
        processing_id = str(uuid.uuid4())
        
        with self._lock:
            status = ProcessingStatus(processing_id, content_type, privacy_level)
            if metadata:
                status.metadata.update(metadata)
            self._statuses[processing_id] = status
            
        self.logger.info(f"创建处理会话: {processing_id} ({content_type}, {privacy_level})")
        return processing_id
        
    def update_status(self, processing_id: str, stage: ProcessingStage, 
                     progress: int = None, message: str = None) -> bool:
        """更新处理状态
        
        Args:
            processing_id: 处理ID
            stage: 处理阶段
            progress: 进度百分比
            message: 状态消息
            
        Returns:
            是否更新成功
        """
        with self._lock:
            if processing_id not in self._statuses:
                self.logger.warning(f"处理ID不存在: {processing_id}")
                return False
                
            status = self._statuses[processing_id]
            status.update_stage(stage, progress, message)
            
        self.logger.debug(f"更新处理状态: {processing_id} -> {stage.value} ({progress}%)")
        return True
        
    def add_log(self, processing_id: str, message: str, level: str = 'info') -> bool:
        """为指定处理会话添加日志
        
        Args:
            processing_id: 处理ID
            message: 日志消息
            level: 日志级别 ('info', 'warning', 'error', 'success')
            
        Returns:
            是否添加成功
        """
        with self._lock:
            if processing_id not in self._statuses:
                self.logger.warning(f"处理ID不存在: {processing_id}")
                return False
                
            status = self._statuses[processing_id]
            status.add_log(message, level)
            
        return True
        
    def set_error(self, processing_id: str, error_message: str) -> bool:
        """设置错误状态"""
        with self._lock:
            if processing_id not in self._statuses:
                return False
                
            status = self._statuses[processing_id]
            status.set_error(error_message)
            
        self.logger.error(f"处理失败: {processing_id} - {error_message}")
        return True
        
    def set_completed(self, processing_id: str, result_url: str = None) -> bool:
        """设置完成状态"""
        with self._lock:
            if processing_id not in self._statuses:
                return False
                
            status = self._statuses[processing_id]
            status.set_completed(result_url)
            
        self.logger.info(f"Processing completed: {processing_id}")
        return True
        
    def get_status(self, processing_id: str) -> Optional[Dict[str, Any]]:
        """获取处理状态"""
        with self._lock:
            if processing_id not in self._statuses:
                return None
            return self._statuses[processing_id].to_dict()
            
    def list_active_sessions(self) -> List[Dict[str, Any]]:
        """列出所有活跃的处理会话"""
        with self._lock:
            active_sessions = []
            for status in self._statuses.values():
                if status.stage not in [ProcessingStage.COMPLETED, ProcessingStage.FAILED]:
                    active_sessions.append(status.to_dict())
            return active_sessions
            
    def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """清理旧的处理会话
        
        Args:
            max_age_hours: 最大保留时间（小时）
            
        Returns:
            清理的会话数量
        """
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        cleaned_count = 0
        
        with self._lock:
            expired_ids = []
            for processing_id, status in self._statuses.items():
                if status.updated_time.timestamp() < cutoff_time:
                    expired_ids.append(processing_id)
                    
            for processing_id in expired_ids:
                del self._statuses[processing_id]
                cleaned_count += 1
                
        if cleaned_count > 0:
            self.logger.info(f"清理了 {cleaned_count} 个过期处理会话")
            
        return cleaned_count


# 全局单例实例
_processing_service = None
_service_lock = threading.Lock()


def get_processing_service() -> ProcessingService:
    """获取处理服务的全局单例"""
    global _processing_service
    
    with _service_lock:
        if _processing_service is None:
            _processing_service = ProcessingService()
    
    return _processing_service


class ProcessingTracker:
    """处理状态跟踪器 - 上下文管理器"""
    
    def __init__(self, content_type: str, privacy_level: str = 'public', 
                 metadata: Dict[str, Any] = None):
        self.content_type = content_type
        self.privacy_level = privacy_level
        self.metadata = metadata or {}
        self.processing_id = None
        self.service = get_processing_service()
        
    def __enter__(self):
        """进入上下文"""
        self.processing_id = self.service.create_processing_session(
            self.content_type, self.privacy_level, self.metadata
        )
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        if exc_type is not None:
            # 发生异常
            error_msg = str(exc_val) if exc_val else "未知错误"
            self.service.set_error(self.processing_id, error_msg)
        
    def update_stage(self, stage: ProcessingStage, progress: int = None, message: str = None):
        """更新处理阶段"""
        if self.processing_id:
            self.service.update_status(self.processing_id, stage, progress, message)
            
    def set_completed(self, result_url: str = None):
        """设置完成状态"""
        if self.processing_id:
            self.service.set_completed(self.processing_id, result_url)
            
    def set_error(self, error_message: str):
        """设置错误状态"""
        if self.processing_id:
            self.service.set_error(self.processing_id, error_message)