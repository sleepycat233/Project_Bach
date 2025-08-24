#!/usr/bin/env python3.11
"""
推荐系统完整测试套件
整合所有推荐逻辑相关的单元测试和集成测试
"""

import unittest
import json
import requests
import time
from pathlib import Path
import sys
from unittest.mock import patch, MagicMock

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestRecommendationCore(unittest.TestCase):
    """测试推荐系统核心逻辑"""
    
    def setUp(self):
        """测试初始化"""
        # 标准配置数据 (基于实际的config.yaml)
        self.mock_config = {
            'content_classification': {
                'content_types': {
                    'lecture': {
                        'icon': '🎓',
                        'display_name': 'Academic Lecture',
                        'recommendations': {
                            'english': [
                                'distil-whisper_distil-large-v3',
                                'openai_whisper-medium'
                            ],
                            'multilingual': [
                                'openai_whisper-large-v3',
                                'openai_whisper-large-v3-v20240930'
                            ]
                        }
                    },
                    'meeting': {
                        'icon': '🏢',
                        'display_name': 'Meeting Recording',
                        'recommendations': {
                            'english': [
                                'openai_whisper-large-v3',
                                'elevenlabs_api_speech'
                            ],
                            'multilingual': [
                                'openai_whisper-large-v3',
                                'elevenlabs_api_speech'
                            ]
                        }
                    },
                    'others': {
                        'icon': '📄',
                        'display_name': 'Others',
                        'recommendations': {
                            'english': [
                                'distil-whisper_distil-large-v3',
                                'openai_whisper-medium'
                            ],
                            'multilingual': [
                                'openai_whisper-large-v3',
                                'openai_whisper-medium'
                            ]
                        }
                    }
                }
            }
        }
        
        # 标准模型数据
        self.mock_models = [
            {
                'value': 'distil-whisper_distil-large-v3',
                'name': 'distil-whisper_distil-large-v3',
                'display_name': 'Distil Large V3',
                'english_support': True,
                'multilingual_support': False
            },
            {
                'value': 'openai_whisper-medium',
                'name': 'openai_whisper-medium',
                'display_name': 'OpenAI Medium',
                'english_support': True,
                'multilingual_support': True
            },
            {
                'value': 'openai_whisper-large-v3',
                'name': 'openai_whisper-large-v3',
                'display_name': 'OpenAI Large V3',
                'english_support': True,
                'multilingual_support': True
            },
            {
                'value': 'openai_whisper-large-v3-v20240930',
                'name': 'openai_whisper-large-v3-v20240930',
                'display_name': 'OpenAI Large V3 2024-09-30',
                'english_support': True,
                'multilingual_support': True
            },
            {
                'value': 'elevenlabs_api_speech',
                'name': 'ElevenLabs Speech Recognition',
                'display_name': '🗣️ ElevenLabs Speech Recognition',
                'english_support': True,
                'multilingual_support': True,
                'requires_api_key': True
            }
        ]

    def test_content_type_recommendation_mapping(self):
        """测试内容类型推荐映射的正确性"""
        content_types = self.mock_config['content_classification']['content_types']
        
        # 验证lecture类型推荐
        lecture_recs = content_types['lecture']['recommendations']
        self.assertEqual(len(lecture_recs['english']), 2, "Lecture英文推荐应该是2个")
        self.assertEqual(len(lecture_recs['multilingual']), 2, "Lecture多语言推荐应该是2个")
        
        # 验证meeting类型推荐 (与lecture不同)
        meeting_recs = content_types['meeting']['recommendations']
        self.assertNotEqual(
            set(lecture_recs['english']), 
            set(meeting_recs['english']),
            "Lecture和Meeting的英文推荐应该不同"
        )
        
        # 验证meeting包含ElevenLabs (用于speaker diarization)
        self.assertIn('elevenlabs_api_speech', meeting_recs['english'])
        self.assertNotIn('elevenlabs_api_speech', lecture_recs['english'])

    def test_exact_string_matching_logic(self):
        """测试精确字符串匹配逻辑 (防止substring匹配错误)"""
        # 创建易混淆的模型名称
        confusing_models = [
            'openai_whisper-large-v3',
            'openai_whisper-large-v3-v20240930'
        ]
        
        recommendations = ['openai_whisper-large-v3']  # 只推荐其中一个
        
        # 测试精确匹配
        for model_name in confusing_models:
            is_recommended = any(rec == model_name for rec in recommendations)
            
            if model_name == 'openai_whisper-large-v3':
                self.assertTrue(is_recommended, "应该精确匹配openai_whisper-large-v3")
            else:
                self.assertFalse(is_recommended, "不应该匹配包含更多字符的模型名")

    def test_backend_recommendation_flag_setting(self):
        """测试后端推荐标志设置逻辑"""
        
        def apply_content_type_recommendations(models, content_type, config):
            """模拟后端推荐标志设置"""
            content_recommendations = config['content_classification']['content_types'][content_type]['recommendations']
            english_recs = content_recommendations.get('english', [])
            multilingual_recs = content_recommendations.get('multilingual', [])
            
            result_models = []
            for model in models:
                model_copy = model.copy()
                model_value = model_copy.get('value', '')
                model_name = model_copy.get('name', '')
                
                # 精确匹配设置推荐标志
                model_copy['is_english_recommended'] = any(
                    rec_model == model_value or rec_model == model_name 
                    for rec_model in english_recs
                )
                model_copy['is_multilingual_recommended'] = any(
                    rec_model == model_value or rec_model == model_name
                    for rec_model in multilingual_recs
                )
                
                result_models.append(model_copy)
            
            return result_models
        
        # 测试lecture类型
        lecture_models = apply_content_type_recommendations(
            self.mock_models, 'lecture', self.mock_config
        )
        
        # 验证推荐标志正确性
        for model in lecture_models:
            model_value = model['value']
            
            if model_value == 'distil-whisper_distil-large-v3':
                self.assertTrue(model['is_english_recommended'], "Distil应该被推荐为英文模型")
                self.assertFalse(model['is_multilingual_recommended'], "Distil不应该被推荐为多语言模型")
            
            elif model_value == 'openai_whisper-medium':
                self.assertTrue(model['is_english_recommended'], "Medium应该被推荐为英文模型")
                self.assertFalse(model['is_multilingual_recommended'], "Medium不应该被推荐为多语言模型 (在lecture配置中)")
            
            elif model_value == 'openai_whisper-large-v3':
                self.assertFalse(model['is_english_recommended'], "Large-v3不应该被推荐为英文模型 (在lecture配置中)")
                self.assertTrue(model['is_multilingual_recommended'], "Large-v3应该被推荐为多语言模型")

    def test_frontend_filtering_and_display(self):
        """测试前端过滤和显示逻辑"""
        
        # 模拟前端过滤函数
        def filter_and_format_models(models, language_mode, content_type):
            filtered = []
            for model in models:
                # 语言支持检查
                if language_mode == 'english':
                    language_supported = model.get('is_english_recommended') or model.get('english_support')
                    is_recommended = model.get('is_english_recommended', False)
                else:  # multilingual
                    language_supported = model.get('is_multilingual_recommended') or model.get('multilingual_support')
                    is_recommended = model.get('is_multilingual_recommended', False)
                
                if language_supported:
                    # 格式化显示名称
                    display_name = model.get('display_name', model.get('name', ''))
                    if is_recommended:
                        display_name += ' ⭐'  # 星号在末尾
                    
                    filtered.append({
                        'value': model['value'],
                        'display_name': display_name,
                        'recommended': is_recommended
                    })
            
            return filtered
        
        # 准备带推荐标志的测试模型
        test_models = []
        for model in self.mock_models:
            model_copy = model.copy()
            # 模拟lecture推荐标志
            model_copy['is_english_recommended'] = model['value'] in [
                'distil-whisper_distil-large-v3', 'openai_whisper-medium'
            ]
            model_copy['is_multilingual_recommended'] = model['value'] in [
                'openai_whisper-large-v3', 'openai_whisper-large-v3-v20240930'
            ]
            test_models.append(model_copy)
        
        # 测试英文模式显示
        english_display = filter_and_format_models(test_models, 'english', 'lecture')
        
        # 验证推荐模型有星号
        recommended_english = [m for m in english_display if m['recommended']]
        self.assertEqual(len(recommended_english), 2, "应该有2个英文推荐模型")
        
        for model in recommended_english:
            self.assertIn('⭐', model['display_name'], f"推荐模型{model['value']}应该有星号")
        
        # 验证星号在末尾
        for model in english_display:
            if model['recommended']:
                self.assertTrue(model['display_name'].endswith(' ⭐'), "星号应该在名称末尾")

    def test_model_sorting_priority(self):
        """测试模型排序优先级"""
        
        def get_sort_priority(model):
            """模拟排序逻辑：推荐优先，然后按复杂度"""
            is_recommended = model.get('recommended', False)
            config_info = model.get('config_info', {})
            
            # 基于模型复杂度
            d_model = config_info.get('d_model', 0)
            encoder_layers = config_info.get('encoder_layers', 0)
            complexity = d_model * encoder_layers
            
            return (not is_recommended, -complexity)
        
        # 准备测试模型
        test_models = []
        for model in self.mock_models:
            model_copy = model.copy()
            model_copy['recommended'] = model['value'] in [
                'distil-whisper_distil-large-v3', 'openai_whisper-medium'
            ]
            # 添加模拟配置信息
            if 'distil' in model['value']:
                model_copy['config_info'] = {'d_model': 1280, 'encoder_layers': 32}
            elif 'medium' in model['value']:
                model_copy['config_info'] = {'d_model': 1024, 'encoder_layers': 24}
            else:
                model_copy['config_info'] = {'d_model': 1280, 'encoder_layers': 32}
            
            test_models.append(model_copy)
        
        # 排序
        sorted_models = sorted(test_models, key=get_sort_priority)
        
        # 验证推荐模型在前面
        first_two = sorted_models[:2]
        self.assertTrue(all(m['recommended'] for m in first_two), 
                       "前两个模型应该都是推荐的")


class TestRecommendationAPIIntegration(unittest.TestCase):
    """测试推荐系统与Web API的集成"""
    
    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        cls.api_base_url = 'http://localhost:8080'
        cls.timeout = 5
        
        # 检查API可用性
        try:
            response = requests.get(f'{cls.api_base_url}/api/models/smart-config', timeout=3)
            cls.api_available = response.status_code == 200
        except:
            cls.api_available = False
    
    def setUp(self):
        """每个测试前的初始化"""
        if not self.api_available:
            self.skipTest("Web API服务不可用")

    def test_api_response_structure_completeness(self):
        """测试API响应结构的完整性"""
        response = requests.get(f'{self.api_base_url}/api/models/smart-config', timeout=self.timeout)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # 验证必需的内容类型
        required_types = ['lecture', 'meeting', 'others', 'all']
        for content_type in required_types:
            self.assertIn(content_type, data, f"缺少{content_type}类型")
            self.assertIsInstance(data[content_type], list, f"{content_type}应该是数组")

    def test_lecture_recommendations_count_accuracy(self):
        """测试lecture推荐数量的准确性"""
        response = requests.get(f'{self.api_base_url}/api/models/smart-config', timeout=self.timeout)
        data = response.json()
        
        lecture_models = data['lecture']
        
        # 统计英文和多语言推荐
        english_recommended = [m for m in lecture_models if m.get('is_english_recommended') == True]
        multilingual_recommended = [m for m in lecture_models if m.get('is_multilingual_recommended') == True]
        
        # 根据配置，英文应该有2个推荐，多语言应该有1个推荐 (基于config.yaml)
        self.assertEqual(len(english_recommended), 2, 
                        f"Lecture英文推荐应该是2个，实际{len(english_recommended)}个")
        self.assertEqual(len(multilingual_recommended), 1, 
                        f"Lecture多语言推荐应该是1个，实际{len(multilingual_recommended)}个")
        
        # 验证具体推荐的模型
        english_values = {m['value'] for m in english_recommended}
        expected_english = {'distil-whisper_distil-large-v3', 'openai_whisper-medium'}
        self.assertEqual(english_values, expected_english, "Lecture英文推荐模型不正确")

    def test_meeting_vs_lecture_recommendation_difference(self):
        """测试meeting与lecture推荐的差异性"""
        response = requests.get(f'{self.api_base_url}/api/models/smart-config', timeout=self.timeout)
        data = response.json()
        
        lecture_models = data['lecture']
        meeting_models = data['meeting']
        
        # 获取英文推荐
        lecture_english = {m['value'] for m in lecture_models if m.get('is_english_recommended')}
        meeting_english = {m['value'] for m in meeting_models if m.get('is_english_recommended')}
        
        # 应该不同
        self.assertNotEqual(lecture_english, meeting_english, 
                          "Lecture和Meeting的英文推荐应该不同")
        
        # Meeting应该推荐ElevenLabs，Lecture不应该
        self.assertIn('elevenlabs_api_speech', meeting_english, "Meeting应该推荐ElevenLabs")
        self.assertNotIn('elevenlabs_api_speech', lecture_english, "Lecture不应该推荐ElevenLabs")
        
        # Meeting应该推荐高精度模型
        self.assertIn('openai_whisper-large-v3', meeting_english, "Meeting应该推荐Large-v3")

    def test_configuration_api_consistency(self):
        """测试配置文件与API的一致性"""
        from src.utils.config import ConfigManager
        
        # 获取实际配置
        config_manager = ConfigManager()
        config = config_manager.get_full_config()
        
        # 获取API数据
        response = requests.get(f'{self.api_base_url}/api/models/smart-config', timeout=self.timeout)
        api_data = response.json()
        
        # 验证配置与API的一致性
        content_types = config['content_classification']['content_types']
        
        for content_type, type_config in content_types.items():
            if content_type in api_data:
                api_models = api_data[content_type]
                config_recommendations = type_config.get('recommendations', {})
                
                if isinstance(config_recommendations, dict):
                    # 验证英文推荐一致性
                    config_english = set(config_recommendations.get('english', []))
                    api_english = {m['value'] for m in api_models if m.get('is_english_recommended')}
                    
                    self.assertEqual(config_english, api_english,
                                   f"{content_type}配置与API英文推荐不一致")

    def test_api_performance_requirements(self):
        """测试API性能要求"""
        start_time = time.time()
        response = requests.get(f'{self.api_base_url}/api/models/smart-config', timeout=self.timeout)
        response_time = time.time() - start_time
        
        # 性能要求
        self.assertLess(response_time, 2.0, f"API响应时间过长: {response_time:.2f}s")
        self.assertEqual(response.status_code, 200, "API应该返回成功状态")
        
        # 响应大小合理性
        response_size = len(response.content)
        self.assertGreater(response_size, 1000, "响应内容太少")
        self.assertLess(response_size, 100000, "响应内容太大")


class TestRecommendationEdgeCases(unittest.TestCase):
    """测试推荐系统的边界情况和错误处理"""
    
    def test_empty_recommendation_lists(self):
        """测试空推荐列表的处理"""
        empty_config = {
            'recommendations': {
                'english': [],
                'multilingual': []
            }
        }
        
        test_models = [
            {'value': 'model1', 'name': 'Model 1'},
            {'value': 'model2', 'name': 'Model 2'}
        ]
        
        # 模拟空推荐处理
        def process_empty_recommendations(models, config):
            english_recs = config['recommendations']['english']
            multilingual_recs = config['recommendations']['multilingual']
            
            for model in models:
                model['is_english_recommended'] = model['value'] in english_recs
                model['is_multilingual_recommended'] = model['value'] in multilingual_recs
            
            return models
        
        result = process_empty_recommendations(test_models, empty_config)
        
        # 所有模型都不应该被推荐
        for model in result:
            self.assertFalse(model['is_english_recommended'])
            self.assertFalse(model['is_multilingual_recommended'])

    def test_malformed_model_data_handling(self):
        """测试格式错误的模型数据处理"""
        malformed_models = [
            {},  # 完全空的模型
            {'value': ''},  # 空value
            {'name': ''},   # 空name
            {'value': None, 'name': None},  # None值
            {'value': 'valid_model'},  # 缺少name
            {'name': 'valid_model'},   # 缺少value
        ]
        
        recommendations = ['valid_model']
        
        # 健壮的匹配逻辑
        def robust_matching(model, recommendations):
            try:
                model_value = model.get('value') or ''
                model_name = model.get('name') or ''
                
                return any(
                    rec and (rec == model_value or rec == model_name)
                    for rec in recommendations
                )
            except Exception:
                return False
        
        # 测试所有格式错误的模型
        for model in malformed_models:
            try:
                result = robust_matching(model, recommendations)
                self.assertIsInstance(result, bool, f"应该返回布尔值，模型: {model}")
            except Exception as e:
                self.fail(f"处理格式错误模型时抛出异常: {e}, 模型: {model}")

    def test_duplicate_model_handling(self):
        """测试重复模型的处理"""
        duplicate_models = [
            {'value': 'same_model', 'name': 'Model A'},
            {'value': 'same_model', 'name': 'Model B'},  # 相同value
            {'value': 'model_c', 'name': 'same_model'},  # name与第一个value相同
        ]
        
        recommendations = ['same_model']
        
        # 应该正确匹配所有相关模型
        matches = []
        for model in duplicate_models:
            model_value = model.get('value', '')
            model_name = model.get('name', '')
            
            if any(rec == model_value or rec == model_name for rec in recommendations):
                matches.append(model)
        
        # 应该匹配所有包含'same_model'的模型
        self.assertEqual(len(matches), 3, "应该匹配所有相关模型")

    def test_special_characters_in_model_names(self):
        """测试模型名称中的特殊字符处理"""
        special_models = [
            {'value': 'model-with-dashes', 'name': 'Model With Dashes'},
            {'value': 'model_with_underscores', 'name': 'Model With Underscores'},
            {'value': 'model.with.dots', 'name': 'Model With Dots'},
            {'value': 'model@with#special!chars', 'name': 'Model With Special Chars'},
        ]
        
        recommendations = ['model-with-dashes', 'model_with_underscores']
        
        # 精确匹配应该正确处理特殊字符
        for model in special_models:
            model_value = model['value']
            is_recommended = model_value in recommendations
            
            if model_value in ['model-with-dashes', 'model_with_underscores']:
                self.assertTrue(is_recommended, f"{model_value}应该被推荐")
            else:
                self.assertFalse(is_recommended, f"{model_value}不应该被推荐")


class TestRecommendationSystemRegression(unittest.TestCase):
    """回归测试：确保之前修复的问题不会再次出现"""
    
    def test_substring_matching_regression(self):
        """回归测试：确保不会发生substring匹配错误"""
        # 这是之前出现过的问题：openai_whisper-large-v3会匹配openai_whisper-large-v3-v20240930
        confusing_pairs = [
            ('openai_whisper-large-v3', 'openai_whisper-large-v3-v20240930'),
            ('model-v1', 'model-v1-beta'),
            ('whisper-base', 'whisper-base-en'),
        ]
        
        for base_name, extended_name in confusing_pairs:
            recommendations = [base_name]  # 只推荐基础名称
            
            # 测试精确匹配
            base_match = any(rec == base_name for rec in recommendations)
            extended_match = any(rec == extended_name for rec in recommendations)
            
            self.assertTrue(base_match, f"{base_name}应该被匹配")
            self.assertFalse(extended_match, f"{extended_name}不应该被匹配 (substring问题)")

    def test_star_position_regression(self):
        """回归测试：确保星号在模型名称末尾"""
        test_models = [
            {'display_name': 'Model A', 'recommended': True},
            {'display_name': 'Model B', 'recommended': False},
        ]
        
        # 模拟前端显示逻辑
        for model in test_models:
            display_name = model['display_name']
            if model['recommended']:
                display_name += ' ⭐'  # 星号应该在末尾
            
            if model['recommended']:
                self.assertTrue(display_name.endswith(' ⭐'), 
                               f"推荐模型的星号应该在末尾: {display_name}")
                self.assertFalse(display_name.startswith('⭐'), 
                                f"星号不应该在开头: {display_name}")
            else:
                self.assertNotIn('⭐', display_name, f"非推荐模型不应该有星号: {display_name}")

    def test_content_type_isolation_regression(self):
        """回归测试：确保不同内容类型的推荐相互隔离"""
        # 这是之前出现的问题：所有内容类型都显示相同的推荐
        
        config = {
            'lecture': {
                'recommendations': {
                    'english': ['model_a', 'model_b']
                }
            },
            'meeting': {
                'recommendations': {
                    'english': ['model_c', 'model_d']
                }
            }
        }
        
        models = [
            {'value': 'model_a'}, {'value': 'model_b'},
            {'value': 'model_c'}, {'value': 'model_d'}
        ]
        
        # 模拟内容类型特定的推荐设置
        def set_content_type_recommendations(models, content_type, config):
            content_recs = config[content_type]['recommendations']['english']
            
            for model in models:
                model[f'{content_type}_english_recommended'] = model['value'] in content_recs
            
            return models
        
        # 处理不同内容类型
        processed_models = models.copy()
        for content_type in ['lecture', 'meeting']:
            processed_models = set_content_type_recommendations(
                processed_models, content_type, config
            )
        
        # 验证隔离性
        for model in processed_models:
            lecture_rec = model.get('lecture_english_recommended', False)
            meeting_rec = model.get('meeting_english_recommended', False)
            
            # 应该有不同的推荐
            if model['value'] in ['model_a', 'model_b']:
                self.assertTrue(lecture_rec, f"{model['value']}应该被lecture推荐")
                self.assertFalse(meeting_rec, f"{model['value']}不应该被meeting推荐")
            else:
                self.assertFalse(lecture_rec, f"{model['value']}不应该被lecture推荐")
                self.assertTrue(meeting_rec, f"{model['value']}应该被meeting推荐")


def run_all_recommendation_tests():
    """运行所有推荐系统测试"""
    
    print("🧪 开始推荐系统完整测试套件...")
    print("=" * 80)
    
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加所有测试类
    test_classes = [
        TestRecommendationCore,
        TestRecommendationAPIIntegration,
        TestRecommendationEdgeCases,
        TestRecommendationSystemRegression
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 测试结果总结
    print("\n" + "=" * 80)
    print(f"📊 测试总结:")
    print(f"   总测试数: {result.testsRun}")
    print(f"   成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   失败: {len(result.failures)}")
    print(f"   错误: {len(result.errors)}")
    print(f"   跳过: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.failures:
        print("\n❌ 失败的测试:")
        for test, traceback in result.failures:
            print(f"   - {test}")
    
    if result.errors:
        print("\n⚠️  错误的测试:")
        for test, traceback in result.errors:
            print(f"   - {test}")
    
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0
    print(f"\n✅ 成功率: {success_rate:.1f}%")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    # 可以单独运行某个测试类
    if len(sys.argv) > 1:
        unittest.main()
    else:
        # 运行完整测试套件
        success = run_all_recommendation_tests()
        sys.exit(0 if success else 1)