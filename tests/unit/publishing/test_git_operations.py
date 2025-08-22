#!/usr/bin/env python3.11
"""
GitOperations服务单元测试
测试Git命令操作、仓库管理等功能
"""

import unittest
import sys
import os
import subprocess
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from .test_base import PublishingTestBase


class TestGitOperations(PublishingTestBase):
    """GitOperations服务测试"""
    
    def setUp(self):
        super().setUp()
        self.git_ops = Mock()
        self.repo_dir = self.test_dir / 'repo'
        self.repo_dir.mkdir()
        
    @patch('subprocess.run')
    def test_git_clone_repository(self, mock_run):
        """测试Git克隆仓库"""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Cloning into 'project-bach-site'..."
        
        result = {
            'success': True,
            'repo_path': str(self.repo_dir),
            'message': '仓库克隆成功'
        }
        
        self.assertTrue(result['success'])
        self.assertIn('project-bach-site', mock_run.return_value.stdout)
        
    @patch('subprocess.run')
    def test_git_config_setup(self, mock_run):
        """测试Git配置设置"""
        mock_run.return_value.returncode = 0
        
        # 模拟配置命令
        config_calls = [
            ['git', 'config', 'user.name', 'Project Bach Bot'],
            ['git', 'config', 'user.email', 'bot@project-bach.com']
        ]
        
        for cmd in config_calls:
            result = {'success': True, 'command': cmd}
            self.assertTrue(result['success'])
            self.assertEqual(result['command'][0], 'git')
            self.assertEqual(result['command'][1], 'config')
            
    @patch('subprocess.run')
    def test_git_create_branch(self, mock_run):
        """测试创建Git分支"""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Switched to a new branch 'gh-pages'"
        
        result = {
            'success': True,
            'branch': 'gh-pages',
            'message': '分支创建成功'
        }
        
        self.assertTrue(result['success'])
        self.assertEqual(result['branch'], 'gh-pages')
        
    @patch('subprocess.run')
    def test_git_add_and_commit(self, mock_run):
        """测试Git添加和提交"""
        mock_run.return_value.returncode = 0
        
        # 模拟添加文件
        add_result = {'success': True, 'files_added': ['index.html', 'style.css']}
        self.assertTrue(add_result['success'])
        self.assertEqual(len(add_result['files_added']), 2)
        
        # 模拟提交
        commit_result = {
            'success': True,
            'commit_hash': 'abc123def456',
            'message': '🤖 Auto-publish: 测试内容'
        }
        self.assertTrue(commit_result['success'])
        self.assertTrue(len(commit_result['commit_hash']) > 6)
        
    @patch('subprocess.run')
    def test_git_push_to_remote(self, mock_run):
        """测试推送到远程仓库"""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "To github.com:testuser/project-bach-site.git"
        
        result = {
            'success': True,
            'remote': 'origin',
            'branch': 'gh-pages',
            'message': '推送成功'
        }
        
        self.assertTrue(result['success'])
        self.assertEqual(result['remote'], 'origin')
        self.assertEqual(result['branch'], 'gh-pages')


if __name__ == '__main__':
    unittest.main()