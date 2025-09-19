#!/usr/bin/env python3.11
"""
Content Type Service

Centralised access to content-type definitions combining defaults and user
preferences (config.yaml no longer provides overrides).
"""

from __future__ import annotations

import os
import threading
from copy import deepcopy
from typing import Dict, Any, List, Optional, Tuple

from .config import ConfigManager
from .content_type_defaults import DEFAULT_CONTENT_TYPES
from .preferences_manager import get_preferences_manager, PreferencesManager


class ContentTypeService:
    """Provides merged content-type metadata for the whole application."""

    def __init__(self, config_manager: ConfigManager, preferences_manager: Optional[PreferencesManager] = None):
        self.config_manager = config_manager
        paths_config = config_manager.get_paths_config()
        data_folder = paths_config.get('data_folder', './data')
        prefs_file = os.path.join(data_folder, 'user_preferences.json')
        if preferences_manager is None:
            preferences_manager = get_preferences_manager(prefs_file)
        self.preferences_manager: PreferencesManager = preferences_manager
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_all(self) -> Dict[str, Dict[str, Any]]:
        """Return merged content-type definitions."""
        with self._lock:
            content_types = self._build_base_content_types()

            # include types implicitly introduced by preferences
            for content_type in self._iter_preference_content_types():
                content_types.setdefault(
                    content_type,
                    {
                        'display_name': content_type.title(),
                    },
                )

            # attach subcategory lists & recommendation overrides
            for key in list(content_types.keys()):
                subcategories = self.preferences_manager.get_subcategories_with_names(key)
                has_custom_recs, recommendations = self._get_recommendations_for_content_type(key)

                content_types[key] = {
                    **content_types[key],
                    'subcategories': subcategories,
                }

                if has_custom_recs or 'recommendations' in content_types[key]:
                    content_types[key]['recommendations'] = recommendations

            return content_types

    def get_subcategories(self, content_type: str) -> List[Dict[str, str]]:
        with self._lock:
            return self.preferences_manager.get_subcategories_with_names(content_type)

    def get_preferences_manager(self) -> PreferencesManager:
        """Expose the underlying preferences manager for mutation APIs."""
        return self.preferences_manager

    def get_effective_config(self, content_type: str, subcategory: Optional[str] = None) -> Dict[str, Any]:
        """Return the effective preference config for a content type/subcategory."""
        with self._lock:
            return self.preferences_manager.get_effective_config(content_type, subcategory)

    def save_subcategory(
        self,
        content_type: str,
        subcategory: str,
        display_name: str,
        config: Dict[str, Any],
    ) -> None:
        """Persist a subcategory configuration via the preferences manager."""
        with self._lock:
            self.preferences_manager.save_config(content_type, subcategory, display_name, config)

    def delete_subcategory(self, content_type: str, subcategory: str) -> bool:
        """Remove a subcategory from preferences if it exists."""
        with self._lock:
            return self.preferences_manager.delete_subcategory(content_type, subcategory)

    def reload_preferences(self) -> None:
        """Force the underlying preferences manager to reload from disk."""
        with self._lock:
            self.preferences_manager.load_preferences()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _build_base_content_types(self) -> Dict[str, Dict[str, Any]]:
        base: Dict[str, Dict[str, Any]] = deepcopy(DEFAULT_CONTENT_TYPES)

        for key, data in base.items():
            if 'display_name' not in data:
                data['display_name'] = key.title()
            data['recommendations'] = self._normalize_recommendations(data.get('recommendations'))

        return base

    def _iter_preference_content_types(self) -> List[str]:
        return [
            key
            for key in self.preferences_manager.prefs.keys()
            if not key.startswith('_')
        ]

    def _get_recommendations_for_content_type(self, content_type: str) -> Tuple[bool, Dict[str, List[str]]]:
        """Return preference overrides if present, otherwise normalized config recommendations."""
        pref_recommendations = self.preferences_manager.get_content_type_recommendations(content_type)
        if pref_recommendations is not None:
            return True, pref_recommendations

        base_entry = DEFAULT_CONTENT_TYPES.get(content_type, {})
        return False, self._normalize_recommendations(base_entry.get('recommendations'))

    @staticmethod
    def _normalize_recommendations(recommendations: Optional[Any]) -> Dict[str, List[str]]:
        """Normalize recommendation data to the standard structure."""
        if isinstance(recommendations, dict):
            english = recommendations.get('english') or []
            multilingual = recommendations.get('multilingual') or []
        elif isinstance(recommendations, list):
            english = recommendations
            multilingual = []
        else:
            english = []
            multilingual = []

        return {
            'english': [str(item) for item in english],
            'multilingual': [str(item) for item in multilingual],
        }

    def get_content_type_recommendations(self, content_type: str) -> Dict[str, List[str]]:
        """Expose recommendations for external callers (normalized)."""
        _, recommendations = self._get_recommendations_for_content_type(content_type)
        return recommendations

    def save_content_type_recommendations(self, content_type: str, recommendations: Dict[str, Any]) -> None:
        """Persist recommendations via preferences manager."""
        normalized = self._normalize_recommendations(recommendations)
        with self._lock:
            self.preferences_manager.save_content_type_recommendations(content_type, normalized)
