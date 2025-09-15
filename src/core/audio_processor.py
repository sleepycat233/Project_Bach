#!/usr/bin/env python3.11
"""
音频处理流程编排器
负责协调各个模块完成音频处理流程
"""

import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from .mlx_transcription import MLXTranscriptionService as TranscriptionService
from .anonymization import NameAnonymizer
from .ai_generation import AIContentGenerator
from .speaker_diarization import SpeakerDiarization
from ..storage.transcript_storage import TranscriptStorage
from ..storage.result_storage import ResultStorage
from ..publishing.git_publisher import GitPublisher
from ..monitoring.file_monitor import FileMonitor
from ..utils.config import ConfigManager
from .processing_service import ProcessingService, ProcessingStage, get_processing_service


class AudioProcessor:
    """音频处理流程编排器 - 轻量级版本"""

    def __init__(self, config_manager: ConfigManager):
        """初始化音频处理器

        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger('project_bach.audio_processor')

        # 服务组件（通过依赖注入设置）
        self.transcription_service: Optional[TranscriptionService] = None
        self.anonymization_service: Optional[NameAnonymizer] = None
        self.ai_generation_service: Optional[AIContentGenerator] = None
        self.speaker_diarization_service: Optional[SpeakerDiarization] = None
        self.transcript_storage: Optional[TranscriptStorage] = None
        self.result_storage: Optional[ResultStorage] = None

        # 处理状态服务
        self.processing_service: ProcessingService = get_processing_service()

        # 文件监控器（可选）
        self.file_monitor: Optional[FileMonitor] = None

        # Git发布服务（可选）
        self.git_publisher: Optional[GitPublisher] = None

    def set_transcription_service(self, service: TranscriptionService):
        """设置转录服务

        Args:
            service: 转录服务实例
        """
        self.transcription_service = service
        self.logger.debug("转录服务已设置")

    def set_anonymization_service(self, service: NameAnonymizer):
        """设置匿名化服务

        Args:
            service: 匿名化服务实例
        """
        self.anonymization_service = service
        self.logger.debug("匿名化服务已设置")

    def set_ai_generation_service(self, service: AIContentGenerator):
        """设置AI生成服务

        Args:
            service: AI生成服务实例
        """
        self.ai_generation_service = service
        self.logger.debug("AI生成服务已设置")

    def set_speaker_diarization_service(self, service: SpeakerDiarization):
        """设置说话人分离服务

        Args:
            service: 说话人分离服务实例
        """
        self.speaker_diarization_service = service
        self.logger.debug("说话人分离服务已设置")

    def set_storage_services(self, transcript_storage: TranscriptStorage, result_storage: ResultStorage):
        """设置存储服务

        Args:
            transcript_storage: 转录存储服务
            result_storage: 结果存储服务
        """
        self.transcript_storage = transcript_storage
        self.result_storage = result_storage
        self.logger.debug("存储服务已设置")

    def set_file_monitor(self, monitor: FileMonitor):
        """设置文件监控器

        Args:
            monitor: 文件监控器实例
        """
        self.file_monitor = monitor

    def set_git_publisher(self, publisher: GitPublisher):
        """设置Git发布服务

        Args:
            publisher: Git发布服务实例
        """
        self.git_publisher = publisher

    def _clean_transcription_for_output(self, transcription_result):
        """清理转录结果，只保留输出需要的字段"""
        if not isinstance(transcription_result, dict):
            return transcription_result

        import copy
        cleaned = copy.deepcopy(transcription_result)

        # 清理chunks中不必要的字段，只保留核心信息用于存储
        if 'chunks' in cleaned and isinstance(cleaned['chunks'], list):
            cleaned_chunks = []
            for chunk in cleaned['chunks']:
                if isinstance(chunk, dict):
                    # 只保留核心字段
                    cleaned_chunk = {
                        'text': chunk.get('text', ''),
                        'timestamp': chunk.get('timestamp', [0, 0])
                    }
                    cleaned_chunks.append(cleaned_chunk)

            cleaned['chunks'] = cleaned_chunks

        return cleaned

    def process_audio_file(self, audio_path: str, privacy_level: str = 'public', metadata: Dict[str, Any] = None, processing_id: str = None) -> bool:
        """处理单个音频文件的完整流程

        Args:
            audio_path: 音频文件路径
            privacy_level: 隐私级别 ('public' 或 'private')
            metadata: 处理元数据，包含content_type、subcategory、description(Whisper prompt)和audio_language
            processing_id: 处理ID (可选)

        Returns:
            处理是否成功
        """
        # 验证依赖
        if not self._validate_dependencies():
            return False

        start_time = time.time()
        audio_path = Path(audio_path)

        self.logger.info(f"开始处理音频文件: {audio_path.name}")

        try:
            # 获取metadata信息
            prompt = metadata.get('description', '') if metadata else ''
            audio_language = metadata.get('audio_language', 'english') if metadata else 'english'

            # 步骤1: 音频转录（使用description作为Whisper prompt）
            self.logger.info("步骤1: 开始音频转录")
            if processing_id:
                self.processing_service.update_status(processing_id, ProcessingStage.TRANSCRIBING, 20, "Transcribing audio...")

            # 提取模型选择参数
            custom_model = metadata.get('whisper_model') if metadata else None

            # 步骤0: 判断是否需要说话人分离（决定word_timestamps参数）
            should_diarize = False
            if self.speaker_diarization_service:
                content_type = metadata.get('content_type') if metadata else None
                subcategory = metadata.get('subcategory') if metadata else None
                enable_diarization = metadata.get('enable_diarization', None) if metadata else None

                # 简化的diarization决策：直接使用前端传来的选择（已包含默认值处理）
                should_diarize = enable_diarization if enable_diarization is not None else False
                self.logger.info(f"🔍 Diarization设置: {should_diarize} (来自前端选择，content_type='{content_type}')")

                if should_diarize:
                    self.logger.info("检测到需要说话人分离，启用词级时间戳")
                else:
                    self.logger.info("无需说话人分离，关闭词级时间戳以优化性能")

            transcription_result = self.transcription_service.transcribe_audio(
                audio_path,
                prompt=prompt,
                language_preference=audio_language,
                custom_model=custom_model,
                word_timestamps=should_diarize
            )
            if not transcription_result:
                raise Exception("转录失败或结果为空")

            # 从转录结果中提取文本
            transcript = transcription_result.get('text', '') if isinstance(transcription_result, dict) else transcription_result

            # 保存原始转录
            self.transcript_storage.save_raw_transcript(audio_path.stem, transcript, privacy_level)

            # 步骤1.5: 说话人分离（可选）
            diarization_result = None
            if self.speaker_diarization_service and should_diarize:
                self.logger.info("步骤1.5: 开始说话人分离")
                if processing_id:
                    self.processing_service.update_status(processing_id, ProcessingStage.TRANSCRIBING, 30, "Analyzing speakers...")

                try:
                    speaker_segments = self.speaker_diarization_service.diarize_audio(audio_path)

                    if speaker_segments:
                        content_type = metadata.get('content_type') if metadata else None
                        subcategory = metadata.get('subcategory') if metadata else None

                        # 合并转录结果与说话人信息
                        self.logger.info("步骤1.6: 合并转录与说话人信息")
                        try:
                            merged_transcription = self.speaker_diarization_service.merge_with_transcription(
                                transcription_result,  # 包含chunks的完整转录结果
                                speaker_segments,
                                group_by_speaker=True  # 按说话人分组模式
                            )
                        except Exception as merge_error:
                            self.logger.error(f"转录合并失败: {merge_error}")
                            merged_transcription = None

                        diarization_result = {
                            'has_diarization': True,
                            'speaker_segments': speaker_segments,
                            'merged_transcription': merged_transcription,  # 添加合并结果
                            'speaker_statistics': self.speaker_diarization_service.get_speaker_statistics(speaker_segments),
                            'content_type': content_type,
                            'subcategory': subcategory
                        }
                        self.logger.info(f"说话人分离完成: {len(merged_transcription)} 个发言段落")
                    else:
                        self.logger.warning("说话人分离未检测到多个说话人")

                except Exception as e:
                    self.logger.error(f"说话人分离处理失败: {e}")
                    # 继续处理，不影响主流程

            # 获取Post-Processing配置
            enable_anonymization = metadata.get('enable_anonymization', True) if metadata else True
            enable_summary = metadata.get('enable_summary', True) if metadata else True
            enable_mindmap = metadata.get('enable_mindmap', True) if metadata else True

            # 步骤2: 人名匿名化（可选）
            anonymized_text = transcript
            mapping = {}
            
            if enable_anonymization:
                self.logger.info("步骤2: 开始人名匿名化")
                if processing_id:
                    self.processing_service.update_status(processing_id, ProcessingStage.ANONYMIZING, 50, "Anonymizing personal names...")
                anonymized_text, mapping = self.anonymization_service.anonymize_names(transcript)
                self.transcript_storage.save_anonymized_transcript(audio_path.stem, anonymized_text, privacy_level)

                # 记录匿名化映射
                if mapping:
                    self.logger.info(f"人名匿名化映射: {mapping}")
            else:
                self.logger.info("步骤2: 跳过人名匿名化（用户未启用）")

            # 步骤3: AI内容生成（可选）
            summary = ""
            mindmap = ""
            
            if enable_summary or enable_mindmap:
                self.logger.info("步骤3: 开始AI内容生成")
                if processing_id:
                    self.processing_service.update_status(processing_id, ProcessingStage.AI_GENERATING, 70, "Generating AI content...")
                
                if enable_summary:
                    summary = self.ai_generation_service.generate_summary(anonymized_text)
                    self.logger.info("摘要生成完成")
                else:
                    self.logger.info("跳过摘要生成（用户未启用）")
                
                if enable_mindmap:
                    mindmap = self.ai_generation_service.generate_mindmap(anonymized_text)
                    self.logger.info("思维导图生成完成")
                else:
                    self.logger.info("跳过思维导图生成（用户未启用）")
            else:
                self.logger.info("步骤3: 跳过AI内容生成（用户未启用）")

            # 步骤4: 保存结果
            self.logger.info("步骤4: 保存处理结果")
            
            # 构建统一的元数据结构
            metadata_dict = {
                'filename': audio_path.stem,
                'original_file': str(audio_path),
                'processed_time': datetime.now().isoformat(),
                'format_version': '2.0',
                'privacy_level': privacy_level,
            }
            
            # 添加上传时的元数据（包含分类信息）
            if metadata:
                metadata_dict.update({
                    'content_type': metadata.get('content_type', 'others'),
                    'subcategory': metadata.get('subcategory', ''),
                    'audio_language': metadata.get('audio_language', ''),
                    'whisper_model': metadata.get('whisper_model', ''),
                    'description': metadata.get('description', ''),
                    'file_size': metadata.get('file_size', 0)
                })
            
            # 根级别的核心数据（新结构）
            results = {
                'summary': summary,
                'mindmap': mindmap,
                'transcription': self._clean_transcription_for_output(transcription_result),
                'anonymized_transcript': anonymized_text,
                'anonymization_mapping': mapping,
                'metadata': metadata_dict
            }

            # 添加说话人分离结果（如果存在）
            if 'diarization_result' in locals():
                results['diarization_result'] = diarization_result
                self.logger.info("已添加说话人分离结果到输出")

                # 重要：如果有diarization，使用合并后的转录结果作为主要输出
                if (diarization_result and
                    'merged_transcription' in diarization_result and
                    diarization_result['merged_transcription'] is not None):
                    results['transcription_with_speakers'] = diarization_result['merged_transcription']
                    self.logger.info("已添加按说话人分组的转录结果")

            # 按隐私级别保存结果
            self.result_storage.save_json_result(audio_path.stem, results, privacy_level=privacy_level)
            self.result_storage.save_html_result(audio_path.stem, results, privacy_level=privacy_level)

            # 自动发布到GitHub Pages
            if self.git_publisher and privacy_level == 'public':
                result_filename = f"{audio_path.stem}_result.html"
                publish_success = self.git_publisher.publish_result(result_filename, privacy_level)
                if publish_success:
                    self.logger.info(f"音频处理结果已自动发布到GitHub Pages: {result_filename}")
                else:
                    self.logger.warning(f"GitHub Pages自动发布失败: {result_filename}")

            # 完成处理
            if processing_id:
                status_msg = f"Processing complete ({privacy_level} content)"
                self.processing_service.update_status(processing_id, ProcessingStage.COMPLETED, 100, status_msg)

            elapsed = time.time() - start_time
            self.logger.info(f"处理完成: {audio_path.name} (耗时: {elapsed:.2f}秒, 隐私级别: {privacy_level})")
            return True

        except Exception as e:
            self.logger.error(f"处理失败: {audio_path.name} - {str(e)}")
            if processing_id:
                self.processing_service.update_status(processing_id, ProcessingStage.FAILED, 0, f"Processing failed: {str(e)}")
            return False


    def _validate_dependencies(self) -> bool:
        """验证所有必要的依赖是否已设置

        Returns:
            依赖是否完整
        """
        missing_deps = []

        if self.transcription_service is None:
            missing_deps.append("转录服务")
        if self.anonymization_service is None:
            missing_deps.append("匿名化服务")
        if self.ai_generation_service is None:
            missing_deps.append("AI生成服务")
        if self.transcript_storage is None:
            missing_deps.append("转录存储服务")
        if self.result_storage is None:
            missing_deps.append("结果存储服务")

        if missing_deps:
            self.logger.error(f"缺少必要的依赖: {', '.join(missing_deps)}")
            return False

        return True

    def start_file_monitoring(self):
        """启动文件监控（如果已设置）"""
        if self.file_monitor is None:
            self.logger.error("文件监控器未设置，无法启动监控")
            return False

        try:
            self.file_monitor.start_monitoring()
            self.logger.info("自动文件监控已启动")
            return True
        except Exception as e:
            self.logger.error(f"启动文件监控失败: {str(e)}")
            return False

    def stop_file_monitoring(self):
        """停止文件监控"""
        if self.file_monitor:
            self.file_monitor.stop_monitoring()
            self.logger.info("自动文件监控已停止")

    def get_queue_status(self) -> Dict[str, Any]:
        """获取处理队列状态

        Returns:
            队列状态信息
        """
        if not self.file_monitor:
            return {"status": "monitoring_not_available"}

        return self.file_monitor.get_queue_status()

    def process_batch_files(self, file_paths: list) -> Dict[str, bool]:
        """批量处理音频文件

        Args:
            file_paths: 文件路径列表

        Returns:
            文件路径到处理结果的映射
        """
        results = {}

        for file_path in file_paths:
            self.logger.info(f"批量处理文件: {Path(file_path).name}")
            results[file_path] = self.process_audio_file(file_path)

        # 统计结果
        success_count = sum(1 for success in results.values() if success)
        total_count = len(file_paths)

        self.logger.info(f"批量处理完成: {success_count}/{total_count} 成功")

        return results

    def process_youtube_content(self, youtube_result: Dict[str, Any], privacy_level: str = 'public') -> bool:
        """处理YouTube内容（字幕优先策略）

        Args:
            youtube_result: YouTubeProcessor的处理结果
            privacy_level: 隐私级别 ('public' 或 'private')

        Returns:
            处理是否成功
        """
        try:
            video_metadata = youtube_result.get('video_metadata', {})
            video_id = video_metadata.get('video_id', 'unknown')
            video_title = video_metadata.get('title', 'Unknown Video')

            self.logger.info(f"开始处理YouTube内容: {video_title}")

            # 确定转录文本来源
            transcript_text = ""
            transcription_method = youtube_result.get('transcription_method', 'unknown')

            if transcription_method == 'subtitles':
                # 使用字幕文本
                transcript_text = youtube_result.get('transcript_text', '')
                self.logger.info(f"使用YouTube字幕: {len(transcript_text)}字符")
            elif transcription_method == 'whisper':
                # 使用Whisper转录
                audio_file_path = youtube_result.get('audio_file_path')
                if audio_file_path and Path(audio_file_path).exists():
                    if not self.transcription_service:
                        self.logger.error("Whisper转录服务未配置")
                        return False

                    self.logger.info("使用Whisper转录音频")
                    # YouTube处理默认不启用word_timestamps（无diarization需求）
                    transcript_text = self.transcription_service.transcribe_audio(
                        Path(audio_file_path),
                        word_timestamps=False
                    )

                    if transcript_text and transcript_text.strip():
                        self.logger.info(f"Whisper转录完成: {len(transcript_text)}字符")
                    else:
                        self.logger.error("Whisper转录失败或结果为空")
                        return False
                else:
                    self.logger.error("音频文件路径无效")
                    return False
            else:
                self.logger.error(f"未知的转录方法: {transcription_method}")
                return False

            if not transcript_text.strip():
                self.logger.error("转录文本为空")
                return False

            # YouTube视频不需要人名匿名化（已是公开资源）
            anonymized_text = transcript_text
            mapping = {}
            self.logger.info("跳过人名匿名化处理（YouTube内容为公开资源）")

            # AI内容生成
            if not self.ai_generation_service:
                self.logger.error("AI内容生成服务未配置")
                return False

            self.logger.info("开始AI内容生成")
            summary = self.ai_generation_service.generate_summary(anonymized_text)
            mindmap = self.ai_generation_service.generate_mindmap(anonymized_text)

            if not summary or not mindmap:
                self.logger.error("AI内容生成失败")
                return False

            # 保存转录结果
            if self.transcript_storage:
                self.transcript_storage.save_raw_transcript(
                    filename=f"youtube_{video_id}",
                    content=transcript_text,
                    privacy_level=privacy_level
                )
                self.transcript_storage.save_anonymized_transcript(
                    filename=f"youtube_{video_id}",
                    content=anonymized_text,
                    privacy_level=privacy_level
                )

            # 保存最终结果
            if self.result_storage:
                # 构建统一的元数据结构
                metadata_dict = {
                    'filename': f"youtube_{video_id}",
                    'original_file': youtube_result.get('source_url', ''),
                    'processed_time': datetime.now().isoformat(),
                    'format_version': '2.0',
                    'privacy_level': privacy_level,
                    'content_type': 'youtube',
                    'transcription_method': transcription_method,
                    'title': video_title,
                    'video_metadata': video_metadata
                }
                
                # 添加upload_metadata（包含用户提交的信息）
                upload_metadata = youtube_result.get('upload_metadata', {})
                if upload_metadata:
                    metadata_dict.update({
                        'subcategory': upload_metadata.get('subcategory', ''),
                        'description': upload_metadata.get('description', '')
                    })
                
                # 根级别的核心数据（新结构）
                result_data = {
                    'summary': summary,
                    'mindmap': mindmap,
                    'transcription': anonymized_text,  # YouTube的原始转录（不保存匿名化前的）
                    'anonymized_transcript': anonymized_text,
                    'anonymization_mapping': mapping,
                    'metadata': metadata_dict
                }

                # 保存HTML和JSON格式的YouTube处理结果
                self.result_storage.save_html_result(
                    filename=f"youtube_{video_id}",
                    results=result_data,
                    privacy_level=privacy_level
                )
                self.result_storage.save_json_result(
                    filename=f"youtube_{video_id}",
                    results=result_data,
                    privacy_level=privacy_level
                )

            # 自动发布到GitHub Pages
            if self.git_publisher and privacy_level == 'public':
                result_filename = f"youtube_{video_id}_result.html"
                publish_success = self.git_publisher.publish_result(result_filename, privacy_level)
                if publish_success:
                    self.logger.info(f"YouTube内容已自动发布到GitHub Pages: {result_filename}")
                else:
                    self.logger.warning(f"GitHub Pages自动发布失败: {result_filename}")

            self.logger.info(f"YouTube内容处理完成: {video_title}")
            return True

        except Exception as e:
            self.logger.error(f"YouTube内容处理异常: {e}")
            return False

    def _generate_youtube_html(self, video_metadata: Dict, summary: str, mindmap: str,
                             transcription_method: str, privacy_level: str) -> str:
        """生成包含YouTube视频嵌入的HTML内容

        Args:
            video_metadata: 视频元数据
            summary: AI生成的摘要
            mindmap: AI生成的思维导图
            transcription_method: 转录方法
            privacy_level: 隐私级别

        Returns:
            完整的HTML内容
        """
        video_id = video_metadata.get('video_id', '')
        title = video_metadata.get('title', 'Unknown Video')
        channel_name = video_metadata.get('channel_name', 'Unknown Channel')
        duration_formatted = video_metadata.get('duration_formatted', 'Unknown')
        upload_date_formatted = video_metadata.get('upload_date_formatted', 'Unknown')

        # 隐私标识
        privacy_badge = "🔒 Private" if privacy_level == 'private' else "🌐 Public"

        # 转录方法标识
        method_badge = "📄 Subtitles" if transcription_method == 'subtitles' else "🎤 Whisper"

        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Project Bach</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
            background-color: #f8f9fa;
        }}
        .header {{
            background: white;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .video-container {{
            position: relative;
            padding-bottom: 56.25%;
            height: 0;
            overflow: hidden;
            background: white;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .video-container iframe {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            border-radius: 12px;
        }}
        .content-section {{
            background: white;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .badges {{
            margin: 10px 0;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 16px;
            font-size: 0.9em;
            font-weight: 500;
            margin-right: 8px;
        }}
        .badge-privacy {{
            background-color: {"#dc3545" if privacy_level == "private" else "#28a745"};
            color: white;
        }}
        .badge-method {{
            background-color: #6f42c1;
            color: white;
        }}
        .meta-info {{
            color: #6c757d;
            font-size: 0.9em;
            margin-top: 10px;
        }}
        .summary {{
            margin-top: 20px;
        }}
        .mindmap {{
            background: #f8f9ff;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #6f42c1;
            margin-top: 20px;
        }}
        .nav-links {{
            text-align: center;
            margin-top: 30px;
            padding: 15px;
            background: #e9ecef;
            border-radius: 8px;
        }}
        .nav-links a {{
            color: #495057;
            text-decoration: none;
            margin: 0 15px;
            font-weight: 500;
        }}
        h1 {{ color: #343a40; margin-bottom: 10px; }}
        h2 {{ color: #495057; border-bottom: 2px solid #e9ecef; padding-bottom: 8px; }}
        pre {{ white-space: pre-wrap; background: #f8f9fa; padding: 15px; border-radius: 6px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{title}</h1>
        <div class="badges">
            <span class="badge badge-privacy">{privacy_badge}</span>
            <span class="badge badge-method">{method_badge}</span>
        </div>
        <div class="meta-info">
            <strong>频道:</strong> {channel_name} |
            <strong>时长:</strong> {duration_formatted} |
            <strong>上传时间:</strong> {upload_date_formatted}
        </div>
    </div>

    <div class="video-container">
        <iframe
            src="https://www.youtube.com/embed/{video_id}"
            title="YouTube video player"
            frameborder="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            allowfullscreen>
        </iframe>
    </div>

    <div class="content-section">
        <h2>📋 内容摘要</h2>
        <div class="summary">
            {summary.replace(chr(10), '<br>')}
        </div>
    </div>

    <div class="content-section">
        <h2>🧠 思维导图</h2>
        <div class="mindmap">
            <pre>{mindmap}</pre>
        </div>
    </div>

    <div class="nav-links">
        <a href="{"/" if privacy_level == "public" else "/private/"}"">← 返回主页</a>
        {"| <a href='/private/'>Private内容</a>" if privacy_level == "private" else ""}
    </div>

    <footer style="text-align: center; margin-top: 30px; color: #6c757d; font-size: 0.9em;">
        <p>Generated by Project Bach - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </footer>
</body>
</html>'''

        return html_content


    def validate_audio_file(self, file_path: str) -> bool:
        """验证音频文件是否有效

        Args:
            file_path: 文件路径

        Returns:
            文件是否有效
        """
        try:
            path = Path(file_path)

            # 检查文件是否存在
            if not path.exists():
                self.logger.error(f"文件不存在: {file_path}")
                return False

            # 检查文件大小
            if path.stat().st_size == 0:
                self.logger.error(f"文件为空: {file_path}")
                return False

            # 检查文件扩展名
            if self.file_monitor:
                supported_formats = self.file_monitor.get_supported_formats()
                if path.suffix.lower() not in supported_formats:
                    self.logger.error(f"不支持的文件格式: {path.suffix}")
                    return False

            return True

        except Exception as e:
            self.logger.error(f"验证文件时出错: {file_path}, 错误: {str(e)}")
            return False

    def force_process_file(self, file_path: str) -> bool:
        """强制处理指定文件（跳过队列）

        Args:
            file_path: 文件路径

        Returns:
            处理是否成功
        """
        if not self.validate_audio_file(file_path):
            return False

        self.logger.info(f"强制处理文件: {Path(file_path).name}")
        return self.process_audio_file(file_path)

