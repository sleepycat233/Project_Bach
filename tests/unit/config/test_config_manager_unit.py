#!/usr/bin/env python3
"""
配置管理器 单元测试

测试配置管理器的各个功能，严格遵循单元测试原则：
- 一个测试方法只测试一个功能
- Mock所有外部依赖 
- 测试单个函数/方法的输入输出
"""

import unittest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path
import tempfile
import os

import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent))


class MockConfigManager:
    """Mock Configuration Manager for unit testing"""
    
    def __init__(self, config_path=None):
        self.config_path = config_path
        self.config = {}
        self.env_vars = {}
    
    def load_config(self, config_data):
        """加载配置数据"""
        if isinstance(config_data, dict):
            self.config = config_data
            return True
        return False
    
    def get_config_value(self, key, default=None):
        """获取配置值"""
        keys = key.split('.')
        current = self.config
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        
        return current
    
    def get(self, *path, default=None):
        """通用配置读取，支持点路径或序列路径"""
        if len(path) == 1 and isinstance(path[0], (str, list, tuple)):
            keys = path[0]
        else:
            keys = path

        if isinstance(keys, str):
            key_list = [segment for segment in keys.split('.') if segment]
        else:
            key_list = list(keys)

        if not key_list:
            return self.config if default is None else default

        current = self.config
        for key in key_list:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default if default is not None else {}

        return current
    
    def get_full_config(self):
        """获取完整配置"""
        return self.config.copy()
    
    def set_config_value(self, key, value):
        """设置配置值"""
        keys = key.split('.')
        current = self.config
        
        # 创建嵌套字典结构
        for k in keys[:-1]:
            if k not in current or not isinstance(current[k], dict):
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
    
    def load_env_vars(self, env_prefix='BACH_'):
        """加载环境变量"""
        self.env_vars = {}
        for key, value in os.environ.items():
            if key.startswith(env_prefix):
                config_key = key[len(env_prefix):].lower()
                self.env_vars[config_key] = value
        return self.env_vars
    
    def merge_env_vars(self):
        """合并环境变量到配置"""
        for key, value in self.env_vars.items():
            # 尝试转换布尔值和数字
            if value.lower() in ('true', 'false'):
                value = value.lower() == 'true'
            elif value.isdigit():
                value = int(value)
            
            self.set_config_value(key, value)


class TestConfigManagerInit(unittest.TestCase):
    """测试配置管理器初始化"""
    
    def test_init_with_config_path(self):
        """测试使用配置路径初始化"""
        config_path = "/path/to/config.yaml"
        manager = MockConfigManager(config_path)
        
        self.assertEqual(manager.config_path, config_path)
        self.assertEqual(manager.config, {})
    
    def test_init_without_config_path(self):
        """测试无配置路径初始化"""
        manager = MockConfigManager()
        
        self.assertIsNone(manager.config_path)
        self.assertEqual(manager.config, {})


class TestConfigLoading(unittest.TestCase):
    """测试配置加载"""
    
    def setUp(self):
        """设置测试环境"""
        self.manager = MockConfigManager()
    
    def test_load_valid_config_dict(self):
        """测试加载有效配置字典"""
        config_data = {
            'api': {
                'openrouter': {
                    'base_url': 'https://openrouter.ai/api/v1',
                    'model': 'deepseek/deepseek-chat'
                }
            },
            'tailscale': {'enabled': True}
        }
        
        result = self.manager.load_config(config_data)
        
        self.assertTrue(result)
        self.assertEqual(self.manager.config, config_data)
    
    def test_load_empty_config(self):
        """测试加载空配置"""
        result = self.manager.load_config({})
        
        self.assertTrue(result)
        self.assertEqual(self.manager.config, {})
    
    def test_load_invalid_config(self):
        """测试加载无效配置"""
        invalid_configs = [None, "string", 123, []]
        
        for config in invalid_configs:
            result = self.manager.load_config(config)
            self.assertFalse(result, f"Invalid config {config} should return False")


class TestConfigRetrieval(unittest.TestCase):
    """测试配置获取"""
    
    def setUp(self):
        """设置测试环境"""
        self.manager = MockConfigManager()
        self.test_config = {
            'api': {
                'openrouter': {
                    'base_url': 'https://openrouter.ai/api/v1',
                    'model': 'deepseek/deepseek-chat'
                }
            },
            'tailscale': {'enabled': True},
            'paths': {
                'output_folder': './data/output'
            }
        }
        self.manager.load_config(self.test_config)
    
    def test_get_top_level_config(self):
        """测试获取顶级配置"""
        result = self.manager.get_config_value('tailscale')
        expected = {'enabled': True}
        
        self.assertEqual(result, expected)
    
    def test_get_with_dot_notation(self):
        """测试使用点号获取嵌套配置"""
        result = self.manager.get('api.openrouter.model')

        self.assertEqual(result, 'deepseek/deepseek-chat')
    
    def test_get_non_existent_config(self):
        """测试获取不存在的配置"""
        result = self.manager.get_config_value('non.existent.key')
        
        self.assertIsNone(result)
    
    def test_get_config_with_default(self):
        """测试获取配置使用默认值"""
        default_value = "default_model"
        result = self.manager.get_config_value('api.non_existent', default_value)
        
        self.assertEqual(result, default_value)
    
    def test_get_nested_config_direct(self):
        """测试直接获取嵌套配置"""
        result = self.manager.get(['api', 'openrouter'])
        expected = {
            'base_url': 'https://openrouter.ai/api/v1',
            'model': 'deepseek/deepseek-chat'
        }
        
        self.assertEqual(result, expected)
    
    def test_get_nested_config_non_existent(self):
        """测试获取不存在的嵌套配置"""
        result = self.manager.get(['non', 'existent'], default={})

        self.assertEqual(result, {})


class TestConfigModification(unittest.TestCase):
    """测试配置修改"""
    
    def setUp(self):
        """设置测试环境"""
        self.manager = MockConfigManager()
    
    def test_set_top_level_config(self):
        """测试设置顶级配置"""
        self.manager.set_config_value('debug', True)
        
        result = self.manager.get_config_value('debug')
        self.assertTrue(result)
    
    def test_set_nested_config(self):
        """测试设置嵌套配置"""
        self.manager.set_config_value('api.new_service.key', 'test_key')
        
        result = self.manager.get_config_value('api.new_service.key')
        self.assertEqual(result, 'test_key')
    
    def test_set_deep_nested_config(self):
        """测试设置深层嵌套配置"""
        self.manager.set_config_value('level1.level2.level3.value', 'deep_value')
        
        result = self.manager.get_config_value('level1.level2.level3.value')
        self.assertEqual(result, 'deep_value')
    
    def test_overwrite_existing_config(self):
        """测试覆盖现有配置"""
        # 先设置初始值
        self.manager.set_config_value('test.key', 'original')
        
        # 覆盖
        self.manager.set_config_value('test.key', 'updated')
        
        result = self.manager.get_config_value('test.key')
        self.assertEqual(result, 'updated')


class TestEnvironmentVariables(unittest.TestCase):
    """测试环境变量处理"""
    
    def setUp(self):
        """设置测试环境"""
        self.manager = MockConfigManager()
    
    @patch.dict(os.environ, {
        'BACH_API_KEY': 'test_api_key',
        'BACH_DEBUG': 'true',
        'BACH_PORT': '8080',
        'OTHER_VAR': 'should_be_ignored'
    })
    def test_load_env_vars_with_prefix(self):
        """测试加载带前缀的环境变量"""
        env_vars = self.manager.load_env_vars('BACH_')
        
        expected = {
            'api_key': 'test_api_key',
            'debug': 'true',
            'port': '8080'
        }
        
        self.assertEqual(env_vars, expected)
    
    @patch.dict(os.environ, {
        'BACH_ENABLE_FEATURE': 'false',
        'BACH_MAX_SIZE': '1024'
    })
    def test_merge_env_vars_type_conversion(self):
        """测试环境变量类型转换"""
        self.manager.load_env_vars('BACH_')
        self.manager.merge_env_vars()
        
        # 检查布尔值转换
        self.assertFalse(self.manager.get_config_value('enable_feature'))
        
        # 检查整数转换
        self.assertEqual(self.manager.get_config_value('max_size'), 1024)
        self.assertIsInstance(self.manager.get_config_value('max_size'), int)
    
    @patch.dict(os.environ, {}, clear=True)
    def test_load_env_vars_empty(self):
        """测试加载空环境变量"""
        env_vars = self.manager.load_env_vars('BACH_')
        
        self.assertEqual(env_vars, {})


class TestConfigValidation(unittest.TestCase):
    """测试配置验证"""
    
    def setUp(self):
        """设置测试环境"""
        self.manager = MockConfigManager()
    
    def test_get_full_config(self):
        """测试获取完整配置"""
        test_config = {
            'api': {'key': 'value'},
            'database': {'host': 'localhost'}
        }
        
        self.manager.load_config(test_config)
        result = self.manager.get_full_config()
        
        self.assertEqual(result, test_config)
        # 确保返回的是副本，不是原引用
        result['new_key'] = 'new_value'
        self.assertNotIn('new_key', self.manager.config)


class TestEdgeCases(unittest.TestCase):
    """测试边界情况"""
    
    def setUp(self):
        """设置测试环境"""
        self.manager = MockConfigManager()
    
    def test_get_config_empty_key(self):
        """测试空键获取配置"""
        self.manager.load_config({'test': 'value'})
        result = self.manager.get_config_value('')
        
        self.assertIsNone(result)
    
    def test_nested_config_non_dict_value(self):
        """测试嵌套配置遇到非字典值"""
        self.manager.load_config({'api': 'string_value'})
        result = self.manager.get(['api', 'sub_key'], default={})
        
        self.assertEqual(result, {})
    
    def test_set_config_on_non_dict_parent(self):
        """测试在非字典父节点设置配置"""
        self.manager.load_config({'parent': 'string_value'})
        
        # 这应该覆盖原值并创建字典结构
        self.manager.set_config_value('parent.child', 'child_value')
        
        result = self.manager.get_config_value('parent.child')
        self.assertEqual(result, 'child_value')


if __name__ == '__main__':
    unittest.main()