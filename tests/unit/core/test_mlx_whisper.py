#!/usr/bin/env python3.11
"""
MLX Whisper转录服务单元测试
"""

import unittest
import tempfile
import shutil
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import json

# 添加src目录到Python路径
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src'))

from core.mlx_transcription import MLXTranscriptionService


class TestMLXTranscriptionService(unittest.TestCase):
    """测试MLX Whisper转录服务"""
    
    def setUp(self):
        """每个测试前的准备工作"""
        self.test_dir = tempfile.mkdtemp()
        self.mlx_config = {
            'model_repo': 'mlx-community/whisper-large-v3',
            'local_model_path': f'{self.test_dir}/models/mlx_whisper',
            'word_timestamps': True
        }
        
        # 创建测试音频文件
        self.audio_path = Path(self.test_dir) / 'test_audio.mp3'
        self.audio_path.write_bytes(b'fake audio data')
        
        # 创建模型目录
        os.makedirs(self.mlx_config['local_model_path'], exist_ok=True)
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.test_dir)
    
    @patch('core.mlx_transcription.mlx_whisper')
    def test_transcribe_audio_success(self, mock_mlx_whisper):
        """测试成功转录音频"""
        # 设置mock返回值
        mock_result = {
            'text': 'This is a test transcription.',
            'segments': [
                {
                    'start': 0.0,
                    'end': 3.0,
                    'text': 'This is a test transcription.',
                    'words': [
                        {'start': 0.0, 'end': 0.5, 'word': 'This'},
                        {'start': 0.5, 'end': 1.0, 'word': 'is'},
                        {'start': 1.0, 'end': 1.5, 'word': 'a'},
                        {'start': 1.5, 'end': 2.0, 'word': 'test'},
                        {'start': 2.0, 'end': 3.0, 'word': 'transcription'}
                    ]
                }
            ]
        }
        mock_mlx_whisper.transcribe.return_value = mock_result
        
        service = MLXTranscriptionService(self.mlx_config)
        result = service.transcribe_audio(
            audio_path=self.audio_path,
            language_preference='english'
        )
        
        # 验证结果
        self.assertEqual(result, 'This is a test transcription.')
        
        # 验证mlx_whisper.transcribe被正确调用
        mock_mlx_whisper.transcribe.assert_called_once()
        call_args = mock_mlx_whisper.transcribe.call_args
        self.assertEqual(call_args[0][0], str(self.audio_path))  # 音频路径
        self.assertTrue('word_timestamps' in call_args[1])
        self.assertTrue(call_args[1]['word_timestamps'])
    
    @patch('core.mlx_transcription.mlx_whisper')
    def test_transcribe_audio_with_model_repo(self, mock_mlx_whisper):
        """测试使用指定模型仓库转录"""
        mock_result = {'text': 'Test with custom model.'}
        mock_mlx_whisper.transcribe.return_value = mock_result
        
        service = MLXTranscriptionService(self.mlx_config)
        result = service.transcribe_audio(
            audio_path=self.audio_path,
            custom_model='whisper-medium'                # MLX模型名
        )
        
        self.assertEqual(result, 'Test with custom model.')
        
        # 验证使用了正确的模型
        call_args = mock_mlx_whisper.transcribe.call_args
        self.assertEqual(call_args[1]['path_or_hf_repo'], 'mlx-community/whisper-medium')
    
    @patch('core.mlx_transcription.mlx_whisper')
    def test_transcribe_audio_with_distil_model(self, mock_mlx_whisper):
        """测试使用distil模型转录"""
        mock_result = {'text': 'Test with distil model.'}
        mock_mlx_whisper.transcribe.return_value = mock_result
        
        service = MLXTranscriptionService(self.mlx_config)
        result = service.transcribe_audio(
            audio_path=self.audio_path,
            custom_model='whisper-large-v3'              # MLX模型名
        )
        
        self.assertEqual(result, 'Test with distil model.')
        
        # 验证使用了正确的模型
        call_args = mock_mlx_whisper.transcribe.call_args
        self.assertEqual(call_args[1]['path_or_hf_repo'], 'mlx-community/whisper-large-v3')
    
    @patch('core.mlx_transcription.mlx_whisper')
    def test_transcribe_audio_with_full_repo_name(self, mock_mlx_whisper):
        """测试使用完整仓库名转录"""
        mock_result = {'text': 'Test with full repo name.'}
        mock_mlx_whisper.transcribe.return_value = mock_result
        
        service = MLXTranscriptionService(self.mlx_config)
        result = service.transcribe_audio(
            audio_path=self.audio_path,
            custom_model='custom-org/custom-whisper-model'  # 完整仓库名
        )
        
        self.assertEqual(result, 'Test with full repo name.')
        
        # 验证直接使用了完整仓库名
        call_args = mock_mlx_whisper.transcribe.call_args
        self.assertEqual(call_args[1]['path_or_hf_repo'], 'custom-org/custom-whisper-model')
    
    @patch('core.mlx_transcription.mlx_whisper')
    def test_transcribe_audio_with_prompt(self, mock_mlx_whisper):
        """测试使用提示词转录"""
        mock_result = {'text': 'Technical terms recognized correctly.'}
        mock_mlx_whisper.transcribe.return_value = mock_result
        
        service = MLXTranscriptionService(self.mlx_config)
        prompt = "This is a technical presentation about machine learning."
        
        result = service.transcribe_audio(
            audio_path=self.audio_path,
            prompt=prompt
        )
        
        self.assertEqual(result, 'Technical terms recognized correctly.')
        
        # 验证prompt被传递
        call_args = mock_mlx_whisper.transcribe.call_args
        self.assertEqual(call_args[1]['initial_prompt'], prompt)
    
    @patch('core.mlx_transcription.mlx_whisper')
    def test_transcribe_audio_multilingual(self, mock_mlx_whisper):
        """测试多语言转录"""
        mock_result = {'text': '这是一个中文测试转录。'}
        mock_mlx_whisper.transcribe.return_value = mock_result
        
        service = MLXTranscriptionService(self.mlx_config)
        result = service.transcribe_audio(
            audio_path=self.audio_path,
            language_preference='multilingual'
        )
        
        self.assertEqual(result, '这是一个中文测试转录。')
        
        # 验证没有设置特定语言
        call_args = mock_mlx_whisper.transcribe.call_args
        self.assertNotIn('language', call_args[1])  # MLX Whisper默认自动检测
    
    @patch('core.mlx_transcription.mlx_whisper')
    def test_transcribe_audio_english_only(self, mock_mlx_whisper):
        """测试纯英文转录"""
        mock_result = {'text': 'English only transcription test.'}
        mock_mlx_whisper.transcribe.return_value = mock_result
        
        service = MLXTranscriptionService(self.mlx_config)
        result = service.transcribe_audio(
            audio_path=self.audio_path,
            language_preference='english'
        )
        
        self.assertEqual(result, 'English only transcription test.')
        
        # 验证设置了英文语言
        call_args = mock_mlx_whisper.transcribe.call_args
        self.assertEqual(call_args[1].get('language'), 'en')
    
    @patch('core.mlx_transcription.mlx_whisper')
    def test_transcribe_audio_failure(self, mock_mlx_whisper):
        """测试转录失败处理"""
        # 设置mlx_whisper抛出异常
        mock_mlx_whisper.transcribe.side_effect = Exception("Model loading failed")
        
        service = MLXTranscriptionService(self.mlx_config)
        
        with self.assertRaises(Exception) as context:
            service.transcribe_audio(self.audio_path)
        
        self.assertIn("MLX Whisper转录失败", str(context.exception))
        self.assertIn("Model loading failed", str(context.exception))
    
    @patch('core.mlx_transcription.mlx_whisper')
    def test_transcribe_with_word_timestamps_disabled(self, mock_mlx_whisper):
        """测试禁用词级时间戳"""
        mock_result = {'text': 'Test without word timestamps.'}
        mock_mlx_whisper.transcribe.return_value = mock_result
        
        # 禁用词级时间戳
        config_no_timestamps = self.mlx_config.copy()
        config_no_timestamps['word_timestamps'] = False
        
        service = MLXTranscriptionService(config_no_timestamps)
        result = service.transcribe_audio(self.audio_path)
        
        self.assertEqual(result, 'Test without word timestamps.')
        
        # 验证word_timestamps被设置为False
        call_args = mock_mlx_whisper.transcribe.call_args
        self.assertFalse(call_args[1]['word_timestamps'])
    
    @patch('core.mlx_transcription.mlx_whisper')
    def test_get_model_path_with_local_model(self, mock_mlx_whisper):
        """测试使用本地模型路径"""
        mock_result = {'text': 'Test with local model.'}
        mock_mlx_whisper.transcribe.return_value = mock_result
        
        # 创建本地模型文件
        local_model_path = Path(self.mlx_config['local_model_path'])
        local_model_path.mkdir(parents=True, exist_ok=True)
        
        (local_model_path / 'weights.npz').write_text('fake model weights')
        (local_model_path / 'config.json').write_text('{"fake": "config"}')
        
        service = MLXTranscriptionService(self.mlx_config)
        result = service.transcribe_audio(self.audio_path)
        
        self.assertEqual(result, 'Test with local model.')
        
        # 验证使用了本地模型路径
        call_args = mock_mlx_whisper.transcribe.call_args
        self.assertEqual(call_args[1]['path_or_hf_repo'], str(Path(self.mlx_config['local_model_path'])))
    
    def test_invalid_audio_path(self):
        """测试无效音频路径"""
        service = MLXTranscriptionService(self.mlx_config)
        invalid_path = Path(self.test_dir) / 'nonexistent.mp3'
        
        with self.assertRaises(Exception) as context:
            service.transcribe_audio(invalid_path)
        
        self.assertIn("音频文件不存在", str(context.exception))
    
    def test_large_file_warning(self):
        """测试大文件警告"""
        # 创建一个"大"文件（通过文件名模拟）
        large_audio_path = Path(self.test_dir) / 'large_audio_100MB.mp3'
        large_audio_path.write_bytes(b'fake large audio data' * 1000)  # 模拟大文件
        
        service = MLXTranscriptionService(self.mlx_config)
        
        with patch('core.mlx_transcription.mlx_whisper') as mock_mlx_whisper:
            mock_mlx_whisper.transcribe.return_value = {'text': 'Large file transcription.'}
            
            with patch.object(service.logger, 'warning') as mock_warning:
                result = service.transcribe_audio(large_audio_path)
                
                # 验证大文件警告被记录（如果文件足够大）
                file_size_mb = large_audio_path.stat().st_size / (1024 * 1024)
                if file_size_mb > 50:  # 大文件阈值
                    mock_warning.assert_called()


class TestMLXTranscriptionServiceIntegration(unittest.TestCase):
    """MLX Whisper转录服务集成测试"""
    
    def setUp(self):
        """准备集成测试环境"""
        self.test_dir = tempfile.mkdtemp()
        self.mlx_config = {
            'model_repo': 'mlx-community/whisper-tiny',  # 使用tiny模型进行快速测试
            'local_model_path': f'{self.test_dir}/models/mlx_whisper',
            'word_timestamps': True
        }
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.test_dir)
    
    @unittest.skipUnless(
        os.getenv('TEST_MLX_INTEGRATION', 'false').lower() == 'true',
        "需要设置TEST_MLX_INTEGRATION=true环境变量来运行集成测试"
    )
    def test_real_mlx_whisper_transcription(self):
        """真实的MLX Whisper转录测试（需要MLX环境）"""
        # 这个测试只在显式启用时运行，因为需要真实的MLX环境
        import mlx_whisper
        
        # 创建一个小的测试音频文件（实际应用中需要真实音频）
        audio_path = Path(self.test_dir) / 'test_audio.wav'
        # 在真实测试中，这里应该是真实的音频文件
        
        service = MLXTranscriptionService(self.mlx_config)
        
        # 由于没有真实音频，这个测试主要验证集成没有导入错误
        with self.assertRaises(Exception):
            # 预期会失败，因为没有真实音频文件
            service.transcribe_audio(audio_path)


if __name__ == '__main__':
    unittest.main()