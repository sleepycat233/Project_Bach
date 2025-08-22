#!/usr/bin/env python3.11
"""
配置管理模块单元测试
"""

import unittest
import tempfile
import shutil
import os
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

# 添加src目录到Python路径
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from utils.config import ConfigManager, LoggingSetup, DirectoryManager


class TestConfigManager(unittest.TestCase):
    """测试配置管理器"""
    
    def setUp(self):
        """每个测试前的准备工作"""
        self.test_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.test_dir, 'test_config.yaml')
        self.valid_config = {
            'api': {
                'openrouter': {
                    'key': 'test-api-key',
                    'base_url': 'https://openrouter.ai/api/v1',
                    'models': {
                        'summary': 'deepseek/deepseek-chat',
                        'mindmap': 'openai/gpt-4o-mini'
                    }
                }
            },
            'paths': {
                'watch_folder': os.path.join(self.test_dir, 'watch_folder'),
                'data_folder': os.path.join(self.test_dir, 'data'),
                'output_folder': os.path.join(self.test_dir, 'output')
            },
            'spacy': {
                'model': 'zh_core_web_sm'
            },
            'whisperkit': {
                'model': 'medium',
                'language': 'en',
                'supported_languages': ['en', 'zh']
            },
            'logging': {
                'level': 'INFO',
                'file': os.path.join(self.test_dir, 'app.log')
            }
        }
        
        # 创建测试配置文件
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.valid_config, f)
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.test_dir)
    
    @patch('utils.env_manager.setup_project_environment')
    def test_load_valid_config(self, mock_setup_env):
        """测试加载有效配置文件"""
        mock_setup_env.side_effect = Exception("Force use direct loading")
        manager = ConfigManager(self.config_path)
        self.assertEqual(manager.get_full_config(), self.valid_config)
    
    def test_load_nonexistent_config(self):
        """测试加载不存在的配置文件"""
        with self.assertRaises(FileNotFoundError):
            ConfigManager('nonexistent.yaml')
    
    def test_load_invalid_yaml(self):
        """测试加载无效的YAML文件"""
        invalid_yaml_path = os.path.join(self.test_dir, 'invalid.yaml')
        with open(invalid_yaml_path, 'w') as f:
            f.write('invalid: yaml: content: [')
        
        with self.assertRaises(ValueError):
            ConfigManager(invalid_yaml_path)
    
    @patch('utils.env_manager.setup_project_environment')
    def test_validate_missing_required_keys(self, mock_setup_env):
        """测试验证缺少必要键的配置"""
        mock_setup_env.side_effect = Exception("Force use direct loading")
        incomplete_config = {'api': {'openrouter': {'key': 'test'}}}
        incomplete_path = os.path.join(self.test_dir, 'incomplete.yaml')
        
        with open(incomplete_path, 'w', encoding='utf-8') as f:
            yaml.dump(incomplete_config, f)
        
        with self.assertRaises(ValueError) as context:
            ConfigManager(incomplete_path)
        
        self.assertIn('配置文件缺少必要项', str(context.exception))
    
    @patch('utils.env_manager.setup_project_environment')
    def test_get_api_config(self, mock_setup_env):
        """测试获取API配置"""
        mock_setup_env.side_effect = Exception("Force use direct loading")
        manager = ConfigManager(self.config_path)
        api_config = manager.get_api_config()
        self.assertEqual(api_config, self.valid_config['api'])
    
    @patch('utils.env_manager.setup_project_environment')
    def test_get_openrouter_config(self, mock_setup_env):
        """测试获取OpenRouter配置"""
        mock_setup_env.side_effect = Exception("Force use direct loading")
        manager = ConfigManager(self.config_path)
        openrouter_config = manager.get_openrouter_config()
        self.assertEqual(openrouter_config, self.valid_config['api']['openrouter'])
    
    @patch('utils.env_manager.setup_project_environment')
    def test_get_paths_config(self, mock_setup_env):
        """测试获取路径配置"""
        mock_setup_env.side_effect = Exception("Force use direct loading")
        manager = ConfigManager(self.config_path)
        paths_config = manager.get_paths_config()
        self.assertEqual(paths_config, self.valid_config['paths'])
    
    @patch('utils.env_manager.setup_project_environment')
    def test_get_whisperkit_config(self, mock_setup_env):
        """测试获取WhisperKit配置"""
        mock_setup_env.side_effect = Exception("Force use direct loading")
        manager = ConfigManager(self.config_path)
        whisperkit_config = manager.get_whisperkit_config()
        self.assertEqual(whisperkit_config, self.valid_config['whisperkit'])
    
    def test_update_config(self):
        """测试更新配置项"""
        manager = ConfigManager(self.config_path)
        manager.update_config('api.openrouter.key', 'new-api-key')
        self.assertEqual(manager.get_openrouter_config()['key'], 'new-api-key')
    
    def test_update_nested_config(self):
        """测试更新嵌套配置项"""
        manager = ConfigManager(self.config_path)
        manager.update_config('whisperkit.model', 'large-v3')
        self.assertEqual(manager.get_whisperkit_config()['model'], 'large-v3')
    
    def test_save_config(self):
        """测试保存配置"""
        manager = ConfigManager(self.config_path)
        manager.update_config('api.openrouter.key', 'updated-key')
        
        new_path = os.path.join(self.test_dir, 'saved_config.yaml')
        manager.save_config(new_path)
        
        # 验证保存的配置
        with open(new_path, 'r', encoding='utf-8') as f:
            saved_config = yaml.safe_load(f)
        
        self.assertEqual(saved_config['api']['openrouter']['key'], 'updated-key')


class TestLoggingSetup(unittest.TestCase):
    """测试日志设置"""
    
    def setUp(self):
        """每个测试前的准备工作"""
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.test_dir)
    
    @patch('logging.getLogger')
    def test_setup_logging(self, mock_get_logger):
        """测试日志设置"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        log_config = {
            'level': 'DEBUG',
            'file': os.path.join(self.test_dir, 'test.log')
        }
        
        logger = LoggingSetup.setup_logging(log_config)
        
        # 验证日志文件目录被创建
        self.assertTrue(Path(log_config['file']).parent.exists())
        
        # 验证logger被正确配置
        mock_get_logger.assert_called_with('project_bach')
        mock_logger.setLevel.assert_called()
        mock_logger.addHandler.assert_called()


class TestDirectoryManager(unittest.TestCase):
    """测试目录管理"""
    
    def setUp(self):
        """每个测试前的准备工作"""
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.test_dir)
    
    def test_setup_directories(self):
        """测试目录创建"""
        paths_config = {
            'watch_folder': os.path.join(self.test_dir, 'watch'),
            'data_folder': os.path.join(self.test_dir, 'data'),
            'output_folder': os.path.join(self.test_dir, 'output')
        }
        
        with patch('logging.getLogger'):
            DirectoryManager.setup_directories(paths_config)
        
        # 验证主目录被创建
        self.assertTrue(Path(paths_config['watch_folder']).exists())
        self.assertTrue(Path(paths_config['data_folder']).exists())
        self.assertTrue(Path(paths_config['output_folder']).exists())
        
        # 验证子目录被创建
        self.assertTrue(Path(paths_config['data_folder'], 'transcripts').exists())
        self.assertTrue(Path(paths_config['data_folder'], 'logs').exists())
    
    def test_setup_directories_with_empty_paths(self):
        """测试处理空路径配置"""
        paths_config = {
            'watch_folder': '',
            'data_folder': None,
            'output_folder': os.path.join(self.test_dir, 'output')
        }
        
        with patch('logging.getLogger'):
            # 应该不抛出异常
            DirectoryManager.setup_directories(paths_config)
        
        # 只有非空路径应该被创建
        self.assertTrue(Path(paths_config['output_folder']).exists())


if __name__ == '__main__':
    unittest.main()