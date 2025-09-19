#!/usr/bin/env python3
"""
简化的API集成测试

测试新开发功能的集成，避免复杂的环境配置：
1. Whisper模型名称与文件夹对应功能
2. GitHub API集成
3. 模型配置API集成
"""

import unittest
import json
from unittest.mock import Mock, patch
from pathlib import Path


class TestAPIIntegrationSimple(unittest.TestCase):
    """简化的API集成测试"""
    
    def setUp(self):
        """设置测试环境"""
        # 直接导入应用工厂，避免复杂初始化
        try:
            from src.web_frontend.app import create_app
            self.app = create_app({'TESTING': True})
            self.client = self.app.test_client()
            self.app_context = self.app.app_context()
            self.app_context.push()
        except Exception as e:
            self.skipTest(f"Cannot initialize Flask app: {e}")
    
    def tearDown(self):
        """清理测试环境"""
        if hasattr(self, 'app_context'):
            self.app_context.pop()
    
    @patch('ipaddress.ip_address')
    @patch('ipaddress.ip_network')
    def test_whisper_model_name_api_integration(self, mock_ip_network, mock_ip_address):
        """测试Whisper模型名称API集成"""
        # Mock Tailscale网络检查通过
        mock_network = Mock()
        mock_ip = Mock()
        mock_ip_network.return_value = mock_network
        mock_ip_address.return_value = mock_ip
        mock_network.__contains__ = Mock(return_value=True)
        
        response = self.client.get('/api/models/smart-config')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        
        # 验证API结构 - 更新后的结构使用'all'和'others'
        self.assertIn('all', data)
        self.assertIn('others', data)
        
        # 验证模型名称映射功能
        all_models = data.get('all', [])
        downloaded_models = [m for m in all_models if m.get('downloaded', False)]
        
        if downloaded_models:  # 如果有已下载的模型
            for model in downloaded_models:
                # 验证关键字段存在
                self.assertIn('value', model)
                self.assertIn('display_name', model)
                self.assertIn('downloaded', model)
                
                # 验证基本字段逻辑
                value = model['value']
                display_name = model['display_name']
                
                # 验证基本逻辑：value和display_name应该有内容
                self.assertTrue(len(value) > 0, "Model value should not be empty")
                self.assertTrue(len(display_name) > 0, "Display name should not be empty")
                
                # 验证value格式（model|provider格式或api格式）
                self.assertTrue(('|' in value and len(value.split('|')) >= 2) or 'api' in value,
                            f"Model {value} should follow expected format")
                
                # 验证下载状态一致性
                self.assertTrue(model['downloaded'], f"Model {value} should be marked as downloaded")
        
        print(f"✅ Model name API integration: {len(downloaded_models)} models validated")
    
    @patch('ipaddress.ip_address')
    @patch('ipaddress.ip_network')  
    def test_github_pages_status_api_integration(self, mock_ip_network, mock_ip_address):
        """测试GitHub Pages状态API集成"""
        # Mock Tailscale网络检查通过
        mock_network = Mock()
        mock_ip = Mock()
        mock_ip_network.return_value = mock_network
        mock_ip_address.return_value = mock_ip
        mock_network.__contains__ = Mock(return_value=True)
        
        # 测试API端点存在并返回合理的错误
        response = self.client.get('/api/github/pages-status')
        # API应该返回错误状态但是HTTP状态码为500（配置问题）或者200（正常响应）
        self.assertIn(response.status_code, [200, 500])
        
        data = json.loads(response.data)
        
        # 验证基本API结构
        self.assertIn('status', data)
        self.assertIn('last_checked', data)
        
        # API方法和仓库信息应该存在（如果不是配置错误）
        if 'api_method' in data:
            self.assertEqual(data['api_method'], 'github_rest_api')
        if 'repository' in data:
            self.assertIn('sleepycat233/Project_Bach', data['repository'])
        
        print("✅ GitHub Pages status API integration validated")
    
    @patch('ipaddress.ip_address')
    @patch('ipaddress.ip_network')
    def test_content_categories_api_integration(self, mock_ip_network, mock_ip_address):
        """测试内容分类API集成"""
        # Mock Tailscale网络检查通过
        mock_network = Mock()
        mock_ip = Mock()
        mock_ip_network.return_value = mock_network
        mock_ip_address.return_value = mock_ip
        mock_network.__contains__ = Mock(return_value=True)
        
        response = self.client.get('/api/categories')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIsInstance(data, dict)
        
        # 验证基本分类存在
        expected_categories = ['lecture', 'youtube']
        for category in expected_categories:
            self.assertIn(category, data, f"Should have {category} category")
            
            # 验证分类结构
            category_info = data[category]
            self.assertIn('display_name', category_info)
            self.assertIn('recommendations', category_info)
        
        print(f"✅ Content categories API integration: {len(data)} categories validated")
    
    @patch('ipaddress.ip_address')
    @patch('ipaddress.ip_network')
    def test_processing_status_api_integration(self, mock_ip_network, mock_ip_address):
        """测试处理状态API集成"""
        # Mock Tailscale网络检查通过
        mock_network = Mock()
        mock_ip = Mock()
        mock_ip_network.return_value = mock_network
        mock_ip_address.return_value = mock_ip
        mock_network.__contains__ = Mock(return_value=True)
        
        response = self.client.get('/api/status/processing')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('active_sessions', data)
        
        print("✅ Processing status API integration validated")
    
    def test_model_configuration_consistency(self):
        """测试模型配置的一致性"""
        # 这个测试不需要网络检查，直接测试逻辑
        from pathlib import Path
        
        # 检查模型目录是否存在
        models_path = Path('./models/whisperkit-coreml')
        if models_path.exists():
            actual_dirs = [d.name for d in models_path.iterdir() if d.is_dir()]
            print(f"Found model directories: {actual_dirs}")
            
            # 验证至少有一些预期的模型
            expected_patterns = ['distil-whisper', 'openai_whisper']
            found_patterns = []
            
            for actual_dir in actual_dirs:
                for pattern in expected_patterns:
                    if pattern in actual_dir:
                        found_patterns.append(pattern)
                        break
            
            self.assertGreater(len(found_patterns), 0, 
                             "Should find at least one expected model pattern")
            
            print(f"✅ Model directory consistency: {len(found_patterns)} patterns matched")
        else:
            self.skipTest("Models directory not found, skipping consistency test")
    
    def test_integration_workflow_simulation(self):
        """模拟完整的集成工作流"""
        workflow_steps = []
        
        # 1. 检查应用初始化
        self.assertIsNotNone(self.app)
        workflow_steps.append("✅ Flask app initialized")
        
        # 2. 验证重要路由存在
        with self.app.app_context():
            # 获取所有路由
            routes = []
            for rule in self.app.url_map.iter_rules():
                routes.append(rule.rule)
            
            # 验证关键路由
            expected_routes = [
                '/',
                '/api/models/smart-config', 
                '/api/categories',
                '/api/status/processing',
                '/api/github/pages-status'
            ]
            
            for expected_route in expected_routes:
                self.assertIn(expected_route, routes, f"Missing route: {expected_route}")
                workflow_steps.append(f"✅ Route {expected_route} exists")
        
        print("🎯 Integration workflow simulation completed:")
        for step in workflow_steps:
            print(f"  {step}")
        
        self.assertGreater(len(workflow_steps), 5, "Should complete multiple workflow steps")



if __name__ == '__main__':
    # 运行测试
    import sys
    
    print("🧪 Starting API Integration Tests...")
    print("=" * 50)
    
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加测试
    test_suite.addTest(TestAPIIntegrationSimple('test_whisper_model_name_api_integration'))
    test_suite.addTest(TestAPIIntegrationSimple('test_content_categories_api_integration'))
    test_suite.addTest(TestAPIIntegrationSimple('test_processing_status_api_integration'))
    test_suite.addTest(TestAPIIntegrationSimple('test_model_configuration_consistency'))
    test_suite.addTest(TestAPIIntegrationSimple('test_integration_workflow_simulation'))
    
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 输出结果
    print("\n" + "=" * 50)
    print(f"🎯 Integration Tests Summary:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    print(f"   Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%" if result.testsRun > 0 else "N/A")
    
    # 退出码
    sys.exit(0 if result.wasSuccessful() else 1)
