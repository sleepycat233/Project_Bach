#!/usr/bin/env python3.11
"""
Speaker Diarization服务
基于pyannote.audio的说话人分离实现
与转录服务解耦，提供独立的说话人识别功能
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

try:
    from pyannote.audio import Pipeline
    import torch
except ImportError:
    Pipeline = None
    torch = None


class SpeakerDiarization:
    """说话人分离服务"""
    
    def __init__(self, diarization_config: Dict[str, Any], huggingface_config: Dict[str, Any]):
        """初始化说话人分离服务
        
        Args:
            diarization_config: 说话人分离配置字典
            huggingface_config: HuggingFace配置字典
        """
        if Pipeline is None:
            raise ImportError("pyannote.audio未安装。请运行: pip install pyannote-audio")
            
        self.config = diarization_config
        self.hf_config = huggingface_config
        self.logger = logging.getLogger('project_bach.speaker_diarization')
        self._pipeline = None  # 延迟加载
        
        # 从配置中获取基本参数
        self.provider = diarization_config.get('provider', 'pyannote')
        self.max_speakers = diarization_config.get('max_speakers', 6)
        self.min_segment_duration = diarization_config.get('min_segment_duration', 1.0)
        self.model_path = Path(diarization_config.get('model_path', './models/diarization'))
        
        # 内容类型默认设置
        self.content_type_defaults = diarization_config.get('content_type_defaults', {})
        
        # 输出格式配置
        self.output_format = diarization_config.get('output_format', {
            'group_by_speaker': True,
            'timestamp_precision': 1,
            'include_confidence': False
        })
        
        self.logger.info(f"Speaker Diarization服务初始化完成")
        self.logger.info(f"提供商: {self.provider}")
        self.logger.info(f"最大说话人数: {self.max_speakers}")
        self.logger.info(f"最小段落时长: {self.min_segment_duration}秒")
        
    def should_enable_diarization(self, content_type: str, subcategory: str = None) -> bool:
        """根据内容类型和子分类判断是否应该启用diarization
        
        Args:
            content_type: 内容类型 (lecture, meeting等)
            subcategory: 子分类 (cs, seminar, standup等)
            
        Returns:
            是否应该启用diarization
        """
        defaults = self.content_type_defaults
        
        # 检查子分类设置
        if subcategory:
            subcategory_key = f"{content_type}_subcategories"
            if subcategory_key in defaults:
                subcategory_defaults = defaults[subcategory_key]
                if subcategory in subcategory_defaults:
                    result = subcategory_defaults[subcategory]
                    self.logger.debug(f"使用子分类设置 {content_type}/{subcategory}: {result}")
                    return result
        
        # 使用主分类默认设置
        if content_type in defaults:
            result = defaults[content_type]
            self.logger.debug(f"使用主分类设置 {content_type}: {result}")
            return result
        
        # 未知类型默认不启用
        self.logger.debug(f"未知内容类型 {content_type}，默认不启用diarization")
        return False
    
    def diarize_audio(self, audio_path: Path, **kwargs) -> List[Dict[str, Any]]:
        """执行说话人分离
        
        Args:
            audio_path: 音频文件路径
            **kwargs: 额外参数
            
        Returns:
            说话人段落列表，每个元素包含speaker, start, end等信息
            
        Raises:
            Exception: 说话人分离失败
        """
        # 验证音频文件存在
        if not audio_path.exists():
            raise Exception(f"音频文件不存在: {audio_path}")
        
        file_size_mb = audio_path.stat().st_size / (1024 * 1024)
        self.logger.info(f"开始说话人分离: {audio_path.name}")
        self.logger.info(f"文件大小: {file_size_mb:.1f}MB")
        
        try:
            # 设置HuggingFace token
            self._setup_huggingface_token()
            
            # 获取或初始化pipeline
            pipeline = self._get_pipeline()
            
            # 执行diarization
            self.logger.info("正在执行说话人分离...")
            diarization_result = pipeline(str(audio_path))
            
            # 转换结果格式
            speaker_segments = []
            for segment, _, speaker in diarization_result.itertracks(yield_label=True):
                speaker_segments.append({
                    'speaker': speaker,
                    'start': round(segment.start, self.output_format.get('timestamp_precision', 1)),
                    'end': round(segment.end, self.output_format.get('timestamp_precision', 1))
                })
            
            self.logger.info(f"识别出 {len(speaker_segments)} 个说话人段落")
            
            # 统计说话人数量
            unique_speakers = set(seg['speaker'] for seg in speaker_segments)
            self.logger.info(f"检测到 {len(unique_speakers)} 个不同的说话人: {', '.join(sorted(unique_speakers))}")
            
            return speaker_segments
            
        except Exception as e:
            error_msg = f"Speaker diarization失败: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
    
    def merge_with_transcription(self, transcription: Dict[str, Any], 
                                speaker_segments: List[Dict[str, Any]], 
                                group_by_speaker: bool = True) -> List[Dict[str, Any]]:
        """合并转录文本与说话人信息
        
        Args:
            transcription: 转录结果，包含text和chunks
            speaker_segments: 说话人段落列表
            group_by_speaker: 是否按说话人分组
            
        Returns:
            合并后的结果列表
        """
        if 'chunks' not in transcription:
            self.logger.warning("转录结果中缺少chunks信息，无法进行时间戳对齐")
            return [{'text': transcription.get('text', ''), 'speaker': 'Unknown'}]
        
        chunks = transcription['chunks']
        self.logger.info(f"开始合并转录与说话人信息: {len(chunks)} chunks, {len(speaker_segments)} speaker segments")
        
        # 第一步：对齐时间戳，为每个chunk分配说话人
        aligned_chunks = self._align_timestamps_with_speakers(chunks, speaker_segments)
        
        # 第二步：根据group_by_speaker选择输出模式
        if group_by_speaker:
            result = self._group_by_speaker_mode(aligned_chunks)
        else:
            result = self._chunk_level_mode(aligned_chunks)
        
        self.logger.info(f"合并完成，生成 {len(result)} 个输出段落")
        return result
    
    def _align_timestamps_with_speakers(self, chunks: List[Dict[str, Any]], 
                                       speaker_segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """时间戳对齐算法 - 为ASR chunks分配说话人标签
        
        基于HuggingFace ASRDiarizationPipeline的对齐算法实现
        
        Args:
            chunks: ASR转录chunks
            speaker_segments: 说话人段落
            
        Returns:
            对齐后的chunks，每个chunk包含speaker信息
        """
        if not chunks or not speaker_segments:
            return chunks
        
        # 提取ASR chunk的结束时间戳
        end_timestamps = np.array([chunk["timestamp"][1] for chunk in chunks])
        
        # 为每个说话人段落找到对应的ASR chunks
        aligned_chunks = []
        current_chunk_idx = 0
        
        for speaker_segment in speaker_segments:
            speaker = speaker_segment["speaker"]
            segment_end = speaker_segment["end"]
            
            # 使用numpy.argmin找到最接近的ASR时间戳
            # 找到所有结束时间小于等于当前说话人段落结束时间的chunks
            valid_indices = np.where(end_timestamps <= segment_end)[0]
            
            if len(valid_indices) == 0:
                continue  # 没有匹配的chunks
            
            # 找到最后一个有效的chunk索引
            last_valid_idx = valid_indices[-1]
            
            # 将从current_chunk_idx到last_valid_idx的所有chunks分配给当前说话人
            for i in range(current_chunk_idx, min(last_valid_idx + 1, len(chunks))):
                chunk = chunks[i].copy()
                chunk['speaker'] = speaker
                aligned_chunks.append(chunk)
            
            # 更新下一个开始位置
            current_chunk_idx = last_valid_idx + 1
        
        # 处理剩余的chunks（分配给最后一个说话人或标记为未知）
        if current_chunk_idx < len(chunks):
            last_speaker = speaker_segments[-1]["speaker"] if speaker_segments else "Unknown"
            for i in range(current_chunk_idx, len(chunks)):
                chunk = chunks[i].copy()
                chunk['speaker'] = last_speaker
                aligned_chunks.append(chunk)
        
        self.logger.debug(f"时间戳对齐完成: {len(chunks)} chunks -> {len(aligned_chunks)} aligned chunks")
        return aligned_chunks
    
    def _group_by_speaker_mode(self, aligned_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """按说话人分组模式 - 合并同一说话人的连续chunks
        
        适用场景：会议纪要、对话摘要
        
        Args:
            aligned_chunks: 已对齐的chunks
            
        Returns:
            按说话人分组的结果
        """
        if not aligned_chunks:
            return []
        
        grouped_result = []
        current_group = None
        
        for chunk in aligned_chunks:
            speaker = chunk['speaker']
            text = chunk['text']
            timestamp = chunk['timestamp']
            
            # 如果是同一个说话人，合并到当前组
            if current_group and current_group['speaker'] == speaker:
                current_group['text'] += ' ' + text
                current_group['timestamp'][1] = timestamp[1]  # 更新结束时间
            else:
                # 新的说话人，保存上一个组并开始新组
                if current_group:
                    grouped_result.append(current_group)
                
                current_group = {
                    'speaker': speaker,
                    'text': text,
                    'timestamp': [timestamp[0], timestamp[1]]
                }
        
        # 添加最后一个组
        if current_group:
            grouped_result.append(current_group)
        
        self.logger.debug(f"按说话人分组: {len(aligned_chunks)} chunks -> {len(grouped_result)} groups")
        return grouped_result
    
    def _chunk_level_mode(self, aligned_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Chunk级别模式 - 保持ASR chunk粒度，为每个chunk分配说话人
        
        适用场景：字幕制作、语音分析
        
        Args:
            aligned_chunks: 已对齐的chunks
            
        Returns:
            chunk级别的结果
        """
        # 在chunk级别模式下，直接返回对齐后的chunks
        self.logger.debug(f"Chunk级别模式: 保持 {len(aligned_chunks)} chunks")
        return aligned_chunks
    
    def _get_pipeline(self) -> Pipeline:
        """获取或初始化pyannote pipeline
        
        Returns:
            pyannote Pipeline实例
        """
        if self._pipeline is None:
            self.logger.info("初始化pyannote.audio pipeline...")
            
            try:
                # 使用预训练的speaker diarization pipeline
                self._pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    use_auth_token=self.hf_config.get('token')
                )
                
                # 设置最大说话人数
                self._pipeline.max_speakers = self.max_speakers
                
                self.logger.info("pyannote.audio pipeline初始化成功")
                
            except Exception as e:
                error_msg = f"初始化pyannote pipeline失败: {str(e)}"
                self.logger.error(error_msg)
                raise Exception(error_msg)
        
        return self._pipeline
    
    def _setup_huggingface_token(self):
        """设置HuggingFace认证token"""
        hf_token = self.hf_config.get('token')
        if hf_token:
            os.environ['HUGGINGFACE_HUB_TOKEN'] = hf_token
            self.logger.debug("HuggingFace token已设置")
        else:
            # 尝试从环境变量获取
            env_token = os.environ.get('HUGGINGFACE_TOKEN')
            if env_token:
                os.environ['HUGGINGFACE_HUB_TOKEN'] = env_token
                self.logger.debug("使用环境变量中的HuggingFace token")
            else:
                self.logger.warning("未找到HuggingFace token，可能影响模型下载")
    
    def get_speaker_statistics(self, speaker_segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """获取说话人统计信息
        
        Args:
            speaker_segments: 说话人段落列表
            
        Returns:
            统计信息字典
        """
        if not speaker_segments:
            return {'total_speakers': 0, 'total_duration': 0, 'speaker_durations': {}}
        
        # 计算每个说话人的总时长
        speaker_durations = {}
        total_duration = 0
        
        for segment in speaker_segments:
            speaker = segment['speaker']
            duration = segment['end'] - segment['start']
            
            if speaker not in speaker_durations:
                speaker_durations[speaker] = 0
            speaker_durations[speaker] += duration
            total_duration += duration
        
        # 计算说话比例
        speaker_ratios = {}
        for speaker, duration in speaker_durations.items():
            speaker_ratios[speaker] = duration / total_duration if total_duration > 0 else 0
        
        return {
            'total_speakers': len(speaker_durations),
            'total_duration': round(total_duration, 2),
            'speaker_durations': {k: round(v, 2) for k, v in speaker_durations.items()},
            'speaker_ratios': {k: round(v, 3) for k, v in speaker_ratios.items()},
            'total_segments': len(speaker_segments)
        }
    
    def cleanup(self):
        """清理资源"""
        if self._pipeline is not None:
            self.logger.info("清理pyannote pipeline")
            self._pipeline = None
            
        # 清理GPU内存（如果使用）
        if torch is not None and torch.cuda.is_available():
            torch.cuda.empty_cache()


