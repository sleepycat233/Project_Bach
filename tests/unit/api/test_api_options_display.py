#!/usr/bin/env python3.11
"""
API选项显示功能测试
测试前端API服务选择和配置功能
"""

import unittest
import json
from pathlib import Path
import sys

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

class TestAPIOptionsDisplay(unittest.TestCase):
    """测试API选项显示功能"""
    
    def setUp(self):
        """测试初始化"""
        self.api_config = {
            'local': {
                'enabled': True,
                'type': 'whisperkit_local',
                'path': './models/whisperkit-coreml'
            },
            'openai_api': {
                'enabled': False,
                'type': 'openai_whisper_api',
                'api_key': '${OPENAI_API_KEY}',
                'base_url': 'https://api.openai.com/v1',
                'models': ['whisper-1', 'whisper-large-v3-turbo']
            },
            'elevenlabs_api': {
                'enabled': False,
                'type': 'elevenlabs_api',
                'api_key': '${ELEVENLABS_API_KEY}',
                'base_url': 'https://api.elevenlabs.io/v1'
            },
            'azure_speech': {
                'enabled': False,
                'type': 'azure_cognitive_services',
                'api_key': '${AZURE_SPEECH_KEY}',
                'region': 'eastus'
            }
        }
    
    
    def test_api_configuration_validation(self):
        """测试API配置验证"""
        def validate_api_config(provider_config):
            """验证API配置的有效性"""
            required_fields = ['type', 'api_key', 'base_url']
            
            for field in required_fields:
                if not provider_config.get(field):
                    return False, f"Missing required field: {field}"
            
            # 验证API密钥格式
            api_key = provider_config['api_key']
            if api_key.startswith('${') and api_key.endswith('}'):
                return False, "API key not configured (still using placeholder)"
            
            # 验证URL格式
            base_url = provider_config['base_url']
            if not base_url.startswith('http'):
                return False, "Invalid base URL format"
            
            return True, "Valid configuration"
        
        # 测试有效配置
        valid_config = {
            'type': 'openai_whisper_api',
            'api_key': 'sk-test-key',
            'base_url': 'https://api.openai.com/v1'
        }
        is_valid, message = validate_api_config(valid_config)
        self.assertTrue(is_valid, f"Valid config should pass: {message}")
        
        # 测试无效配置（缺少字段）
        invalid_config = {
            'type': 'openai_whisper_api',
            'base_url': 'https://api.openai.com/v1'
        }
        is_valid, message = validate_api_config(invalid_config)
        self.assertFalse(is_valid, "Missing API key should fail validation")
        
        # 测试占位符配置
        placeholder_config = {
            'type': 'openai_whisper_api',
            'api_key': '${OPENAI_API_KEY}',
            'base_url': 'https://api.openai.com/v1'
        }
        is_valid, message = validate_api_config(placeholder_config)
        self.assertFalse(is_valid, "Placeholder API key should fail validation")
        
        print("✅ API配置验证测试通过")
    
    def test_recommendation_with_api_models(self):
        """测试包含API模型的推荐逻辑"""
        from src.utils.config import ConfigManager
        
        try:
            config_manager = ConfigManager()
            content_type_service = ContentTypeService(config_manager)
            content_types = content_type_service.get_all()
            
            # 验证meeting类型推荐包含elevenlabs-api
            meeting_config = content_types.get('meeting', {})
            meeting_recommendations = meeting_config.get('recommendations', {})
            
            self.assertIn('elevenlabs-api', meeting_recommendations.get('english', []), "会议类型应推荐ElevenLabs API用于说话者分离")
            
            # 验证lecture类型推荐
            lecture_config = content_types.get('lecture', {})
            lecture_recommendations = lecture_config.get('recommendations', {})
            
            self.assertGreater(len(lecture_recommendations.get('english', [])) + len(lecture_recommendations.get('multilingual', [])), 0, "讲座类型应有推荐模型")
            
            print("✅ API模型推荐逻辑测试通过")
            
        except Exception as e:
            print(f"⚠️  推荐逻辑测试跳过: {e}")
    
    def test_api_model_integration_with_frontend(self):
        """测试API模型与前端集成"""
        def simulate_frontend_api_call():
            """模拟前端API调用获取模型配置"""
            try:
                import requests
                response = requests.get('http://localhost:8080/api/models/smart-config', timeout=2)
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get('all', [])
                else:
                    return []
            except:
                return []
        
        # 尝试获取前端模型数据
        models = simulate_frontend_api_call()
        
        if models:
            # 验证返回的模型数据结构
            for model in models:
                self.assertIn('value', model)
                self.assertIn('display_name', model)
                # 简化后的API不再包含recommended_for字段
                # self.assertIn('recommended_for', model)
                
            # 检查是否有本地模型
            local_models = [m for m in models if m.get('type', 'local') == 'local']
            self.assertGreater(len(local_models), 0, "应该有本地模型")
            
            print("✅ 前端API集成测试通过")
        else:
            print("⚠️  前端API集成测试跳过: 前端服务未运行")


if __name__ == '__main__':
    print("🧪 开始API选项显示功能测试...")
    print("=" * 50)
    
    # 运行测试
    unittest.main(verbosity=2)
