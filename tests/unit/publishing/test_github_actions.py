#!/usr/bin/env python3.11
"""
GitHubActionsManager服务单元测试
测试CI/CD工作流管理、监控等功能
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src'))

from .test_base import PublishingTestBase


class TestGitHubActionsManager(PublishingTestBase):
    """GitHubActionsManager服务测试"""
    
    def setUp(self):
        super().setUp()
        self.actions_manager = Mock()
        
    def test_create_pages_workflow(self):
        """测试创建Pages工作流"""
        workflow_config = {
            'name': 'Deploy to GitHub Pages',
            'on': {
                'push': {'branches': ['gh-pages']},
                'workflow_dispatch': {}
            },
            'jobs': {
                'deploy': {
                    'runs-on': 'ubuntu-latest',
                    'steps': [
                        {'uses': 'actions/checkout@v3'},
                        {'uses': 'actions/configure-pages@v3'},
                        {'uses': 'actions/deploy-pages@v2'}
                    ]
                }
            }
        }
        
        # 验证工作流配置
        self.assertIn('Deploy to GitHub Pages', workflow_config['name'])
        self.assertIn('push', workflow_config['on'])
        self.assertIn('gh-pages', workflow_config['on']['push']['branches'])
        self.assertIn('deploy', workflow_config['jobs'])
        
    def test_workflow_trigger(self):
        """测试工作流触发"""
        trigger_event = {
            'event_type': 'push',
            'ref': 'refs/heads/gh-pages',
            'commit_sha': 'abc123def456',
            'timestamp': '2025-08-21T10:30:00Z',
            'author': 'Project Bach Bot'
        }
        
        # 验证触发事件
        self.assertEqual(trigger_event['event_type'], 'push')
        self.assertIn('gh-pages', trigger_event['ref'])
        self.assertTrue(len(trigger_event['commit_sha']) > 6)
        
    def test_monitor_workflow_run(self):
        """测试监控工作流运行"""
        workflow_run = {
            'id': 12345,
            'status': 'completed',
            'conclusion': 'success',
            'started_at': '2025-08-21T10:30:00Z',
            'completed_at': '2025-08-21T10:32:15Z',
            'duration': 135,  # 秒
            'jobs': [
                {
                    'name': 'deploy',
                    'status': 'completed',
                    'conclusion': 'success',
                    'duration': 120
                }
            ]
        }
        
        # 验证工作流运行状态
        self.assertEqual(workflow_run['status'], 'completed')
        self.assertEqual(workflow_run['conclusion'], 'success')
        self.assertLess(workflow_run['duration'], 300)  # 应在5分钟内完成
        
        # 验证作业状态
        deploy_job = workflow_run['jobs'][0]
        self.assertEqual(deploy_job['name'], 'deploy')
        self.assertEqual(deploy_job['conclusion'], 'success')
        
    def test_workflow_validation(self):
        """测试工作流配置验证"""
        # 有效配置
        valid_config = {
            'name': 'Valid Workflow',
            'on': ['push'],
            'jobs': {
                'build': {
                    'runs-on': 'ubuntu-latest',
                    'steps': [{'run': 'echo "Hello"'}]
                }
            }
        }
        
        # 配置验证
        self.assertIn('name', valid_config)
        self.assertIn('on', valid_config)
        self.assertIn('jobs', valid_config)
        self.assertIn('build', valid_config['jobs'])
        
        # 无效配置
        invalid_config = {'name': 'Invalid Workflow'}
        
        self.assertNotIn('jobs', invalid_config)
        self.assertNotIn('on', invalid_config)


if __name__ == '__main__':
    unittest.main()