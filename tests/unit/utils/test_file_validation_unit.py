#!/usr/bin/env python3
"""
文件验证工具函数单元测试

测试文件验证相关的纯函数，每个测试只验证一个函数的行为
"""

import unittest
from pathlib import Path
import tempfile
import os

import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent))


def validate_audio_extension(filename):
    """验证音频文件扩展名"""
    if not filename:
        return False
    
    allowed_extensions = {'.mp3', '.wav', '.m4a', '.mp4', '.flac', '.aac', '.ogg'}
    file_ext = Path(filename).suffix.lower()
    return file_ext in allowed_extensions


def validate_file_size(file_size_bytes, max_size_bytes=500*1024*1024):
    """验证文件大小"""
    if file_size_bytes is None or file_size_bytes < 0:
        return False
    return file_size_bytes <= max_size_bytes


def validate_youtube_url(url):
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


def sanitize_filename(filename):
    """清理文件名，移除危险字符"""
    if not filename:
        return "unknown_file"
    
    # 移除路径分隔符和危险字符
    dangerous_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '\n', '\r']
    clean_name = filename
    
    for char in dangerous_chars:
        clean_name = clean_name.replace(char, '_')
    
    # 限制长度
    if len(clean_name) > 200:
        name_part = Path(clean_name).stem[:150]
        ext_part = Path(clean_name).suffix
        clean_name = name_part + ext_part
    
    return clean_name


class TestValidateAudioExtension(unittest.TestCase):
    """测试音频文件扩展名验证函数"""
    
    def test_valid_mp3_extension(self):
        """测试有效的MP3扩展名"""
        result = validate_audio_extension('test.mp3')
        self.assertTrue(result)
    
    def test_valid_wav_extension(self):
        """测试有效的WAV扩展名"""
        result = validate_audio_extension('audio.wav')
        self.assertTrue(result)
    
    def test_valid_case_insensitive(self):
        """测试扩展名大小写不敏感"""
        result = validate_audio_extension('audio.MP3')
        self.assertTrue(result)
    
    def test_invalid_txt_extension(self):
        """测试无效的TXT扩展名"""
        result = validate_audio_extension('document.txt')
        self.assertFalse(result)
    
    def test_no_extension(self):
        """测试无扩展名文件"""
        result = validate_audio_extension('filename')
        self.assertFalse(result)
    
    def test_empty_filename(self):
        """测试空文件名"""
        result = validate_audio_extension('')
        self.assertFalse(result)
    
    def test_none_filename(self):
        """测试None文件名"""
        result = validate_audio_extension(None)
        self.assertFalse(result)


class TestValidateFileSize(unittest.TestCase):
    """测试文件大小验证函数"""
    
    def test_size_within_default_limit(self):
        """测试文件大小在默认限制内"""
        size_100mb = 100 * 1024 * 1024
        result = validate_file_size(size_100mb)
        self.assertTrue(result)
    
    def test_size_equals_default_limit(self):
        """测试文件大小等于默认限制"""
        size_500mb = 500 * 1024 * 1024
        result = validate_file_size(size_500mb)
        self.assertTrue(result)
    
    def test_size_exceeds_default_limit(self):
        """测试文件大小超过默认限制"""
        size_600mb = 600 * 1024 * 1024
        result = validate_file_size(size_600mb)
        self.assertFalse(result)
    
    def test_size_within_custom_limit(self):
        """测试文件大小在自定义限制内"""
        size_50mb = 50 * 1024 * 1024
        limit_100mb = 100 * 1024 * 1024
        result = validate_file_size(size_50mb, limit_100mb)
        self.assertTrue(result)
    
    def test_size_exceeds_custom_limit(self):
        """测试文件大小超过自定义限制"""
        size_150mb = 150 * 1024 * 1024
        limit_100mb = 100 * 1024 * 1024
        result = validate_file_size(size_150mb, limit_100mb)
        self.assertFalse(result)
    
    def test_zero_size(self):
        """测试零字节文件"""
        result = validate_file_size(0)
        self.assertTrue(result)
    
    def test_negative_size(self):
        """测试负数文件大小"""
        result = validate_file_size(-1)
        self.assertFalse(result)
    
    def test_none_size(self):
        """测试None文件大小"""
        result = validate_file_size(None)
        self.assertFalse(result)


class TestValidateYoutubeUrl(unittest.TestCase):
    """测试YouTube URL验证函数"""
    
    def test_valid_watch_url(self):
        """测试有效的watch URL"""
        url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        result = validate_youtube_url(url)
        self.assertTrue(result)
    
    def test_valid_short_url(self):
        """测试有效的短链接"""
        url = 'https://youtu.be/dQw4w9WgXcQ'
        result = validate_youtube_url(url)
        self.assertTrue(result)
    
    def test_valid_embed_url(self):
        """测试有效的嵌入URL"""
        url = 'https://www.youtube.com/embed/dQw4w9WgXcQ'
        result = validate_youtube_url(url)
        self.assertTrue(result)
    
    def test_valid_case_insensitive(self):
        """测试大小写不敏感"""
        url = 'https://WWW.YOUTUBE.COM/watch?v=test'
        result = validate_youtube_url(url)
        self.assertTrue(result)
    
    def test_invalid_non_youtube_url(self):
        """测试非YouTube URL"""
        url = 'https://www.google.com'
        result = validate_youtube_url(url)
        self.assertFalse(result)
    
    def test_invalid_empty_url(self):
        """测试空URL"""
        result = validate_youtube_url('')
        self.assertFalse(result)
    
    def test_invalid_none_url(self):
        """测试None URL"""
        result = validate_youtube_url(None)
        self.assertFalse(result)
    
    def test_invalid_non_string_url(self):
        """测试非字符串URL"""
        result = validate_youtube_url(123)
        self.assertFalse(result)


class TestSanitizeFilename(unittest.TestCase):
    """测试文件名清理函数"""
    
    def test_clean_normal_filename(self):
        """测试普通文件名不变"""
        result = sanitize_filename('normal_file.mp3')
        self.assertEqual(result, 'normal_file.mp3')
    
    def test_remove_path_separators(self):
        """测试移除路径分隔符"""
        result = sanitize_filename('path/to/file.mp3')
        self.assertEqual(result, 'path_to_file.mp3')
    
    def test_remove_dangerous_characters(self):
        """测试移除危险字符"""
        result = sanitize_filename('file*name?.mp3')
        self.assertEqual(result, 'file_name_.mp3')
    
    def test_remove_newlines(self):
        """测试移除换行符"""
        result = sanitize_filename('file\nname\r.mp3')
        self.assertEqual(result, 'file_name_.mp3')
    
    def test_long_filename_truncation(self):
        """测试长文件名截断"""
        long_name = 'a' * 250 + '.mp3'
        result = sanitize_filename(long_name)
        self.assertLessEqual(len(result), 200)
        self.assertTrue(result.endswith('.mp3'))
    
    def test_empty_filename(self):
        """测试空文件名"""
        result = sanitize_filename('')
        self.assertEqual(result, 'unknown_file')
    
    def test_none_filename(self):
        """测试None文件名"""
        result = sanitize_filename(None)
        self.assertEqual(result, 'unknown_file')


if __name__ == '__main__':
    unittest.main()