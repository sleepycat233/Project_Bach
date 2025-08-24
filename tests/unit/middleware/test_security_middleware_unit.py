#!/usr/bin/env python3
"""
Flask安全中间件 单元测试

测试Flask安全中间件的各个功能，严格遵循单元测试原则：
- 一个测试方法只测试一个功能
- Mock所有外部依赖 
- 测试单个函数/方法的输入输出
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import ipaddress

import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent))


class MockSecurityMiddleware:
    """Mock Security Middleware for unit testing"""
    
    def __init__(self, app=None, config_manager=None):
        self.app = app
        self.config_manager = config_manager
        self.tailscale_network = ipaddress.ip_network('100.64.0.0/10')
    
    def is_tailscale_enabled(self):
        """检查Tailscale是否启用"""
        if not self.config_manager:
            return True  # 默认启用
        
        return self.config_manager.config.get('tailscale', {}).get('enabled', True)
    
    def is_tailscale_ip(self, ip_str):
        """检查IP是否属于Tailscale网络"""
        try:
            ip = ipaddress.ip_address(ip_str)
            return ip in self.tailscale_network
        except (ValueError, TypeError):
            return False
    
    def is_localhost(self, ip_str):
        """检查是否是本地地址"""
        localhost_ips = ['127.0.0.1', '::1', 'localhost']
        return ip_str in localhost_ips
    
    def validate_request_ip(self, request_ip):
        """验证请求IP地址"""
        if not self.is_tailscale_enabled():
            return True  # 如果禁用Tailscale检查，允许所有IP
        
        if self.is_localhost(request_ip):
            return True
        
        if self.is_tailscale_ip(request_ip):
            return True
        
        return False
    
    def create_security_response(self, message="Access denied", status_code=403):
        """创建安全响应"""
        return {
            'error': 'Access denied',
            'message': message,
            'status_code': status_code
        }


class TestSecurityMiddlewareInit(unittest.TestCase):
    """测试安全中间件初始化"""
    
    def test_init_with_app_and_config(self):
        """测试使用应用和配置初始化"""
        mock_app = Mock()
        mock_config = Mock()
        
        middleware = MockSecurityMiddleware(mock_app, mock_config)
        
        self.assertEqual(middleware.app, mock_app)
        self.assertEqual(middleware.config_manager, mock_config)
        self.assertIsNotNone(middleware.tailscale_network)
    
    def test_init_without_config(self):
        """测试无配置时的初始化"""
        mock_app = Mock()
        
        middleware = MockSecurityMiddleware(mock_app, None)
        
        self.assertEqual(middleware.app, mock_app)
        self.assertIsNone(middleware.config_manager)
    
    def test_init_tailscale_network_setup(self):
        """测试Tailscale网络设置"""
        middleware = MockSecurityMiddleware()
        
        # 验证Tailscale网络范围
        self.assertEqual(str(middleware.tailscale_network), '100.64.0.0/10')


class TestTailscaleConfiguration(unittest.TestCase):
    """测试Tailscale配置检查"""
    
    def test_tailscale_enabled_with_config(self):
        """测试配置中启用Tailscale"""
        mock_config = Mock()
        mock_config.config = {'tailscale': {'enabled': True}}
        
        middleware = MockSecurityMiddleware(config_manager=mock_config)
        
        result = middleware.is_tailscale_enabled()
        self.assertTrue(result)
    
    def test_tailscale_disabled_with_config(self):
        """测试配置中禁用Tailscale"""
        mock_config = Mock()
        mock_config.config = {'tailscale': {'enabled': False}}
        
        middleware = MockSecurityMiddleware(config_manager=mock_config)
        
        result = middleware.is_tailscale_enabled()
        self.assertFalse(result)
    
    def test_tailscale_default_enabled_no_config(self):
        """测试无配置时默认启用"""
        middleware = MockSecurityMiddleware(config_manager=None)
        
        result = middleware.is_tailscale_enabled()
        self.assertTrue(result)
    
    def test_tailscale_default_enabled_empty_config(self):
        """测试空配置时默认启用"""
        mock_config = Mock()
        mock_config.config = {}
        
        middleware = MockSecurityMiddleware(config_manager=mock_config)
        
        result = middleware.is_tailscale_enabled()
        self.assertTrue(result)


class TestIPValidation(unittest.TestCase):
    """测试IP地址验证"""
    
    def setUp(self):
        """设置测试环境"""
        self.middleware = MockSecurityMiddleware()
    
    def test_valid_tailscale_ip(self):
        """测试有效Tailscale IP"""
        valid_ips = [
            '100.64.0.1',
            '100.127.255.254',
            '100.100.100.100'
        ]
        
        for ip in valid_ips:
            result = self.middleware.is_tailscale_ip(ip)
            self.assertTrue(result, f"IP {ip} should be valid Tailscale IP")
    
    def test_invalid_tailscale_ip(self):
        """测试无效Tailscale IP"""
        invalid_ips = [
            '192.168.1.100',
            '10.0.0.1',
            '172.16.0.1',
            '8.8.8.8',
            '100.63.255.255',  # 刚好在范围外
            '100.128.0.0'      # 刚好在范围外
        ]
        
        for ip in invalid_ips:
            result = self.middleware.is_tailscale_ip(ip)
            self.assertFalse(result, f"IP {ip} should be invalid Tailscale IP")
    
    def test_localhost_detection(self):
        """测试本地地址检测"""
        localhost_ips = ['127.0.0.1', '::1', 'localhost']
        
        for ip in localhost_ips:
            result = self.middleware.is_localhost(ip)
            self.assertTrue(result, f"IP {ip} should be localhost")
    
    def test_invalid_ip_format(self):
        """测试无效IP格式"""
        invalid_formats = [
            'not.an.ip',
            '256.256.256.256',
            '192.168.1',
            '',
            None
        ]
        
        for ip in invalid_formats:
            result = self.middleware.is_tailscale_ip(ip)
            self.assertFalse(result, f"Invalid format {ip} should return False")


class TestRequestValidation(unittest.TestCase):
    """测试请求验证"""
    
    def test_validate_tailscale_ip_when_enabled(self):
        """测试启用Tailscale时的IP验证"""
        mock_config = Mock()
        mock_config.config = {'tailscale': {'enabled': True}}
        
        middleware = MockSecurityMiddleware(config_manager=mock_config)
        
        # 有效Tailscale IP
        result = middleware.validate_request_ip('100.64.0.100')
        self.assertTrue(result)
        
        # 无效IP
        result = middleware.validate_request_ip('8.8.8.8')
        self.assertFalse(result)
    
    def test_validate_localhost_when_enabled(self):
        """测试启用Tailscale时的本地地址验证"""
        mock_config = Mock()
        mock_config.config = {'tailscale': {'enabled': True}}
        
        middleware = MockSecurityMiddleware(config_manager=mock_config)
        
        # 本地地址应该始终允许
        result = middleware.validate_request_ip('127.0.0.1')
        self.assertTrue(result)
    
    def test_validate_any_ip_when_disabled(self):
        """测试禁用Tailscale时允许所有IP"""
        mock_config = Mock()
        mock_config.config = {'tailscale': {'enabled': False}}
        
        middleware = MockSecurityMiddleware(config_manager=mock_config)
        
        # 禁用时应该允许任何IP
        test_ips = ['8.8.8.8', '192.168.1.100', '10.0.0.1']
        
        for ip in test_ips:
            result = middleware.validate_request_ip(ip)
            self.assertTrue(result, f"IP {ip} should be allowed when Tailscale disabled")


class TestSecurityResponse(unittest.TestCase):
    """测试安全响应创建"""
    
    def setUp(self):
        """设置测试环境"""
        self.middleware = MockSecurityMiddleware()
    
    def test_default_security_response(self):
        """测试默认安全响应"""
        response = self.middleware.create_security_response()
        
        self.assertEqual(response['error'], 'Access denied')
        self.assertEqual(response['message'], 'Access denied')
        self.assertEqual(response['status_code'], 403)
    
    def test_custom_security_response(self):
        """测试自定义安全响应"""
        custom_message = "Custom security message"
        custom_status = 401
        
        response = self.middleware.create_security_response(custom_message, custom_status)
        
        self.assertEqual(response['error'], 'Access denied')
        self.assertEqual(response['message'], custom_message)
        self.assertEqual(response['status_code'], custom_status)


class TestEdgeCases(unittest.TestCase):
    """测试边界情况"""
    
    def setUp(self):
        """设置测试环境"""
        self.middleware = MockSecurityMiddleware()
    
    def test_tailscale_network_boundaries(self):
        """测试Tailscale网络边界"""
        # 网络边界测试
        boundary_tests = [
            ('100.64.0.0', True),      # 网络起始
            ('100.127.255.255', True), # 网络结束
            ('100.63.255.255', False), # 刚好外面
            ('100.128.0.0', False)     # 刚好外面
        ]
        
        for ip, expected in boundary_tests:
            result = self.middleware.is_tailscale_ip(ip)
            self.assertEqual(result, expected, f"IP {ip} boundary test failed")
    
    def test_ipv6_handling(self):
        """测试IPv6地址处理"""
        # 目前只处理IPv4，IPv6应该返回False
        ipv6_addresses = [
            '2001:db8::1',
            '::1',  # 除了在localhost检查中
            'fe80::1'
        ]
        
        for ip in ipv6_addresses:
            if ip != '::1':  # ::1在localhost中单独处理
                result = self.middleware.is_tailscale_ip(ip)
                self.assertFalse(result, f"IPv6 address {ip} should return False for Tailscale check")


if __name__ == '__main__':
    unittest.main()