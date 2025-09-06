#!/usr/bin/env python3
"""
Speaker Diarization时间戳对齐算法单元测试

测试场景:
1. 无重叠场景 - speaker segments完全不重叠
2. 部分重叠场景 - speaker segments部分时间重叠
3. 完全重叠场景 - 一个segment完全包含在另一个segment内
4. 边界条件 - 空segments、空chunks、时间戳相等等边界情况
5. 复杂混合场景 - 多种情况组合

重点验证:
- 每个chunk只被分配给一个speaker
- 时间戳对齐准确性
- 重叠处理的正确性
- 异常情况处理
"""

import unittest
import sys
from pathlib import Path
from typing import Dict, List, Any
import numpy as np

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'src'))

from core.speaker_diarization import SpeakerDiarization


class TestSpeakerDiarizationAlignment(unittest.TestCase):
    """Speaker Diarization时间戳对齐算法测试"""
    
    def setUp(self):
        """测试准备"""
        # 创建测试用的配置
        diarization_config = {
            'max_speakers': 6,
            'min_segment_duration': 1.0,
            'provider': 'pyannote'
        }
        
        huggingface_config = {
            'token': 'test_token'  # 测试用的token
        }
        
        content_classification_config = {
            'content_types': {
                'lecture': {
                    'diarization_default': False
                },
                'meeting': {
                    'diarization_default': True
                }
            }
        }
        
        self.diarization_service = SpeakerDiarization(
            diarization_config, 
            huggingface_config, 
            content_classification_config
        )
    
    def create_test_transcription(self, chunks: List[Dict]) -> Dict[str, Any]:
        """创建测试用的转录结果"""
        return {
            'text': ' '.join([chunk['text'] for chunk in chunks]),
            'chunks': chunks,
            'segments': []  # 简化测试，主要关注chunks
        }
    
    def create_test_speaker_segments(self, segments: List[Dict]) -> List[Dict]:
        """创建测试用的说话人段落"""
        return segments
    
    # ============= 场景1: 无重叠测试 =============
    
    def test_no_overlap_simple(self):
        """测试无重叠的简单场景"""
        # 转录chunks: 完全不重叠的时间段
        chunks = [
            {'text': 'Hello', 'timestamp': [0.0, 2.0]},
            {'text': 'world', 'timestamp': [2.0, 4.0]},
            {'text': 'how', 'timestamp': [4.0, 6.0]},
            {'text': 'are', 'timestamp': [6.0, 8.0]},
            {'text': 'you', 'timestamp': [8.0, 10.0]},
        ]
        
        # 说话人段落: 完全不重叠
        speaker_segments = [
            {'speaker': 'SPEAKER_00', 'start': 0.0, 'end': 4.0},
            {'speaker': 'SPEAKER_01', 'start': 4.0, 'end': 10.0},
        ]
        
        transcription = self.create_test_transcription(chunks)
        result = self.diarization_service.merge_with_transcription(
            transcription, speaker_segments, group_by_speaker=False
        )
        
        # 验证结果 - result是chunks的列表，不是字典
        self.assertEqual(len(result), 5)
        
        # 验证speaker分配
        expected_speakers = ['SPEAKER_00', 'SPEAKER_00', 'SPEAKER_01', 'SPEAKER_01', 'SPEAKER_01']
        actual_speakers = [chunk['speaker'] for chunk in result]
        self.assertEqual(actual_speakers, expected_speakers)
        
        # 验证没有重复分配
        self.assert_no_duplicate_assignments(result)
    
    def test_no_overlap_precise_boundaries(self):
        """测试无重叠且边界精确对齐的场景"""
        chunks = [
            {'text': 'First', 'timestamp': [0.0, 1.5]},
            {'text': 'speaker', 'timestamp': [1.5, 3.0]},
            {'text': 'Second', 'timestamp': [3.0, 4.5]},
            {'text': 'speaker', 'timestamp': [4.5, 6.0]},
        ]
        
        speaker_segments = [
            {'speaker': 'SPEAKER_00', 'start': 0.0, 'end': 3.0},
            {'speaker': 'SPEAKER_01', 'start': 3.0, 'end': 6.0},
        ]
        
        transcription = self.create_test_transcription(chunks)
        result = self.diarization_service.merge_with_transcription(
            transcription, speaker_segments, group_by_speaker=False
        )
        
        # 验证边界精确对齐
        expected_speakers = ['SPEAKER_00', 'SPEAKER_00', 'SPEAKER_01', 'SPEAKER_01']
        actual_speakers = [chunk['speaker'] for chunk in result]
        self.assertEqual(actual_speakers, expected_speakers)
    
    # ============= 场景2: 部分重叠测试 =============
    
    def test_partial_overlap_basic(self):
        """测试基本的部分重叠场景"""
        chunks = [
            {'text': 'This', 'timestamp': [0.0, 2.0]},
            {'text': 'is', 'timestamp': [2.0, 4.0]},
            {'text': 'overlapping', 'timestamp': [4.0, 6.0]},    # 重叠区域
            {'text': 'speech', 'timestamp': [6.0, 8.0]},        # 重叠区域  
            {'text': 'test', 'timestamp': [8.0, 10.0]},
        ]
        
        # 部分重叠的说话人段落
        speaker_segments = [
            {'speaker': 'SPEAKER_00', 'start': 0.0, 'end': 5.0},    # 到5.0
            {'speaker': 'SPEAKER_01', 'start': 3.0, 'end': 10.0},   # 从3.0开始，重叠2秒
        ]
        
        transcription = self.create_test_transcription(chunks)
        result = self.diarization_service.merge_with_transcription(
            transcription, speaker_segments, group_by_speaker=False
        )
        
        # 验证每个chunk只分配给一个speaker
        self.assert_no_duplicate_assignments(result)
        self.assertEqual(len(result), 5)
        
        # 验证重叠区域的处理逻辑
        chunk_speakers = [chunk['speaker'] for chunk in result]
        self.assertEqual(len(set(chunk_speakers)), 2)  # 应该有两个不同的speaker
    
    def test_partial_overlap_complex(self):
        """测试复杂的部分重叠场景"""
        chunks = [
            {'text': 'A', 'timestamp': [0.0, 1.0]},
            {'text': 'B', 'timestamp': [1.0, 2.0]},
            {'text': 'C', 'timestamp': [2.0, 3.0]},    # 三重重叠区域
            {'text': 'D', 'timestamp': [3.0, 4.0]},    # 三重重叠区域
            {'text': 'E', 'timestamp': [4.0, 5.0]},    # 双重重叠区域
            {'text': 'F', 'timestamp': [5.0, 6.0]},
            {'text': 'G', 'timestamp': [6.0, 7.0]},
        ]
        
        # 三个speaker，时间有复杂重叠
        speaker_segments = [
            {'speaker': 'SPEAKER_00', 'start': 0.0, 'end': 3.5},
            {'speaker': 'SPEAKER_01', 'start': 1.5, 'end': 5.5},   # 与00重叠1.5-3.5，与02重叠3.0-5.5
            {'speaker': 'SPEAKER_02', 'start': 3.0, 'end': 7.0},   # 与01重叠3.0-5.5
        ]
        
        transcription = self.create_test_transcription(chunks)
        result = self.diarization_service.merge_with_transcription(
            transcription, speaker_segments, group_by_speaker=False
        )
        
        # 核心验证：无重复分配
        self.assert_no_duplicate_assignments(result)
        self.assertEqual(len(result), 7)
        
        # 验证所有chunks都被分配了speaker
        for chunk in result:
            self.assertIn('speaker', chunk)
            self.assertIn(chunk['speaker'], ['SPEAKER_00', 'SPEAKER_01', 'SPEAKER_02'])
    
    # ============= 场景3: 完全重叠测试 =============
    
    def test_complete_overlap_contained(self):
        """测试完全包含的重叠场景"""
        chunks = [
            {'text': 'Before', 'timestamp': [0.0, 2.0]},
            {'text': 'contained', 'timestamp': [2.0, 4.0]},   # 完全包含在内
            {'text': 'speech', 'timestamp': [4.0, 6.0]},     # 完全包含在内
            {'text': 'after', 'timestamp': [6.0, 8.0]},
        ]
        
        speaker_segments = [
            {'speaker': 'SPEAKER_00', 'start': 0.0, 'end': 8.0},   # 包含所有
            {'speaker': 'SPEAKER_01', 'start': 2.0, 'end': 6.0},   # 完全包含在SPEAKER_00内
        ]
        
        transcription = self.create_test_transcription(chunks)
        result = self.diarization_service.merge_with_transcription(
            transcription, speaker_segments, group_by_speaker=False
        )
        
        self.assert_no_duplicate_assignments(result)
        self.assertEqual(len(result), 4)
    
    def test_complete_overlap_identical(self):
        """测试完全相同时间段的重叠场景"""
        chunks = [
            {'text': 'Same', 'timestamp': [0.0, 2.0]},
            {'text': 'time', 'timestamp': [2.0, 4.0]},
            {'text': 'range', 'timestamp': [4.0, 6.0]},
        ]
        
        # 两个speaker有完全相同的时间段
        speaker_segments = [
            {'speaker': 'SPEAKER_00', 'start': 0.0, 'end': 6.0},
            {'speaker': 'SPEAKER_01', 'start': 0.0, 'end': 6.0},   # 完全相同
        ]
        
        transcription = self.create_test_transcription(chunks)
        result = self.diarization_service.merge_with_transcription(
            transcription, speaker_segments, group_by_speaker=False
        )
        
        # 即使时间完全相同，每个chunk也只能分配给一个speaker
        self.assert_no_duplicate_assignments(result)
        self.assertEqual(len(result), 3)
        
        # 所有chunks应该分配给同一个speaker (根据算法优先级)
        speakers = set(chunk['speaker'] for chunk in result)
        self.assertEqual(len(speakers), 1)
    
    # ============= 场景4: 边界条件测试 =============
    
    def test_empty_chunks(self):
        """测试空chunks列表"""
        transcription = self.create_test_transcription([])
        speaker_segments = [
            {'speaker': 'SPEAKER_00', 'start': 0.0, 'end': 5.0},
        ]
        
        result = self.diarization_service.merge_with_transcription(
            transcription, speaker_segments, group_by_speaker=False
        )
        
        self.assertEqual(len(result), 0)
    
    def test_empty_speaker_segments(self):
        """测试空speaker_segments列表"""
        chunks = [
            {'text': 'No', 'timestamp': [0.0, 2.0]},
            {'text': 'speakers', 'timestamp': [2.0, 4.0]},
        ]
        
        transcription = self.create_test_transcription(chunks)
        result = self.diarization_service.merge_with_transcription(
            transcription, [], group_by_speaker=False
        )
        
        # 没有speaker segments，chunks应该保持原样但没有speaker信息
        self.assertEqual(len(result), 2)
        for chunk in result:
            # 根据实现，可能添加默认speaker或保持无speaker
            # 这里测试实际行为
            pass
    
    def test_zero_duration_segments(self):
        """测试零时长的segments"""
        chunks = [
            {'text': 'Normal', 'timestamp': [0.0, 2.0]},
            {'text': 'speech', 'timestamp': [2.0, 4.0]},
        ]
        
        speaker_segments = [
            {'speaker': 'SPEAKER_00', 'start': 1.0, 'end': 1.0},   # 零时长
            {'speaker': 'SPEAKER_01', 'start': 0.0, 'end': 4.0},   # 正常时长
        ]
        
        transcription = self.create_test_transcription(chunks)
        result = self.diarization_service.merge_with_transcription(
            transcription, speaker_segments, group_by_speaker=False
        )
        
        self.assert_no_duplicate_assignments(result)
        # 零时长segment应该不影响结果
        self.assertEqual(len(result), 2)
    
    def test_same_timestamp_chunks(self):
        """测试相同时间戳的chunks"""
        chunks = [
            {'text': 'Same', 'timestamp': [2.0, 2.0]},      # 零时长chunk
            {'text': 'start', 'timestamp': [2.0, 4.0]},     # 相同开始时间
            {'text': 'time', 'timestamp': [2.0, 6.0]},      # 相同开始时间，不同结束时间
        ]
        
        speaker_segments = [
            {'speaker': 'SPEAKER_00', 'start': 0.0, 'end': 3.0},
            {'speaker': 'SPEAKER_01', 'start': 3.0, 'end': 8.0},
        ]
        
        transcription = self.create_test_transcription(chunks)
        result = self.diarization_service.merge_with_transcription(
            transcription, speaker_segments, group_by_speaker=False
        )
        
        self.assert_no_duplicate_assignments(result)
        self.assertEqual(len(result), 3)
    
    # ============= 场景5: 复杂混合场景测试 =============
    
    def test_real_world_scenario(self):
        """测试接近真实场景的复杂情况"""
        # 模拟真实的2分钟对话转录结果
        chunks = [
            {'text': 'Hello', 'timestamp': [0.0, 1.2]},
            {'text': 'everyone', 'timestamp': [1.2, 2.5]},
            {'text': 'Hi', 'timestamp': [2.8, 3.1]},          # 短暂插话
            {'text': 'there', 'timestamp': [3.1, 3.8]},
            {'text': 'Thanks', 'timestamp': [4.0, 4.8]},       # 回到原speaker
            {'text': 'for', 'timestamp': [4.8, 5.2]},
            {'text': 'joining', 'timestamp': [5.2, 6.0]},
            {'text': 'Yeah', 'timestamp': [6.2, 6.6]},         # 另一个插话
            {'text': 'absolutely', 'timestamp': [6.6, 7.8]},
            {'text': 'So', 'timestamp': [8.0, 8.3]},           # 回到主speaker
            {'text': 'lets', 'timestamp': [8.3, 8.8]},
            {'text': 'begin', 'timestamp': [8.8, 9.5]},
        ]
        
        # 真实的说话人分离结果 - 有重叠和交替
        speaker_segments = [
            {'speaker': 'SPEAKER_00', 'start': 0.0, 'end': 2.7},    # 主speaker开场
            {'speaker': 'SPEAKER_01', 'start': 2.5, 'end': 4.2},    # 插话，有重叠
            {'speaker': 'SPEAKER_00', 'start': 3.8, 'end': 6.5},    # 继续，有重叠
            {'speaker': 'SPEAKER_01', 'start': 6.0, 'end': 8.2},    # 再次插话，有重叠  
            {'speaker': 'SPEAKER_00', 'start': 7.8, 'end': 10.0},   # 结束，有重叠
        ]
        
        transcription = self.create_test_transcription(chunks)
        result = self.diarization_service.merge_with_transcription(
            transcription, speaker_segments, group_by_speaker=False
        )
        
        # 核心验证
        self.assert_no_duplicate_assignments(result)
        self.assertEqual(len(result), 12)
        
        # 验证speaker分配的合理性
        chunk_speakers = [chunk['speaker'] for chunk in result]
        unique_speakers = set(chunk_speakers)
        self.assertEqual(len(unique_speakers), 2)
        self.assertEqual(unique_speakers, {'SPEAKER_00', 'SPEAKER_01'})
        
        # 验证时间戳保持不变
        for i, chunk in enumerate(result):
            self.assertEqual(chunk['timestamp'], chunks[i]['timestamp'])
            self.assertEqual(chunk['text'], chunks[i]['text'])
    
    def test_group_by_speaker_mode(self):
        """测试group_by_speaker=True模式"""
        chunks = [
            {'text': 'Hello', 'timestamp': [0.0, 2.0]},
            {'text': 'world', 'timestamp': [2.0, 4.0]},
            {'text': 'Hi', 'timestamp': [4.0, 6.0]},
            {'text': 'there', 'timestamp': [6.0, 8.0]},
            {'text': 'How', 'timestamp': [8.0, 10.0]},
            {'text': 'are', 'timestamp': [10.0, 12.0]},
            {'text': 'you', 'timestamp': [12.0, 14.0]},
        ]
        
        speaker_segments = [
            {'speaker': 'SPEAKER_00', 'start': 0.0, 'end': 4.0},
            {'speaker': 'SPEAKER_01', 'start': 4.0, 'end': 8.0}, 
            {'speaker': 'SPEAKER_00', 'start': 8.0, 'end': 14.0},
        ]
        
        transcription = self.create_test_transcription(chunks)
        result = self.diarization_service.merge_with_transcription(
            transcription, speaker_segments, group_by_speaker=True
        )
        
        # 验证分组结果 - group_by_speaker=True返回分组后的列表
        # 应该有3个组 (SPEAKER_00, SPEAKER_01, SPEAKER_00)
        self.assertEqual(len(result), 3)
        
        # 验证分组内容
        expected_texts = ['Hello world', 'Hi there', 'How are you']
        actual_texts = [group['text'] for group in result]
        self.assertEqual(actual_texts, expected_texts)
        
        expected_speakers = ['SPEAKER_00', 'SPEAKER_01', 'SPEAKER_00']
        actual_speakers = [group['speaker'] for group in result]
        self.assertEqual(actual_speakers, expected_speakers)
    
    # ============= 辅助验证方法 =============
    
    def assert_no_duplicate_assignments(self, chunks: List[Dict]):
        """验证没有重复分配 - 每个原始chunk只出现一次"""
        texts = [chunk['text'] for chunk in chunks]
        timestamps = [tuple(chunk['timestamp']) for chunk in chunks]
        
        # 验证text+timestamp的组合是唯一的
        text_timestamp_pairs = list(zip(texts, timestamps))
        unique_pairs = set(text_timestamp_pairs)
        
        self.assertEqual(len(text_timestamp_pairs), len(unique_pairs), 
                         f"发现重复的chunk分配: {text_timestamp_pairs}")
    
    def test_performance_large_input(self):
        """测试大输入的性能"""
        import time
        
        # 创建大量chunks和segments测试性能
        num_chunks = 1000
        num_segments = 50
        
        chunks = []
        for i in range(num_chunks):
            start_time = i * 0.1
            end_time = start_time + 0.1
            chunks.append({
                'text': f'word_{i}',
                'timestamp': [start_time, end_time]
            })
        
        speaker_segments = []
        for i in range(num_segments):
            start_time = i * 2.0
            end_time = start_time + 2.5  # 创建重叠
            speaker_segments.append({
                'speaker': f'SPEAKER_{i % 10}',  # 10个speaker循环
                'start': start_time,
                'end': end_time
            })
        
        transcription = self.create_test_transcription(chunks)
        
        start_time = time.time()
        result = self.diarization_service.merge_with_transcription(
            transcription, speaker_segments, group_by_speaker=False
        )
        end_time = time.time()
        
        # 验证结果正确性
        self.assert_no_duplicate_assignments(result)
        self.assertEqual(len(result), num_chunks)
        
        # 性能应该在合理范围内 (这里设置为5秒，可根据实际调整)
        processing_time = end_time - start_time
        self.assertLess(processing_time, 5.0, 
                       f"处理{num_chunks}个chunks和{num_segments}个segments用时{processing_time:.2f}秒，超过预期")
        
        print(f"性能测试: {num_chunks}个chunks + {num_segments}个segments = {processing_time:.3f}秒")


if __name__ == '__main__':
    unittest.main()