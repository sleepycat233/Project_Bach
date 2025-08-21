#!/usr/bin/env python3.11
"""
人名匿名化模块单元测试
"""

import unittest
import tempfile
import shutil
import os
from unittest.mock import patch, MagicMock

# 添加src目录到Python路径
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from core.anonymization import (
    NameAnonymizer, VirtualNameGenerator, NameMappingManager,
    is_chinese_text, extract_person_names
)


class TestNameAnonymizer(unittest.TestCase):
    """测试人名匿名化器"""
    
    def setUp(self):
        """每个测试前的准备工作"""
        self.spacy_config = {'model': 'zh_core_web_sm'}
        
        # Mock spaCy模型以避免实际加载
        self.mock_nlp_zh = MagicMock()
        self.mock_nlp_en = MagicMock()
        
        with patch('spacy.load') as mock_spacy_load:
            def side_effect(model_name):
                if 'zh_' in model_name:
                    return self.mock_nlp_zh
                else:
                    return self.mock_nlp_en
            
            mock_spacy_load.side_effect = side_effect
            
            with patch('logging.getLogger'):
                self.anonymizer = NameAnonymizer(self.spacy_config)
    
    def test_setup_spacy_models_success(self):
        """测试spaCy模型设置成功"""
        # 已在setUp中测试，验证模型被正确赋值
        self.assertEqual(self.anonymizer.nlp_zh, self.mock_nlp_zh)
        self.assertEqual(self.anonymizer.nlp_en, self.mock_nlp_en)
    
    @patch('spacy.load')
    @patch('logging.getLogger')
    def test_setup_spacy_models_failure(self, mock_logger, mock_spacy_load):
        """测试spaCy模型加载失败"""
        mock_spacy_load.side_effect = OSError("Model not found")
        
        with self.assertRaises(OSError):
            NameAnonymizer(self.spacy_config)
    
    def test_select_nlp_model_auto_chinese(self):
        """测试自动选择中文模型"""
        chinese_text = "这是一段包含很多中文字符的文本，用于测试语言检测功能。"
        model = self.anonymizer._select_nlp_model(chinese_text, 'auto')
        self.assertEqual(model, self.mock_nlp_zh)
    
    def test_select_nlp_model_auto_english(self):
        """测试自动选择英文模型"""
        english_text = "This is an English text used for testing language detection."
        model = self.anonymizer._select_nlp_model(english_text, 'auto')
        self.assertEqual(model, self.mock_nlp_en)
    
    def test_select_nlp_model_explicit_language(self):
        """测试明确指定语言"""
        text = "Mixed text 混合文本"
        
        zh_model = self.anonymizer._select_nlp_model(text, 'zh')
        self.assertEqual(zh_model, self.mock_nlp_zh)
        
        en_model = self.anonymizer._select_nlp_model(text, 'en')
        self.assertEqual(en_model, self.mock_nlp_en)
    
    def test_is_invalid_name(self):
        """测试无效人名过滤"""
        invalid_names = ['张三先生', '李四女士', '王教授', '赵博士', '总监', '经理']
        valid_names = ['张三', '李四', '王五', 'John', 'Mary']
        
        for name in invalid_names:
            self.assertTrue(self.anonymizer._is_invalid_name(name))
        
        for name in valid_names:
            self.assertFalse(self.anonymizer._is_invalid_name(name))
    
    def test_anonymize_names_with_persons(self):
        """测试包含人名的文本匿名化"""
        text = "张三和李四在会议中讨论了项目进展。"
        
        # Mock spaCy实体识别
        mock_ent1 = MagicMock()
        mock_ent1.text = "张三"
        mock_ent1.label_ = "PERSON"
        
        mock_ent2 = MagicMock()
        mock_ent2.text = "李四"
        mock_ent2.label_ = "PERSON"
        
        mock_doc = MagicMock()
        mock_doc.ents = [mock_ent1, mock_ent2]
        self.mock_nlp_zh.return_value = mock_doc
        
        # Mock虚拟人名生成
        with patch.object(self.anonymizer.name_generator, 'generate_name') as mock_generate:
            mock_generate.side_effect = ['赵云', '钱伟']
            
            result_text, mapping = self.anonymizer.anonymize_names(text)
            
            self.assertIn('赵云', result_text)
            self.assertIn('钱伟', result_text)
            self.assertNotIn('张三', result_text)
            self.assertNotIn('李四', result_text)
            
            self.assertEqual(mapping['张三'], '赵云')
            self.assertEqual(mapping['李四'], '钱伟')
    
    def test_anonymize_names_no_persons(self):
        """测试不包含人名的文本"""
        text = "这是一个没有人名的测试文本。"
        
        # Mock空的实体列表
        mock_doc = MagicMock()
        mock_doc.ents = []
        self.mock_nlp_zh.return_value = mock_doc
        
        result_text, mapping = self.anonymizer.anonymize_names(text)
        
        self.assertEqual(result_text, text)
        self.assertEqual(mapping, {})
    
    def test_get_name_mapping(self):
        """测试获取人名映射"""
        self.anonymizer.name_mapping = {'张三': '赵云', '李四': '钱伟'}
        mapping = self.anonymizer.get_name_mapping()
        
        self.assertEqual(mapping, {'张三': '赵云', '李四': '钱伟'})
        # 验证返回的是副本，不是原始字典
        mapping['新增'] = '测试'
        self.assertNotIn('新增', self.anonymizer.name_mapping)
    
    def test_clear_name_mapping(self):
        """测试清除人名映射"""
        self.anonymizer.name_mapping = {'张三': '赵云'}
        self.anonymizer.name_generator.used_names = {'赵云'}
        
        with patch('logging.getLogger'):
            self.anonymizer.clear_name_mapping()
        
        self.assertEqual(self.anonymizer.name_mapping, {})
        self.assertEqual(self.anonymizer.name_generator.used_names, set())


class TestVirtualNameGenerator(unittest.TestCase):
    """测试虚拟人名生成器"""
    
    def setUp(self):
        """每个测试前的准备工作"""
        with patch('faker.Faker'):
            self.generator = VirtualNameGenerator()
            
            # Mock Faker实例
            self.generator.fake_zh = MagicMock()
            self.generator.fake_en = MagicMock()
    
    def test_is_chinese_name(self):
        """测试中文人名判断"""
        chinese_names = ['张三', '李四', '王小明', '赵丽华']
        english_names = ['John', 'Mary', 'Smith', 'Johnson']
        
        for name in chinese_names:
            self.assertTrue(self.generator._is_chinese_name(name))
        
        for name in english_names:
            self.assertFalse(self.generator._is_chinese_name(name))
    
    def test_generate_chinese_name(self):
        """测试生成中文虚拟人名"""
        self.generator.fake_zh.name.return_value = "王小明"
        
        result = self.generator._generate_chinese_name()
        
        self.assertEqual(result, "王小明")
        self.assertIn("王小明", self.generator.used_names)
    
    def test_generate_english_name(self):
        """测试生成英文虚拟人名"""
        self.generator.fake_en.first_name.return_value = "John"
        
        result = self.generator._generate_english_name()
        
        self.assertEqual(result, "John")
        self.assertIn("John", self.generator.used_names)
    
    def test_generate_name_chinese_context(self):
        """测试中文语境下的人名生成"""
        self.generator.fake_zh.name.return_value = "赵云"
        
        result = self.generator.generate_name("张三", "这是中文语境", "zh")
        
        self.assertEqual(result, "赵云")
    
    def test_generate_name_english_context(self):
        """测试英文语境下的人名生成"""
        self.generator.fake_en.first_name.return_value = "Mike"
        
        result = self.generator.generate_name("John", "This is English context", "en")
        
        self.assertEqual(result, "Mike")
    
    def test_generate_name_fallback_chinese(self):
        """测试中文人名生成回退方案"""
        # 模拟所有生成的名字都重复
        self.generator.fake_zh.name.return_value = "重复名字"
        self.generator.used_names = {"重复名字"}
        
        result = self.generator._generate_chinese_name()
        
        self.assertTrue(result.startswith("李明"))
        self.assertIn(result, self.generator.used_names)
    
    def test_clear_used_names(self):
        """测试清除已使用的人名"""
        self.generator.used_names = {"张三", "李四", "John", "Mary"}
        self.generator.clear_used_names()
        
        self.assertEqual(self.generator.used_names, set())


class TestNameMappingManager(unittest.TestCase):
    """测试人名映射管理器"""
    
    def setUp(self):
        """每个测试前的准备工作"""
        self.manager = NameMappingManager()
    
    def test_store_and_get_mapping(self):
        """测试存储和获取映射"""
        mapping = {'张三': '赵云', '李四': '钱伟'}
        self.manager.store_mapping('doc1', mapping)
        
        retrieved = self.manager.get_mapping('doc1')
        self.assertEqual(retrieved, mapping)
    
    def test_get_nonexistent_mapping(self):
        """测试获取不存在的映射"""
        result = self.manager.get_mapping('nonexistent')
        self.assertEqual(result, {})
    
    def test_get_all_mappings(self):
        """测试获取所有映射"""
        mapping1 = {'张三': '赵云'}
        mapping2 = {'李四': '钱伟'}
        
        self.manager.store_mapping('doc1', mapping1)
        self.manager.store_mapping('doc2', mapping2)
        
        all_mappings = self.manager.get_all_mappings()
        
        self.assertEqual(all_mappings['doc1'], mapping1)
        self.assertEqual(all_mappings['doc2'], mapping2)
    
    def test_reverse_mapping(self):
        """测试反向映射"""
        mapping = {'张三': '赵云', '李四': '钱伟'}
        self.manager.store_mapping('doc1', mapping)
        
        anonymized_text = "赵云和钱伟在开会。"
        original_text = self.manager.reverse_mapping('doc1', anonymized_text)
        
        self.assertEqual(original_text, "张三和李四在开会。")
    
    def test_clear_mapping(self):
        """测试清除指定文档映射"""
        self.manager.store_mapping('doc1', {'张三': '赵云'})
        self.manager.store_mapping('doc2', {'李四': '钱伟'})
        
        self.manager.clear_mapping('doc1')
        
        self.assertEqual(self.manager.get_mapping('doc1'), {})
        self.assertNotEqual(self.manager.get_mapping('doc2'), {})
    
    def test_clear_all_mappings(self):
        """测试清除所有映射"""
        self.manager.store_mapping('doc1', {'张三': '赵云'})
        self.manager.store_mapping('doc2', {'李四': '钱伟'})
        
        self.manager.clear_all_mappings()
        
        self.assertEqual(self.manager.get_all_mappings(), {})


class TestUtilityFunctions(unittest.TestCase):
    """测试工具函数"""
    
    def test_is_chinese_text(self):
        """测试中文文本检测"""
        chinese_texts = [
            "这是中文文本",
            "Chinese English 中文混合 text",
            "技术分享：人工智能在软件开发中的应用"
        ]
        
        english_texts = [
            "This is English text",
            "Pure English content here",
            "Meeting notes and discussion"
        ]
        
        for text in chinese_texts:
            self.assertTrue(is_chinese_text(text), f"Should detect Chinese: {text}")
        
        for text in english_texts:
            self.assertFalse(is_chinese_text(text), f"Should not detect Chinese: {text}")
    
    @patch('core.anonymization.NameAnonymizer')
    def test_extract_person_names(self, mock_anonymizer_class):
        """测试提取人名功能"""
        # Mock NameAnonymizer
        mock_anonymizer = MagicMock()
        mock_nlp = MagicMock()
        
        # Mock实体
        mock_ent1 = MagicMock()
        mock_ent1.text.strip.return_value = "张三"
        mock_ent1.label_ = "PERSON"
        
        mock_ent2 = MagicMock()
        mock_ent2.text.strip.return_value = "李四"
        mock_ent2.label_ = "PERSON"
        
        mock_doc = MagicMock()
        mock_doc.ents = [mock_ent1, mock_ent2]
        mock_nlp.return_value = mock_doc
        
        mock_anonymizer._select_nlp_model.return_value = mock_nlp
        mock_anonymizer._is_invalid_name.return_value = False
        mock_anonymizer_class.return_value = mock_anonymizer
        
        result = extract_person_names("张三和李四在开会", "auto")
        
        self.assertIn("张三", result)
        self.assertIn("李四", result)


if __name__ == '__main__':
    unittest.main()