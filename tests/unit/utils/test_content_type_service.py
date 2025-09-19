import json
import os
from pathlib import Path

import pytest

from src.utils.content_type_service import ContentTypeService
from src.utils.preferences_manager import PreferencesManager


class DummyConfigManager:
    def __init__(self, config=None, data_folder='.'):
        self.config = config or {}
        self._paths = {'data_folder': data_folder}

    def get_paths_config(self):
        return self._paths


@pytest.fixture
def temp_preferences(tmp_path: Path):
    prefs_file = tmp_path / 'user_prefs.json'
    return PreferencesManager(str(prefs_file))


def test_service_returns_defaults_when_no_overrides(temp_preferences):
    manager = DummyConfigManager(data_folder=os.path.dirname(temp_preferences.prefs_file))
    service = ContentTypeService(manager, preferences_manager=temp_preferences)

    content_types = service.get_all()

    assert 'lecture' in content_types
    assert 'meeting' in content_types
    assert 'subcategories' in content_types['lecture']
    assert 'recommendations' in content_types['lecture']


def test_service_merges_preferences_subcategories(tmp_path: Path, temp_preferences):
    temp_preferences.save_config('lecture', 'MATH101', 'Advanced Calculus', {'enable_summary': True})

    manager = DummyConfigManager(data_folder=tmp_path)
    service = ContentTypeService(manager, preferences_manager=temp_preferences)

    content_types = service.get_all()
    lecture = content_types['lecture']
    assert any(sub['value'] == 'MATH101' for sub in lecture['subcategories'])


def test_service_includes_configured_types(tmp_path: Path, temp_preferences):
    config = {
        'content_classification': {
            'content_types': {
                'podcast': {
                    'icon': '🎙️',
                    'display_name': 'Podcast',
                    'has_subcategory': False,
                }
            }
        }
    }

    manager = DummyConfigManager(config=config, data_folder=tmp_path)
    service = ContentTypeService(manager, preferences_manager=temp_preferences)

    content_types = service.get_all()
    assert 'podcast' in content_types
    assert content_types['podcast']['display_name'] == 'Podcast'
    assert 'recommendations' in content_types['podcast']


def test_service_adds_preference_only_types(tmp_path: Path, temp_preferences):
    # Directly inject a custom content type into preferences to mimic legacy data
    temp_preferences.prefs['custom'] = {
        '_defaults': {},
        'my_topic': {'_display_name': 'My Topic'}
    }
    temp_preferences._save_to_file()

    manager = DummyConfigManager(data_folder=tmp_path)
    service = ContentTypeService(manager, preferences_manager=temp_preferences)

    content_types = service.get_all()
    assert 'custom' in content_types
    assert any(sub['value'] == 'my_topic' for sub in content_types['custom']['subcategories'])


def test_service_gets_effective_config(tmp_path: Path, temp_preferences):
    manager = DummyConfigManager(data_folder=tmp_path)
    service = ContentTypeService(manager, preferences_manager=temp_preferences)

    config = service.get_effective_config('lecture')

    assert isinstance(config, dict)
    assert 'enable_summary' in config
    assert config['enable_summary'] is False


def test_service_persists_subcategory_changes(tmp_path: Path, temp_preferences):
    manager = DummyConfigManager(data_folder=tmp_path)
    service = ContentTypeService(manager, preferences_manager=temp_preferences)

    service.save_subcategory('lecture', 'CS101', 'Computer Science 101', {'enable_summary': True})

    subcategories = service.get_subcategories('lecture')
    assert any(sub['value'] == 'CS101' for sub in subcategories)

    effective = service.get_effective_config('lecture', 'CS101')
    assert effective['enable_summary'] is True

    removed = service.delete_subcategory('lecture', 'CS101')
    assert removed is True
    subcategories_after = service.get_subcategories('lecture')
    assert all(sub['value'] != 'CS101' for sub in subcategories_after)


def test_service_reload_preferences(tmp_path: Path, temp_preferences):
    manager = DummyConfigManager(data_folder=tmp_path)
    service = ContentTypeService(manager, preferences_manager=temp_preferences)

    # Simulate external change by writing directly to the file
    prefs_path = Path(temp_preferences.prefs_file)
    prefs_data = temp_preferences.prefs.copy()
    prefs_data.setdefault('meeting', {})['external'] = {'_display_name': 'External Meeting'}
    prefs_path.write_text(json.dumps(prefs_data))

    service.reload_preferences()

    subcategories = service.get_subcategories('meeting')
    assert any(sub['value'] == 'external' for sub in subcategories)


def test_service_handles_recommendations(tmp_path: Path, temp_preferences):
    manager = DummyConfigManager(data_folder=tmp_path)
    service = ContentTypeService(manager, preferences_manager=temp_preferences)

    # 默认推荐应存在并为dict结构
    defaults = service.get_content_type_recommendations('lecture')
    assert isinstance(defaults, dict)
    assert 'english' in defaults
    assert 'multilingual' in defaults

    # 更新推荐并验证持久化
    service.save_content_type_recommendations('lecture', {
        'english': ['custom-model'],
        'multilingual': []
    })

    updated = service.get_content_type_recommendations('lecture')
    assert updated['english'] == ['custom-model']
    assert updated['multilingual'] == []

    content_types = service.get_all()
    assert content_types['lecture']['recommendations']['english'] == ['custom-model']
