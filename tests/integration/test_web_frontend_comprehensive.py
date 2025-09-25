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
        
        # 创建模拟的MLX模型目录结构
        models_dir = Path(temp_dir) / 'models' / 'mlx-models'
        models_dir.mkdir(parents=True, exist_ok=True)

        # 创建模拟MLX模型文件夹和文件
        test_models = [
            'mlx-community--whisper-tiny-mlx',
            'mlx-community--whisper-large-v3-mlx'
        ]

        for model_name in test_models:
            model_dir = models_dir / model_name
            model_dir.mkdir(exist_ok=True)

            # 创建必要的MLX模型文件
            required_files = ['config.json', 'weights.npz', 'tokenizer.json']
            for file_name in required_files:
                (model_dir / file_name).touch()
        
        # 创建其他必要目录
        directories = [
            'data',
            'watch_folder',
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
        config_content = f"""
# 测试配置文件
paths:
  data_folder: "{temp_dir}/data"
  watch_folder: "{temp_dir}/watch_folder"
  output_folder: "{temp_dir}/data/output"
  input: "{temp_dir}/watch_folder"
  output_private: "{temp_dir}/data/output/private"
  output_public: "{temp_dir}/data/output/public"
  uploads: "{temp_dir}/data/uploads"
  logs: "{temp_dir}/data/logs"
  models: "{temp_dir}/models"

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

spacy:
  model: "zh_core_web_sm"

system:
  debug: false

mlx_whisper:
  default_model: "whisper-tiny-mlx"
  available_models:
    - "mlx-community/whisper-tiny-mlx"
    - "mlx-community/whisper-large-v3-mlx"

diarization:
  provider: "pyannote"
  max_speakers: 6
  min_segment_duration: 1.0

openrouter:
  base_url: "https://openrouter.ai/api/v1"
  models:
    summary: "google/gemma-3n-e4b-it:free"
    mindmap: "google/gemma-3n-e4b-it:free"

github:
  repo_name: "Project_Bach"
  pages:
    enabled: true
    url: "https://sleepycat233.github.io/Project_Bach"

web_frontend:
  app:
    host: "0.0.0.0"
    port: 8080
    debug: false
  upload:
    max_file_size: 1073741824

youtube:
  downloader:
    max_duration: 7200
    min_duration: 60
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
            
            # 1. 获取可用模型目录
            response = flask_app.get('/api/models/available')
            assert response.status_code == 200

            catalog_payload = json.loads(response.data)
            assert catalog_payload.get('success') is True

            catalog = catalog_payload.get('data', {})
            models = catalog.get('models', [])

            # 2. 验证API返回了模型列表
            assert len(models) >= 1, f"Expected at least 1 model in catalog, got {len(models)}"

            # 3. 验证每个模型的基本结构
            for model in models:
                # 验证必需字段
                assert 'value' in model and model['value'], "Model entry must include value"
                assert 'display_name' in model, "Model entry must include display_name"
                assert 'repo' in model and model['repo'].startswith('mlx-community/'), \
                    f"Model repo should use mlx-community namespace: {model.get('repo')}"
                assert isinstance(model.get('is_default'), bool), "Model must include boolean is_default"
                assert isinstance(model.get('downloaded'), bool), "Model must include boolean downloaded status"

                print(f"✅ Found model: {model['display_name']} (value: {model['value']}, downloaded: {model.get('downloaded')})")

            # 4. 验证默认模型设置
            default_model = catalog.get('default_model')
            assert default_model, "Default model should be defined"
            print(f"✅ Default model: {default_model}")

            # 5. 验证有一些已下载的模型（如果有的话）
            downloaded_models = [m for m in models if m.get('downloaded') is True]
            print(f"✅ Downloaded models count: {len(downloaded_models)}")
            if len(downloaded_models) > 0:
                print("✅ At least one model is marked as downloaded")
            else:
                print("ℹ️ No models marked as downloaded (expected in test environment)")

            print(f"✅ Model name integration test passed with {len(models)} total models")
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
            
            response = flask_app.get('/api/config/github-status')
            assert response.status_code == 200
            
            data = json.loads(response.data)

            # 验证统一API响应结构
            assert 'success' in data
            assert data['success'] is True
            assert 'data' in data

            config_status = data['data']
            assert 'configured' in config_status
            
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
            assert 'success' in data and data['success'] is True
            assert 'data' in data
            processing_data = data['data']
            assert 'active_sessions' in processing_data
            
            # 测试内容分类API
            response = flask_app.get('/api/categories')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert 'success' in data and data['success'] is True
            assert 'data' in data
            categories_data = data['data']
            assert isinstance(categories_data, dict)
            assert 'lecture' in categories_data
            assert 'meeting' in categories_data
            # youtube 通过ContentTypeService动态添加，在测试环境中可能不存在
            
            # 验证分类信息结构
            for category_name, category_info in categories_data.items():
                assert 'display_name' in category_info
                assert 'recommendations' in category_info
            
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
            
            # 1. 获取模型目录与推荐数据
            catalog_resp = flask_app.get('/api/models/available')
            recs_resp = flask_app.get('/api/preferences/recommendations/_all')

            assert catalog_resp.status_code == 200
            assert recs_resp.status_code == 200

            catalog_payload = json.loads(catalog_resp.data)
            recs_payload = json.loads(recs_resp.data)

            models = catalog_payload.get('data', {}).get('models', [])
            aggregates = recs_payload.get('data', {})

            assert models, "Model catalog should not be empty"

            global_english = set(aggregates.get('all', {}).get('english', []))
            global_multilingual = set(aggregates.get('all', {}).get('multilingual', []))

            def build_entry(model, english_set, multilingual_set):
                entry = dict(model)
                value = entry['value']
                entry['is_english_recommended'] = value in english_set
                entry['is_multilingual_recommended'] = value in multilingual_set
                if entry['is_english_recommended'] and not entry['is_multilingual_recommended']:
                    entry['language_mode'] = 'english'
                elif entry['is_multilingual_recommended'] and not entry['is_english_recommended']:
                    entry['language_mode'] = 'multilingual'
                else:
                    entry['language_mode'] = 'general'
                return entry

            all_models = [build_entry(model, global_english, global_multilingual) for model in models]

            english_models = [
                entry for entry in all_models
                if entry['language_mode'] in ('english', 'general')
            ]

            multilingual_models = [
                entry for entry in all_models
                if entry['language_mode'] in ('multilingual', 'general')
            ]

            # 验证每种语言模式都有模型
            assert len(english_models) >= 1, "Should have English model options"
            assert len(multilingual_models) >= 1, "Should have multilingual model options"
            
            # 2. 验证模型选择的一致性
            all_model_values = set()
            for language_models in [english_models, multilingual_models]:
                for model in language_models:
                    value = model['value']
                    display_name = model['display_name']

                    assert isinstance(display_name, str) and display_name, "Display name should be non-empty"
                    assert len(display_name) < 120, f"Display name too long: {display_name}"

                    assert value not in all_model_values, f"Duplicate model value: {value}"
                    all_model_values.add(value)

            # 3. 验证模型在实际使用中的一致性
            # 模拟使用其中一个模型值进行上传
            if english_models:
                selected_model = english_models[0]
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
            response = flask_app.get('/api/models/available')
            assert response.status_code == 200
            models_payload = json.loads(response.data)
            catalog = models_payload.get('data', {})
            available_models = [m for m in catalog.get('models', []) if m.get('downloaded')]
            assert len(catalog.get('models', [])) > 0, "Should have models in catalog"
            workflow_steps.append(f"✅ Found {len(catalog.get('models', []))} total models, {len(available_models)} downloaded")
            
            # 3. 用户查看内容分类
            response = flask_app.get('/api/categories')
            assert response.status_code == 200
            categories_payload = json.loads(response.data)
            categories_data = categories_payload.get('data', {})
            workflow_steps.append(f"✅ Found {len(categories_data)} content categories")

            # 4. 用户检查部署状态
            response = flask_app.get('/api/config/github-status')
            assert response.status_code == 200
            status_payload = json.loads(response.data)
            assert 'success' in status_payload
            workflow_steps.append("✅ GitHub Pages status checked")

            # 5. 用户查看处理状态
            response = flask_app.get('/api/status/processing')
            assert response.status_code == 200
            processing_payload = json.loads(response.data)
            processing_data = processing_payload.get('data', {})
            assert 'active_sessions' in processing_data
            workflow_steps.append("✅ Processing status retrieved")
            
            # 6. 模拟文件上传准备（不实际上传，验证表单）
            all_models = catalog.get('models', [])
            if all_models:
                selected_model = all_models[0]['value']
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
