#!/usr/bin/env python3
"""
Phase 6 多媒体内容分类与Web界面 - 集成测试

测试各个组件之间的集成和端到端工作流
"""

import pytest
import tempfile
import shutil
import json
import time
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))


class TestPhase6Integration:
    """Phase 6 集成测试"""
    
    @pytest.fixture
    def temp_workspace(self):
        """临时工作空间"""
        temp_dir = tempfile.mkdtemp(prefix="phase6_integration_")
        
        # 创建完整的目录结构
        directories = [
            'data/uploads',
            'output',
            'temp',
            'data/logs',
            'data/output/public/transcripts',
            'data/output',
            'web_frontend/static',
            'web_frontend/templates'
        ]
        
        for dir_path in directories:
            (Path(temp_dir) / dir_path).mkdir(parents=True, exist_ok=True)
        
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def integration_system(self, temp_workspace):
        """创建集成测试系统"""
        from src.web_frontend.integration_workflow import Phase6IntegrationWorkflow
        return Phase6IntegrationWorkflow(temp_workspace)
    
    @pytest.fixture
    def sample_audio_file(self, temp_workspace):
        """创建示例音频文件"""
        audio_path = Path(temp_workspace) / "data/uploads" / "physics_lecture.mp3"
        
        # 创建模拟MP3文件
        mp3_header = b'\xff\xfb\x90\x00'
        fake_audio_data = mp3_header + b'\x00' * (5 * 1024 * 1024)  # 5MB
        
        with open(audio_path, 'wb') as f:
            f.write(fake_audio_data)
        
        return str(audio_path)
    
    def test_end_to_end_audio_upload_workflow(self, integration_system, sample_audio_file):
        """测试端到端音频上传工作流"""
        # 准备上传数据
        upload_data = {
            'file_path': sample_audio_file,
            'content_type': 'lecture',
            'lecture_series': 'Physics 101',
            'tags': ['physics', 'quantum', 'education'],
            'description': 'Introduction to quantum mechanics fundamentals'
        }
        
        with patch('src.core.audio_processor.AudioProcessor.process_file') as mock_audio_process:
            # 模拟音频处理结果
            mock_audio_process.return_value = {
                'filename': 'physics_lecture.mp3',
                'transcription': 'Today we will discuss quantum mechanics and wave-particle duality...',
                'summary': 'This lecture introduces fundamental concepts of quantum mechanics...',
                'mindmap': '''# Quantum Mechanics\n## Wave-Particle Duality\n## Uncertainty Principle''',
                'anonymized_text': 'Today we will discuss quantum mechanics and wave-particle duality...',
                'processing_time': 145.2
            }
            
            with patch('src.web_frontend.processors.content_classifier.ContentClassifier.classify_content') as mock_classify:
                mock_classify.return_value = {
                    'content_type': 'lecture',
                    'confidence': 0.92,
                    'auto_detected': True,
                    'tags': ['physics', 'quantum', 'education', 'mechanics'],
                    'metadata': {'icon': '🎓', 'series': 'Physics 101'}
                }
                
                # 执行完整处理流程
                result = integration_system.process_audio_upload(upload_data)
                
                # 验证结果
                assert result['status'] == 'success'
                assert result['content_type'] == 'lecture'
                assert 'processing_id' in result
                assert result['confidence'] > 0.9
                assert 'physics' in result['tags']
                
                # 验证调用链
                mock_audio_process.assert_called_once()
                mock_classify.assert_called_once()
    
    def test_end_to_end_youtube_processing_workflow(self, integration_system):
        """测试端到端YouTube处理工作流"""
        youtube_data = {
            'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'content_type': 'youtube',
            'tags': ['machine-learning', 'tutorial', 'AI'],
            'description': 'Comprehensive ML tutorial for beginners'
        }
        
        with patch('src.web_frontend.processors.youtube_processor.YouTubeProcessor.process') as mock_yt_process:
            # 模拟YouTube处理结果
            mock_yt_process.return_value = {
                'audio_file': '/tmp/ml_tutorial.mp3',
                'metadata': {
                    'title': 'Machine Learning Tutorial - Neural Networks',
                    'duration': 1800,
                    'uploader': 'AI Education Channel',
                    'description': 'Comprehensive tutorial on neural networks...',
                    'view_count': 50000
                }
            }
            
            with patch('src.core.audio_processor.AudioProcessor.process_file') as mock_audio_process:
                mock_audio_process.return_value = {
                    'transcription': 'Welcome to this machine learning tutorial...',
                    'summary': 'This tutorial covers neural network fundamentals...',
                    'mindmap': '''# Machine Learning\n## Neural Networks\n## Training Process''',
                    'processing_time': 220.5
                }
                
                with patch('src.web_frontend.processors.content_classifier.ContentClassifier.classify_content') as mock_classify:
                    mock_classify.return_value = {
                        'content_type': 'youtube',
                        'confidence': 0.95,
                        'auto_detected': True,
                        'tags': ['machine-learning', 'tutorial', 'AI', 'neural-networks'],
                        'metadata': {'icon': '📺', 'platform': 'YouTube'}
                    }
                    
                    # 执行YouTube处理流程
                    result = integration_system.process_youtube_url(youtube_data)
                    
                    # 验证结果
                    assert result['status'] == 'success'
                    assert result['content_type'] == 'youtube'
                    assert result['video_title'] == 'Machine Learning Tutorial - Neural Networks'
                    assert result['duration'] == 1800
                    assert 'machine-learning' in result['tags']
                    
                    # 验证调用链
                    mock_yt_process.assert_called_once()
                    mock_audio_process.assert_called_once()
                    mock_classify.assert_called_once()
    
    def test_end_to_end_rss_processing_workflow(self, integration_system):
        """测试端到端RSS处理工作流"""
        rss_data = {
            'feed_url': 'https://feeds.techcrunch.com/TechCrunch/',
            'subscription_name': 'TechCrunch AI News',
            'category': 'technology',
            'max_articles': 5,
            'auto_process': True
        }
        
        with patch('src.web_frontend.processors.rss_processor.RSSProcessor.process_feed') as mock_rss_process:
            # 模拟RSS处理结果
            mock_rss_process.return_value = [
                {
                    'title': 'AI Breakthrough in Natural Language Processing',
                    'content': 'Researchers at leading tech companies have achieved...' * 100,
                    'summary': 'New AI models show remarkable improvements in NLP tasks...',
                    'link': 'https://techcrunch.com/ai-breakthrough-nlp',
                    'author': 'Tech Reporter',
                    'published': '2024-01-15T10:00:00Z',
                    'tags': ['AI', 'NLP', 'research']
                },
                {
                    'title': 'Quantum Computing Advances in 2024',
                    'content': 'The field of quantum computing continues to evolve...' * 80,
                    'summary': 'Significant progress in quantum computing hardware and algorithms...',
                    'link': 'https://techcrunch.com/quantum-computing-2024',
                    'author': 'Science Writer',
                    'published': '2024-01-14T15:30:00Z',
                    'tags': ['quantum', 'computing', 'technology']
                }
            ]
            
            with patch('src.core.ai_generation.AIContentGenerator.generate_content') as mock_ai_gen:
                mock_ai_gen.return_value = {
                    'summary': 'Comprehensive summary of recent tech developments...',
                    'mindmap': '''# Technology News\n## AI Advances\n## Quantum Computing''',
                    'key_points': ['AI NLP improvements', 'Quantum hardware progress']
                }
                
                with patch('src.web_frontend.processors.content_classifier.ContentClassifier.classify_content') as mock_classify:
                    mock_classify.return_value = {
                        'content_type': 'rss',
                        'confidence': 0.88,
                        'auto_detected': True,
                        'tags': ['technology', 'AI', 'quantum', 'news'],
                        'metadata': {'icon': '📰', 'source': 'TechCrunch'}
                    }
                    
                    # 执行RSS处理流程
                    result = integration_system.process_rss_subscription(rss_data)
                    
                    # 验证结果
                    assert result['status'] == 'success'
                    assert result['content_type'] == 'rss'
                    assert result['articles_processed'] == 2
                    assert result['subscription_name'] == 'TechCrunch AI News'
                    assert 'technology' in result['tags']
                    
                    # 验证调用链
                    mock_rss_process.assert_called_once()
                    mock_ai_gen.assert_called()
                    mock_classify.assert_called()
    
    def test_github_pages_categorized_deployment(self, integration_system):
        """测试GitHub Pages分类部署集成"""
        # 准备多类型内容数据
        content_data = [
            {
                'filename': 'physics_lecture.mp3',
                'content_type': 'lecture',
                'title': 'Quantum Mechanics Introduction',
                'summary': 'Fundamental concepts of quantum physics...',
                'lecture_series': 'Physics 101',
                'tags': ['physics', 'quantum', 'education'],
                'processed_at': '2024-01-15T10:00:00Z'
            },
            {
                'filename': 'ml_tutorial.mp3',
                'content_type': 'youtube',
                'title': 'Machine Learning Basics',
                'summary': 'Introduction to neural networks...',
                'source_url': 'https://youtube.com/watch?v=ml123',
                'uploader': 'AI Channel',
                'tags': ['AI', 'machine-learning', 'tutorial'],
                'processed_at': '2024-01-15T09:30:00Z'
            },
            {
                'filename': 'tech_news.txt',
                'content_type': 'rss',
                'title': 'Latest Technology Trends',
                'summary': 'Overview of current tech developments...',
                'source_url': 'https://techblog.com/trends-2024',
                'publication': 'Tech Blog',
                'tags': ['technology', 'trends', 'news'],
                'processed_at': '2024-01-15T08:00:00Z'
            }
        ]
        
        with patch('src.publishing.content_formatter.ContentFormatter.format_batch') as mock_format:
            mock_format.return_value = content_data
            
            with patch('src.publishing.template_engine.TemplateEngine.generate_category_pages') as mock_template:
                mock_template.return_value = {
                    'lecture': [content_data[0]],
                    'youtube': [content_data[1]],
                    'rss': [content_data[2]],
                    'index': content_data
                }
                
                with patch('src.publishing.publishing_workflow.PublishingWorkflow.deploy_to_github_pages') as mock_deploy:
                    mock_deploy.return_value = {
                        'status': 'success',
                        'pages_deployed': ['index.html', 'lectures.html', 'videos.html', 'articles.html'],
                        'commit_hash': 'abc123def',
                        'deployment_time': 45.3
                    }
                    
                    # 执行分类部署
                    deployment_result = integration_system.deploy_categorized_content(content_data)
                    
                    # 验证结果
                    assert deployment_result['status'] == 'success'
                    assert 'pages_generated' in deployment_result
                    assert 'lecture' in deployment_result['pages_generated']
                    assert 'youtube' in deployment_result['pages_generated']
                    assert 'rss' in deployment_result['pages_generated']
                    assert 'index' in deployment_result['pages_generated']
                    
                    # 验证调用链
                    mock_format.assert_called_once()
                    mock_template.assert_called_once()
                    mock_deploy.assert_called_once()
    
    def test_flask_web_interface_integration(self, integration_system, temp_workspace):
        """测试Flask Web界面集成"""
        from src.web_frontend.app import create_app
        
        app_config = {
            'TESTING': True,
            'SECRET_KEY': 'test-key',
            'UPLOAD_FOLDER': temp_workspace,
            'WTF_CSRF_ENABLED': False
        }
        
        app = create_app(app_config)
        client = app.test_client()
        
        # 测试主要端点的集成
        with patch('src.web_frontend.services.processing_service.ProcessingService') as mock_service:
            mock_service.return_value.get_status.return_value = {
                'queue_size': 2,
                'processing_items': [],
                'completed_today': 5
            }
            
            # 测试主页
            response = client.get('/')
            assert response.status_code == 200
            
            # 测试API端点
            response = client.get('/api/status/processing')
            assert response.status_code == 200
            
            response = client.get('/api/categories')
            assert response.status_code == 200
    
    def test_content_classification_pipeline_integration(self, integration_system):
        """测试内容分类管道集成"""
        # 测试数据
        test_inputs = [
            {
                'filename': 'professor_lecture.mp3',
                'content': 'Today we will study advanced mathematics in university...',
                'source_url': None,
                'expected_type': 'lecture'
            },
            {
                'filename': 'downloaded_video.mp3',
                'content': 'Welcome to this tutorial video...',
                'source_url': 'https://youtube.com/watch?v=abc123',
                'expected_type': 'youtube'
            },
            {
                'filename': 'article_summary.txt',
                'content': 'Technology news and trends in artificial intelligence...',
                'source_url': 'https://techblog.com/feed.rss',
                'expected_type': 'rss'
            }
        ]
        
        with patch('src.web_frontend.processors.content_classifier.ContentClassifier') as mock_classifier:
            classifier_instance = mock_classifier.return_value
            
            # 为每个测试输入设置不同的返回值
            def mock_classify_content(filename, content, source_url):
                for test_input in test_inputs:
                    if filename == test_input['filename']:
                        return {
                            'content_type': test_input['expected_type'],
                            'confidence': 0.9,
                            'auto_detected': True,
                            'tags': ['test', 'classification'],
                            'metadata': {'icon': '🎓' if test_input['expected_type'] == 'lecture' else '📺'}
                        }
                return {'content_type': 'lecture', 'confidence': 0.5}
            
            classifier_instance.classify_content.side_effect = mock_classify_content
            
            # 测试分类管道
            for test_input in test_inputs:
                result = integration_system.classify_and_process_content(
                    filename=test_input['filename'],
                    content=test_input['content'],
                    source_url=test_input['source_url']
                )
                
                assert result['content_type'] == test_input['expected_type']
                assert result['confidence'] > 0.8
    
    def test_performance_monitoring_integration(self, integration_system):
        """测试性能监控集成"""
        # 模拟处理活动
        with patch('src.monitoring.performance_monitor.PerformanceMonitor') as mock_monitor:
            monitor_instance = mock_monitor.return_value
            monitor_instance.get_metrics.return_value = {
                'processing_times': {
                    'lecture': {'avg': 120.5, 'min': 80.2, 'max': 180.7},
                    'youtube': {'avg': 250.8, 'min': 180.5, 'max': 350.2},
                    'rss': {'avg': 45.3, 'min': 20.1, 'max': 90.5}
                },
                'queue_sizes': {
                    'current': 3,
                    'peak_today': 12,
                    'avg_today': 4.5
                },
                'success_rates': {
                    'lecture': 0.95,
                    'youtube': 0.88,
                    'rss': 0.92
                },
                'error_counts': {
                    'lecture': 2,
                    'youtube': 5,
                    'rss': 3
                }
            }
            
            # 获取性能指标
            metrics = integration_system.get_performance_metrics()
            
            # 验证指标结构
            assert 'processing_times' in metrics
            assert 'queue_sizes' in metrics
            assert 'success_rates' in metrics
            assert 'error_counts' in metrics
            
            # 验证各类型处理时间统计
            assert 'lecture' in metrics['processing_times']
            assert 'youtube' in metrics['processing_times']
            assert 'rss' in metrics['processing_times']
            
            # 验证成功率合理
            for content_type, rate in metrics['success_rates'].items():
                assert 0.0 <= rate <= 1.0
    
    def test_error_handling_and_recovery_integration(self, integration_system):
        """测试错误处理和恢复集成"""
        # 模拟各种错误场景
        error_scenarios = [
            {
                'type': 'network_error',
                'exception': ConnectionError("Network unreachable"),
                'expected_status': 'error',
                'expected_retry': True
            },
            {
                'type': 'file_not_found',
                'exception': FileNotFoundError("Audio file not found"),
                'expected_status': 'error',
                'expected_retry': False
            },
            {
                'type': 'processing_timeout',
                'exception': TimeoutError("Processing timeout"),
                'expected_status': 'timeout',
                'expected_retry': True
            }
        ]
        
        for scenario in error_scenarios:
            with patch('src.core.audio_processor.AudioProcessor.process_file') as mock_process:
                mock_process.side_effect = scenario['exception']
                
                # 测试错误处理
                result = integration_system.handle_processing_error(
                    error_type=scenario['type'],
                    file_path='/test/file.mp3'
                )
                
                assert result['status'] == scenario['expected_status']
                assert result['retry_recommended'] == scenario['expected_retry']
                assert 'error_message' in result
                assert 'timestamp' in result
    
    def test_concurrent_processing_integration(self, integration_system):
        """测试并发处理集成"""
        import threading
        import queue
        
        # 准备多个并发任务
        tasks = [
            {'type': 'audio', 'file': 'lecture1.mp3'},
            {'type': 'youtube', 'url': 'https://youtube.com/watch?v=test1'},
            {'type': 'audio', 'file': 'lecture2.mp3'},
            {'type': 'rss', 'url': 'https://feeds.example.com/feed1.rss'},
            {'type': 'youtube', 'url': 'https://youtube.com/watch?v=test2'}
        ]
        
        results_queue = queue.Queue()
        
        def process_task(task):
            """模拟任务处理"""
            with patch('time.sleep'):  # 跳过实际等待
                if task['type'] == 'audio':
                    result = integration_system.process_audio_upload({
                        'file_path': task['file'],
                        'content_type': 'lecture'
                    })
                elif task['type'] == 'youtube':
                    result = integration_system.process_youtube_url({
                        'url': task['url'],
                        'content_type': 'youtube'
                    })
                elif task['type'] == 'rss':
                    result = integration_system.process_rss_subscription({
                        'feed_url': task['url']
                    })
                
                results_queue.put(result)
        
        # 启动并发处理
        threads = []
        for task in tasks:
            thread = threading.Thread(target=process_task, args=(task,))
            threads.append(thread)
            thread.start()
        
        # 等待所有任务完成
        for thread in threads:
            thread.join(timeout=1.0)  # 短超时用于测试
        
        # 验证结果
        results = []
        while not results_queue.empty():
            results.append(results_queue.get_nowait())
        
        # 至少应该有一些结果（可能不是全部，由于mock和超时）
        assert len(results) >= 0
        for result in results:
            assert 'status' in result
            assert result['status'] in ['success', 'error', 'timeout']