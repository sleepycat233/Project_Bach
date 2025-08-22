#!/usr/bin/env python3
"""
Phase 6 内容格式化器增强版 - 单元测试

测试ContentFormatter的多媒体内容类型支持功能
"""

import pytest
import tempfile
import shutil
import yaml
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.config import ConfigManager
from src.publishing.content_formatter import ContentFormatter


class TestContentFormatterEnhanced:
    """测试Phase 6增强的内容格式化器"""
    
    @pytest.fixture
    def temp_dir(self):
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def config_manager(self, temp_dir):
        """创建配置管理器"""
        config_data = {
            'content_classification': {
                'content_types': {
                    'lecture': {
                        'icon': '🎓',
                        'display_name': '讲座',
                        'description': '学术讲座、课程录音、教育内容'
                    },
                    'youtube': {
                        'icon': '📺', 
                        'display_name': '视频',
                        'description': 'YouTube视频内容、教学视频、技术分享'
                    },
                    'rss': {
                        'icon': '📰',
                        'display_name': '文章', 
                        'description': 'RSS订阅文章、技术博客、新闻资讯'
                    },
                    'podcast': {
                        'icon': '🎙️',
                        'display_name': '播客',
                        'description': '播客节目、访谈内容、讨论节目'
                    }
                }
            }
        }
        config_path = Path(temp_dir) / "config.yaml"
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, allow_unicode=True)
        return ConfigManager(str(config_path))
    
    @pytest.fixture
    def formatter(self, config_manager):
        """创建增强的内容格式化器实例"""
        config = {
            'site_title': 'Project Bach',
            'site_description': 'AI多媒体内容处理结果发布',
            'theme': 'enhanced'
        }
        return ContentFormatter(config, config_manager)
    
    def test_detect_content_type_from_classification_result(self, formatter):
        """测试从分类结果检测内容类型"""
        content_data = {
            'title': '测试视频',
            'classification_result': {
                'content_type': 'youtube',
                'confidence': 0.9
            }
        }
        
        content_type = formatter._detect_content_type(content_data)
        assert content_type == 'youtube'
    
    def test_detect_content_type_from_filename(self, formatter):
        """测试从文件名检测内容类型"""
        content_data = {
            'title': '测试内容',
            'original_file': 'machine_learning_lecture.mp3'
        }
        
        content_type = formatter._detect_content_type(content_data)
        assert content_type == 'lecture'
    
    def test_detect_content_type_youtube_filename(self, formatter):
        """测试YouTube文件名检测"""
        content_data = {
            'title': '测试内容',
            'original_file': 'youtube_tutorial_video.mp4'
        }
        
        content_type = formatter._detect_content_type(content_data)
        assert content_type == 'youtube'
    
    def test_detect_content_type_default_fallback(self, formatter):
        """测试默认回退检测"""
        content_data = {
            'title': '未知类型内容'
        }
        
        content_type = formatter._detect_content_type(content_data)
        assert content_type == 'lecture'
    
    def test_generate_youtube_markdown(self, formatter):
        """测试YouTube专用Markdown生成"""
        content_data = {
            'title': 'AI教程视频',
            'summary': '这是一个关于人工智能的教程视频，内容非常详细。',
            'mindmap': '# AI教程\n## 基础概念\n- 机器学习\n- 深度学习',
            'processed_time': '2025-08-22T10:30:00',
            'original_file': 'ai_tutorial.mp4',
            'source_url': 'https://www.youtube.com/watch?v=test123',
            'channel_name': 'AI教育频道',
            'video_duration': '25分30秒',
            'view_count': '12,345',
            'anonymized_names': {}
        }
        
        markdown = formatter._generate_youtube_markdown(content_data, '📺', '视频')
        
        # 验证YouTube特有内容
        assert '📺 AI教程视频' in markdown
        assert '**内容类型**: 视频' in markdown
        assert '**视频链接**: https://www.youtube.com/watch?v=test123' in markdown
        assert '**频道名称**: AI教育频道' in markdown
        assert '**视频时长**: 25分30秒' in markdown
        assert '**观看次数**: 12,345' in markdown
        assert '## 📹 视频信息' in markdown
        assert '## 🧠 知识提取' in markdown
        assert 'youtube-footer' in markdown
    
    def test_generate_podcast_markdown(self, formatter):
        """测试播客专用Markdown生成"""
        content_data = {
            'title': '技术访谈节目',
            'summary': '这是一期关于前端开发的技术访谈节目。',
            'mindmap': '# 技术访谈\n## 主要话题\n- React开发\n- 性能优化',
            'processed_time': '2025-08-22T15:00:00',
            'original_file': 'tech_interview_ep01.mp3',
            'podcast_series': '前端技术谈',
            'episode_number': '第1期',
            'host_name': '张主持',
            'guest_names': ['李嘉宾', '王专家'],
            'audio_duration': '45分钟',
            'anonymized_names': {'张三': '张主持', '李四': '李嘉宾'}
        }
        
        markdown = formatter._generate_podcast_markdown(content_data, '🎙️', '播客')
        
        # 验证播客特有内容
        assert '🎙️ 技术访谈节目' in markdown
        assert '**内容类型**: 播客' in markdown
        assert '**播客系列**: 前端技术谈' in markdown
        assert '**集数**: 第1期' in markdown
        assert '**主持人**: 张主持' in markdown
        assert '**嘉宾**: 李嘉宾, 王专家' in markdown
        assert '## 🎙️ 节目摘要' in markdown
        assert '## 💬 对话要点' in markdown
        assert '## 👥 人物信息' in markdown
        assert 'podcast-footer' in markdown
    
    def test_generate_lecture_markdown(self, formatter):
        """测试学术讲座专用Markdown生成"""
        content_data = {
            'title': '量子物理基础讲座',
            'summary': '这是一场关于量子物理基础知识的学术讲座。',
            'mindmap': '# 量子物理\n## 基本概念\n- 波粒二象性\n- 量子纠缠',
            'processed_time': '2025-08-22T14:00:00',
            'original_file': 'quantum_physics_lecture.mp3',
            'lecturer': '王教授',
            'institution': '清华大学',
            'course_name': '现代物理学导论',
            'academic_field': '物理学',
            'audio_duration': '90分钟',
            'anonymized_names': {'王老师': '王教授'}
        }
        
        markdown = formatter._generate_lecture_markdown(content_data, '🎓', '讲座')
        
        # 验证讲座特有内容
        assert '🎓 量子物理基础讲座' in markdown
        assert '**内容类型**: 讲座' in markdown
        assert '**讲师**: 王教授' in markdown
        assert '**机构**: 清华大学' in markdown
        assert '**课程名称**: 现代物理学导论' in markdown
        assert '**学科领域**: 物理学' in markdown
        assert '## 📚 讲座摘要' in markdown
        assert '## 🧠 知识框架' in markdown
        assert '## 🔬 学术标签' in markdown
        assert 'lecture-footer' in markdown
    
    def test_generate_rss_markdown(self, formatter):
        """测试RSS文章专用Markdown生成"""
        content_data = {
            'title': '人工智能最新进展',
            'summary': '这篇文章介绍了人工智能领域的最新研究进展。',
            'mindmap': '# AI进展\n## 新技术\n- GPT-4\n- 多模态AI',
            'processed_time': '2025-08-22T09:00:00',
            'original_file': 'ai_progress_article.txt',
            'source_url': 'https://tech-blog.com/ai-progress',
            'author': '科技作者',
            'published_date': '2025-08-20',
            'category': '技术',
            'anonymized_names': {}
        }
        
        markdown = formatter._generate_rss_markdown(content_data, '📰', '文章')
        
        # 验证RSS特有内容
        assert '📰 人工智能最新进展' in markdown
        assert '**内容类型**: 文章' in markdown
        assert '**文章链接**: https://tech-blog.com/ai-progress' in markdown
        assert '**作者**: 科技作者' in markdown
        assert '**发布日期**: 2025-08-20' in markdown
        assert '**分类**: 技术' in markdown
        assert '## 📰 文章摘要' in markdown
        assert '## 🔍 关键信息提取' in markdown
        assert 'rss-footer' in markdown
    
    def test_format_content_with_classification(self, formatter):
        """测试带分类结果的内容格式化"""
        content_data = {
            'title': 'Python编程教程',
            'summary': '这是一个Python编程的入门教程。',
            'mindmap': '# Python教程\n## 基础语法\n- 变量和类型',
            'processed_time': '2025-08-22T16:00:00',
            'original_file': 'python_tutorial.mp4',
            'classification_result': {
                'content_type': 'youtube',
                'confidence': 0.85,
                'auto_detected': True,
                'tags': ['编程', 'Python', '教程', '入门'],
                'metadata': {'icon': '📺'}
            },
            'source_url': 'https://www.youtube.com/watch?v=python123',
            'anonymized_names': {}
        }
        
        result = formatter.format_content(content_data)
        
        assert result['success'] is True
        content = result['content']
        
        # 验证内容类型被正确检测和应用
        assert content['content_type'] == 'youtube'
        assert '📺 Python编程教程' in content['markdown']
        assert '**内容类型**: 视频' in content['markdown']
        assert 'youtube.com' in content['markdown']
        
        # 验证元数据包含类型信息
        metadata = content['metadata']
        assert metadata['content_type'] == 'youtube'
        assert metadata['content_type_display'] == '视频'
        assert metadata['content_type_icon'] == '📺'
        assert metadata['type'] == 'youtube-analysis'
    
    def test_extract_enhanced_keywords_by_type(self, formatter):
        """测试根据内容类型提取增强关键词"""
        content_data = {
            'title': '机器学习算法讲解',
            'summary': '深度学习和神经网络的详细分析，包含实际项目案例。',
            'classification_result': {
                'tags': ['AI', '深度学习', '神经网络']
            }
        }
        
        # 测试不同内容类型的关键词
        youtube_keywords = formatter._extract_enhanced_keywords(content_data, 'youtube')
        lecture_keywords = formatter._extract_enhanced_keywords(content_data, 'lecture')
        podcast_keywords = formatter._extract_enhanced_keywords(content_data, 'podcast')
        
        # YouTube类型应包含视频相关关键词
        assert 'YouTube' in youtube_keywords
        assert '视频处理' in youtube_keywords
        
        # 讲座类型应包含教育相关关键词
        assert '学术讲座' in lecture_keywords
        assert '教育内容' in lecture_keywords
        
        # 播客类型应包含音频节目关键词
        assert '播客' in podcast_keywords
        assert '音频节目' in podcast_keywords
        
        # 所有类型都应包含从标题和摘要提取的关键词
        for keywords in [youtube_keywords, lecture_keywords, podcast_keywords]:
            assert '机器学习' in keywords
            # 检查是否包含"数据"相关关键词（数据分析、数据科学等）
            has_data_keyword = any('数据' in kw for kw in keywords)
            # 如果没有"数据"关键词，检查是否有"项目"相关关键词（从"项目案例"提取）
            has_project_keyword = any('项目' in kw for kw in keywords)
            assert has_data_keyword or has_project_keyword, f"应该包含数据或项目相关关键词，实际关键词: {keywords}"
            assert 'AI' in keywords  # 从分类结果
    
    def test_analyze_content_types(self, formatter):
        """测试内容类型分析统计"""
        results = [
            {
                'title': '视频1',
                'content_type': 'youtube',
                'date': '2025-08-22',
                'file': 'video1.html'
            },
            {
                'title': '讲座1',
                'content_type': 'lecture',
                'date': '2025-08-21',
                'file': 'lecture1.html'
            },
            {
                'title': '讲座2',
                'classification_result': {'content_type': 'lecture'},
                'date': '2025-08-20',
                'file': 'lecture2.html'
            },
            {
                'title': '播客1',
                'original_file': 'podcast_interview.mp3',
                'date': '2025-08-19',
                'file': 'podcast1.html'
            }
        ]
        
        type_stats = formatter._analyze_content_types(results)
        
        # 验证统计结果
        assert len(type_stats) == 3  # youtube, lecture, podcast
        assert type_stats['youtube']['count'] == 1
        assert type_stats['lecture']['count'] == 2
        assert type_stats['podcast']['count'] == 1
        
        # 验证类型配置信息
        assert type_stats['youtube']['icon'] == '📺'
        assert type_stats['youtube']['display_name'] == '视频'
        assert type_stats['lecture']['icon'] == '🎓'
        assert type_stats['podcast']['icon'] == '🎙️'
        
        # 验证最近条目记录
        assert len(type_stats['lecture']['recent_items']) == 2
        assert type_stats['youtube']['recent_items'][0]['title'] == '视频1'
    
    def test_create_enhanced_site_index(self, formatter):
        """测试创建增强的网站索引"""
        results = [
            {
                'title': 'Python视频教程',
                'content_type': 'youtube',
                'date': '2025-08-22',
                'file': 'python_video.html',
                'summary': '详细的Python编程视频教程'
            },
            {
                'title': '机器学习讲座',
                'content_type': 'lecture',
                'date': '2025-08-21',
                'file': 'ml_lecture.html',
                'summary': '机器学习基础知识讲座'
            }
        ]
        
        index_result = formatter.create_site_index(results)
        
        assert index_result['success'] is True
        content = index_result['content']
        
        # 验证增强的索引内容
        assert 'Project Bach - 多媒体内容处理结果' == content['title']
        assert content['total_items'] == 2
        assert 'content_type_stats' in content
        
        # 验证Markdown内容包含类型概览
        markdown = content['markdown']
        assert '## 📋 内容类型概览' in markdown
        assert '📺 视频' in markdown
        assert '🎓 讲座' in markdown
        
        # 验证类型分布统计
        assert '### 🏷️ 类型分布' in markdown
        assert '📱 按内容类型浏览' in markdown
        
        # 验证结果表格包含类型列
        assert '| 类型 | 日期 | 标题 | 摘要预览 | 操作 |' in markdown
        
        # 验证元数据更新
        metadata = content['metadata']
        assert '多媒体内容处理结果' in metadata['title']
        assert '内容分类' in metadata['keywords']
    
    def test_infer_type_from_filename(self, formatter):
        """测试从文件名推断内容类型"""
        test_cases = [
            ('youtube_tutorial_video.mp4', 'youtube'),
            ('rss_tech_news_feed.xml', 'rss'),
            ('podcast_interview_ep1.mp3', 'podcast'),
            ('machine_learning_lecture.mp3', 'lecture'),
            ('unknown_file.mp3', 'lecture')  # 默认回退
        ]
        
        for filename, expected_type in test_cases:
            result = formatter._infer_type_from_filename(filename)
            assert result == expected_type, f"文件名 {filename} 应该推断为 {expected_type}，实际为 {result}"
    
    def test_enhanced_metadata_extraction(self, formatter):
        """测试增强的元数据提取"""
        content_data = {
            'title': 'AI技术分享视频',
            'summary': '关于人工智能最新技术的分享视频，包含实际应用案例。',
            'processed_time': '2025-08-22T20:00:00',
            'content_type': 'youtube',
            'source_url': 'https://www.youtube.com/watch?v=ai_tech',
            'channel_name': 'AI科技频道',
            'video_duration': '30分钟',
            'view_count': '50,000',
            'classification_result': {
                'auto_detected': True,
                'confidence': 0.92,
                'tags': ['AI', '技术分享', '机器学习', '应用案例']
            }
        }
        
        metadata = formatter._extract_metadata(content_data)
        
        # 验证基础元数据
        assert metadata['title'] == 'AI技术分享视频'
        assert metadata['content_type'] == 'youtube'
        assert metadata['content_type_display'] == '视频'
        assert metadata['content_type_icon'] == '📺'
        assert metadata['type'] == 'youtube-analysis'
        
        # 验证YouTube特定元数据
        assert metadata['source_platform'] == 'YouTube'
        assert metadata['video_url'] == 'https://www.youtube.com/watch?v=ai_tech'
        assert metadata['channel'] == 'AI科技频道'
        assert metadata['video_duration'] == '30分钟'
        assert metadata['view_count'] == '50,000'
        
        # 验证分类结果元数据
        assert metadata['auto_detected'] is True
        assert metadata['classification_confidence'] == 0.92
        assert metadata['extracted_tags'] == ['AI', '技术分享', '机器学习', '应用案例']
        
        # 验证关键词包含类型特定和提取的标签
        keywords = metadata['keywords']
        assert 'YouTube' in keywords
        assert 'AI' in keywords
        assert '人工智能' in keywords
        assert '技术分享' in keywords


if __name__ == '__main__':
    # 运行测试
    pytest.main([__file__, '-v'])