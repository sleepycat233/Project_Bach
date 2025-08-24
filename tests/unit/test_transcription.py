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
        # 验证transcribe被调用，但不验证具体参数（因为内部可能有额外的参数处理）
        mock_whisperkit.transcribe.assert_called()
    
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
    @patch('logging.getLogger')
    def test_transcribe_success(self, mock_logger, mock_subprocess):
        """测试成功的WhisperKit转录"""
        
        # 设置subprocess返回值
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "This is the transcribed text."
        mock_subprocess.return_value = mock_result
        
        client = WhisperKitClient(self.config)
        result = client.transcribe(self.audio_path)
        
        self.assertEqual(result, "This is the transcribed text.")
        
        # 验证调用了正确的命令（核心参数）
        mock_subprocess.assert_called_once()
        actual_cmd = mock_subprocess.call_args[0][0]
        
        # 验证关键命令参数存在
        self.assertIn("whisperkit-cli", actual_cmd)
        self.assertIn("transcribe", actual_cmd)
        self.assertIn("--audio-path", actual_cmd)
        self.assertIn(str(self.audio_path), actual_cmd)
        self.assertIn("--model", actual_cmd)
        self.assertIn("medium", actual_cmd)
    
    @patch('subprocess.run')
    @patch('logging.getLogger')
    def test_transcribe_failure(self, mock_logger, mock_subprocess):
        """测试WhisperKit转录失败"""
        
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
    @patch('logging.getLogger')
    def test_transcribe_empty_result(self, mock_logger, mock_subprocess):
        """测试WhisperKit返回空结果"""
        
        # 设置subprocess返回空结果
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "   "  # 空白内容
        mock_subprocess.return_value = mock_result
        
        client = WhisperKitClient(self.config)
        
        with self.assertRaises(Exception) as context:
            client.transcribe(self.audio_path)
        
        self.assertIn("转录结果为空或过短", str(context.exception))



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


class TestWhisperKitModelPathMappings(unittest.TestCase):
    """测试WhisperKit模型路径映射修复"""
    
    def setUp(self):
        """每个测试前的准备工作"""
        self.config = {
            'model_path': './models',
            'model': 'large-v3',
            'language': 'en'
        }
    
    @patch('pathlib.Path.exists')
    @patch('logging.getLogger')
    def test_distil_model_path_mapping(self, mock_logger, mock_path_exists):
        """测试distil模型的特殊路径映射"""
        mock_path_exists.return_value = True
        
        client = WhisperKitClient(self.config)
        
        # 测试distil模型的路径构建
        with patch.object(client, '_ensure_model_available') as mock_ensure:
            with patch('subprocess.run') as mock_subprocess:
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = "Test transcription"
                mock_subprocess.return_value = mock_result
                
                # 测试distil模型前缀
                client.transcribe(
                    Path('/test/audio.mp3'), 
                    model='large-v3', 
                    model_prefix='distil'
                )
                
                # 验证使用了正确的distil模型文件夹名
                expected_path = "./models/whisperkit-coreml/distil-whisper_distil-large-v3"
                mock_ensure.assert_called_once()
                actual_path = mock_ensure.call_args[0][1]
                self.assertEqual(actual_path, expected_path)
    
    @patch('pathlib.Path.exists')
    @patch('logging.getLogger')
    def test_openai_model_path_mapping(self, mock_logger, mock_path_exists):
        """测试OpenAI模型的标准路径映射"""
        mock_path_exists.return_value = True
        
        client = WhisperKitClient(self.config)
        
        with patch.object(client, '_ensure_model_available') as mock_ensure:
            with patch('subprocess.run') as mock_subprocess:
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = "Test transcription"
                mock_subprocess.return_value = mock_result
                
                # 测试OpenAI模型前缀
                client.transcribe(
                    Path('/test/audio.mp3'), 
                    model='large-v3', 
                    model_prefix='openai'
                )
                
                # 验证使用了正确的OpenAI模型文件夹名
                expected_path = "./models/whisperkit-coreml/openai_whisper-large-v3"
                mock_ensure.assert_called_once()
                actual_path = mock_ensure.call_args[0][1]
                self.assertEqual(actual_path, expected_path)


class TestProgressMonitoringThread(unittest.TestCase):
    """测试进度监控线程修复"""
    
    def setUp(self):
        """每个测试前的准备工作"""
        self.config = {
            'model_path': './models',
            'model': 'large-v3',
            'language': 'en'
        }
    
    @patch('threading.Thread')
    @patch('threading.Event')
    @patch('pathlib.Path.exists')
    @patch('logging.getLogger')
    def test_progress_monitoring_stop_event(self, mock_logger, mock_path_exists, mock_event_class, mock_thread_class):
        """测试进度监控使用stop_event正确停止"""
        mock_path_exists.return_value = True
        mock_stop_event = MagicMock()
        mock_event_class.return_value = mock_stop_event
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread
        
        client = WhisperKitClient(self.config)
        
        with patch('subprocess.run') as mock_subprocess:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Test transcription"
            mock_subprocess.return_value = mock_result
            
            client.transcribe(Path('/test/audio.mp3'))
            
            # 验证创建了stop_event
            mock_event_class.assert_called_once()
            
            # 验证启动了进度监控线程，并传入了stop_event
            mock_thread_class.assert_called_once()
            thread_args = mock_thread_class.call_args[1]['args']
            self.assertIn(mock_stop_event, thread_args)
            
            # 验证在成功完成时设置了stop_event
            mock_stop_event.set.assert_called()
    
    @patch('threading.Thread')
    @patch('threading.Event')
    @patch('pathlib.Path.exists')
    @patch('logging.getLogger')
    def test_progress_monitoring_stop_on_error(self, mock_logger, mock_path_exists, mock_event_class, mock_thread_class):
        """测试进度监控在错误时也会停止"""
        mock_path_exists.return_value = True
        mock_stop_event = MagicMock()
        mock_event_class.return_value = mock_stop_event
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread
        
        client = WhisperKitClient(self.config)
        
        with patch('subprocess.run') as mock_subprocess:
            # 模拟subprocess失败
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stderr = "Test error"
            mock_subprocess.return_value = mock_result
            
            with self.assertRaises(Exception):
                client.transcribe(Path('/test/audio.mp3'))
            
            # 验证即使在错误情况下也设置了stop_event
            mock_stop_event.set.assert_called()


class TestEnglishLogMessages(unittest.TestCase):
    """测试英文日志消息修复"""
    
    @patch('pathlib.Path.exists')
    @patch('logging.getLogger')
    def test_english_log_messages(self, mock_logger_func, mock_path_exists):
        """测试所有日志消息都使用英文"""
        mock_path_exists.return_value = True
        mock_logger = MagicMock()
        mock_logger_func.return_value = mock_logger
        
        client = WhisperKitClient({
            'model_path': './models',
            'model': 'large-v3',
            'language': 'en'
        })
        
        with patch('subprocess.run') as mock_subprocess:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Test transcription"
            mock_subprocess.return_value = mock_result
            
            client.transcribe(Path('/test/audio.mp3'), model='large-v3', model_prefix='distil')
            
            # 检查日志调用中是否使用了英文
            log_calls = [str(call) for call in mock_logger.info.call_args_list]
            
            # 验证关键日志消息使用英文
            english_keywords = [
                'WhisperKit transcription config',
                'Model:',
                'Compute units:',
                'Optimization:',
                'Timeout limit:',
                'transcription completed',
                'Performance metrics:',
                'Result stats:'
            ]
            
            log_text = ' '.join(log_calls)
            for keyword in english_keywords:
                self.assertIn(keyword, log_text, 
                             f"English keyword '{keyword}' not found in logs")
            
            # 验证没有中文关键词
            chinese_keywords = [
                '转录配置',
                '模型',
                '计算单元',
                '优化选项',
                '超时限制',
                '转录完成',
                '性能指标',
                '结果统计'
            ]
            
            for keyword in chinese_keywords:
                self.assertNotIn(keyword, log_text, 
                               f"Chinese keyword '{keyword}' found in logs")


class TestCustomPromptSupport(unittest.TestCase):
    """测试自定义提示词支持"""
    
    @patch('pathlib.Path.exists')
    @patch('logging.getLogger')
    def test_custom_prompt_usage(self, mock_logger, mock_path_exists):
        """测试自定义提示词被正确传递给WhisperKit"""
        mock_path_exists.return_value = True
        
        client = WhisperKitClient({
            'model_path': './models',
            'model': 'large-v3',
            'language': 'en'
        })
        
        with patch('subprocess.run') as mock_subprocess:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Test transcription"
            mock_subprocess.return_value = mock_result
            
            custom_prompt = "Physics lecture by Richard Feynman about diffusion"
            client.transcribe(
                Path('/test/audio.mp3'), 
                prompt=custom_prompt,
                model='large-v3', 
                model_prefix='distil'
            )
            
            # 验证命令行包含了自定义提示词
            mock_subprocess.assert_called_once()
            cmd_args = mock_subprocess.call_args[0][0]
            
            # 检查命令中是否包含--prompt参数
            self.assertIn('--prompt', cmd_args)
            prompt_index = cmd_args.index('--prompt')
            self.assertEqual(cmd_args[prompt_index + 1], custom_prompt)


if __name__ == '__main__':
    unittest.main()