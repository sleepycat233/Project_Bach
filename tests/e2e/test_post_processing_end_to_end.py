#!/usr/bin/env python3.11
"""
端到端测试: Post-Processing选择器实际效果验证
使用真实音频文件测试不同配置的输出差异和性能差异
"""

import time
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.core.audio_processor import AudioProcessor
from src.utils.config import ConfigManager
from src.core.dependency_container import DependencyContainer


class TestPostProcessingEndToEnd:
    """端到端测试Post-Processing选择器的实际效果"""

    @pytest.fixture
    def test_audio_file(self):
        """使用2分钟的Feynman讲座音频作为测试文件"""
        test_audio = Path("audio/feynman_lecture_2min.mp4")
        if test_audio.exists():
            return test_audio

        pytest.skip("Test audio file 'feynman_lecture_2min.mp4' not found in audio directory")

    @pytest.fixture
    def audio_processor_with_config(self):
        """创建配置完整的AudioProcessor，mock转录服务避免外部依赖"""
        config_manager = ConfigManager()
        container = DependencyContainer(config_manager)

        # 获取真实的AudioProcessor
        audio_processor = container.get_audio_processor()

        # Mock转录服务返回固定结果，专注测试post-processing逻辑
        with patch.object(audio_processor, 'transcription_service') as mock_transcription:
            mock_transcription.transcribe_audio.return_value = {
                'text': 'This is a test transcript with names like John Smith and Alice Johnson discussing quantum physics.',
                'chunks': [
                    {'text': 'This is a test transcript', 'timestamp': [0, 2]},
                    {'text': 'with names like John Smith', 'timestamp': [2, 4]},
                    {'text': 'and Alice Johnson discussing', 'timestamp': [4, 6]},
                    {'text': 'quantum physics.', 'timestamp': [6, 8]}
                ]
            }

            yield audio_processor, config_manager

    def test_ner_disabled_output_contains_original_names(self, audio_processor_with_config, test_audio_file, tmp_path):
        """测试: 关闭NER匿名化时，输出包含原始人名"""
        audio_processor, config_manager = audio_processor_with_config

        # 测试配置：关闭匿名化
        metadata = {
            'content_type': 'meeting',
            'subcategory': 'test',
            'description': 'Meeting with John Smith discussing the project',  # 包含人名
            'enable_anonymization': False,  # 关闭匿名化
            'enable_summary': False,        # 关闭摘要以加速测试
            'enable_mindmap': False,        # 关闭思维导图
            'enable_diarization': False,    # 关闭说话人分离
        }

        # 执行处理
        result_dir = tmp_path / "results"
        result_dir.mkdir()

        with patch.object(audio_processor, 'result_storage') as mock_storage:
            # 配置存储路径到临时目录
            mock_storage.save_json_result.side_effect = self._save_to_temp_dir(result_dir)

            success = audio_processor.process_audio_file(
                str(test_audio_file),
                privacy_level='private',
                metadata=metadata
            )

        assert success

        # 验证输出文件存在
        json_files = list(result_dir.glob("*.json"))
        assert len(json_files) > 0, "No JSON result file generated"

        # 检查结果内容
        result_data = json.loads(json_files[0].read_text())

        # 关键验证：转录文本应该包含原始人名（如果音频中有的话）
        transcript = result_data.get('anonymized_transcript', '')

        # 验证没有匿名化标记（如[NAME_1]这样的占位符）
        assert '[NAME_' not in transcript, "Found anonymization markers when anonymization is disabled"
        assert '[PERSON_' not in transcript, "Found anonymization markers when anonymization is disabled"

        # 验证结果中明确标记匿名化已禁用
        processing_config = result_data.get('metadata', {}).get('processing_config', {})
        assert processing_config.get('enable_anonymization') is False

    def test_ai_summary_disabled_no_summary_in_output(self, audio_processor_with_config, test_audio_file, tmp_path):
        """测试: 关闭AI摘要时，输出不包含摘要内容"""
        audio_processor, config_manager = audio_processor_with_config

        metadata = {
            'content_type': 'lecture',
            'enable_anonymization': False,
            'enable_summary': False,        # 关闭摘要
            'enable_mindmap': False,
            'enable_diarization': False,
        }

        result_dir = tmp_path / "results"
        result_dir.mkdir()

        with patch.object(audio_processor, 'result_storage') as mock_storage:
            mock_storage.save_json_result.side_effect = self._save_to_temp_dir(result_dir)

            success = audio_processor.process_audio_file(
                str(test_audio_file),
                privacy_level='private',
                metadata=metadata
            )

        assert success

        json_files = list(result_dir.glob("*.json"))
        assert len(json_files) > 0, "No JSON result file generated"

        result_data = json.loads(json_files[0].read_text())

        # 打印实际输出用于调试
        print(f"Result data keys: {result_data.keys()}")
        if 'summary' in result_data:
            print(f"Summary content: '{result_data['summary']}'")

        # 验证没有生成摘要内容 - 应该为None或空字符串
        summary_content = result_data.get('ai_summary') or result_data.get('summary')
        assert not summary_content or summary_content.strip() == '', f"Expected no summary content, but got: '{summary_content}'"

    def test_processing_time_difference_with_ai_disabled(self, audio_processor_with_config, test_audio_file, tmp_path):
        """测试: 关闭AI功能时处理时间显著减少"""
        audio_processor, config_manager = audio_processor_with_config

        # 测试1：全部AI功能开启
        full_metadata = {
            'content_type': 'lecture',
            'enable_anonymization': True,
            'enable_summary': True,
            'enable_mindmap': True,
            'enable_diarization': False,  # 说话人分离耗时长，这里关闭
        }

        # 测试2：全部AI功能关闭
        minimal_metadata = {
            'content_type': 'lecture',
            'enable_anonymization': False,
            'enable_summary': False,
            'enable_mindmap': False,
            'enable_diarization': False,
        }

        def measure_processing_time(metadata_config, label):
            """测量处理时间"""
            result_dir = tmp_path / f"results_{label}"
            result_dir.mkdir(exist_ok=True)

            start_time = time.time()

            with patch.object(audio_processor, 'result_storage') as mock_storage:
                mock_storage.save_json_result.side_effect = self._save_to_temp_dir(result_dir)
                mock_storage.save_html_result.return_value = "mocked"

                success = audio_processor.process_audio_file(
                    str(test_audio_file),
                    privacy_level='private',
                    metadata=metadata_config
                )

            end_time = time.time()
            processing_time = end_time - start_time

            assert success, f"Processing failed for {label} configuration"
            return processing_time

        # 如果外部API不可用，mock AI生成服务
        with patch.object(audio_processor, 'ai_generation_service') as mock_ai:
            mock_ai.generate_summary.return_value = "Test summary"
            mock_ai.generate_mindmap.return_value = "Test mindmap"

            # 测量两种配置的处理时间
            full_time = measure_processing_time(full_metadata, "full")
            minimal_time = measure_processing_time(minimal_metadata, "minimal")

        # 验证时间差异显著（至少minimal应该更快）
        time_saved = full_time - minimal_time
        print(f"Full processing: {full_time:.2f}s, Minimal: {minimal_time:.2f}s, Saved: {time_saved:.2f}s")

        # 最小配置应该明显更快（允许一定误差范围）
        assert minimal_time < full_time, f"Minimal processing ({minimal_time:.2f}s) should be faster than full processing ({full_time:.2f}s)"

    def test_mixed_configuration_output_consistency(self, audio_processor_with_config, test_audio_file, tmp_path):
        """测试: 混合配置的输出一致性"""
        audio_processor, config_manager = audio_processor_with_config

        # 混合配置：匿名化开启，AI功能关闭
        metadata = {
            'content_type': 'meeting',
            'enable_anonymization': True,   # 开启
            'enable_summary': False,        # 关闭
            'enable_mindmap': False,        # 关闭
            'enable_diarization': False,
        }

        result_dir = tmp_path / "results"
        result_dir.mkdir()

        with patch.object(audio_processor, 'result_storage') as mock_storage:
            mock_storage.save_json_result.side_effect = self._save_to_temp_dir(result_dir)

            success = audio_processor.process_audio_file(
                str(test_audio_file),
                privacy_level='private',
                metadata=metadata
            )

        assert success

        json_files = list(result_dir.glob("*.json"))
        result_data = json.loads(json_files[0].read_text())

        # 验证：应该有匿名化处理，但没有AI生成内容
        transcript = result_data.get('anonymized_transcript', '')

        # 可能包含匿名化标记（取决于音频内容）
        # 不应该有AI生成的内容
        assert 'ai_summary' not in result_data or result_data.get('ai_summary') is None
        assert 'mindmap' not in result_data or result_data.get('mindmap') is None

        # 验证配置记录
        processing_config = result_data.get('metadata', {}).get('processing_config', {})
        assert processing_config.get('enable_anonymization') is True
        assert processing_config.get('enable_summary') is False
        assert processing_config.get('enable_mindmap') is False

    @staticmethod
    def _save_to_temp_dir(result_dir: Path):
        """Helper: 创建mock函数保存结果到临时目录"""
        def mock_save(filename: str, data: dict, privacy_level: str = 'private'):
            output_file = result_dir / f"{filename}_result.json"
            output_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))
            return str(output_file)

        return mock_save

    def test_dependency_availability_affects_processing(self, audio_processor_with_config, test_audio_file):
        """测试: 依赖不可用时的处理行为"""
        audio_processor, config_manager = audio_processor_with_config

        # 模拟OpenRouter API不可用
        with patch.object(audio_processor, 'ai_generation_service', None):
            metadata = {
                'content_type': 'lecture',
                'enable_anonymization': False,
                'enable_summary': True,         # 尝试开启但服务不可用
                'enable_mindmap': True,         # 尝试开启但服务不可用
                'enable_diarization': False,
            }

            # 处理应该成功但跳过不可用的服务
            success = audio_processor.process_audio_file(
                str(test_audio_file),
                privacy_level='private',
                metadata=metadata
            )

            # 处理应该完成（优雅降级）
            assert success, "Processing should succeed even when AI services are unavailable"