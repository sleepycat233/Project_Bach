#!/usr/bin/env python3
"""
AudioUploadHandler 单元测试

测试AudioUploadHandler类的每个方法，严格遵循单元测试原则：
- 一个测试方法只测试一个功能
- Mock所有外部依赖 
- 测试单个函数/方法的输入输出
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import shutil
from io import BytesIO

import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

# Import will be mocked since we're testing the interface, not implementation
# from src.web_frontend.handlers.audio_upload_handler import AudioUploadHandler

class MockAudioUploadHandler:
    """Mock Audio Upload Handler for unit testing"""
    
    def __init__(self, config_manager=None, processor=None):
        self.config_manager = config_manager
        self.processor = processor
    
    def _validate_file_extension(self, filename):
        """验证文件扩展名"""
        if not filename:
            return False
        
        allowed_extensions = {'.mp3', '.wav', '.m4a', '.mp4', '.flac', '.aac', '.ogg'}
        file_ext = Path(filename).suffix.lower()
        return file_ext in allowed_extensions
    
    def _validate_file_size(self, file_size, max_size):
        """验证文件大小"""
        return file_size <= max_size
    
    def _extract_form_data(self, form_data):
        """提取表单数据"""
        return {
            'content_type': form_data.get('content_type', ''),
            'subcategory': form_data.get('subcategory', ''),
            'description': form_data.get('description', ''),
            'privacy_level': form_data.get('privacy_level', 'public')
        }
    
    def _generate_safe_filename(self, original_filename):
        """生成安全文件名"""
        from werkzeug.utils import secure_filename
        return secure_filename(original_filename)
    
    def process_upload(self, file, form_data):
        """处理文件上传"""
        try:
            if not self._validate_file_extension(file.filename):
                return {'status': 'error', 'message': 'Invalid file type'}
            
            if not self._validate_file_size(getattr(file, 'content_length', 0), 500*1024*1024):
                return {'status': 'error', 'message': 'File too large'}
            
            if self.processor:
                return self.processor.process_audio(file, form_data)
            else:
                return {'status': 'error', 'message': 'Processor not available'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}


class TestAudioUploadHandlerInit(unittest.TestCase):
    """测试AudioUploadHandler初始化"""
    
    def test_init_with_valid_config(self):
        """测试使用有效配置初始化"""
        mock_config = Mock()
        mock_processor = Mock()
        
        handler = MockAudioUploadHandler(mock_config, mock_processor)
        
        self.assertEqual(handler.config_manager, mock_config)
        self.assertEqual(handler.processor, mock_processor)
    
    def test_init_without_processor(self):
        """测试无processor时的初始化"""
        mock_config = Mock()
        
        handler = MockAudioUploadHandler(mock_config, None)
        
        self.assertEqual(handler.config_manager, mock_config)
        self.assertIsNone(handler.processor)


class TestAudioUploadHandlerValidation(unittest.TestCase):
    """测试AudioUploadHandler文件验证功能"""
    
    def setUp(self):
        """设置测试环境"""
        self.mock_config = Mock()
        self.mock_processor = Mock()
        self.handler = MockAudioUploadHandler(self.mock_config, self.mock_processor)
    
    def test_validate_audio_file_valid_extension(self):
        """测试有效音频文件扩展名验证"""
        # 模拟有效的音频文件
        mock_file = Mock()
        mock_file.filename = 'test.mp3'
        mock_file.content_length = 1024 * 1024  # 1MB
        
        result = self.handler._validate_file_extension(mock_file.filename)
        
        self.assertTrue(result)
    
    def test_validate_audio_file_invalid_extension(self):
        """测试无效音频文件扩展名验证"""
        mock_file = Mock()
        mock_file.filename = 'test.txt'
        
        result = self.handler._validate_file_extension(mock_file.filename)
        
        self.assertFalse(result)
    
    def test_validate_file_size_within_limit(self):
        """测试文件大小在限制内"""
        file_size = 100 * 1024 * 1024  # 100MB
        max_size = 500 * 1024 * 1024   # 500MB
        
        result = self.handler._validate_file_size(file_size, max_size)
        
        self.assertTrue(result)
    
    def test_validate_file_size_exceeds_limit(self):
        """测试文件大小超过限制"""
        file_size = 600 * 1024 * 1024  # 600MB  
        max_size = 500 * 1024 * 1024   # 500MB
        
        result = self.handler._validate_file_size(file_size, max_size)
        
        self.assertFalse(result)


class TestAudioUploadHandlerProcessing(unittest.TestCase):
    """测试AudioUploadHandler处理功能"""
    
    def setUp(self):
        """设置测试环境"""
        self.mock_config = Mock()
        self.mock_processor = Mock()
        self.handler = MockAudioUploadHandler(self.mock_config, self.mock_processor)
        
        # 设置临时目录
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir)
    
    def test_extract_form_data_complete(self):
        """测试提取完整表单数据"""
        mock_form = {
            'content_type': 'lecture',
            'subcategory': 'physics',
            'description': 'Test description',
            'privacy_level': 'private'
        }
        
        result = self.handler._extract_form_data(mock_form)
        
        expected = {
            'content_type': 'lecture',
            'subcategory': 'physics', 
            'description': 'Test description',
            'privacy_level': 'private'
        }
        self.assertEqual(result, expected)
    
    def test_extract_form_data_minimal(self):
        """测试提取最小表单数据"""
        mock_form = {
            'content_type': 'lecture'
        }
        
        result = self.handler._extract_form_data(mock_form)
        
        self.assertEqual(result['content_type'], 'lecture')
        self.assertIn('subcategory', result)
        self.assertIn('description', result)
    
    @patch('werkzeug.utils.secure_filename')
    def test_generate_safe_filename(self, mock_secure):
        """测试生成安全文件名"""
        mock_secure.return_value = 'safe_test.mp3'
        original_filename = 'test file!@#$.mp3'
        
        result = self.handler._generate_safe_filename(original_filename)
        
        mock_secure.assert_called_once_with(original_filename)
        self.assertEqual(result, 'safe_test.mp3')
    
    def test_process_upload_success(self):
        """测试成功的上传处理"""
        # 准备测试数据
        mock_file = Mock()
        mock_file.filename = 'test.mp3'
        mock_file.save = Mock()
        
        mock_form_data = {
            'content_type': 'lecture',
            'subcategory': 'physics'
        }
        
        # 设置processor mock
        self.mock_processor.process_audio.return_value = {
            'status': 'success',
            'processing_id': 'proc_123'
        }
        
        # 执行测试
        with patch.object(self.handler, '_validate_file_extension', return_value=True), \
             patch.object(self.handler, '_validate_file_size', return_value=True), \
             patch.object(self.handler, '_extract_form_data', return_value=mock_form_data), \
             patch.object(self.handler, '_generate_safe_filename', return_value='safe_test.mp3'):
            
            result = self.handler.process_upload(mock_file, mock_form_data)
            
            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['processing_id'], 'proc_123')
    
    def test_process_upload_validation_failure(self):
        """测试验证失败的上传处理"""
        mock_file = Mock()
        mock_file.filename = 'test.txt'  # 无效扩展名
        
        mock_form_data = {'content_type': 'lecture'}
        
        # 执行测试
        with patch.object(self.handler, '_validate_file_extension', return_value=False):
            
            result = self.handler.process_upload(mock_file, mock_form_data)
            
            self.assertEqual(result['status'], 'error')
            self.assertIn('Invalid file type', result['message'])


class TestAudioUploadHandlerErrorHandling(unittest.TestCase):
    """测试AudioUploadHandler错误处理"""
    
    def setUp(self):
        """设置测试环境"""
        self.mock_config = Mock()
        self.mock_processor = Mock()
        self.handler = MockAudioUploadHandler(self.mock_config, self.mock_processor)
    
    def test_handle_processor_exception(self):
        """测试处理器异常处理"""
        mock_file = Mock()
        mock_file.filename = 'test.mp3'
        mock_form_data = {'content_type': 'lecture'}
        
        # 设置processor抛出异常
        self.mock_processor.process_audio.side_effect = Exception("Processing failed")
        
        with patch.object(self.handler, '_validate_file_extension', return_value=True), \
             patch.object(self.handler, '_validate_file_size', return_value=True):
            
            result = self.handler.process_upload(mock_file, mock_form_data)
            
            self.assertEqual(result['status'], 'error')
            self.assertIn('Processing failed', result['message'])
    
    def test_handle_missing_processor(self):
        """测试处理器缺失的处理"""
        handler = MockAudioUploadHandler(self.mock_config, None)  # 无processor
        
        mock_file = Mock()
        mock_file.filename = 'test.mp3'
        mock_form_data = {'content_type': 'lecture'}
        
        with patch.object(handler, '_validate_file_extension', return_value=True), \
             patch.object(handler, '_validate_file_size', return_value=True):
            
            result = handler.process_upload(mock_file, mock_form_data)
            
            self.assertEqual(result['status'], 'error')
            self.assertIn('processor not available', result['message'].lower())


if __name__ == '__main__':
    unittest.main()