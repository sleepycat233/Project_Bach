#!/usr/bin/env python3
"""
Phase 6 YouTube处理器 - 单元测试

测试YouTubeProcessor类的各个方法
"""

import pytest
import tempfile
import shutil
import yaml
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.config import ConfigManager


class TestYouTubeProcessor:
    """测试YouTube处理器"""
    
    @pytest.fixture
    def temp_dir(self):
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def config_manager(self, temp_dir):
        """创建配置管理器"""
        config_data = {
            'youtube': {
                'downloader': {
                    'max_duration': 7200,
                    'min_duration': 60,
                    'preferred_quality': 'best[height<=720]',
                    'extract_audio_only': True,
                    'output_format': 'mp3',
                    'output_dir': temp_dir,
                    'timeout': 600
                },
                'validation': {
                    'check_availability': True,
                    'validate_duration': True,
                    'skip_private': True,
                    'skip_age_restricted': False
                },
                'metadata': {
                    'extract_thumbnail': True,
                    'extract_description': True,
                    'extract_tags': True,
                    'extract_comments': False
                }
            }
        }
        config_path = Path(temp_dir) / "config.yaml"
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, allow_unicode=True)
        return ConfigManager(str(config_path))
    
    @pytest.fixture
    def youtube_processor(self, config_manager, temp_dir):
        """创建YouTube处理器实例"""
        from src.web_frontend.processors.youtube_processor import YouTubeProcessor
        processor = YouTubeProcessor(config_manager)
        # 确保输出目录存在
        processor.output_dir.mkdir(exist_ok=True)
        return processor
    
    def test_validate_youtube_url_valid_formats(self, youtube_processor):
        """测试有效YouTube URL格式验证"""
        valid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://m.youtube.com/watch?v=abc123def45",
            "https://www.youtube.com/watch?v=test123ghij&t=30s",
            "https://youtu.be/short_id456?t=45"
        ]
        
        for url in valid_urls:
            assert youtube_processor.validate_youtube_url(url) is True
    
    def test_validate_youtube_url_invalid_formats(self, youtube_processor):
        """测试无效URL格式验证"""
        invalid_urls = [
            "https://vimeo.com/123456",
            "https://dailymotion.com/video",
            "https://example.com/video",
            "not-a-url",
            "",
            None,
            "youtube.com",  # 缺少协议
            "https://youtube.com"  # 缺少视频ID
        ]
        
        for url in invalid_urls:
            assert youtube_processor.validate_youtube_url(url) is False
    
    @patch('subprocess.run')
    def test_get_video_info_success(self, mock_subprocess, youtube_processor):
        """测试成功获取视频信息"""
        # 模拟yt-dlp成功输出
        mock_video_info = {
            "id": "dQw4w9WgXcQ",
            "title": "Test Video - Machine Learning Tutorial",
            "duration": 1800,  # 30分钟
            "uploader": "AI Education Channel",
            "description": "A comprehensive tutorial on neural networks and deep learning algorithms",
            "upload_date": "20240101",
            "view_count": 150000,
            "like_count": 5000,
            "thumbnails": [{"url": "https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg"}],
            "categories": ["Education", "Technology"],
            "tags": ["machine learning", "AI", "tutorial"],
            "availability": "public"
        }
        
        mock_subprocess.return_value = Mock(
            stdout=json.dumps(mock_video_info),
            stderr="",
            returncode=0
        )
        
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        result = youtube_processor.get_video_info(url)
        
        assert result['success'] is True
        info = result['info']
        assert info['title'] == "Test Video - Machine Learning Tutorial"
        assert info['duration'] == 1800
        assert info['uploader'] == "AI Education Channel"
        assert info['view_count'] == 150000
        assert 'machine learning' in info['tags']
        
        # 验证调用了正确的yt-dlp命令
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert 'yt-dlp' in call_args
        assert '--dump-json' in call_args
        assert url in call_args
    
    @patch('subprocess.run')
    def test_get_video_info_failure(self, mock_subprocess, youtube_processor):
        """测试获取视频信息失败"""
        mock_subprocess.return_value = Mock(
            stdout="",
            stderr="ERROR: Video unavailable",
            returncode=1
        )
        
        url = "https://www.youtube.com/watch?v=unavailable"
        result = youtube_processor.get_video_info(url)
        
        assert result['success'] is False
        assert 'Video unavailable' in result['error']
    
    def test_validate_video_info_valid_video(self, youtube_processor):
        """测试有效视频信息验证"""
        valid_info = {
            "duration": 1800,  # 30分钟
            "availability": "public",
            "age_limit": 0
        }
        
        result = youtube_processor.validate_video_info(valid_info)
        assert result['valid'] is True
        assert result['message'] == "视频信息验证通过"
    
    def test_validate_video_info_too_long(self, youtube_processor):
        """测试视频时长过长验证"""
        long_video_info = {
            "duration": 8000,  # 超过2小时限制
            "availability": "public",
            "age_limit": 0
        }
        
        result = youtube_processor.validate_video_info(long_video_info)
        assert result['valid'] is False
        assert "视频时长(8000秒)超过限制(7200秒)" == result['message']
    
    def test_validate_video_info_too_short(self, youtube_processor):
        """测试视频时长过短验证"""
        short_video_info = {
            "duration": 30,  # 少于1分钟限制
            "availability": "public",
            "age_limit": 0
        }
        
        result = youtube_processor.validate_video_info(short_video_info)
        assert result['valid'] is False
        assert "视频时长(30秒)少于最小限制(60秒)" == result['message']
    
    def test_validate_video_info_private_video(self, youtube_processor):
        """测试私有视频验证"""
        private_video_info = {
            "duration": 1800,
            "availability": "private",
            "age_limit": 0
        }
        
        result = youtube_processor.validate_video_info(private_video_info)
        assert result['valid'] is False
        assert "私有视频" in result['message']
    
    @patch('subprocess.run')
    def test_download_audio_success(self, mock_subprocess, youtube_processor):
        """测试音频下载成功"""
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="Download completed",
            stderr=""
        )
        
        url = "https://www.youtube.com/watch?v=test123"
        video_id = "test123"
        
        # 创建模拟下载的文件
        expected_path = youtube_processor.output_dir / f"{video_id}.mp3"
        expected_path.touch()
        
        result = youtube_processor.download_audio(url, video_id)
        
        assert result['success'] is True
        assert 'output_file' in result
        assert video_id in result['output_file']
        
        # 验证调用了正确的yt-dlp命令
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert 'yt-dlp' in call_args
        assert '--extract-audio' in call_args
        assert '--audio-format' in call_args
        assert 'mp3' in call_args
        assert url in call_args
    
    @patch('subprocess.run')
    def test_download_audio_failure(self, mock_subprocess, youtube_processor):
        """测试音频下载失败"""
        mock_subprocess.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="ERROR: Private video"
        )
        
        url = "https://www.youtube.com/watch?v=private123"
        video_id = "private123"
        
        result = youtube_processor.download_audio(url, video_id)
        
        assert result['success'] is False
        assert 'Private video' in result['error']
    
    def test_extract_video_id_from_url(self, youtube_processor):
        """测试从URL提取视频ID"""
        test_cases = [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://m.youtube.com/watch?v=abc123def45", "abc123def45"),
            ("https://www.youtube.com/watch?v=test1234567&t=30s", "test1234567"),
        ]
        
        for url, expected_id in test_cases:
            result = youtube_processor.extract_video_id(url)
            assert result == expected_id
    
    def test_extract_video_id_invalid_url(self, youtube_processor):
        """测试无效URL的视频ID提取"""
        invalid_urls = [
            "https://vimeo.com/123456",
            "https://example.com/video",
            "not-a-url",
            ""
        ]
        
        for url in invalid_urls:
            assert youtube_processor.extract_video_id(url) is None
    
    def test_format_video_metadata(self, youtube_processor):
        """测试视频元数据格式化"""
        video_info = {
            "id": "dQw4w9WgXcQ",
            "title": "Test Video",
            "description": "A test video description",
            "duration": 3600,
            "view_count": 1000000,
            "uploader": "Test Channel",
            "upload_date": "20250822",
            "tags": ["test", "video", "demo"],
            "thumbnails": [{"url": "https://example.com/thumb.jpg"}]
        }
        
        result = youtube_processor.format_video_metadata(video_info)
        
        assert result['video_id'] == "dQw4w9WgXcQ"
        assert result['title'] == "Test Video"
        assert result['channel_name'] == "Test Channel"
        assert result['duration_formatted'] == "1:00:00"
        assert result['view_count_formatted'] == "1,000,000"
        assert result['upload_date_formatted'] == "2025-08-22"
        assert result['tags'] == ["test", "video", "demo"]
        assert 'description_preview' in result
    
    def test_format_duration(self, youtube_processor):
        """测试时长格式化"""
        test_cases = [
            (30, "0:30"),
            (90, "1:30"),
            (3600, "1:00:00"),
            (3661, "1:01:01"),
            (7200, "2:00:00"),
        ]
        
        for seconds, expected in test_cases:
            result = youtube_processor.format_duration(seconds)
            assert result == expected
    
    def test_format_view_count(self, youtube_processor):
        """测试观看次数格式化"""
        test_cases = [
            (1000, "1,000"),
            (1000000, "1,000,000"),
            (1234567, "1,234,567"),
            (999, "999"),
        ]
        
        for count, expected in test_cases:
            result = youtube_processor.format_view_count(count)
            assert result == expected