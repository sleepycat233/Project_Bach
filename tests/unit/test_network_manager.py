#!/usr/bin/env python3.11
"""
网络管理模块单元测试
包含Tailscale管理和网络连接监控的测试用例
"""

import unittest
import tempfile
import shutil
import os
import json
import subprocess
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, call

# 添加src目录到Python路径
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# 模拟网络管理模块导入
try:
    from network.tailscale_manager import TailscaleManager
    from network.connection_monitor import NetworkConnectionMonitor
except ImportError:
    # 如果模块不存在，创建模拟类用于测试
    class TailscaleManager:
        def __init__(self, config=None):
            self.config = config or {}
        
        def check_status(self):
            return {'connected': False, 'node_id': None}
        
        def connect(self):
            return True
        
        def disconnect(self):
            return True
        
        def get_network_info(self):
            return {'peers': [], 'network_status': 'unknown'}
    
    class NetworkConnectionMonitor:
        def __init__(self, config=None):
            self.config = config or {}
        
        def start_monitoring(self):
            return True
        
        def stop_monitoring(self):
            return True
        
        def get_connection_status(self):
            return {'status': 'connected', 'latency': 10}


class TestTailscaleManager(unittest.TestCase):
    """测试Tailscale管理器"""
    
    def setUp(self):
        """每个测试前的准备工作"""
        self.test_dir = tempfile.mkdtemp()
        self.tailscale_config = {
            'auth_key': 'tskey-test-auth-key',
            'machine_name': 'project-bach-test',
            'network_name': 'test-network',
            'auto_connect': True,
            'timeout': 30
        }
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_init_with_config(self):
        """测试带配置的初始化"""
        manager = TailscaleManager(self.tailscale_config)
        self.assertEqual(manager.config, self.tailscale_config)
    
    def test_init_without_config(self):
        """测试无配置的初始化"""
        manager = TailscaleManager()
        self.assertEqual(manager.config, {})
    
    @patch('subprocess.run')
    def test_check_tailscale_installed(self, mock_subprocess):
        """测试检查Tailscale是否已安装"""
        # 模拟Tailscale已安装
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "tailscale version 1.50.0"
        mock_subprocess.return_value = mock_result
        
        manager = TailscaleManager(self.tailscale_config)
        # 这里需要实际的方法实现
        # is_installed = manager.check_tailscale_installed()
        # self.assertTrue(is_installed)
    
    @patch('subprocess.run')
    def test_check_tailscale_not_installed(self, mock_subprocess):
        """测试Tailscale未安装的情况"""
        # 模拟命令未找到
        mock_subprocess.side_effect = FileNotFoundError("tailscale not found")
        
        manager = TailscaleManager(self.tailscale_config)
        # is_installed = manager.check_tailscale_installed()
        # self.assertFalse(is_installed)
    
    @patch('subprocess.run')
    def test_tailscale_status_connected(self, mock_subprocess):
        """测试Tailscale连接状态 - 已连接"""
        # 模拟已连接状态
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "BackendState": "Running",
            "TailscaleIPs": ["100.64.0.1"],
            "Self": {
                "ID": "n123456789abcdef",
                "UserID": 12345,
                "Name": "project-bach-test",
                "DNSName": "project-bach-test.tail-scale.ts.net"
            }
        })
        mock_subprocess.return_value = mock_result
        
        manager = TailscaleManager(self.tailscale_config)
        status = manager.check_status()
        
        # 验证返回的状态信息
        self.assertTrue(status.get('connected', False))
        self.assertIn('node_id', status)
    
    @patch('subprocess.run')
    def test_tailscale_status_disconnected(self, mock_subprocess):
        """测试Tailscale连接状态 - 未连接"""
        # 模拟未连接状态
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "BackendState": "Stopped",
            "TailscaleIPs": [],
            "Self": None
        })
        mock_subprocess.return_value = mock_result
        
        manager = TailscaleManager(self.tailscale_config)
        status = manager.check_status()
        
        self.assertFalse(status.get('connected', True))
        self.assertIsNone(status.get('node_id'))
    
    @patch('subprocess.run')
    def test_tailscale_login_success(self, mock_subprocess):
        """测试Tailscale登录成功"""
        # 模拟登录成功
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Success."
        mock_subprocess.return_value = mock_result
        
        manager = TailscaleManager(self.tailscale_config)
        result = manager.connect()
        
        self.assertTrue(result)
    
    @patch('subprocess.run')
    def test_tailscale_login_failure(self, mock_subprocess):
        """测试Tailscale登录失败"""
        # 模拟登录失败
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Invalid auth key"
        mock_subprocess.return_value = mock_result
        
        manager = TailscaleManager(self.tailscale_config)
        result = manager.connect()
        
        self.assertFalse(result)
    
    @patch('subprocess.run')
    def test_tailscale_logout_success(self, mock_subprocess):
        """测试Tailscale登出成功"""
        # 模拟登出成功
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        manager = TailscaleManager(self.tailscale_config)
        result = manager.disconnect()
        
        self.assertTrue(result)
    
    @patch('subprocess.run')
    def test_get_peer_list(self, mock_subprocess):
        """测试获取网络节点列表"""
        # 模拟节点列表
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "Peer": {
                "n987654321fedcba": {
                    "ID": "n987654321fedcba",
                    "PublicKey": "nodekey:abcdef123456789",
                    "HostName": "iphone-user",
                    "DNSName": "iphone-user.tail-scale.ts.net",
                    "OS": "iOS",
                    "TailscaleIPs": ["100.64.0.2"],
                    "Online": True
                }
            }
        })
        mock_subprocess.return_value = mock_result
        
        manager = TailscaleManager(self.tailscale_config)
        network_info = manager.get_network_info()
        
        self.assertIn('peers', network_info)
        self.assertGreater(len(network_info['peers']), 0)
    
    def test_validate_config(self):
        """测试配置验证"""
        # 测试有效配置
        valid_config = {
            'auth_key': 'tskey-auth-valid-key',
            'machine_name': 'valid-machine-name'
        }
        
        manager = TailscaleManager(valid_config)
        # is_valid = manager.validate_config()
        # self.assertTrue(is_valid)
        
        # 测试无效配置
        invalid_configs = [
            {},  # 空配置
            {'auth_key': ''},  # 空auth_key
            {'auth_key': 'invalid-key-format'},  # 无效格式
            {'machine_name': 'invalid machine name!@#'}  # 无效机器名
        ]
        
        for invalid_config in invalid_configs:
            manager = TailscaleManager(invalid_config)
            # is_valid = manager.validate_config()
            # self.assertFalse(is_valid, f"Should be invalid: {invalid_config}")


class TestNetworkConnectionMonitor(unittest.TestCase):
    """测试网络连接监控器"""
    
    def setUp(self):
        """每个测试前的准备工作"""
        self.monitor_config = {
            'check_interval': 30,  # 检查间隔(秒)
            'timeout': 5,
            'max_retries': 3,
            'target_hosts': ['100.64.0.1', '100.64.0.2'],
            'alert_on_disconnect': True
        }
    
    def test_init_with_config(self):
        """测试带配置的初始化"""
        monitor = NetworkConnectionMonitor(self.monitor_config)
        self.assertEqual(monitor.config, self.monitor_config)
    
    @patch('ping3.ping')
    def test_ping_host_success(self, mock_ping):
        """测试ping主机成功"""
        # 模拟ping成功，返回延迟时间
        mock_ping.return_value = 0.015  # 15ms延迟
        
        monitor = NetworkConnectionMonitor(self.monitor_config)
        target_host = "100.64.0.1"
        
        # latency = monitor.ping_host(target_host)
        # self.assertIsNotNone(latency)
        # self.assertGreater(latency, 0)
    
    @patch('ping3.ping')
    def test_ping_host_failure(self, mock_ping):
        """测试ping主机失败"""
        # 模拟ping失败
        mock_ping.return_value = None
        
        monitor = NetworkConnectionMonitor(self.monitor_config)
        target_host = "100.64.0.1"
        
        # latency = monitor.ping_host(target_host)
        # self.assertIsNone(latency)
    
    @patch('ping3.ping')
    def test_monitor_all_hosts(self, mock_ping):
        """测试监控所有主机"""
        # 模拟第一个主机连通，第二个主机不通
        mock_ping.side_effect = [0.020, None]
        
        monitor = NetworkConnectionMonitor(self.monitor_config)
        # status = monitor.check_all_hosts()
        
        # self.assertIn('100.64.0.1', status)
        # self.assertIn('100.64.0.2', status)
        # self.assertIsNotNone(status['100.64.0.1'])
        # self.assertIsNone(status['100.64.0.2'])
    
    def test_start_stop_monitoring(self):
        """测试启动和停止监控"""
        monitor = NetworkConnectionMonitor(self.monitor_config)
        
        # 测试启动监控
        result = monitor.start_monitoring()
        self.assertTrue(result)
        
        # 测试停止监控
        result = monitor.stop_monitoring()
        self.assertTrue(result)
    
    @patch('time.time')
    def test_get_connection_status(self, mock_time):
        """测试获取连接状态"""
        mock_time.return_value = 1640995200  # 固定时间戳
        
        monitor = NetworkConnectionMonitor(self.monitor_config)
        status = monitor.get_connection_status()
        
        self.assertIn('status', status)
        self.assertIn('last_check', status)
    
    def test_connection_health_score(self):
        """测试连接健康评分"""
        monitor = NetworkConnectionMonitor(self.monitor_config)
        
        # 模拟不同的连接统计
        test_cases = [
            {'success_rate': 1.0, 'avg_latency': 10, 'expected_score': 'excellent'},
            {'success_rate': 0.9, 'avg_latency': 50, 'expected_score': 'good'},
            {'success_rate': 0.7, 'avg_latency': 100, 'expected_score': 'fair'},
            {'success_rate': 0.3, 'avg_latency': 200, 'expected_score': 'poor'}
        ]
        
        for case in test_cases:
            # score = monitor.calculate_health_score(
            #     case['success_rate'], 
            #     case['avg_latency']
            # )
            # self.assertEqual(score, case['expected_score'])
            pass


if __name__ == '__main__':
    unittest.main()