#!/usr/bin/env python3
"""
依赖注入容器单元测试

测试DependencyContainer的服务创建、管理和依赖注入功能
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
from pathlib import Path

# 添加项目根目录到路径
import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from src.core.dependency_container import DependencyContainer, ServiceFactory
from src.utils.config import ConfigManager


class TestDependencyContainer(unittest.TestCase):
    """测试依赖注入容器"""
    
    def setUp(self):
        """测试前设置"""
        # 创建临时配置文件
        self.temp_config_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        test_config = """
api:
  openrouter:
    key: "test-key"
    base_url: "https://test.com"
    models:
      summary: "test-model"
      mindmap: "test-model"

paths:
  watch_folder: "./data/uploads"
  data_folder: "./data"
  output_folder: "./data/output"

spacy:
  model: "zh_core_web_sm"

whisperkit:
  model_path: "./test_models"
  providers:
    local:
      enabled: true
      type: "whisperkit_local"
      path: "./test_models/whisperkit-coreml"

logging:
  level: "DEBUG"
  file: "./test.log"
  console: false
"""
        self.temp_config_file.write(test_config)
        self.temp_config_file.close()
        
        # 创建配置管理器和容器
        self.config_manager = ConfigManager(self.temp_config_file.name)
        self.container = DependencyContainer(self.config_manager)
    
    def tearDown(self):
        """测试后清理"""
        # 清理临时文件
        os.unlink(self.temp_config_file.name)
        if hasattr(self, 'container'):
            self.container.clear_cache()
    
    def test_container_initialization(self):
        """测试容器初始化"""
        self.assertIsNotNone(self.container.config_manager)
        self.assertIsNotNone(self.container.logger)
        self.assertIsInstance(self.container._services, dict)
        self.assertEqual(len(self.container._services), 0)  # 初始时服务缓存为空
    
    def test_get_config_manager(self):
        """测试获取配置管理器"""
        config_manager = self.container.get_config_manager()
        self.assertEqual(config_manager, self.config_manager)
    
    @patch('src.core.dependency_container.TranscriptionService')
    def test_get_transcription_service(self, mock_transcription_service):
        """测试获取转录服务实例"""
        mock_service = Mock()
        mock_transcription_service.return_value = mock_service
        
        # 第一次调用，创建新实例
        service1 = self.container.get_transcription_service()
        self.assertEqual(service1, mock_service)
        mock_transcription_service.assert_called_once()
        
        # 第二次调用，返回缓存的实例
        service2 = self.container.get_transcription_service()
        self.assertEqual(service2, mock_service)
        self.assertEqual(service1, service2)
        # 确保只调用了一次构造函数
        self.assertEqual(mock_transcription_service.call_count, 1)
    
    @patch('src.core.dependency_container.NameAnonymizer')
    def test_get_anonymization_service(self, mock_anonymizer):
        """测试获取匿名化服务实例"""
        mock_service = Mock()
        mock_anonymizer.return_value = mock_service
        
        service = self.container.get_anonymization_service()
        self.assertEqual(service, mock_service)
        mock_anonymizer.assert_called_once()
        
        # 验证服务已缓存
        self.assertIn('anonymization_service', self.container._services)
    
    @patch('src.core.dependency_container.AIContentGenerator')
    def test_get_ai_generation_service(self, mock_ai_generator):
        """测试获取AI生成服务实例"""
        mock_service = Mock()
        mock_ai_generator.return_value = mock_service
        
        service = self.container.get_ai_generation_service()
        self.assertEqual(service, mock_service)
        mock_ai_generator.assert_called_once()
        
        # 验证服务已缓存
        self.assertIn('ai_generation_service', self.container._services)
    
    @patch('src.core.dependency_container.TranscriptStorage')
    def test_get_transcript_storage(self, mock_transcript_storage):
        """测试获取转录存储服务实例"""
        mock_service = Mock()
        mock_transcript_storage.return_value = mock_service
        
        service = self.container.get_transcript_storage()
        self.assertEqual(service, mock_service)
        mock_transcript_storage.assert_called_with('./data')
    
    @patch('src.core.dependency_container.ResultStorage')
    def test_get_result_storage(self, mock_result_storage):
        """测试获取结果存储服务实例"""
        mock_service = Mock()
        mock_result_storage.return_value = mock_service
        
        service = self.container.get_result_storage()
        self.assertEqual(service, mock_service)
        mock_result_storage.assert_called_with('./data/output')
    
    @patch('src.core.dependency_container.AudioProcessor')
    def test_get_audio_processor(self, mock_audio_processor):
        """测试获取音频处理器实例"""
        mock_processor = Mock()
        mock_audio_processor.return_value = mock_processor
        
        # Mock所有依赖服务
        with patch.object(self.container, 'get_transcription_service') as mock_get_trans, \
             patch.object(self.container, 'get_anonymization_service') as mock_get_anon, \
             patch.object(self.container, 'get_ai_generation_service') as mock_get_ai, \
             patch.object(self.container, 'get_transcript_storage') as mock_get_trans_storage, \
             patch.object(self.container, 'get_result_storage') as mock_get_result_storage:
            
            mock_trans_service = Mock()
            mock_anon_service = Mock()
            mock_ai_service = Mock()
            mock_trans_storage = Mock()
            mock_result_storage = Mock()
            
            mock_get_trans.return_value = mock_trans_service
            mock_get_anon.return_value = mock_anon_service
            mock_get_ai.return_value = mock_ai_service
            mock_get_trans_storage.return_value = mock_trans_storage
            mock_get_result_storage.return_value = mock_result_storage
            
            processor = self.container.get_audio_processor()
            
            # 验证处理器创建
            self.assertEqual(processor, mock_processor)
            mock_audio_processor.assert_called_once_with(self.config_manager)
            
            # 验证依赖注入调用
            mock_processor.set_transcription_service.assert_called_once_with(mock_trans_service)
            mock_processor.set_anonymization_service.assert_called_once_with(mock_anon_service)
            mock_processor.set_ai_generation_service.assert_called_once_with(mock_ai_service)
            mock_processor.set_storage_services.assert_called_once_with(
                mock_trans_storage, mock_result_storage
            )
    
    @patch('src.core.dependency_container.FileMonitor')
    @patch('src.core.dependency_container.AudioProcessor')
    def test_get_file_monitor(self, mock_audio_processor, mock_file_monitor):
        """测试获取文件监控器实例"""
        mock_monitor = Mock()
        mock_processor = Mock()
        mock_file_monitor.return_value = mock_monitor
        mock_audio_processor.return_value = mock_processor
        
        with patch.object(self.container, 'get_audio_processor', return_value=mock_processor):
            monitor = self.container.get_file_monitor()
            
            self.assertEqual(monitor, mock_monitor)
            mock_file_monitor.assert_called_once_with(
                watch_folder='./data/uploads',
                file_processor_callback=mock_processor.process_audio_file
            )
    
    def test_service_status(self):
        """测试获取服务状态信息"""
        # 初始状态
        status = self.container.get_service_status()
        self.assertEqual(status, {})
        
        # 创建一个服务后
        with patch('src.core.dependency_container.TranscriptionService') as mock_service:
            mock_instance = Mock()
            mock_service.return_value = mock_instance
            
            self.container.get_transcription_service()
            status = self.container.get_service_status()
            
            self.assertIn('transcription_service', status)
            self.assertTrue(status['transcription_service']['created'])
            self.assertIn('type', status['transcription_service'])
            self.assertIn('module', status['transcription_service'])
    
    def test_clear_cache(self):
        """测试清除服务缓存"""
        # 创建一些服务
        with patch('src.core.dependency_container.TranscriptionService'), \
             patch('src.core.dependency_container.NameAnonymizer'):
            
            self.container.get_transcription_service()
            self.container.get_anonymization_service()
            
            # 验证服务已缓存
            self.assertEqual(len(self.container._services), 2)
            
            # 清除缓存
            self.container.clear_cache()
            
            # 验证缓存已清空
            self.assertEqual(len(self.container._services), 0)
    
    def test_validate_dependencies_success(self):
        """测试依赖验证成功情况"""
        with patch.object(self.container, 'get_transcription_service'), \
             patch.object(self.container, 'get_anonymization_service'), \
             patch.object(self.container, 'get_ai_generation_service'), \
             patch.object(self.container, 'get_transcript_storage'), \
             patch.object(self.container, 'get_result_storage'), \
             patch.object(self.container, 'get_audio_processor'):
            
            result = self.container.validate_dependencies()
            
            # 验证所有依赖都通过验证
            expected_services = [
                'transcription_service', 'anonymization_service', 'ai_generation_service',
                'transcript_storage', 'result_storage', 'audio_processor'
            ]
            
            for service in expected_services:
                self.assertIn(service, result)
                self.assertTrue(result[service])
    
    def test_validate_dependencies_failure(self):
        """测试依赖验证失败情况"""
        # 模拟转录服务创建失败
        with patch.object(self.container, 'get_transcription_service', 
                          side_effect=Exception("Service creation failed")), \
             patch.object(self.container, 'get_anonymization_service'), \
             patch.object(self.container, 'get_ai_generation_service'), \
             patch.object(self.container, 'get_transcript_storage'), \
             patch.object(self.container, 'get_result_storage'), \
             patch.object(self.container, 'get_audio_processor'):
            
            result = self.container.validate_dependencies()
            
            # 验证转录服务验证失败，其他成功
            self.assertFalse(result['transcription_service'])
            self.assertTrue(result['anonymization_service'])


class TestServiceFactory(unittest.TestCase):
    """测试服务工厂类"""
    
    def test_create_container_from_config_file(self):
        """测试从配置文件创建依赖容器"""
        # 创建临时配置文件
        temp_config_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        test_config = """
api:
  openrouter:
    key: "test-key"
    base_url: "https://test.com"

paths:
  watch_folder: "./test_watch"
  data_folder: "./test_data"
  output_folder: "./test_output"
"""
        temp_config_file.write(test_config)
        temp_config_file.close()
        
        try:
            container = ServiceFactory.create_container_from_config_file(temp_config_file.name)
            self.assertIsInstance(container, DependencyContainer)
            self.assertIsNotNone(container.config_manager)
            
        finally:
            os.unlink(temp_config_file.name)
    
    def test_create_test_container(self):
        """测试创建测试用依赖容器"""
        container = ServiceFactory.create_test_container()
        
        self.assertIsInstance(container, DependencyContainer)
        self.assertIsNotNone(container.config_manager)
        
        # 验证测试配置
        config = container.config_manager.get_full_config()
        self.assertIn('api', config)
        self.assertIn('paths', config)
        self.assertIn('spacy', config)
        self.assertIn('whisperkit', config)
    
    def test_create_test_container_with_overrides(self):
        """测试使用配置覆盖创建测试容器"""
        overrides = {
            'api': {
                'openrouter': {
                    'key': 'custom-test-key'
                }
            }
        }
        
        container = ServiceFactory.create_test_container(overrides)
        config = container.config_manager.get_full_config()
        
        # 验证基本配置存在
        self.assertIsInstance(container, DependencyContainer)
        self.assertIn('api', config)
        self.assertIn('paths', config)


if __name__ == '__main__':
    unittest.main()