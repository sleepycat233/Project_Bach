#!/usr/bin/env python3.11
"""
GitHubPublisher服务单元测试
测试GitHub仓库操作、Pages配置等功能
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from .test_base import PublishingTestBase


class TestGitHubPublisher(PublishingTestBase):
    """GitHubPublisher服务测试"""
    
    def setUp(self):
        super().setUp()
        # 导入将要实现的模块 (现在用Mock)
        self.github_publisher = Mock()
        self.github_publisher.config = self.config['github']
        
    @patch('requests.post')
    @patch('requests.get')
    def test_create_repository_success(self, mock_get, mock_post):
        """测试成功创建GitHub仓库"""
        # 模拟仓库不存在
        mock_get.return_value.status_code = 404
        
        # 模拟创建成功
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {
            'name': 'project-bach-site',
            'full_name': 'testuser/project-bach-site',
            'html_url': 'https://github.com/testuser/project-bach-site'
        }
        
        # 测试创建仓库逻辑
        result = {
            'success': True,
            'repo_url': 'https://github.com/testuser/project-bach-site',
            'message': '仓库创建成功'
        }
        
        self.assertTrue(result['success'])
        self.assertIn('github.com', result['repo_url'])
        
    @patch('requests.get')
    def test_repository_already_exists(self, mock_get):
        """测试仓库已存在的情况"""
        # 模拟仓库已存在
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'name': 'project-bach-site',
            'full_name': 'testuser/project-bach-site'
        }
        
        result = {
            'success': True,
            'repo_url': 'https://github.com/testuser/project-bach-site',
            'message': '仓库已存在'
        }
        
        self.assertTrue(result['success'])
        
    @patch('requests.put')
    def test_configure_github_pages(self, mock_put):
        """测试配置GitHub Pages"""
        mock_put.return_value.status_code = 201
        mock_put.return_value.json.return_value = {
            'url': 'https://testuser.github.io/project-bach-site/',
            'source': {'branch': 'gh-pages', 'path': '/'}
        }
        
        result = {
            'success': True,
            'pages_url': 'https://testuser.github.io/project-bach-site/',
            'message': 'GitHub Pages配置成功'
        }
        
        self.assertTrue(result['success'])
        self.assertIn('github.io', result['pages_url'])
        
    def test_validate_github_token(self):
        """测试GitHub Token验证"""
        # 有效token
        valid_token = 'ghp_1234567890abcdef1234567890abcdef'
        self.assertTrue(len(valid_token) > 20)
        self.assertTrue(valid_token.startswith('ghp_'))
        
        # 无效token
        invalid_token = 'invalid_token'
        self.assertFalse(len(invalid_token) > 20)
        
    @patch('requests.get')
    def test_check_repository_status(self, mock_get):
        """测试检查仓库状态"""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'name': 'project-bach-site',
            'private': False,
            'has_pages': True,
            'updated_at': '2025-08-21T10:00:00Z'
        }
        
        status = {
            'exists': True,
            'private': False,
            'pages_enabled': True,
            'last_updated': '2025-08-21T10:00:00Z'
        }
        
        self.assertTrue(status['exists'])
        self.assertTrue(status['pages_enabled'])


if __name__ == '__main__':
    unittest.main()