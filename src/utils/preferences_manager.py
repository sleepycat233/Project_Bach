#!/usr/bin/env python3
"""
用户偏好管理器
Phase 7.2: 智能Subcategory管理和Post-Processing选择器的核心组件

实现差异化存储和智能继承机制：
- 系统默认值 → content_type默认值 → subcategory覆盖
- 只存储与默认值不同的配置，节省存储空间
- 支持display_name等元数据管理
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path


class PreferencesManager:
    """用户偏好管理器

    负责管理用户的处理偏好，包括：
    - Post-processing选项（匿名化、摘要、思维导图、说话人分离）
    - Subcategory的创建和配置
    - 差异化存储（只保存与默认值不同的部分）
    - 继承机制（系统默认 → content_type默认 → subcategory覆盖）
    """

    def __init__(self, prefs_file: str = 'user_preferences.json'):
        """初始化偏好管理器

        Args:
            prefs_file: 偏好文件路径
        """
        self.prefs_file = prefs_file
        self.logger = logging.getLogger(__name__)

        # 加载用户偏好（包含系统默认值）
        self.prefs = {}
        self.load_preferences()

        # 从文件中获取系统默认值，如果不存在则使用fallback
        self.system_defaults = self.prefs.get('_system_defaults', {
            'enable_anonymization': False,
            'enable_summary': False,
            'enable_mindmap': False,
            'diarization': False
        })

    def load_preferences(self) -> None:
        """从文件加载用户偏好"""
        if os.path.exists(self.prefs_file):
            try:
                with open(self.prefs_file, 'r', encoding='utf-8') as f:
                    self.prefs = json.load(f)
                self.logger.debug(f"Loaded preferences from {self.prefs_file}")
            except (json.JSONDecodeError, IOError) as e:
                self.logger.warning(f"Failed to load preferences: {e}, using defaults")
                self.prefs = {}
        else:
            # 首次运行，创建包含系统默认值的配置
            self.prefs = {
                '_system_defaults': {
                    'enable_anonymization': False,
                    'enable_summary': False,
                    'enable_mindmap': False,
                    'diarization': False
                },
                'lecture': {
                    '_defaults': {
                        'diarization': False  # 讲座默认不启用diarization
                    }
                },
                'meeting': {
                    '_defaults': {
                        'diarization': True   # 会议默认启用diarization
                    }
                },
                '_media_defaults': {
                    'youtube': {
                        'enable_anonymization': False,
                        'enable_summary': False,
                        'enable_mindmap': False,
                        'diarization': False,
                        '_recommendations': {
                            'english': ['whisper-tiny-mlx'],
                            'multilingual': ['whisper-large-v3-mlx']
                        }
                    }
                }
            }
            self._save_to_file()
            self.logger.debug("Created new preferences file with defaults")

    def get_effective_config(self, content_type: str, subcategory: Optional[str] = None) -> Dict[str, Any]:
        """获取最终生效的配置（继承机制）

        继承优先级：
        1. 系统默认值（硬编码）
        2. content_type的_defaults覆盖
        3. subcategory的特定覆盖

        Args:
            content_type: 内容类型 (lecture, meeting等)
            subcategory: 子分类 (CS101, standup等)，可选

        Returns:
            最终生效的配置字典
        """
        # 1. 从系统默认值开始
        config = self.system_defaults.copy()

        if content_type in self.prefs:
            # 2. 应用content_type的_defaults
            if '_defaults' in self.prefs[content_type]:
                defaults = self.prefs[content_type]['_defaults']
                # 只应用非元数据字段
                config.update({k: v for k, v in defaults.items() if not k.startswith('_')})

            # 3. 应用subcategory的覆盖
            if subcategory and subcategory in self.prefs[content_type]:
                overrides = self.prefs[content_type][subcategory]
                # 只应用非元数据字段
                config.update({k: v for k, v in overrides.items() if not k.startswith('_')})
        else:
            media_defaults = self.prefs.get('_media_defaults', {})
            if content_type in media_defaults:
                config.update({k: v for k, v in media_defaults[content_type].items() if not k.startswith('_')})

        return config

    @staticmethod
    def _normalize_recommendations(recommendations: Optional[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Normalize recommendation structure to {english: [], multilingual: []}."""
        if isinstance(recommendations, dict):
            english = recommendations.get('english') or []
            multilingual = recommendations.get('multilingual') or []
        elif isinstance(recommendations, list):
            english = recommendations
            multilingual = []
        else:
            english = []
            multilingual = []

        # Ensure lists and remove falsy entries while preserving order
        return {
            'english': [str(item) for item in english],
            'multilingual': [str(item) for item in multilingual],
        }

    def save_config(self, content_type: str, subcategory: str, display_name: str, new_config: Dict[str, Any]) -> None:
        """保存配置（差异化存储）

        只保存与有效默认值不同的配置，节省存储空间

        Args:
            content_type: 内容类型
            subcategory: 子分类名称
            display_name: 显示名称
            new_config: 新的配置
        """
        # 确保content_type存在
        if content_type not in self.prefs:
            self.prefs[content_type] = {'_defaults': {}}

        # 获取有效的defaults（合并系统默认和content_type默认）
        content_defaults = self.prefs[content_type].get('_defaults', {})
        effective_defaults = self.system_defaults.copy()
        effective_defaults.update(content_defaults)

        # 计算与有效defaults的差异
        diff = {k: v for k, v in new_config.items()
                if effective_defaults.get(k) != v and not k.startswith('_')}

        # 保存：元数据 + 配置差异
        self.prefs[content_type][subcategory] = {'_display_name': display_name}
        if diff:  # 只有差异才保存
            self.prefs[content_type][subcategory].update(diff)

        self._save_to_file()
        self.logger.debug(f"Saved config for {content_type}/{subcategory}: {diff}")

    def get_content_type_recommendations(self, content_type: str) -> Optional[Dict[str, List[str]]]:
        """Get stored model recommendations for a content type, if any."""
        if content_type in self.prefs:
            recommendations = self.prefs[content_type].get('_recommendations')
            if recommendations is None:
                return None
            return self._normalize_recommendations(recommendations)

        media_defaults = self.prefs.get('_media_defaults', {})
        if content_type in media_defaults:
            media_recs = media_defaults[content_type].get('_recommendations')
            if media_recs is None:
                return None
            return self._normalize_recommendations(media_recs)

        return None

    def save_content_type_recommendations(self, content_type: str,
                                          recommendations: Dict[str, Any]) -> None:
        """Persist model recommendations for a content type."""
        normalized = self._normalize_recommendations(recommendations)

        if content_type in self.prefs:
            self.prefs[content_type].setdefault('_defaults', {})
            self.prefs[content_type]['_recommendations'] = normalized
        else:
            media_defaults = self.prefs.setdefault('_media_defaults', {})
            media_entry = media_defaults.setdefault(content_type, {})
            media_entry['_recommendations'] = normalized

        self._save_to_file()
        self.logger.debug(
            "Saved recommendations for %s: english=%s, multilingual=%s",
            content_type,
            normalized['english'],
            normalized['multilingual'],
        )

    def get_subcategories_with_names(self, content_type: str) -> List[Dict[str, str]]:
        """获取某个content_type的所有subcategory及其显示名称

        Args:
            content_type: 内容类型

        Returns:
            包含value和display_name的字典列表
        """
        result = []
        if content_type in self.prefs:
            for key in self.prefs[content_type]:
                if not key.startswith('_'):  # 排除_defaults等元数据
                    subcat_data = self.prefs[content_type][key]
                    display_name = subcat_data.get('_display_name', key)
                    result.append({
                        'value': key,
                        'display_name': display_name
                    })

        return result

    def update_content_type_defaults(self, content_type: str, new_defaults: Dict[str, Any]) -> None:
        """更新content_type级别的默认值

        Args:
            content_type: 内容类型
            new_defaults: 新的默认值配置
        """
        if content_type not in self.prefs:
            self.prefs[content_type] = {}

        # 计算与系统默认值的差异
        diff = {k: v for k, v in new_defaults.items()
                if self.system_defaults.get(k) != v and not k.startswith('_')}

        self.prefs[content_type]['_defaults'] = diff if diff else {}

        self._save_to_file()
        self.logger.debug(f"Updated {content_type} defaults: {diff}")

    def get_subcategory_info(self, content_type: str, subcategory: str) -> Dict[str, Any]:
        """获取subcategory的完整信息（包括display_name和配置）

        Args:
            content_type: 内容类型
            subcategory: 子分类名称

        Returns:
            包含display_name和config的字典
        """
        if (content_type in self.prefs and
            subcategory in self.prefs[content_type]):
            subcat_data = self.prefs[content_type][subcategory]
            return {
                'display_name': subcat_data.get('_display_name', subcategory),
                'config': {k: v for k, v in subcat_data.items() if not k.startswith('_')}
            }

        return {
            'display_name': subcategory,
            'config': {}
        }

    def delete_subcategory(self, content_type: str, subcategory: str) -> bool:
        """删除subcategory

        Args:
            content_type: 内容类型
            subcategory: 子分类名称

        Returns:
            是否成功删除
        """
        if (content_type in self.prefs and
            subcategory in self.prefs[content_type] and
            not subcategory.startswith('_')):

            del self.prefs[content_type][subcategory]
            self._save_to_file()
            self.logger.debug(f"Deleted {content_type}/{subcategory}")
            return True

        return False

    def get_content_types_config(self) -> Dict[str, Dict[str, Any]]:
        """获取所有content_type的基本信息和subcategory列表

        适用于前端API调用

        Returns:
            content_type配置字典
        """
        result = {}

        # 从config.yaml解析基本信息（如果有的话）
        # 这里假设调用方会提供content_type的基本信息

        # 添加subcategory信息
        for content_type in self.prefs:
            if content_type not in result:
                result[content_type] = {}

            result[content_type]['subcategories'] = self.get_subcategories_with_names(content_type)

        return result

    def _save_to_file(self) -> None:
        """保存偏好到文件"""
        try:
            # 确保目录存在
            prefs_path = Path(self.prefs_file)
            prefs_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.prefs_file, 'w', encoding='utf-8') as f:
                json.dump(self.prefs, f, indent=2, ensure_ascii=False)

            self.logger.debug(f"Saved preferences to {self.prefs_file}")

        except (IOError, OSError) as e:
            self.logger.error(f"Failed to save preferences: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """获取使用统计信息

        Returns:
            统计信息字典
        """
        stats = {
            'total_content_types': len(self.prefs),
            'total_subcategories': 0,
            'content_types': {}
        }

        for content_type, data in self.prefs.items():
            subcategory_count = len([k for k in data.keys() if not k.startswith('_')])
            stats['total_subcategories'] += subcategory_count
            stats['content_types'][content_type] = {
                'subcategory_count': subcategory_count,
                'has_custom_defaults': '_defaults' in data and bool(data['_defaults'])
            }

        return stats


# 全局实例
_preferences_manager = None

def get_preferences_manager(prefs_file: str = 'user_preferences.json') -> PreferencesManager:
    """获取全局偏好管理器实例（单例模式）

    Args:
        prefs_file: 偏好文件路径

    Returns:
        PreferencesManager实例
    """
    global _preferences_manager
    if _preferences_manager is None:
        _preferences_manager = PreferencesManager(prefs_file)
    return _preferences_manager
