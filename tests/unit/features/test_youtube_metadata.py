#!/usr/bin/env python3
"""
YouTube元数据获取功能测试

测试YouTube视频标题和描述获取功能，包括API端点和YouTube处理器
"""

import unittest
import json
from unittest.mock import Mock, patch, MagicMock
from src.web_frontend.handlers.youtube_handler import YouTubeHandler
from src.utils.config import ConfigManager


class TestYouTubeMetadata(unittest.TestCase):
    """YouTube元数据获取功能测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.config_manager = Mock()
        self.config_manager.load_config.return_value = {
            'youtube': {
                'downloader': {
                    'timeout': 600,
                    'output_format': 'mp3'
                }
            }
        }
        self.handler = YouTubeHandler(self.config_manager)
        
    def test_youtube_handler_initialization(self):
        """测试YouTube处理器初始化"""
        handler = YouTubeHandler()
        self.assertIsNotNone(handler)
        self.assertIsNone(handler.config_manager)
        
    def test_extract_video_id_standard_url(self):
        """测试从标准YouTube URL提取视频ID"""
        test_cases = [
            ('https://www.youtube.com/watch?v=dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
            ('https://youtube.com/watch?v=dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
            ('https://youtu.be/dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
            ('https://www.youtube.com/watch?v=dQw4w9WgXcQ&feature=youtu.be', 'dQw4w9WgXcQ'),
        ]
        
        for url, expected_id in test_cases:
            with self.subTest(url=url):
                video_id = self.handler.extract_video_id(url)
                self.assertEqual(video_id, expected_id)
                
    def test_extract_video_id_invalid_url(self):
        """测试无效URL的视频ID提取"""
        invalid_urls = [
            'https://example.com/watch?v=invalid',
            'not-a-url',
            'https://youtube.com/invalid-path',
            ''
        ]
        
        for url in invalid_urls:
            with self.subTest(url=url):
                video_id = self.handler.extract_video_id(url)
                self.assertIsNone(video_id)
                
    def test_is_valid_youtube_url(self):
        """测试YouTube URL验证"""
        valid_urls = [
            'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'https://youtube.com/watch?v=dQw4w9WgXcQ',
            'https://youtu.be/dQw4w9WgXcQ',
            'https://m.youtube.com/watch?v=dQw4w9WgXcQ'
        ]
        
        invalid_urls = [
            'https://example.com/watch?v=invalid',
            'not-a-url',
            'https://vimeo.com/123456',
            ''
        ]
        
        for url in valid_urls:
            with self.subTest(url=url):
                self.assertTrue(self.handler.is_valid_youtube_url(url))
                
        for url in invalid_urls:
            with self.subTest(url=url):
                self.assertFalse(self.handler.is_valid_youtube_url(url))
    
    @patch('subprocess.run')
    def test_get_video_metadata_with_ytdlp(self, mock_subprocess):
        """测试使用yt-dlp获取视频元数据"""
        # Mock yt-dlp 成功响应
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            'title': 'Test Video Title',
            'description': 'This is a test video description with technical terms like API, machine learning, and neural networks.',
            'duration': 300,
            'uploader': 'Test Channel',
            'tags': ['test', 'video', 'tutorial', 'api', 'ml']
        })
        mock_subprocess.return_value = mock_result
        
        # 测试元数据获取
        url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        metadata = self.handler.get_video_metadata(url)
        
        # 验证结果
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata['title'], 'Test Video Title')
        self.assertIn('technical terms', metadata['description'])
        self.assertEqual(metadata['duration'], 300)
        self.assertEqual(metadata['uploader'], 'Test Channel')
        self.assertIsInstance(metadata['tags'], list)
        self.assertLessEqual(len(metadata['tags']), 10)  # 标签数量限制
        
    @patch('subprocess.run')  
    def test_get_video_metadata_ytdlp_failure(self, mock_subprocess):
        """测试yt-dlp获取失败时的处理"""
        # Mock yt-dlp 失败响应
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ''
        mock_subprocess.return_value = mock_result
        
        # 测试获取失败时返回模拟数据
        url = 'https://www.youtube.com/watch?v=invalid'
        metadata = self.handler.get_video_metadata(url)
        
        # 验证返回模拟数据
        self.assertIsNotNone(metadata)
        self.assertIn('invalid', metadata['title'])
        self.assertEqual(metadata['description'], 'Description not available')
        
    @patch('subprocess.run')
    def test_get_video_metadata_timeout(self, mock_subprocess):
        """测试yt-dlp超时处理"""
        import subprocess
        mock_subprocess.side_effect = subprocess.TimeoutExpired('yt-dlp', 30)
        
        url = 'https://www.youtube.com/watch?v=timeout'
        metadata = self.handler.get_video_metadata(url)
        
        # 超时时应返回模拟数据
        self.assertIsNotNone(metadata)
        self.assertIn('timeout', metadata['title'])
        
    def test_get_video_metadata_invalid_url(self):
        """测试无效URL的元数据获取"""
        invalid_url = 'not-a-youtube-url'
        metadata = self.handler.get_video_metadata(invalid_url)
        
        self.assertIsNone(metadata)
        
    @patch('subprocess.run')
    def test_description_length_limit(self, mock_subprocess):
        """测试描述长度限制"""
        # 创建超长描述
        long_description = 'A' * 2000
        
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            'title': 'Test Video',
            'description': long_description,
            'duration': 300,
            'uploader': 'Test Channel',
            'tags': []
        })
        mock_subprocess.return_value = mock_result
        
        url = 'https://www.youtube.com/watch?v=long-desc'
        metadata = self.handler.get_video_metadata(url)
        
        # 验证描述被限制在1000字符以内
        self.assertLessEqual(len(metadata['description']), 1000)
        
    @patch('subprocess.run')
    def test_tags_quantity_limit(self, mock_subprocess):
        """测试标签数量限制"""
        # 创建超多标签
        many_tags = [f'tag{i}' for i in range(20)]
        
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            'title': 'Test Video',
            'description': 'Test description',
            'duration': 300,
            'uploader': 'Test Channel',
            'tags': many_tags
        })
        mock_subprocess.return_value = mock_result
        
        url = 'https://www.youtube.com/watch?v=many-tags'
        metadata = self.handler.get_video_metadata(url)
        
        # 验证标签被限制在10个以内
        self.assertLessEqual(len(metadata['tags']), 10)
    
    @patch('subprocess.run')
    def test_get_video_metadata_with_manual_subtitles(self, mock_subprocess):
        """测试获取有手动字幕的视频元数据 - 手动字幕优先"""
        # Mock yt-dlp metadata response
        metadata_result = Mock()
        metadata_result.returncode = 0
        metadata_result.stdout = json.dumps({
            'title': 'Video with Manual Subtitles',
            'description': 'This video has high-quality manual subtitles',
            'duration': 300,
            'uploader': 'Professional Channel',
            'tags': ['professional', 'subtitles']
        })
        
        # Mock yt-dlp subtitle list response - 有手动字幕和自动字幕
        subtitle_result = Mock()
        subtitle_result.returncode = 0
        subtitle_result.stdout = '''Available subtitles for test123:
Language formats
zh-CN    vtt srt
en       vtt

Available automatic captions for test123:
Language formats
zh-Hans  vtt
en-US    vtt
ja       vtt'''
        
        # Configure subprocess.run to return different responses for different calls
        mock_subprocess.side_effect = [metadata_result, subtitle_result]
        
        url = 'https://www.youtube.com/watch?v=test123'
        metadata = self.handler.get_video_metadata(url)
        
        # 验证返回包含字幕信息，且手动字幕优先
        self.assertIsNotNone(metadata)
        self.assertIn('subtitle_info', metadata)
        self.assertTrue(metadata['subtitle_info']['available'])
        
        # 验证同时有手动字幕和自动字幕
        self.assertIn('zh-CN', metadata['subtitle_info']['subtitles'])
        self.assertIn('en-US', metadata['subtitle_info']['auto_captions'])
        
        # 总语言数应该包括所有类型
        expected_total = len(metadata['subtitle_info']['subtitles']) + len(metadata['subtitle_info']['auto_captions'])
        self.assertEqual(metadata['subtitle_info']['total_languages'], expected_total)
    
    @patch('subprocess.run')
    def test_get_video_metadata_no_subtitles_available(self, mock_subprocess):
        """测试获取视频元数据，无字幕可用"""
        # Mock yt-dlp metadata response
        metadata_result = Mock()
        metadata_result.returncode = 0
        metadata_result.stdout = json.dumps({
            'title': 'Video Without Subtitles',
            'description': 'This video has no subtitles',
            'duration': 600,
            'uploader': 'Test Channel',
            'tags': ['test', 'no-subs']
        })
        
        # Mock yt-dlp subtitle list response (no subtitles)
        subtitle_result = Mock()
        subtitle_result.returncode = 1  # Failed to get subtitles
        subtitle_result.stderr = 'No subtitles available'
        
        mock_subprocess.side_effect = [metadata_result, subtitle_result]
        
        url = 'https://www.youtube.com/watch?v=no_subtitles'
        metadata = self.handler.get_video_metadata(url)
        
        # 验证返回包含字幕信息，但显示无字幕
        self.assertIsNotNone(metadata)
        self.assertIn('subtitle_info', metadata)
        self.assertFalse(metadata['subtitle_info']['available'])
        self.assertEqual(metadata['subtitle_info']['total_languages'], 0)
    
    @patch('subprocess.run')
    def test_get_video_metadata_only_auto_captions(self, mock_subprocess):
        """测试获取仅有自动字幕的视频元数据 - 应该警告质量问题"""
        # Mock yt-dlp metadata response
        metadata_result = Mock()
        metadata_result.returncode = 0
        metadata_result.stdout = json.dumps({
            'title': 'Video with Only Auto Captions',
            'description': 'This video only has auto-generated captions',
            'duration': 600,
            'uploader': 'Auto Channel',
            'tags': ['auto', 'captions-only']
        })
        
        # Mock yt-dlp subtitle list response - 仅有自动字幕，无手动字幕
        subtitle_result = Mock()
        subtitle_result.returncode = 0
        subtitle_result.stdout = '''Available automatic captions for auto123:
Language formats
en-US    vtt
zh-Hans  vtt
es       vtt'''
        
        mock_subprocess.side_effect = [metadata_result, subtitle_result]
        
        url = 'https://www.youtube.com/watch?v=auto123'
        metadata = self.handler.get_video_metadata(url)
        
        # 验证返回包含字幕信息
        self.assertIsNotNone(metadata)
        self.assertIn('subtitle_info', metadata)
        self.assertTrue(metadata['subtitle_info']['available'])
        
        # 验证仅有自动字幕，无手动字幕
        self.assertEqual(len(metadata['subtitle_info']['subtitles']), 0)
        self.assertGreater(len(metadata['subtitle_info']['auto_captions']), 0)
        self.assertIn('en-US', metadata['subtitle_info']['auto_captions'])
        self.assertEqual(metadata['subtitle_info']['total_languages'], 3)
    
    @patch('subprocess.run')
    def test_get_video_metadata_subtitle_detection_error(self, mock_subprocess):
        """测试获取视频元数据，字幕检测出错"""
        # Mock yt-dlp metadata response (successful)
        metadata_result = Mock()
        metadata_result.returncode = 0
        metadata_result.stdout = json.dumps({
            'title': 'Video with Subtitle Error',
            'description': 'This video has subtitle detection error',
            'duration': 300,
            'uploader': 'Test Channel',
            'tags': ['test', 'error']
        })
        
        # Mock yt-dlp subtitle error (return code != 0)
        subtitle_result = Mock()
        subtitle_result.returncode = 1  # Error
        subtitle_result.stderr = 'Subtitle detection failed'
        
        # First call returns metadata, second call returns subtitle error
        mock_subprocess.side_effect = [metadata_result, subtitle_result]
        
        url = 'https://www.youtube.com/watch?v=error_test'
        metadata = self.handler.get_video_metadata(url)
        
        # 即使字幕检测失败，也应该返回基础元数据，字幕信息设为不可用
        self.assertIsNotNone(metadata)
        self.assertIn('subtitle_info', metadata)
        self.assertFalse(metadata['subtitle_info']['available'])


class TestYouTubeMetadataAPI(unittest.TestCase):
    """YouTube元数据API测试"""
    
    def setUp(self):
        """设置Flask测试客户端"""
        from src.web_frontend.app import create_app
        self.app = create_app()
        
        # 禁用测试环境的Tailscale IP检查
        self.app.config['TESTING'] = True
        
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
    def tearDown(self):
        """清理测试环境"""
        self.app_context.pop()
        
    @patch('ipaddress.ip_address')
    @patch('ipaddress.ip_network')
    def test_metadata_api_missing_url(self, mock_ip_network, mock_ip_address):
        """测试缺少URL参数的API请求"""
        # Mock Tailscale网络检查通过
        mock_network = Mock()
        mock_ip = Mock()
        mock_ip_network.return_value = mock_network
        mock_ip_address.return_value = mock_ip
        mock_network.__contains__ = Mock(return_value=True)
        
        response = self.client.get('/api/youtube/metadata')
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('URL parameter is required', data['error'])
        
    @patch('ipaddress.ip_address')
    @patch('ipaddress.ip_network') 
    @patch.object(YouTubeHandler, 'get_video_metadata')
    def test_metadata_api_success(self, mock_get_metadata, mock_ip_network, mock_ip_address):
        """测试成功获取元数据的API请求"""
        # Mock Tailscale网络检查通过
        mock_network = Mock()
        mock_ip = Mock()
        mock_ip_network.return_value = mock_network
        mock_ip_address.return_value = mock_ip
        mock_network.__contains__ = Mock(return_value=True)
        
        # Mock成功响应 - 手动字幕优先场景
        mock_get_metadata.return_value = {
            'title': 'Machine Learning Tutorial',
            'description': 'Learn about neural networks, deep learning, and AI algorithms.',
            'duration': 1200,
            'uploader': 'AI Education Channel',
            'tags': ['ml', 'ai', 'tutorial'],
            'subtitle_info': {
                'available': True,
                'subtitles': {'zh-CN': ['vtt', 'srt'], 'en': ['vtt']},  # 手动字幕
                'auto_captions': {'ja': ['vtt'], 'es': ['vtt']},  # 自动字幕
                'total_languages': 4
            }
        }
        
        url = 'https://www.youtube.com/watch?v=test123'
        response = self.client.get(f'/api/youtube/metadata?url={url}')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'Machine Learning Tutorial')
        self.assertIn('neural networks', data['description'])
        self.assertEqual(data['duration'], 1200)
        self.assertEqual(data['uploader'], 'AI Education Channel')
        self.assertIsInstance(data['tags'], list)
        
        # 验证字幕信息在API响应中 - 手动字幕优先
        self.assertIn('subtitle_info', data)
        self.assertTrue(data['subtitle_info']['available'])
        self.assertEqual(data['subtitle_info']['total_languages'], 4)
        
        # 验证手动字幕存在且优先
        self.assertIn('zh-CN', data['subtitle_info']['subtitles'])
        self.assertIn('en', data['subtitle_info']['subtitles'])
        
        # 验证自动字幕也存在但为次要
        self.assertIn('ja', data['subtitle_info']['auto_captions'])
        self.assertIn('es', data['subtitle_info']['auto_captions'])
        
    @patch.object(YouTubeHandler, 'get_video_metadata')
    def test_metadata_api_failure(self, mock_get_metadata):
        """测试获取元数据失败的API请求"""
        # Mock失败响应
        mock_get_metadata.return_value = None
        
        url = 'https://www.youtube.com/watch?v=invalid'
        response = self.client.get(f'/api/youtube/metadata?url={url}')
        
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('Failed to fetch video metadata', data['error'])
        
    @patch.object(YouTubeHandler, 'get_video_metadata')
    def test_metadata_api_exception(self, mock_get_metadata):
        """测试API异常处理"""
        # Mock异常
        mock_get_metadata.side_effect = Exception('Network error')
        
        url = 'https://www.youtube.com/watch?v=exception'
        response = self.client.get(f'/api/youtube/metadata?url={url}')
        
        self.assertEqual(response.status_code, 500)
        
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('Failed to get video metadata', data['error'])
        
    @patch('ipaddress.ip_address')
    @patch('ipaddress.ip_network')
    @patch.object(YouTubeHandler, 'get_video_metadata')
    def test_metadata_api_no_subtitles(self, mock_get_metadata, mock_ip_network, mock_ip_address):
        """测试API返回无字幕的视频元数据"""
        # Mock Tailscale网络检查通过
        mock_network = Mock()
        mock_ip = Mock()
        mock_ip_network.return_value = mock_network
        mock_ip_address.return_value = mock_ip
        mock_network.__contains__ = Mock(return_value=True)
        
        # Mock返回仅自动字幕的元数据 - 测试次优情况
        mock_get_metadata.return_value = {
            'title': 'Video with Only Auto Subtitles',
            'description': 'This video only has auto-generated subtitles.',
            'duration': 600,
            'uploader': 'Auto Channel',
            'tags': ['test', 'auto-only'],
            'subtitle_info': {
                'available': True,
                'subtitles': {},  # 无手动字幕
                'auto_captions': {'en-US': ['vtt'], 'zh-Hans': ['vtt']},  # 仅自动字幕
                'total_languages': 2
            }
        }
        
        url = 'https://www.youtube.com/watch?v=no_subtitles'
        response = self.client.get(f'/api/youtube/metadata?url={url}')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'Video with Only Auto Subtitles')
        
        # 验证API正确返回仅自动字幕的情况
        self.assertIn('subtitle_info', data)
        self.assertTrue(data['subtitle_info']['available'])  # 有字幕可用
        
        # 验证无手动字幕，仅有自动字幕
        self.assertEqual(len(data['subtitle_info']['subtitles']), 0)
        self.assertGreater(len(data['subtitle_info']['auto_captions']), 0)
        self.assertEqual(data['subtitle_info']['total_languages'], 2)


class TestYouTubeSuggestionsUIIntegration(unittest.TestCase):
    """测试YouTube建议UI集成功能"""
    
    def test_suggestions_ui_javascript_integration(self):
        """测试建议UI的JavaScript集成"""
        from pathlib import Path
        
        template_path = Path('./src/web_frontend/templates/upload.html')
        if template_path.exists():
            content = template_path.read_text()
            
            # 验证JavaScript函数存在
            self.assertIn('setupYouTubeSuggestions', content)
            self.assertIn('fetchVideoMetadata', content)
            
            # 验证API调用正确
            self.assertIn('/api/youtube/metadata', content)
            
    def test_suggestions_click_handlers(self):
        """测试建议点击处理器"""
        from pathlib import Path
        
        template_path = Path('./src/web_frontend/templates/upload.html')
        if template_path.exists():
            content = template_path.read_text()
            
            # 验证点击事件处理
            self.assertIn('addEventListener', content)
            self.assertIn('suggestion-item', content)
            
            # 验证文本填充功能
            self.assertIn('textarea', content)
            
    def test_error_handling_ui(self):
        """测试错误处理UI"""
        from pathlib import Path
        
        template_path = Path('./src/web_frontend/templates/upload.html')
        if template_path.exists():
            content = template_path.read_text()
            
            # 验证错误状态显示
            self.assertIn('metadata-error', content)
            self.assertIn('metadata-loading', content)


class TestYouTubeMetadataPerformance(unittest.TestCase):
    """测试YouTube元数据获取性能"""
    
    def setUp(self):
        """设置测试环境"""
        self.config_manager = Mock()
        self.config_manager.load_config.return_value = {
            'youtube': {
                'downloader': {
                    'timeout': 30,  # 较短的超时用于测试
                    'output_format': 'mp3'
                }
            }
        }
        self.handler = YouTubeHandler(self.config_manager)
    
    @patch('subprocess.run')
    def test_metadata_extraction_timeout(self, mock_subprocess):
        """测试元数据提取超时处理"""
        import subprocess
        
        # Mock超时异常
        mock_subprocess.side_effect = subprocess.TimeoutExpired('yt-dlp', 30)
        
        url = 'https://www.youtube.com/watch?v=timeout_test'
        metadata = self.handler.get_video_metadata(url)
        
        # 超时时应该返回fallback数据
        self.assertIsNotNone(metadata)
        self.assertIn('timeout_test', metadata['title'])
        self.assertEqual(metadata['description'], 'Description not available')
    
    @patch('subprocess.run')
    def test_large_description_truncation(self, mock_subprocess):
        """测试大型描述截断"""
        # 创建超长描述
        very_long_description = 'A' * 5000
        
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            'title': 'Test Video',
            'description': very_long_description,
            'duration': 300,
            'uploader': 'Test Channel',
            'tags': []
        })
        mock_subprocess.return_value = mock_result
        
        url = 'https://www.youtube.com/watch?v=large_desc'
        metadata = self.handler.get_video_metadata(url)
        
        # 验证描述被正确截断
        self.assertLessEqual(len(metadata['description']), 1000)
        self.assertGreater(len(metadata['description']), 0)


if __name__ == '__main__':
    unittest.main()