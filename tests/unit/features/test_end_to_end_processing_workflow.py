#!/usr/bin/env python3
"""
端到端处理流程测试

测试完整的音频处理工作流：
1. Web界面文件上传
2. WhisperKit转录（包括模型路径修复）
3. 实时状态跟踪
4. GitHub Pages自动部署
5. 处理完成通知
"""

import unittest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestEndToEndAudioProcessingWorkflow(unittest.TestCase):
    """测试端到端音频处理工作流"""
    
    def setUp(self):
        """设置测试环境"""
        from src.web_frontend.app import create_app
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # 创建临时目录和测试音频文件
        self.test_dir = tempfile.mkdtemp()
        self.test_audio = Path(self.test_dir) / 'test_audio.mp4'
        self.test_audio.write_bytes(b'fake audio data for testing')
        
    def tearDown(self):
        """清理测试环境"""
        self.app_context.pop()
        shutil.rmtree(self.test_dir, ignore_errors=True)
        
    @patch('ipaddress.ip_address')
    @patch('ipaddress.ip_network')
    @patch('src.web_frontend.processors.audio_upload_processor.AudioUploadProcessor')
    def test_complete_audio_upload_workflow(self, mock_processor_class, mock_ip_network, mock_ip_address):
        """测试完整的音频上传处理流程"""
        # Mock Tailscale网络检查通过
        mock_network = Mock()
        mock_ip = Mock()
        mock_ip_network.return_value = mock_network
        mock_ip_address.return_value = mock_ip
        mock_network.__contains__ = Mock(return_value=True)
        
        # Mock音频处理器返回成功
        mock_processor = MagicMock()
        mock_processor.process_audio_file.return_value = True
        mock_processor_class.return_value = mock_processor
        
        # 模拟文件上传
        with open(self.test_audio, 'rb') as f:
            response = self.client.post('/upload/audio', 
                data={
                    'audio_file': (f, 'test_feynman_lecture.mp4'),
                    'content_type': 'lecture',
                    'privacy_level': 'public',
                    'context': 'Physics lecture by Richard Feynman about diffusion',
                    'language_preference': 'english',
                    'model_selection': 'large-v3|distil'
                },
                content_type='multipart/form-data'
            )
        
        # 验证上传成功并重定向到状态页面
        self.assertEqual(response.status_code, 302)
        self.assertIn('/status/', response.location)
        
        # 验证音频处理器被正确调用
        mock_processor.process_audio_file.assert_called_once()
        call_args = mock_processor.process_audio_file.call_args
        
        # 验证传递了正确的参数
        self.assertIn('privacy_level', call_args.kwargs)
        self.assertIn('metadata', call_args.kwargs)
        self.assertEqual(call_args.kwargs['privacy_level'], 'public')
        
        # 验证元数据包含了自定义提示词
        metadata = call_args.kwargs['metadata']
        self.assertEqual(metadata['content_type'], 'lecture')
        self.assertIn('Physics lecture by Richard Feynman', metadata.get('context', ''))


class TestWhisperKitIntegrationInWorkflow(unittest.TestCase):
    """测试WhisperKit在完整工作流中的集成"""
    
    @patch('src.core.transcription.WhisperKitClient')
    @patch('pathlib.Path.exists')
    def test_whisperkit_model_path_resolution_in_workflow(self, mock_path_exists, mock_whisperkit_class):
        """测试工作流中WhisperKit模型路径解析"""
        # Mock模型路径存在
        mock_path_exists.return_value = True
        
        # Mock WhisperKit客户端
        mock_client = MagicMock()
        mock_client.transcribe.return_value = "Well, I mean, May 1st, 1962, Lecture 43..."
        mock_whisperkit_class.return_value = mock_client
        
        # 创建转录服务并测试
        from src.core.transcription import TranscriptionService
        
        config = {
            'model_path': './models',
            'model': 'large-v3',
            'language': 'en'
        }
        
        service = TranscriptionService(config)
        
        # 测试使用distil模型前缀的转录
        test_audio_path = Path('/test/feynman_lecture.mp4')
        result = service.transcribe_audio(
            test_audio_path, 
            custom_model='large-v3',
            custom_model_prefix='distil',
            prompt='Physics lecture by Richard Feynman about diffusion'
        )
        
        # 验证调用了WhisperKit
        mock_client.transcribe.assert_called_once()
        call_args = mock_client.transcribe.call_args
        
        # 验证传递了正确的参数
        self.assertEqual(call_args.kwargs['model'], 'large-v3')
        self.assertEqual(call_args.kwargs['model_prefix'], 'distil')
        self.assertIn('Physics lecture', call_args.kwargs.get('prompt', ''))
        
        # 验证返回了正确的转录结果
        self.assertIn('Lecture 43', result)


class TestRealTimeStatusTracking(unittest.TestCase):
    """测试实时状态跟踪"""
    
    def setUp(self):
        """设置测试环境"""
        from src.web_frontend.app import create_app
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
    def tearDown(self):
        """清理测试环境"""
        self.app_context.pop()
    
    @patch('ipaddress.ip_address')
    @patch('ipaddress.ip_network')
    @patch('src.web_frontend.services.processing_service.get_processing_service')
    def test_processing_status_stages(self, mock_get_service, mock_ip_network, mock_ip_address):
        """测试处理状态各个阶段的跟踪"""
        # Mock Tailscale网络检查通过
        mock_network = Mock()
        mock_ip = Mock()
        mock_ip_network.return_value = mock_network
        mock_ip_address.return_value = mock_ip
        mock_network.__contains__ = Mock(return_value=True)
        
        # Mock处理服务
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        
        # Mock不同阶段的状态
        status_stages = [
            {'stage': 'UPLOADED', 'progress': 10, 'message': 'File uploaded successfully'},
            {'stage': 'TRANSCRIBING', 'progress': 20, 'message': 'Transcribing audio...'},
            {'stage': 'ANONYMIZING', 'progress': 40, 'message': 'Anonymizing personal names...'},
            {'stage': 'AI_GENERATING', 'progress': 60, 'message': 'Generating AI content...'},
            {'stage': 'PUBLISHING', 'progress': 90, 'message': 'Deploying to GitHub Pages...'},
            {'stage': 'COMPLETED', 'progress': 100, 'message': 'Processing completed!'}
        ]
        
        processing_id = 'test-processing-id-123'
        
        for stage_info in status_stages:
            mock_service.get_status.return_value = {
                'id': processing_id,
                'stage': stage_info['stage'],
                'progress': stage_info['progress'],
                'message': stage_info['message'],
                'content_type': 'audio',
                'privacy_level': 'public',
                'created_at': '2025-08-24T03:22:12',
                'updated_at': '2025-08-24T03:22:30',
                'logs': [
                    {'timestamp': '2025-08-24T03:22:12', 'level': 'uploaded', 'message': 'File uploaded'},
                    {'timestamp': '2025-08-24T03:22:14', 'level': stage_info['stage'].lower(), 'message': stage_info['message']}
                ]
            }
            
            # 测试状态API
            response = self.client.get(f'/api/status/{processing_id}')
            self.assertEqual(response.status_code, 200)
            
            data = json.loads(response.data)
            self.assertEqual(data['stage'], stage_info['stage'])
            self.assertEqual(data['progress'], stage_info['progress'])
            self.assertIn(stage_info['message'], data['message'])


class TestGitHubPagesDeploymentInWorkflow(unittest.TestCase):
    """测试GitHub Pages部署在工作流中的集成"""
    
    @patch('src.publishing.publishing_workflow.PublishingWorkflow')
    def test_github_pages_deployment_success(self, mock_workflow_class):
        """测试GitHub Pages部署成功流程"""
        # Mock发布工作流
        mock_workflow = MagicMock()
        mock_workflow.publish_results.return_value = {
            'success': True,
            'website_url': 'https://sleepycat233.github.io/Project_Bach',
            'result_url': 'https://sleepycat233.github.io/Project_Bach/test_result.html'
        }
        mock_workflow_class.return_value = mock_workflow
        
        # 导入并测试音频处理器的部署功能
        from src.core.audio_processor import AudioProcessor
        from src.utils.config import ConfigManager
        
        config = ConfigManager()
        processor = AudioProcessor(config)
        
        # Mock其他依赖
        with patch('src.core.transcription.TranscriptionService') as mock_transcription, \
             patch('src.core.anonymization.NameAnonymizer') as mock_anonymization, \
             patch('src.core.ai_generation.AIContentGenerator') as mock_ai_gen, \
             patch('src.storage.result_storage.ResultStorage') as mock_storage:
            
            # 设置mock返回值
            mock_transcription.return_value.transcribe_audio.return_value = "Test transcription"
            mock_anonymization.return_value.anonymize_names.return_value = ("Test transcription", {})
            mock_ai_gen.return_value.generate_content.return_value = {
                'summary': 'Test summary',
                'mind_map': 'Test mind map'
            }
            mock_storage.return_value.save_results.return_value = '/test/result.md'
            
            # 执行处理
            success = processor.process_audio_file(
                '/test/audio.mp4',
                privacy_level='public',
                metadata={'content_type': 'lecture'}
            )
            
            # 验证处理成功
            self.assertTrue(success)
            
            # 验证发布工作流被调用
            mock_workflow.publish_results.assert_called_once()


class TestProcessingServiceIntegration(unittest.TestCase):
    """测试ProcessingService集成"""
    
    def test_processing_service_status_updates(self):
        """测试ProcessingService状态更新"""
        from src.web_frontend.services.processing_service import ProcessingService, ProcessingStage
        
        service = ProcessingService()
        processing_id = service.create_processing('audio', 'public')
        
        # 测试各个阶段的状态更新
        test_stages = [
            (ProcessingStage.TRANSCRIBING, 20, "Transcribing audio..."),
            (ProcessingStage.ANONYMIZING, 40, "Anonymizing personal names..."), 
            (ProcessingStage.AI_GENERATING, 60, "Generating AI content..."),
            (ProcessingStage.PUBLISHING, 90, "Deploying to GitHub Pages..."),
            (ProcessingStage.COMPLETED, 100, "Processing completed!")
        ]
        
        for stage, progress, message in test_stages:
            service.update_status(processing_id, stage, progress, message)
            status = service.get_status(processing_id)
            
            self.assertEqual(status['stage'], stage.value)
            self.assertEqual(status['progress'], progress)
            self.assertEqual(status['message'], message)
        
        # 测试完成处理
        service.complete_processing(processing_id, "https://example.com/result.html")
        final_status = service.get_status(processing_id)
        
        self.assertEqual(final_status['stage'], ProcessingStage.COMPLETED.value)
        self.assertEqual(final_status['progress'], 100)
        self.assertIn('example.com', final_status.get('result_url', ''))


if __name__ == '__main__':
    unittest.main()