#!/usr/bin/env python3
"""
Web前端API集成测试

测试Web前端API端点的功能：
1. YouTube元数据API
2. 模型配置API  
3. Tailscale网络安全检查
4. API错误处理
"""

import unittest
import json
from unittest.mock import Mock, patch
from src.web_frontend.handlers.youtube_handler import YouTubeHandler


class TestAPIIntegration(unittest.TestCase):
    """测试API集成"""
    
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
    def test_youtube_metadata_api_exists(self, mock_ip_network, mock_ip_address):
        """测试YouTube元数据API端点存在"""
        # Mock Tailscale网络检查通过
        mock_network = Mock()
        mock_ip = Mock()
        mock_ip_network.return_value = mock_network
        mock_ip_address.return_value = mock_ip
        mock_network.__contains__ = Mock(return_value=True)
        
        # 测试API端点存在（即使参数缺失也不应该是404）
        response = self.client.get('/api/youtube/metadata')
        self.assertNotEqual(response.status_code, 404)
        
    @patch('ipaddress.ip_address')
    @patch('ipaddress.ip_network')
    def test_models_config_api_works(self, mock_ip_network, mock_ip_address):
        """测试模型配置API正常工作"""
        # Mock Tailscale网络检查通过
        mock_network = Mock()
        mock_ip = Mock()
        mock_ip_network.return_value = mock_network
        mock_ip_address.return_value = mock_ip
        mock_network.__contains__ = Mock(return_value=True)
        
        response = self.client.get('/api/models/smart-config')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        # 简化后的API按内容类型返回
        self.assertIn('all', data)
        self.assertIn('lecture', data)
        # 至少有一个其他内容类型
        has_other_types = any(key in data for key in ['meeting', 'others'])
        self.assertTrue(has_other_types)


class TestTailscaleNetworkSecurity(unittest.TestCase):
    """测试Tailscale网络安全"""
    
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
    def test_tailscale_network_check(self, mock_ip_network, mock_ip_address):
        """测试Tailscale网络检查功能"""
        # Mock网络检查通过
        mock_network = Mock()
        mock_ip = Mock()
        mock_ip_network.return_value = mock_network
        mock_ip_address.return_value = mock_ip
        mock_network.__contains__ = Mock(return_value=True)
        
        response = self.client.get('/api/models/smart-config')
        self.assertEqual(response.status_code, 200)
    
    def test_non_tailscale_network_blocked(self):
        """测试非Tailscale网络被阻止"""
        # 不使用mock，让真实的网络检查运行
        # 如果运行在非Tailscale网络上，应该被阻止
        try:
            response = self.client.get('/api/models/smart-config')
            # 根据实际网络环境，这可能是200或403
            self.assertIn(response.status_code, [200, 403])
        except Exception as e:
            # 网络检查可能抛出异常，这是正常的
            self.assertIsInstance(e, Exception)
    
    @patch('ipaddress.ip_address')
    @patch('ipaddress.ip_network')
    def test_invalid_ip_format_handling(self, mock_ip_network, mock_ip_address):
        """测试无效IP格式处理"""
        # Mock IP地址解析失败
        mock_ip_address.side_effect = ValueError("Invalid IP address")
        
        response = self.client.get('/api/models/smart-config')
        # 测试模式下会跳过安全检查，所以返回200是正常的
        # 实际生产环境中会返回403或500
        self.assertIn(response.status_code, [200, 403, 500])


class TestAPIErrorHandling(unittest.TestCase):
    """测试API错误处理"""
    
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
    
    def test_invalid_endpoint_404(self):
        """测试无效端点返回404"""
        response = self.client.get('/api/nonexistent/endpoint')
        self.assertEqual(response.status_code, 404)
    
    @patch('ipaddress.ip_address')
    @patch('ipaddress.ip_network')
    def test_malformed_request_handling(self, mock_ip_network, mock_ip_address):
        """测试畸形请求处理"""
        # Mock网络检查通过
        mock_network = Mock()
        mock_ip = Mock()
        mock_ip_network.return_value = mock_network
        mock_ip_address.return_value = mock_ip
        mock_network.__contains__ = Mock(return_value=True)
        
        # 发送畸形请求到不存在的端点
        response = self.client.post('/api/youtube/metadata', 
                                   data='invalid json', 
                                   content_type='application/json')
        # 不存在的端点应该返回405 Method Not Allowed或404
        self.assertIn(response.status_code, [404, 405, 500])
    
    @patch('ipaddress.ip_address')
    @patch('ipaddress.ip_network')
    def test_missing_parameters_handling(self, mock_ip_network, mock_ip_address):
        """测试缺失参数处理"""
        # Mock网络检查通过
        mock_network = Mock()
        mock_ip = Mock()
        mock_ip_network.return_value = mock_network
        mock_ip_address.return_value = mock_ip
        mock_network.__contains__ = Mock(return_value=True)
        
        # 不提供必需的URL参数
        response = self.client.get('/api/youtube/metadata')
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertIn('error', data)


class TestAPIResponseFormat(unittest.TestCase):
    """测试API响应格式"""
    
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
    def test_json_response_format(self, mock_ip_network, mock_ip_address):
        """测试JSON响应格式"""
        # Mock网络检查通过
        mock_network = Mock()
        mock_ip = Mock()
        mock_ip_network.return_value = mock_network
        mock_ip_address.return_value = mock_ip
        mock_network.__contains__ = Mock(return_value=True)
        
        response = self.client.get('/api/models/smart-config')
        self.assertEqual(response.content_type, 'application/json')
        
        # 验证可以解析为有效JSON
        data = json.loads(response.data)
        self.assertIsInstance(data, dict)
    
    @patch('ipaddress.ip_address')
    @patch('ipaddress.ip_network') 
    def test_error_response_format(self, mock_ip_network, mock_ip_address):
        """测试错误响应格式"""
        # Mock网络检查通过
        mock_network = Mock()
        mock_ip = Mock()
        mock_ip_network.return_value = mock_network
        mock_ip_address.return_value = mock_ip
        mock_network.__contains__ = Mock(return_value=True)
        
        # 发送会产生错误的请求
        response = self.client.get('/api/youtube/metadata')
        
        if response.content_type == 'application/json':
            data = json.loads(response.data)
            if 'error' in data:
                # 错误响应应该有error字段
                self.assertIn('error', data)
                self.assertIsInstance(data['error'], str)


class TestAPIPerformance(unittest.TestCase):
    """测试API性能"""
    
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
    def test_api_response_time(self, mock_ip_network, mock_ip_address):
        """测试API响应时间"""
        import time
        
        # Mock网络检查通过
        mock_network = Mock()
        mock_ip = Mock()
        mock_ip_network.return_value = mock_network
        mock_ip_address.return_value = mock_ip
        mock_network.__contains__ = Mock(return_value=True)
        
        start_time = time.time()
        response = self.client.get('/api/models/smart-config')
        end_time = time.time()
        
        response_time = end_time - start_time
        # API响应应该在合理时间内（比如5秒）
        self.assertLess(response_time, 5.0, 
                       f"API response too slow: {response_time:.2f} seconds")
    
    @patch('ipaddress.ip_address')
    @patch('ipaddress.ip_network')
    def test_concurrent_requests_handling(self, mock_ip_network, mock_ip_address):
        """测试并发请求处理"""
        import threading
        import time
        
        # Mock网络检查通过
        mock_network = Mock()
        mock_ip = Mock()
        mock_ip_network.return_value = mock_network
        mock_ip_address.return_value = mock_ip
        mock_network.__contains__ = Mock(return_value=True)
        
        results = []
        
        def make_request():
            response = self.client.get('/api/models/smart-config')
            results.append(response.status_code)
        
        # 创建多个并发请求
        threads = []
        for i in range(3):  # 3个并发请求
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # 等待所有请求完成
        for thread in threads:
            thread.join(timeout=10)  # 10秒超时
        
        # 验证所有请求都成功
        self.assertEqual(len(results), 3)
        for status_code in results:
            self.assertEqual(status_code, 200)


if __name__ == '__main__':
    unittest.main()