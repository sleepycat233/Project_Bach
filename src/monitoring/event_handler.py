#!/usr/bin/env python3.11
"""
文件事件处理模块
负责处理文件系统事件
"""

import logging
from pathlib import Path
from typing import Set, Callable
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent


class AudioFileHandler(FileSystemEventHandler):
    """音频文件事件处理器"""
    
    def __init__(self, file_callback: Callable[[str], None], supported_formats: Set[str]):
        """初始化音频文件事件处理器

        Args:
            file_callback: 处理新文件的回调函数
            supported_formats: 支持的音频格式集合（必需参数）
        """
        super().__init__()
        self.file_callback = file_callback
        self.logger = logging.getLogger('project_bach.audio_handler')

        # 支持的音频格式 - 必须从外部传入
        if not supported_formats:
            raise ValueError("supported_formats 参数不能为空")
        self.supported_formats: Set[str] = supported_formats
        
        # 忽略的文件模式
        self.ignore_patterns: Set[str] = {
            '.DS_Store', '.tmp', '.part', '.download', '.crdownload'
        }
    
    def on_created(self, event):
        """文件创建事件
        
        Args:
            event: 文件系统事件对象
        """
        if not event.is_directory:
            self._handle_new_file(event.src_path)
    
    def on_moved(self, event):
        """文件移动事件
        
        Args:
            event: 文件系统事件对象
        """
        if not event.is_directory:
            self._handle_new_file(event.dest_path)
    
    def _handle_new_file(self, file_path: str):
        """处理新文件
        
        Args:
            file_path: 文件路径
        """
        path = Path(file_path)
        
        # 检查文件格式
        if not self._is_supported_audio_file(path):
            self.logger.debug(f"跳过非音频文件: {path.name}")
            return
        
        # 检查是否为临时文件
        if self._is_temporary_file(path):
            self.logger.debug(f"跳过临时文件: {path.name}")
            return
        
        # 调用回调函数处理文件
        try:
            self.logger.info(f"检测到新音频文件: {path.name}")
            self.file_callback(file_path)
        except Exception as e:
            self.logger.error(f"处理文件回调时出错: {path.name}, 错误: {str(e)}")
    
    def _is_supported_audio_file(self, file_path: Path) -> bool:
        """检查是否为支持的音频文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否为支持的音频文件
        """
        return file_path.suffix.lower() in self.supported_formats
    
    def _is_temporary_file(self, file_path: Path) -> bool:
        """检查是否为临时文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否为临时文件
        """
        filename = file_path.name.lower()
        return any(pattern in filename for pattern in self.ignore_patterns)
    
    def add_supported_format(self, extension: str):
        """添加支持的音频格式
        
        Args:
            extension: 文件扩展名（包含点号，如'.mp3'）
        """
        if not extension.startswith('.'):
            extension = '.' + extension
        self.supported_formats.add(extension.lower())
        self.logger.info(f"添加支持的音频格式: {extension}")
    
    def remove_supported_format(self, extension: str):
        """移除支持的音频格式
        
        Args:
            extension: 文件扩展名
        """
        if not extension.startswith('.'):
            extension = '.' + extension
        self.supported_formats.discard(extension.lower())
        self.logger.info(f"移除支持的音频格式: {extension}")
    
    def add_ignore_pattern(self, pattern: str):
        """添加忽略模式
        
        Args:
            pattern: 忽略的文件名模式
        """
        self.ignore_patterns.add(pattern.lower())
        self.logger.info(f"添加忽略模式: {pattern}")
    
    def get_supported_formats(self) -> Set[str]:
        """获取支持的音频格式
        
        Returns:
            支持的格式集合
        """
        return self.supported_formats.copy()
    
    def get_ignore_patterns(self) -> Set[str]:
        """获取忽略模式
        
        Returns:
            忽略模式集合
        """
        return self.ignore_patterns.copy()




