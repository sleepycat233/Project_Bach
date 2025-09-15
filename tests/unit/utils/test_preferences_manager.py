#!/usr/bin/env python3
"""
PreferencesManager测试用例
Phase 7.2: Post-Processing选项和智能Subcategory管理的核心组件测试
"""

import unittest
import json
import tempfile
import os
from unittest.mock import patch, mock_open
from pathlib import Path

# 导入真实的PreferencesManager
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from utils.preferences_manager import PreferencesManager

# 保留MockPreferencesManager用于参考，但测试将使用真实实现
class MockPreferencesManager:
    """临时的PreferencesManager实现，用于测试设计"""
    
    def __init__(self, prefs_file='user_preferences.json'):
        self.prefs_file = prefs_file
        self.system_defaults = {
            'enable_anonymization': False,
            'enable_summary': False,
            'enable_mindmap': False,
            'diarization': False
        }
        self.prefs = {}
        self.load_preferences()
    
    def load_preferences(self):
        """加载用户偏好"""
        if os.path.exists(self.prefs_file):
            try:
                with open(self.prefs_file, 'r', encoding='utf-8') as f:
                    self.prefs = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.prefs = {}
        else:
            self.prefs = {}
    
    def get_effective_config(self, content_type, subcategory=None):
        """获取最终生效的配置（继承机制）"""
        config = self.system_defaults.copy()
        
        # 应用content_type的_defaults
        if content_type in self.prefs and '_defaults' in self.prefs[content_type]:
            defaults = self.prefs[content_type]['_defaults']
            config.update({k: v for k, v in defaults.items() if not k.startswith('_')})
        
        # 应用subcategory的覆盖（排除元数据）
        if subcategory and content_type in self.prefs and subcategory in self.prefs[content_type]:
            overrides = self.prefs[content_type][subcategory]
            config.update({k: v for k, v in overrides.items() if not k.startswith('_')})
        
        return config
    
    def save_config(self, content_type, subcategory, display_name, new_config):
        """保存配置（只存储差异）"""
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
    
    def get_subcategories_with_names(self, content_type):
        """获取subcategory列表（包含display_name）"""
        result = []
        if content_type in self.prefs:
            for key in self.prefs[content_type]:
                if not key.startswith('_'):  # 排除_defaults
                    subcat_data = self.prefs[content_type][key]
                    display_name = subcat_data.get('_display_name', key)
                    result.append({
                        'value': key,
                        'display_name': display_name
                    })
        return result
    
    def update_content_type_defaults(self, content_type, new_defaults):
        """更新content_type级别的默认值"""
        if content_type not in self.prefs:
            self.prefs[content_type] = {}
        
        # 计算与系统默认值的差异
        diff = {k: v for k, v in new_defaults.items() if self.system_defaults.get(k) != v}
        self.prefs[content_type]['_defaults'] = diff if diff else {}
        
        self._save_to_file()
    
    def _save_to_file(self):
        """保存到文件"""
        with open(self.prefs_file, 'w', encoding='utf-8') as f:
            json.dump(self.prefs, f, indent=2, ensure_ascii=False)


class TestPreferencesManager(unittest.TestCase):
    """PreferencesManager测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.prefs_file = os.path.join(self.temp_dir, 'test_preferences.json')
        self.manager = PreferencesManager(self.prefs_file)
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.prefs_file):
            os.remove(self.prefs_file)
        os.rmdir(self.temp_dir)
    
    def test_system_defaults(self):
        """测试系统默认值"""
        config = self.manager.get_effective_config('lecture', 'CS101')
        
        expected = {
            'enable_anonymization': False,
            'enable_summary': False,
            'enable_mindmap': False,
            'diarization': False
        }
        
        self.assertEqual(config, expected)
    
    def test_content_type_defaults_inheritance(self):
        """测试content_type级别的默认值继承"""
        # 设置lecture的默认值：启用摘要和思维导图
        self.manager.update_content_type_defaults('lecture', {
            'enable_anonymization': False,  # 保持系统默认
            'enable_summary': True,         # 覆盖系统默认
            'enable_mindmap': True,         # 覆盖系统默认
            'diarization': False           # 保持系统默认
        })
        
        # 测试新的subcategory应该继承这些默认值
        config = self.manager.get_effective_config('lecture', 'CS101')
        
        self.assertFalse(config['enable_anonymization'])  # 保持系统默认
        self.assertTrue(config['enable_summary'])  # 被content_type覆盖为True
        self.assertTrue(config['enable_mindmap'])  # 被content_type覆盖为True
        self.assertFalse(config['diarization'])  # 保持系统默认
    
    def test_subcategory_specific_overrides(self):
        """测试subcategory级别的覆盖"""
        # 先设置content_type默认值
        self.manager.update_content_type_defaults('lecture', {
            'enable_anonymization': False,
            'diarization': False
        })
        
        # 为特定subcategory设置覆盖
        self.manager.save_config('lecture', 'ML101', 'Machine Learning 101', {
            'enable_anonymization': True,  # 覆盖默认值
            'enable_summary': True,
            'enable_mindmap': True,
            'diarization': False
        })
        
        # 测试覆盖生效
        config = self.manager.get_effective_config('lecture', 'ML101')
        
        self.assertTrue(config['enable_anonymization'])  # 被ML101覆盖为True
        self.assertTrue(config['enable_summary'])
        self.assertTrue(config['enable_mindmap'])
        self.assertFalse(config['diarization'])
    
    def test_differential_storage(self):
        """测试差异化存储：只保存与默认值不同的部分"""
        # 设置content_type默认值
        self.manager.update_content_type_defaults('lecture', {
            'enable_anonymization': False,
            'enable_summary': True,
            'enable_mindmap': True,
            'diarization': False
        })
        
        # 保存一个只有部分差异的配置
        self.manager.save_config('lecture', 'CS101', 'Computer Science 101', {
            'enable_anonymization': True,  # 与默认值不同
            'enable_summary': True,        # 与默认值相同
            'enable_mindmap': True,        # 与默认值相同
            'diarization': False           # 与默认值相同
        })
        
        # 检查文件中只保存了差异
        with open(self.prefs_file, 'r') as f:
            data = json.load(f)
        
        cs101_data = data['lecture']['CS101']
        
        # 应该包含display_name和差异
        self.assertEqual(cs101_data['_display_name'], 'Computer Science 101')
        self.assertTrue(cs101_data['enable_anonymization'])
        
        # 不应该保存与默认值相同的配置
        self.assertNotIn('enable_summary', cs101_data)
        self.assertNotIn('enable_mindmap', cs101_data)
        self.assertNotIn('diarization', cs101_data)
    
    def test_subcategory_list_with_display_names(self):
        """测试获取subcategory列表及其显示名称"""
        # 添加几个subcategory
        self.manager.save_config('lecture', 'CS101', 'Computer Science 101', {
            'enable_anonymization': True
        })
        self.manager.save_config('lecture', 'PHYS202', 'Advanced Physics', {
            'diarization': True
        })
        
        # 获取列表
        subcategories = self.manager.get_subcategories_with_names('lecture')
        
        # 验证结果
        self.assertEqual(len(subcategories), 2)
        
        # 找到CS101
        cs101 = next((item for item in subcategories if item['value'] == 'CS101'), None)
        self.assertIsNotNone(cs101)
        self.assertEqual(cs101['display_name'], 'Computer Science 101')
        
        # 找到PHYS202
        phys202 = next((item for item in subcategories if item['value'] == 'PHYS202'), None)
        self.assertIsNotNone(phys202)
        self.assertEqual(phys202['display_name'], 'Advanced Physics')
    
    def test_empty_preferences_file(self):
        """测试空的偏好文件"""
        # 删除文件，模拟首次运行
        if os.path.exists(self.prefs_file):
            os.remove(self.prefs_file)
        
        # 重新初始化
        manager = PreferencesManager(self.prefs_file)
        
        # 应该返回系统默认值
        config = manager.get_effective_config('lecture', 'CS101')
        expected = {
            'enable_anonymization': False,
            'enable_summary': False,
            'enable_mindmap': False,
            'diarization': False
        }
        self.assertEqual(config, expected)
        
        # subcategory列表应该为空
        subcategories = manager.get_subcategories_with_names('lecture')
        self.assertEqual(len(subcategories), 0)
    
    def test_complex_inheritance_chain(self):
        """测试复杂的继承链：系统默认 → content_type默认 → subcategory覆盖"""
        # 1. 系统默认值（在代码中定义）
        # enable_anonymization: True, enable_summary: True, enable_mindmap: True, diarization: False
        
        # 2. 设置meeting的content_type默认值
        self.manager.update_content_type_defaults('meeting', {
            'enable_anonymization': True,   # 与系统默认相同
            'enable_summary': True,         # 与系统默认相同
            'enable_mindmap': False,        # 覆盖系统默认
            'diarization': True             # 覆盖系统默认
        })
        
        # 3. 设置standup的特定覆盖
        self.manager.save_config('meeting', 'standup', 'Daily Standup', {
            'enable_anonymization': True,   # 与content_type默认相同
            'enable_summary': False,        # 覆盖content_type默认
            'enable_mindmap': False,        # 与content_type默认相同
            'diarization': True             # 与content_type默认相同
        })
        
        # 测试最终配置
        config = self.manager.get_effective_config('meeting', 'standup')
        
        expected = {
            'enable_anonymization': True,   # 系统默认 = content_type默认 = subcategory
            'enable_summary': False,        # 被subcategory覆盖
            'enable_mindmap': False,        # 被content_type覆盖
            'diarization': True             # 被content_type覆盖
        }
        
        self.assertEqual(config, expected)
        
        # 检查存储的差异（standup只应该保存enable_summary: false）
        with open(self.prefs_file, 'r') as f:
            data = json.load(f)
        
        standup_data = data['meeting']['standup']
        
        # 应该包含display_name和差异
        self.assertEqual(standup_data['_display_name'], 'Daily Standup')
        self.assertFalse(standup_data['enable_summary'])  # 唯一的差异
        
        # 不应该保存与content_type默认相同的值
        self.assertNotIn('enable_anonymization', standup_data)
        self.assertNotIn('enable_mindmap', standup_data)
        self.assertNotIn('diarization', standup_data)


if __name__ == '__main__':
    unittest.main()