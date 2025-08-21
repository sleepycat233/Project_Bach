#!/usr/bin/env python3.11
"""
文件监控模块
负责监控文件夹变化并管理文件处理
"""

import os
import time
import threading
import signal
import logging
from pathlib import Path
from typing import Callable, Optional, Dict, Any
from watchdog.observers import Observer

from .event_handler import AudioFileHandler
from .processing_queue import ProcessingQueue, ProcessingStatus


class FileMonitor:
    """文件监控器"""
    
    def __init__(self, 
                 watch_folder: str, 
                 file_processor_callback: Callable[[str], bool],
                 queue_max_size: int = 100):
        """初始化文件监控器
        
        Args:
            watch_folder: 监控的文件夹路径
            file_processor_callback: 文件处理回调函数，返回bool表示是否成功
            queue_max_size: 处理队列最大大小
        """
        self.watch_folder = Path(watch_folder)
        self.file_processor_callback = file_processor_callback
        self.logger = logging.getLogger('project_bach.file_monitor')
        
        # 确保监控文件夹存在
        self.watch_folder.mkdir(parents=True, exist_ok=True)
        
        # 初始化组件
        self.processing_queue = ProcessingQueue(queue_max_size)
        self.observer = Observer()
        self.event_handler = AudioFileHandler(self._on_new_file)
        
        # 状态管理
        self.is_running = False
        self.processing_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        
        # 文件稳定性检查
        self.stability_check_delay = 2.0  # 秒
        self.stability_check_interval = 1.0  # 秒
    
    def start_monitoring(self):
        """开始文件监控"""
        if self.is_running:
            self.logger.warning("文件监控已在运行")
            return
        
        try:
            # 设置文件系统监控
            self.observer.schedule(
                self.event_handler,
                str(self.watch_folder),
                recursive=False
            )
            
            # 启动观察者
            self.observer.start()
            
            # 启动处理线程
            self._shutdown_event.clear()
            self.processing_thread = threading.Thread(
                target=self._processing_worker,
                name="FileProcessingWorker"
            )
            self.processing_thread.daemon = True
            self.processing_thread.start()
            
            self.is_running = True
            self.logger.info(f"开始监控文件夹: {self.watch_folder}")
            
        except Exception as e:
            self.logger.error(f"启动文件监控失败: {str(e)}")
            self.stop_monitoring()
            raise
    
    def stop_monitoring(self):
        """停止文件监控"""
        if not self.is_running:
            return
        
        self.logger.info("正在停止文件监控...")
        
        try:
            # 设置停止信号
            self._shutdown_event.set()
            self.is_running = False
            
            # 停止文件系统观察者
            if self.observer.is_alive():
                self.observer.stop()
                self.observer.join(timeout=5.0)
                if self.observer.is_alive():
                    self.logger.warning("观察者线程未能及时停止")
            
            # 停止处理线程
            if self.processing_thread and self.processing_thread.is_alive():
                self.processing_thread.join(timeout=5.0)
                if self.processing_thread.is_alive():
                    self.logger.warning("处理线程未能及时停止")
            
            # 取消待处理的文件
            cancelled_count = self.processing_queue.cancel_pending_files()
            if cancelled_count > 0:
                self.logger.info(f"取消了 {cancelled_count} 个待处理文件")
            
            self.logger.info("文件监控已停止")
            
        except Exception as e:
            self.logger.error(f"停止文件监控时出错: {str(e)}")
    
    def _on_new_file(self, file_path: str):
        """新文件回调
        
        Args:
            file_path: 新文件路径
        """
        # 等待文件稳定
        time.sleep(self.stability_check_delay)
        
        if self._is_file_stable(file_path):
            metadata = {
                'detected_time': time.time(),
                'file_size': Path(file_path).stat().st_size if Path(file_path).exists() else 0
            }
            
            if self.processing_queue.add_file(file_path, metadata):
                self.logger.info(f"文件已添加到处理队列: {Path(file_path).name}")
            else:
                self.logger.warning(f"文件无法添加到队列: {Path(file_path).name}")
        else:
            self.logger.warning(f"文件不稳定，跳过处理: {Path(file_path).name}")
    
    def _is_file_stable(self, file_path: str) -> bool:
        """检查文件是否稳定（大小不再变化）
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件是否稳定
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return False
            
            # 检查文件大小稳定性
            initial_size = path.stat().st_size
            time.sleep(self.stability_check_interval)
            
            if not path.exists():
                return False
            
            final_size = path.stat().st_size
            is_stable = (initial_size == final_size and final_size > 0)
            
            if not is_stable:
                self.logger.debug(f"文件大小变化: {initial_size} -> {final_size}")
            
            return is_stable
            
        except Exception as e:
            self.logger.error(f"检查文件稳定性失败: {file_path}, 错误: {str(e)}")
            return False
    
    def _processing_worker(self):
        """处理队列工作线程"""
        self.logger.info("处理工作线程已启动")
        
        while not self._shutdown_event.is_set():
            try:
                # 从队列获取文件
                file_path = self.processing_queue.get_file(timeout=0.5)
                
                if file_path:
                    self.logger.info(f"开始处理文件: {Path(file_path).name}")
                    start_time = time.time()
                    
                    try:
                        # 调用文件处理回调
                        success = self.file_processor_callback(file_path)
                        
                        processing_time = time.time() - start_time
                        
                        if success:
                            self.processing_queue.mark_completed(
                                file_path, 
                                {'processing_time': processing_time}
                            )
                            self.logger.info(
                                f"文件处理完成: {Path(file_path).name} "
                                f"(耗时: {processing_time:.2f}秒)"
                            )
                        else:
                            self.processing_queue.mark_failed(
                                file_path, 
                                "处理回调返回失败",
                                retry=True
                            )
                            
                    except Exception as e:
                        self.processing_queue.mark_failed(
                            file_path,
                            f"处理异常: {str(e)}",
                            retry=True
                        )
                        self.logger.error(f"文件处理异常: {Path(file_path).name}, 错误: {str(e)}")
                
            except Exception as e:
                if not self._shutdown_event.is_set():
                    self.logger.error(f"处理工作线程异常: {str(e)}")
                    time.sleep(1.0)  # 避免快速循环
        
        self.logger.info("处理工作线程已停止")
    
    def get_queue_status(self) -> Dict[str, Any]:
        """获取处理队列状态
        
        Returns:
            队列状态信息
        """
        if not self.is_running:
            return {"status": "monitoring_not_started"}
        
        stats = self.processing_queue.get_processing_stats()
        
        return {
            "is_running": self.is_running,
            "watch_folder": str(self.watch_folder),
            "queue_stats": stats,
            "processing_files": self.processing_queue.get_files_by_status(ProcessingStatus.PROCESSING)
        }
    
    def add_supported_format(self, extension: str):
        """添加支持的音频格式
        
        Args:
            extension: 文件扩展名
        """
        self.event_handler.add_supported_format(extension)
    
    def remove_supported_format(self, extension: str):
        """移除支持的音频格式
        
        Args:
            extension: 文件扩展名
        """
        self.event_handler.remove_supported_format(extension)
    
    def get_supported_formats(self) -> set:
        """获取支持的音频格式
        
        Returns:
            支持的格式集合
        """
        return self.event_handler.get_supported_formats()
    
    def force_process_file(self, file_path: str) -> bool:
        """强制处理指定文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否成功添加到队列
        """
        if not Path(file_path).exists():
            self.logger.error(f"文件不存在: {file_path}")
            return False
        
        metadata = {
            'forced': True,
            'detected_time': time.time(),
            'file_size': Path(file_path).stat().st_size
        }
        
        return self.processing_queue.add_file(file_path, metadata)
    
    def clear_completed_records(self) -> int:
        """清理已完成的处理记录
        
        Returns:
            清理的记录数量
        """
        return self.processing_queue.clear_completed()
    
    def get_file_status(self, file_path: str) -> str:
        """获取指定文件的处理状态
        
        Args:
            file_path: 文件路径
            
        Returns:
            处理状态字符串
        """
        status = self.processing_queue.get_status(file_path)
        return status.value
    
    def cancel_file_processing(self, file_path: str) -> bool:
        """取消指定文件的处理
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否成功取消
        """
        current_status = self.processing_queue.get_status(file_path)
        
        if current_status == ProcessingStatus.PENDING:
            self.processing_queue.mark_cancelled(file_path)
            return True
        elif current_status == ProcessingStatus.PROCESSING:
            # 注意：无法中断正在处理的文件，只能标记为取消
            self.logger.warning(f"无法中断正在处理的文件: {file_path}")
            return False
        else:
            self.logger.warning(f"文件状态不允许取消: {file_path} ({current_status.value})")
            return False


def setup_signal_handlers(monitor: FileMonitor):
    """设置信号处理器以优雅关闭监控
    
    Args:
        monitor: 文件监控器实例
    """
    def signal_handler(signum, frame):
        logging.getLogger('project_bach.file_monitor').info(f"收到信号 {signum}，正在停止文件监控...")
        monitor.stop_monitoring()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Windows 特殊处理
    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, signal_handler)