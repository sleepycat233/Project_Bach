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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from utils.config import ConfigManager, LoggingSetup, DirectoryManager


class TestConfigManager(unittest.TestCase):
    """测试配置管理器"""
    
    def setUp(self):
        """每个测试前的准备工作"""
        self.test_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.test_dir, 'test_config.yaml')
        self.valid_config = {
            'openrouter': {
                'key': 'test-api-key',
                'base_url': 'https://openrouter.ai/api/v1',
                'models': {
                    'summary': 'deepseek/deepseek-chat',
                    'mindmap': 'openai/gpt-4o-mini'
                },
                'rate_limit_tier': 'free'
            },
            'huggingface': {
                'token': 'test-hf-token'
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
        # 直接测试load_config方法，这样可以绕过env_manager的fallback逻辑
        manager = ConfigManager()
        with self.assertRaises(FileNotFoundError):
            manager.load_config('nonexistent.yaml')
    
    def test_load_invalid_yaml(self):
        """测试加载无效的YAML文件"""
        # 直接测试load_config方法
        manager = ConfigManager()
        invalid_yaml_path = os.path.join(self.test_dir, 'invalid.yaml')
        with open(invalid_yaml_path, 'w') as f:
            f.write('invalid: yaml: content: [')
        
        with self.assertRaises(ValueError):
            manager.load_config(invalid_yaml_path)
    
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
    def test_get_flattened_api_config(self, mock_setup_env):
        """测试获取扁平化后的API配置"""
        mock_setup_env.side_effect = Exception("Force use direct loading")
        manager = ConfigManager(self.config_path)
        
        # 测试各个API服务配置的单独获取
        openrouter_config = manager.get('openrouter', default={})
        huggingface_config = manager.get('huggingface', default={})

        # 验证配置结构正确
        self.assertIn('key', openrouter_config)
        self.assertIn('models', openrouter_config)
        self.assertIn('token', huggingface_config)
    
    @patch('utils.env_manager.setup_project_environment')
    def test_get_openrouter_config(self, mock_setup_env):
        """测试获取OpenRouter配置"""
        mock_setup_env.side_effect = Exception("Force use direct loading")
        manager = ConfigManager(self.config_path)
        openrouter_config = manager.get('openrouter', default={})
        self.assertEqual(openrouter_config, self.valid_config['openrouter'])
    
    @patch('utils.env_manager.setup_project_environment')
    def test_get_paths_config(self, mock_setup_env):
        """测试获取路径配置"""
        mock_setup_env.side_effect = Exception("Force use direct loading")
        manager = ConfigManager(self.config_path)
        paths_config = manager.get_paths_config()
        self.assertEqual(paths_config, self.valid_config['paths'])
    
    @patch('utils.env_manager.setup_project_environment')
    def test_get_mlx_whisper_config(self, mock_setup_env):
        """测试获取MLX Whisper配置 - 测试不存在的配置项返回None"""
        mock_setup_env.side_effect = Exception("Force use direct loading")
        manager = ConfigManager(self.config_path)
        mlx_config = manager.get('mlx_whisper', default={})
        # 由于测试配置中没有mlx_whisper项，应该返回默认值 {}
        self.assertEqual(mlx_config, {})
    
    def test_update_config(self):
        """测试更新配置项 - 跳过，update_config方法已移除"""
        # ConfigManager现在是只读的，不支持动态更新配置
        # 所有配置更改应通过编辑config.yaml文件完成
        self.skipTest("update_config method removed - ConfigManager is now read-only")
    
    def test_update_nested_config(self):
        """测试更新嵌套配置项 - 跳过，update_config方法已移除"""
        # ConfigManager现在是只读的，不支持动态更新配置
        # 所有配置更改应通过编辑config.yaml文件完成
        self.skipTest("update_config method removed - ConfigManager is now read-only")
    
    def test_save_config(self):
        """测试保存配置 - 跳过，save_config方法已移除"""
        # ConfigManager现在是只读的，不支持保存配置
        # 所有配置更改应通过编辑config.yaml文件完成
        self.skipTest("save_config method removed - ConfigManager is now read-only")
        
        # 验证保存的配置
        with open(new_path, 'r', encoding='utf-8') as f:
            saved_config = yaml.safe_load(f)
        
        self.assertEqual(saved_config['api']['openrouter']['key'], 'updated-key')
    
    @patch('utils.env_manager.setup_project_environment')
    def test_get_content_classification_config(self, mock_setup_env):
        """测试获取内容分类配置"""
        mock_setup_env.side_effect = Exception("Force use direct loading")
        
        # 添加内容分类配置到测试配置
        self.valid_config['content_classification'] = {
            'content_types': {
                'lecture': {
                    'icon': '🎓',
                    'display_name': 'Academic Lecture',
                    'subcategories': ['PHYS101', 'CS101', 'ML301']
                },
                'meeting': {
                    'icon': '🏢', 
                    'display_name': 'Meeting Recording',
                    'subcategories': ['team_meeting', 'project_review']
                }
            }
        }
        
        # 更新测试配置文件
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.valid_config, f)
        
        manager = ConfigManager(self.config_path)
        content_types = manager.get(['content_classification', 'content_types'], default={})
        
        # 验证内容类型配置
        self.assertIn('lecture', content_types)
        self.assertIn('meeting', content_types)
        
        # 验证lecture配置
        lecture_config = content_types['lecture']
        self.assertEqual(lecture_config['icon'], '🎓')
        self.assertEqual(lecture_config['display_name'], 'Academic Lecture')
        self.assertIn('PHYS101', lecture_config['subcategories'])
        self.assertIn('CS101', lecture_config['subcategories'])
        self.assertIn('ML301', lecture_config['subcategories'])
        
        # 验证meeting配置
        meeting_config = content_types['meeting']
        self.assertEqual(meeting_config['icon'], '🏢')
        self.assertIn('team_meeting', meeting_config['subcategories'])
        self.assertIn('project_review', meeting_config['subcategories'])
    
    @patch('utils.env_manager.setup_project_environment')
    def test_uploads_folder_path_consistency(self, mock_setup_env):
        """测试uploads目录路径一致性"""
        mock_setup_env.side_effect = Exception("Force use direct loading")
        
        # 更新配置使watch_folder和upload_folder一致
        self.valid_config['web_frontend'] = {
            'upload': {
                'upload_folder': './data/uploads',
                'organize_by_category': True,
                'create_subcategory_folders': True
            }
        }
        self.valid_config['paths']['watch_folder'] = './data/uploads'
        
        # 更新测试配置文件
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.valid_config, f)
        
        manager = ConfigManager(self.config_path)
        
        # 获取路径配置
        paths_config = manager.get_paths_config()
        upload_config = manager.get(['web_frontend', 'upload'], default={})
        
        # 验证一致性
        watch_folder = paths_config.get('watch_folder')
        upload_folder = upload_config.get('upload_folder')
        
        self.assertEqual(watch_folder, './data/uploads')
        self.assertEqual(upload_folder, './data/uploads')
        self.assertEqual(watch_folder, upload_folder)


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
        
        # 验证子目录被创建 (不再创建data/transcripts，现在使用output下的分层结构)
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


class TestGitHubPagesURLGeneration(unittest.TestCase):
    """测试GitHub Pages URL自动生成功能"""

    def setUp(self):
        """每个测试前的准备工作"""
        self.test_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.test_dir, 'test_config.yaml')

        # 创建包含GitHub配置的测试配置
        self.test_config = {
            'paths': {
                'watch_folder': './watch',
                'data_folder': './data',
                'output_folder': './output'
            },
            'logging': {
                'level': 'INFO',
                'file': './app.log'
            },
            'github': {
                'repo_name': 'Project_Bach',
                'pages': {
                    'enabled': True
                }
            }
        }

        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.test_config, f)

        # 保存原始环境变量
        self.original_env = os.environ.copy()

    def tearDown(self):
        """清理测试环境"""
        # 恢复原始环境变量
        os.environ.clear()
        os.environ.update(self.original_env)

        shutil.rmtree(self.test_dir)

    @patch('utils.env_manager.setup_project_environment')
    def test_github_pages_url_generation_with_username(self, mock_setup_env):
        """测试有GitHub用户名时自动生成pages_url"""
        mock_setup_env.side_effect = Exception("Force use direct loading")

        # 设置环境变量
        os.environ['GITHUB_USERNAME'] = 'testuser'

        manager = ConfigManager(self.config_path)

        # 验证自动生成的GitHub Pages URL
        github_config = manager.get('github', default={})
        self.assertEqual(github_config['username'], 'testuser')
        self.assertEqual(github_config['pages_url'], 'https://testuser.github.io/Project_Bach')

    @patch('utils.env_manager.setup_project_environment')
    def test_github_pages_url_generation_with_custom_repo(self, mock_setup_env):
        """测试自定义仓库名时的URL生成"""
        mock_setup_env.side_effect = Exception("Force use direct loading")

        # 修改配置中的仓库名
        self.test_config['github']['repo_name'] = 'CustomRepo'
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.test_config, f)

        # 设置环境变量
        os.environ['GITHUB_USERNAME'] = 'customuser'

        manager = ConfigManager(self.config_path)

        # 验证使用自定义仓库名的URL
        github_config = manager.get('github', default={})
        self.assertEqual(github_config['pages_url'], 'https://customuser.github.io/CustomRepo')

    @patch('utils.env_manager.setup_project_environment')
    def test_github_pages_url_disabled(self, mock_setup_env):
        """测试禁用GitHub Pages时不生成URL"""
        mock_setup_env.side_effect = Exception("Force use direct loading")

        # 禁用GitHub Pages
        self.test_config['github']['pages']['enabled'] = False
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.test_config, f)

        # 设置环境变量
        os.environ['GITHUB_USERNAME'] = 'testuser'

        manager = ConfigManager(self.config_path)

        # 验证不生成pages_url
        github_config = manager.get('github', default={})
        self.assertEqual(github_config['username'], 'testuser')
        self.assertIsNone(github_config.get('pages_url'))

    @patch('utils.env_manager.setup_project_environment')
    def test_github_pages_url_no_username(self, mock_setup_env):
        """测试没有GitHub用户名时不生成pages_url"""
        mock_setup_env.side_effect = Exception("Force use direct loading")

        # 不设置GITHUB_USERNAME环境变量
        manager = ConfigManager(self.config_path)

        # 验证GitHub配置存在但没有pages_url
        github_config = manager.get('github', default={})
        self.assertIsNotNone(github_config)  # 配置文件中的基础配置仍然存在
        self.assertEqual(github_config['repo_name'], 'Project_Bach')
        self.assertNotIn('pages_url', github_config)  # 没有生成pages_url
        self.assertNotIn('username', github_config)  # 没有username

    @patch('utils.env_manager.setup_project_environment')
    def test_github_pages_url_fallback_repo_name(self, mock_setup_env):
        """测试配置中没有repo_name时使用默认值"""
        mock_setup_env.side_effect = Exception("Force use direct loading")

        # 删除配置中的repo_name
        del self.test_config['github']['repo_name']
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.test_config, f)

        # 设置环境变量
        os.environ['GITHUB_USERNAME'] = 'fallbackuser'

        manager = ConfigManager(self.config_path)

        # 验证使用默认仓库名
        github_config = manager.get('github', default={})
        self.assertEqual(github_config['pages_url'], 'https://fallbackuser.github.io/Project_Bach')


if __name__ == '__main__':
    unittest.main()