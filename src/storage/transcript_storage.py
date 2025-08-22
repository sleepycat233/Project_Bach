#!/usr/bin/env python3.11
"""
转录文本存储模块
负责转录文本的保存、读取和管理
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import json


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
        # 旧版本兼容
        self.transcripts_folder = self.data_folder / 'transcripts'
        self.logger = logging.getLogger('project_bach.transcript_storage')
        
        # 确保目录存在
        self.public_transcripts_folder.mkdir(parents=True, exist_ok=True)
        self.private_transcripts_folder.mkdir(parents=True, exist_ok=True)
        self.transcripts_folder.mkdir(parents=True, exist_ok=True)
        
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
    
    def save_processed_transcript(self, filename: str, content: str, privacy_level: str = 'public') -> str:
        """保存处理后的转录文本
        
        Args:
            filename: 文件名（不包含扩展名）
            content: 处理后的内容
            privacy_level: 隐私级别 ('public' 或 'private')
            
        Returns:
            保存的文件路径
        """
        return self._save_transcript(filename, content, "processed", privacy_level)
    
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
    
    def load_transcript(self, filename: str, suffix: str = "raw", privacy_level: str = 'public') -> Optional[str]:
        """加载转录文本
        
        Args:
            filename: 文件名（不包含扩展名）
            suffix: 后缀标识
            privacy_level: 隐私级别 ('public' 或 'private')
            
        Returns:
            转录内容，如果文件不存在返回None
        """
        # 根据隐私级别选择文件夹
        if privacy_level == 'private':
            target_folder = self.private_transcripts_folder
        else:
            target_folder = self.public_transcripts_folder
            
        file_path = target_folder / f"{filename}_{suffix}.txt"
        
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.logger.debug(f"加载转录文件: {file_path}")
                return content
            else:
                # 尝试从旧位置加载（兼容性）
                old_file_path = self.transcripts_folder / f"{filename}_{suffix}.txt"
                if old_file_path.exists():
                    with open(old_file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    self.logger.debug(f"从旧位置加载转录文件: {old_file_path}")
                    return content
                else:
                    self.logger.warning(f"转录文件不存在: {file_path}")
                    return None
                
        except Exception as e:
            self.logger.error(f"加载转录文件失败: {file_path}, 错误: {str(e)}")
            return None
    
    def list_transcripts(self, suffix: Optional[str] = None) -> List[str]:
        """列出所有转录文件
        
        Args:
            suffix: 可选的后缀过滤器
            
        Returns:
            文件名列表（不包含路径和扩展名）
        """
        try:
            pattern = f"*_{suffix}.txt" if suffix else "*.txt"
            files = list(self.transcripts_folder.glob(pattern))
            
            # 提取基础文件名
            base_names = []
            for file_path in files:
                name = file_path.stem
                if suffix:
                    # 移除后缀
                    if name.endswith(f"_{suffix}"):
                        base_name = name[:-len(f"_{suffix}")]
                        base_names.append(base_name)
                else:
                    # 移除所有已知后缀
                    for known_suffix in ["raw", "anonymized", "processed"]:
                        if name.endswith(f"_{known_suffix}"):
                            base_name = name[:-len(f"_{known_suffix}")]
                            if base_name not in base_names:
                                base_names.append(base_name)
                            break
                    else:
                        # 没有已知后缀，直接添加
                        if name not in base_names:
                            base_names.append(name)
            
            return sorted(base_names)
            
        except Exception as e:
            self.logger.error(f"列出转录文件失败: {str(e)}")
            return []
    
    def delete_transcript(self, filename: str, suffix: Optional[str] = None) -> bool:
        """删除转录文件
        
        Args:
            filename: 文件名（不包含扩展名）
            suffix: 可选的后缀，如果为None则删除所有相关文件
            
        Returns:
            是否成功删除
        """
        try:
            if suffix:
                # 删除特定后缀的文件
                file_path = self.transcripts_folder / f"{filename}_{suffix}.txt"
                if file_path.exists():
                    file_path.unlink()
                    self.logger.info(f"删除转录文件: {file_path}")
                    return True
                else:
                    self.logger.warning(f"要删除的文件不存在: {file_path}")
                    return False
            else:
                # 删除所有相关文件
                deleted_count = 0
                for known_suffix in ["raw", "anonymized", "processed"]:
                    file_path = self.transcripts_folder / f"{filename}_{known_suffix}.txt"
                    if file_path.exists():
                        file_path.unlink()
                        deleted_count += 1
                        self.logger.info(f"删除转录文件: {file_path}")
                
                return deleted_count > 0
                
        except Exception as e:
            self.logger.error(f"删除转录文件失败: {filename}, 错误: {str(e)}")
            return False
    
    def get_transcript_info(self, filename: str) -> Dict[str, any]:
        """获取转录文件信息
        
        Args:
            filename: 文件名（不包含扩展名）
            
        Returns:
            包含文件信息的字典
        """
        info = {
            'filename': filename,
            'files': {},
            'total_size': 0,
            'created_time': None,
            'modified_time': None
        }
        
        try:
            for suffix in ["raw", "anonymized", "processed"]:
                file_path = self.transcripts_folder / f"{filename}_{suffix}.txt"
                if file_path.exists():
                    stat = file_path.stat()
                    info['files'][suffix] = {
                        'path': str(file_path),
                        'size': stat.st_size,
                        'created': datetime.fromtimestamp(stat.st_ctime),
                        'modified': datetime.fromtimestamp(stat.st_mtime)
                    }
                    info['total_size'] += stat.st_size
                    
                    # 更新总体时间信息
                    if info['created_time'] is None or info['files'][suffix]['created'] < info['created_time']:
                        info['created_time'] = info['files'][suffix]['created']
                    if info['modified_time'] is None or info['files'][suffix]['modified'] > info['modified_time']:
                        info['modified_time'] = info['files'][suffix]['modified']
            
            return info
            
        except Exception as e:
            self.logger.error(f"获取文件信息失败: {filename}, 错误: {str(e)}")
            return info
    
    def cleanup_old_files(self, days: int = 30) -> int:
        """清理旧的转录文件
        
        Args:
            days: 保留天数，超过此天数的文件将被删除
            
        Returns:
            删除的文件数量
        """
        try:
            cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
            deleted_count = 0
            
            for file_path in self.transcripts_folder.glob("*.txt"):
                if file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    deleted_count += 1
                    self.logger.info(f"清理旧文件: {file_path}")
            
            self.logger.info(f"清理完成，删除了 {deleted_count} 个文件")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"清理旧文件失败: {str(e)}")
            return 0


class TranscriptMetadata:
    """转录文件元数据管理"""
    
    def __init__(self, storage: TranscriptStorage):
        """初始化元数据管理器
        
        Args:
            storage: 转录存储实例
        """
        self.storage = storage
        self.metadata_file = storage.transcripts_folder / "metadata.json"
        self.logger = logging.getLogger('project_bach.transcript_metadata')
        self._metadata = self._load_metadata()
    
    def _load_metadata(self) -> Dict[str, Dict]:
        """加载元数据"""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            self.logger.error(f"加载元数据失败: {str(e)}")
            return {}
    
    def _save_metadata(self):
        """保存元数据"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self._metadata, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"保存元数据失败: {str(e)}")
    
    def add_metadata(self, filename: str, metadata: Dict[str, any]):
        """添加文件元数据
        
        Args:
            filename: 文件名
            metadata: 元数据字典
        """
        self._metadata[filename] = {
            **metadata,
            'created_time': datetime.now().isoformat(),
            'updated_time': datetime.now().isoformat()
        }
        self._save_metadata()
    
    def update_metadata(self, filename: str, updates: Dict[str, any]):
        """更新文件元数据
        
        Args:
            filename: 文件名
            updates: 更新的元数据
        """
        if filename in self._metadata:
            self._metadata[filename].update(updates)
            self._metadata[filename]['updated_time'] = datetime.now().isoformat()
            self._save_metadata()
    
    def get_metadata(self, filename: str) -> Optional[Dict[str, any]]:
        """获取文件元数据
        
        Args:
            filename: 文件名
            
        Returns:
            元数据字典或None
        """
        return self._metadata.get(filename)
    
    def remove_metadata(self, filename: str):
        """删除文件元数据
        
        Args:
            filename: 文件名
        """
        if filename in self._metadata:
            del self._metadata[filename]
            self._save_metadata()
    
    def list_metadata(self) -> Dict[str, Dict]:
        """列出所有元数据
        
        Returns:
            所有元数据的字典
        """
        return self._metadata.copy()