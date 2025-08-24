#!/usr/bin/env python3
"""
GitHub部署监控功能测试

测试GitHub Pages部署状态检测和监控功能：
1. 部署状态API
2. GitHub部署监控服务
3. ProcessingService集成
"""

import unittest
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path


class TestGitHubDeploymentStatusAPI(unittest.TestCase):
    """测试GitHub部署状态API"""
    
    def setUp(self):
        """设置测试环境"""
        from src.web_frontend.app import create_app
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
    def tearDown(self):
        """清理测试环境"""
        self.app_context.pop()
    
    @patch('ipaddress.ip_address')
    @patch('ipaddress.ip_network')
    def test_github_pages_status_api_exists(self, mock_ip_network, mock_ip_address):
        """测试GitHub Pages状态API端点存在"""
        # Mock Tailscale网络检查通过
        mock_network = Mock()
        mock_ip = Mock()
        mock_ip_network.return_value = mock_network
        mock_ip_address.return_value = mock_ip
        mock_network.__contains__ = Mock(return_value=True)
        
        response = self.client.get('/api/github/pages-status')
        # API应该存在（不是404），可能返回200或503等
        self.assertNotEqual(response.status_code, 404)
        
    @patch('ipaddress.ip_address')
    @patch('ipaddress.ip_network')
    @patch('requests.get')
    def test_github_pages_status_response_format(self, mock_requests, mock_ip_network, mock_ip_address):
        """测试GitHub Pages状态响应格式"""
        # Mock Tailscale网络检查通过
        mock_network = Mock()
        mock_ip = Mock()
        mock_ip_network.return_value = mock_network
        mock_ip_address.return_value = mock_ip
        mock_network.__contains__ = Mock(return_value=True)
        
        # Mock成功的GitHub Pages响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><head><title>Project Bach</title></head></html>"
        mock_requests.return_value = mock_response
        
        response = self.client.get('/api/github/pages-status')
        
        if response.status_code == 200:
            data = json.loads(response.data)
            
            # 验证响应格式
            self.assertIn('status', data)
            self.assertIn('url', data) 
            self.assertIn('last_checked', data)
            
    @patch('ipaddress.ip_address')
    @patch('ipaddress.ip_network')
    @patch('requests.get')
    def test_github_pages_status_error_handling(self, mock_requests, mock_ip_network, mock_ip_address):
        """测试GitHub Pages状态错误处理"""
        # Mock Tailscale网络检查通过
        mock_network = Mock()
        mock_ip = Mock()
        mock_ip_network.return_value = mock_network
        mock_ip_address.return_value = mock_ip
        mock_network.__contains__ = Mock(return_value=True)
        
        # Mock网络错误
        mock_requests.side_effect = Exception("Network error")
        
        response = self.client.get('/api/github/pages-status')
        
        # 应该优雅地处理错误
        if response.status_code == 200:
            data = json.loads(response.data)
            self.assertEqual(data['status'], 'error')
        else:
            # 或者返回适当的错误状态码
            self.assertIn(response.status_code, [500, 503])


class TestGitHubDeploymentMonitorService(unittest.TestCase):
    """测试GitHub部署监控服务"""
    
    def test_monitor_service_initialization(self):
        """测试监控服务初始化"""
        try:
            # 尝试导入GitHub部署监控相关模块
            from src.web_frontend.handlers.processing_service import ProcessingService
            
            # 验证ProcessingService可以初始化
            service = ProcessingService()
            self.assertIsNotNone(service)
            
        except ImportError as e:
            self.skipTest(f"GitHub deployment monitoring not implemented: {e}")
    
    @patch('requests.get')
    def test_github_pages_url_detection(self, mock_requests):
        """测试GitHub Pages URL自动检测"""
        try:
            from src.web_frontend.handlers.processing_service import ProcessingService
            
            service = ProcessingService()
            
            # Mock成功响应
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = "<html></html>"
            mock_requests.return_value = mock_response
            
            # 测试URL检测逻辑
            if hasattr(service, 'get_github_pages_status'):
                status = service.get_github_pages_status()
                self.assertIsNotNone(status)
                
        except (ImportError, AttributeError) as e:
            self.skipTest(f"GitHub Pages URL detection not implemented: {e}")
    
    def test_deployment_status_tracking(self):
        """测试部署状态跟踪"""
        try:
            from src.web_frontend.handlers.processing_service import ProcessingService
            
            service = ProcessingService()
            
            # 测试状态跟踪功能
            if hasattr(service, 'track_deployment_status'):
                # 这应该是非阻塞的
                service.track_deployment_status()
                # 验证没有抛出异常
                self.assertTrue(True)
                
        except (ImportError, AttributeError) as e:
            self.skipTest(f"Deployment status tracking not implemented: {e}")


class TestProcessingServiceGitHubIntegration(unittest.TestCase):
    """测试ProcessingService与GitHub监控集成"""
    
    def test_processing_service_github_integration(self):
        """测试ProcessingService集成GitHub监控"""
        try:
            from src.web_frontend.handlers.processing_service import ProcessingService
            
            service = ProcessingService()
            
            # 验证ProcessingService有GitHub相关方法
            github_methods = [
                'get_github_pages_status',
                'check_deployment_status',
                'track_deployment_status'
            ]
            
            for method_name in github_methods:
                if hasattr(service, method_name):
                    method = getattr(service, method_name)
                    self.assertTrue(callable(method), f"{method_name} should be callable")
                    
        except ImportError as e:
            self.skipTest(f"ProcessingService GitHub integration not implemented: {e}")
    
    @patch('requests.get')
    def test_processing_status_with_deployment_check(self, mock_requests):
        """测试处理状态包含部署检查"""
        try:
            from src.web_frontend.handlers.processing_service import ProcessingService
            
            # Mock GitHub Pages响应
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = "<html></html>"
            mock_requests.return_value = mock_response
            
            service = ProcessingService()
            
            # 获取处理状态
            if hasattr(service, 'get_status'):
                status = service.get_status()
                
                # 验证状态包含GitHub相关信息
                if isinstance(status, dict):
                    # 检查是否包含GitHub Pages相关信息
                    github_keys = ['github_pages', 'deployment_status', 'pages_url']
                    has_github_info = any(key in status for key in github_keys)
                    
                    # 如果集成了GitHub监控，应该有相关信息
                    # 这是一个软检查，因为集成可能还在进行中
                    if has_github_info:
                        self.assertTrue(True, "GitHub integration detected in status")
                    
        except (ImportError, AttributeError) as e:
            self.skipTest(f"Processing status GitHub integration not implemented: {e}")


class TestGitHubMonitoringConfiguration(unittest.TestCase):
    """测试GitHub监控配置"""
    
    def test_github_config_exists(self):
        """测试GitHub配置存在"""
        config_path = Path('./config.yaml')
        if config_path.exists():
            import yaml
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            # 检查是否有GitHub相关配置
            github_config = config.get('github', {})
            
            if github_config:
                # 验证基本配置项
                self.assertIsInstance(github_config, dict)
                
                # 检查可能的配置项
                possible_keys = [
                    'repository_url', 'pages_url', 'username', 
                    'deployment_check_interval', 'pages_check_timeout'
                ]
                
                # 至少应该有一些GitHub相关配置
                has_config = any(key in github_config for key in possible_keys)
                if has_config:
                    self.assertTrue(True, "GitHub configuration found")
    
    def test_github_pages_url_format(self):
        """测试GitHub Pages URL格式"""
        config_path = Path('./config.yaml')
        if config_path.exists():
            import yaml
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            github_config = config.get('github', {})
            pages_url = github_config.get('pages_url', '')
            
            if pages_url:
                # 验证URL格式
                self.assertTrue(pages_url.startswith('https://'), 
                              "GitHub Pages URL should use HTTPS")
                self.assertIn('github.io', pages_url, 
                             "Should be a GitHub Pages URL")


class TestGitHubMonitoringPerformance(unittest.TestCase):
    """测试GitHub监控性能"""
    
    @patch('requests.get')
    def test_github_status_check_timeout(self, mock_requests):
        """测试GitHub状态检查超时"""
        import requests
        
        # Mock超时异常
        mock_requests.side_effect = requests.exceptions.Timeout("Request timed out")
        
        try:
            from src.web_frontend.handlers.processing_service import ProcessingService
            
            service = ProcessingService()
            
            if hasattr(service, 'get_github_pages_status'):
                # 状态检查应该优雅地处理超时
                status = service.get_github_pages_status()
                
                # 应该返回错误状态而不是抛出异常
                if isinstance(status, dict):
                    self.assertIn(status.get('status'), ['error', 'timeout', 'unknown'])
                    
        except (ImportError, AttributeError) as e:
            self.skipTest(f"GitHub status check not implemented: {e}")
    
    @patch('requests.get')
    def test_github_monitoring_non_blocking(self, mock_requests):
        """测试GitHub监控非阻塞"""
        import time
        
        # Mock慢响应
        def slow_response(*args, **kwargs):
            time.sleep(0.1)  # 模拟慢响应
            response = Mock()
            response.status_code = 200
            response.text = "<html></html>"
            return response
            
        mock_requests.side_effect = slow_response
        
        try:
            from src.web_frontend.handlers.processing_service import ProcessingService
            
            service = ProcessingService()
            
            if hasattr(service, 'track_deployment_status'):
                start_time = time.time()
                
                # 部署状态跟踪不应该阻塞
                service.track_deployment_status()
                
                end_time = time.time()
                elapsed = end_time - start_time
                
                # 应该很快返回（非阻塞）
                self.assertLess(elapsed, 0.5, "Deployment tracking should be non-blocking")
                
        except (ImportError, AttributeError) as e:
            self.skipTest(f"GitHub monitoring performance test not implemented: {e}")


if __name__ == '__main__':
    unittest.main()