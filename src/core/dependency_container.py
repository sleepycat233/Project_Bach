#!/usr/bin/env python3.11
"""
依赖注入容器
负责创建和管理所有服务组件的依赖关系
"""

import logging
from typing import Dict, Any, Optional

from ..utils.config import ConfigManager, LoggingSetup, DirectoryManager
from .transcription import TranscriptionService
from .anonymization import NameAnonymizer
from .ai_generation import AIContentGenerator
from .audio_processor import AudioProcessor
from ..storage.transcript_storage import TranscriptStorage
from ..storage.result_storage import ResultStorage
from ..monitoring.file_monitor import FileMonitor
from ..publishing.git_publisher import GitPublisher


class DependencyContainer:
    """依赖注入容器"""
    
    def __init__(self, config_manager: ConfigManager):
        """初始化依赖容器
        
        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager
        self.logger = self._setup_logging()
        
        # 单例服务缓存
        self._services = {}
        
        # 设置目录结构
        self._setup_directories()
        
    def _setup_logging(self) -> logging.Logger:
        """设置日志系统
        
        Returns:
            配置好的logger实例
        """
        logging_config = self.config_manager.get_logging_config()
        return LoggingSetup.setup_logging(logging_config)
    
    def _setup_directories(self):
        """设置目录结构"""
        paths_config = self.config_manager.get_paths_config()
        DirectoryManager.setup_directories(paths_config)
    
    def get_transcription_service(self) -> TranscriptionService:
        """获取转录服务实例
        
        Returns:
            转录服务实例
        """
        if 'transcription_service' not in self._services:
            whisperkit_config = self.config_manager.get_whisperkit_config()
            self._services['transcription_service'] = TranscriptionService(whisperkit_config)
            self.logger.debug("创建转录服务实例")
        
        return self._services['transcription_service']
    
    def get_anonymization_service(self) -> NameAnonymizer:
        """获取匿名化服务实例
        
        Returns:
            匿名化服务实例
        """
        if 'anonymization_service' not in self._services:
            spacy_config = self.config_manager.get_spacy_config()
            self._services['anonymization_service'] = NameAnonymizer(spacy_config)
            self.logger.debug("创建匿名化服务实例")
        
        return self._services['anonymization_service']
    
    def get_ai_generation_service(self) -> AIContentGenerator:
        """获取AI生成服务实例
        
        Returns:
            AI生成服务实例
        """
        if 'ai_generation_service' not in self._services:
            api_config = self.config_manager.get_api_config()
            self._services['ai_generation_service'] = AIContentGenerator(api_config)
            self.logger.debug("创建AI生成服务实例")
        
        return self._services['ai_generation_service']
    
    def get_transcript_storage(self) -> TranscriptStorage:
        """获取转录存储服务实例
        
        Returns:
            转录存储服务实例
        """
        if 'transcript_storage' not in self._services:
            paths_config = self.config_manager.get_paths_config()
            data_folder = paths_config.get('data_folder', './data')
            self._services['transcript_storage'] = TranscriptStorage(data_folder)
            self.logger.debug("创建转录存储服务实例")
        
        return self._services['transcript_storage']
    
    def get_result_storage(self) -> ResultStorage:
        """获取结果存储服务实例
        
        Returns:
            结果存储服务实例
        """
        if 'result_storage' not in self._services:
            paths_config = self.config_manager.get_paths_config()
            output_folder = paths_config.get('output_folder', './data/output')
            self._services['result_storage'] = ResultStorage(output_folder)
            self.logger.debug("创建结果存储服务实例")
        
        return self._services['result_storage']
    
    def get_file_monitor(self) -> FileMonitor:
        """获取文件监控器实例
        
        Returns:
            文件监控器实例
        """
        if 'file_monitor' not in self._services:
            paths_config = self.config_manager.get_paths_config()
            watch_folder = paths_config.get('watch_folder', './watch_folder')
            
            # 获取音频处理器实例
            audio_processor = self.get_audio_processor()
            
            # 创建文件监控器，传入处理回调
            self._services['file_monitor'] = FileMonitor(
                watch_folder=watch_folder,
                file_processor_callback=audio_processor.process_audio_file
            )
            self.logger.debug("创建文件监控器实例")
        
        return self._services['file_monitor']
    
    
    def get_audio_processor(self) -> AudioProcessor:
        """获取音频处理器实例（完全装配的）
        
        Returns:
            音频处理器实例
        """
        if 'audio_processor' not in self._services:
            # 创建音频处理器
            processor = AudioProcessor(self.config_manager)
            
            # 注入所有依赖
            processor.set_transcription_service(self.get_transcription_service())
            processor.set_anonymization_service(self.get_anonymization_service())
            processor.set_ai_generation_service(self.get_ai_generation_service())
            processor.set_storage_services(
                self.get_transcript_storage(),
                self.get_result_storage()
            )
            
            self._services['audio_processor'] = processor
            self.logger.debug("创建并装配音频处理器实例")
        
        return self._services['audio_processor']
    
    def get_configured_audio_processor(self) -> AudioProcessor:
        """获取完全配置的音频处理器（包含文件监控器）
        
        Returns:
            完全配置的音频处理器实例
        """
        processor = self.get_audio_processor()
        
        # 设置文件监控器
        if 'file_monitor' not in self._services:
            # 需要特殊处理，避免循环依赖
            paths_config = self.config_manager.get_paths_config()
            watch_folder = paths_config.get('watch_folder', './watch_folder')
            
            file_monitor = FileMonitor(
                watch_folder=watch_folder,
                file_processor_callback=processor.process_audio_file
            )
            self._services['file_monitor'] = file_monitor
        
        processor.set_file_monitor(self._services['file_monitor'])
        
        # 设置Git发布服务
        processor.set_git_publisher(self.get_git_publisher())
        
        return processor
    
    def validate_dependencies(self) -> Dict[str, bool]:
        """验证所有依赖是否可以正常创建
        
        Returns:
            依赖验证结果
        """
        validation_results = {}
        
        try:
            self.get_transcription_service()
            validation_results['transcription_service'] = True
        except Exception as e:
            validation_results['transcription_service'] = False
            self.logger.error(f"转录服务验证失败: {str(e)}")
        
        try:
            self.get_anonymization_service()
            validation_results['anonymization_service'] = True
        except Exception as e:
            validation_results['anonymization_service'] = False
            self.logger.error(f"匿名化服务验证失败: {str(e)}")
        
        try:
            self.get_ai_generation_service()
            validation_results['ai_generation_service'] = True
        except Exception as e:
            validation_results['ai_generation_service'] = False
            self.logger.error(f"AI生成服务验证失败: {str(e)}")
        
        try:
            self.get_transcript_storage()
            validation_results['transcript_storage'] = True
        except Exception as e:
            validation_results['transcript_storage'] = False
            self.logger.error(f"转录存储服务验证失败: {str(e)}")
        
        try:
            self.get_result_storage()
            validation_results['result_storage'] = True
        except Exception as e:
            validation_results['result_storage'] = False
            self.logger.error(f"结果存储服务验证失败: {str(e)}")
        
        try:
            self.get_audio_processor()
            validation_results['audio_processor'] = True
        except Exception as e:
            validation_results['audio_processor'] = False
            self.logger.error(f"音频处理器验证失败: {str(e)}")
        
        return validation_results
    
    def get_service_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有服务的状态信息
        
        Returns:
            服务状态信息
        """
        status = {}
        
        for service_name in self._services:
            service = self._services[service_name]
            status[service_name] = {
                'created': True,
                'type': type(service).__name__,
                'module': type(service).__module__
            }
        
        return status
    
    def get_git_publisher(self) -> GitPublisher:
        """获取Git发布服务实例
        
        Returns:
            Git发布服务实例
        """
        if 'git_publisher' not in self._services:
            self._services['git_publisher'] = GitPublisher(self.config_manager)
            self.logger.debug("创建Git发布服务实例")
        
        return self._services['git_publisher']
    
    def clear_cache(self):
        """清除服务缓存（用于测试或重置）"""
        old_count = len(self._services)
        self._services.clear()
        self.logger.info(f"清除了 {old_count} 个缓存的服务实例")
    
    def get_config_manager(self) -> ConfigManager:
        """获取配置管理器
        
        Returns:
            配置管理器实例
        """
        return self.config_manager


class ServiceFactory:
    """服务工厂类（可选的高级功能）"""
    
    @staticmethod
    def create_container_from_config_file(config_path: str) -> DependencyContainer:
        """从配置文件创建依赖容器
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            依赖容器实例
        """
        config_manager = ConfigManager(config_path)
        return DependencyContainer(config_manager)
    
    @staticmethod
    def create_test_container(config_overrides: Dict[str, Any] = None) -> DependencyContainer:
        """创建测试用的依赖容器
        
        Args:
            config_overrides: 配置覆盖
            
        Returns:
            测试用依赖容器
        """
        import tempfile
        import yaml
        
        # 创建测试配置
        test_config = {
            'api': {
                'openrouter': {
                    'key': 'test-key',
                    'base_url': 'https://openrouter.ai/api/v1',
                    'models': {
                        'summary': 'test-model',
                        'mindmap': 'test-model'
                    }
                }
            },
            'paths': {
                'watch_folder': tempfile.mkdtemp(),
                'data_folder': tempfile.mkdtemp(),
                'output_folder': tempfile.mkdtemp()
            },
            'spacy': {
                'model': 'zh_core_web_sm'
            },
            'whisperkit': {
                'model': 'medium',
                'language': 'en',
                'supported_languages': ['en', 'zh']
            },
            'logging': {
                'level': 'DEBUG',
                'file': tempfile.mktemp(suffix='.log')
            }
        }
        
        # 应用覆盖配置
        if config_overrides:
            test_config.update(config_overrides)
        
        # 创建临时配置文件
        config_file = tempfile.mktemp(suffix='.yaml')
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(test_config, f)
        
        return ServiceFactory.create_container_from_config_file(config_file)


# 全局容器实例（可选）
_global_container: Optional[DependencyContainer] = None


def get_global_container() -> Optional[DependencyContainer]:
    """获取全局依赖容器实例
    
    Returns:
        全局容器实例或None
    """
    return _global_container


def set_global_container(container: DependencyContainer):
    """设置全局依赖容器实例
    
    Args:
        container: 依赖容器实例
    """
    global _global_container
    _global_container = container


def clear_global_container():
    """清除全局依赖容器"""
    global _global_container
    _global_container = None