#!/usr/bin/env python3
"""
Phase 6 内容分类器

自动识别和分类多媒体内容类型：lecture、youtube、rss、podcast
基于文件名、URL模式和内容特征进行智能分类
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlparse
from pathlib import Path

from src.utils.config import ConfigManager


class ContentClassifier:
    """内容分类器
    
    支持多种分类策略：
    1. 文件名模式匹配
    2. URL模式识别
    3. 内容特征分析
    4. 置信度计算
    5. 自动标签提取
    """
    
    def __init__(self, config_manager: ConfigManager):
        """初始化内容分类器
        
        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger('project_bach.content_classifier')
        
        # 加载配置
        self.content_types_config = config_manager.get_content_types_config()
        self.classification_config = config_manager.get_classification_config()
        self.content_filter_config = config_manager.get_content_filter_config()
        
        # 设置默认值
        self.confidence_threshold = self.classification_config.get('confidence_threshold', 0.7)
        self.default_category = self.classification_config.get('default_category', 'lecture')
        self.max_content_length = self.classification_config.get('max_content_length', 5000)
        
        # 权重配置
        weights = self.classification_config.get('scoring_weights', {})
        self.url_weight = weights.get('url_match', 0.6)
        self.filename_weight = weights.get('filename_match', 0.3)
        self.content_weight = weights.get('content_match', 0.1)
        
        # 标签提取配置
        tag_config = self.classification_config.get('tag_extraction', {})
        self.max_tags = tag_config.get('max_tags', 10)
        self.min_tag_length = tag_config.get('min_tag_length', 2)
        self.exclude_common = tag_config.get('exclude_common_words', True)
        
        # 常见词汇列表（用于标签过滤）- 增强中英双语支持
        self.common_words = {
            # 英文常见词（以英文为主的内容）
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
            'will', 'would', 'can', 'could', 'should', 'may', 'might', 'must', 'shall',
            'do', 'does', 'did', 'get', 'got', 'make', 'made', 'take', 'took', 'come', 'came',
            'go', 'went', 'see', 'saw', 'know', 'knew', 'think', 'thought', 'say', 'said',
            'like', 'want', 'need', 'work', 'time', 'way', 'day', 'man', 'thing', 'life',
            'world', 'hand', 'part', 'place', 'case', 'fact', 'right', 'good', 'new', 'first',
            'last', 'long', 'great', 'little', 'own', 'other', 'old', 'same', 'big', 'high',
            'different', 'small', 'large', 'next', 'early', 'young', 'important', 'few', 'public',
            # 中文常见词
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
            '会', '说', '他', '她', '它', '我们', '你们', '他们', '这', '那', '这个', '那个',
            '可以', '能够', '应该', '需要', '想要', '觉得', '认为', '知道', '看到', '听到',
            '非常', '很', '比较', '更', '最', '也', '还', '都', '只', '已经', '正在', '将要'
        }
        
        self.logger.info("ContentClassifier初始化完成")
    
    def classify_by_filename(self, filename: str) -> str:
        """基于文件名进行分类
        
        Args:
            filename: 文件名
            
        Returns:
            分类结果
        """
        if not filename:
            return self.default_category
        
        filename_lower = filename.lower()
        
        # 检查每种内容类型的文件名模式
        for content_type, type_config in self.content_types_config.items():
            patterns = type_config.get('auto_detect_patterns', {}).get('filename', [])
            
            for pattern in patterns:
                if pattern.lower() in filename_lower:
                    self.logger.debug(f"文件名匹配: {filename} -> {content_type} (模式: {pattern})")
                    return content_type
        
        return self.default_category
    
    def classify_by_url(self, url: str) -> str:
        """基于URL进行分类
        
        Args:
            url: URL字符串
            
        Returns:
            分类结果
        """
        if not url:
            return self.default_category
        
        url_lower = url.lower()
        
        # 检查每种内容类型的URL模式
        for content_type, type_config in self.content_types_config.items():
            patterns = type_config.get('auto_detect_patterns', {}).get('url', [])
            
            for pattern in patterns:
                if pattern.lower() in url_lower:
                    self.logger.debug(f"URL匹配: {url} -> {content_type} (模式: {pattern})")
                    return content_type
        
        return self.default_category
    
    def classify_by_content(self, content: str) -> str:
        """基于内容特征进行分类
        
        Args:
            content: 文本内容
            
        Returns:
            分类结果
        """
        if not content:
            return self.default_category
        
        # 限制内容长度以提高性能
        if len(content) > self.max_content_length:
            content = content[:self.max_content_length]
        
        content_lower = content.lower()
        best_match = self.default_category
        best_score = 0.0
        
        # 检查每种内容类型的内容模式
        for content_type, type_config in self.content_types_config.items():
            patterns = type_config.get('auto_detect_patterns', {}).get('content', [])
            
            # 计算匹配分数
            score = 0.0
            matches = 0
            
            for pattern in patterns:
                if pattern.lower() in content_lower:
                    matches += 1
                    # 根据模式长度给予不同权重
                    weight = len(pattern) / 10.0  # 较长的模式权重更高
                    score += weight
            
            # 归一化分数
            if patterns:
                score = score / len(patterns)
            
            if score > best_score:
                best_score = score
                best_match = content_type
        
        self.logger.debug(f"内容分析: {content[:50]}... -> {best_match} (分数: {best_score:.3f})")
        return best_match
    
    def extract_tags(self, content: str) -> List[str]:
        """从内容中提取标签
        
        Args:
            content: 文本内容
            
        Returns:
            标签列表
        """
        if not content:
            return []
        
        # 限制内容长度
        if len(content) > self.max_content_length:
            content = content[:self.max_content_length]
        
        # 简单的标签提取策略
        tags = set()
        
        # 1. 提取技术术语（大写字母开头的词）
        tech_terms = re.findall(r'\b[A-Z][a-z]+\b', content)
        for term in tech_terms:
            if len(term) >= self.min_tag_length and term.lower() not in self.common_words:
                tags.add(term.lower())
        
        # 2. 提取全大写的缩写
        abbreviations = re.findall(r'\b[A-Z]{2,}\b', content)
        for abbr in abbreviations:
            if len(abbr) >= self.min_tag_length:
                tags.add(abbr.lower())
        
        # 3. 提取特殊词汇（技术相关）- 增强中英双语支持
        tech_patterns = [
            # 核心技术词汇（英文）
            r'\b(machine|deep|neural|artificial|quantum|computer|software|hardware|programming|algorithm|data|analysis|research|technology|science|engineering|mathematics|physics|chemistry|biology)\b',
            # 编程和开发相关（英文）
            r'\b(python|javascript|java|cpp|golang|rust|swift|kotlin|typescript|react|vue|angular|node|docker|kubernetes|git|github|api|database|framework|library|cloud|aws|azure|gcp)\b',
            # 学习和教育相关（英文）
            r'\b(tutorial|guide|course|lecture|education|learning|teaching|training|workshop|seminar|presentation|demonstration|walkthrough|howto|documentation|example|practice)\b',
            # AI和机器学习（英文）
            r'\b(ai|ml|nlp|cv|llm|gpt|transformer|bert|cnn|rnn|lstm|gan|reinforcement|supervised|unsupervised|classification|regression|clustering|optimization)\b',
            # 中文技术词汇
            r'\b(机器学习|深度学习|人工智能|神经网络|量子|计算机|软件|硬件|编程|算法|数据|分析|研究|技术|科学|工程|数学|物理|化学|生物)\b',
            # 中文教育词汇
            r'\b(教育|学习|课程|讲座|教程|指南|培训|研讨|演示|实践|文档|示例|练习|知识|理论|概念|原理)\b',
            # 专业术语（英文）
            r'\b(development|architecture|design|pattern|methodology|framework|infrastructure|system|platform|solution|implementation|deployment|optimization|performance|security|scalability)\b'
        ]
        
        for pattern in tech_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if len(match) >= self.min_tag_length and match.lower() not in self.common_words:
                    tags.add(match.lower())
        
        # 转换为列表并限制数量
        result_tags = list(tags)[:self.max_tags]
        
        self.logger.debug(f"提取标签: {result_tags}")
        return result_tags
    
    def get_confidence_score(self, content: str, predicted_type: str) -> float:
        """计算分类置信度
        
        Args:
            content: 文本内容
            predicted_type: 预测的类型
            
        Returns:
            置信度分数 (0.0 - 1.0)
        """
        if not content or predicted_type not in self.content_types_config:
            return 0.0
        
        # 限制内容长度
        if len(content) > self.max_content_length:
            content = content[:self.max_content_length]
        
        content_lower = content.lower()
        type_config = self.content_types_config[predicted_type]
        
        # 计算内容匹配度
        patterns = type_config.get('auto_detect_patterns', {}).get('content', [])
        if not patterns:
            return 0.5  # 如果没有模式，返回中等置信度
        
        matches = 0
        total_patterns = len(patterns)
        
        for pattern in patterns:
            if pattern.lower() in content_lower:
                matches += 1
        
        # 基础置信度 (提高权重)
        base_confidence = matches / total_patterns
        
        # 内容长度因子（更长的内容置信度更高）
        length_factor = min(len(content) / 100, 1.0)  # 100字符以上开始有加成
        
        # 关键词密度因子
        keyword_density = self._calculate_keyword_density(content_lower, patterns)
        
        # 综合置信度 (调整权重以提高分数)
        confidence = (base_confidence * 0.7 + length_factor * 0.15 + keyword_density * 0.15)
        
        # 如果有任何匹配，给予基础分数保证
        if matches > 0:
            confidence = max(confidence, 0.3)  # 最低保证分数
        
        # 如果有多个匹配，给予额外加成
        if matches > 1:
            confidence = min(confidence * 1.3, 1.0)
        
        # 为高匹配度内容提供更高的基础分数
        if base_confidence > 0.5:
            confidence = max(confidence, 0.8)
        
        # 确保在合理范围内
        confidence = max(0.0, min(1.0, confidence))
        
        self.logger.debug(f"置信度计算: {predicted_type} = {confidence:.3f} (匹配: {matches}/{total_patterns})")
        return confidence
    
    def _calculate_keyword_density(self, content: str, patterns: List[str]) -> float:
        """计算关键词密度
        
        Args:
            content: 文本内容
            patterns: 模式列表
            
        Returns:
            关键词密度分数
        """
        if not content or not patterns:
            return 0.0
        
        words = content.split()
        total_words = len(words)
        
        if total_words == 0:
            return 0.0
        
        keyword_count = 0
        for pattern in patterns:
            keyword_count += content.count(pattern.lower())
        
        density = keyword_count / total_words
        return min(density * 10, 1.0)  # 归一化到0-1范围
    
    def classify_content(self, 
                        filename: Optional[str] = None,
                        content: Optional[str] = None,
                        source_url: Optional[str] = None) -> Dict[str, Any]:
        """综合分类内容
        
        Args:
            filename: 文件名
            content: 文本内容
            source_url: 来源URL
            
        Returns:
            分类结果字典
        """
        # 收集各种分类结果
        classifications = {}
        
        # URL分类（优先级最高）
        if source_url:
            url_type = self.classify_by_url(source_url)
            classifications['url'] = url_type
        
        # 文件名分类
        if filename:
            filename_type = self.classify_by_filename(filename)
            classifications['filename'] = filename_type
        
        # 内容分类
        if content:
            content_type = self.classify_by_content(content)
            classifications['content'] = content_type
        
        # 如果没有任何输入，返回默认分类
        if not classifications:
            return {
                'content_type': self.default_category,
                'confidence': 0.0,
                'auto_detected': False,
                'tags': [],
                'metadata': self._get_type_metadata(self.default_category),
                'classification_details': {}
            }
        
        # 计算加权分数
        type_scores = {}
        
        for method, predicted_type in classifications.items():
            if predicted_type not in type_scores:
                type_scores[predicted_type] = 0.0
            
            # 根据方法分配权重
            if method == 'url':
                type_scores[predicted_type] += self.url_weight
            elif method == 'filename':
                type_scores[predicted_type] += self.filename_weight
            elif method == 'content':
                type_scores[predicted_type] += self.content_weight
        
        # 选择得分最高的类型
        final_type = max(type_scores.items(), key=lambda x: x[1])[0]
        final_score = type_scores[final_type]
        
        # 计算置信度
        confidence = self.get_confidence_score(content or '', final_type)
        
        # 如果置信度太低且没有强指示（如URL匹配），使用默认分类
        if confidence < self.confidence_threshold and 'url' not in classifications:
            # 但是如果分类结果本身就是默认分类，保持原置信度
            if final_type != self.default_category:
                final_type = self.default_category
                confidence = 0.5
        
        # 提取标签
        tags = self.extract_tags(content or '')
        
        # 添加默认标签
        default_tags = self.content_types_config.get(final_type, {}).get('default_tags', [])
        tags.extend(default_tags)
        tags = list(set(tags))  # 去重
        
        result = {
            'content_type': final_type,
            'confidence': confidence,
            'auto_detected': True,
            'tags': tags,
            'metadata': self._get_type_metadata(final_type),
            'classification_details': {
                'method_results': classifications,
                'type_scores': type_scores,
                'final_score': final_score
            }
        }
        
        self.logger.info(f"内容分类完成: {final_type} (置信度: {confidence:.3f})")
        return result
    
    def _get_type_metadata(self, content_type: str) -> Dict[str, Any]:
        """获取内容类型的元数据
        
        Args:
            content_type: 内容类型
            
        Returns:
            元数据字典
        """
        if content_type not in self.content_types_config:
            content_type = self.default_category
        
        type_config = self.content_types_config[content_type]
        
        return {
            'icon': type_config.get('icon', '📄'),
            'display_name': type_config.get('display_name', content_type.title()),
            'description': type_config.get('description', ''),
            'supported_formats': type_config.get('supported_formats', []),
            'default_tags': type_config.get('default_tags', [])
        }
    
    def validate_content_type(self, content_type: str) -> bool:
        """验证内容类型是否有效
        
        Args:
            content_type: 内容类型
            
        Returns:
            是否有效
        """
        return content_type in self.content_types_config
    
    def get_supported_types(self) -> List[str]:
        """获取支持的内容类型列表
        
        Returns:
            内容类型列表
        """
        return list(self.content_types_config.keys())
    
    def get_type_info(self, content_type: str) -> Optional[Dict[str, Any]]:
        """获取特定内容类型的详细信息
        
        Args:
            content_type: 内容类型
            
        Returns:
            类型信息字典
        """
        if content_type not in self.content_types_config:
            return None
        
        type_config = self.content_types_config[content_type].copy()
        type_config['metadata'] = self._get_type_metadata(content_type)
        
        return type_config