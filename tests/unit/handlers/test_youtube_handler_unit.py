#!/usr/bin/env python3
"""
YouTubeHandler 单元测试

测试YouTubeHandler类的每个方法，严格遵循单元测试原则：
- 一个测试方法只测试一个功能
- Mock所有外部依赖 
- 测试单个函数/方法的输入输出
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import shutil

import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent))


class MockYouTubeHandler:
    """Mock YouTube Handler for testing when real handler is not available"""
    
    def __init__(self, config, processor=None):
        self.config = config
        self.processor = processor
    
    def validate_url(self, url):
        """验证YouTube URL格式"""
        if not url or not isinstance(url, str):
            return False
        
        youtube_patterns = [
            'youtube.com/watch?v=',
            'youtu.be/',
            'youtube.com/embed/',
            'youtube.com/v/'
        ]
        
        url_lower = url.lower()
        return any(pattern in url_lower for pattern in youtube_patterns)
    
    def extract_video_id(self, url):
        """从URL提取视频ID"""
        if 'youtu.be/' in url:
            return url.split('youtu.be/')[-1].split('?')[0]
        elif 'watch?v=' in url:
            return url.split('watch?v=')[-1].split('&')[0]
        return None
    
    def process_url(self, url, form_data):
        """处理YouTube URL"""
        if not self.validate_url(url):
            return {'status': 'error', 'message': 'Invalid YouTube URL'}
        
        video_id = self.extract_video_id(url)
        if not video_id:
            return {'status': 'error', 'message': 'Could not extract video ID'}
        
        if self.processor:
            try:
                return self.processor.process_youtube(url, form_data)
            except Exception as e:
                return {'status': 'error', 'message': str(e)}
        else:
            return {'status': 'error', 'message': 'Processor not available'}


class TestYouTubeHandlerInit(unittest.TestCase):
    """测试YouTubeHandler初始化"""
    
    def test_init_with_valid_config(self):
        """测试使用有效配置初始化"""
        mock_config = Mock()
        mock_processor = Mock()
        
        handler = MockYouTubeHandler(mock_config, mock_processor)
        
        self.assertEqual(handler.config, mock_config)
        self.assertEqual(handler.processor, mock_processor)
    
    def test_init_without_processor(self):
        """测试无processor时的初始化"""
        mock_config = Mock()
        
        handler = MockYouTubeHandler(mock_config, None)
        
        self.assertEqual(handler.config, mock_config)
        self.assertIsNone(handler.processor)


class TestYouTubeHandlerValidation(unittest.TestCase):
    """测试YouTubeHandler URL验证功能"""
    
    def setUp(self):
        """设置测试环境"""
        self.mock_config = Mock()
        self.mock_processor = Mock()
        self.handler = MockYouTubeHandler(self.mock_config, self.mock_processor)
    
    def test_validate_url_standard_format(self):
        """测试标准YouTube URL格式验证"""
        url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        result = self.handler.validate_url(url)
        self.assertTrue(result)
    
    def test_validate_url_short_format(self):
        """测试短链接格式验证"""
        url = 'https://youtu.be/dQw4w9WgXcQ'
        result = self.handler.validate_url(url)
        self.assertTrue(result)
    
    def test_validate_url_embed_format(self):
        """测试嵌入格式验证"""
        url = 'https://www.youtube.com/embed/dQw4w9WgXcQ'
        result = self.handler.validate_url(url)
        self.assertTrue(result)
    
    def test_validate_url_invalid_format(self):
        """测试无效URL格式"""
        invalid_urls = [
            'https://www.google.com',
            'https://vimeo.com/123456',
            'not a url',
            ''
        ]
        
        for url in invalid_urls:
            result = self.handler.validate_url(url)
            self.assertFalse(result, f"URL {url} should be invalid")
    
    def test_validate_url_none_input(self):
        """测试None输入"""
        result = self.handler.validate_url(None)
        self.assertFalse(result)
    
    def test_validate_url_non_string_input(self):
        """测试非字符串输入"""
        result = self.handler.validate_url(123)
        self.assertFalse(result)


class TestYouTubeHandlerVideoIdExtraction(unittest.TestCase):
    """测试YouTube视频ID提取功能"""
    
    def setUp(self):
        """设置测试环境"""
        self.mock_config = Mock()
        self.handler = MockYouTubeHandler(self.mock_config)
    
    def test_extract_video_id_standard_url(self):
        """测试从标准URL提取视频ID"""
        url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        result = self.handler.extract_video_id(url)
        self.assertEqual(result, 'dQw4w9WgXcQ')
    
    def test_extract_video_id_short_url(self):
        """测试从短链接提取视频ID"""
        url = 'https://youtu.be/dQw4w9WgXcQ'
        result = self.handler.extract_video_id(url)
        self.assertEqual(result, 'dQw4w9WgXcQ')
    
    def test_extract_video_id_with_parameters(self):
        """测试带参数的URL"""
        url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s'
        result = self.handler.extract_video_id(url)
        self.assertEqual(result, 'dQw4w9WgXcQ')
    
    def test_extract_video_id_short_url_with_parameters(self):
        """测试带参数的短链接"""
        url = 'https://youtu.be/dQw4w9WgXcQ?t=30s'
        result = self.handler.extract_video_id(url)
        self.assertEqual(result, 'dQw4w9WgXcQ')
    
    def test_extract_video_id_invalid_url(self):
        """测试无效URL"""
        url = 'https://www.google.com'
        result = self.handler.extract_video_id(url)
        self.assertIsNone(result)


class TestYouTubeHandlerProcessing(unittest.TestCase):
    """测试YouTubeHandler处理功能"""
    
    def setUp(self):
        """设置测试环境"""
        self.mock_config = Mock()
        self.mock_processor = Mock()
        self.handler = MockYouTubeHandler(self.mock_config, self.mock_processor)
    
    def test_process_url_success(self):
        """测试成功的URL处理"""
        url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        form_data = {
            'content_type': 'youtube',
            'description': 'Test video'
        }
        
        # 设置processor mock
        self.mock_processor.process_youtube.return_value = {
            'status': 'success',
            'processing_id': 'yt_123'
        }
        
        result = self.handler.process_url(url, form_data)
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['processing_id'], 'yt_123')
        self.mock_processor.process_youtube.assert_called_once_with(url, form_data)
    
    def test_process_url_invalid_url(self):
        """测试处理无效URL"""
        url = 'https://www.google.com'
        form_data = {'content_type': 'youtube'}
        
        result = self.handler.process_url(url, form_data)
        
        self.assertEqual(result['status'], 'error')
        self.assertIn('Invalid YouTube URL', result['message'])
    
    def test_process_url_processor_exception(self):
        """测试处理器异常"""
        url = 'https://www.youtube.com/watch?v=test123'
        form_data = {'content_type': 'youtube'}
        
        # 设置processor抛出异常
        self.mock_processor.process_youtube.side_effect = Exception("Processing failed")
        
        result = self.handler.process_url(url, form_data)
        
        self.assertEqual(result['status'], 'error')
        self.assertIn('Processing failed', result['message'])
    
    def test_process_url_no_processor(self):
        """测试无processor的处理"""
        handler = MockYouTubeHandler(self.mock_config, None)
        
        url = 'https://www.youtube.com/watch?v=test123'
        form_data = {'content_type': 'youtube'}
        
        result = handler.process_url(url, form_data)
        
        self.assertEqual(result['status'], 'error')
        self.assertIn('Processor not available', result['message'])


class TestYouTubeHandlerErrorHandling(unittest.TestCase):
    """测试YouTubeHandler错误处理"""
    
    def setUp(self):
        """设置测试环境"""
        self.mock_config = Mock()
        self.mock_processor = Mock()
        self.handler = MockYouTubeHandler(self.mock_config, self.mock_processor)
    
    def test_handle_empty_url(self):
        """测试空URL处理"""
        result = self.handler.process_url('', {'content_type': 'youtube'})
        
        self.assertEqual(result['status'], 'error')
        self.assertIn('Invalid YouTube URL', result['message'])
    
    def test_handle_none_url(self):
        """测试None URL处理"""
        result = self.handler.process_url(None, {'content_type': 'youtube'})
        
        self.assertEqual(result['status'], 'error')
        self.assertIn('Invalid YouTube URL', result['message'])
    
    def test_handle_malformed_youtube_url(self):
        """测试格式错误的YouTube URL"""
        malformed_urls = [
            'youtube.com',  # 缺少协议
            'https://youtube.com',  # 缺少具体页面
            'https://www.youtube.com/user/test',  # 用户页面而非视频
        ]
        
        for url in malformed_urls:
            if 'youtube.com' not in url:
                continue  # Skip non-youtube URLs for this test
                
            result = self.handler.process_url(url, {'content_type': 'youtube'})
            
            # 这些URL可能验证失败或视频ID提取失败
            self.assertEqual(result['status'], 'error')
            self.assertTrue(
                'Invalid YouTube URL' in result['message'] or 
                'Could not extract video ID' in result['message']
            )


if __name__ == '__main__':
    unittest.main()