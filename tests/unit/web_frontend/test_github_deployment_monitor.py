#!/usr/bin/env python3
"""
GitHub部署监控服务单元测试

测试GitHubDeploymentMonitor的部署状态检查和监控功能
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import requests
from pathlib import Path

# 添加项目根目录到路径
import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from src.web_frontend.services.github_deployment_monitor import (
    GitHubDeploymentMonitor, 
    create_deployment_monitor
)


class TestGitHubDeploymentMonitor(unittest.TestCase):
    """测试GitHub部署监控器"""
    
    def setUp(self):
        """测试前设置"""
        self.test_config = {
            'github': {
                'token': 'test-token',
                'username': 'test-user',
                'repo_name': 'test-repo',
                'base_url': 'https://api.github.com'
            }
        }
        self.monitor = GitHubDeploymentMonitor(self.test_config)
    
    def test_monitor_initialization(self):
        """测试监控器初始化"""
        self.assertEqual(self.monitor.token, 'test-token')
        self.assertEqual(self.monitor.username, 'test-user')
        self.assertEqual(self.monitor.repo_name, 'test-repo')
        self.assertEqual(self.monitor.base_url, 'https://api.github.com')
        
        # 验证请求头设置
        expected_headers = {
            'Authorization': 'token test-token',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Project-Bach-Monitor/1.0'
        }
        self.assertEqual(self.monitor.headers, expected_headers)
    
    def test_monitor_initialization_without_token(self):
        """测试无token时的初始化"""
        config_without_token = {
            'github': {
                'username': 'test-user',
                'repo_name': 'test-repo'
            }
        }
        monitor = GitHubDeploymentMonitor(config_without_token)
        
        self.assertEqual(monitor.token, '')
        self.assertEqual(monitor.headers, {})
    
    def test_is_github_configured_true(self):
        """测试GitHub配置检查 - 已配置"""
        self.assertTrue(self.monitor._is_github_configured())
    
    def test_is_github_configured_false(self):
        """测试GitHub配置检查 - 未配置"""
        config_incomplete = {'github': {'username': 'test-user'}}
        monitor = GitHubDeploymentMonitor(config_incomplete)
        self.assertFalse(monitor._is_github_configured())
    
    def test_get_pages_url(self):
        """测试获取GitHub Pages URL"""
        expected_url = "https://test-user.github.io/test-repo"
        actual_url = self.monitor._get_pages_url()
        self.assertEqual(actual_url, expected_url)
    
    def test_get_pages_url_empty_config(self):
        """测试空配置时的GitHub Pages URL"""
        config_empty = {'github': {}}
        monitor = GitHubDeploymentMonitor(config_empty)
        self.assertEqual(monitor._get_pages_url(), "")
    
    @patch('src.web_frontend.services.github_deployment_monitor.requests.get')
    def test_get_latest_pages_deployment_success(self, mock_get):
        """测试获取最新部署成功"""
        # Mock deployments API响应
        mock_deployments_response = Mock()
        mock_deployments_response.status_code = 200
        mock_deployments_response.json.return_value = [
            {
                'id': 12345,
                'sha': 'abc123def',
                'created_at': '2024-01-01T10:00:00Z',
                'updated_at': '2024-01-01T10:05:00Z',
                'environment': 'github-pages'
            }
        ]
        
        # Mock deployment status API响应
        mock_status_response = Mock()
        mock_status_response.status_code = 200
        mock_status_response.json.return_value = [
            {
                'state': 'success',
                'environment_url': 'https://test-user.github.io/test-repo'
            }
        ]
        
        mock_get.side_effect = [mock_deployments_response, mock_status_response]
        
        result = self.monitor._get_latest_pages_deployment()
        
        self.assertTrue(result['found'])
        deployment = result['deployment']
        self.assertEqual(deployment['id'], 12345)
        self.assertEqual(deployment['state'], 'success')
        self.assertEqual(deployment['environment_url'], 'https://test-user.github.io/test-repo')
        
        # 验证API调用
        self.assertEqual(mock_get.call_count, 2)
    
    @patch('src.web_frontend.services.github_deployment_monitor.requests.get')
    def test_get_latest_pages_deployment_not_found(self, mock_get):
        """测试获取部署时无部署记录"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response
        
        result = self.monitor._get_latest_pages_deployment()
        
        self.assertFalse(result['found'])
    
    @patch('src.web_frontend.services.github_deployment_monitor.requests.get')
    def test_get_latest_pages_deployment_api_error(self, mock_get):
        """测试API错误时的部署获取"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        result = self.monitor._get_latest_pages_deployment()
        
        self.assertFalse(result['found'])
    
    @patch('src.web_frontend.services.github_deployment_monitor.requests.get')
    def test_get_deployment_status_success(self, mock_get):
        """测试获取部署状态成功"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                'state': 'success',
                'environment_url': 'https://test-user.github.io/test-repo'
            }
        ]
        mock_get.return_value = mock_response
        
        status = self.monitor._get_deployment_status(12345)
        
        self.assertIsNotNone(status)
        self.assertEqual(status['state'], 'success')
        self.assertEqual(status['environment_url'], 'https://test-user.github.io/test-repo')
    
    @patch('src.web_frontend.services.github_deployment_monitor.requests.get')
    def test_get_deployment_status_not_found(self, mock_get):
        """测试部署状态不存在"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response
        
        status = self.monitor._get_deployment_status(12345)
        
        self.assertIsNone(status)
    
    @patch('src.web_frontend.services.github_deployment_monitor.requests.head')
    def test_verify_website_accessibility_success(self, mock_head):
        """测试网站可访问性验证成功"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response
        
        result = self.monitor._verify_website_accessibility()
        
        self.assertTrue(result['accessible'])
        self.assertIn('GitHub Pages is accessible', result['message'])
        self.assertEqual(result['response_code'], 200)
    
    @patch('src.web_frontend.services.github_deployment_monitor.requests.head')
    def test_verify_website_accessibility_failed(self, mock_head):
        """测试网站可访问性验证失败"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_head.return_value = mock_response
        
        result = self.monitor._verify_website_accessibility()
        
        self.assertFalse(result['accessible'])
        self.assertIn('returned 404', result['message'])
        self.assertEqual(result['response_code'], 404)
    
    @patch('src.web_frontend.services.github_deployment_monitor.requests.head')
    def test_verify_website_accessibility_network_error(self, mock_head):
        """测试网络错误时的可访问性验证"""
        mock_head.side_effect = requests.RequestException("Network error")
        
        result = self.monitor._verify_website_accessibility()
        
        self.assertFalse(result['accessible'])
        self.assertIn('Network error', result['message'])
    
    @patch.object(GitHubDeploymentMonitor, '_get_latest_pages_deployment')
    @patch.object(GitHubDeploymentMonitor, '_verify_website_accessibility')
    def test_check_pages_deployment_status_success(self, mock_verify, mock_get_deployment):
        """测试检查Pages部署状态成功"""
        mock_get_deployment.return_value = {
            'found': True,
            'deployment': {
                'id': 12345,
                'state': 'success',
                'created_at': '2024-01-01T10:00:00Z',
                'updated_at': '2024-01-01T10:05:00Z',
                'environment': 'github-pages',
                'environment_url': 'https://test-user.github.io/test-repo'
            }
        }
        
        mock_verify.return_value = {
            'accessible': True,
            'message': 'GitHub Pages is accessible'
        }
        
        result = self.monitor.check_pages_deployment_status()
        
        self.assertTrue(result['deployed'])
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['method'], 'github_api')
        self.assertIn('deployment_info', result)
        self.assertEqual(result['deployment_info']['id'], 12345)
    
    @patch.object(GitHubDeploymentMonitor, '_get_latest_pages_deployment')
    def test_check_pages_deployment_status_not_found(self, mock_get_deployment):
        """测试检查部署状态时未找到部署"""
        mock_get_deployment.return_value = {'found': False}
        
        result = self.monitor.check_pages_deployment_status()
        
        self.assertFalse(result['deployed'])
        self.assertEqual(result['status'], 'not_found')
        self.assertEqual(result['method'], 'github_api')
    
    @patch.object(GitHubDeploymentMonitor, '_get_latest_pages_deployment')
    def test_check_pages_deployment_status_deploying(self, mock_get_deployment):
        """测试部署进行中状态"""
        mock_get_deployment.return_value = {
            'found': True,
            'deployment': {
                'id': 12345,
                'state': 'pending',
                'created_at': '2024-01-01T10:00:00Z'
            }
        }
        
        result = self.monitor.check_pages_deployment_status()
        
        self.assertFalse(result['deployed'])
        self.assertEqual(result['status'], 'deploying')
        self.assertIn('pending', result['message'])
    
    @patch.object(GitHubDeploymentMonitor, '_get_latest_pages_deployment')
    def test_check_pages_deployment_status_failed(self, mock_get_deployment):
        """测试部署失败状态"""
        mock_get_deployment.return_value = {
            'found': True,
            'deployment': {
                'id': 12345,
                'state': 'failure',
                'created_at': '2024-01-01T10:00:00Z'
            }
        }
        
        result = self.monitor.check_pages_deployment_status()
        
        self.assertFalse(result['deployed'])
        self.assertEqual(result['status'], 'failed')
        self.assertIn('failed', result['message'])
    
    def test_check_pages_deployment_status_unconfigured(self):
        """测试未配置GitHub时的状态检查"""
        config_empty = {'github': {}}
        monitor = GitHubDeploymentMonitor(config_empty)
        
        result = monitor.check_pages_deployment_status()
        
        self.assertTrue(result['deployed'])  # 默认认为成功
        self.assertEqual(result['status'], 'assumed_success')
        self.assertEqual(result['method'], 'fallback')
    
    def test_create_fallback_result_no_url(self):
        """测试无URL时的fallback结果"""
        config_no_url = {'github': {}}
        monitor = GitHubDeploymentMonitor(config_no_url)
        
        result = monitor._create_fallback_result()
        
        self.assertTrue(result['deployed'])
        self.assertEqual(result['status'], 'assumed_success')
        self.assertEqual(result['method'], 'fallback')
    
    @patch('src.web_frontend.services.github_deployment_monitor.requests.head')
    def test_create_fallback_result_with_url_check(self, mock_head):
        """测试有URL时的fallback结果网络检查"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response
        
        result = self.monitor._create_fallback_result()
        
        self.assertTrue(result['deployed'])
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['method'], 'fallback_http_check')
    
    @patch('src.web_frontend.services.github_deployment_monitor.requests.get')
    def test_get_recent_deployments_success(self, mock_get):
        """测试获取最近部署记录成功"""
        # Mock deployments API响应
        mock_deployments_response = Mock()
        mock_deployments_response.status_code = 200
        mock_deployments_response.json.return_value = [
            {
                'id': 12345,
                'sha': 'abc123',
                'created_at': '2024-01-01T10:00:00Z',
                'updated_at': '2024-01-01T10:05:00Z',
                'environment': 'github-pages'
            }
        ]
        
        # Mock deployment status API响应
        mock_status_response = Mock()
        mock_status_response.status_code = 200
        mock_status_response.json.return_value = [
            {
                'state': 'success',
                'environment_url': 'https://test-user.github.io/test-repo'
            }
        ]
        
        mock_get.side_effect = [mock_deployments_response, mock_status_response]
        
        result = self.monitor.get_recent_deployments(1)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['total'], 1)
        deployment = result['deployments'][0]
        self.assertEqual(deployment['id'], 12345)
        self.assertEqual(deployment['state'], 'success')
    
    def test_get_recent_deployments_unconfigured(self):
        """测试未配置时的最近部署记录获取"""
        config_empty = {'github': {}}
        monitor = GitHubDeploymentMonitor(config_empty)
        
        result = monitor.get_recent_deployments()
        
        self.assertFalse(result['success'])
        self.assertEqual(result['message'], 'GitHub not configured')


class TestCreateDeploymentMonitor(unittest.TestCase):
    """测试部署监控器创建函数"""
    
    def test_create_deployment_monitor(self):
        """测试创建部署监控器"""
        config = {
            'github': {
                'token': 'test-token',
                'username': 'test-user',
                'repo_name': 'test-repo'
            }
        }
        
        monitor = create_deployment_monitor(config)
        
        self.assertIsInstance(monitor, GitHubDeploymentMonitor)
        self.assertEqual(monitor.token, 'test-token')
        self.assertEqual(monitor.username, 'test-user')
        self.assertEqual(monitor.repo_name, 'test-repo')


if __name__ == '__main__':
    unittest.main()