#!/usr/bin/env python3
"""
Phase 6.5 音频上传处理器 - 单元测试

测试AudioUploadProcessor类的各个方法
"""

import pytest
import tempfile
import shutil
import yaml
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.config import ConfigManager
from src.web_frontend.processors.audio_upload_processor import AudioUploadProcessor


class TestAudioUploadProcessor:
    """测试音频上传处理器"""
    
    @pytest.fixture
    def temp_dir(self):
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def config_manager(self, temp_dir):
        """创建配置管理器"""
        config_data = {
            'content_classification': {
                'content_types': {
                    'lecture': {
                        'icon': '🎓',
                        'display_name': '讲座',
                        'description': '学术讲座、课程录音、教育内容',
                        'auto_detect_patterns': {
                            'filename': ['lecture', 'course', '教授'],
                            'content': ['education', 'university', '学习']
                        }
                    },
                    'podcast': {
                        'icon': '🎙️',
                        'display_name': '播客',
                        'description': '播客节目、访谈内容、讨论节目',
                        'auto_detect_patterns': {
                            'filename': ['podcast', 'interview'],
                            'content': ['interview', 'discussion']
                        }
                    },
                    'youtube': {
                        'icon': '📺',
                        'display_name': '视频',
                        'description': 'YouTube视频内容、教学视频、技术分享'
                    }
                }
            },
            'audio_upload': {
                'auto_process': True,
                'preserve_original': True,
                'filename_sanitization': True
            }
        }
        config_path = Path(temp_dir) / "config.yaml"
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, allow_unicode=True)
        
        # 创建一个简单的ConfigManager实例，避免环境管理器干扰
        class SimpleConfigManager:
            def __init__(self, config_data):
                self.config = config_data
            
            def get_nested_config(self, *keys):
                current = self.config
                for key in keys:
                    if isinstance(current, dict) and key in current:
                        current = current[key]
                    else:
                        return None
                return current
        
        return SimpleConfigManager(config_data)
    
    @pytest.fixture
    def upload_processor(self, config_manager, temp_dir):
        """创建音频上传处理器实例"""
        # 使用临时目录作为上传和监控目录
        processor = AudioUploadProcessor(config_manager)
        processor.upload_dir = Path(temp_dir) / "uploads"
        processor.watch_dir = Path(temp_dir) / "watch"
        processor.upload_dir.mkdir(exist_ok=True)
        processor.watch_dir.mkdir(exist_ok=True)
        return processor
    
    @pytest.fixture
    def sample_audio_files(self, temp_dir):
        """创建示例音频文件"""
        files = {}
        
        # 创建有效的音频文件
        valid_file = Path(temp_dir) / "test_lecture.mp3"
        valid_file.write_bytes(b"fake mp3 content" * 1000)  # 约17KB
        files['valid_mp3'] = valid_file
        
        # 创建不同格式的文件
        wav_file = Path(temp_dir) / "test_podcast.wav"
        wav_file.write_bytes(b"fake wav content" * 2000)  # 约34KB
        files['valid_wav'] = wav_file
        
        # 创建大文件
        large_file = Path(temp_dir) / "large_file.mp3"
        large_file.write_bytes(b"x" * (600 * 1024 * 1024))  # 600MB
        files['large_file'] = large_file
        
        # 创建小文件
        small_file = Path(temp_dir) / "small_file.mp3"
        small_file.write_bytes(b"x" * 500)  # 500字节
        files['small_file'] = small_file
        
        # 创建不支持格式的文件
        invalid_file = Path(temp_dir) / "test_document.txt"
        invalid_file.write_text("This is not an audio file")
        files['invalid_format'] = invalid_file
        
        return files
    
    def test_validate_audio_file_valid_mp3(self, upload_processor, sample_audio_files):
        """测试有效MP3文件验证"""
        result = upload_processor.validate_audio_file(sample_audio_files['valid_mp3'])
        
        assert result['valid'] is True
        assert result['message'] == '文件验证通过'
        assert 'file_info' in result
        
        file_info = result['file_info']
        assert file_info['extension'] == '.mp3'
        assert file_info['name'] == 'test_lecture.mp3'
        assert file_info['stem'] == 'test_lecture'
        assert file_info['size'] > 0
        assert file_info['size_mb'] > 0
    
    def test_validate_audio_file_valid_wav(self, upload_processor, sample_audio_files):
        """测试有效WAV文件验证"""
        result = upload_processor.validate_audio_file(sample_audio_files['valid_wav'])
        
        assert result['valid'] is True
        assert result['file_info']['extension'] == '.wav'
        assert result['file_info']['name'] == 'test_podcast.wav'
    
    def test_validate_audio_file_nonexistent(self, upload_processor, temp_dir):
        """测试不存在文件的验证"""
        nonexistent_file = Path(temp_dir) / "nonexistent.mp3"
        result = upload_processor.validate_audio_file(nonexistent_file)
        
        assert result['valid'] is False
        assert '文件不存在' in result['error']
    
    def test_validate_audio_file_invalid_format(self, upload_processor, sample_audio_files):
        """测试无效格式文件验证"""
        result = upload_processor.validate_audio_file(sample_audio_files['invalid_format'])
        
        assert result['valid'] is False
        assert '不支持的文件格式' in result['error']
        assert 'supported_formats' in result
        assert '.mp3' in result['supported_formats']
    
    def test_validate_audio_file_too_large(self, upload_processor, sample_audio_files):
        """测试文件过大验证"""
        result = upload_processor.validate_audio_file(sample_audio_files['large_file'])
        
        assert result['valid'] is False
        assert '文件大小' in result['error']
        assert '超过限制' in result['error']
    
    def test_validate_audio_file_too_small(self, upload_processor, sample_audio_files):
        """测试文件过小验证"""
        result = upload_processor.validate_audio_file(sample_audio_files['small_file'])
        
        assert result['valid'] is False
        assert '文件大小' in result['error']
        assert '小于最小限制' in result['error']
    
    def test_get_available_content_types(self, upload_processor):
        """测试获取可用内容类型"""
        content_types = upload_processor.get_available_content_types()
        
        assert 'lecture' in content_types
        assert 'podcast' in content_types
        assert 'youtube' in content_types
        
        lecture_config = content_types['lecture']
        assert lecture_config['icon'] == '🎓'
        assert lecture_config['display_name'] == '讲座'
        assert '学术讲座' in lecture_config['description']
        assert lecture_config['auto_detect_available'] is True
        
        youtube_config = content_types['youtube']
        # YouTube在测试配置中没有auto_detect_patterns，应该是False
        assert youtube_config['auto_detect_available'] is False
    
    def test_sanitize_filename_normal(self, upload_processor):
        """测试正常文件名安全化"""
        normal_filename = "normal_audio_file.mp3"
        result = upload_processor.sanitize_filename(normal_filename)
        assert result == normal_filename
    
    def test_sanitize_filename_unsafe_chars(self, upload_processor):
        """测试包含不安全字符的文件名"""
        unsafe_filename = "audio<>file|with?unsafe*chars.mp3"
        result = upload_processor.sanitize_filename(unsafe_filename)
        assert result == "audio__file_with_unsafe_chars.mp3"
        
        # 确保所有不安全字符都被替换
        unsafe_chars = '<>:"/\\|?*'
        for char in unsafe_chars:
            assert char not in result
    
    def test_sanitize_filename_empty(self, upload_processor):
        """测试空文件名处理"""
        result = upload_processor.sanitize_filename("")
        assert "audio_" in result
        assert len(result) > 10  # 应该生成基于时间戳的文件名
    
    def test_sanitize_filename_disabled(self, upload_processor):
        """测试禁用文件名安全化"""
        upload_processor.filename_sanitization = False
        unsafe_filename = "unsafe<>filename.mp3"
        result = upload_processor.sanitize_filename(unsafe_filename)
        assert result == unsafe_filename  # 应该保持原样
    
    def test_process_uploaded_file_success(self, upload_processor, sample_audio_files):
        """测试成功处理上传文件"""
        source_file = sample_audio_files['valid_mp3']
        selected_type = 'lecture'
        custom_metadata = {
            'title': 'Test Lecture Audio',
            'tags': ['education', 'test'],
            'description': 'A test lecture audio file'
        }
        
        result = upload_processor.process_uploaded_file(
            source_file,
            selected_type,
            custom_metadata
        )
        
        assert result['success'] is True
        assert 'target_file_path' in result
        assert 'preserved_file_path' in result
        assert 'processing_metadata' in result
        assert '类型: 讲座' in result['message']
        
        # 检查文件是否被复制到watch目录
        target_path = Path(result['target_file_path'])
        assert target_path.exists()
        assert target_path.parent == upload_processor.watch_dir
        assert 'LEC_' in target_path.name  # 应该有内容类型前缀
        
        # 检查原始文件是否被保留
        if result['preserved_file_path']:
            preserved_path = Path(result['preserved_file_path'])
            assert preserved_path.exists()
            assert preserved_path.parent == upload_processor.upload_dir
        
        # 检查处理元数据
        metadata = result['processing_metadata']
        assert metadata['selected_content_type'] == 'lecture'
        assert metadata['auto_process'] is True
        assert metadata['custom_metadata'] == custom_metadata
        
        # 检查分类结果
        classification = metadata['classification_result']
        assert classification['content_type'] == 'lecture'
        assert classification['confidence'] == 1.0
        assert classification['manual_selection'] is True
        assert classification['auto_detected'] is False
    
    def test_process_uploaded_file_invalid_file(self, upload_processor, sample_audio_files):
        """测试处理无效文件"""
        invalid_file = sample_audio_files['invalid_format']
        result = upload_processor.process_uploaded_file(invalid_file, 'lecture')
        
        assert result['success'] is False
        assert '文件验证失败' in result['error']
    
    def test_process_uploaded_file_invalid_content_type(self, upload_processor, sample_audio_files):
        """测试无效内容类型"""
        valid_file = sample_audio_files['valid_mp3']
        result = upload_processor.process_uploaded_file(valid_file, 'invalid_type')
        
        assert result['success'] is False
        assert '无效的内容类型' in result['error']
        assert 'available_types' in result
    
    def test_process_uploaded_file_preserve_original_disabled(self, upload_processor, sample_audio_files):
        """测试禁用原始文件保留"""
        upload_processor.preserve_original = False
        
        source_file = sample_audio_files['valid_mp3']
        result = upload_processor.process_uploaded_file(source_file, 'lecture')
        
        assert result['success'] is True
        assert result['preserved_file_path'] is None
    
    def test_process_uploaded_file_unique_filename(self, upload_processor, sample_audio_files):
        """测试文件名唯一性处理"""
        source_file = sample_audio_files['valid_mp3']
        
        # 第一次上传
        result1 = upload_processor.process_uploaded_file(source_file, 'lecture')
        assert result1['success'] is True
        
        # 第二次上传相同文件
        result2 = upload_processor.process_uploaded_file(source_file, 'lecture')
        assert result2['success'] is True
        
        # 文件名应该不同
        path1 = Path(result1['target_file_path'])
        path2 = Path(result2['target_file_path'])
        assert path1.name != path2.name
        # 两个文件都应该存在
        assert path1.exists()
        assert path2.exists()
    
    def test_create_upload_metadata_file(self, upload_processor, temp_dir):
        """测试创建上传元数据文件"""
        target_file = Path(temp_dir) / "test_audio.mp3"
        target_file.touch()
        
        metadata = {
            'source_file': 'original_audio.mp3',
            'selected_content_type': 'lecture',
            'upload_time': datetime.now().isoformat()
        }
        
        result_path = upload_processor.create_upload_metadata_file(target_file, metadata)
        
        assert result_path is not None
        assert result_path.exists()
        assert result_path.suffix == '.json'
        assert 'test_audio_upload_metadata.json' == result_path.name
        
        # 验证JSON内容
        with open(result_path, 'r', encoding='utf-8') as f:
            saved_metadata = json.load(f)
        
        assert saved_metadata['source_file'] == 'original_audio.mp3'
        assert saved_metadata['selected_content_type'] == 'lecture'
    
    def test_get_upload_statistics(self, upload_processor, sample_audio_files):
        """测试获取上传统计信息"""
        # 处理几个文件
        upload_processor.process_uploaded_file(sample_audio_files['valid_mp3'], 'lecture')
        upload_processor.process_uploaded_file(sample_audio_files['valid_wav'], 'podcast')
        
        stats = upload_processor.get_upload_statistics()
        
        assert 'total_audio_files' in stats
        assert 'total_preserved_files' in stats
        assert 'content_type_distribution' in stats
        assert 'watch_directory' in stats
        assert 'upload_directory' in stats
        assert 'supported_formats' in stats
        assert 'last_updated' in stats
        
        assert stats['total_audio_files'] >= 2
        assert stats['content_type_distribution'].get('lecture', 0) >= 1
        assert stats['content_type_distribution'].get('podcast', 0) >= 1
        assert '.mp3' in stats['supported_formats']
    
    def test_cleanup_old_files(self, upload_processor, temp_dir):
        """测试清理旧文件"""
        # 创建一些测试文件
        old_file = upload_processor.upload_dir / "old_file.mp3"
        old_file.write_bytes(b"old content")
        
        # 修改文件时间为31天前
        import os
        old_time = datetime.now() - timedelta(days=31)
        old_timestamp = old_time.timestamp()
        os.utime(old_file, (old_timestamp, old_timestamp))
        
        new_file = upload_processor.upload_dir / "new_file.mp3"
        new_file.write_bytes(b"new content")
        
        # 清理30天前的文件
        result = upload_processor.cleanup_old_files(days_to_keep=30)
        
        assert result['success'] is True
        assert result['cleaned_files_count'] >= 1
        assert result['total_cleaned_size'] > 0
        assert result['total_cleaned_size_mb'] >= 0  # 小文件可能为0.0MB
        
        # 旧文件应该被删除，新文件应该保留
        assert not old_file.exists()
        assert new_file.exists()
    
    def test_cleanup_old_files_no_files_to_clean(self, upload_processor):
        """测试没有文件需要清理的情况"""
        result = upload_processor.cleanup_old_files(days_to_keep=1)
        
        assert result['success'] is True
        assert result['cleaned_files_count'] == 0
        assert result['total_cleaned_size'] == 0
    
    def test_supported_formats_constant(self, upload_processor):
        """测试支持的格式常量"""
        formats = upload_processor.SUPPORTED_FORMATS
        
        # 检查常见音频格式
        assert '.mp3' in formats
        assert '.wav' in formats
        assert '.m4a' in formats
        assert '.mp4' in formats
        assert '.flac' in formats
        assert '.aac' in formats
        assert '.ogg' in formats
        
        # 确保是集合类型
        assert isinstance(formats, set)
    
    def test_file_size_limits(self, upload_processor):
        """测试文件大小限制常量"""
        assert upload_processor.MAX_FILE_SIZE == 500 * 1024 * 1024  # 500MB
        assert upload_processor.MIN_FILE_SIZE == 1024  # 1KB
    
    def test_initialization_with_missing_config(self, temp_dir):
        """测试缺少配置时的初始化"""
        # 创建没有content_classification的配置
        config_data = {'other_config': 'value'}
        
        # 创建简单的配置管理器（模拟缺失配置）
        class SimpleConfigManager:
            def __init__(self, config_data):
                self.config = config_data
            
            def get_nested_config(self, *keys):
                current = self.config
                for key in keys:
                    if isinstance(current, dict) and key in current:
                        current = current[key]
                    else:
                        return None
                return current
        
        config_manager = SimpleConfigManager(config_data)
        
        with pytest.raises(ValueError, match="内容分类配置缺失"):
            AudioUploadProcessor(config_manager)