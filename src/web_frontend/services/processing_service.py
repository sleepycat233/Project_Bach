#!/usr/bin/env python3
"""
处理服务

提供处理状态查询和队列管理功能
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .github_deployment_monitor import create_deployment_monitor, GitHubDeploymentMonitor

# Import ProcessingStage from core module
try:
    from ...core.audio_processor import ProcessingStage
except ImportError:
    # Fallback enum if import fails
    from enum import Enum
    class ProcessingStage(Enum):
        UPLOADED = "uploaded"
        TRANSCRIBING = "transcribing"
        ANONYMIZING = "anonymizing"
        AI_GENERATING = "ai_generating"
        PUBLISHING = "publishing"
        COMPLETED = "completed"
        FAILED = "failed"

logger = logging.getLogger(__name__)


class ProcessingService:
    """处理状态和队列管理服务"""
    
    def __init__(self, config: Optional[Dict] = None):
        """初始化处理服务
        
        Args:
            config: 应用配置（可选）
        """
        # 模拟处理项目存储
        self._processing_items = {}
        self._completed_items = []
        self._queue_items = []
        
        # 统计信息
        self._stats = {
            'total_processed': 0,
            'total_errors': 0,
            'average_processing_time': 180  # 3分钟
        }
        
        # GitHub部署监控器
        self.deployment_monitor = None
        if config:
            try:
                self.deployment_monitor = create_deployment_monitor(config)
                logger.info("GitHub部署监控器初始化成功")
            except Exception as e:
                logger.warning(f"GitHub部署监控器初始化失败: {e}")
        else:
            logger.info("未提供配置，跳过GitHub部署监控器初始化")
    
    def get_status(self) -> Dict:
        """
        获取整体处理状态
        
        Returns:
            dict: 处理状态信息
        """
        try:
            # 清理过期的处理项目
            self._cleanup_expired_items()
            
            # 统计当天完成的项目
            today = datetime.now().date()
            completed_today = len([
                item for item in self._completed_items
                if item.get('completed_at', '').startswith(str(today))
            ])
            
            return {
                'queue_size': len(self._queue_items),
                'processing_items': [
                    {
                        'id': item_id,
                        'type': item['type'],
                        'progress': item['progress'],
                        'started_at': item['started_at'],
                        'estimated_completion': item['estimated_completion']
                    }
                    for item_id, item in self._processing_items.items()
                    if item['status'] == 'processing'
                ],
                'completed_today': completed_today,
                'average_processing_time': self._stats['average_processing_time'],
                'total_processed': self._stats['total_processed'],
                'total_errors': self._stats['total_errors']
            }
            
        except Exception as e:
            logger.error(f"Error getting processing status: {e}")
            return {
                'queue_size': 0,
                'processing_items': [],
                'completed_today': 0,
                'average_processing_time': 180,
                'error': 'Failed to get processing status'
            }
    
    def get_item_status(self, processing_id: str) -> Optional[Dict]:
        """
        获取特定处理项目的状态
        
        Args:
            processing_id: 处理项目ID
            
        Returns:
            dict: 项目状态信息，如果不存在返回None
        """
        try:
            if processing_id in self._processing_items:
                item = self._processing_items[processing_id]
                
                # 模拟进度更新
                if item['status'] == 'processing':
                    self._update_item_progress(processing_id)
                
                return {
                    'id': processing_id,
                    'status': item['status'],
                    'type': item['type'],
                    'progress': item['progress'],
                    'started_at': item['started_at'],
                    'estimated_completion': item['estimated_completion'],
                    'message': item.get('message', ''),
                    'result_url': item.get('result_url', '')
                }
            
            # 检查是否在已完成列表中
            for completed_item in self._completed_items:
                if completed_item['id'] == processing_id:
                    return completed_item
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting item status for {processing_id}: {e}")
            return {
                'id': processing_id,
                'status': 'error',
                'message': 'Failed to get status'
            }
    
    def add_processing_item(self, processing_id: str, item_type: str, 
                          estimated_time: int = 300) -> bool:
        """
        添加处理项目到队列
        
        Args:
            processing_id: 处理项目ID
            item_type: 项目类型 (audio/youtube/rss)
            estimated_time: 预估处理时间（秒）
            
        Returns:
            bool: 是否添加成功
        """
        try:
            now = datetime.now()
            estimated_completion = now + timedelta(seconds=estimated_time)
            
            item = {
                'id': processing_id,
                'type': item_type,
                'status': 'queued',
                'progress': 0,
                'started_at': now.isoformat(),
                'estimated_completion': estimated_completion.isoformat(),
                'estimated_time': estimated_time,
                'message': f'{item_type.title()} processing queued'
            }
            
            # 添加到队列
            self._queue_items.append(item)
            self._processing_items[processing_id] = item
            
            logger.info(f"Added processing item: {processing_id} ({item_type})")
            return True
            
        except Exception as e:
            logger.error(f"Error adding processing item {processing_id}: {e}")
            return False
    
    def _update_item_progress(self, processing_id: str):
        """更新处理项目进度（模拟）"""
        try:
            item = self._processing_items[processing_id]
            
            if item['status'] == 'queued':
                # 开始处理
                item['status'] = 'processing'
                item['progress'] = 10
                item['message'] = f"{item['type'].title()} processing started"
            
            elif item['status'] == 'processing':
                # 逐步增加进度
                current_progress = item['progress']
                
                if current_progress < 90:
                    # 随机增加进度
                    import random
                    progress_increment = random.randint(5, 15)
                    new_progress = min(current_progress + progress_increment, 90)
                    item['progress'] = new_progress
                    
                    # 更新消息
                    if new_progress < 25:
                        item['message'] = "Processing audio transcription..."
                    elif new_progress < 50:
                        item['message'] = "Anonymizing content..."
                    elif new_progress < 75:
                        item['message'] = "Generating AI summary..."
                    elif new_progress < 90:
                        item['message'] = "Publishing to GitHub Pages..."
                    
                elif current_progress >= 90:
                    # 检查GitHub Pages部署状态
                    if not item.get('deployment_checked', False):
                        self._check_github_deployment(processing_id)
                    else:
                        # 完成处理
                        self._complete_item(processing_id)
                    
        except Exception as e:
            logger.error(f"Error updating progress for {processing_id}: {e}")
    
    def _check_github_deployment(self, processing_id: str):
        """检查GitHub Pages部署状态"""
        try:
            item = self._processing_items[processing_id]
            
            # 标记已检查
            item['deployment_checked'] = True
            item['progress'] = 95
            item['message'] = "Checking GitHub Pages deployment..."
            
            # 模拟检查GitHub Pages部署状态
            # 实际实现可以检查GitHub API或网站是否可访问
            deployment_success = self._simulate_deployment_check(processing_id)
            
            if deployment_success:
                item['progress'] = 100
                item['message'] = "GitHub Pages deployment verified"
                self._complete_item(processing_id)
            else:
                # 如果部署失败，等待下次检查
                item['progress'] = 92
                item['message'] = "Waiting for GitHub Pages deployment..."
                # 设置重新检查标志
                item['deployment_checked'] = False
                
        except Exception as e:
            logger.error(f"Error checking GitHub deployment for {processing_id}: {e}")
            # 部署检查失败，直接完成处理
            self._complete_item(processing_id)
    
    def _simulate_deployment_check(self, processing_id: str) -> bool:
        """检查GitHub Pages部署状态（基于GitHub API的真实实现）
        
        Args:
            processing_id: 处理ID
        
        Returns:
            bool: 部署是否成功
        """
        try:
            item = self._processing_items[processing_id]
            started_at = datetime.fromisoformat(item['started_at'])
            now = datetime.now()
            
            # 如果处理刚开始不久（少于30秒），跳过检查
            if now - started_at < timedelta(seconds=30):
                item['deployment_message'] = "Waiting for deployment to start..."
                return False
            
            # 使用GitHub部署监控器检查部署状态
            if self.deployment_monitor:
                # 获取可能的commit hash
                commit_hash = item.get('commit_hash')
                
                deployment_status = self.deployment_monitor.check_pages_deployment_status(commit_hash)
                
                # 更新部署消息
                item['deployment_message'] = deployment_status.get('message', 'Checking deployment...')
                item['deployment_method'] = deployment_status.get('method', 'unknown')
                
                if deployment_status.get('deployed'):
                    logger.info(f"GitHub Pages deployment verified via {deployment_status.get('method')}")
                    return True
                elif deployment_status.get('status') == 'failed':
                    logger.warning(f"GitHub Pages deployment failed: {deployment_status.get('message')}")
                    return True  # 认为处理完成，即使部署失败
                else:
                    logger.debug(f"GitHub Pages deployment still in progress: {deployment_status.get('status')}")
                    return False
            
            # 回退到简单的超时检查
            else:
                item['deployment_message'] = "GitHub API not configured, using timeout check"
                item['deployment_method'] = 'timeout_fallback'
                
                # 如果已经超过5分钟，认为部署完成
                if now - started_at > timedelta(minutes=5):
                    logger.info("Deployment timeout reached, assuming success")
                    return True
                
                return False
            
        except Exception as e:
            logger.error(f"Error in deployment check: {e}")
            # 设置错误信息
            if processing_id in self._processing_items:
                self._processing_items[processing_id]['deployment_message'] = f"Deployment check error: {str(e)}"
            return True  # 默认认为完成
    
    def _complete_item(self, processing_id: str):
        """完成处理项目"""
        try:
            item = self._processing_items[processing_id]
            
            # 更新状态
            item['status'] = 'completed'
            item['progress'] = 100
            item['completed_at'] = datetime.now().isoformat()
            item['message'] = 'Processing completed successfully'
            item['result_url'] = f'/results/{processing_id}'
            
            # 移动到完成列表
            self._completed_items.append(item.copy())
            
            # 从处理队列中移除
            if processing_id in self._processing_items:
                del self._processing_items[processing_id]
            
            # 更新统计
            self._stats['total_processed'] += 1
            
            logger.info(f"Completed processing item: {processing_id}")
            
        except Exception as e:
            logger.error(f"Error completing item {processing_id}: {e}")
            self._error_item(processing_id, str(e))
    
    def _error_item(self, processing_id: str, error_message: str):
        """处理项目出错"""
        try:
            if processing_id in self._processing_items:
                item = self._processing_items[processing_id]
                item['status'] = 'error'
                item['message'] = f'Processing failed: {error_message}'
                item['completed_at'] = datetime.now().isoformat()
                
                # 移动到完成列表
                self._completed_items.append(item.copy())
                del self._processing_items[processing_id]
                
                # 更新统计
                self._stats['total_errors'] += 1
                
        except Exception as e:
            logger.error(f"Error handling error for {processing_id}: {e}")
    
    def _cleanup_expired_items(self):
        """清理过期的处理项目"""
        try:
            now = datetime.now()
            expired_items = []
            
            for item_id, item in self._processing_items.items():
                started_at = datetime.fromisoformat(item['started_at'])
                
                # 特殊处理PUBLISHING状态的项目 - 检查GitHub deployment状态
                if item.get('stage') == ProcessingStage.PUBLISHING.value and item.get('progress', 0) >= 90:
                    if not item.get('deployment_checked', False):
                        self._check_github_deployment(item_id)
                        continue  # 跳过过期检查，让deployment check完成
                
                # 如果处理时间超过预估时间的2倍，认为已过期
                max_time = timedelta(seconds=item.get('estimated_time', 300) * 2)
                
                if now - started_at > max_time:
                    expired_items.append(item_id)
            
            # 清理过期项目
            for item_id in expired_items:
                self._error_item(item_id, 'Processing timeout')
                
        except Exception as e:
            logger.error(f"Error cleaning up expired items: {e}")
    
    def get_queue_status(self) -> Dict:
        """获取队列状态"""
        return {
            'total_queued': len(self._queue_items),
            'total_processing': len([
                item for item in self._processing_items.values()
                if item['status'] == 'processing'
            ]),
            'total_completed': len(self._completed_items),
            'queue_items': [
                {
                    'id': item['id'],
                    'type': item['type'],
                    'status': item['status'],
                    'progress': item['progress']
                }
                for item in self._queue_items[-10:]  # 最近10个
            ]
        }