#!/usr/bin/env python3.11
"""
AI内容生成模块的单元测试
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from core.ai_generation import (
    AIContentGenerator, 
    OpenRouterClient, 
    APIException,
    ContentGenerator,
    ContentValidator
)
from utils.rate_limiter import RateLimitedAPIClient


class TestAIContentGenerator(unittest.TestCase):
    """测试AI内容生成器"""
    
    def setUp(self):
        """测试设置"""
        self.api_config = {
            'openrouter': {
                'key': 'test-api-key',
                'base_url': 'https://openrouter.ai/api/v1',
                'models': {
                    'summary': 'test-model',
                    'mindmap': 'test-model'
                },
                'rate_limits': {
                    'free_tier': {
                        'requests_per_10s': 10,
                        'daily_credit_limit': 5
                    }
                }
            }
        }
    
    @patch('core.ai_generation.create_rate_limited_client')
    @patch('core.ai_generation.OpenRouterClient')
    def test_init_with_rate_limiting(self, mock_client_class, mock_rate_limited):
        """测试启用限流的初始化"""
        mock_client = Mock()
        mock_rate_limiter = Mock()
        mock_client_class.return_value = mock_client
        mock_rate_limited.return_value = (mock_client, mock_rate_limiter)
        
        generator = AIContentGenerator(self.api_config, enable_rate_limiting=True)
        
        self.assertEqual(generator.client, mock_client)
        self.assertEqual(generator.rate_limiter, mock_rate_limiter)
        mock_rate_limited.assert_called_once()
    
    @patch('core.ai_generation.OpenRouterClient')
    def test_init_without_rate_limiting(self, mock_client_class):
        """测试禁用限流的初始化"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        generator = AIContentGenerator(self.api_config, enable_rate_limiting=False)
        
        self.assertEqual(generator.client, mock_client)
        self.assertIsNone(generator.rate_limiter)
    
    @patch('core.ai_generation.OpenRouterClient')
    def test_init_without_api_key(self, mock_client_class):
        """测试没有API密钥的初始化"""
        config_without_key = {
            'openrouter': {
                'key': 'YOUR_API_KEY_HERE',
                'models': {}
            }
        }
        
        generator = AIContentGenerator(config_without_key, enable_rate_limiting=True)
        
        self.assertIsNone(generator.rate_limiter)
    
    def test_generate_summary_success(self):
        """测试成功生成摘要"""
        mock_client = Mock()
        mock_client.generate_content.return_value = "This is a test summary"
        
        generator = AIContentGenerator(self.api_config, enable_rate_limiting=False)
        generator.client = mock_client
        
        result = generator.generate_summary("test text")
        
        self.assertEqual(result, "This is a test summary")
        mock_client.generate_content.assert_called_once_with(
            model_type='summary',
            prompt="请为以下内容生成一个简洁的摘要（300字以内）：\n\ntest text",
            max_tokens=500,
            temperature=0.7
        )
    
    def test_generate_summary_failure(self):
        """测试摘要生成失败"""
        mock_client = Mock()
        mock_client.generate_content.side_effect = Exception("API Error")
        
        generator = AIContentGenerator(self.api_config, enable_rate_limiting=False)
        generator.client = mock_client
        
        result = generator.generate_summary("test text")
        
        self.assertIn("摘要生成失败", result)
        self.assertIn("API Error", result)
    
    def test_generate_mindmap_success(self):
        """测试成功生成思维导图"""
        mock_client = Mock()
        mock_client.generate_content.return_value = "# Test Mindmap\n- Item 1\n- Item 2"
        
        generator = AIContentGenerator(self.api_config, enable_rate_limiting=False)
        generator.client = mock_client
        
        result = generator.generate_mindmap("test text")
        
        self.assertEqual(result, "# Test Mindmap\n- Item 1\n- Item 2")
        mock_client.generate_content.assert_called_once_with(
            model_type='mindmap',
            prompt="请将以下内容整理成Markdown格式的思维导图结构，使用#、##、###等标题层级和-列表项：\n\ntest text",
            max_tokens=800,
            temperature=0.5
        )
    
    def test_generate_custom_content(self):
        """测试生成自定义内容"""
        mock_client = Mock()
        mock_client.generate_content.return_value = "Custom content result"
        
        generator = AIContentGenerator(self.api_config, enable_rate_limiting=False)
        generator.client = mock_client
        
        result = generator.generate_custom_content(
            "test text", 
            "Custom task",
            model_type="summary",
            max_tokens=100
        )
        
        self.assertEqual(result, "Custom content result")
        mock_client.generate_content.assert_called_once_with(
            model_type='summary',
            prompt="Custom task\n\ntest text",
            max_tokens=100
        )
    
    def test_get_rate_limit_status_with_limiter(self):
        """测试获取限流状态（有限流器）"""
        mock_rate_limiter = Mock()
        mock_rate_limiter.get_rate_limit_info.return_value = {"status": "ok"}
        
        generator = AIContentGenerator(self.api_config, enable_rate_limiting=False)
        generator.rate_limiter = mock_rate_limiter
        
        result = generator.get_rate_limit_status()
        
        self.assertEqual(result, {"status": "ok"})
    
    def test_get_rate_limit_status_without_limiter(self):
        """测试获取限流状态（无限流器）"""
        generator = AIContentGenerator(self.api_config, enable_rate_limiting=False)
        
        result = generator.get_rate_limit_status()
        
        self.assertEqual(result, {"rate_limiting": "disabled"})


class TestOpenRouterClient(unittest.TestCase):
    """测试OpenRouter客户端"""
    
    def setUp(self):
        """测试设置"""
        self.config = {
            'key': 'test-api-key',
            'base_url': 'https://openrouter.ai/api/v1',
            'models': {
                'summary': 'test-summary-model',
                'mindmap': 'test-mindmap-model'
            }
        }
    
    def test_init(self):
        """测试初始化"""
        client = OpenRouterClient(self.config)
        
        self.assertEqual(client.config, self.config)
        self.assertEqual(client.base_url, 'https://openrouter.ai/api/v1')
        self.assertEqual(client.models, self.config['models'])
        self.assertEqual(client.request_timeout, 30)
        self.assertEqual(client.max_retries, 3)
    
    @patch('core.ai_generation.requests.Session')
    def test_generate_content_success(self, mock_session_class):
        """测试成功生成内容"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'Generated content'}}]
        }
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        client = OpenRouterClient(self.config)
        
        result = client.generate_content('summary', 'test prompt')
        
        self.assertEqual(result, 'Generated content')
        mock_session.post.assert_called_once()
    
    @patch('core.ai_generation.requests.Session')
    def test_generate_content_model_not_found(self, mock_session_class):
        """测试模型不存在"""
        client = OpenRouterClient(self.config)
        
        with self.assertRaises(APIException) as context:
            client.generate_content('nonexistent', 'test prompt')
        
        self.assertIn("未找到模型类型", str(context.exception))
    
    @patch('core.ai_generation.requests.Session')
    def test_generate_content_http_error(self, mock_session_class):
        """测试HTTP错误"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            'error': {'message': 'Bad request'}
        }
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        client = OpenRouterClient(self.config)
        
        with self.assertRaises(APIException) as context:
            client.generate_content('summary', 'test prompt')
        
        self.assertIn("400", str(context.exception))
    
    @patch('core.ai_generation.requests.Session')
    def test_generate_content_with_retry(self, mock_session_class):
        """测试重试机制"""
        mock_session = Mock()
        
        # 第一次调用失败，第二次成功
        mock_response_fail = Mock()
        mock_response_fail.status_code = 500
        mock_response_fail.json.return_value = {'error': {'message': 'Server error'}}
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            'choices': [{'message': {'content': 'Success after retry'}}]
        }
        
        mock_session.post.side_effect = [mock_response_fail, mock_response_success]
        mock_session_class.return_value = mock_session
        
        client = OpenRouterClient(self.config)
        
        with patch('core.ai_generation.time.sleep'):  # 避免实际等待
            result = client.generate_content('summary', 'test prompt')
        
        self.assertEqual(result, 'Success after retry')
        self.assertEqual(mock_session.post.call_count, 2)
    
    def test_test_connection_success(self):
        """测试连接测试成功"""
        client = OpenRouterClient(self.config)
        
        with patch.object(client, '_make_request') as mock_make_request:
            mock_make_request.return_value = "test response"
            
            result = client.test_connection()
            
            self.assertTrue(result)
    
    def test_test_connection_failure(self):
        """测试连接测试失败"""
        client = OpenRouterClient(self.config)
        
        with patch.object(client, '_make_request') as mock_make_request:
            mock_make_request.side_effect = Exception("Connection failed")
            
            result = client.test_connection()
            
            self.assertFalse(result)
    
    def test_get_available_models(self):
        """测试获取可用模型"""
        client = OpenRouterClient(self.config)
        
        models = client.get_available_models()
        
        self.assertEqual(models, self.config['models'])
    
    def test_update_model(self):
        """测试更新模型配置"""
        client = OpenRouterClient(self.config)
        
        client.update_model('summary', 'new-model')
        
        self.assertEqual(client.models['summary'], 'new-model')


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
    
    def test_generate_content_with_rate_limit(self):
        """测试受限流影响的内容生成"""
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


class TestContentGenerator(unittest.TestCase):
    """测试内容生成器工厂类"""
    
    def test_create_summary_generator(self):
        """测试创建摘要生成器"""
        api_config = {'test': 'config'}
        
        generator = ContentGenerator.create_summary_generator(api_config)
        
        self.assertIsInstance(generator, AIContentGenerator)
    
    def test_create_mindmap_generator(self):
        """测试创建思维导图生成器"""
        api_config = {'test': 'config'}
        
        generator = ContentGenerator.create_mindmap_generator(api_config)
        
        self.assertIsInstance(generator, AIContentGenerator)


class TestContentValidator(unittest.TestCase):
    """测试内容验证器"""
    
    def test_validate_summary_valid(self):
        """测试有效摘要验证"""
        valid_summary = "这是一个有效的摘要，包含足够的内容。"
        
        result = ContentValidator.validate_summary(valid_summary)
        
        self.assertTrue(result)
    
    def test_validate_summary_too_short(self):
        """测试过短摘要验证"""
        short_summary = "太短"
        
        result = ContentValidator.validate_summary(short_summary)
        
        self.assertFalse(result)
    
    def test_validate_summary_with_error(self):
        """测试包含错误的摘要验证"""
        error_summary = "生成失败，出现错误"
        
        result = ContentValidator.validate_summary(error_summary)
        
        self.assertFalse(result)
    
    def test_validate_summary_invalid_input(self):
        """测试无效输入的摘要验证"""
        result1 = ContentValidator.validate_summary(None)
        result2 = ContentValidator.validate_summary("")
        result3 = ContentValidator.validate_summary(123)
        
        self.assertFalse(result1)
        self.assertFalse(result2)
        self.assertFalse(result3)
    
    def test_validate_mindmap_valid(self):
        """测试有效思维导图验证"""
        valid_mindmap = "# 主题\n- 子项目1\n- 子项目2"
        
        result = ContentValidator.validate_mindmap(valid_mindmap)
        
        self.assertTrue(result)
    
    def test_validate_mindmap_no_markdown(self):
        """测试没有Markdown标记的思维导图验证"""
        no_markdown = "这只是普通文本，没有任何标记"
        
        result = ContentValidator.validate_mindmap(no_markdown)
        
        self.assertFalse(result)
    
    def test_validate_mindmap_with_error(self):
        """测试包含错误的思维导图验证"""
        error_mindmap = "# 标题\n思维导图生成异常"
        
        result = ContentValidator.validate_mindmap(error_mindmap)
        
        self.assertFalse(result)


class TestAPIException(unittest.TestCase):
    """测试API异常类"""
    
    def test_api_exception_basic(self):
        """测试基本API异常"""
        exception = APIException("Test error")
        
        self.assertEqual(str(exception), "Test error")
        self.assertIsNone(exception.status_code)
        self.assertIsNone(exception.response_data)
    
    def test_api_exception_with_details(self):
        """测试带详细信息的API异常"""
        response_data = {"error": "details"}
        exception = APIException("Test error", status_code=400, response_data=response_data)
        
        self.assertEqual(str(exception), "Test error")
        self.assertEqual(exception.status_code, 400)
        self.assertEqual(exception.response_data, response_data)


if __name__ == '__main__':
    unittest.main()