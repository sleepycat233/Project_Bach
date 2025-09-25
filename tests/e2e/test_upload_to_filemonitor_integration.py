#!/usr/bin/env python3.11
"""
端到端测试: Web上传 → FileMonitor配置传递
测试Web上传的Post-Processing配置能正确传递到FileMonitor处理
"""

import pytest
import tempfile
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
from werkzeug.datastructures import FileStorage
from io import BytesIO

from src.web_frontend.audio_upload_handler import AudioUploadHandler
from src.monitoring.file_monitor import FileMonitor
from src.utils.config import ConfigManager
from src.core.dependency_container import DependencyContainer


class TestUploadToFileMonitorIntegration:
    """测试Web上传到FileMonitor的完整配置传递流程"""

    @pytest.fixture
    def temp_directories(self):
        """创建临时目录结构"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            watch_folder = temp_path / "watch_folder"
            output_folder = temp_path / "output"

            watch_folder.mkdir()
            output_folder.mkdir()

            yield {
                'watch_folder': str(watch_folder),
                'output_folder': str(output_folder),
                'temp_path': temp_path
            }

    @pytest.fixture
    def mock_config_manager(self, temp_directories):
        """创建Mock配置管理器"""
        config = {
            'paths': {
                'watch_folder': temp_directories['watch_folder'],
                'output': temp_directories['output_folder']
            },
            'upload': {
                'supported_formats': ['.mp3', '.wav', '.m4a']
            }
        }
        return ConfigManager(config)

    @pytest.fixture
    def file_monitor_with_container(self, mock_config_manager, temp_directories):
        """创建带容器的FileMonitor"""
        # Mock音频处理器
        mock_processor = MagicMock()
        mock_processor.process_audio_file.return_value = True

        # 创建FileMonitor
        file_monitor = FileMonitor(
            watch_folder=temp_directories['watch_folder'],
            file_processor_callback=mock_processor.process_audio_file,
            supported_formats={'.mp3', '.wav', '.m4a'},
            audio_processor=mock_processor
        )

        # 创建容器并注入FileMonitor
        container = MagicMock()
        container.get_file_monitor.return_value = file_monitor

        return file_monitor, container, mock_processor

    @pytest.fixture
    def upload_handler(self, mock_config_manager, file_monitor_with_container):
        """创建AudioUploadHandler"""
        file_monitor, container, mock_processor = file_monitor_with_container

        handler = AudioUploadHandler(
            config_manager=mock_config_manager,
            container=container
        )

        return handler, file_monitor, mock_processor

    def create_test_file(self, filename="test_audio.mp3", content=b"fake audio data"):
        """创建测试文件"""
        file_data = BytesIO(content)
        return FileStorage(
            stream=file_data,
            filename=filename,
            content_type="audio/mpeg"
        )

    def test_web_upload_config_passed_to_filemonitor(self, upload_handler, temp_directories):
        """测试: Web上传的Post-Processing配置正确传递到FileMonitor"""
        handler, file_monitor, mock_processor = upload_handler

        # 创建测试音频文件
        test_file = self.create_test_file("test_lecture.mp3")

        # Web上传配置: 只开启匿名化，关闭其他功能
        upload_metadata = {
            'content_type': 'lecture',
            'subcategory': 'CS101',
            'enable_anonymization': True,   # 开启
            'enable_summary': False,        # 关闭
            'enable_mindmap': False,        # 关闭
            'enable_diarization': False,    # 关闭
            'description': 'Test lecture with names'
        }

        # 执行上传
        result = handler.process_upload(
            file=test_file,
            content_type='lecture',
            subcategory='CS101',
            privacy_level='private',
            metadata=upload_metadata
        )

        # 验证上传成功
        assert result['status'] == 'success'
        processing_id = result['processing_id']

        # 检查文件是否保存到watch_folder
        watch_path = Path(temp_directories['watch_folder'])
        saved_files = list(watch_path.glob("*.mp3"))
        assert len(saved_files) == 1, f"Expected 1 file, found {len(saved_files)}"

        saved_file = saved_files[0]
        print(f"Saved file: {saved_file}")

        # 验证FileMonitor是否收到了正确的配置
        # 检查register_metadata是否被调用
        file_path_str = str(saved_file.resolve())

        # 检查元数据是否正确注册
        registered_metadata = file_monitor.processing_queue.pending_metadata.get(file_path_str)
        assert registered_metadata is not None, "Metadata should be registered in FileMonitor"

        # 验证配置内容
        processing_config = registered_metadata.get('processing_config', {})
        assert processing_config['enable_anonymization'] is True
        assert processing_config['enable_summary'] is False
        assert processing_config['enable_mindmap'] is False
        assert processing_config['enable_diarization'] is False
        assert processing_config['content_type'] == 'lecture'
        assert processing_config['subcategory'] == 'CS101'

        print(f"✅ Configuration correctly passed: {processing_config}")

    def test_filemonitor_processes_with_web_config(self, upload_handler, temp_directories):
        """测试: FileMonitor处理文件时使用Web上传的配置"""
        handler, file_monitor, mock_processor = upload_handler

        # 上传带特定配置的文件
        test_file = self.create_test_file("meeting_recording.wav")
        upload_metadata = {
            'enable_anonymization': False,
            'enable_summary': True,
            'enable_mindmap': True,
            'enable_diarization': True,
            'description': 'Important meeting'
        }

        # 上传文件
        result = handler.process_upload(
            file=test_file,
            content_type='meeting',
            subcategory='team_standup',
            privacy_level='private',
            metadata=upload_metadata
        )

        assert result['status'] == 'success'

        # 获取保存的文件路径
        watch_path = Path(temp_directories['watch_folder'])
        saved_files = list(watch_path.glob("*.wav"))
        assert len(saved_files) == 1

        saved_file_path = str(saved_files[0].resolve())

        # 模拟FileMonitor处理文件（调用_on_new_file）
        file_monitor._on_new_file(saved_file_path)

        # 验证AudioProcessor被调用，且传入了正确的配置
        mock_processor.process_audio_file.assert_called_once()

        # 检查传入AudioProcessor的参数
        call_args = mock_processor.process_audio_file.call_args
        called_file_path = call_args[0][0]  # 第一个位置参数
        called_privacy = call_args[0][1]    # 第二个位置参数
        called_metadata = call_args[1]['metadata']  # 关键字参数

        assert called_file_path == saved_file_path
        assert called_privacy == 'private'

        # 验证metadata包含Web上传的配置
        assert called_metadata['enable_anonymization'] is False
        assert called_metadata['enable_summary'] is True
        assert called_metadata['enable_mindmap'] is True
        assert called_metadata['enable_diarization'] is True
        assert called_metadata['content_type'] == 'meeting'
        assert called_metadata['subcategory'] == 'team_standup'
        assert called_metadata['description'] == 'Important meeting'

        print(f"✅ FileMonitor called AudioProcessor with config: {called_metadata}")

    def test_watchdog_fallback_preserves_config(self, upload_handler, temp_directories):
        """测试: Watchdog兜底机制也能保持配置"""
        handler, file_monitor, mock_processor = upload_handler

        # Mock enqueue_file_for_processing返回False（排队失败）
        with patch.object(file_monitor, 'enqueue_file_for_processing', return_value=False):
            test_file = self.create_test_file("fallback_test.mp3")
            upload_metadata = {
                'enable_anonymization': True,
                'enable_summary': False,
                'enable_mindmap': True,
                'enable_diarization': False,
                'content_type': 'lecture',
                'description': 'Fallback test'
            }

            # 上传文件（排队会失败，走watchdog路径）
            result = handler.process_upload(
                file=test_file,
                content_type='lecture',
                metadata=upload_metadata
            )

            # 上传应该成功（只是消息不同）
            assert result['status'] == 'success'
            assert 'watch-folder' in result['message'] or 'watch folder' in result['message']

        # 获取保存的文件
        watch_path = Path(temp_directories['watch_folder'])
        saved_files = list(watch_path.glob("*.mp3"))
        saved_file_path = str(saved_files[0].resolve())

        # 验证配置仍然被注册（即使排队失败）
        registered_metadata = file_monitor.processing_queue.pending_metadata.get(saved_file_path)
        assert registered_metadata is not None

        # 模拟watchdog检测到文件
        file_monitor._on_new_file(saved_file_path)

        # 验证处理时仍使用正确配置
        mock_processor.process_audio_file.assert_called_once()
        called_metadata = mock_processor.process_audio_file.call_args[1]['metadata']

        assert called_metadata['enable_anonymization'] is True
        assert called_metadata['enable_summary'] is False
        assert called_metadata['enable_mindmap'] is True
        assert called_metadata['description'] == 'Fallback test'

        print(f"✅ Watchdog fallback preserved config: {called_metadata}")

    def test_multiple_files_config_isolation(self, upload_handler, temp_directories):
        """测试: 多个文件的配置隔离"""
        handler, file_monitor, mock_processor = upload_handler

        # 上传第一个文件
        file1 = self.create_test_file("file1.mp3")
        result1 = handler.process_upload(
            file=file1,
            content_type='lecture',
            metadata={'enable_anonymization': True, 'enable_summary': False}
        )

        # 上传第二个文件，不同配置
        file2 = self.create_test_file("file2.mp3")
        result2 = handler.process_upload(
            file=file2,
            content_type='meeting',
            metadata={'enable_anonymization': False, 'enable_summary': True}
        )

        assert result1['status'] == 'success'
        assert result2['status'] == 'success'

        # 检查两个文件都有独立的配置
        watch_path = Path(temp_directories['watch_folder'])
        saved_files = sorted(list(watch_path.glob("*.mp3")))
        assert len(saved_files) == 2

        # 验证每个文件都有独立的元数据
        for saved_file in saved_files:
            file_path_str = str(saved_file.resolve())
            metadata = file_monitor.processing_queue.pending_metadata.get(file_path_str)
            assert metadata is not None

            config = metadata['processing_config']
            if 'file1' in saved_file.name:
                assert config['enable_anonymization'] is True
                assert config['enable_summary'] is False
                assert config['content_type'] == 'lecture'
            else:  # file2
                assert config['enable_anonymization'] is False
                assert config['enable_summary'] is True
                assert config['content_type'] == 'meeting'

        print("✅ Multiple files have isolated configurations")