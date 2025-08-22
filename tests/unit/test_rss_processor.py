#!/usr/bin/env python3
"""
Phase 6 RSS处理器 - 单元测试

测试RSSProcessor类的各个方法
"""

import pytest
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))


class TestRSSProcessor:
    """测试RSS处理器"""
    
    @pytest.fixture
    def rss_processor(self):
        """创建RSS处理器实例"""
        from src.web_frontend.processors.rss_processor import RSSProcessor
        config = {
            'max_articles': 50,
            'refresh_interval': 3600,
            'content_filter': {
                'min_content_length': 500,
                'max_content_length': 50000,
                'exclude_patterns': ['advertisement', 'sponsored', 'ad-block'],
                'include_patterns': ['technology', 'AI', 'research']
            },
            'summarization': {
                'max_summary_length': 500,
                'min_summary_length': 100,
                'preserve_key_terms': True
            }
        }
        return RSSProcessor(config)
    
    @pytest.fixture
    def sample_feed_entries(self):
        """示例RSS条目数据"""
        return [
            Mock(
                title="Advanced AI Research Breakthrough",
                link="https://techblog.example.com/ai-breakthrough-2024",
                summary="Scientists achieve new milestone in artificial intelligence...",
                published_parsed=datetime(2024, 1, 15, 10, 0, 0).timetuple(),
                content=[Mock(value="This comprehensive research paper discusses the latest advancements in artificial intelligence, focusing on novel neural network architectures that have shown remarkable performance improvements across various domains. The study involved extensive experiments and analysis of different machine learning approaches." * 10)],
                author="Dr. Jane Smith",
                tags=[Mock(term="AI"), Mock(term="research"), Mock(term="technology")]
            ),
            Mock(
                title="Tech Industry News Update",
                link="https://news.example.com/tech-update",
                summary="Latest updates from the technology sector...",
                published_parsed=datetime(2024, 1, 14, 14, 30, 0).timetuple(),
                content=[Mock(value="Brief update on technology industry trends and developments in various sectors including software and hardware innovations.")],
                author="Tech Reporter",
                tags=[Mock(term="technology"), Mock(term="industry")]
            ),
            Mock(
                title="Sponsored Advertisement Content",
                link="https://ads.example.com/sponsored-post",
                summary="This is a sponsored advertisement for products...",
                published_parsed=datetime(2024, 1, 13, 9, 0, 0).timetuple(),
                content=[Mock(value="Advertisement content for sponsored products and services.")],
                author="Ad Agency",
                tags=[Mock(term="advertisement")]
            )
        ]
    
    @patch('feedparser.parse')
    def test_parse_rss_feed_success(self, mock_feedparser, rss_processor, sample_feed_entries):
        """测试RSS feed解析成功"""
        # 模拟feedparser响应
        mock_feed = Mock()
        mock_feed.entries = sample_feed_entries
        mock_feed.feed = Mock(
            title="Tech Blog RSS",
            link="https://techblog.example.com",
            description="Latest technology news and research"
        )
        mock_feedparser.return_value = mock_feed
        
        url = "https://feeds.techblog.com/latest.rss"
        articles = rss_processor.parse_feed(url)
        
        assert len(articles) == 3
        assert articles[0]['title'] == "Advanced AI Research Breakthrough"
        assert articles[1]['title'] == "Tech Industry News Update"
        assert articles[2]['title'] == "Sponsored Advertisement Content"
        
        # 验证内容正确解析
        assert "artificial intelligence" in articles[0]['content'].lower()
        assert articles[0]['author'] == "Dr. Jane Smith"
        assert 'AI' in articles[0]['tags']
    
    @patch('feedparser.parse')
    def test_parse_rss_feed_failure(self, mock_feedparser, rss_processor):
        """测试RSS feed解析失败"""
        mock_feed = Mock()
        mock_feed.entries = []
        mock_feed.bozo = 1  # 表示解析错误
        mock_feed.bozo_exception = Exception("Feed parsing error")
        mock_feedparser.return_value = mock_feed
        
        url = "https://invalid-feed.com/rss.xml"
        
        with pytest.raises(ValueError, match="Failed to parse RSS feed"):
            rss_processor.parse_feed(url)
    
    def test_content_filtering_by_length(self, rss_processor):
        """测试基于长度的内容过滤"""
        articles = [
            {
                'title': 'Long Quality Article',
                'content': 'This is a comprehensive article with substantial content that provides valuable information to readers. ' * 20,  # 长内容
                'summary': 'Quality content with good length',
                'tags': ['technology']
            },
            {
                'title': 'Short Article',
                'content': 'Too short content.',  # 短内容
                'summary': 'Brief summary',
                'tags': ['tech']
            },
            {
                'title': 'Very Long Article',
                'content': 'Extremely long content that exceeds reasonable limits. ' * 1000,  # 超长内容
                'summary': 'Too much content',
                'tags': ['technology']
            }
        ]
        
        filtered = rss_processor.filter_content(articles)
        
        # 应该只保留长度适中的文章
        assert len(filtered) == 1
        assert filtered[0]['title'] == 'Long Quality Article'
    
    def test_content_filtering_by_patterns(self, rss_processor):
        """测试基于模式的内容过滤"""
        articles = [
            {
                'title': 'Good Technology Article',
                'content': 'This article discusses advanced technology and research innovations in the field of artificial intelligence. ' * 10,
                'summary': 'Technology research content',
                'tags': ['technology', 'AI']
            },
            {
                'title': 'Sponsored Advertisement Post',
                'content': 'This is sponsored advertisement content promoting various products and services for commercial purposes. ' * 10,
                'summary': 'Advertisement content',
                'tags': ['advertisement']
            },
            {
                'title': 'Ad-block Bypassing Content',
                'content': 'Content designed to bypass ad-block software and display promotional material to users without consent. ' * 10,
                'summary': 'Ad-block related content',
                'tags': ['marketing']
            }
        ]
        
        filtered = rss_processor.filter_content(articles)
        
        # 应该过滤掉广告相关内容
        assert len(filtered) == 1
        assert filtered[0]['title'] == 'Good Technology Article'
    
    def test_article_summarization_basic(self, rss_processor):
        """测试基础文章摘要生成"""
        long_content = """
        Artificial intelligence has revolutionized numerous industries and continues to advance at an unprecedented pace.
        Machine learning algorithms, particularly deep neural networks, have demonstrated remarkable capabilities in
        pattern recognition, natural language processing, and computer vision tasks. Researchers are now exploring
        novel architectures that can handle more complex reasoning tasks and exhibit better generalization abilities.
        The integration of AI systems into everyday applications has created new opportunities for innovation while
        also raising important questions about ethics, privacy, and the future of human-AI collaboration.
        """ * 10  # 重复创建长文本
        
        summary = rss_processor.generate_summary(long_content)
        
        assert isinstance(summary, str)
        assert len(summary) < len(long_content)
        assert 100 <= len(summary) <= 500  # 在配置的范围内
        assert "artificial intelligence" in summary.lower() or "AI" in summary or "machine learning" in summary.lower()
    
    def test_article_summarization_short_content(self, rss_processor):
        """测试短内容的摘要生成"""
        short_content = "Brief article about technology trends."
        
        summary = rss_processor.generate_summary(short_content)
        
        # 短内容应该返回原内容或轻微修改
        assert isinstance(summary, str)
        assert len(summary) >= len(short_content) - 10  # 允许少量修改
    
    def test_subscription_management_add(self, rss_processor):
        """测试添加订阅"""
        subscription = {
            'url': 'https://feeds.techblog.com/latest.rss',
            'name': 'Tech Blog Feed',
            'category': 'technology',
            'refresh_interval': 3600,
            'enabled': True
        }
        
        result = rss_processor.add_subscription(subscription)
        
        assert result is True
        subscriptions = rss_processor.get_subscriptions()
        assert len(subscriptions) == 1
        assert subscriptions[0]['name'] == 'Tech Blog Feed'
        assert subscriptions[0]['category'] == 'technology'
    
    def test_subscription_management_duplicate(self, rss_processor):
        """测试重复订阅处理"""
        subscription = {
            'url': 'https://feeds.techblog.com/latest.rss',
            'name': 'Tech Blog Feed',
            'category': 'technology'
        }
        
        # 第一次添加应该成功
        assert rss_processor.add_subscription(subscription) is True
        
        # 第二次添加相同URL应该失败或更新
        result = rss_processor.add_subscription(subscription)
        # 根据实现可能返回False(拒绝)或True(更新)
        subscriptions = rss_processor.get_subscriptions()
        assert len(subscriptions) == 1  # 应该只有一个订阅
    
    def test_subscription_management_remove(self, rss_processor):
        """测试删除订阅"""
        # 先添加订阅
        subscription = {
            'url': 'https://feeds.techblog.com/latest.rss',
            'name': 'Tech Blog Feed',
            'category': 'technology'
        }
        rss_processor.add_subscription(subscription)
        
        # 删除订阅
        result = rss_processor.remove_subscription('https://feeds.techblog.com/latest.rss')
        
        assert result is True
        subscriptions = rss_processor.get_subscriptions()
        assert len(subscriptions) == 0
    
    def test_duplicate_detection_same_url(self, rss_processor):
        """测试基于URL的重复文章检测"""
        article1 = {
            'title': 'Technology Article',
            'link': 'https://techblog.com/article-123',
            'content': 'Article content about technology trends and innovations.',
            'published': '2024-01-15T10:00:00Z'
        }
        
        article2 = {
            'title': 'Technology Article (Updated)',
            'link': 'https://techblog.com/article-123',  # 相同URL
            'content': 'Updated article content about technology trends.',
            'published': '2024-01-15T11:00:00Z'
        }
        
        # 第一次应该不是重复
        assert rss_processor.is_duplicate(article1) is False
        rss_processor.mark_as_processed(article1)
        
        # 第二次相同URL应该被检测为重复
        assert rss_processor.is_duplicate(article2) is True
    
    def test_duplicate_detection_same_title(self, rss_processor):
        """测试基于标题的重复文章检测"""
        article1 = {
            'title': 'Breakthrough in AI Research',
            'link': 'https://site1.com/ai-breakthrough',
            'content': 'Content about AI research developments.'
        }
        
        article2 = {
            'title': 'Breakthrough in AI Research',  # 相同标题
            'link': 'https://site2.com/ai-news',     # 不同URL
            'content': 'Similar content about AI research.'
        }
        
        # 第一次不是重复
        assert rss_processor.is_duplicate(article1) is False
        rss_processor.mark_as_processed(article1)
        
        # 相同标题应该被检测为重复
        assert rss_processor.is_duplicate(article2) is True
    
    @patch('requests.get')
    def test_feed_validation_valid_feed(self, mock_requests, rss_processor):
        """测试有效RSS feed验证"""
        # 模拟有效的RSS响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'content-type': 'application/rss+xml; charset=utf-8'}
        mock_response.text = '''<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <title>Test Feed</title>
                <description>Test RSS Feed</description>
            </channel>
        </rss>'''
        mock_requests.return_value = mock_response
        
        url = "https://valid-feed.com/rss.xml"
        result = rss_processor.validate_feed_url(url)
        
        assert result is True
        mock_requests.assert_called_once_with(url, timeout=10, headers={'User-Agent': 'RSS Reader'})
    
    @patch('requests.get')
    def test_feed_validation_invalid_feed(self, mock_requests, rss_processor):
        """测试无效RSS feed验证"""
        # 模拟404响应
        mock_response = Mock()
        mock_response.status_code = 404
        mock_requests.return_value = mock_response
        
        url = "https://invalid-feed.com/nonexistent.rss"
        result = rss_processor.validate_feed_url(url)
        
        assert result is False
    
    @patch('requests.get')
    def test_feed_validation_connection_error(self, mock_requests, rss_processor):
        """测试网络连接错误处理"""
        # 模拟连接错误
        mock_requests.side_effect = ConnectionError("Connection failed")
        
        url = "https://unreachable-feed.com/rss.xml"
        result = rss_processor.validate_feed_url(url)
        
        assert result is False
    
    def test_get_feed_statistics(self, rss_processor):
        """测试获取订阅统计信息"""
        # 添加一些订阅
        subscriptions = [
            {'url': 'https://tech.com/rss', 'category': 'technology', 'enabled': True},
            {'url': 'https://ai.com/feed', 'category': 'AI', 'enabled': True},
            {'url': 'https://news.com/rss', 'category': 'news', 'enabled': False}
        ]
        
        for sub in subscriptions:
            rss_processor.add_subscription(sub)
        
        stats = rss_processor.get_statistics()
        
        assert isinstance(stats, dict)
        assert 'total_subscriptions' in stats
        assert 'active_subscriptions' in stats
        assert 'articles_processed_today' in stats
        assert stats['total_subscriptions'] == 3
        assert stats['active_subscriptions'] == 2  # 只有enabled=True的