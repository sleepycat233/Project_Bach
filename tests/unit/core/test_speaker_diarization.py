#!/usr/bin/env python3.11
"""
Speaker Diarization服务单元测试
"""

import unittest
import tempfile
import shutil
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import numpy as np

# 添加src目录到Python路径
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src'))

from core.speaker_diarization import SpeakerDiarization


class TestSpeakerDiarization(unittest.TestCase):
    """测试Speaker Diarization服务"""
    
    def setUp(self):
        """每个测试前的准备工作"""
        self.test_dir = tempfile.mkdtemp()
        self.diarization_config = {
            'provider': 'pyannote',
            'max_speakers': 6,
            'min_segment_duration': 1.0,
            'model_path': f'{self.test_dir}/models/diarization',
            'content_type_defaults': {
                'lecture': False,
                'meeting': True,
                'lecture_subcategories': {
                    'cs': False,
                    'seminar': True,
                    'workshop': True
                },
                'meeting_subcategories': {
                    'standup': True,
                    'review': True,
                    'planning': True,
                    'interview': True,
                    'oneonone': False
                }
            },
            'output_format': {
                'group_by_speaker': True,
                'timestamp_precision': 1,
                'include_confidence': False
            }
        }
        
        self.huggingface_config = {
            'token': 'fake_hf_token'
        }
        
        # 创建测试音频文件
        self.audio_path = Path(self.test_dir) / 'test_audio.mp3'
        self.audio_path.write_bytes(b'fake audio data')
        
        # 创建模型目录
        os.makedirs(self.diarization_config['model_path'], exist_ok=True)
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.test_dir)
    
    def test_should_enable_diarization_lecture_default(self):
        """测试讲座类型默认不启用diarization"""
        service = SpeakerDiarization(self.diarization_config, self.huggingface_config)
        
        result = service.should_enable_diarization('lecture', None)
        self.assertFalse(result)
        
        result = service.should_enable_diarization('lecture', 'cs')
        self.assertFalse(result)
        
        result = service.should_enable_diarization('lecture', 'seminar')
        self.assertTrue(result)
    
    def test_should_enable_diarization_meeting_default(self):
        """测试会议类型默认启用diarization"""
        service = SpeakerDiarization(self.diarization_config, self.huggingface_config)
        
        result = service.should_enable_diarization('meeting', None)
        self.assertTrue(result)
        
        result = service.should_enable_diarization('meeting', 'standup')
        self.assertTrue(result)
        
        result = service.should_enable_diarization('meeting', 'oneonone')
        self.assertFalse(result)
    
    def test_should_enable_diarization_unknown_type(self):
        """测试未知内容类型默认行为"""
        service = SpeakerDiarization(self.diarization_config, self.huggingface_config)
        
        result = service.should_enable_diarization('unknown', None)
        self.assertFalse(result)  # 默认不启用
    
    @patch('core.speaker_diarization.Pipeline')
    @patch('os.environ')
    def test_diarize_audio_success(self, mock_environ, mock_pipeline_class):
        """测试成功的说话人分离"""
        # 设置环境变量
        mock_environ.get.return_value = 'fake_hf_token'
        
        # 模拟pyannote pipeline
        mock_pipeline = MagicMock()
        mock_diarization_result = MagicMock()
        
        # 模拟diarization结果
        mock_segments = [
            MagicMock(start=0.0, end=8.5, label='Speaker_A'),
            MagicMock(start=8.5, end=12.3, label='Speaker_B'),
            MagicMock(start=12.3, end=18.0, label='Speaker_A')
        ]
        mock_diarization_result.itertracks.return_value = [
            (segment, None, segment.label) for segment in mock_segments
        ]
        
        mock_pipeline.return_value = mock_diarization_result
        mock_pipeline_class.from_pretrained.return_value = mock_pipeline
        
        service = SpeakerDiarization(self.diarization_config, self.huggingface_config)
        result = service.diarize_audio(self.audio_path)
        
        # 验证结果格式
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)
        
        # 验证第一个段落
        first_segment = result[0]
        self.assertEqual(first_segment['speaker'], 'Speaker_A')
        self.assertEqual(first_segment['start'], 0.0)
        self.assertEqual(first_segment['end'], 8.5)
        
        # 验证pipeline被正确调用
        mock_pipeline_class.from_pretrained.assert_called_once()
        mock_pipeline.assert_called_once_with(str(self.audio_path))
    
    def test_merge_with_transcription_group_by_speaker(self):
        """测试合并转录结果 - 按说话人分组模式"""
        service = SpeakerDiarization(self.diarization_config, self.huggingface_config)
        
        # 模拟转录结果
        transcription = {
            'text': 'Hello everyone. Today we will discuss. Yes, that sounds good. Let me start.',
            'chunks': [
                {'timestamp': [0.0, 3.5], 'text': 'Hello everyone.'},
                {'timestamp': [3.5, 8.0], 'text': 'Today we will discuss.'},
                {'timestamp': [8.0, 10.5], 'text': 'Yes, that sounds good.'},
                {'timestamp': [10.5, 15.0], 'text': 'Let me start.'}
            ]
        }
        
        # 模拟说话人分离结果
        speaker_segments = [
            {'speaker': 'Speaker_A', 'start': 0.0, 'end': 8.2},
            {'speaker': 'Speaker_B', 'start': 8.2, 'end': 10.8},
            {'speaker': 'Speaker_A', 'start': 10.8, 'end': 15.0}
        ]
        
        result = service.merge_with_transcription(
            transcription, speaker_segments, group_by_speaker=True
        )
        
        # 验证按说话人分组的结果
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)  # 3个说话人段落
        
        # 验证第一个说话人段落（合并了两个chunks）
        first_group = result[0]
        self.assertEqual(first_group['speaker'], 'Speaker_A')
        self.assertIn('Hello everyone', first_group['text'])
        self.assertIn('Today we will discuss', first_group['text'])
        self.assertEqual(first_group['timestamp'][0], 0.0)
        self.assertEqual(first_group['timestamp'][1], 8.0)
    
    def test_merge_with_transcription_chunk_level(self):
        """测试合并转录结果 - chunk级别模式"""
        service = SpeakerDiarization(self.diarization_config, self.huggingface_config)
        
        # 模拟转录结果
        transcription = {
            'text': 'Hello everyone. Today we will discuss.',
            'chunks': [
                {'timestamp': [0.0, 3.5], 'text': 'Hello everyone.'},
                {'timestamp': [3.5, 8.0], 'text': 'Today we will discuss.'}
            ]
        }
        
        # 模拟说话人分离结果
        speaker_segments = [
            {'speaker': 'Speaker_A', 'start': 0.0, 'end': 8.2}
        ]
        
        result = service.merge_with_transcription(
            transcription, speaker_segments, group_by_speaker=False
        )
        
        # 验证chunk级别的结果
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)  # 保持原始chunk数量
        
        # 验证每个chunk都分配了说话人
        for chunk in result:
            self.assertEqual(chunk['speaker'], 'Speaker_A')
            self.assertIn('timestamp', chunk)
            self.assertIn('text', chunk)
    
    def test_align_timestamps_with_speakers(self):
        """测试时间戳对齐算法"""
        service = SpeakerDiarization(self.diarization_config, self.huggingface_config)
        
        # 模拟ASR chunks
        chunks = [
            {'timestamp': [0.0, 3.2], 'text': '你好，我是张三'},
            {'timestamp': [3.2, 8.5], 'text': '今天天气真不错'},
            {'timestamp': [8.5, 12.1], 'text': '是的，很晴朗'},
            {'timestamp': [12.1, 18.3], 'text': '我们开始讨论项目吧'}
        ]
        
        # 模拟说话人段落
        speaker_segments = [
            {'speaker': 'Speaker_A', 'start': 0.0, 'end': 8.7},
            {'speaker': 'Speaker_B', 'start': 8.7, 'end': 12.3},
            {'speaker': 'Speaker_A', 'start': 12.3, 'end': 18.3}
        ]
        
        # 测试内部对齐算法
        aligned_chunks = service._align_timestamps_with_speakers(chunks, speaker_segments)
        
        # 验证对齐结果
        self.assertEqual(len(aligned_chunks), 4)
        
        # 验证前两个chunk分配给Speaker_A
        self.assertEqual(aligned_chunks[0]['speaker'], 'Speaker_A')
        self.assertEqual(aligned_chunks[1]['speaker'], 'Speaker_A')
        
        # 验证第三个chunk分配给Speaker_B
        self.assertEqual(aligned_chunks[2]['speaker'], 'Speaker_B')
        
        # 验证第四个chunk分配给Speaker_A
        self.assertEqual(aligned_chunks[3]['speaker'], 'Speaker_A')
    
    def test_group_by_speaker_mode(self):
        """测试按说话人分组模式"""
        service = SpeakerDiarization(self.diarization_config, self.huggingface_config)
        
        # 模拟对齐后的chunks
        aligned_chunks = [
            {'speaker': 'Speaker_A', 'timestamp': [0.0, 3.2], 'text': 'Hello'},
            {'speaker': 'Speaker_A', 'timestamp': [3.2, 8.5], 'text': 'How are you?'},
            {'speaker': 'Speaker_B', 'timestamp': [8.5, 12.1], 'text': 'Fine, thanks'},
            {'speaker': 'Speaker_A', 'timestamp': [12.1, 18.3], 'text': 'Great to hear'}
        ]
        
        grouped_result = service._group_by_speaker_mode(aligned_chunks)
        
        # 验证分组结果
        self.assertEqual(len(grouped_result), 3)  # 3个说话人段落
        
        # 验证第一个分组（合并了前两个chunks）
        first_group = grouped_result[0]
        self.assertEqual(first_group['speaker'], 'Speaker_A')
        self.assertIn('Hello', first_group['text'])
        self.assertIn('How are you?', first_group['text'])
        self.assertEqual(first_group['timestamp'][0], 0.0)
        self.assertEqual(first_group['timestamp'][1], 8.5)
        
        # 验证第二个分组
        second_group = grouped_result[1]
        self.assertEqual(second_group['speaker'], 'Speaker_B')
        self.assertEqual(second_group['text'], 'Fine, thanks')
        
        # 验证第三个分组
        third_group = grouped_result[2]
        self.assertEqual(third_group['speaker'], 'Speaker_A')
        self.assertEqual(third_group['text'], 'Great to hear')
    
    def test_chunk_level_mode(self):
        """测试chunk级别模式"""
        service = SpeakerDiarization(self.diarization_config, self.huggingface_config)
        
        # 模拟对齐后的chunks
        aligned_chunks = [
            {'speaker': 'Speaker_A', 'timestamp': [0.0, 3.2], 'text': 'Hello'},
            {'speaker': 'Speaker_B', 'timestamp': [3.2, 8.5], 'text': 'Hi there'}
        ]
        
        chunk_result = service._chunk_level_mode(aligned_chunks)
        
        # 验证chunk级别结果（应该保持不变）
        self.assertEqual(len(chunk_result), 2)
        self.assertEqual(chunk_result[0]['speaker'], 'Speaker_A')
        self.assertEqual(chunk_result[1]['speaker'], 'Speaker_B')
        
        # 验证保持了原始的时间戳精度
        self.assertEqual(chunk_result[0]['timestamp'], [0.0, 3.2])
        self.assertEqual(chunk_result[1]['timestamp'], [3.2, 8.5])
    
    @patch('core.speaker_diarization.Pipeline')
    def test_diarization_failure(self, mock_pipeline_class):
        """测试diarization失败处理"""
        # 设置Pipeline抛出异常
        mock_pipeline_class.from_pretrained.side_effect = Exception("Model loading failed")
        
        service = SpeakerDiarization(self.diarization_config, self.huggingface_config)
        
        with self.assertRaises(Exception) as context:
            service.diarize_audio(self.audio_path)
        
        self.assertIn("Speaker diarization失败", str(context.exception))
        self.assertIn("Model loading failed", str(context.exception))
    
    def test_invalid_audio_path(self):
        """测试无效音频路径"""
        service = SpeakerDiarization(self.diarization_config, self.huggingface_config)
        invalid_path = Path(self.test_dir) / 'nonexistent.mp3'
        
        with self.assertRaises(Exception) as context:
            service.diarize_audio(invalid_path)
        
        self.assertIn("音频文件不存在", str(context.exception))
    
    def test_output_format_configuration(self):
        """测试输出格式配置"""
        # 测试不同的输出格式配置
        custom_config = self.diarization_config.copy()
        custom_config['output_format'] = {
            'group_by_speaker': False,
            'timestamp_precision': 2,
            'include_confidence': True
        }
        
        service = SpeakerDiarization(custom_config, self.huggingface_config)
        
        # 验证配置被正确加载
        self.assertFalse(service.config['output_format']['group_by_speaker'])
        self.assertEqual(service.config['output_format']['timestamp_precision'], 2)
        self.assertTrue(service.config['output_format']['include_confidence'])
    
    def test_max_speakers_configuration(self):
        """测试最大说话人数配置"""
        service = SpeakerDiarization(self.diarization_config, self.huggingface_config)
        
        # 验证最大说话人数配置
        self.assertEqual(service.config['max_speakers'], 6)
        
        # 测试自定义最大说话人数
        custom_config = self.diarization_config.copy()
        custom_config['max_speakers'] = 4
        
        custom_service = SpeakerDiarization(custom_config, self.huggingface_config)
        self.assertEqual(custom_service.config['max_speakers'], 4)


class TestSpeakerDiarizationIntegration(unittest.TestCase):
    """Speaker Diarization集成测试"""
    
    def setUp(self):
        """准备集成测试环境"""
        self.test_dir = tempfile.mkdtemp()
        self.diarization_config = {
            'provider': 'pyannote',
            'max_speakers': 2,  # 使用较小的值进行快速测试
            'min_segment_duration': 1.0,
            'model_path': f'{self.test_dir}/models/diarization',
            'content_type_defaults': {
                'meeting': True
            }
        }
        self.huggingface_config = {
            'token': os.getenv('HUGGINGFACE_TOKEN', 'fake_token')
        }
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.test_dir)
    
    @unittest.skipUnless(
        os.getenv('TEST_DIARIZATION_INTEGRATION', 'false').lower() == 'true',
        "需要设置TEST_DIARIZATION_INTEGRATION=true和HUGGINGFACE_TOKEN来运行集成测试"
    )
    def test_real_diarization_pipeline(self):
        """真实的pyannote.audio diarization测试（需要HuggingFace token）"""
        from pyannote.audio import Pipeline
        
        # 创建一个小的测试音频文件（实际应用中需要真实音频）
        audio_path = Path(self.test_dir) / 'test_audio.wav'
        # 在真实测试中，这里应该是真实的音频文件
        
        service = SpeakerDiarization(self.diarization_config, self.huggingface_config)
        
        # 由于没有真实音频和HF token，这个测试主要验证集成没有导入错误
        with self.assertRaises(Exception):
            # 预期会失败，因为没有真实音频文件或HF token
            service.diarize_audio(audio_path)


if __name__ == '__main__':
    unittest.main()