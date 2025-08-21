#!/usr/bin/env python3.11
"""
API限流模块的单元测试
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import time
from datetime import datetime, timedelta

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from utils.rate_limiter import (
    RateLimiter,
    RateLimitedAPIClient,
    create_rate_limited_client
)


class TestRateLimiter(unittest.TestCase):
    """测试限流器"""
    
    def setUp(self):
        """测试设置"""
        self.api_key = "test-api-key"
        self.rate_limit_config = {
            'free_tier': {
                'requests_per_10s': 10,
                'requests_per_minute': 60,
                'daily_credit_limit': 5
            },
            'paid_tier': {
                'requests_per_10s': 10,
                'requests_per_minute': 60,
                'credit_to_requests_ratio': 100
            }
        }
    
    def test_init_with_config(self):
        """测试带配置的初始化"""
        limiter = RateLimiter(self.api_key, self.rate_limit_config)
        
        self.assertEqual(limiter.api_key, self.api_key)
        self.assertEqual(limiter.limits['free_models']['requests_per_10s'], 10)
        self.assertEqual(limiter.limits['paid_models']['credit_to_requests_ratio'], 100)
    
    def test_init_without_config(self):
        """测试无配置的初始化（使用默认值）"""
        limiter = RateLimiter(self.api_key)
        
        self.assertEqual(limiter.api_key, self.api_key)
        self.assertEqual(limiter.limits['free_models']['requests_per_10s'], 10)
        self.assertEqual(limiter.limits['paid_models']['credit_to_requests_ratio'], 100)
    
    @patch('utils.rate_limiter.requests.get')
    def test_check_account_status_success(self, mock_get):
        """测试成功检查账户状态"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'limit': 5,
                'usage': 2,
                'limit_remaining': 3,
                'is_free_tier': True
            }
        }
        mock_get.return_value = mock_response
        
        limiter = RateLimiter(self.api_key)
        result = limiter.check_account_status()
        
        self.assertIn('data', result)
        self.assertEqual(result['data']['limit'], 5)
    
    @patch('utils.rate_limiter.requests.get')
    def test_check_account_status_failure(self, mock_get):
        """测试账户状态检查失败"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_get.return_value = mock_response
        
        limiter = RateLimiter(self.api_key)
        result = limiter.check_account_status()
        
        self.assertIn('error', result)
    
    @patch('utils.rate_limiter.requests.get')
    def test_check_account_status_exception(self, mock_get):
        """测试账户状态检查异常"""
        mock_get.side_effect = Exception("Network error")
        
        limiter = RateLimiter(self.api_key)
        result = limiter.check_account_status()
        
        self.assertIn('error', result)
        self.assertIn('Network error', result['error'])
    
    def test_estimate_daily_limit_free_tier(self):
        """测试免费层日限制估算"""
        limiter = RateLimiter(self.api_key, self.rate_limit_config)
        limiter.account_info = {
            'data': {
                'limit': 5,
                'is_free_tier': True
            }
        }
        
        daily_limit = limiter._estimate_daily_limit()
        
        self.assertEqual(daily_limit, 5)
    
    def test_estimate_daily_limit_paid_tier(self):
        """测试付费层日限制估算"""
        limiter = RateLimiter(self.api_key, self.rate_limit_config)
        limiter.account_info = {
            'data': {
                'limit': 0.1,  # $0.10 = 10 credits
                'is_free_tier': False
            }
        }
        
        daily_limit = limiter._estimate_daily_limit()
        
        self.assertEqual(daily_limit, 1000)  # 0.1 * 10000 = 1000
    
    def test_estimate_daily_limit_no_account_info(self):
        """测试无账户信息时的日限制估算"""
        limiter = RateLimiter(self.api_key, self.rate_limit_config)
        
        daily_limit = limiter._estimate_daily_limit()
        
        self.assertEqual(daily_limit, 5)  # 默认免费层限制
    
    def test_can_make_request_allowed(self):
        """测试允许的请求"""
        limiter = RateLimiter(self.api_key, self.rate_limit_config)
        
        can_request, reason = limiter.can_make_request('free')
        
        self.assertTrue(can_request)
        self.assertEqual(reason, "可以发送请求")
    
    def test_can_make_request_10s_limit_exceeded(self):
        """测试10秒限制超出"""
        limiter = RateLimiter(self.api_key, self.rate_limit_config)
        
        # 填满10秒窗口
        for _ in range(10):
            limiter.record_request('free')
        
        can_request, reason = limiter.can_make_request('free')
        
        self.assertFalse(can_request)
        self.assertIn("10秒级限制", reason)
    
    def test_can_make_request_daily_limit_exceeded(self):
        """测试日限制超出"""
        limiter = RateLimiter(self.api_key, self.rate_limit_config)
        
        # 手动设置日使用量
        limiter.daily_usage['free'] = 5
        
        can_request, reason = limiter.can_make_request('free')
        
        self.assertFalse(can_request)
        self.assertIn("日级限制", reason)
    
    def test_is_free_model_in_paid_account(self):
        """测试付费账户下的免费模型检测"""
        limiter = RateLimiter(self.api_key, self.rate_limit_config)
        limiter.account_info = {
            'data': {
                'is_free_tier': False
            }
        }
        
        result1 = limiter._is_free_model_in_paid_account('google/gemma-3n-e2b-it:free')
        result2 = limiter._is_free_model_in_paid_account('openai/gpt-4')
        result3 = limiter._is_free_model_in_paid_account(None)
        
        self.assertTrue(result1)
        self.assertFalse(result2)
        self.assertFalse(result3)
    
    def test_is_free_model_in_free_account(self):
        """测试免费账户下的模型检测"""
        limiter = RateLimiter(self.api_key, self.rate_limit_config)
        limiter.account_info = {
            'data': {
                'is_free_tier': True
            }
        }
        
        result = limiter._is_free_model_in_paid_account('google/gemma-3n-e2b-it:free')
        
        self.assertFalse(result)
    
    def test_record_request_normal(self):
        """测试正常请求记录"""
        limiter = RateLimiter(self.api_key, self.rate_limit_config)
        
        limiter.record_request('free')
        
        self.assertEqual(limiter.daily_usage['free'], 1)
        self.assertEqual(len(limiter.request_history['free']), 1)
    
    def test_record_request_free_model_in_paid_account(self):
        """测试付费账户下免费模型的请求记录"""
        limiter = RateLimiter(self.api_key, self.rate_limit_config)
        limiter.account_info = {
            'data': {
                'is_free_tier': False
            }
        }
        
        limiter.record_request('free', 'google/gemma-3n-e2b-it:free')
        
        self.assertEqual(limiter.daily_usage.get('free', 0), 0)  # 不计入credit消耗
        self.assertEqual(len(limiter.request_history['free']), 1)  # 但记录历史
    
    def test_get_wait_time_no_wait_needed(self):
        """测试无需等待的情况"""
        limiter = RateLimiter(self.api_key, self.rate_limit_config)
        
        wait_time = limiter.get_wait_time('free')
        
        self.assertEqual(wait_time, 0.0)
    
    def test_get_wait_time_with_wait_needed(self):
        """测试需要等待的情况"""
        limiter = RateLimiter(self.api_key, self.rate_limit_config)
        
        # 填满10秒窗口
        for _ in range(10):
            limiter.record_request('free')
        
        wait_time = limiter.get_wait_time('free')
        
        self.assertGreater(wait_time, 0)
    
    @patch('utils.rate_limiter.time.sleep')
    def test_wait_if_needed_no_wait(self, mock_sleep):
        """测试无需等待的情况"""
        limiter = RateLimiter(self.api_key, self.rate_limit_config)
        
        waited = limiter.wait_if_needed('free')
        
        self.assertFalse(waited)
        mock_sleep.assert_not_called()
    
    @patch('utils.rate_limiter.time.sleep')
    def test_wait_if_needed_with_wait(self, mock_sleep):
        """测试需要等待的情况"""
        limiter = RateLimiter(self.api_key, self.rate_limit_config)
        
        # 填满10秒窗口
        for _ in range(10):
            limiter.record_request('free')
        
        waited = limiter.wait_if_needed('free')
        
        self.assertTrue(waited)
        mock_sleep.assert_called_once()
    
    def test_get_current_usage(self):
        """测试获取当前使用量"""
        limiter = RateLimiter(self.api_key, self.rate_limit_config)
        
        # 记录一些请求
        limiter.record_request('free')
        limiter.record_request('free')
        
        usage = limiter._get_current_usage()
        
        self.assertEqual(usage['requests_today'], 2)
        self.assertEqual(usage['limit_10s'], 10)
        self.assertEqual(usage['daily_limit'], 5)
    
    def test_get_rate_limit_info(self):
        """测试获取限流信息"""
        limiter = RateLimiter(self.api_key, self.rate_limit_config)
        
        with patch.object(limiter, 'check_account_status') as mock_check:
            mock_check.return_value = {'data': {'limit': 5}}
            
            info = limiter.get_rate_limit_info()
            
            self.assertIn('account_info', info)
            self.assertIn('configured_limits', info)
            self.assertIn('current_usage', info)
            self.assertIn('estimated_daily_limit', info)


class TestRateLimitedAPIClient(unittest.TestCase):
    """测试限流API客户端"""
    
    def setUp(self):
        """测试设置"""
        self.mock_api_client = Mock()
        self.mock_rate_limiter = Mock()
        self.client = RateLimitedAPIClient(self.mock_api_client, self.mock_rate_limiter)
    
    def test_generate_content_success(self):
        """测试成功生成内容"""
        self.mock_api_client.models = {'summary': 'test-model'}
        self.mock_rate_limiter.can_make_request.return_value = (True, "OK")
        self.mock_api_client.generate_content.return_value = "Generated content"
        
        result = self.client.generate_content('summary', 'test prompt')
        
        self.assertEqual(result, "Generated content")
        self.mock_rate_limiter.can_make_request.assert_called_once_with('free', 'test-model')
        self.mock_rate_limiter.record_request.assert_called_once_with('free', 'test-model')
    
    def test_generate_content_with_wait(self):
        """测试需要等待的内容生成"""
        self.mock_api_client.models = {'summary': 'test-model'}
        self.mock_rate_limiter.can_make_request.return_value = (False, "Rate limited")
        self.mock_api_client.generate_content.return_value = "Generated content"
        
        result = self.client.generate_content('summary', 'test prompt')
        
        self.assertEqual(result, "Generated content")
        self.mock_rate_limiter.wait_if_needed.assert_called_once_with('free')
    
    def test_generate_content_api_failure(self):
        """测试API调用失败"""
        self.mock_api_client.models = {'summary': 'test-model'}
        self.mock_rate_limiter.can_make_request.return_value = (True, "OK")
        self.mock_api_client.generate_content.side_effect = Exception("API Error")
        
        with self.assertRaises(Exception) as context:
            self.client.generate_content('summary', 'test prompt')
        
        self.assertEqual(str(context.exception), "API Error")


class TestCreateRateLimitedClient(unittest.TestCase):
    """测试创建限流客户端函数"""
    
    @patch('utils.rate_limiter.RateLimiter')
    def test_create_rate_limited_client(self, mock_rate_limiter_class):
        """测试创建限流客户端"""
        mock_original_client = Mock()
        mock_rate_limiter = Mock()
        mock_rate_limiter_class.return_value = mock_rate_limiter
        
        api_key = "test-key"
        rate_limit_config = {"test": "config"}
        
        client, limiter = create_rate_limited_client(
            mock_original_client, 
            api_key, 
            rate_limit_config
        )
        
        self.assertIsInstance(client, RateLimitedAPIClient)
        self.assertEqual(limiter, mock_rate_limiter)
        mock_rate_limiter_class.assert_called_once_with(api_key, rate_limit_config)
    
    @patch('utils.rate_limiter.RateLimiter')
    def test_create_rate_limited_client_without_config(self, mock_rate_limiter_class):
        """测试创建无配置的限流客户端"""
        mock_original_client = Mock()
        mock_rate_limiter = Mock()
        mock_rate_limiter_class.return_value = mock_rate_limiter
        
        api_key = "test-key"
        
        client, limiter = create_rate_limited_client(mock_original_client, api_key)
        
        self.assertIsInstance(client, RateLimitedAPIClient)
        self.assertEqual(limiter, mock_rate_limiter)
        mock_rate_limiter_class.assert_called_once_with(api_key, None)


if __name__ == '__main__':
    unittest.main()