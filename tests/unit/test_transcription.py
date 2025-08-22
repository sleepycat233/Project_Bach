#!/usr/bin/env python3.11
"""
音频转录模块单元测试
"""

import unittest
import tempfile
import shutil
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import subprocess

# 添加src目录到Python路径
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from core.transcription import (
    TranscriptionService, WhisperKitClient, 
    TranscriptionValidator
)


class TestTranscriptionService(unittest.TestCase):
    """测试转录服务"""
    
    def setUp(self):
        """每个测试前的准备工作"""
        self.test_dir = tempfile.mkdtemp()
        self.whisperkit_config = {
            'model': 'medium',
            'language': 'en',
            'supported_languages': ['en', 'zh']
        }
        
        # 创建测试音频文件
        self.audio_path = Path(self.test_dir) / 'test_audio.mp3'
        self.audio_path.write_bytes(b'fake audio data')
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.test_dir)
    
    @patch('core.transcription.WhisperKitClient')
    @patch('logging.getLogger')
    def test_transcribe_audio_success(self, mock_logger, mock_whisperkit_class):
        """测试成功转录音频"""
        # 设置mock
        mock_whisperkit = MagicMock()
        mock_whisperkit.transcribe.return_value = "This is a test transcription."
        mock_whisperkit_class.return_value = mock_whisperkit
        
        service = TranscriptionService(self.whisperkit_config)
        result = service.transcribe_audio(self.audio_path)
        
        self.assertEqual(result, "This is a test transcription.")
        mock_whisperkit.transcribe.assert_called_once_with(self.audio_path)
    
    @patch('core.transcription.WhisperKitClient')
    @patch('logging.getLogger')
    def test_transcribe_audio_fallback(self, mock_logger, mock_whisperkit_class):
        """测试转录失败时使用备用方案"""
        # 设置WhisperKit失败
        mock_whisperkit = MagicMock()
        mock_whisperkit.transcribe.side_effect = Exception("WhisperKit failed")
        mock_whisperkit_class.return_value = mock_whisperkit
        
        service = TranscriptionService(self.whisperkit_config)
        result = service.transcribe_audio(self.audio_path)
        
        # 应该返回备用方案的结果
        self.assertIn("WhisperKit转录备用方案", result)
        self.assertIn(self.audio_path.name, result)
    
    @patch('logging.getLogger')
    def test_fallback_transcription_meeting(self, mock_logger):
        """测试会议类型的备用转录"""
        meeting_path = Path(self.test_dir) / 'meeting_audio.mp3'
        meeting_path.write_bytes(b'fake audio data')
        
        service = TranscriptionService(self.whisperkit_config)
        result = service._fallback_transcription(meeting_path)
        
        self.assertIn("会议转录", result)
        self.assertIn("张三", result)
        self.assertIn("项目进展", result)
    
    @patch('logging.getLogger')
    def test_fallback_transcription_lecture(self, mock_logger):
        """测试讲座类型的备用转录"""
        lecture_path = Path(self.test_dir) / 'lecture_audio.mp3'
        lecture_path.write_bytes(b'fake audio data')
        
        service = TranscriptionService(self.whisperkit_config)
        result = service._fallback_transcription(lecture_path)
        
        self.assertIn("技术讲座", result)
        self.assertIn("教授", result)
        self.assertIn("人工智能", result)


class TestWhisperKitClient(unittest.TestCase):
    """测试WhisperKit客户端"""
    
    def setUp(self):
        """每个测试前的准备工作"""
        self.test_dir = tempfile.mkdtemp()
        self.config = {
            'model': 'medium',
            'language': 'en',
            'supported_languages': ['en', 'zh']
        }
        self.audio_path = Path(self.test_dir) / 'test.mp3'
        self.audio_path.write_bytes(b'fake audio data')
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.test_dir)
    
    @patch('subprocess.run')
    @patch('core.transcription.LanguageDetector')
    @patch('logging.getLogger')
    def test_transcribe_success(self, mock_logger, mock_detector_class, mock_subprocess):
        """测试成功的WhisperKit转录"""
        # 设置语言检测器
        mock_detector = MagicMock()
        mock_detector.detect_language.return_value = 'en'
        mock_detector_class.return_value = mock_detector
        
        # 设置subprocess返回值
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "This is the transcribed text."
        mock_subprocess.return_value = mock_result
        
        client = WhisperKitClient(self.config)
        result = client.transcribe(self.audio_path)
        
        self.assertEqual(result, "This is the transcribed text.")
        
        # 验证调用了正确的命令
        expected_cmd = [
            "whisperkit-cli",
            "transcribe",
            "--audio-path", str(self.audio_path),
            "--language", "en",
            "--model", "medium",
            "--task", "transcribe"
        ]
        mock_subprocess.assert_called_once()
        actual_cmd = mock_subprocess.call_args[0][0]
        self.assertEqual(actual_cmd, expected_cmd)
    
    @patch('subprocess.run')
    @patch('core.transcription.LanguageDetector')
    @patch('logging.getLogger')
    def test_transcribe_failure(self, mock_logger, mock_detector_class, mock_subprocess):
        """测试WhisperKit转录失败"""
        # 设置语言检测器
        mock_detector = MagicMock()
        mock_detector.detect_language.return_value = 'en'
        mock_detector_class.return_value = mock_detector
        
        # 设置subprocess失败
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "WhisperKit error"
        mock_subprocess.return_value = mock_result
        
        client = WhisperKitClient(self.config)
        
        with self.assertRaises(Exception) as context:
            client.transcribe(self.audio_path)
        
        self.assertIn("WhisperKit执行失败", str(context.exception))
    
    @patch('subprocess.run')
    @patch('core.transcription.LanguageDetector')
    @patch('logging.getLogger')
    def test_transcribe_empty_result(self, mock_logger, mock_detector_class, mock_subprocess):
        """测试WhisperKit返回空结果"""
        # 设置语言检测器
        mock_detector = MagicMock()
        mock_detector.detect_language.return_value = 'en'
        mock_detector_class.return_value = mock_detector
        
        # 设置subprocess返回空结果
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "   "  # 空白内容
        mock_subprocess.return_value = mock_result
        
        client = WhisperKitClient(self.config)
        
        with self.assertRaises(Exception) as context:
            client.transcribe(self.audio_path)
        
        self.assertIn("转录结果为空或过短", str(context.exception))


class TestLanguageDetector(unittest.TestCase):
    """测试语言检测器"""
    
    def setUp(self):
        """每个测试前的准备工作"""
        self.test_dir = tempfile.mkdtemp()
        self.config = {
            'supported_languages': ['en', 'zh']
        }
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.test_dir)
    
    def test_detect_chinese_by_keyword(self):
        """测试通过关键词检测中文"""
        detector = LanguageDetector(self.config)
        
        chinese_files = [
            Path('会议录音.mp3'),
            Path('chinese_lecture.wav'),
            Path('讨论记录.m4a')
        ]
        
        for file_path in chinese_files:
            result = detector.detect_language(file_path, 'en')
            self.assertEqual(result, 'zh', f"Failed for {file_path.name}")
    
    def test_detect_english_by_keyword(self):
        """测试通过关键词检测英文"""
        detector = LanguageDetector(self.config)
        
        english_files = [
            Path('meeting_recording.mp3'),
            Path('english_lecture.wav'),
            Path('class_session.m4a'),
            Path('presentation.wav')
        ]
        
        for file_path in english_files:
            result = detector.detect_language(file_path, 'zh')
            self.assertEqual(result, 'en', f"Failed for {file_path.name}")
    
    def test_detect_chinese_by_characters(self):
        """测试通过中文字符检测中文"""
        detector = LanguageDetector(self.config)
        
        chinese_files = [
            Path('团队会议记录.mp3'),
            Path('技术分享课程.wav')
        ]
        
        for file_path in chinese_files:
            result = detector.detect_language(file_path, 'en')
            self.assertEqual(result, 'zh', f"Failed for {file_path.name}")
    
    def test_detect_default_language(self):
        """测试使用默认语言"""
        detector = LanguageDetector(self.config)
        
        neutral_files = [
            Path('audio123.mp3'),
            Path('recording.wav'),
            Path('file.m4a')
        ]
        
        for file_path in neutral_files:
            result = detector.detect_language(file_path, 'en')
            self.assertEqual(result, 'en', f"Failed for {file_path.name}")
    
    def test_is_supported_language(self):
        """测试支持的语言检查"""
        detector = LanguageDetector(self.config)
        
        self.assertTrue(detector.is_supported_language('en'))
        self.assertTrue(detector.is_supported_language('zh'))
        self.assertFalse(detector.is_supported_language('fr'))
        self.assertFalse(detector.is_supported_language('de'))


class TestTranscriptionValidator(unittest.TestCase):
    """测试转录结果验证器"""
    
    def test_validate_transcript_valid(self):
        """测试有效的转录文本"""
        valid_transcripts = [
            "This is a valid transcription.",
            "这是一个有效的转录文本。",
            "Meeting notes: discuss project timeline and budget.",
            "技术分享：人工智能在软件开发中的应用"
        ]
        
        for transcript in valid_transcripts:
            self.assertTrue(
                TranscriptionValidator.validate_transcript(transcript),
                f"Should be valid: {transcript}"
            )
    
    def test_validate_transcript_invalid(self):
        """测试无效的转录文本"""
        invalid_transcripts = [
            "",  # 空字符串
            None,  # None值
            "   ",  # 只有空白
            "abc",  # 太短
            "\n\t\r   \n",  # 只有空白字符
            123,  # 非字符串类型
        ]
        
        for transcript in invalid_transcripts:
            self.assertFalse(
                TranscriptionValidator.validate_transcript(transcript),
                f"Should be invalid: {transcript}"
            )
    
    def test_clean_transcript(self):
        """测试转录文本清理"""
        test_cases = [
            {
                'input': "  This is  a   test.  \n\n  ",
                'expected': "This is a test."
            },
            {
                'input': "[00:00] >> Speaker: Hello world\nThis is content\n[00:30] >> End",
                'expected': "This is content"
            },
            {
                'input': "Multiple\n\n\nlines\nwith\n\n\nspaces",
                'expected': "Multiple\nlines\nwith\nspaces"
            },
            {
                'input': "",
                'expected': ""
            }
        ]
        
        for case in test_cases:
            result = TranscriptionValidator.clean_transcript(case['input'])
            self.assertEqual(result, case['expected'])


if __name__ == '__main__':
    unittest.main()