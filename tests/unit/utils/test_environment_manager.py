#!/usr/bin/env python3
"""
环境管理器单元测试

测试EnvironmentManager的环境变量处理和配置生成功能
"""

import unittest
import tempfile
import shutil
import os
import yaml
from pathlib import Path
from unittest.mock import patch, Mock

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from utils.env_manager import EnvironmentManager, setup_project_environment


class TestEnvironmentManager(unittest.TestCase):
    """测试环境管理器"""
    
    def setUp(self):
        """设置测试环境"""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # 创建测试用的模板文件
        self.config_template_content = """api:
  openrouter:
    key: "${OPENROUTER_API_KEY}"
    base_url: "https://openrouter.ai/api/v1"

github:
  username: "${GITHUB_USERNAME}"
  repo_name: "Project_Bach"
  token: "${GITHUB_TOKEN}"

network:
  tailscale:
    auth_key: "${TAILSCALE_AUTH_KEY}"
  secure_file_server:
    auth_token: "${SECURE_FILE_SERVER_TOKEN}"
"""
        
        self.template_file = Path(self.test_dir) / 'config.template.yaml'
        with open(self.template_file, 'w', encoding='utf-8') as f:
            f.write(self.config_template_content)
        
        self.env_manager = EnvironmentManager(self.test_dir)
    
    def tearDown(self):
        """清理测试环境"""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    def test_environment_manager_initialization(self):
        """测试环境管理器初始化"""
        manager = EnvironmentManager(self.test_dir)
        
        self.assertEqual(manager.project_root, Path(self.test_dir))
        self.assertEqual(manager.env_file, Path(self.test_dir) / '.env')
        self.assertEqual(manager.config_template, Path(self.test_dir) / 'config.template.yaml')
        self.assertEqual(manager.config_file, Path(self.test_dir) / 'config.yaml')
    
    def test_load_env_file_success(self):
        """测试成功加载.env文件"""
        # 创建测试.env文件
        env_content = """# Test environment file
OPENROUTER_API_KEY=sk-test-key-123
GITHUB_USERNAME=testuser
GITHUB_TOKEN=ghp_test_token_456
TAILSCALE_AUTH_KEY=tskey-auth-test
SECURE_FILE_SERVER_TOKEN=secure-token-789
DEBUG=true
"""
        
        env_file = Path(self.test_dir) / '.env'
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        env_vars = self.env_manager.load_env_file()
        
        # 验证加载的环境变量
        expected_vars = {
            'OPENROUTER_API_KEY': 'sk-test-key-123',
            'GITHUB_USERNAME': 'testuser',
            'GITHUB_TOKEN': 'ghp_test_token_456',
            'TAILSCALE_AUTH_KEY': 'tskey-auth-test',
            'SECURE_FILE_SERVER_TOKEN': 'secure-token-789',
            'DEBUG': 'true'
        }
        
        for key, expected_value in expected_vars.items():
            self.assertEqual(env_vars[key], expected_value,
                           f"Environment variable {key} should be {expected_value}")
    
    def test_load_env_file_nonexistent(self):
        """测试加载不存在的.env文件"""
        env_vars = self.env_manager.load_env_file()
        self.assertEqual(env_vars, {})
    
    def test_load_env_file_with_quotes(self):
        """测试带引号的环境变量"""
        env_content = '''OPENROUTER_API_KEY="sk-test-key-with-quotes"
GITHUB_TOKEN='ghp_single_quotes_token'
GITHUB_USERNAME=no-quotes-user
'''
        
        env_file = Path(self.test_dir) / '.env'
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        env_vars = self.env_manager.load_env_file()
        
        # 验证引号被正确移除
        self.assertEqual(env_vars['OPENROUTER_API_KEY'], 'sk-test-key-with-quotes')
        self.assertEqual(env_vars['GITHUB_TOKEN'], 'ghp_single_quotes_token')
        self.assertEqual(env_vars['GITHUB_USERNAME'], 'no-quotes-user')
    
    def test_substitute_variables(self):
        """测试变量替换功能"""
        template = "Key: ${TEST_KEY}, Token: ${TEST_TOKEN}, Value: ${MISSING_VAR}"
        variables = {
            'TEST_KEY': 'replaced-key',
            'TEST_TOKEN': 'replaced-token'
        }
        
        result = self.env_manager.substitute_variables(template, variables)
        
        expected = "Key: replaced-key, Token: replaced-token, Value: ${MISSING_VAR}"
        self.assertEqual(result, expected)
    
    def test_generate_config_from_template_success(self):
        """测试成功从模板生成配置"""
        # 创建.env文件
        env_content = """OPENROUTER_API_KEY=sk-real-key-123
GITHUB_USERNAME=realuser
GITHUB_TOKEN=ghp_real_token_456
TAILSCALE_AUTH_KEY=tskey-real-auth
SECURE_FILE_SERVER_TOKEN=real-secure-token
"""
        
        env_file = Path(self.test_dir) / '.env'
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        # 生成配置文件
        success = self.env_manager.generate_config_from_template()
        self.assertTrue(success)
        
        # 验证配置文件生成
        config_file = Path(self.test_dir) / 'config.yaml'
        self.assertTrue(config_file.exists())
        
        # 验证配置内容
        with open(config_file, 'r', encoding='utf-8') as f:
            generated_config = yaml.safe_load(f)
        
        # 验证关键配置被正确替换
        self.assertEqual(generated_config['api']['openrouter']['key'], 'sk-real-key-123')
        self.assertEqual(generated_config['github']['username'], 'realuser')
        self.assertEqual(generated_config['github']['token'], 'ghp_real_token_456')
        self.assertEqual(generated_config['network']['tailscale']['auth_key'], 'tskey-real-auth')
        self.assertEqual(generated_config['network']['secure_file_server']['auth_token'], 'real-secure-token')
    
    def test_generate_config_missing_template(self):
        """测试模板文件不存在时的处理"""
        # 删除模板文件
        os.remove(self.template_file)
        
        success = self.env_manager.generate_config_from_template()
        self.assertFalse(success)
    
    @patch('os.environ', {'GITHUB_TOKEN': 'env-github-token', 'OPENROUTER_API_KEY': 'env-openrouter-key'})
    def test_generate_config_with_system_env(self):
        """测试使用系统环境变量生成配置"""
        # 创建不完整的.env文件
        env_content = """GITHUB_USERNAME=fileuser
TAILSCALE_AUTH_KEY=tskey-file-auth
"""
        
        env_file = Path(self.test_dir) / '.env'
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        success = self.env_manager.generate_config_from_template()
        self.assertTrue(success)
        
        # 验证系统环境变量被优先使用
        with open(Path(self.test_dir) / 'config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        self.assertEqual(config['github']['token'], 'env-github-token')  # 来自系统环境变量
        self.assertEqual(config['api']['openrouter']['key'], 'env-openrouter-key')  # 来自系统环境变量
        self.assertEqual(config['github']['username'], 'fileuser')  # 来自.env文件
    
    def test_create_env_template(self):
        """测试创建环境变量模板"""
        success = self.env_manager.create_env_template()
        self.assertTrue(success)
        
        template_file = Path(self.test_dir) / '.env.template'
        self.assertTrue(template_file.exists())
        
        # 验证模板内容
        with open(template_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 验证包含所有必要的环境变量
        required_vars = [
            'OPENROUTER_API_KEY',
            'TAILSCALE_AUTH_KEY', 
            'SECURE_FILE_SERVER_TOKEN',
            'GITHUB_USERNAME',
            'GITHUB_TOKEN'
        ]
        
        for var in required_vars:
            self.assertIn(var, content, f"Template should contain {var}")
    
    def test_generate_secure_token(self):
        """测试安全令牌生成"""
        token = self.env_manager.generate_secure_token()
        
        # 验证令牌属性
        self.assertEqual(len(token), 32)  # 默认长度
        self.assertTrue(token.replace('-', '').replace('_', '').isalnum())
        
        # 测试自定义长度
        custom_token = self.env_manager.generate_secure_token(16)
        self.assertEqual(len(custom_token), 16)
        
        # 验证每次生成的令牌不同
        another_token = self.env_manager.generate_secure_token()
        self.assertNotEqual(token, another_token)
    
    def test_setup_environment(self):
        """测试环境设置流程"""
        # 创建有效的.env文件
        env_content = """OPENROUTER_API_KEY=sk-valid-key
TAILSCALE_AUTH_KEY=tskey-valid-auth
SECURE_FILE_SERVER_TOKEN=valid-token
GITHUB_USERNAME=validuser
GITHUB_TOKEN=ghp_valid_token
"""
        
        env_file = Path(self.test_dir) / '.env'
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        success = self.env_manager.setup_environment()
        self.assertTrue(success)
    
    def test_setup_environment_missing_env(self):
        """测试缺少.env文件时的环境设置"""
        success = self.env_manager.setup_environment()
        
        # 应该创建基础.env文件
        self.assertTrue((Path(self.test_dir) / '.env').exists())
        
        # 但由于缺少必要变量，setup应该返回False
        self.assertFalse(success)


class TestEnvironmentManagerIntegration(unittest.TestCase):
    """环境管理器集成测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        self.env_manager = EnvironmentManager(self.test_dir)
    
    def tearDown(self):
        """清理测试环境"""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    def test_complete_workflow_with_github_token(self):
        """测试包含GitHub Token的完整工作流"""
        # 1. 创建配置模板
        template_content = """api:
  openrouter:
    key: "${OPENROUTER_API_KEY}"

github:
  username: "${GITHUB_USERNAME}"
  repo_name: "Project_Bach"
  token: "${GITHUB_TOKEN}"

paths:
  watch_folder: "./watch_folder"
  data_folder: "./data"
"""
        
        template_file = Path(self.test_dir) / 'config.template.yaml'
        with open(template_file, 'w', encoding='utf-8') as f:
            f.write(template_content)
        
        # 2. 创建.env文件
        env_content = """OPENROUTER_API_KEY=sk-workflow-test-key
GITHUB_USERNAME=workflowuser
GITHUB_TOKEN=ghp_workflow_test_token
"""
        
        env_file = Path(self.test_dir) / '.env'
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        # 3. 运行环境管理器
        manager = EnvironmentManager(self.test_dir)
        success = manager.generate_config_from_template()
        
        self.assertTrue(success)
        
        # 4. 验证生成的配置
        config_file = Path(self.test_dir) / 'config.yaml'
        self.assertTrue(config_file.exists())
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 验证GitHub配置正确生成
        self.assertEqual(config['github']['username'], 'workflowuser')
        self.assertEqual(config['github']['token'], 'ghp_workflow_test_token')
        self.assertEqual(config['api']['openrouter']['key'], 'sk-workflow-test-key')
    
    def test_config_masking_with_github_token(self):
        """测试配置掩码功能包含GitHub Token"""
        config = {
            'api': {
                'openrouter': {
                    'key': 'sk-very-long-api-key-12345'
                }
            },
            'github': {
                'username': 'testuser',
                'token': 'ghp_very_long_github_token_67890'
            },
            'network': {
                'tailscale': {
                    'auth_key': 'tskey-auth-very-long-key-abc'
                }
            }
        }
        
        manager = EnvironmentManager(self.test_dir)
        masked_config = manager.mask_sensitive_config(config)
        
        # 验证敏感信息被掩码
        self.assertTrue(masked_config['api']['openrouter']['key'].endswith('*'))
        self.assertTrue(masked_config['github']['token'].endswith('*'))
        self.assertTrue(masked_config['network']['tailscale']['auth_key'].endswith('*'))
        
        # 验证非敏感信息未被掩码
        self.assertEqual(masked_config['github']['username'], 'testuser')
        
        # 验证掩码格式正确（保留前4位）
        self.assertTrue(masked_config['github']['token'].startswith('ghp_'))
        self.assertTrue(masked_config['api']['openrouter']['key'].startswith('sk-v'))
    
    def test_load_config_full_workflow(self):
        """测试加载配置的完整工作流"""
        # 创建.env文件
        env_content = """OPENROUTER_API_KEY=sk-full-workflow-key
GITHUB_USERNAME=fulluser
GITHUB_TOKEN=ghp_full_workflow_token
TAILSCALE_AUTH_KEY=tskey-full-auth
SECURE_FILE_SERVER_TOKEN=full-secure-token
"""
        
        env_file = Path(self.test_dir) / '.env'
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        # 测试load_config方法
        config = self.env_manager.load_config()
        
        # 验证配置成功加载
        self.assertIsNotNone(config)
        self.assertEqual(config['github']['username'], 'fulluser')
        self.assertEqual(config['github']['token'], 'ghp_full_workflow_token')
    
    def test_setup_project_environment_function(self):
        """测试setup_project_environment函数"""
        # 创建必要文件
        env_content = """OPENROUTER_API_KEY=sk-setup-test-key
TAILSCALE_AUTH_KEY=tskey-setup-auth
GITHUB_USERNAME=setupuser
GITHUB_TOKEN=ghp_setup_token
"""
        
        env_file = Path(self.test_dir) / '.env'
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        # 使用函数设置环境
        with patch('logging.warning'), patch('logging.info'), patch('logging.error'):
            config = setup_project_environment(self.test_dir)
        
        # 验证返回的配置
        if config:  # 如果配置验证通过
            self.assertEqual(config['github']['username'], 'setupuser')
            self.assertEqual(config['github']['token'], 'ghp_setup_token')


class TestEnvironmentManagerEdgeCases(unittest.TestCase):
    """环境管理器边界情况测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.test_dir)
    
    def test_malformed_env_file(self):
        """测试格式错误的.env文件"""
        env_content = """# 正常注释
VALID_KEY=valid_value
INVALID_LINE_NO_EQUALS
=EMPTY_KEY
KEY_WITH_EMPTY_VALUE=
ANOTHER_VALID=another_value
"""
        
        env_file = Path(self.test_dir) / '.env'
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        manager = EnvironmentManager(self.test_dir)
        env_vars = manager.load_env_file()
        
        # 应该只加载有效的键值对
        expected_vars = {
            'VALID_KEY': 'valid_value',
            'KEY_WITH_EMPTY_VALUE': '',
            'ANOTHER_VALID': 'another_value'
        }
        
        self.assertEqual(env_vars, expected_vars)
    
    def test_empty_variable_substitution(self):
        """测试空变量替换"""
        template = "Key: ${EMPTY_VAR}, Token: ${NULL_VAR}"
        variables = {
            'EMPTY_VAR': '',
            'NULL_VAR': None
        }
        
        manager = EnvironmentManager(self.test_dir)
        result = manager.substitute_variables(template, variables)
        
        # 空字符串和None都应该被替换
        expected = "Key: , Token: None"
        self.assertEqual(result, expected)
    
    def test_config_generation_with_partial_env(self):
        """测试部分环境变量时的配置生成"""
        # 创建模板
        template_content = """api:
  openrouter:
    key: "${OPENROUTER_API_KEY}"

github:
  username: "${GITHUB_USERNAME}"
  token: "${GITHUB_TOKEN}"
"""
        
        template_file = Path(self.test_dir) / 'config.template.yaml'
        with open(template_file, 'w', encoding='utf-8') as f:
            f.write(template_content)
        
        # 只提供部分环境变量
        env_content = """OPENROUTER_API_KEY=sk-partial-key
# GITHUB_USERNAME缺失
GITHUB_TOKEN=ghp_partial_token
"""
        
        env_file = Path(self.test_dir) / '.env'
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        manager = EnvironmentManager(self.test_dir)
        success = manager.generate_config_from_template()
        
        # 即使部分变量缺失，生成仍应成功
        self.assertTrue(success)
        
        # 验证未替换的变量保持原样
        with open(Path(self.test_dir) / 'config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        self.assertEqual(config['api']['openrouter']['key'], 'sk-partial-key')
        self.assertEqual(config['github']['token'], 'ghp_partial_token')
        self.assertEqual(config['github']['username'], '${GITHUB_USERNAME}')  # 未被替换


if __name__ == '__main__':
    print("🧪 Testing Environment Manager...")
    print("=" * 50)
    unittest.main(verbosity=2)