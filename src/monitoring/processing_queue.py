#!/usr/bin/env python3.11
"""
处理队列管理模块
负责管理文件处理队列和状态跟踪
"""

import queue
import threading
import logging
from typing import Dict, Optional, List, Set
from enum import Enum
from datetime import datetime
import time
from pathlib import Path


class ProcessingStatus(Enum):
    """处理状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProcessingQueue:
    """处理队列管理器"""

    def __init__(self, max_size: int = 100):
        """初始化处理队列

        Args:
            max_size: 队列最大大小
        """
        self.queue = queue.Queue(maxsize=max_size)
        self.processing_status: Dict[str, ProcessingStatus] = {}
        self.processing_metadata: Dict[str, Dict] = {}
        self.pending_metadata: Dict[str, Dict] = {}
        self.lock = threading.Lock()
        self.logger = logging.getLogger('project_bach.processing_queue')

    def register_metadata(self, file_path: str, metadata: Dict) -> None:
        """预注册文件的处理元数据，当文件稍后入队时合并使用。"""
        with self.lock:
            normalized_path = str(Path(file_path).resolve())
            self.pending_metadata[normalized_path] = dict(metadata)

    def add_file(self, file_path: str, metadata: Dict = None) -> bool:
        """添加文件到队列

        Args:
            file_path: 文件路径
            metadata: 可选的元数据

        Returns:
            是否成功添加
        """
        with self.lock:
            # 防止重复处理
            if file_path in self.processing_status:
                current_status = self.processing_status[file_path]
                if current_status in [ProcessingStatus.PENDING, ProcessingStatus.PROCESSING]:
                    self.logger.warning(f"文件已在队列中或正在处理: {file_path}")
                    return False

            try:
                self.queue.put(file_path, block=False)
                merged_metadata = dict(metadata or {})
                if file_path in self.pending_metadata:
                    merged_metadata = {**self.pending_metadata.pop(file_path), **merged_metadata}

                self.processing_status[file_path] = ProcessingStatus.PENDING
                self.processing_metadata[file_path] = {
                    'added_time': datetime.now(),
                    'metadata': merged_metadata,
                    'retry_count': 0
                }

                self.logger.info(f"文件已添加到处理队列: {file_path}")
                return True

            except queue.Full:
                self.logger.error(f"队列已满，无法添加文件: {file_path}")
                return False

    def get_file(self, timeout: float = 1.0) -> Optional[str]:
        """从队列获取文件

        Args:
            timeout: 超时时间（秒）

        Returns:
            文件路径或None
        """
        try:
            file_path = self.queue.get(timeout=timeout)
            with self.lock:
                self.processing_status[file_path] = ProcessingStatus.PROCESSING
                if file_path in self.processing_metadata:
                    self.processing_metadata[file_path]['start_time'] = datetime.now()

            self.logger.debug(f"从队列获取文件: {file_path}")
            return file_path

        except queue.Empty:
            return None

    def get_file_metadata(self, file_path: str) -> Dict:
        """获取队列中文件的元数据"""
        with self.lock:
            entry = self.processing_metadata.get(file_path)
            if entry:
                metadata = entry.get('metadata', {})
                if isinstance(metadata, dict):
                    return metadata.copy()
        return {}

    def is_tracking(self, file_path: str) -> bool:
        """判断文件是否已在队列或处理中"""
        with self.lock:
            return file_path in self.processing_status

    def update_file_metadata(self, file_path: str, extra_metadata: Dict) -> bool:
        """更新已存在文件的元数据"""
        with self.lock:
            entry = self.processing_metadata.get(file_path)
            if not entry:
                return False

            metadata = entry.setdefault('metadata', {})
            if isinstance(metadata, dict):
                metadata.update(extra_metadata)
            else:
                entry['metadata'] = extra_metadata.copy()
            return True

    def mark_completed(self, file_path: str, result_data: Dict = None):
        """标记文件处理完成

        Args:
            file_path: 文件路径
            result_data: 可选的结果数据
        """
        with self.lock:
            self.processing_status[file_path] = ProcessingStatus.COMPLETED
            if file_path in self.processing_metadata:
                self.processing_metadata[file_path].update({
                    'completed_time': datetime.now(),
                    'result_data': result_data or {}
                })

        self.logger.info(f"文件处理完成: {file_path}")

    def mark_failed(self, file_path: str, error_message: str = None, retry: bool = False):
        """标记文件处理失败

        Args:
            file_path: 文件路径
            error_message: 错误消息
            retry: 是否重新加入队列重试
        """
        with self.lock:
            if file_path in self.processing_metadata:
                metadata = self.processing_metadata[file_path]
                metadata['retry_count'] = metadata.get('retry_count', 0) + 1
                metadata['last_error'] = error_message
                metadata['failed_time'] = datetime.now()

                # 检查是否应该重试
                if retry and metadata['retry_count'] < 3:
                    try:
                        self.queue.put(file_path, block=False)
                        self.processing_status[file_path] = ProcessingStatus.PENDING
                        self.logger.warning(f"文件处理失败，重新加入队列 (重试 {metadata['retry_count']}/3): {file_path}")
                        return
                    except queue.Full:
                        self.logger.error(f"队列已满，无法重试: {file_path}")

            self.processing_status[file_path] = ProcessingStatus.FAILED

        self.logger.error(f"文件处理失败: {file_path}, 错误: {error_message}")

    def mark_cancelled(self, file_path: str):
        """标记文件处理被取消

        Args:
            file_path: 文件路径
        """
        with self.lock:
            self.processing_status[file_path] = ProcessingStatus.CANCELLED
            if file_path in self.processing_metadata:
                self.processing_metadata[file_path]['cancelled_time'] = datetime.now()

        self.logger.info(f"文件处理被取消: {file_path}")

    def get_status(self, file_path: str) -> ProcessingStatus:
        """获取文件处理状态

        Args:
            file_path: 文件路径

        Returns:
            处理状态
        """
        with self.lock:
            return self.processing_status.get(file_path, ProcessingStatus.PENDING)

    def get_metadata(self, file_path: str) -> Optional[Dict]:
        """获取文件处理元数据

        Args:
            file_path: 文件路径

        Returns:
            元数据字典或None
        """
        with self.lock:
            return self.processing_metadata.get(file_path, {}).copy()

    def is_empty(self) -> bool:
        """检查队列是否为空

        Returns:
            队列是否为空
        """
        return self.queue.empty()

    def get_queue_size(self) -> int:
        """获取队列大小

        Returns:
            队列中待处理的文件数量
        """
        return self.queue.qsize()

    def get_all_status(self) -> Dict[str, str]:
        """获取所有文件的处理状态

        Returns:
            文件路径到状态的映射
        """
        with self.lock:
            return {path: status.value for path, status in self.processing_status.items()}

    def get_files_by_status(self, status: ProcessingStatus) -> List[str]:
        """获取指定状态的文件列表

        Args:
            status: 目标状态

        Returns:
            文件路径列表
        """
        with self.lock:
            return [path for path, file_status in self.processing_status.items()
                   if file_status == status]

    def clear_completed(self) -> int:
        """清理已完成的文件记录

        Returns:
            清理的记录数量
        """
        with self.lock:
            completed_files = [
                path for path, status in self.processing_status.items()
                if status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED, ProcessingStatus.CANCELLED]
            ]

            for file_path in completed_files:
                del self.processing_status[file_path]
                if file_path in self.processing_metadata:
                    del self.processing_metadata[file_path]

            self.logger.info(f"清理了 {len(completed_files)} 个已完成的文件记录")
            return len(completed_files)

    def cancel_pending_files(self) -> int:
        """取消所有待处理的文件

        Returns:
            取消的文件数量
        """
        cancelled_count = 0

        # 清空队列
        try:
            while not self.queue.empty():
                file_path = self.queue.get_nowait()
                self.mark_cancelled(file_path)
                cancelled_count += 1
        except queue.Empty:
            pass

        # 标记所有待处理状态的文件为取消
        with self.lock:
            pending_files = [
                path for path, status in self.processing_status.items()
                if status == ProcessingStatus.PENDING
            ]

            for file_path in pending_files:
                self.processing_status[file_path] = ProcessingStatus.CANCELLED
                if file_path in self.processing_metadata:
                    self.processing_metadata[file_path]['cancelled_time'] = datetime.now()
                cancelled_count += 1

        if cancelled_count > 0:
            self.logger.info(f"取消了 {cancelled_count} 个待处理文件")

        return cancelled_count

    def get_processing_stats(self) -> Dict[str, int]:
        """获取处理统计信息

        Returns:
            统计信息字典
        """
        with self.lock:
            stats = {
                'pending': 0,
                'processing': 0,
                'completed': 0,
                'failed': 0,
                'cancelled': 0,
                'total': len(self.processing_status)
            }

            for status in self.processing_status.values():
                stats[status.value] += 1

            stats['queue_size'] = self.queue.qsize()

            return stats

    def remove_file(self, file_path: str) -> bool:
        """从队列和状态中移除文件

        Args:
            file_path: 文件路径

        Returns:
            是否成功移除
        """
        with self.lock:
            # 从状态中移除
            removed = False
            if file_path in self.processing_status:
                del self.processing_status[file_path]
                removed = True

            if file_path in self.processing_metadata:
                del self.processing_metadata[file_path]
                removed = True

            # 注意：无法直接从queue.Queue中移除特定项目
            # 如果需要这个功能，可能需要使用不同的数据结构

            if removed:
                self.logger.info(f"文件已从队列状态中移除: {file_path}")

            return removed
