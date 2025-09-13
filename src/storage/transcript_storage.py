#!/usr/bin/env python3.11
"""
转录文本存储模块
负责转录文本的保存、读取和管理
"""

import os
import logging
from pathlib import Path


class TranscriptStorage:
    """转录文本存储服务"""
    
    def __init__(self, data_folder: str):
        """初始化转录文本存储
        
        Args:
            data_folder: 数据文件夹路径
        """
        self.data_folder = Path(data_folder)
        # 支持按privacy_level分别存储
        self.public_transcripts_folder = self.data_folder / 'output' / 'public' / 'transcripts'
        self.private_transcripts_folder = self.data_folder / 'output' / 'private' / 'transcripts'
        self.logger = logging.getLogger('project_bach.transcript_storage')
        
        # 确保目录存在
        self.public_transcripts_folder.mkdir(parents=True, exist_ok=True)
        self.private_transcripts_folder.mkdir(parents=True, exist_ok=True)
        
    def save_raw_transcript(self, filename: str, content: str, privacy_level: str = 'public') -> str:
        """保存原始转录文本
        
        Args:
            filename: 文件名（不包含扩展名）
            content: 转录内容
            privacy_level: 隐私级别 ('public' 或 'private')
            
        Returns:
            保存的文件路径
        """
        return self._save_transcript(filename, content, "raw", privacy_level)
    
    def save_anonymized_transcript(self, filename: str, content: str, privacy_level: str = 'public') -> str:
        """保存匿名化转录文本
        
        Args:
            filename: 文件名（不包含扩展名）
            content: 匿名化后的内容
            privacy_level: 隐私级别 ('public' 或 'private')
            
        Returns:
            保存的文件路径
        """
        return self._save_transcript(filename, content, "anonymized", privacy_level)
    
    def _save_transcript(self, filename: str, content: str, suffix: str, privacy_level: str = 'public') -> str:
        """内部方法：保存转录文本
        
        Args:
            filename: 文件名
            content: 内容
            suffix: 后缀标识
            privacy_level: 隐私级别 ('public' 或 'private')
            
        Returns:
            保存的文件路径
            
        Raises:
            OSError: 文件保存失败
        """
        # 根据隐私级别选择存储文件夹
        if privacy_level == 'private':
            target_folder = self.private_transcripts_folder
        else:
            target_folder = self.public_transcripts_folder
            
        file_path = target_folder / f"{filename}_{suffix}.txt"
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.logger.debug(f"保存转录文件: {file_path} (隐私级别: {privacy_level})")
            return str(file_path)
            
        except Exception as e:
            error_msg = f"保存转录文件失败: {file_path}, 错误: {str(e)}"
            self.logger.error(error_msg)
            raise OSError(error_msg)