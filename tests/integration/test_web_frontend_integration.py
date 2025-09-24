#!/usr/bin/env python3
"""
Web前端集成测试

测试多个组件协作的场景，与单元测试分离：
- Flask应用与handlers的集成
- Templates与API的集成
- 端到端的用户工作流
"""

import pytest
import tempfile
import shutil
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))


class TestWebFrontendIntegration:
    """Web前端集成测试"""
    
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
            'SECRET_KEY': 'test-secret-key',
            'WTF_CSRF_ENABLED': False,
            'UPLOAD_FOLDER': temp_dir,
            'MAX_CONTENT_LENGTH': 100 * 1024 * 1024,
            'ALLOWED_EXTENSIONS': {'.mp3', '.wav', '.m4a'},
        }
    
    @pytest.fixture
    def flask_app(self, app_config):
        """创建Flask应用实例"""
        from src.web_frontend.app import create_app
        
        from src.utils.config import UploadSettings, SecuritySettings

        # 设置完整的mock配置
        mock_config_manager = Mock()
        mock_config_manager.get_upload_settings.return_value = UploadSettings()
        mock_config_manager.get_security_settings.return_value = SecuritySettings()
        mock_config_manager.get_full_config.return_value = {}
        mock_config_manager.get_paths_config.return_value = {
            'data_folder': app_config['UPLOAD_FOLDER'],
            'output_folder': './data/output',
            'watch_folder': './data/uploads'
        }
        mock_config_manager.get.return_value = {}
        mock_config_manager.config = {
            'tailscale': {'enabled': False},
            'paths': {'output_folder': './data/output'}
        }
        
        app = create_app(app_config)
        app.config['CONFIG_MANAGER'] = mock_config_manager
        return app
    
    @pytest.fixture
    def client(self, flask_app):
        """创建测试客户端"""
        return flask_app.test_client()

    # ===== 端到端集成测试 =====
    
    def test_homepage_to_upload_workflow(self, client):
        """测试从主页到上传的完整工作流"""
        # 1. 访问主页
        response = client.get('/')
        assert response.status_code == 200
        assert b'Project Bach' in response.data
        assert b'Upload' in response.data
        
        # 2. 上传音频文件
        audio_data = b'\xff\xfb\x90\x00' + b'\x00' * 1024
        
        with patch('src.web_frontend.handlers.audio_upload_handler.AudioUploadHandler.process_upload') as mock_process:
            mock_process.return_value = {
                'status': 'success',
                'processing_id': 'test_proc_123',
                'redirect_url': '/status/test_proc_123'
            }
            
            data = {
                'audio_file': (BytesIO(audio_data), 'test.mp3'),
                'content_type': 'lecture',
                'description': 'Test lecture'
            }
            
            response = client.post('/upload/audio', 
                                 data=data,
                                 content_type='multipart/form-data')
            
            # 验证上传成功并重定向
            assert response.status_code in [200, 302]

    def test_youtube_upload_workflow(self, client):
        """测试YouTube上传工作流"""
        with patch('src.web_frontend.handlers.youtube_handler.YouTubeHandler.process_url') as mock_process:
            mock_process.return_value = {
                'status': 'success',
                'processing_id': 'yt_456'
            }
            
            data = {
                'url': 'https://www.youtube.com/watch?v=test123',
                'description': 'Test YouTube video'
            }
            
            response = client.post('/upload/youtube', data=data)
            assert response.status_code in [200, 302]

    # Models API测试已移至 test_api_endpoints.py
    # 此文件专注于前端页面和模板集成测试

    def test_template_rendering_integration(self, client):
        """测试模板渲染集成"""
        # 测试上传页面模板渲染
        response = client.get('/')
        assert response.status_code == 200
        
        # 检查模板是否正确渲染了配置数据
        assert b'lecture' in response.data or b'Lecture' in response.data

    # ===== 错误处理集成测试 =====
    
    def test_upload_error_handling_integration(self, client):
        """测试上传错误处理集成"""
        # 测试无效文件类型
        invalid_data = {
            'audio_file': (BytesIO(b'not audio'), 'test.txt'),
            'content_type': 'lecture'
        }
        
        response = client.post('/upload/audio', 
                             data=invalid_data,
                             content_type='multipart/form-data')
        
        # 应该处理错误而不是崩溃
        assert response.status_code in [200, 400]

    def test_api_error_handling_integration(self, client):
        """测试API错误处理集成"""
        # 测试不存在的端点
        response = client.get('/api/nonexistent')
        assert response.status_code == 404

    # ===== 安全性集成测试 =====
    
    def test_file_size_limit_integration(self, client):
        """测试文件大小限制集成"""
        # 创建超大文件（模拟）
        large_audio_data = b'\xff\xfb\x90\x00' + b'\x00' * (200 * 1024 * 1024)  # 200MB
        
        data = {
            'audio_file': (BytesIO(large_audio_data), 'large.mp3'),
            'content_type': 'lecture'
        }
        
        # 应该被文件大小限制拒绝
        response = client.post('/upload/audio',
                             data=data,
                             content_type='multipart/form-data')
        
        # Flask应该处理文件大小限制
        assert response.status_code in [400, 413]  # Bad Request or Payload Too Large

    # ===== 配置集成测试 =====
    
    def test_config_manager_integration(self, client):
        """测试配置管理器集成"""
        # 测试配置影响页面渲染
        response = client.get('/')
        assert response.status_code == 200
        
        # 配置的内容类型应该出现在页面中
        content = response.data.decode()
        assert 'lecture' in content.lower() or 'meeting' in content.lower()


class TestTemplateIntegration:
    """模板系统集成测试"""
    
    def test_template_inheritance_works(self):
        """测试模板继承系统工作正常"""
        base_template = Path('./templates/base/shared_base.html')
        web_app_template = Path('./templates/base/web_app_base.html')
        upload_template = Path('./templates/web_app/upload.html')
        
        if all(t.exists() for t in [base_template, web_app_template, upload_template]):
            # 检查继承链
            web_app_content = web_app_template.read_text()
            upload_content = upload_template.read_text()
            
            assert '{% extends "base/shared_base.html" %}' in web_app_content
            assert '{% extends "base/web_app_base.html" %}' in upload_content

    def test_static_assets_integration(self):
        """测试静态资源集成"""
        css_files = [
            Path('./static/css/shared.css'),
            Path('./static/css/web-app.css')
        ]
        
        for css_file in css_files:
            if css_file.exists():
                content = css_file.read_text()
                # CSS文件应该包含实际样式
                assert len(content) > 100
                assert '{' in content and '}' in content


# API测试已迁移到 test_api_endpoints.py
# 此文件专注于前端集成测试


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
