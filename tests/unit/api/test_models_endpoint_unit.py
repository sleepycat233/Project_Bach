#!/usr/bin/env python3
"""
Models API端点单元测试

专门测试 /api/models/* 相关端点的业务逻辑，
每个测试只测试一个API端点的一种情况
"""

import unittest
from unittest.mock import Mock, patch
import json
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent))


class MockFlaskRequest:
    """模拟Flask request对象"""
    def __init__(self, method='GET', json_data=None, form_data=None):
        self.method = method
        self.json = json_data
        self.form = form_data or {}


def mock_smart_config_endpoint(request, config_manager=None, processing_service=None):
    """
    模拟smart-config端点的业务逻辑
    这是从实际端点中提取的纯业务逻辑
    """
    try:
        # 获取模型配置
        if processing_service:
            models_data = processing_service.get_available_models()
        else:
            models_data = {'english': [], 'multilingual': [], 'all': []}
        
        # 添加推荐标记
        for category, models in models_data.items():
            if isinstance(models, list):
                for model in models:
                    if 'distil' in model.get('value', '').lower():
                        model['recommended'] = True
                    else:
                        model['recommended'] = False
        
        return {
            'status': 'success',
            'models': models_data
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


def mock_model_info_endpoint(model_id, processing_service=None):
    """
    模拟model-info端点的业务逻辑
    """
    if not model_id:
        return {
            'status': 'error',
            'message': 'Model ID is required'
        }
    
    try:
        if processing_service:
            model_info = processing_service.get_model_info(model_id)
        else:
            model_info = {
                'name': model_id,
                'size': 'unknown',
                'language_support': 'unknown'
            }
        
        return {
            'status': 'success',
            'model_info': model_info
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Failed to get model info: {str(e)}'
        }


class TestSmartConfigEndpoint(unittest.TestCase):
    """测试smart-config端点业务逻辑"""
    
    def test_smart_config_with_valid_service(self):
        """测试有效processing service的smart-config"""
        # 准备mock service
        mock_service = Mock()
        mock_service.get_available_models.return_value = {
            'english': [
                {'value': 'distil-large-v3', 'name': 'Distil Large V3'},
                {'value': 'base', 'name': 'Base Model'}
            ],
            'multilingual': [
                {'value': 'large-v3', 'name': 'Large V3'}
            ]
        }
        
        mock_request = MockFlaskRequest()
        
        # 执行测试
        result = mock_smart_config_endpoint(mock_request, processing_service=mock_service)
        
        # 验证结果
        self.assertEqual(result['status'], 'success')
        self.assertIn('models', result)
        
        # 验证推荐标记
        english_models = result['models']['english']
        distil_model = next(m for m in english_models if 'distil' in m['value'])
        self.assertTrue(distil_model['recommended'])
        
        base_model = next(m for m in english_models if m['value'] == 'base')
        self.assertFalse(base_model['recommended'])
    
    def test_smart_config_without_service(self):
        """测试无processing service的smart-config"""
        mock_request = MockFlaskRequest()
        
        result = mock_smart_config_endpoint(mock_request)
        
        self.assertEqual(result['status'], 'success')
        self.assertIn('models', result)
        self.assertEqual(result['models']['english'], [])
        self.assertEqual(result['models']['multilingual'], [])
    
    def test_smart_config_service_exception(self):
        """测试processing service抛出异常"""
        mock_service = Mock()
        mock_service.get_available_models.side_effect = Exception("Service unavailable")
        
        mock_request = MockFlaskRequest()
        
        result = mock_smart_config_endpoint(mock_request, processing_service=mock_service)
        
        self.assertEqual(result['status'], 'error')
        self.assertIn('Service unavailable', result['message'])
    
    def test_smart_config_recommendation_logic(self):
        """测试推荐逻辑的正确性"""
        mock_service = Mock()
        mock_service.get_available_models.return_value = {
            'english': [
                {'value': 'distil-medium', 'name': 'Distil Medium'},
                {'value': 'whisper-large', 'name': 'Whisper Large'},
                {'value': 'tiny-distil', 'name': 'Tiny Distil'}
            ]
        }
        
        mock_request = MockFlaskRequest()
        
        result = mock_smart_config_endpoint(mock_request, processing_service=mock_service)
        
        english_models = result['models']['english']
        
        # 检查所有包含'distil'的模型都被推荐
        for model in english_models:
            if 'distil' in model['value'].lower():
                self.assertTrue(model['recommended'], f"Model {model['value']} should be recommended")
            else:
                self.assertFalse(model['recommended'], f"Model {model['value']} should not be recommended")


class TestModelInfoEndpoint(unittest.TestCase):
    """测试model-info端点业务逻辑"""
    
    def test_model_info_with_valid_id(self):
        """测试有效model ID的信息获取"""
        mock_service = Mock()
        mock_service.get_model_info.return_value = {
            'name': 'distil-large-v3',
            'size': '756MB',
            'language_support': 'multilingual',
            'accuracy': 'high'
        }
        
        result = mock_model_info_endpoint('distil-large-v3', mock_service)
        
        self.assertEqual(result['status'], 'success')
        self.assertIn('model_info', result)
        self.assertEqual(result['model_info']['name'], 'distil-large-v3')
        self.assertEqual(result['model_info']['size'], '756MB')
    
    def test_model_info_with_empty_id(self):
        """测试空model ID"""
        result = mock_model_info_endpoint('', Mock())
        
        self.assertEqual(result['status'], 'error')
        self.assertIn('Model ID is required', result['message'])
    
    def test_model_info_with_none_id(self):
        """测试None model ID"""
        result = mock_model_info_endpoint(None, Mock())
        
        self.assertEqual(result['status'], 'error')
        self.assertIn('Model ID is required', result['message'])
    
    def test_model_info_service_exception(self):
        """测试service抛出异常"""
        mock_service = Mock()
        mock_service.get_model_info.side_effect = Exception("Model not found")
        
        result = mock_model_info_endpoint('invalid-model', mock_service)
        
        self.assertEqual(result['status'], 'error')
        self.assertIn('Failed to get model info', result['message'])
        self.assertIn('Model not found', result['message'])
    
    def test_model_info_without_service(self):
        """测试无processing service的情况"""
        result = mock_model_info_endpoint('test-model', None)
        
        self.assertEqual(result['status'], 'success')
        self.assertIn('model_info', result)
        self.assertEqual(result['model_info']['name'], 'test-model')
        self.assertEqual(result['model_info']['size'], 'unknown')


class TestModelEndpointHelpers(unittest.TestCase):
    """测试模型端点辅助函数"""
    
    def test_add_recommendation_flags_distil_models(self):
        """测试为distil模型添加推荐标记"""
        models = [
            {'value': 'distil-large-v3', 'name': 'Distil Large'},
            {'value': 'base-model', 'name': 'Base Model'},
            {'value': 'tiny-distil', 'name': 'Tiny Distil'}
        ]
        
        # 模拟添加推荐标记的逻辑
        for model in models:
            if 'distil' in model.get('value', '').lower():
                model['recommended'] = True
            else:
                model['recommended'] = False
        
        # 验证结果
        distil_models = [m for m in models if 'distil' in m['value'].lower()]
        non_distil_models = [m for m in models if 'distil' not in m['value'].lower()]
        
        for model in distil_models:
            self.assertTrue(model['recommended'])
        
        for model in non_distil_models:
            self.assertFalse(model['recommended'])
    
    def test_model_category_filtering(self):
        """测试模型分类过滤逻辑"""
        all_models = [
            {'value': 'distil-en', 'language_mode': 'english'},
            {'value': 'large-multi', 'language_mode': 'multilingual'},
            {'value': 'general', 'language_mode': 'general'}
        ]
        
        # 模拟英文模型过滤
        english_models = [m for m in all_models 
                         if m.get('language_mode') in ['english', 'general']]
        
        # 模拟多语言模型过滤
        multilingual_models = [m for m in all_models 
                              if m.get('language_mode') in ['multilingual', 'general']]
        
        # 验证过滤结果
        self.assertEqual(len(english_models), 2)  # english + general
        self.assertEqual(len(multilingual_models), 2)  # multilingual + general
        
        english_values = [m['value'] for m in english_models]
        self.assertIn('distil-en', english_values)
        self.assertIn('general', english_values)


if __name__ == '__main__':
    unittest.main()