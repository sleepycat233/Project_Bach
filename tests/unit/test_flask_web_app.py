#!/usr/bin/env python3
"""
Phase 6 Flask Web应用 - 单元测试

测试Flask Web界面的各个组件和路由
"""

import pytest
import tempfile
import shutil
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from werkzeug.datastructures import FileStorage

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))


class TestFlaskWebApplication:
    """测试Flask Web应用"""
    
    @pytest.fixture
    def temp_dir(self):
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def app_config(self, temp_dir):
        """Flask应用配置"""
        return {
            'TESTING': True,
            'SECRET_KEY': 'test-secret-key-for-phase6',
            'WTF_CSRF_ENABLED': False,
            'UPLOAD_FOLDER': temp_dir,
            'MAX_CONTENT_LENGTH': 100 * 1024 * 1024,  # 100MB
            'ALLOWED_EXTENSIONS': {'.mp3', '.wav', '.m4a', '.mp4', '.flac'},
            'TAILSCALE_NETWORK': '100.64.0.0/10',
            'RATE_LIMIT_PER_MINUTE': 60
        }
    
    @pytest.fixture
    def flask_app(self, app_config):
        """创建Flask应用测试实例"""
        from src.web_frontend.app import create_app
        app = create_app(app_config)
        return app
    
    @pytest.fixture
    def client(self, flask_app):
        """创建测试客户端"""
        return flask_app.test_client()
    
    def test_homepage_renders_correctly(self, client):
        """测试主页正确渲染"""
        response = client.get('/')
        
        assert response.status_code == 200
        assert b'Project Bach' in response.data
        assert b'Upload Audio' in response.data
        assert b'YouTube Video' in response.data
        
        # 检查分类选项
        assert b'lecture' in response.data
    
    def test_audio_upload_form_valid_file(self, client, temp_dir):
        """测试有效音频文件上传"""
        # 创建模拟MP3文件
        mp3_content = b'\xff\xfb\x90\x00' + b'\x00' * 1024  # MP3头 + 数据
        
        data = {
            'audio_file': (BytesIO(mp3_content), 'physics_lecture.mp3'),
            'content_type': 'lecture',
            'lecture_series': 'Physics 101',
            'tags': 'quantum, physics, education',
            'description': 'Introduction to quantum mechanics'
        }
        
        with patch('src.web_frontend.handlers.audio_upload_handler.AudioUploadHandler.process_upload') as mock_process:
            mock_process.return_value = {
                'status': 'success',
                'processing_id': 'proc_123',
                'estimated_time': 300
            }
            
            response = client.post('/upload/audio', 
                                 data=data, 
                                 content_type='multipart/form-data')
            
            assert response.status_code in [200, 302]  # 成功或重定向
            mock_process.assert_called_once()
    
    def test_audio_upload_invalid_file_type(self, client):
        """测试无效文件类型上传"""
        # 创建文本文件而不是音频文件
        text_content = b'This is not an audio file'
        
        data = {
            'audio_file': (BytesIO(text_content), 'document.txt'),
            'content_type': 'lecture'
        }
        
        response = client.post('/upload/audio', 
                             data=data, 
                             content_type='multipart/form-data')
        
        assert response.status_code == 400  # Bad Request
        assert b'Invalid file type' in response.data or b'error' in response.data.lower()
    
    def test_audio_upload_file_too_large(self, client):
        """测试文件过大处理"""
        # 创建超大文件 (超过100MB限制)
        large_content = b'\xff\xfb\x90\x00' + b'\x00' * (101 * 1024 * 1024)
        
        data = {
            'audio_file': (BytesIO(large_content), 'large_file.mp3'),
            'content_type': 'lecture'
        }
        
        response = client.post('/upload/audio', 
                             data=data, 
                             content_type='multipart/form-data')
        
        assert response.status_code == 413  # Payload Too Large
    
    def test_audio_upload_missing_required_fields(self, client):
        """测试缺少必需字段"""
        # 只提供文件，缺少content_type
        mp3_content = b'\xff\xfb\x90\x00' + b'\x00' * 1024
        
        data = {
            'audio_file': (BytesIO(mp3_content), 'test.mp3')
            # 缺少 content_type
        }
        
        response = client.post('/upload/audio', 
                             data=data, 
                             content_type='multipart/form-data')
        
        assert response.status_code == 400  # Bad Request
        assert b'content_type' in response.data or b'required' in response.data.lower()
    
    def test_youtube_url_submission_valid(self, client):
        """测试有效YouTube URL提交"""
        data = {
            'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'content_type': 'youtube',
            'tags': 'music, entertainment, tutorial',
            'description': 'Educational video about music theory'
        }
        
        with patch('src.web_frontend.handlers.youtube_handler.YouTubeHandler.process_url') as mock_process:
            mock_process.return_value = {
                'status': 'success',
                'processing_id': 'yt_456',
                'video_title': 'Test Video',
                'estimated_time': 600
            }
            
            response = client.post('/upload/youtube', data=data)
            
            assert response.status_code in [200, 302]
            mock_process.assert_called_once()
    
    def test_youtube_url_submission_invalid_url(self, client):
        """测试无效YouTube URL提交"""
        data = {
            'youtube_url': 'https://vimeo.com/123456',  # 不是YouTube
            'content_type': 'youtube'
        }
        
        response = client.post('/upload/youtube', data=data)
        
        assert response.status_code == 400
        assert b'Invalid YouTube URL' in response.data or b'youtube' in response.data.lower()
    
    def test_youtube_url_submission_missing_url(self, client):
        """测试缺少YouTube URL"""
        data = {
            'content_type': 'youtube'
            # 缺少 youtube_url
        }
        
        response = client.post('/upload/youtube', data=data)
        
        assert response.status_code == 400
        assert b'URL' in response.data or b'required' in response.data.lower()
    
    def test_processing_status_api(self, client):
        """测试处理状态查询API"""
        with patch('src.web_frontend.services.processing_service.ProcessingService.get_status') as mock_status:
            mock_status.return_value = {
                'queue_size': 3,
                'processing_items': [
                    {'id': 'proc_123', 'type': 'audio', 'progress': 45},
                    {'id': 'yt_456', 'type': 'youtube', 'progress': 20}
                ],
                'completed_today': 8,
                'average_processing_time': 180
            }
            
            response = client.get('/api/status/processing')
            
            assert response.status_code == 200
            
            data = response.get_json()
            assert 'queue_size' in data
            assert 'processing_items' in data
            assert 'completed_today' in data
            assert data['queue_size'] == 3
            assert len(data['processing_items']) == 2
    
    def test_content_categories_api(self, client):
        """测试内容分类API"""
        response = client.get('/api/categories')
        
        assert response.status_code == 200
        
        data = response.get_json()
        assert isinstance(data, dict)
        assert 'lecture' in data
        assert 'youtube' in data
        # 检查分类详细信息
        assert data['lecture']['icon'] == '🎓'
        assert data['youtube']['icon'] == '📺'
    
    def test_recent_results_api(self, client):
        """测试最近结果API"""
        with patch('src.web_frontend.app.get_processing_service') as mock_service:
            mock_service.return_value.get_recent_results.return_value = [
                {
                    'filename': 'lecture1.mp3',
                    'content_type': 'lecture',
                    'summary': 'Physics lecture summary',
                    'processed_at': '2024-01-15T10:00:00Z'
                },
                {
                    'filename': 'video1.mp3',
                    'content_type': 'youtube',
                    'summary': 'Tech video summary',
                    'processed_at': '2024-01-15T09:30:00Z'
                }
            ]
            
            response = client.get('/api/results/recent?limit=10')
            
            assert response.status_code == 200
            
            data = response.get_json()
            assert isinstance(data, list)
            assert len(data) == 2
            assert data[0]['content_type'] == 'lecture'
            assert data[1]['content_type'] == 'youtube'
    
    def test_tailscale_security_middleware_valid_ip(self, client):
        """测试Tailscale网络安全中间件 - 有效IP"""
        # 模拟Tailscale网络内的IP访问
        with client.application.test_request_context('/', environ_base={'REMOTE_ADDR': '100.64.0.100'}):
            response = client.get('/')
            assert response.status_code == 200
    
    def test_tailscale_security_middleware_invalid_ip(self, client):
        """测试Tailscale网络安全中间件 - 无效IP"""
        # 模拟非Tailscale IP访问
        invalid_ips = ['192.168.1.100', '10.0.0.1', '172.16.0.1', '8.8.8.8']
        
        for ip in invalid_ips:
            with client.application.test_request_context('/', environ_base={'REMOTE_ADDR': ip}):
                response = client.get('/')
                # 应该被拒绝或重定向到错误页面
                assert response.status_code in [403, 404, 302]
    
    def test_rate_limiting_protection(self, client):
        """测试请求频率限制保护"""
        # 快速发送多个请求
        responses = []
        for i in range(65):  # 超过60次/分钟的限制
            response = client.get('/api/status/processing')
            responses.append(response.status_code)
        
        # 应该有一些请求被限制
        assert 429 in responses  # Too Many Requests
    
    def test_error_handling_404(self, client):
        """测试404错误处理"""
        response = client.get('/nonexistent-page')
        
        assert response.status_code == 404
        assert b'Not Found' in response.data or b'404' in response.data
    
    def test_error_handling_500(self, client):
        """测试500错误处理"""
        # 模拟内部服务器错误
        with patch('src.web_frontend.app.render_template') as mock_render:
            mock_render.side_effect = Exception("Internal error")
            
            response = client.get('/')
            
            assert response.status_code == 500
    
    def test_csrf_protection_disabled_in_testing(self, client):
        """测试CSRF保护在测试环境中被禁用"""
        # 在测试配置中CSRF应该被禁用
        data = {
            'youtube_url': 'https://www.youtube.com/watch?v=test',
            'content_type': 'youtube'
        }
        
        with patch('src.web_frontend.handlers.youtube_handler.YouTubeHandler.process_url') as mock_process:
            mock_process.return_value = {'status': 'success', 'processing_id': 'test'}
            
            # 不提供CSRF token应该仍然成功（因为在测试中禁用了）
            response = client.post('/upload/youtube', data=data)
            
            assert response.status_code != 400  # 不应该因为CSRF失败