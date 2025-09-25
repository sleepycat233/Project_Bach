#!/usr/bin/env python3
"""Tests for Flask upload route post-processing flag handling."""

import io
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure src package is importable
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.config import UploadSettings, SecuritySettings
from src.web_frontend.app import create_app


class TestUploadRoutePostProcessing(unittest.TestCase):
    """Ensure the /upload/audio route forwards checkbox values correctly."""

    def setUp(self):
        self.mock_config_manager = MagicMock()
        self.mock_config_manager.get_upload_settings.return_value = UploadSettings(max_file_size=10 * 1024 * 1024)
        self.mock_config_manager.get_security_settings.return_value = SecuritySettings(tailscale_only=False)

    @patch('src.web_frontend.app.AudioUploadHandler')
    @patch('src.web_frontend.app.ContentTypeService')
    @patch('src.web_frontend.app.get_global_container', return_value=None)
    def test_upload_audio_checkbox_propagation(
        self,
        _mock_get_container,
        mock_content_type_service_cls,
        mock_audio_handler_cls,
    ):
        mock_content_type_service = MagicMock()
        mock_content_type_service.get_effective_config.return_value = {
            'enable_anonymization': True,
            'enable_summary': True,
            'enable_mindmap': True,
            'diarization': True,
        }
        mock_content_type_service_cls.return_value = mock_content_type_service

        mock_handler = MagicMock()
        mock_handler.is_supported_format.return_value = True
        mock_handler.content_type_service = mock_content_type_service
        mock_handler.process_upload.return_value = {
            'status': 'success',
            'processing_id': 'abc123',
        }
        mock_audio_handler_cls.return_value = mock_handler

        app = create_app({
            'TESTING': True,
            'CONFIG_MANAGER': self.mock_config_manager,
        })

        data = {
            'content_type': 'lecture',
            'subcategory': 'CS101',
            'privacy_level': 'private',
            'audio_language': 'english',
            'whisper_model': 'whisper-small',
            'enable_anonymization': 'on',
            'enable_summary': '',
            'enable_mindmap': 'on',
            # enable_diarization omitted to simulate unchecked box
        }

        data['audio_file'] = (io.BytesIO(b'data'), 'test.wav')

        with app.test_client() as client:
            response = client.post('/upload/audio', data=data, content_type='multipart/form-data')

        self.assertEqual(response.status_code, 302)
        mock_handler.process_upload.assert_called_once()
        _, kwargs = mock_handler.process_upload.call_args
        metadata = kwargs['metadata']

        self.assertTrue(metadata['enable_anonymization'])
        self.assertFalse(metadata['enable_summary'])
        self.assertTrue(metadata['enable_mindmap'])
        self.assertFalse(metadata['enable_diarization'])


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
