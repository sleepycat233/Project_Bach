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

from .transcription import TranscriptionService
from .anonymization import NameAnonymizer
from .ai_generation import AIContentGenerator
from ..storage.transcript_storage import TranscriptStorage
from ..storage.result_storage import ResultStorage
from ..monitoring.file_monitor import FileMonitor
from ..publishing.publishing_workflow import PublishingWorkflow
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
        self.transcript_storage: Optional[TranscriptStorage] = None
        self.result_storage: Optional[ResultStorage] = None
        self.publishing_workflow: Optional[PublishingWorkflow] = None
        
        # 处理状态服务
        self.processing_service: ProcessingService = get_processing_service()
        
        # 文件监控器（可选）
        self.file_monitor: Optional[FileMonitor] = None
    
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
    
    def set_publishing_workflow(self, workflow: PublishingWorkflow):
        """设置发布工作流
        
        Args:
            workflow: 发布工作流实例
        """
        self.publishing_workflow = workflow
        self.logger.debug("发布工作流已设置")
    
    def process_audio_file(self, audio_path: str, privacy_level: str = 'public', metadata: Dict[str, Any] = None, processing_id: str = None) -> bool:
        """处理单个音频文件的完整流程
        
        Args:
            audio_path: 音频文件路径
            privacy_level: 隐私级别 ('public' 或 'private')
            metadata: 处理元数据，包含description(Whisper prompt)和audio_language
            
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
            custom_model_prefix = metadata.get('model_prefix') if metadata else None
            
            transcript = self.transcription_service.transcribe_audio(
                audio_path, 
                prompt=prompt, 
                language_preference=audio_language,
                custom_model=custom_model,
                custom_model_prefix=custom_model_prefix
            )
            if not transcript:
                raise Exception("转录失败或结果为空")
            
            # 保存原始转录
            self.transcript_storage.save_raw_transcript(audio_path.stem, transcript, privacy_level)
            
            # 步骤2: 人名匿名化
            self.logger.info("步骤2: 开始人名匿名化")
            if processing_id:
                self.processing_service.update_status(processing_id, ProcessingStage.ANONYMIZING, 50, "Anonymizing personal names...")
            anonymized_text, mapping = self.anonymization_service.anonymize_names(transcript)
            self.transcript_storage.save_anonymized_transcript(audio_path.stem, anonymized_text, privacy_level)
            
            # 记录匿名化映射
            if mapping:
                self.logger.info(f"人名匿名化映射: {mapping}")
            
            # 步骤3: AI内容生成
            self.logger.info("步骤3: 开始AI内容生成")
            if processing_id:
                self.processing_service.update_status(processing_id, ProcessingStage.AI_GENERATING, 70, "Generating AI content...")
            summary = self.ai_generation_service.generate_summary(anonymized_text)
            mindmap = self.ai_generation_service.generate_mindmap(anonymized_text)
            
            # 步骤4: 保存结果
            self.logger.info("步骤4: 保存处理结果")
            results = {
                'summary': summary,
                'mindmap': mindmap,
                'original_file': str(audio_path),
                'processed_time': datetime.now().isoformat(),
                'anonymized_transcript': anonymized_text,  # 添加匿名化转录文本
                'anonymization_mapping': mapping,
                'privacy_level': privacy_level
            }
            
            # 按隐私级别保存结果
            self.result_storage.save_markdown_result(audio_path.stem, results, privacy_level=privacy_level)
            self.result_storage.save_json_result(audio_path.stem, results, privacy_level=privacy_level)
            self.result_storage.save_html_result(audio_path.stem, results, privacy_level=privacy_level)
            
            # 步骤5: 自动部署到GitHub Pages (仅公开内容)
            if privacy_level == 'public' and self.publishing_workflow and self._should_auto_deploy():
                self.logger.info("步骤5: 开始自动部署到GitHub Pages")
                if processing_id:
                    self.processing_service.update_status(processing_id, ProcessingStage.PUBLISHING, 90, "Deploying to GitHub Pages...")
                try:
                    deploy_result = self.publishing_workflow.deploy_to_github_pages()
                    if deploy_result.get('success'):
                        self.logger.info("✅ 自动部署成功!")
                        if 'website_url' in deploy_result:
                            self.logger.info(f"🔗 网站地址: {deploy_result['website_url']}")
                            if processing_id:
                                self.processing_service.update_status(processing_id, ProcessingStage.COMPLETED, 100, f"Deployment successful! Website: {deploy_result['website_url']}")
                    else:
                        self.logger.warning(f"⚠️  自动部署失败: {deploy_result.get('error', '未知错误')}")
                        if processing_id:
                            self.processing_service.update_status(processing_id, ProcessingStage.COMPLETED, 100, f"Deployment failed but processing complete: {deploy_result.get('error', 'Unknown error')}")
                except Exception as e:
                    self.logger.error(f"❌ 自动部署异常: {e}")
                    if processing_id:
                        self.processing_service.update_status(processing_id, ProcessingStage.COMPLETED, 100, f"Deployment error but processing complete: {str(e)}")
            elif privacy_level == 'private':
                self.logger.info("私人内容，跳过GitHub Pages部署")
                if processing_id:
                    self.processing_service.update_status(processing_id, ProcessingStage.COMPLETED, 100, "Processing complete (private content, not deployed)")
            else:
                # 公开内容但没有启用部署或没有配置部署工作流
                self.logger.info("处理完成，但未配置自动部署")
                if processing_id:
                    self.processing_service.update_status(processing_id, ProcessingStage.COMPLETED, 100, "Processing complete (auto deployment not configured)")
            
            elapsed = time.time() - start_time
            self.logger.info(f"处理完成: {audio_path.name} (耗时: {elapsed:.2f}秒, 隐私级别: {privacy_level})")
            return True
            
        except Exception as e:
            self.logger.error(f"处理失败: {audio_path.name} - {str(e)}")
            if processing_id:
                self.processing_service.update_status(processing_id, ProcessingStage.FAILED, 0, f"Processing failed: {str(e)}")
            return False
    
    def _should_auto_deploy(self) -> bool:
        """检查是否应该自动部署
        
        Returns:
            是否应该自动部署
        """
        try:
            config = self.config_manager.get_full_config()
            return config.get('github', {}).get('publishing', {}).get('auto_deploy', False)
        except Exception:
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
                    transcription_result = self.transcription_service.transcribe_audio(audio_file_path)
                    
                    if transcription_result.get('success'):
                        transcript_text = transcription_result['transcript']
                        self.logger.info(f"Whisper转录完成: {len(transcript_text)}字符")
                    else:
                        self.logger.error(f"Whisper转录失败: {transcription_result.get('error')}")
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
                result_data = {
                    'title': video_title,
                    'video_id': video_id,
                    'video_url': youtube_result.get('source_url', ''),
                    'summary': summary,
                    'mindmap': mindmap,
                    'transcription_method': transcription_method,
                    'privacy_level': privacy_level,
                    'processed_time': datetime.now().isoformat(),
                    'content_type': 'youtube',
                    'video_metadata': video_metadata,
                    'anonymized_transcript': anonymized_text,  # 添加匿名化转录文本
                    'anonymization_mapping': mapping
                }
                
                # 保存HTML格式的YouTube处理结果
                self.result_storage.save_html_result(
                    filename=f"youtube_{video_id}",
                    results=result_data,
                    privacy_level=privacy_level
                )
            
            # 发布到GitHub Pages（仅公开内容 + 敏感内容保护）
            if privacy_level == 'public' and self.publishing_workflow:
                # 政治敏感内容检测 🕵️
                sensitive_keywords = ['习近平', '政治', '中共', '权力', '斯大林', '传闻', '听床师', '政府', '党', '领导人']
                is_sensitive = any(keyword in video_title.lower() or keyword in transcript_text[:500] 
                                 for keyword in sensitive_keywords)
                
                if is_sensitive:
                    self.logger.warning(f"🚨 检测到政治敏感内容，智能保护启动，跳过GitHub Pages发布: {video_title}")
                    self.logger.info("💡 建议: 如需发布此内容，请手动设置为Private模式")
                else:
                    try:
                        self.logger.info("发布YouTube内容到GitHub Pages")
                        self.publishing_workflow.deploy_to_github_pages()
                    except Exception as e:
                        self.logger.warning(f"GitHub Pages发布失败: {e}")
            
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
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """获取处理统计信息
        
        Returns:
            统计信息字典
        """
        stats = {
            'dependencies_status': {
                'transcription_service': self.transcription_service is not None,
                'anonymization_service': self.anonymization_service is not None,
                'ai_generation_service': self.ai_generation_service is not None,
                'transcript_storage': self.transcript_storage is not None,
                'result_storage': self.result_storage is not None,
                'file_monitor': self.file_monitor is not None
            }
        }
        
        # 添加存储统计信息
        if self.result_storage:
            try:
                storage_stats = self.result_storage.get_storage_stats()
                stats['storage_stats'] = storage_stats
            except Exception as e:
                stats['storage_stats'] = {'error': str(e)}
        
        # 添加队列统计信息
        if self.file_monitor:
            try:
                queue_stats = self.get_queue_status()
                stats['queue_stats'] = queue_stats
            except Exception as e:
                stats['queue_stats'] = {'error': str(e)}
        
        return stats
    
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
    
    def get_file_processing_history(self, filename: str) -> Dict[str, Any]:
        """获取文件的处理历史
        
        Args:
            filename: 文件名（不含扩展名）
            
        Returns:
            处理历史信息
        """
        history = {
            'filename': filename,
            'transcripts': {},
            'results': {},
            'status': 'not_found'
        }
        
        # 检查转录文件
        if self.transcript_storage:
            for suffix in ['raw', 'anonymized', 'processed']:
                transcript = self.transcript_storage.load_transcript(filename, suffix)
                if transcript:
                    history['transcripts'][suffix] = {
                        'exists': True,
                        'length': len(transcript)
                    }
        
        # 检查结果文件
        if self.result_storage:
            for format_type in ['json', 'markdown', 'html']:
                result = self.result_storage.load_result(filename, format_type)
                if result:
                    history['results'][format_type] = {
                        'exists': True,
                        'data': result
                    }
        
        # 确定状态
        if history['transcripts'] or history['results']:
            history['status'] = 'processed'
        
        return history