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
    
    def __init__(self, file_callback: Callable[[str], None], supported_formats: Set[str] = None):
        """初始化音频文件事件处理器
        
        Args:
            file_callback: 处理新文件的回调函数
            supported_formats: 支持的音频格式集合，如果为None则使用默认格式
        """
        super().__init__()
        self.file_callback = file_callback
        self.logger = logging.getLogger('project_bach.audio_handler')
        
        # 支持的音频格式 - 从参数传入或使用默认值
        self.supported_formats: Set[str] = supported_formats or {
            '.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg', '.mp4'
        }
        
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


class GenericFileHandler(FileSystemEventHandler):
    """通用文件事件处理器"""
    
    def __init__(self, 
                 on_created_callback: Callable[[str], None] = None,
                 on_modified_callback: Callable[[str], None] = None,
                 on_deleted_callback: Callable[[str], None] = None,
                 on_moved_callback: Callable[[str, str], None] = None):
        """初始化通用文件事件处理器
        
        Args:
            on_created_callback: 文件创建回调
            on_modified_callback: 文件修改回调
            on_deleted_callback: 文件删除回调
            on_moved_callback: 文件移动回调
        """
        super().__init__()
        self.on_created_callback = on_created_callback
        self.on_modified_callback = on_modified_callback
        self.on_deleted_callback = on_deleted_callback
        self.on_moved_callback = on_moved_callback
        
        self.logger = logging.getLogger('project_bach.generic_handler')
    
    def on_created(self, event):
        """文件创建事件"""
        if not event.is_directory and self.on_created_callback:
            try:
                self.on_created_callback(event.src_path)
            except Exception as e:
                self.logger.error(f"创建事件回调失败: {event.src_path}, 错误: {str(e)}")
    
    def on_modified(self, event):
        """文件修改事件"""
        if not event.is_directory and self.on_modified_callback:
            try:
                self.on_modified_callback(event.src_path)
            except Exception as e:
                self.logger.error(f"修改事件回调失败: {event.src_path}, 错误: {str(e)}")
    
    def on_deleted(self, event):
        """文件删除事件"""
        if not event.is_directory and self.on_deleted_callback:
            try:
                self.on_deleted_callback(event.src_path)
            except Exception as e:
                self.logger.error(f"删除事件回调失败: {event.src_path}, 错误: {str(e)}")
    
    def on_moved(self, event):
        """文件移动事件"""
        if not event.is_directory and self.on_moved_callback:
            try:
                self.on_moved_callback(event.src_path, event.dest_path)
            except Exception as e:
                self.logger.error(f"移动事件回调失败: {event.src_path} -> {event.dest_path}, 错误: {str(e)}")


class FilteredFileHandler(FileSystemEventHandler):
    """带过滤功能的文件事件处理器"""
    
    def __init__(self, 
                 file_callback: Callable[[str], None],
                 file_extensions: Set[str] = None,
                 include_patterns: Set[str] = None,
                 exclude_patterns: Set[str] = None):
        """初始化过滤文件事件处理器
        
        Args:
            file_callback: 文件处理回调函数
            file_extensions: 允许的文件扩展名集合
            include_patterns: 包含的文件名模式
            exclude_patterns: 排除的文件名模式
        """
        super().__init__()
        self.file_callback = file_callback
        self.file_extensions = file_extensions or set()
        self.include_patterns = include_patterns or set()
        self.exclude_patterns = exclude_patterns or set()
        
        self.logger = logging.getLogger('project_bach.filtered_handler')
    
    def on_created(self, event):
        """文件创建事件"""
        if not event.is_directory:
            self._handle_file_event(event.src_path)
    
    def on_moved(self, event):
        """文件移动事件"""
        if not event.is_directory:
            self._handle_file_event(event.dest_path)
    
    def _handle_file_event(self, file_path: str):
        """处理文件事件
        
        Args:
            file_path: 文件路径
        """
        if self._should_process_file(file_path):
            try:
                self.logger.debug(f"处理文件: {Path(file_path).name}")
                self.file_callback(file_path)
            except Exception as e:
                self.logger.error(f"文件处理回调失败: {file_path}, 错误: {str(e)}")
    
    def _should_process_file(self, file_path: str) -> bool:
        """判断是否应该处理该文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否应该处理
        """
        path = Path(file_path)
        filename = path.name.lower()
        
        # 检查文件扩展名
        if self.file_extensions and path.suffix.lower() not in self.file_extensions:
            return False
        
        # 检查排除模式
        if self.exclude_patterns:
            for pattern in self.exclude_patterns:
                if pattern.lower() in filename:
                    return False
        
        # 检查包含模式
        if self.include_patterns:
            for pattern in self.include_patterns:
                if pattern.lower() in filename:
                    return True
            return False  # 如果有包含模式但都不匹配
        
        return True
    
    def update_filters(self,
                      file_extensions: Set[str] = None,
                      include_patterns: Set[str] = None,
                      exclude_patterns: Set[str] = None):
        """更新过滤器配置
        
        Args:
            file_extensions: 新的文件扩展名集合
            include_patterns: 新的包含模式集合
            exclude_patterns: 新的排除模式集合
        """
        if file_extensions is not None:
            self.file_extensions = file_extensions
        if include_patterns is not None:
            self.include_patterns = include_patterns
        if exclude_patterns is not None:
            self.exclude_patterns = exclude_patterns
        
        self.logger.info("文件过滤器配置已更新")