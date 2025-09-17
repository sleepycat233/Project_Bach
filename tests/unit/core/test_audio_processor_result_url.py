import pytest


from src.core.audio_processor import AudioProcessor


class DummyConfigManager:
    """Minimal config manager stub for result URL tests."""

    def __init__(self, data):
        self._data = data

    def get_nested_config(self, *keys):
        current = self._data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current


@pytest.mark.parametrize(
    "config_data,privacy_level,expected",
    [
        (
            {'github': {'pages': {'url': 'https://example.com/docs'}}},
            'public',
            'https://example.com/docs/demo_result.html',
        ),
        (
            {'github': {'username': 'user123', 'repo_name': 'custom-repo'}},
            'public',
            'https://user123.github.io/custom-repo/demo_result.html',
        ),
        (
            {},
            'public',
            '/public/demo_result.html',
        ),
        (
            {},
            'private',
            '/private/demo_result.html',
        ),
    ],
)
def test_build_result_url(config_data, privacy_level, expected):
    config_manager = DummyConfigManager(config_data)
    result = AudioProcessor.build_result_url(config_manager, 'demo', privacy_level)
    assert result == expected


def test_build_result_url_without_config_manager():
    result_public = AudioProcessor.build_result_url(None, 'demo', 'public')
    result_private = AudioProcessor.build_result_url(None, 'demo', 'private')
    assert result_public == '/public/demo_result.html'
    assert result_private == '/private/demo_result.html'

