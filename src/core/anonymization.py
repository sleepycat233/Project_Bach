#!/usr/bin/env python3.11
"""
人名匿名化模块
负责文本中人名的识别、匿名化处理和虚拟人名生成
"""

import spacy
import logging
from typing import Dict, Tuple, Set, Any
from faker import Faker


class NameAnonymizer:
    """人名匿名化服务"""
    
    def __init__(self, spacy_config: Dict[str, Any]):
        """初始化人名匿名化服务
        
        Args:
            spacy_config: spaCy配置字典
        """
        self.config = spacy_config
        self.logger = logging.getLogger('project_bach.anonymization')
        self.setup_spacy_models()
        
        # 初始化虚拟人名生成器
        self.name_generator = VirtualNameGenerator()
        
        # 全局人名映射（跨文档持久化）
        self.name_mapping: Dict[str, str] = {}
        
    def setup_spacy_models(self):
        """设置spaCy双语模型"""
        try:
            # 加载中文模型
            self.logger.info("加载spaCy中文模型: zh_core_web_sm")
            self.nlp_zh = spacy.load("zh_core_web_sm")
            
            # 加载英文模型
            self.logger.info("加载spaCy英文模型: en_core_web_sm")
            self.nlp_en = spacy.load("en_core_web_sm")
            
            # 默认使用中文模型（向后兼容）
            self.nlp = self.nlp_zh
            
            self.logger.info("spaCy双语模型加载成功")
        except OSError as e:
            self.logger.error(f"spaCy模型加载失败: {str(e)}")
            self.logger.error("请运行: python -m spacy download zh_core_web_sm")
            self.logger.error("请运行: python -m spacy download en_core_web_sm")
            raise
    
    def anonymize_names(self, text: str, language: str = 'auto') -> Tuple[str, Dict[str, str]]:
        """使用spaCy进行基于NLP的完全动态人名匿名化（支持双语）
        
        Args:
            text: 待匿名化的文本
            language: 指定语言 ('auto', 'zh', 'en')
            
        Returns:
            (匿名化后的文本, 本次处理的人名映射)
        """
        self.logger.info("开始基于NLP的动态人名匿名化处理")
        
        try:
            # 智能选择spaCy模型
            nlp_model = self._select_nlp_model(text, language)
            
            doc = nlp_model(text)
            result = text
            current_mapping = {}
            
            # 使用spaCy识别所有人名实体
            person_entities = [ent for ent in doc.ents if ent.label_ == "PERSON"]
            
            if not person_entities:
                self.logger.info("NLP检测：未发现人名实体")
                return result, current_mapping
            
            # 基于NLP检测结果进行动态处理
            for ent in person_entities:
                original_name = ent.text.strip()
                
                # 过滤无效检测结果
                if len(original_name) < 2 or self._is_invalid_name(original_name):
                    continue
                
                # 为每个新检测到的人名动态生成虚拟人名
                if original_name not in self.name_mapping:
                    # 基于检测到的语言生成虚拟人名
                    detected_lang = 'zh' if nlp_model == self.nlp_zh else 'en'
                    fake_name = self.name_generator.generate_name(
                        original_name, text, detected_lang
                    )
                    self.name_mapping[original_name] = fake_name
                    self.logger.debug(
                        f"NLP检测到新人名，动态映射: {original_name} -> {fake_name} "
                        f"(语言: {detected_lang})"
                    )
                
                current_mapping[original_name] = self.name_mapping[original_name]
                
                # 执行全文替换
                result = result.replace(original_name, self.name_mapping[original_name])
            
            self.logger.info(f"NLP动态匿名化完成，处理了 {len(current_mapping)} 个人名")
            return result, current_mapping
            
        except Exception as e:
            self.logger.error(f"NLP人名匿名化失败: {str(e)}")
            return text, {}
    
    def _select_nlp_model(self, text: str, language: str):
        """智能选择spaCy模型
        
        Args:
            text: 待处理文本
            language: 指定语言
            
        Returns:
            选择的spaCy模型
        """
        if language == 'auto':
            # 自动检测语言
            chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
            if chinese_chars > len(text) * 0.1:  # 如果10%以上是中文字符
                nlp_model = self.nlp_zh
                self.logger.debug("使用中文spaCy模型进行人名识别")
            else:
                nlp_model = self.nlp_en
                self.logger.debug("使用英文spaCy模型进行人名识别")
        elif language == 'zh':
            nlp_model = self.nlp_zh
            self.logger.debug("指定使用中文spaCy模型")
        elif language == 'en':
            nlp_model = self.nlp_en
            self.logger.debug("指定使用英文spaCy模型")
        else:
            nlp_model = self.nlp_zh  # 默认中文
            self.logger.debug("使用默认中文spaCy模型")
        
        return nlp_model
    
    def _is_invalid_name(self, name: str) -> bool:
        """过滤无效的人名检测结果
        
        Args:
            name: 检测到的人名
            
        Returns:
            是否无效
        """
        invalid_patterns = ['先生', '女士', '教授', '博士', '总监', '经理', '老师']
        return any(pattern in name for pattern in invalid_patterns)
    
    def get_name_mapping(self) -> Dict[str, str]:
        """获取完整的人名映射
        
        Returns:
            人名映射字典
        """
        return self.name_mapping.copy()
    
    def clear_name_mapping(self):
        """清除人名映射（用于测试或重置）"""
        self.name_mapping.clear()
        self.name_generator.clear_used_names()
        self.logger.info("人名映射已清除")


class VirtualNameGenerator:
    """虚拟人名生成器"""
    
    def __init__(self):
        """初始化虚拟人名生成器"""
        self.fake_zh = Faker('zh_CN')  # 中文虚拟数据生成器
        self.fake_en = Faker('en_US')  # 英文虚拟数据生成器
        self.used_names: Set[str] = set()  # 已使用的虚拟人名（避免重复）
        
    def generate_name(self, original_name: str, context_text: str, language: str = 'auto') -> str:
        """基于NLP检测结果动态生成虚拟人名（支持双语）
        
        Args:
            original_name: 原始人名
            context_text: 上下文文本
            language: 语言类型
            
        Returns:
            生成的虚拟人名
        """
        if language == 'zh' or (language == 'auto' and self._is_chinese_name(original_name)):
            return self._generate_chinese_name()
        else:
            return self._generate_english_name()
    
    def _is_chinese_name(self, name: str) -> bool:
        """基于NLP检测判断是否为中文人名
        
        Args:
            name: 人名
            
        Returns:
            是否为中文人名
        """
        return any('\u4e00' <= char <= '\u9fff' for char in name)
    
    def _generate_chinese_name(self) -> str:
        """使用Faker动态生成中文虚拟人名
        
        Returns:
            中文虚拟人名
        """
        max_attempts = 50
        for _ in range(max_attempts):
            virtual_name = self.fake_zh.name()
            if virtual_name not in self.used_names:
                self.used_names.add(virtual_name)
                return virtual_name
        
        # 如果重复太多，使用简单的序号方式
        fallback_name = f"李明{len(self.used_names) + 1}"
        self.used_names.add(fallback_name)
        return fallback_name
    
    def _generate_english_name(self) -> str:
        """使用Faker动态生成英文虚拟人名
        
        Returns:
            英文虚拟人名
        """
        max_attempts = 50
        for _ in range(max_attempts):
            virtual_name = self.fake_en.first_name()
            if virtual_name not in self.used_names:
                self.used_names.add(virtual_name)
                return virtual_name
        
        # 如果重复太多，使用简单的序号方式
        fallback_name = f"Alex{len(self.used_names) + 1}"
        self.used_names.add(fallback_name)
        return fallback_name
    
    def get_used_names(self) -> Set[str]:
        """获取已使用的虚拟人名
        
        Returns:
            已使用的人名集合
        """
        return self.used_names.copy()
    
    def clear_used_names(self):
        """清除已使用的人名记录"""
        self.used_names.clear()


class NameMappingManager:
    """人名映射管理器"""
    
    def __init__(self):
        """初始化人名映射管理器"""
        self.mappings: Dict[str, Dict[str, str]] = {}  # 按文档存储映射
        
    def store_mapping(self, document_id: str, mapping: Dict[str, str]):
        """存储文档的人名映射
        
        Args:
            document_id: 文档标识
            mapping: 人名映射字典
        """
        self.mappings[document_id] = mapping.copy()
    
    def get_mapping(self, document_id: str) -> Dict[str, str]:
        """获取文档的人名映射
        
        Args:
            document_id: 文档标识
            
        Returns:
            人名映射字典
        """
        return self.mappings.get(document_id, {})
    
    def get_all_mappings(self) -> Dict[str, Dict[str, str]]:
        """获取所有文档的人名映射
        
        Returns:
            所有映射字典
        """
        return self.mappings.copy()
    
    def reverse_mapping(self, document_id: str, anonymized_text: str) -> str:
        """反向映射：将匿名化文本还原为原始文本
        
        Args:
            document_id: 文档标识
            anonymized_text: 匿名化文本
            
        Returns:
            还原后的文本
        """
        mapping = self.get_mapping(document_id)
        result = anonymized_text
        
        # 反向替换
        for original, virtual in mapping.items():
            result = result.replace(virtual, original)
        
        return result
    
    def clear_mapping(self, document_id: str):
        """清除指定文档的映射
        
        Args:
            document_id: 文档标识
        """
        if document_id in self.mappings:
            del self.mappings[document_id]
    
    def clear_all_mappings(self):
        """清除所有映射"""
        self.mappings.clear()


# 工具函数
def is_chinese_text(text: str) -> bool:
    """检测文本是否主要为中文
    
    Args:
        text: 待检测文本
        
    Returns:
        是否为中文文本
    """
    chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
    return chinese_chars > len(text) * 0.1  # 如果10%以上是中文字符就认为包含中文


def extract_person_names(text: str, language: str = 'auto') -> list:
    """提取文本中的人名（不进行匿名化）
    
    Args:
        text: 待处理文本
        language: 指定语言
        
    Returns:
        人名列表
    """
    try:
        # 临时创建anonymizer来利用其spaCy模型
        anonymizer = NameAnonymizer({'model': 'zh_core_web_sm'})
        nlp_model = anonymizer._select_nlp_model(text, language)
        
        doc = nlp_model(text)
        person_entities = [ent.text.strip() for ent in doc.ents if ent.label_ == "PERSON"]
        
        # 过滤无效结果
        valid_names = []
        for name in person_entities:
            if len(name) >= 2 and not anonymizer._is_invalid_name(name):
                valid_names.append(name)
        
        return list(set(valid_names))  # 去重
        
    except Exception:
        return []