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
    
    def process_audio_file(self, audio_path: str) -> bool:
        """处理单个音频文件的完整流程
        
        Args:
            audio_path: 音频文件路径
            
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
            # 步骤1: 音频转录
            self.logger.info("步骤1: 开始音频转录")
            transcript = self.transcription_service.transcribe_audio(audio_path)
            if not transcript:
                raise Exception("转录失败或结果为空")
            
            # 保存原始转录
            self.transcript_storage.save_raw_transcript(audio_path.stem, transcript)
            
            # 步骤2: 人名匿名化
            self.logger.info("步骤2: 开始人名匿名化")
            anonymized_text, mapping = self.anonymization_service.anonymize_names(transcript)
            self.transcript_storage.save_anonymized_transcript(audio_path.stem, anonymized_text)
            
            # 记录匿名化映射
            if mapping:
                self.logger.info(f"人名匿名化映射: {mapping}")
            
            # 步骤3: AI内容生成
            self.logger.info("步骤3: 开始AI内容生成")
            summary = self.ai_generation_service.generate_summary(anonymized_text)
            mindmap = self.ai_generation_service.generate_mindmap(anonymized_text)
            
            # 步骤4: 保存结果
            self.logger.info("步骤4: 保存处理结果")
            results = {
                'summary': summary,
                'mindmap': mindmap,
                'original_file': str(audio_path),
                'processed_time': datetime.now().isoformat(),
                'anonymization_mapping': mapping
            }
            
            # 保存多种格式的结果
            self.result_storage.save_markdown_result(audio_path.stem, results)
            self.result_storage.save_json_result(audio_path.stem, results)
            
            # 步骤5: 自动部署到GitHub Pages (如果配置了)
            if self.publishing_workflow and self._should_auto_deploy():
                self.logger.info("步骤5: 开始自动部署到GitHub Pages")
                try:
                    deploy_result = self.publishing_workflow.deploy_to_github_pages()
                    if deploy_result.get('success'):
                        self.logger.info("✅ 自动部署成功!")
                        if 'website_url' in deploy_result:
                            self.logger.info(f"🔗 网站地址: {deploy_result['website_url']}")
                    else:
                        self.logger.warning(f"⚠️  自动部署失败: {deploy_result.get('error', '未知错误')}")
                except Exception as e:
                    self.logger.error(f"❌ 自动部署异常: {e}")
            
            elapsed = time.time() - start_time
            self.logger.info(f"处理完成: {audio_path.name} (耗时: {elapsed:.2f}秒)")
            return True
            
        except Exception as e:
            self.logger.error(f"处理失败: {audio_path.name} - {str(e)}")
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