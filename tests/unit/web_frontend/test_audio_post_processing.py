#!/usr/bin/env python3
"""Unit tests for post-processing flag propagation in audio upload flow."""

import os
import shutil
import sys
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure src package is importable
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from werkzeug.datastructures import FileStorage

from src.web_frontend.audio_upload_handler import AudioUploadHandler


class TestAudioUploadPostProcessing(unittest.TestCase):
    """Verify that user-selected post-processing options reach the processor."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.watch_dir = Path(self.temp_dir) / 'data' / 'uploads'
        self.watch_dir.mkdir(parents=True, exist_ok=True)

        self.mock_config = MagicMock()

        def get_side_effect(key, default=None):
            if key == 'paths.watch_folder':
                return str(self.watch_dir)
            return default

        self.mock_config.get.side_effect = get_side_effect

        self.mock_content_type_service = MagicMock()
        self.mock_content_type_service.get_subcategories.return_value = ['CS101']
        self.mock_content_type_service.get_effective_config.return_value = {
            'enable_anonymization': True,
            'enable_summary': True,
            'enable_mindmap': True,
            'diarization': True,
        }

        self.handler = AudioUploadHandler(
            self.mock_config,
            container=None,
            content_type_service=self.mock_content_type_service,
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def _make_file(self, name='lecture.wav') -> FileStorage:
        data = b'test audio data'
        file = FileStorage(stream=BytesIO(data), filename=name, content_type='audio/wav')
        return file

    @patch('src.web_frontend.audio_upload_handler.get_processing_service')
    @patch('src.web_frontend.audio_upload_handler.ProcessingTracker')
    def test_process_upload_respects_user_post_processing(
        self,
        mock_tracker_cls,
        mock_get_processing_service,
    ):
        """User overrides disable all post-processing even when defaults enable them."""

        tracker = MagicMock()
        tracker.processing_id = 'proc-123'
        mock_tracker_cls.return_value.__enter__.return_value = tracker

        processing_service = MagicMock()
        mock_get_processing_service.return_value = processing_service

        mock_file_monitor = MagicMock()
        mock_file_monitor.enqueue_file_for_processing.return_value = True

        mock_container = MagicMock()
        mock_container.get_file_monitor.return_value = mock_file_monitor
        mock_container.get_content_type_service.return_value = self.mock_content_type_service

        handler = AudioUploadHandler(
            self.mock_config,
            container=mock_container,
            content_type_service=self.mock_content_type_service,
        )

        metadata = {
            'audio_language': 'english',
            'enable_anonymization': 'off',
            'enable_summary': 'off',
            'enable_mindmap': 'off',
            'enable_diarization': 'off',
        }

        file = self._make_file()
        result = handler.process_upload(
            file=file,
            content_type='lecture',
            subcategory='CS101',
            privacy_level='private',
            metadata=metadata,
        )

        self.assertEqual(result['status'], 'success')
        mock_file_monitor.register_metadata.assert_called_once()
        register_args, register_kwargs = mock_file_monitor.register_metadata.call_args
        registered_path = register_args[0] if register_args else register_kwargs['file_path']
        registered_payload = register_args[1] if len(register_args) > 1 else register_kwargs['metadata']

        mock_file_monitor.enqueue_file_for_processing.assert_called_once()
        enqueue_args, enqueue_kwargs = mock_file_monitor.enqueue_file_for_processing.call_args
        queue_metadata = enqueue_args[1] if len(enqueue_args) > 1 else enqueue_kwargs['metadata']

        processing_metadata = registered_payload['processing_config']
        self.assertFalse(processing_metadata['enable_anonymization'])
        self.assertFalse(processing_metadata['enable_summary'])
        self.assertFalse(processing_metadata['enable_mindmap'])
        self.assertFalse(processing_metadata['enable_diarization'])
        self.assertFalse(processing_metadata['enable_anonymization'])
        self.assertFalse(processing_metadata['enable_summary'])
        self.assertFalse(processing_metadata['enable_mindmap'])
        self.assertFalse(processing_metadata['enable_diarization'])
        self.assertEqual(
            processing_metadata['post_processing'],
            {
                'enable_anonymization': False,
                'enable_summary': False,
                'enable_mindmap': False,
                'enable_diarization': False,
            },
        )
        self.assertEqual(processing_metadata['content_type'], 'lecture')
        self.assertEqual(processing_metadata['subcategory'], 'CS101')
        self.assertEqual(processing_metadata['privacy_level'], 'private')
        self.assertEqual(processing_metadata.get('audio_language'), 'english')
        self.assertNotIn('diarization', processing_metadata)
        self.assertEqual(queue_metadata['processing_id'], 'proc-123')
        self.assertEqual(queue_metadata['privacy_level'], 'private')
        self.assertEqual(queue_metadata['source'], 'web_upload')

        self.mock_content_type_service.get_effective_config.assert_called_once_with('lecture', 'CS101')


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
