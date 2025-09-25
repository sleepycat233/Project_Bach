#!/usr/bin/env python3.11
"""
统一的API端点测试
整合所有API测试，减少重复，适配create_api_response统一响应格式
"""

import unittest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.web_frontend.app import create_app
from src.utils.config import ConfigManager


class TestAPIEndpoints(unittest.TestCase):
    """统一的API端点测试 - 适配create_api_response响应格式"""

    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

        # 创建测试用的临时配置
        self.config_manager = ConfigManager()

        # Mock网络检查
        with patch('src.web_frontend.app.ipaddress.ip_network'), \
             patch('src.web_frontend.app.ipaddress.ip_address'):
            self.app = create_app()
            self.app.config['TESTING'] = True
            self.processing_service = MagicMock()
            self.app.config['PROCESSING_SERVICE'] = self.processing_service
            self.client = self.app.test_client()

    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_categories_api_http(self):
        """测试分类API - 仅HTTP层面和响应格式"""
        with patch('src.web_frontend.app.get_processing_service'):
            response = self.client.get('/api/categories')

            # HTTP层测试
            self.assertEqual(response.status_code, 200)
            self.assertIn('application/json', response.content_type)

            data = json.loads(response.data)

            # 只验证统一响应格式，业务逻辑在Unit测试
            self.assertIn('success', data)
            self.assertTrue(data['success'])
            self.assertIn('timestamp', data)
            self.assertIn('data', data)

        print("✅ Categories API HTTP layer validated")

    def test_processing_status_api(self):
        """测试处理状态API - 适配统一响应格式"""
        with self.app.app_context():
            # Mock处理服务 - 直接mock app.config中的service
            mock_service = MagicMock()
            mock_service.list_active_sessions.return_value = []
            self.app.config['PROCESSING_SERVICE'] = mock_service

            response = self.client.get('/api/status/processing')

            self.assertEqual(response.status_code, 200)

            data = json.loads(response.data)

            # 验证统一响应格式
            self.assertIn('success', data)
            self.assertTrue(data['success'])
            self.assertIn('timestamp', data)
            self.assertIn('data', data)

            # 验证数据结构
            response_data = data['data']
            self.assertIn('active_sessions', response_data)
            self.assertIsInstance(response_data['active_sessions'], list)

        print("✅ Processing status API unified response format validated")

    def test_single_status_api(self):
        """测试单个状态API - 适配统一响应格式"""
        test_processing_id = 'test_123'

        with self.app.app_context():
            # Mock成功情况 - 直接mock app.config中的service
            mock_service = MagicMock()
            mock_service.get_status.return_value = {
                'stage': 'processing',
                'progress': 50,
                'message': 'Test message'
            }
            self.app.config['PROCESSING_SERVICE'] = mock_service

            response = self.client.get(f'/api/status/{test_processing_id}')

            self.assertEqual(response.status_code, 200)

            data = json.loads(response.data)

            # 验证统一响应格式
            self.assertIn('success', data)
            self.assertTrue(data['success'])
            self.assertIn('data', data)

            # 验证状态数据
            status_data = data['data']
            self.assertEqual(status_data['stage'], 'processing')
            self.assertEqual(status_data['progress'], 50)

        print("✅ Single status API unified response format validated")

    def test_single_status_api_not_found(self):
        """测试单个状态API - 未找到处理ID"""
        test_processing_id = 'nonexistent_id'

        with self.app.app_context():
            # Mock未找到情况 - 直接mock app.config中的service
            mock_service = MagicMock()
            mock_service.get_status.return_value = None
            self.app.config['PROCESSING_SERVICE'] = mock_service

            response = self.client.get(f'/api/status/{test_processing_id}')

            self.assertEqual(response.status_code, 404)

            data = json.loads(response.data)

            # 验证统一错误响应格式
            self.assertIn('success', data)
            self.assertFalse(data['success'])
            self.assertIn('error', data)
            self.assertEqual(data['error'], 'Processing session not found')

    def test_recent_results_api(self):
        """测试最近结果API - 适配统一响应格式"""
        with patch('src.storage.result_storage.ResultStorage') as mock_storage_class:
            # Mock结果存储
            mock_storage = MagicMock()
            mock_storage.get_recent_results.return_value = [
                {'filename': 'test1', 'timestamp': '2023-01-01'},
                {'filename': 'test2', 'timestamp': '2023-01-02'}
            ]
            mock_storage_class.return_value = mock_storage

            response = self.client.get('/api/results/recent?limit=5')

            self.assertEqual(response.status_code, 200)

            data = json.loads(response.data)

            # 验证统一响应格式
            self.assertIn('success', data)
            self.assertTrue(data['success'])
            self.assertIn('data', data)

            # 验证结果数据
            results = data['data']
            self.assertIsInstance(results, list)
            self.assertEqual(len(results), 2)

        print("✅ Recent results API unified response format validated")

    def test_create_subcategory_api(self):
        """测试创建子分类API - 适配统一响应格式"""
        with self.app.app_context():
            # Mock内容类型服务
            mock_service = MagicMock()
            mock_service.save_subcategory.return_value = None  # save操作通常返回None表示成功
            self.app.config['CONTENT_TYPE_SERVICE'] = mock_service

            # 测试数据
            test_data = {
                'content_type': 'lecture',
                'subcategory': 'CS101',
                'display_name': 'Computer Science 101',
                'config': json.dumps({
                    'enable_anonymization': True,
                    'enable_summary': True
                })
            }

            response = self.client.post('/api/preferences/subcategory',
                                      json=test_data,
                                      content_type='application/json')

            self.assertEqual(response.status_code, 200)

            data = json.loads(response.data)

            # 验证统一响应格式
            self.assertIn('success', data)
            self.assertTrue(data['success'])
            self.assertIn('message', data)
            self.assertIn('Computer Science 101', data['message'])

        print("✅ Create subcategory API unified response format validated")

    def test_api_error_handling(self):
        """测试API错误处理的一致性"""
        # 测试categories API在出错时的响应
        with patch('src.web_frontend.app.get_content_types_config') as mock_get_types:
            mock_get_types.side_effect = Exception("Test error")

            response = self.client.get('/api/categories')

            self.assertEqual(response.status_code, 500)

            data = json.loads(response.data)

            # 验证统一错误响应格式
            self.assertIn('success', data)
            self.assertFalse(data['success'])
            self.assertIn('error', data)

        print("✅ API error handling consistency validated")

    def test_api_response_headers(self):
        """测试API响应头的一致性"""
        with patch('src.web_frontend.app.get_processing_service'):
            endpoints_to_test = [
                '/api/categories',
                '/api/status/processing'
            ]

            for endpoint in endpoints_to_test:
                response = self.client.get(endpoint)

                # 验证Content-Type
                self.assertIn('application/json', response.content_type)

                # 验证响应是有效的JSON
                try:
                    json.loads(response.data)
                except json.JSONDecodeError:
                    self.fail(f"Response from {endpoint} is not valid JSON")

        print("✅ API response headers consistency validated")


    def test_github_config_status_api_http(self):
        """测试GitHub配置状态API - 仅HTTP层面测试"""
        with patch('src.web_frontend.app.get_processing_service'):
            response = self.client.get('/api/config/github-status')

            # 只测试HTTP层面
            self.assertEqual(response.status_code, 200)
            self.assertIn('application/json', response.content_type)

            data = json.loads(response.data)

            # 只验证响应格式，不测试具体配置逻辑
            self.assertIn('success', data)
            self.assertIn('timestamp', data)

        print("✅ GitHub config status API HTTP layer validated")


if __name__ == '__main__':
    unittest.main()
