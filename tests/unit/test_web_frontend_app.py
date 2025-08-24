#!/usr/bin/env python3
"""
Web前端应用程序测试

测试Web前端Flask应用的核心功能：
1. 模型下载API移除
2. 智能模型配置API
3. 代码清理验证
"""

import unittest
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestModelDownloadRemoval(unittest.TestCase):
    """测试移除模型下载功能"""
    
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
    def test_download_api_endpoints_removed(self, mock_ip_network, mock_ip_address):
        """测试下载API端点已被移除"""
        # Mock Tailscale网络检查通过
        mock_network = Mock()
        mock_ip = Mock()
        mock_ip_network.return_value = mock_network
        mock_ip_address.return_value = mock_ip
        mock_network.__contains__ = Mock(return_value=True)
        
        # 测试下载进度API不存在
        response = self.client.get('/api/models/download-progress/large-v3|distil')
        self.assertEqual(response.status_code, 404)
        
        # 测试下载API不存在
        response = self.client.post('/api/models/download/large-v3|distil')
        self.assertEqual(response.status_code, 404)
        
    @patch('ipaddress.ip_address')
    @patch('ipaddress.ip_network')
    def test_models_smart_config_only_downloaded(self, mock_ip_network, mock_ip_address):
        """测试模型配置API只返回已下载的模型"""
        # Mock Tailscale网络检查通过
        mock_network = Mock()
        mock_ip = Mock()
        mock_ip_network.return_value = mock_network
        mock_ip_address.return_value = mock_ip
        mock_network.__contains__ = Mock(return_value=True)
        
        response = self.client.get('/api/models/smart-config')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        
        # 验证返回的模型包含已下载模型、API模型或安装提示
        for lang_models in data.values():
            if isinstance(lang_models, list):
                for model in lang_models:
                    model_value = model.get('value', '')
                    if model_value == 'install_required':
                        # 安装提示项
                        self.assertIn('No models installed', model.get('display_name', ''))
                    elif 'api' in model_value:
                        # API模型不需要下载，应该有provider信息
                        self.assertIn('provider', model, f"API model {model_value} should have provider info")
                    else:
                        # 本地模型应该有下载状态信息
                        self.assertIn('downloaded', model, f"Local model {model_value} should have download status")


class TestCodeCleanup(unittest.TestCase):
    """测试代码清理"""
    
    def test_app_py_no_download_apis(self):
        """测试app.py不包含下载API"""
        app_path = Path('./src/web_frontend/app.py')
        if app_path.exists():
            content = app_path.read_text()
            
            # 不应该包含下载API路由
            self.assertNotIn('/api/models/download/<model_id>', content)
            self.assertNotIn('/api/models/download-progress/<model_id>', content)
            self.assertNotIn('api_model_download', content)
            self.assertNotIn('api_model_download_progress', content)
            
    def test_smart_config_api_updated(self):
        """测试smart-config API已更新"""
        app_path = Path('./src/web_frontend/app.py')
        if app_path.exists():
            content = app_path.read_text()
            
            # 应该包含简化的排序逻辑
            self.assertIn('apply_simplified_model_sorting', content)
            self.assertIn('get_model_complexity', content)
            
    def test_youtube_metadata_api_added(self):
        """测试YouTube元数据API已添加"""
        app_path = Path('./src/web_frontend/app.py')
        if app_path.exists():
            content = app_path.read_text()
            
            # 应该包含YouTube元数据API
            self.assertIn('/api/youtube/metadata', content)
            self.assertIn('api_youtube_metadata', content)


class TestSmartModelSorting(unittest.TestCase):
    """测试智能模型排序功能"""
    
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
    def test_smart_model_sorting_english_priority(self, mock_ip_network, mock_ip_address):
        """测试英文模式下智能排序优先级"""
        # Mock Tailscale网络检查通过
        mock_network = Mock()
        mock_ip = Mock()
        mock_ip_network.return_value = mock_network
        mock_ip_address.return_value = mock_ip
        mock_network.__contains__ = Mock(return_value=True)
        
        response = self.client.get('/api/models/smart-config')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        english_models = data.get('english', [])
        
        if len(english_models) > 0:
            # 验证distil模型在英文模式下优先推荐
            recommended_models = [m for m in english_models if m.get('recommended')]
            if recommended_models:
                # 检查第一个推荐模型是否包含distil
                first_recommended = recommended_models[0]
                self.assertIn('distil', first_recommended.get('value', '').lower())
                
    @patch('ipaddress.ip_address') 
    @patch('ipaddress.ip_network')
    def test_smart_model_sorting_multilingual_priority(self, mock_ip_network, mock_ip_address):
        """测试多语言模式下智能排序优先级"""
        # Mock Tailscale网络检查通过
        mock_network = Mock()
        mock_ip = Mock()
        mock_ip_network.return_value = mock_network
        mock_ip_address.return_value = mock_ip
        mock_network.__contains__ = Mock(return_value=True)
        
        response = self.client.get('/api/models/smart-config')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        multilingual_models = data.get('multilingual', [])
        
        if len(multilingual_models) > 0:
            # 验证openai模型在多语言模式下优先推荐
            recommended_models = [m for m in multilingual_models if m.get('recommended')]
            if recommended_models:
                # 检查第一个推荐模型是否包含openai
                first_recommended = recommended_models[0]
                self.assertIn('openai', first_recommended.get('value', '').lower())


class TestDefaultModelSelection(unittest.TestCase):
    """测试默认模型选择逻辑"""
    
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
        
    # Note: Recommendation system tests have been moved to test_recommendation_system.py
    # to avoid duplication and maintain focused test organization
                
    @patch('ipaddress.ip_address')
    @patch('ipaddress.ip_network')
    def test_install_required_handling(self, mock_ip_network, mock_ip_address):
        """测试未安装模型的处理逻辑"""
        # Mock Tailscale网络检查通过
        mock_network = Mock()
        mock_ip = Mock()
        mock_ip_network.return_value = mock_network
        mock_ip_address.return_value = mock_ip
        mock_network.__contains__ = Mock(return_value=True)
        
        response = self.client.get('/api/models/smart-config')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        
        # 验证install_required选项的格式
        for mode, models in data.items():
            if isinstance(models, list):
                install_options = [m for m in models if m.get('value') == 'install_required']
                for option in install_options:
                    self.assertIn('No models installed', option.get('display_name', ''))
                    self.assertFalse(option.get('recommended', True))  # 安装提示不应该被推荐


# TestLanguageBasedRecommendations class removed - these tests are now comprehensively 
# covered in test_recommendation_system.py to avoid duplication

class TestModelFilteringLogic(unittest.TestCase):
    """测试模型过滤逻辑"""
    
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
    def test_english_filter_shows_all_english_capable_models(self, mock_ip_network, mock_ip_address):
        """测试英文过滤器显示所有支持英文的模型"""
        # Mock Tailscale网络检查通过
        mock_network = Mock()
        mock_ip = Mock()
        mock_ip_network.return_value = mock_network
        mock_ip_address.return_value = mock_ip
        mock_network.__contains__ = Mock(return_value=True)
        
        response = self.client.get('/api/models/smart-config')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        all_models = data.get('all', [])
        
        # 检查distil模型是否正确标记为多语言支持
        distil_models = [m for m in all_models if 'distil' in m.get('value', '').lower()]
        for model in distil_models:
            if model.get('config_info', {}).get('vocab_size', 0) >= 51865:
                self.assertTrue(model.get('multilingual_support', False), 
                              f"Distil model with vocab_size >= 51865 should support multilingual: {model}")
                self.assertTrue(model.get('english_support', False),
                              f"Distil model should support English: {model}")
    
    @patch('ipaddress.ip_address') 
    @patch('ipaddress.ip_network')
    def test_multilingual_support_based_on_vocab_size(self, mock_ip_network, mock_ip_address):
        """测试多语言支持基于词汇表大小判断，不基于模型名称"""
        # Mock Tailscale网络检查通过
        mock_network = Mock()
        mock_ip = Mock()
        mock_ip_network.return_value = mock_network
        mock_ip_address.return_value = mock_ip
        mock_network.__contains__ = Mock(return_value=True)
        
        response = self.client.get('/api/models/smart-config')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        all_models = data.get('all', [])
        
        # 验证所有模型的多语言支持都基于vocab_size而不是名称
        for model in all_models:
            vocab_size = model.get('config_info', {}).get('vocab_size', 0)
            multilingual_support = model.get('multilingual_support', False)
            
            if vocab_size >= 51865:
                self.assertTrue(multilingual_support,
                              f"Model with vocab_size {vocab_size} should support multilingual: {model.get('name')}")
            elif vocab_size > 0 and vocab_size < 51865:
                self.assertFalse(multilingual_support,
                               f"Model with vocab_size {vocab_size} should not support multilingual: {model.get('name')}")


if __name__ == '__main__':
    unittest.main()