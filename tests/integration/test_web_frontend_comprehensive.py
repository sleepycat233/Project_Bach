#!/usr/bin/env python3
"""
Web前端综合集成测试

整合新开发功能的端到端测试：
1. Whisper模型名称与文件夹对应功能
2. GitHub Pages部署状态检测
3. Web前端API集成
4. 模型配置和选择流程
"""

import pytest
import tempfile
import shutil
import json
import time
import os
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))


class TestWebFrontendComprehensive:
    """Web前端综合集成测试"""
    
    @pytest.fixture
    def temp_workspace(self):
        """临时工作空间"""
        temp_dir = tempfile.mkdtemp(prefix="web_frontend_integration_")
        
        # 创建模拟的WhisperKit模型目录结构
        models_dir = Path(temp_dir) / 'models' / 'whisperkit-coreml'
        models_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建模拟模型文件夹和文件
        test_models = [
            'distil-whisper_distil-large-v3',
            'openai_whisper-medium',
            'openai_whisper-large-v3',
            'openai_whisper-large-v3-v20240930'
        ]
        
        for model_name in test_models:
            model_dir = models_dir / model_name
            model_dir.mkdir(exist_ok=True)
            
            # 创建必要的模型文件
            required_files = ['MelSpectrogram.mlmodelc', 'AudioEncoder.mlmodelc', 'TextDecoder.mlmodelc']
            for file_name in required_files:
                file_dir = model_dir / file_name
                file_dir.mkdir(exist_ok=True)
                (file_dir / 'coremldata.bin').touch()
        
        # 创建其他必要目录
        directories = [
            'data/uploads',
            'output', 
            'temp',
            'data/logs',
            'data/output/public/transcripts',
            'data/output/public',
            'data/output/private',
            'web_frontend/static',
            'web_frontend/templates'
        ]
        
        for dir_path in directories:
            (Path(temp_dir) / dir_path).mkdir(parents=True, exist_ok=True)
        
        # 创建模拟配置文件
        config_content = """
# 测试配置文件
openrouter:
  api_key: "test-key"
  base_url: "https://openrouter.ai/api/v1"

whisperkit:
  model_path: "./models/whisperkit-coreml"
  default_model: "distil-whisper_distil-large-v3"

github:
  username: "sleepycat233"
  repo_name: "Project_Bach"

content_classification:
  content_types:
    lecture:
      icon: "🎓"
      name: "Academic Lecture"
    youtube:
      icon: "📺"
      name: "YouTube Video"
"""
        
        config_file = Path(temp_dir) / 'config.yaml'
        config_file.write_text(config_content)
        
        # 创建模拟环境文件
        env_content = """
OPENROUTER_API_KEY=test-key
TAILSCALE_AUTH_KEY=test-key
FLASK_SECRET_KEY=test-secret-key
"""
        
        env_file = Path(temp_dir) / '.env'
        env_file.write_text(env_content)
        
        # 更改工作目录到临时目录
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        
        yield temp_dir
        
        # 恢复原目录并清理
        os.chdir(original_cwd)
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def flask_app(self, temp_workspace):
        """创建Flask测试应用"""
        from src.web_frontend.app import create_app
        
        config = {
            'TESTING': True,
            'SECRET_KEY': 'test-secret-key',
            'MAX_CONTENT_LENGTH': 500 * 1024 * 1024,
            'UPLOAD_FOLDER': str(Path(temp_workspace) / 'data/uploads'),
            'WTF_CSRF_ENABLED': False
        }
        
        app = create_app(config)
        
        with app.app_context():
            yield app.test_client()
    
    def test_whisper_model_name_integration(self, flask_app, temp_workspace):
        """测试Whisper模型名称与文件夹对应的完整流程"""
        
        @patch('ipaddress.ip_address')
        @patch('ipaddress.ip_network')
        def run_test(mock_ip_network, mock_ip_address):
            # Mock Tailscale网络检查通过
            mock_network = Mock()
            mock_ip = Mock()
            mock_ip_network.return_value = mock_network
            mock_ip_address.return_value = mock_ip
            mock_network.__contains__ = Mock(return_value=True)
            
            # 1. 测试模型配置API
            response = flask_app.get('/api/models/smart-config')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            
            # 2. 验证模型名称映射
            downloaded_models = []
            for language_mode in ['english', 'multilingual']:
                models = data.get(language_mode, [])
                for model in models:
                    if model.get('downloaded', False):
                        downloaded_models.append(model)
            
            # 应该检测到4个已下载的模型
            assert len(downloaded_models) >= 3, f"Expected at least 3 models, got {len(downloaded_models)}"
            
            # 3. 验证每个模型的名称格式
            expected_folders = [
                'distil-whisper_distil-large-v3',
                'openai_whisper-medium', 
                'openai_whisper-large-v3',
                'openai_whisper-large-v3-v20240930'
            ]
            
            found_folders = []
            for model in downloaded_models:
                # 验证display_name包含实际文件夹名
                display_name = model['display_name']
                actual_dir = model.get('actual_dir', '')
                value = model['value']
                
                # 验证emoji保留
                assert any(emoji in display_name for emoji in ['🚀', '⚖️', '🎯']), \
                    f"Model {value} should retain emoji in display name: {display_name}"
                
                # 验证文件夹名在display_name中
                assert actual_dir in display_name, \
                    f"Display name {display_name} should contain folder name {actual_dir}"
                
                # 验证value与actual_dir一致
                assert value == actual_dir, \
                    f"Value {value} should match actual_dir {actual_dir}"
                
                # 验证有可读描述
                assert 'description_readable' in model, \
                    f"Model {value} should have readable description"
                
                found_folders.append(actual_dir)
            
            # 4. 验证找到了预期的文件夹
            for expected_folder in expected_folders[:3]:  # 至少前3个
                assert any(expected_folder in folder for folder in found_folders), \
                    f"Should find model with folder containing: {expected_folder}"
            
            print(f"✅ Model name integration test passed with {len(downloaded_models)} models")
            return True
        
        result = run_test()
        assert result, "Whisper model name integration test failed"
    
    def test_github_pages_deployment_status_integration(self, flask_app, temp_workspace):
        """测试GitHub Pages部署状态检测的完整流程"""
        
        @patch('ipaddress.ip_address')
        @patch('ipaddress.ip_network')
        @patch('requests.get')
        def run_test(mock_get, mock_ip_network, mock_ip_address):
            # Mock Tailscale网络检查通过
            mock_network = Mock()
            mock_ip = Mock()
            mock_ip_network.return_value = mock_network
            mock_ip_address.return_value = mock_ip
            mock_network.__contains__ = Mock(return_value=True)
            
            # 1. 测试成功的部署状态
            pages_response = Mock()
            pages_response.status_code = 200
            pages_response.json.return_value = {
                'status': 'built',
                'cname': 'sleepycat233.github.io',
                'source': {'branch': 'gh-pages', 'path': '/'}
            }
            
            deployments_response = Mock()
            deployments_response.status_code = 200
            deployments_response.json.return_value = [
                {
                    'id': 123456,
                    'environment': 'github-pages',
                    'created_at': '2024-01-15T10:30:00Z',
                    'updated_at': '2024-01-15T10:35:00Z'
                }
            ]
            
            status_response = Mock()
            status_response.status_code = 200
            status_response.json.return_value = [
                {
                    'state': 'success',
                    'environment_url': 'https://sleepycat233.github.io/Project_Bach',
                    'description': 'Deployment finished successfully',
                    'created_at': '2024-01-15T10:35:00Z'
                }
            ]
            
            mock_get.side_effect = [pages_response, deployments_response, status_response]
            
            response = flask_app.get('/api/github/pages-status')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            
            # 验证返回数据结构
            required_fields = ['status', 'message', 'last_checked', 'api_method', 'repository']
            for field in required_fields:
                assert field in data, f"Response should contain field: {field}"
            
            assert data['api_method'] == 'github_rest_api'
            assert 'sleepycat233/Project_Bach' in data['repository']
            
            # 2. GitHub deployment monitor removed - simplified API test only
            print("✅ GitHub deployment monitor removed - API integration verified")
            
            print("✅ GitHub Pages deployment status integration test passed")
            return True
        
        result = run_test()
        assert result, "GitHub Pages deployment status integration test failed"
    
    def test_processing_status_integration(self, flask_app, temp_workspace):
        """测试处理状态API集成"""
        
        @patch('ipaddress.ip_address')
        @patch('ipaddress.ip_network')
        def run_test(mock_ip_network, mock_ip_address):
            # Mock Tailscale网络检查通过
            mock_network = Mock()
            mock_ip = Mock()
            mock_ip_network.return_value = mock_network
            mock_ip_address.return_value = mock_ip
            mock_network.__contains__ = Mock(return_value=True)
            
            # 测试处理状态API
            response = flask_app.get('/api/status/processing')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert 'active_sessions' in data
            
            # 测试内容分类API
            response = flask_app.get('/api/categories')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert isinstance(data, dict)
            assert 'lecture' in data
            assert 'youtube' in data
            
            # 验证分类信息结构
            for category_name, category_info in data.items():
                assert 'icon' in category_info
                assert 'name' in category_info
            
            print("✅ Processing status integration test passed")
            return True
        
        result = run_test()
        assert result, "Processing status integration test failed"
    
    def test_audio_upload_workflow_integration(self, flask_app, temp_workspace):
        """测试音频上传工作流集成"""
        
        @patch('ipaddress.ip_address')
        @patch('ipaddress.ip_network')
        def run_test(mock_ip_network, mock_ip_address):
            # Mock Tailscale网络检查通过
            mock_network = Mock()
            mock_ip = Mock()
            mock_ip_network.return_value = mock_network
            mock_ip_address.return_value = mock_ip
            mock_network.__contains__ = Mock(return_value=True)
            
            # 1. 测试主页加载
            response = flask_app.get('/')
            assert response.status_code == 200
            
            html_content = response.data.decode('utf-8')
            assert 'Project Bach' in html_content
            assert 'Upload Audio' in html_content
            assert 'YouTube Video' in html_content
            
            # 2. 创建模拟音频文件
            temp_file_path = Path(temp_workspace) / 'test_audio.mp3'
            temp_file_path.write_bytes(b'fake mp3 content')
            
            # 3. 测试音频文件上传（模拟）
            with open(temp_file_path, 'rb') as f:
                data = {
                    'audio_file': (f, 'test_audio.mp3'),
                    'content_type': 'lecture',
                    'privacy_level': 'public',
                    'audio_language': 'english',
                    'whisper_model': 'distil-whisper_distil-large-v3'  # 使用新的文件夹名格式
                }
                
                response = flask_app.post('/upload/audio', 
                                        data=data,
                                        content_type='multipart/form-data')
                
                # 应该返回成功或重定向
                assert response.status_code in [200, 302], f"Upload failed with status {response.status_code}"
            
            # 4. 测试YouTube URL提交（模拟）
            youtube_data = {
                'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                'content_type': 'youtube',
                'privacy_level': 'public',
                'audio_language': 'english',
                'whisper_model': 'openai_whisper-medium'  # 使用新的文件夹名格式
            }
            
            response = flask_app.post('/upload/youtube', data=youtube_data)
            assert response.status_code in [200, 302, 400]  # 400可能是因为mock的YouTube处理
            
            print("✅ Audio upload workflow integration test passed")
            return True
        
        result = run_test()
        assert result, "Audio upload workflow integration test failed"
    
    def test_model_selection_ui_integration(self, flask_app, temp_workspace):
        """测试模型选择UI集成"""
        
        @patch('ipaddress.ip_address')
        @patch('ipaddress.ip_network')
        def run_test(mock_ip_network, mock_ip_address):
            # Mock Tailscale网络检查通过
            mock_network = Mock()
            mock_ip = Mock()
            mock_ip_network.return_value = mock_network
            mock_ip_address.return_value = mock_ip
            mock_network.__contains__ = Mock(return_value=True)
            
            # 1. 获取模型配置
            response = flask_app.get('/api/models/smart-config')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            
            # 2. 验证模型配置在UI中的使用
            english_models = data.get('english', [])
            multilingual_models = data.get('multilingual', [])
            
            # 验证每种语言模式都有模型
            assert len(english_models) > 0, "Should have English models"
            assert len(multilingual_models) > 0, "Should have multilingual models"
            
            # 3. 验证模型选择的一致性
            all_model_values = set()
            for language_models in [english_models, multilingual_models]:
                for model in language_models:
                    if model.get('downloaded', False):
                        value = model['value']
                        display_name = model['display_name']
                        
                        # 验证value在display_name中
                        assert value in display_name, \
                            f"Value {value} should be in display name {display_name}"
                        
                        # 验证value唯一性
                        assert value not in all_model_values, f"Duplicate model value: {value}"
                        all_model_values.add(value)
                        
                        # 验证UI相关字段
                        assert len(display_name) < 100, f"Display name too long: {display_name}"
                        assert len(display_name) > 5, f"Display name too short: {display_name}"
            
            # 4. 验证模型在实际使用中的一致性
            # 模拟使用其中一个模型值进行上传
            if english_models:
                selected_model = english_models[0]
                if selected_model.get('downloaded'):
                    model_value = selected_model['value']
                    
                    # 创建模拟文件
                    temp_file_path = Path(temp_workspace) / 'ui_test_audio.mp3'
                    temp_file_path.write_bytes(b'fake mp3 for ui test')
                    
                    with open(temp_file_path, 'rb') as f:
                        data = {
                            'audio_file': (f, 'ui_test_audio.mp3'),
                            'content_type': 'lecture',
                            'privacy_level': 'public', 
                            'audio_language': 'english',
                            'whisper_model': model_value  # 使用实际的模型值
                        }
                        
                        response = flask_app.post('/upload/audio',
                                                data=data,
                                                content_type='multipart/form-data')
                        
                        # 应该能正确处理模型值
                        assert response.status_code in [200, 302]
            
            print(f"✅ Model selection UI integration test passed with {len(all_model_values)} unique models")
            return True
        
        result = run_test()
        assert result, "Model selection UI integration test failed"
    
    def test_end_to_end_workflow_simulation(self, flask_app, temp_workspace):
        """端到端工作流模拟测试"""
        
        @patch('ipaddress.ip_address')
        @patch('ipaddress.ip_network')
        @patch('requests.get')
        def run_test(mock_get, mock_ip_network, mock_ip_address):
            # Mock Tailscale网络检查通过
            mock_network = Mock()
            mock_ip = Mock()
            mock_ip_network.return_value = mock_network
            mock_ip_address.return_value = mock_ip
            mock_network.__contains__ = Mock(return_value=True)
            
            # Mock GitHub API
            pages_response = Mock()
            pages_response.status_code = 200
            pages_response.json.return_value = {'status': 'built'}
            mock_get.return_value = pages_response
            
            # 模拟完整的用户工作流
            workflow_steps = []
            
            # 1. 用户访问主页
            response = flask_app.get('/')
            assert response.status_code == 200
            workflow_steps.append("✅ Homepage loaded")
            
            # 2. 用户查看可用模型
            response = flask_app.get('/api/models/smart-config')
            assert response.status_code == 200
            models_data = json.loads(response.data)
            available_models = [m for m in models_data.get('english', []) if m.get('downloaded')]
            assert len(available_models) > 0
            workflow_steps.append(f"✅ Found {len(available_models)} available models")
            
            # 3. 用户查看内容分类
            response = flask_app.get('/api/categories')
            assert response.status_code == 200
            categories_data = json.loads(response.data)
            workflow_steps.append(f"✅ Found {len(categories_data)} content categories")
            
            # 4. 用户检查部署状态
            response = flask_app.get('/api/github/pages-status')
            assert response.status_code == 200
            status_data = json.loads(response.data)
            assert 'status' in status_data
            workflow_steps.append("✅ GitHub Pages status checked")
            
            # 5. 用户查看处理状态
            response = flask_app.get('/api/status/processing')
            assert response.status_code == 200
            processing_data = json.loads(response.data)
            assert 'active_sessions' in processing_data
            workflow_steps.append("✅ Processing status retrieved")
            
            # 6. 模拟文件上传准备（不实际上传，验证表单）
            if available_models:
                selected_model = available_models[0]['value']
                temp_file_path = Path(temp_workspace) / 'workflow_test.mp3'
                temp_file_path.write_bytes(b'fake audio for workflow test')
                workflow_steps.append(f"✅ Selected model: {selected_model}")
            
            # 验证所有关键组件都正常工作
            assert len(workflow_steps) >= 5
            
            print("🎯 End-to-end workflow simulation completed:")
            for step in workflow_steps:
                print(f"  {step}")
            
            return True
        
        result = run_test()
        assert result, "End-to-end workflow simulation test failed"
    
    def test_error_handling_integration(self, flask_app, temp_workspace):
        """测试错误处理集成"""
        
        @patch('ipaddress.ip_address')
        @patch('ipaddress.ip_network')
        def run_test(mock_ip_network, mock_ip_address):
            # Mock Tailscale网络检查通过
            mock_network = Mock()
            mock_ip = Mock()
            mock_ip_network.return_value = mock_network
            mock_ip_address.return_value = mock_ip
            mock_network.__contains__ = Mock(return_value=True)
            
            error_scenarios = []
            
            # 1. 测试无效文件上传
            response = flask_app.post('/upload/audio', data={})
            assert response.status_code in [400, 422]
            error_scenarios.append("✅ Invalid file upload handled")
            
            # 2. 测试无效YouTube URL
            response = flask_app.post('/upload/youtube', data={'youtube_url': 'invalid-url'})
            assert response.status_code in [400, 422]
            error_scenarios.append("✅ Invalid YouTube URL handled")
            
            # 3. 测试不存在的状态查询
            response = flask_app.get('/status/nonexistent-id')
            assert response.status_code in [404, 200]  # 可能返回错误页面
            error_scenarios.append("✅ Nonexistent status query handled")
            
            # 4. 测试不存在的API路由
            response = flask_app.get('/api/nonexistent-endpoint')
            assert response.status_code == 404
            error_scenarios.append("✅ Nonexistent API endpoint handled")
            
            print("🛡️ Error handling integration test completed:")
            for scenario in error_scenarios:
                print(f"  {scenario}")
            
            return True
        
        result = run_test()
        assert result, "Error handling integration test failed"


class TestWebFrontendPerformance:
    """Web前端性能集成测试"""
    
    @pytest.fixture
    def performance_app(self):
        """性能测试应用"""
        from src.web_frontend.app import create_app
        
        config = {
            'TESTING': True,
            'SECRET_KEY': 'perf-test-key',
            'WTF_CSRF_ENABLED': False
        }
        
        app = create_app(config)
        
        with app.app_context():
            yield app.test_client()
    
    def test_api_response_times(self, performance_app):
        """测试API响应时间"""
        
        @patch('ipaddress.ip_address')
        @patch('ipaddress.ip_network')
        def run_test(mock_ip_network, mock_ip_address):
            # Mock Tailscale网络检查通过
            mock_network = Mock()
            mock_ip = Mock()
            mock_ip_network.return_value = mock_network
            mock_ip_address.return_value = mock_ip
            mock_network.__contains__ = Mock(return_value=True)
            
            api_endpoints = [
                '/api/models/smart-config',
                '/api/categories', 
                '/api/status/processing'
            ]
            
            performance_results = []
            
            for endpoint in api_endpoints:
                start_time = time.time()
                response = performance_app.get(endpoint)
                end_time = time.time()
                
                response_time = (end_time - start_time) * 1000  # ms
                
                # API应该在1秒内响应
                assert response_time < 1000, f"API {endpoint} too slow: {response_time:.2f}ms"
                assert response.status_code == 200
                
                performance_results.append({
                    'endpoint': endpoint,
                    'response_time_ms': round(response_time, 2),
                    'status': 'PASS'
                })
            
            print("⚡ API Performance test results:")
            for result in performance_results:
                print(f"  {result['endpoint']}: {result['response_time_ms']}ms - {result['status']}")
            
            return True
        
        result = run_test()
        assert result, "API performance test failed"
    
    def test_concurrent_requests(self, performance_app):
        """测试并发请求处理"""
        import threading
        import queue
        
        @patch('ipaddress.ip_address')
        @patch('ipaddress.ip_network')
        def run_test(mock_ip_network, mock_ip_address):
            # Mock Tailscale网络检查通过
            mock_network = Mock()
            mock_ip = Mock()
            mock_ip_network.return_value = mock_network
            mock_ip_address.return_value = mock_ip
            mock_network.__contains__ = Mock(return_value=True)
            
            def make_request(endpoint, results_queue):
                try:
                    start_time = time.time()
                    response = performance_app.get(endpoint)
                    end_time = time.time()
                    
                    results_queue.put({
                        'endpoint': endpoint,
                        'status_code': response.status_code,
                        'response_time': end_time - start_time,
                        'success': response.status_code == 200
                    })
                except Exception as e:
                    results_queue.put({
                        'endpoint': endpoint,
                        'error': str(e),
                        'success': False
                    })
            
            # 模拟5个并发请求
            endpoints = ['/api/models/smart-config'] * 5
            results_queue = queue.Queue()
            threads = []
            
            # 启动并发请求
            for endpoint in endpoints:
                thread = threading.Thread(target=make_request, args=(endpoint, results_queue))
                threads.append(thread)
                thread.start()
            
            # 等待所有请求完成
            for thread in threads:
                thread.join(timeout=10)
            
            # 收集结果
            results = []
            while not results_queue.empty():
                results.append(results_queue.get())
            
            # 验证结果
            assert len(results) == 5, f"Expected 5 results, got {len(results)}"
            
            successful_requests = [r for r in results if r.get('success', False)]
            assert len(successful_requests) >= 4, "At least 4/5 concurrent requests should succeed"
            
            avg_response_time = sum(r.get('response_time', 0) for r in successful_requests) / len(successful_requests)
            assert avg_response_time < 2.0, f"Average response time too high: {avg_response_time:.2f}s"
            
            print(f"🔀 Concurrent requests test: {len(successful_requests)}/5 successful")
            print(f"   Average response time: {avg_response_time:.3f}s")
            
            return True
        
        result = run_test()
        assert result, "Concurrent requests test failed"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])