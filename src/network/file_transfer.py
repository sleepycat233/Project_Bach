#!/usr/bin/env python3.11
"""
网络文件传输模块
处理跨设备文件传输和完整性验证
"""

import os
import shutil
import hashlib
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
import threading


class FileTransferValidator:
    """文件传输验证器"""
    
    @staticmethod
    def calculate_checksum(file_path: str, algorithm: str = 'md5') -> str:
        """
        计算文件校验和
        
        Args:
            file_path: 文件路径
            algorithm: 哈希算法 (md5, sha256)
            
        Returns:
            str: 文件校验和
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 不支持的算法
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        if algorithm not in ['md5', 'sha256']:
            raise ValueError(f"不支持的哈希算法: {algorithm}")
        
        hash_obj = hashlib.md5() if algorithm == 'md5' else hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest()
    
    @staticmethod
    def validate_file_integrity(local_path: str, remote_path: str, algorithm: str = 'md5') -> bool:
        """
        验证文件完整性
        
        Args:
            local_path: 本地文件路径
            remote_path: 远程文件路径
            algorithm: 哈希算法
            
        Returns:
            bool: 文件是否完整
        """
        try:
            local_checksum = FileTransferValidator.calculate_checksum(local_path, algorithm)
            remote_checksum = FileTransferValidator.calculate_checksum(remote_path, algorithm)
            
            return local_checksum == remote_checksum
            
        except Exception:
            return False
    
    @staticmethod
    def validate_file_size(local_path: str, remote_path: str) -> bool:
        """
        验证文件大小是否匹配
        
        Args:
            local_path: 本地文件路径
            remote_path: 远程文件路径
            
        Returns:
            bool: 文件大小是否匹配
        """
        try:
            local_size = os.path.getsize(local_path)
            remote_size = os.path.getsize(remote_path)
            
            return local_size == remote_size
            
        except Exception:
            return False


class NetworkFileTransfer:
    """网络文件传输器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化文件传输器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # 配置参数
        self.remote_base_path = self.config.get('remote_base_path', '/remote/watch_folder')
        self.local_base_path = self.config.get('local_base_path', '.')
        self.chunk_size = self.config.get('chunk_size', 8192)
        self.timeout = self.config.get('timeout', 60)
        self.retry_attempts = self.config.get('retry_attempts', 3)
        self.verify_integrity = self.config.get('verify_integrity', True)
        self.max_file_size = self.config.get('max_file_size', 100 * 1024 * 1024)  # 100MB
        
        # 支持的音频格式
        self.supported_audio_formats = {'.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg'}
    
    def get_supported_audio_formats(self) -> List[str]:
        """
        获取支持的音频格式列表
        
        Returns:
            List[str]: 支持的音频格式
        """
        return list(self.supported_audio_formats)
    
    def is_audio_file(self, file_path: str) -> bool:
        """
        检查是否为音频文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否为音频文件
        """
        file_ext = Path(file_path).suffix.lower()
        return file_ext in self.supported_audio_formats
    
    def _validate_file_size(self, file_path: str) -> bool:
        """
        验证文件大小是否在限制范围内
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 文件大小是否合规
        """
        try:
            file_size = os.path.getsize(file_path)
            if file_size > self.max_file_size:
                self.logger.error(f"文件过大 ({file_size} bytes)，超过限制 ({self.max_file_size} bytes)")
                return False
            return True
        except Exception as e:
            self.logger.error(f"检查文件大小时出错: {e}")
            return False
    
    def transfer_file(self, local_path: str, remote_path: str) -> Dict[str, Any]:
        """
        传输文件到远程位置
        
        Args:
            local_path: 本地文件路径
            remote_path: 远程文件路径
            
        Returns:
            Dict: 传输结果
        """
        start_time = time.time()
        
        # 验证本地文件
        if not os.path.exists(local_path):
            error_msg = f"本地文件不存在: {local_path}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'transferred_bytes': 0,
                'duration': 0
            }
        
        # 验证文件大小
        if not self._validate_file_size(local_path):
            error_msg = "文件大小超过限制"
            return {
                'success': False,
                'error': error_msg,
                'transferred_bytes': 0,
                'duration': 0
            }
        
        try:
            # 确保远程目录存在
            remote_dir = os.path.dirname(remote_path)
            try:
                os.makedirs(remote_dir, exist_ok=True)
            except OSError as e:
                if not os.path.exists(remote_dir):
                    error_msg = f"无法创建远程目录 {remote_dir}: {e}"
                    self.logger.error(error_msg)
                    return {
                        'success': False,
                        'error': error_msg,
                        'transferred_bytes': 0,
                        'duration': time.time() - start_time
                    }
            
            # 获取文件大小
            file_size = os.path.getsize(local_path)
            
            self.logger.info(f"开始传输文件: {local_path} -> {remote_path} ({file_size} bytes)")
            
            # 执行文件复制
            shutil.copy2(local_path, remote_path)
            
            end_time = time.time()
            duration = end_time - start_time
            
            self.logger.info(f"文件传输完成，用时: {duration:.2f}s")
            
            # 验证传输完整性
            if self.verify_integrity:
                if not self.validate_transfer(local_path, remote_path):
                    error_msg = "文件完整性验证失败"
                    self.logger.error(error_msg)
                    return {
                        'success': False,
                        'error': error_msg,
                        'transferred_bytes': file_size,
                        'duration': duration
                    }
            
            return {
                'success': True,
                'transferred_bytes': file_size,
                'duration': duration,
                'transfer_speed': file_size / duration if duration > 0 else 0
            }
            
        except PermissionError as e:
            error_msg = f"权限错误: {e}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'transferred_bytes': 0,
                'duration': time.time() - start_time
            }
        except Exception as e:
            error_msg = f"传输失败: {e}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'transferred_bytes': 0,
                'duration': time.time() - start_time
            }
    
    def validate_transfer(self, local_path: str, remote_path: str) -> bool:
        """
        验证文件传输是否成功
        
        Args:
            local_path: 本地文件路径
            remote_path: 远程文件路径
            
        Returns:
            bool: 传输是否成功
        """
        try:
            # 检查远程文件是否存在
            if not os.path.exists(remote_path):
                self.logger.error(f"远程文件不存在: {remote_path}")
                return False
            
            # 验证文件大小
            if not FileTransferValidator.validate_file_size(local_path, remote_path):
                self.logger.error("文件大小不匹配")
                return False
            
            # 验证文件完整性（如果启用）
            if self.verify_integrity:
                if not FileTransferValidator.validate_file_integrity(local_path, remote_path):
                    self.logger.error("文件校验和不匹配")
                    return False
            
            self.logger.debug("文件传输验证通过")
            return True
            
        except Exception as e:
            self.logger.error(f"验证传输时出错: {e}")
            return False
    
    def transfer_with_progress(self, local_path: str, remote_path: str, 
                             progress_callback: Optional[Callable[[int, int], None]] = None) -> Dict[str, Any]:
        """
        带进度回调的文件传输
        
        Args:
            local_path: 本地文件路径
            remote_path: 远程文件路径
            progress_callback: 进度回调函数 (已传输字节, 总字节)
            
        Returns:
            Dict: 传输结果
        """
        if not os.path.exists(local_path):
            return {
                'success': False,
                'error': f"本地文件不存在: {local_path}",
                'transferred_bytes': 0
            }
        
        try:
            file_size = os.path.getsize(local_path)
            transferred = 0
            
            # 确保远程目录存在
            remote_dir = os.path.dirname(remote_path)
            os.makedirs(remote_dir, exist_ok=True)
            
            self.logger.info(f"开始分块传输: {local_path} -> {remote_path}")
            
            # 分块读取和写入
            with open(local_path, 'rb') as src, open(remote_path, 'wb') as dst:
                while True:
                    chunk = src.read(self.chunk_size)
                    if not chunk:
                        break
                    
                    dst.write(chunk)
                    transferred += len(chunk)
                    
                    # 调用进度回调
                    if progress_callback:
                        progress_callback(transferred, file_size)
            
            # 验证传输
            if self.verify_integrity and not self.validate_transfer(local_path, remote_path):
                return {
                    'success': False,
                    'error': '文件完整性验证失败',
                    'transferred_bytes': transferred
                }
            
            return {
                'success': True,
                'transferred_bytes': transferred
            }
            
        except Exception as e:
            error_msg = f"传输失败: {e}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'transferred_bytes': 0
            }
    
    def transfer_with_retry(self, local_path: str, remote_path: str) -> Dict[str, Any]:
        """
        带重试机制的文件传输
        
        Args:
            local_path: 本地文件路径
            remote_path: 远程文件路径
            
        Returns:
            Dict: 传输结果
        """
        last_result = None
        
        for attempt in range(self.retry_attempts + 1):
            if attempt > 0:
                self.logger.info(f"重试文件传输 (第{attempt}次)")
                time.sleep(min(2 ** attempt, 10))  # 指数退避
            
            result = self.transfer_file(local_path, remote_path)
            last_result = result
            
            if result['success']:
                if attempt > 0:
                    self.logger.info(f"重试成功，共尝试 {attempt + 1} 次")
                return result
        
        self.logger.error(f"文件传输失败，已尝试 {self.retry_attempts + 1} 次")
        return last_result
    
    def get_transfer_statistics(self, transfers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算传输统计信息
        
        Args:
            transfers: 传输结果列表
            
        Returns:
            Dict: 统计信息
        """
        if not transfers:
            return {
                'total_transfers': 0,
                'successful_transfers': 0,
                'failed_transfers': 0,
                'success_rate': 0,
                'total_bytes': 0,
                'total_duration': 0,
                'average_speed': 0
            }
        
        total_transfers = len(transfers)
        successful_transfers = sum(1 for t in transfers if t.get('success', False))
        failed_transfers = total_transfers - successful_transfers
        success_rate = successful_transfers / total_transfers
        
        total_bytes = sum(t.get('transferred_bytes', 0) for t in transfers)
        total_duration = sum(t.get('duration', 0) for t in transfers)
        average_speed = total_bytes / total_duration if total_duration > 0 else 0
        
        return {
            'total_transfers': total_transfers,
            'successful_transfers': successful_transfers,
            'failed_transfers': failed_transfers,
            'success_rate': success_rate,
            'total_bytes': total_bytes,
            'total_duration': total_duration,
            'average_speed': average_speed
        }


class LargeFileTransferManager:
    """大文件传输管理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化大文件传输管理器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.chunk_size = self.config.get('chunk_size', 8192)
        self.max_file_size = self.config.get('max_file_size', 100 * 1024 * 1024)
    
    def calculate_chunks(self, file_size: int) -> int:
        """
        计算文件需要分成多少块
        
        Args:
            file_size: 文件大小（字节）
            
        Returns:
            int: 分块数量
        """
        return (file_size + self.chunk_size - 1) // self.chunk_size
    
    def validate_file_size(self, file_size: int) -> bool:
        """
        验证文件大小是否在允许范围内
        
        Args:
            file_size: 文件大小（字节）
            
        Returns:
            bool: 是否允许传输
        """
        return file_size <= self.max_file_size
    
    def simulate_transfer_interruption(self, total_size: int, transferred: int) -> Dict[str, Any]:
        """
        模拟传输中断和恢复计算
        
        Args:
            total_size: 文件总大小
            transferred: 已传输大小
            
        Returns:
            Dict: 中断恢复信息
        """
        remaining = total_size - transferred
        remaining_chunks = remaining // self.chunk_size
        last_chunk = transferred // self.chunk_size
        
        return {
            'total_size': total_size,
            'transferred': transferred,
            'remaining': remaining,
            'remaining_chunks': remaining_chunks,
            'last_chunk': last_chunk,
            'progress_percentage': (transferred / total_size) * 100 if total_size > 0 else 0
        }