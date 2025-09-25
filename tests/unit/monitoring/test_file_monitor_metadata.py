#!/usr/bin/env python3
"""Tests for FileMonitor metadata persistence workflow."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.monitoring.file_monitor import FileMonitor


class TestFileMonitorMetadata:
    """Ensure watch-folder processing reuses upload metadata."""

    def setup_method(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.watch_dir = Path(self.temp_dir.name) / 'uploads'
        self.watch_dir.mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        self.temp_dir.cleanup()

    def _create_audio_file(self, name: str = 'sample.mp3') -> Path:
        path = self.watch_dir / name
        path.write_bytes(b'fake audio data')
        return path

    def test_registered_metadata_is_merged_and_cleared(self):
        monitor = FileMonitor(
            watch_folder=str(self.watch_dir),
            file_processor_callback=MagicMock(),
            supported_formats={'.mp3'},
        )

        # Speed up stability checks
        monitor.stability_check_delay = 0
        monitor.stability_check_interval = 0

        audio_path = self._create_audio_file()

        monitor.register_metadata(str(audio_path), {
            'processing_id': 'abc-123',
            'processing_config': {
                'content_type': 'lecture',
                'enable_summary': False,
            }
        })

        with patch.object(monitor.processing_queue, 'add_file', return_value=True) as mock_add_file:
            monitor._on_new_file(str(audio_path))

        mock_add_file.assert_called_once()
        _, metadata_arg = mock_add_file.call_args[0]
        assert metadata_arg['processing_id'] == 'abc-123'
        assert metadata_arg['processing_config']['content_type'] == 'lecture'
        assert metadata_arg['processing_config']['enable_summary'] is False
        assert str(audio_path) not in monitor.processing_queue.pending_metadata
