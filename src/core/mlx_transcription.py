#!/usr/bin/env python3.11
"""
MLX Whisper转录服务
基于mlx-whisper的Apple Silicon优化音频转录实现
替代原有的WhisperKit subprocess方式，提供更好的性能和原生Python集成
"""

import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import os
import gc

try:
    import mlx_whisper
except ImportError:
    mlx_whisper = None


class MLXTranscriptionService:
    """MLX Whisper音频转录服务"""
    
    def __init__(self, mlx_config: Dict[str, Any]):
        """初始化MLX转录服务
        
        Args:
            mlx_config: MLX Whisper配置字典
        """
        # 延迟检查mlx_whisper，只在实际使用时检查，这样单元测试可以mock
            
        self.config = mlx_config
        self.logger = logging.getLogger('project_bach.mlx_transcription')
        self._model_cache = {}  # 模型缓存，避免重复加载
        
        # 从配置中获取基本参数（支持新的配置结构）
        # 如果配置为空，提供最小化默认值
        self.default_model = mlx_config.get('default_model', 'whisper-large-v3')
        self.available_models = mlx_config.get('available_models', [])
        
        # 移除本地下载选项，统一使用HuggingFace标准缓存
        
        # 移除固定转录参数配置，改为动态传递
        
        # 构建默认模型仓库路径
        self.model_repo = self._get_model_repo_by_name(self.default_model)
        
        self.logger.info("MLX Whisper服务初始化完成")
        self.logger.debug(f"默认模型: {self.default_model}")
        self.logger.debug(f"模型仓库: {self.model_repo}")
        
    def _get_model_repo_by_name(self, model_name: str) -> str:
        """根据模型名称获取仓库路径
        
        Args:
            model_name: 模型名称 (如 'whisper-tiny', 'whisper-large-v3')
            
        Returns:
            模型仓库路径
        """
        # 遍历available_models中的repo列表
        for repo in self.available_models:
            # 从repo路径中提取模型名 (如 "mlx-community/whisper-tiny" -> "whisper-tiny")
            repo_model_name = repo.split('/')[-1]
            if repo_model_name == model_name:
                return repo
        
        # 如果没有找到，回退到默认格式
        self.logger.warning(f"未找到模型 {model_name}，使用默认格式")
        return f"mlx-community/{model_name}"
    
    def get_available_models(self) -> List[str]:
        """获取可用模型列表
        
        Returns:
            可用模型仓库列表
        """
        return self.available_models
    
    def get_model_names(self) -> List[str]:
        """获取可用模型名称列表
        
        Returns:
            模型名称列表 (从repo中提取)
        """
        return [repo.split('/')[-1] for repo in self.available_models]
    
    def get_model_info_by_name(self, model_name: str) -> Dict[str, Any]:
        """根据模型名称获取模型信息
        
        Args:
            model_name: 模型名称
            
        Returns:
            模型信息字典
        """
        repo = self._get_model_repo_by_name(model_name)
        return {
            'name': model_name,
            'repo': repo,
            'full_name': repo.split('/')[-1] if '/' in repo else repo
        }
        
    def transcribe_audio(self, audio_path: Path, prompt: str = None, 
                        language_preference: str = 'english', 
                        custom_model: str = None,
                        word_timestamps: bool = False) -> Union[str, Dict[str, Any]]:
        """转录音频文件
        
        Args:
            audio_path: 音频文件路径
            prompt: Whisper系统提示词，用于提高特定术语识别准确性
            language_preference: 语言偏好 ('english' 或 'multilingual')
            custom_model: 自定义模型名称 (如'large-v3', 'medium') 或完整仓库地址
            word_timestamps: 是否启用词级时间戳（diarization需要时为True）
            
        Returns:
            str: 转录文本 (当word_timestamps=False时)
            Dict[str, Any]: 包含text和chunks的完整结果 (当word_timestamps=True时)
            
        Raises:
            Exception: 转录失败
        """
        # 验证音频文件存在
        if not audio_path.exists():
            raise Exception(f"音频文件不存在: {audio_path}")
        
        # 获取音频文件信息
        file_size_mb = audio_path.stat().st_size / (1024 * 1024)
        
        self.logger.info(f"开始MLX Whisper转录: {audio_path.name}")
        self.logger.info(f"文件大小: {file_size_mb:.1f}MB")
        if prompt:
            self.logger.info(f"使用自定义提示词: {prompt[:50]}{'...' if len(prompt) > 50 else ''}")
        
        # 大文件预警
        if file_size_mb > 50:  # MB
            self.logger.warning(f"检测到大音频文件 ({file_size_mb:.1f}MB)，转录可能需要较长时间")
        
        try:
            # 确定使用的模型
            model_path_or_repo = self._get_model_path(custom_model)
            
            # 准备转录参数
            transcribe_kwargs = {
                'path_or_hf_repo': model_path_or_repo,
                'word_timestamps': word_timestamps
            }
            
            # 设置语言参数
            if language_preference == 'english':
                transcribe_kwargs['language'] = 'en'
            # multilingual模式让MLX Whisper自动检测，不设置language参数
            
            # 添加提示词
            if prompt:
                transcribe_kwargs['initial_prompt'] = prompt
                
            self.logger.info(f"使用模型: {model_path_or_repo}")
            self.logger.info(f"语言偏好: {language_preference}")
            
            # 检查mlx_whisper是否可用
            if mlx_whisper is None:
                raise ImportError("mlx-whisper未安装。请运行: pip install mlx-whisper")
            
            # 记录开始时间
            start_time = time.time()
            
            # 执行转录
            result = mlx_whisper.transcribe(str(audio_path), **transcribe_kwargs)
            
            # 记录转录时间
            transcribe_time = time.time() - start_time
            self.logger.info(f"转录完成，耗时: {transcribe_time:.2f}秒")
            
            # 调试：打印result结构
            if word_timestamps:
                self.logger.debug(f"MLX Whisper result keys: {list(result.keys()) if isinstance(result, dict) else 'not a dict'}")
                if isinstance(result, dict) and 'segments' in result:
                    self.logger.debug(f"Segments count: {len(result['segments'])}")
                    if result['segments']:
                        first_segment = result['segments'][0]
                        self.logger.debug(f"First segment keys: {list(first_segment.keys()) if isinstance(first_segment, dict) else 'not a dict'}")
                        if 'words' in first_segment:
                            self.logger.debug(f"First segment has {len(first_segment['words'])} words")
                        else:
                            self.logger.debug("First segment has no 'words' key")
            
            # 提取转录文本
            transcribed_text = result.get('text', '')
            if not transcribed_text.strip():
                self.logger.warning("转录结果为空，可能是静音音频或转录失败")
                return "转录结果为空。"
            
            # 记录性能信息
            if 'segments' in result:
                segment_count = len(result['segments'])
                self.logger.info(f"转录生成了 {segment_count} 个语音段落")
            
            # 构建输出结果
            if word_timestamps and isinstance(result, dict) and 'segments' in result:
                self.logger.debug("返回包含时间戳的完整结果")
                
                # ✅ 直接使用segments作为chunks，只需要添加timestamp字段
                # 避免不必要的数组重建，segments本身就包含所需的所有信息
                segments = result.get('segments', [])
                
                # 为每个segment添加timestamp字段以兼容现有代码
                for segment in segments:
                    if 'start' in segment and 'end' in segment:
                        segment['timestamp'] = [float(segment['start']), float(segment['end'])]
                
                self.logger.debug(f"使用 {len(segments)} 个segments作为chunks")
                
                # 返回完整结果供diarization使用
                return {
                    'text': transcribed_text.strip(),
                    'chunks': segments  # 直接使用segments作为chunks，包含timestamp字段
                }
            else:
                self.logger.debug("返回纯文本结果")
            
            return transcribed_text.strip()
            
        except Exception as e:
            error_msg = f"MLX Whisper转录失败: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
    
    def _get_model_path(self, custom_model: str = None) -> str:
        """获取模型仓库地址 (统一使用HuggingFace仓库)
        
        Args:
            custom_model: 自定义模型名称或完整仓库地址
            
        Returns:
            HuggingFace仓库地址
        """
        # 如果custom_model包含'/'，认为是完整的仓库地址
        if custom_model and '/' in custom_model:
            self.logger.debug(f"使用完整模型仓库地址: {custom_model}")
            return custom_model
        
        # 如果只指定了模型名，直接构建仓库地址
        if custom_model:
            model_repo = f"mlx-community/{custom_model}"
            self.logger.debug(f"构建模型仓库: {model_repo}")
            return model_repo
        
        # 使用默认配置的模型仓库
        self.logger.debug(f"使用默认模型仓库: {self.model_repo}")
        return self.model_repo
    
    
    def _estimate_audio_duration(self, audio_path: Path) -> float:
        """估算音频时长（分钟）
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            估算的音频时长（分钟）
        """
        try:
            # 简单的文件大小估算（1MB ≈ 1分钟，这是一个粗略估算）
            file_size_mb = audio_path.stat().st_size / (1024 * 1024)
            estimated_duration = file_size_mb * 0.8  # 保守估算
            return max(estimated_duration, 1.0)  # 至少1分钟
        except Exception:
            return 5.0  # 默认5分钟
    
    def cleanup_model_cache(self):
        """清理模型缓存，释放内存"""
        if self._model_cache:
            self.logger.info("清理MLX模型缓存")
            self._model_cache.clear()
            
        # 强制垃圾回收
        gc.collect()
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取当前模型信息
        
        Returns:
            模型信息字典
        """
        model_repo = self._get_model_path()
        
        return {
            'model_repo': self.model_repo,
            'current_model': model_repo,
            'mlx_whisper_available': mlx_whisper is not None
        }


