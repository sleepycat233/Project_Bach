"""Tests for the new recommendation API endpoints."""

import json
import pytest
from unittest.mock import MagicMock, patch

from src.web_frontend.app import create_app


@pytest.fixture
def app():
    """Create test app instance."""
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def mock_content_type_service():
    """Create mock ContentTypeService."""
    mock_service = MagicMock()
    mock_service.get_content_type_recommendations.return_value = {
        'english': ['model1', 'model2'],
        'multilingual': ['model3']
    }
    return mock_service


class TestRecommendationAPIEndpoints:
    """Test suite for /api/preferences/recommendations endpoints."""

    def test_get_recommendations_success(self, client, app, mock_content_type_service):
        """Test successful GET of recommendations."""
        with app.app_context():
            app.config['CONTENT_TYPE_SERVICE'] = mock_content_type_service

            response = client.get('/api/preferences/recommendations/lecture')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'english' in data['data']
            assert 'multilingual' in data['data']
            assert data['data']['english'] == ['model1', 'model2']
            assert data['data']['multilingual'] == ['model3']

            mock_content_type_service.get_content_type_recommendations.assert_called_once_with('lecture')

    def test_get_recommendations_no_service(self, client, app):
        """Test GET when ContentTypeService is not initialized."""
        with app.app_context():
            app.config['CONTENT_TYPE_SERVICE'] = None

            response = client.get('/api/preferences/recommendations/lecture')

            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'error' in data

    def test_get_recommendations_service_error(self, client, app, mock_content_type_service):
        """Test GET when service raises an exception."""
        with app.app_context():
            mock_content_type_service.get_content_type_recommendations.side_effect = Exception('Service error')
            app.config['CONTENT_TYPE_SERVICE'] = mock_content_type_service

            response = client.get('/api/preferences/recommendations/meeting')

            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'Service error' in data['error']

    def test_save_recommendations_success(self, client, app, mock_content_type_service):
        """Test successful POST to save recommendations."""
        with app.app_context():
            app.config['CONTENT_TYPE_SERVICE'] = mock_content_type_service

            payload = {
                'english': ['new_model1'],
                'multilingual': ['new_model2', 'new_model3']
            }

            response = client.post(
                '/api/preferences/recommendations/lecture',
                json=payload,
                content_type='application/json'
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'message' in data
            assert 'lecture' in data['message']

            mock_content_type_service.save_content_type_recommendations.assert_called_once_with('lecture', payload)

    def test_save_recommendations_invalid_payload(self, client, app, mock_content_type_service):
        """Test POST with invalid payload (not a dict)."""
        with app.app_context():
            app.config['CONTENT_TYPE_SERVICE'] = mock_content_type_service

            # Send a list instead of dict
            response = client.post(
                '/api/preferences/recommendations/meeting',
                json=['invalid', 'payload'],
                content_type='application/json'
            )

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'Invalid payload' in data['error']

    def test_save_recommendations_empty_payload(self, client, app, mock_content_type_service):
        """Test POST with empty payload (should work - clear recommendations)."""
        with app.app_context():
            app.config['CONTENT_TYPE_SERVICE'] = mock_content_type_service
            mock_content_type_service.get_content_type_recommendations.return_value = {
                'english': [],
                'multilingual': []
            }

            response = client.post(
                '/api/preferences/recommendations/youtube',
                json={},
                content_type='application/json'
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True

            mock_content_type_service.save_content_type_recommendations.assert_called_once_with('youtube', {})

    def test_save_recommendations_no_service(self, client, app):
        """Test POST when ContentTypeService is not initialized."""
        with app.app_context():
            app.config['CONTENT_TYPE_SERVICE'] = None

            response = client.post(
                '/api/preferences/recommendations/lecture',
                json={'english': []},
                content_type='application/json'
            )

            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'error' in data

    def test_save_recommendations_service_error(self, client, app, mock_content_type_service):
        """Test POST when service raises an exception."""
        with app.app_context():
            mock_content_type_service.save_content_type_recommendations.side_effect = Exception('Save failed')
            app.config['CONTENT_TYPE_SERVICE'] = mock_content_type_service

            response = client.post(
                '/api/preferences/recommendations/other',
                json={'english': ['model']},
                content_type='application/json'
            )

            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'Save failed' in data['error']

    def test_recommendations_with_special_characters(self, client, app, mock_content_type_service):
        """Test recommendations with special characters in content_type."""
        with app.app_context():
            app.config['CONTENT_TYPE_SERVICE'] = mock_content_type_service

            # Test with special characters in URL
            response = client.get('/api/preferences/recommendations/my-special_type')

            assert response.status_code == 200
            mock_content_type_service.get_content_type_recommendations.assert_called_with('my-special_type')

    def test_recommendations_normalization(self, client, app, mock_content_type_service):
        """Test that recommendations are properly normalized."""
        with app.app_context():
            # Test that service returns normalized structure
            mock_content_type_service.get_content_type_recommendations.return_value = {
                'english': ['model1'],
                'multilingual': []  # Empty list should be preserved
            }
            app.config['CONTENT_TYPE_SERVICE'] = mock_content_type_service

            response = client.get('/api/preferences/recommendations/test')

            data = json.loads(response.data)
            assert isinstance(data['data']['english'], list)
            assert isinstance(data['data']['multilingual'], list)
            assert len(data['data']['multilingual']) == 0