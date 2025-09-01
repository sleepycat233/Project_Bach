#!/usr/bin/env python3.11
"""
MLX Whisper + Speaker Diarization 集成测试
验证转录服务与说话人分离服务的协同工作
"""

import unittest
import tempfile
import shutil
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# 添加src目录到Python路径
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from core.mlx_transcription import MLXTranscriptionService
from core.speaker_diarization import SpeakerDiarization, DiarizationIntegrator


class TestMLXDiarizationIntegration(unittest.TestCase):
    """测试MLX Whisper与Speaker Diarization的集成"""
    
    def setUp(self):
        """准备集成测试环境"""
        self.test_dir = tempfile.mkdtemp()
        
        # MLX Whisper配置
        self.mlx_config = {
            'model_repo': 'mlx-community/whisper-large-v3',
            'local_model_path': f'{self.test_dir}/models/mlx_whisper',
            'word_timestamps': True
        }
        
        # Speaker Diarization配置
        self.diarization_config = {
            'provider': 'pyannote',
            'max_speakers': 4,
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
        self.audio_path = Path(self.test_dir) / 'test_meeting.mp3'
        self.audio_path.write_bytes(b'fake audio data for meeting')
        
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.test_dir)
    
    @patch('core.mlx_transcription.mlx_whisper')
    @patch('core.speaker_diarization.Pipeline')
    @patch('os.environ')
    def test_meeting_with_diarization_enabled(self, mock_environ, mock_pipeline_class, mock_mlx_whisper):
        """测试会议类型音频启用说话人分离"""
        # 设置环境变量
        mock_environ.get.return_value = 'fake_hf_token'
        
        # 模拟MLX Whisper转录结果
        mock_transcription_result = {
            'text': 'Hello everyone. How is the project going? It is going well. Great to hear.',
            'chunks': [
                {'timestamp': [0.0, 2.5], 'text': 'Hello everyone.'},
                {'timestamp': [2.5, 5.0], 'text': 'How is the project going?'},
                {'timestamp': [5.0, 7.5], 'text': 'It is going well.'},
                {'timestamp': [7.5, 10.0], 'text': 'Great to hear.'}
            ]
        }
        mock_mlx_whisper.transcribe.return_value = mock_transcription_result
        
        # 模拟pyannote pipeline结果
        mock_pipeline = MagicMock()
        mock_diarization_result = MagicMock()
        
        # 模拟说话人段落
        mock_segments = [
            MagicMock(start=0.0, end=5.2, label='Speaker_A'),  # 前两个chunks
            MagicMock(start=5.2, end=7.8, label='Speaker_B'),  # 第三个chunk
            MagicMock(start=7.8, end=10.0, label='Speaker_A')  # 第四个chunk
        ]
        mock_diarization_result.itertracks.return_value = [
            (segment, None, segment.label) for segment in mock_segments
        ]
        
        mock_pipeline.return_value = mock_diarization_result
        mock_pipeline_class.from_pretrained.return_value = mock_pipeline
        
        # 创建服务实例
        mlx_service = MLXTranscriptionService(self.mlx_config)
        diarization_service = SpeakerDiarization(self.diarization_config, self.huggingface_config)
        integrator = DiarizationIntegrator(diarization_service)
        
        # 执行转录
        transcription_text = mlx_service.transcribe_audio(self.audio_path)
        self.assertEqual(transcription_text, 'Hello everyone. How is the project going? It is going well. Great to hear.')
        
        # 执行集成处理（会议类型默认启用diarization）
        integrated_result = integrator.process_with_diarization(
            audio_path=self.audio_path,
            transcription_result=transcription_text,
            content_type='meeting',
            subcategory='standup'
        )
        
        # 验证集成结果
        self.assertTrue(integrated_result['has_diarization'])
        self.assertEqual(integrated_result['content_type'], 'meeting')
        self.assertEqual(integrated_result['subcategory'], 'standup')
        self.assertIn('speaker_segments', integrated_result)
        self.assertIn('speaker_statistics', integrated_result)
        
        # 验证说话人段落
        speaker_segments = integrated_result['speaker_segments']
        self.assertEqual(len(speaker_segments), 3)
        self.assertEqual(speaker_segments[0]['speaker'], 'Speaker_A')
        self.assertEqual(speaker_segments[1]['speaker'], 'Speaker_B')
        self.assertEqual(speaker_segments[2]['speaker'], 'Speaker_A')
        
        # 验证说话人统计
        stats = integrated_result['speaker_statistics']
        self.assertEqual(stats['total_speakers'], 2)
        self.assertIn('Speaker_A', stats['speaker_durations'])
        self.assertIn('Speaker_B', stats['speaker_durations'])
    
    @patch('core.mlx_transcription.mlx_whisper')
    def test_lecture_with_diarization_disabled(self, mock_mlx_whisper):
        """测试讲座类型音频不启用说话人分离"""
        # 模拟转录结果
        mock_transcription_result = {
            'text': 'Today we will discuss machine learning algorithms.'
        }
        mock_mlx_whisper.transcribe.return_value = mock_transcription_result
        
        # 创建服务实例
        mlx_service = MLXTranscriptionService(self.mlx_config)
        diarization_service = SpeakerDiarization(self.diarization_config, self.huggingface_config)
        integrator = DiarizationIntegrator(diarization_service)
        
        # 修改音频文件名为讲座类型
        lecture_audio_path = Path(self.test_dir) / 'cs_lecture.mp3'
        lecture_audio_path.write_bytes(b'fake lecture audio')
        
        # 执行转录
        transcription_text = mlx_service.transcribe_audio(lecture_audio_path)
        
        # 执行集成处理（CS讲座默认不启用diarization）
        integrated_result = integrator.process_with_diarization(
            audio_path=lecture_audio_path,
            transcription_result=transcription_text,
            content_type='lecture',
            subcategory='cs'
        )
        
        # 验证diarization被跳过
        self.assertFalse(integrated_result['has_diarization'])
        self.assertEqual(integrated_result['text'], 'Today we will discuss machine learning algorithms.')
        self.assertNotIn('speaker_segments', integrated_result)
    
    @patch('core.mlx_transcription.mlx_whisper')
    @patch('core.speaker_diarization.Pipeline')
    @patch('os.environ')
    def test_lecture_seminar_with_diarization_enabled(self, mock_environ, mock_pipeline_class, mock_mlx_whisper):
        """测试研讨会类型讲座启用说话人分离"""
        # 设置环境变量
        mock_environ.get.return_value = 'fake_hf_token'
        
        # 模拟转录结果
        mock_transcription_result = {
            'text': 'Welcome to the seminar. Thank you for the introduction.',
            'chunks': [
                {'timestamp': [0.0, 3.0], 'text': 'Welcome to the seminar.'},
                {'timestamp': [3.0, 6.0], 'text': 'Thank you for the introduction.'}
            ]
        }
        mock_mlx_whisper.transcribe.return_value = mock_transcription_result
        
        # 模拟diarization结果
        mock_pipeline = MagicMock()
        mock_diarization_result = MagicMock()
        mock_segments = [
            MagicMock(start=0.0, end=3.2, label='Speaker_A'),
            MagicMock(start=3.2, end=6.0, label='Speaker_B')
        ]
        mock_diarization_result.itertracks.return_value = [
            (segment, None, segment.label) for segment in mock_segments
        ]
        mock_pipeline.return_value = mock_diarization_result
        mock_pipeline_class.from_pretrained.return_value = mock_pipeline
        
        # 创建服务实例
        mlx_service = MLXTranscriptionService(self.mlx_config)
        diarization_service = SpeakerDiarization(self.diarization_config, self.huggingface_config)
        integrator = DiarizationIntegrator(diarization_service)
        
        # 创建研讨会音频文件
        seminar_audio_path = Path(self.test_dir) / 'ai_seminar.mp3'
        seminar_audio_path.write_bytes(b'fake seminar audio')
        
        # 执行转录
        transcription_text = mlx_service.transcribe_audio(seminar_audio_path)
        
        # 执行集成处理（研讨会默认启用diarization）
        integrated_result = integrator.process_with_diarization(
            audio_path=seminar_audio_path,
            transcription_result=transcription_text,
            content_type='lecture',
            subcategory='seminar'
        )
        
        # 验证diarization被启用
        self.assertTrue(integrated_result['has_diarization'])
        self.assertEqual(integrated_result['content_type'], 'lecture')
        self.assertEqual(integrated_result['subcategory'], 'seminar')
        self.assertIn('speaker_segments', integrated_result)
        
        # 验证检测到两个说话人
        stats = integrated_result['speaker_statistics']
        self.assertEqual(stats['total_speakers'], 2)
    
    @patch('core.mlx_transcription.mlx_whisper')
    def test_force_enable_diarization(self, mock_mlx_whisper):
        """测试强制启用说话人分离"""
        # 模拟转录结果
        mock_transcription_result = {
            'text': 'This should have diarization despite being a CS lecture.'
        }
        mock_mlx_whisper.transcribe.return_value = mock_transcription_result
        
        # 创建服务实例
        mlx_service = MLXTranscriptionService(self.mlx_config)
        diarization_service = SpeakerDiarization(self.diarization_config, self.huggingface_config)
        integrator = DiarizationIntegrator(diarization_service)
        
        with patch('core.speaker_diarization.Pipeline') as mock_pipeline_class:
            with patch('os.environ'):
                # 模拟diarization成功
                mock_pipeline = MagicMock()
                mock_diarization_result = MagicMock()
                mock_segments = [MagicMock(start=0.0, end=5.0, label='Speaker_A')]
                mock_diarization_result.itertracks.return_value = [
                    (segment, None, segment.label) for segment in mock_segments
                ]
                mock_pipeline.return_value = mock_diarization_result
                mock_pipeline_class.from_pretrained.return_value = mock_pipeline
                
                # 执行转录
                transcription_text = mlx_service.transcribe_audio(self.audio_path)
                
                # 强制启用diarization
                integrated_result = integrator.process_with_diarization(
                    audio_path=self.audio_path,
                    transcription_result=transcription_text,
                    content_type='lecture',  # 通常不启用
                    subcategory='cs',        # CS课程通常不启用
                    force_enable=True        # 但强制启用
                )
                
                # 验证diarization被强制启用
                self.assertTrue(integrated_result['has_diarization'])
    
    @patch('core.mlx_transcription.mlx_whisper')
    def test_diarization_error_handling(self, mock_mlx_whisper):
        """测试说话人分离错误处理"""
        # 模拟转录成功
        mock_transcription_result = {
            'text': 'Transcription succeeded but diarization will fail.'
        }
        mock_mlx_whisper.transcribe.return_value = mock_transcription_result
        
        # 创建服务实例
        mlx_service = MLXTranscriptionService(self.mlx_config)
        diarization_service = SpeakerDiarization(self.diarization_config, self.huggingface_config)
        integrator = DiarizationIntegrator(diarization_service)
        
        with patch('core.speaker_diarization.Pipeline') as mock_pipeline_class:
            # 模拟diarization失败
            mock_pipeline_class.from_pretrained.side_effect = Exception("Diarization model loading failed")
            
            # 执行转录
            transcription_text = mlx_service.transcribe_audio(self.audio_path)
            
            # 尝试集成处理
            integrated_result = integrator.process_with_diarization(
                audio_path=self.audio_path,
                transcription_result=transcription_text,
                content_type='meeting',
                subcategory='standup',
                force_enable=True
            )
            
            # 验证转录文本仍然返回，但diarization失败
            self.assertEqual(integrated_result['text'], 'Transcription succeeded but diarization will fail.')
            self.assertFalse(integrated_result['has_diarization'])
            self.assertIn('diarization_error', integrated_result)
            self.assertIn('Diarization model loading failed', integrated_result['diarization_error'])


if __name__ == '__main__':
    unittest.main()