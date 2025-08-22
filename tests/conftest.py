#!/usr/bin/env python3
"""
Phase 6 测试配置和公共fixtures

为Phase 6多媒体内容分类与Web界面测试提供共享配置
"""

import pytest
import tempfile
import shutil
import os
import yaml
from pathlib import Path
from unittest.mock import Mock, MagicMock
from datetime import datetime
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

@pytest.fixture(scope="session")
def test_config():
    """测试配置数据"""
    return {
        'content_types': {
            'lecture': {
                'icon': '🎓',
                'auto_detect': ['lecture', 'course', '教授', 'professor'],
                'keywords': ['education', 'university', 'classroom'],
                'supported_formats': ['mp3', 'wav', 'm4a', 'mp4']
            },
            'youtube': {
                'icon': '📺',
                'processor': 'yt-dlp',
                'auto_detect': ['youtube.com', 'youtu.be'],
                'supported_formats': ['mp4', 'webm', 'mkv'],
                'max_duration': 7200  # 2小时
            },
            'rss': {
                'icon': '📰',
                'processor': 'feedparser',
                'auto_detect': ['rss', 'feed', 'xml'],
                'refresh_interval': 3600,
                'max_articles': 50
            },
            'podcast': {
                'icon': '🎙️',
                'auto_detect': ['podcast', 'interview', '访谈'],
                'keywords': ['talk', 'conversation', 'discussion'],
                'supported_formats': ['mp3', 'wav', 'aac']
            }
        },
        'web_interface': {
            'upload_folder': './uploads',
            'max_file_size': 100 * 1024 * 1024,  # 100MB
            'allowed_extensions': ['.mp3', '.wav', '.m4a', '.mp4'],
            'tailscale_network': '100.64.0.0/10',
            'security': {
                'rate_limit': 60,  # requests per minute
                'max_connections': 100,
                'session_timeout': 3600
            }
        },
        'github_pages': {
            'categories_per_page': 10,
            'enable_search': True,
            'enable_statistics': True,
            'theme': 'dark'
        }
    }

@pytest.fixture
def temp_workspace():
    """临时工作空间"""
    temp_dir = tempfile.mkdtemp(prefix="phase6_test_")
    
    # 创建基本目录结构
    directories = [
        'uploads',
        'output',
        'templates',
        'static',
        'data/logs'
    ]
    
    for dir_path in directories:
        (Path(temp_dir) / dir_path).mkdir(parents=True, exist_ok=True)
    
    yield temp_dir
    
    # 清理
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def mock_config_manager(test_config, temp_workspace):
    """模拟配置管理器"""
    config_path = Path(temp_workspace) / "test_config.yaml"
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(test_config, f, allow_unicode=True)
    
    mock_config = Mock()
    mock_config.get.side_effect = lambda key, default=None: test_config.get(key, default)
    mock_config.get_nested.side_effect = lambda *keys: _get_nested_value(test_config, keys)
    mock_config.config_path = str(config_path)
    
    return mock_config

def _get_nested_value(data, keys):
    """获取嵌套字典值的辅助函数"""
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return current

@pytest.fixture
def sample_audio_file(temp_workspace):
    """示例音频文件"""
    audio_path = Path(temp_workspace) / "uploads" / "test_lecture.mp3"
    
    # 创建模拟音频文件内容
    fake_mp3_header = b'\xff\xfb\x90\x00'  # MP3文件头
    fake_content = fake_mp3_header + b'\x00' * 1024  # 1KB的模拟音频数据
    
    with open(audio_path, 'wb') as f:
        f.write(fake_content)
    
    return str(audio_path)

@pytest.fixture
def sample_result_data():
    """示例处理结果数据"""
    return {
        'filename': 'physics_lecture_01.mp3',
        'content_type': 'lecture',
        'content_metadata': {
            'lecture_series': 'Physics 101',
            'tags': ['physics', 'quantum', 'education'],
            'confidence': 0.87,
            'auto_detected': True,
            'duration': 1800,
            'source_url': None
        },
        'summary': 'This lecture introduces the fundamental concepts of quantum mechanics...',
        'mindmap': '''
# Quantum Mechanics Basics

## 1. Wave-Particle Duality
- Light behaves as both wave and particle
- De Broglie wavelength
- Uncertainty principle

## 2. Quantum States
- Superposition
- Entanglement
- Measurement problem
''',
        'anonymized_mapping': {},
        'processed_at': datetime.now().isoformat(),
        'processing_time': 45.2,
        'model_info': {
            'transcription': 'whisperkit-large-v3',
            'ai_generation': 'google/gemma-3n-e2b-it'
        }
    }

@pytest.fixture
def sample_youtube_data():
    """示例YouTube数据"""
    return {
        'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        'title': 'Machine Learning Tutorial - Neural Networks',
        'description': 'A comprehensive tutorial on neural networks and deep learning',
        'uploader': 'AI Education Channel',
        'duration': 2400,  # 40分钟
        'view_count': 150000,
        'upload_date': '20240101',
        'thumbnail_url': 'https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg'
    }

@pytest.fixture
def sample_rss_articles():
    """示例RSS文章数据"""
    return [
        {
            'title': 'Advances in Artificial Intelligence Research',
            'link': 'https://techblog.example.com/ai-advances-2024',
            'summary': 'Recent breakthroughs in AI research including new architectures...',
            'content': 'The field of artificial intelligence continues to evolve rapidly...' * 50,
            'author': 'Dr. Jane Smith',
            'published': '2024-01-15T10:00:00Z',
            'tags': ['AI', 'research', 'technology']
        },
        {
            'title': 'Quantum Computing Progress Update',
            'link': 'https://sciencenews.example.com/quantum-update',
            'summary': 'Latest developments in quantum computing hardware and algorithms...',
            'content': 'Quantum computing has reached several important milestones...' * 40,
            'author': 'Prof. Bob Johnson', 
            'published': '2024-01-12T14:30:00Z',
            'tags': ['quantum', 'computing', 'physics']
        }
    ]

@pytest.fixture
def mock_flask_app():
    """模拟Flask应用"""
    from flask import Flask
    
    app = Flask(__name__)
    app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,
        'MAX_CONTENT_LENGTH': 100 * 1024 * 1024  # 100MB
    })
    
    return app

@pytest.fixture
def mock_youtube_processor():
    """模拟YouTube处理器"""
    processor = Mock()
    processor.validate_url.return_value = True
    processor.extract_video_info.return_value = {
        'title': 'Test Video',
        'duration': 1800,
        'uploader': 'Test Channel',
        'description': 'Test video description'
    }
    processor.download_audio.return_value = '/tmp/test_video.mp3'
    processor.validate_duration.return_value = True
    
    return processor

@pytest.fixture
def mock_rss_processor():
    """模拟RSS处理器"""
    processor = Mock()
    processor.parse_feed.return_value = [
        {
            'title': 'Tech Article 1',
            'content': 'Article content 1',
            'link': 'https://example.com/article1'
        }
    ]
    processor.validate_feed_url.return_value = True
    processor.filter_content.return_value = []
    processor.generate_summary.return_value = 'Generated summary'
    
    return processor

@pytest.fixture
def mock_tailscale_validator():
    """模拟Tailscale安全验证器"""
    validator = Mock()
    validator.is_tailscale_ip.return_value = True
    validator.validate_acl_config.return_value = True
    validator.check_access_permission.return_value = True
    validator.check_rate_limit.return_value = True
    validator.detect_intrusion.return_value = None
    validator.validate_ssl_certificate.return_value = {
        'valid': True,
        'expiry_date': '2025-12-31'
    }
    
    return validator

@pytest.fixture(autouse=True)
def setup_test_environment(temp_workspace):
    """自动设置测试环境"""
    # 设置环境变量
    os.environ['PROJECT_BACH_TEST_MODE'] = 'true'
    os.environ['PROJECT_BACH_DATA_DIR'] = temp_workspace
    
    yield
    
    # 清理环境变量
    os.environ.pop('PROJECT_BACH_TEST_MODE', None)
    os.environ.pop('PROJECT_BACH_DATA_DIR', None)

@pytest.fixture
def mock_processing_queue():
    """模拟处理队列"""
    queue = Mock()
    queue.put.return_value = True
    queue.get_status.return_value = {
        'queue_size': 0,
        'processing_items': [],
        'completed_today': 5
    }
    queue.get_processing_history.return_value = []
    
    return queue

class TestHelper:
    """测试辅助类"""
    
    @staticmethod
    def create_mock_file_upload(filename, content=b'fake content', content_type='audio/mpeg'):
        """创建模拟文件上传对象"""
        from io import BytesIO
        from werkzeug.datastructures import FileStorage
        
        return FileStorage(
            stream=BytesIO(content),
            filename=filename,
            content_type=content_type
        )
    
    @staticmethod
    def assert_valid_content_metadata(metadata):
        """断言有效的内容元数据"""
        required_fields = ['content_type', 'confidence', 'auto_detected', 'tags']
        for field in required_fields:
            assert field in metadata, f"Missing required field: {field}"
        
        assert metadata['content_type'] in ['lecture', 'youtube', 'rss', 'podcast']
        assert 0 <= metadata['confidence'] <= 1
        assert isinstance(metadata['auto_detected'], bool)
        assert isinstance(metadata['tags'], list)
    
    @staticmethod
    def assert_valid_result_format(result):
        """断言有效的处理结果格式"""
        required_fields = ['filename', 'content_type', 'summary', 'processed_at']
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
        
        assert isinstance(result['processed_at'], str)
        assert len(result['summary']) > 0

# 全局测试标记
pytestmark = pytest.mark.phase6