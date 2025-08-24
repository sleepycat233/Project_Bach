#!/usr/bin/env python3
"""
Phase 6 Flask Web应用 - 主应用文件

提供Project Bach的Web界面，支持：
- 音频文件上传和分类选择
- YouTube URL提交处理
- 处理状态查询API
- Tailscale网络安全保护
"""

import os
import ipaddress
from pathlib import Path
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import logging

# 导入处理器和服务
from .handlers.audio_upload_handler import AudioUploadHandler
from .handlers.youtube_handler import YouTubeHandler
from ..core.processing_service import get_processing_service
from ..utils.config import ConfigManager

logger = logging.getLogger(__name__)


def create_app(config=None):
    """创建Flask应用工厂函数"""
    app = Flask(__name__)
    
    # 默认配置
    app.config.update({
        'SECRET_KEY': os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production'),
        'MAX_CONTENT_LENGTH': 500 * 1024 * 1024,  # 500MB
        'UPLOAD_FOLDER': '/tmp/project_bach_uploads',
        'ALLOWED_EXTENSIONS': {'.mp3', '.wav', '.m4a', '.mp4', '.flac', '.aac', '.ogg'},
        'TAILSCALE_NETWORK': '100.64.0.0/10',
        'RATE_LIMIT_PER_MINUTE': 60,
        'WTF_CSRF_ENABLED': True
    })
    
    # 应用测试配置
    if config:
        app.config.update(config)
    
    # 创建上传目录
    upload_dir = Path(app.config['UPLOAD_FOLDER'])
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # 初始化配置管理器
    try:
        config_manager = ConfigManager()
        app.config['CONFIG_MANAGER'] = config_manager
    except Exception as e:
        logger.warning(f"Failed to load config manager: {e}")
        app.config['CONFIG_MANAGER'] = None
    
    # 简单的请求频率限制（生产环境需要flask_limiter）
    app.config['SIMPLE_RATE_LIMIT'] = True
    
    # 初始化处理服务
    app.config['AUDIO_HANDLER'] = AudioUploadHandler(config_manager)
    app.config['YOUTUBE_HANDLER'] = YouTubeHandler(config_manager)
    app.config['PROCESSING_SERVICE'] = get_processing_service()
    
    # Tailscale安全中间件
    @app.before_request
    def security_middleware():
        if app.config.get('TESTING'):
            return  # 测试环境跳过安全检查
            
        remote_ip = request.environ.get('REMOTE_ADDR', request.remote_addr)
        
        try:
            tailscale_network = ipaddress.ip_network(app.config['TAILSCALE_NETWORK'])
            client_ip = ipaddress.ip_address(remote_ip)
            
            if client_ip not in tailscale_network:
                logger.warning(f"Access denied for IP: {remote_ip}")
                return jsonify({
                    'error': 'Access denied',
                    'message': 'This service is only available within Tailscale network'
                }), 403
        except Exception as e:
            logger.error(f"Security middleware error: {e}")
            return jsonify({'error': 'Security check failed'}), 500
    
    # 主页路由
    @app.route('/')
    def index():
        """主页 - 显示上传界面和分类选项"""
        config_manager = app.config.get('CONFIG_MANAGER')
        
        # 获取内容类型配置
        if config_manager:
            content_types = config_manager.get_nested_config('content_classification', 'content_types') or {}
        else:
            content_types = {
                'lecture': {'icon': '🎓', 'display_name': 'Academic Lecture'},
                'meeting': {'icon': '🏢', 'display_name': 'Meeting Recording'},
                'others': {'icon': '📄', 'display_name': 'Others'}
            }
        
        # 获取完整配置用于模板
        config_dict = config_manager.get_full_config() if config_manager else {}
        
        return render_template('upload.html', 
                               content_types=content_types,
                               config=config_dict)
    
    # 音频上传路由
    @app.route('/upload/audio', methods=['POST'])
    def upload_audio():
        """处理音频文件上传"""
        try:
            # 检查文件是否存在
            if 'audio_file' not in request.files:
                return jsonify({'error': 'No audio file provided'}), 400
            
            file = request.files['audio_file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            # 检查content_type
            content_type = request.form.get('content_type')
            if not content_type:
                return jsonify({'error': 'content_type is required'}), 400
            
            # 验证文件类型
            if not allowed_file(file.filename, app.config['ALLOWED_EXTENSIONS']):
                return jsonify({'error': 'Invalid file type'}), 400
            
            # 获取隐私级别
            privacy_level = request.form.get('privacy_level', 'public')
            
            # 处理子分类信息
            subcategory = request.form.get('subcategory', '')
            custom_subcategory = request.form.get('custom_subcategory', '')
            audio_language = request.form.get('audio_language', 'english')
            
            # 处理模型选择
            whisper_model = request.form.get('whisper_model', 'large-v3|distil')
            model_parts = whisper_model.split('|')
            model_name = model_parts[0] if len(model_parts) > 0 else 'large-v3'
            model_prefix = model_parts[1] if len(model_parts) > 1 else 'distil'
            
            # 如果选择了other，使用自定义子分类名
            if subcategory == 'other' and custom_subcategory:
                subcategory = custom_subcategory
            
            # 处理上传
            handler = app.config['AUDIO_HANDLER']
            result = handler.process_upload(
                file=file,
                content_type=content_type,
                privacy_level=privacy_level,
                metadata={
                    'subcategory': subcategory,
                    'audio_language': audio_language,
                    'description': request.form.get('description', ''),
                    'whisper_model': model_name,
                    'model_prefix': model_prefix
                }
            )
            
            if result['status'] == 'success':
                flash('Audio file uploaded successfully!', 'success')
                return redirect(url_for('processing_status', 
                               processing_id=result['processing_id']))
            else:
                return jsonify({'error': result.get('message', 'Upload failed')}), 400
                
        except RequestEntityTooLarge:
            return jsonify({'error': 'File too large'}), 413
        except Exception as e:
            logger.error(f"Audio upload error: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    # YouTube URL提交路由
    @app.route('/upload/youtube', methods=['POST'])
    def upload_youtube():
        """处理YouTube URL提交"""
        try:
            youtube_url = request.form.get('youtube_url')
            if not youtube_url:
                return jsonify({'error': 'YouTube URL is required'}), 400
            
            content_type = 'youtube'  # YouTube视频固定为youtube类型
            
            # 验证YouTube URL
            if not is_valid_youtube_url(youtube_url):
                return jsonify({'error': 'Invalid YouTube URL'}), 400
            
            # 获取隐私级别
            privacy_level = request.form.get('privacy_level', 'public')
            
            # 处理YouTube URL
            handler = app.config['YOUTUBE_HANDLER']
            result = handler.process_url(
                url=youtube_url,
                content_type=content_type,
                metadata={
                    'tags': request.form.get('tags', ''),
                    'description': request.form.get('description', '')
                },
                privacy_level=privacy_level
            )
            
            if result['status'] == 'success':
                flash('YouTube video added to processing queue!', 'success')
                return redirect(url_for('processing_status', 
                               processing_id=result['processing_id']))
            else:
                return jsonify({'error': result.get('message', 'Processing failed')}), 400
                
        except Exception as e:
            logger.error(f"YouTube upload error: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    # 处理状态页面
    @app.route('/status/<processing_id>')
    def processing_status(processing_id):
        """显示处理状态页面"""
        service = app.config['PROCESSING_SERVICE']
        status = service.get_status(processing_id)
        
        if status is None:
            return render_template('error.html',
                                 error_code=404,
                                 error_message=f"Processing session not found: {processing_id}"), 404
        
        return render_template('status.html', 
                             processing_id=processing_id,
                             status=status)
    
    # API路由
    @app.route('/api/status/processing')
    def api_processing_status():
        """获取所有活跃处理状态API"""
        try:
            service = app.config['PROCESSING_SERVICE']
            active_sessions = service.list_active_sessions()
            return jsonify({'active_sessions': active_sessions})
        except Exception as e:
            logger.error(f"Processing status API error: {e}")
            return jsonify({'error': 'Failed to get status'}), 500
    
    @app.route('/api/status/<processing_id>')
    def api_single_status(processing_id):
        """获取单个处理状态API"""
        try:
            service = app.config['PROCESSING_SERVICE']
            status = service.get_status(processing_id)
            
            if status is None:
                return jsonify({'error': 'Processing session not found'}), 404
                
            return jsonify(status)
        except Exception as e:
            logger.error(f"Single status API error: {e}")
            return jsonify({'error': 'Failed to get status'}), 500
    
    @app.route('/api/categories')
    def api_categories():
        """内容分类API"""
        categories = {
            'lecture': {'icon': '🎓', 'name': 'Academic Lecture'},
            'youtube': {'icon': '📺', 'name': 'YouTube Video'}
        }
        return jsonify(categories)
    
    @app.route('/api/results/recent')
    def api_recent_results():
        """最近结果API"""
        try:
            from ..storage.result_storage import ResultStorage
            
            limit = request.args.get('limit', 10, type=int)
            storage = ResultStorage()
            results = storage.get_recent_results(limit=limit)
            
            return jsonify(results)
        except Exception as e:
            logger.error(f"Recent results API error: {e}")
            return jsonify({'error': 'Failed to get recent results'}), 500

    @app.route('/api/github/pages-status')
    def api_github_pages_status():
        """获取GitHub Pages部署状态API - 使用真实GitHub REST API"""
        try:
            import requests
            import os
            from datetime import datetime
            
            # 从配置获取GitHub信息
            config_manager = app.config.get('CONFIG_MANAGER')
            if not config_manager:
                return jsonify({
                    'status': 'error',
                    'message': 'Configuration not available',
                    'last_checked': datetime.now().isoformat()
                }), 500
                
            config = config_manager.config
            github_config = config.get('github', {})
            
            # GitHub API参数
            owner = github_config.get('username', 'sleepycat233')
            repo = github_config.get('repo_name', 'Project_Bach')
            
            # 获取GitHub token (可选，用于提高API限制)
            github_token = os.environ.get('GITHUB_TOKEN') or github_config.get('token')
            
            headers = {
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28'
            }
            
            if github_token:
                headers['Authorization'] = f'Bearer {github_token}'
            
            # 1. 首先检查Pages是否已启用
            pages_url = f'https://api.github.com/repos/{owner}/{repo}/pages'
            pages_response = requests.get(pages_url, headers=headers, timeout=10)
            
            result = {
                'status': 'unknown',
                'message': 'Unable to determine status',
                'last_checked': datetime.now().isoformat(),
                'api_method': 'github_rest_api',
                'repository': f'{owner}/{repo}'
            }
            
            if pages_response.status_code == 200:
                pages_data = pages_response.json()
                pages_status = pages_data.get('status', 'unknown')
                
                # 2. 获取Pages部署列表
                deployments_url = f'https://api.github.com/repos/{owner}/{repo}/deployments'
                deploy_params = {'environment': 'github-pages', 'per_page': 5}
                deployments_response = requests.get(deployments_url, headers=headers, params=deploy_params, timeout=10)
                
                if deployments_response.status_code == 200:
                    deployments = deployments_response.json()
                    
                    if deployments:
                        latest_deployment = deployments[0]
                        deployment_id = latest_deployment['id']
                        
                        # 3. 获取最新部署的状态
                        status_url = f'https://api.github.com/repos/{owner}/{repo}/deployments/{deployment_id}/statuses'
                        status_response = requests.get(status_url, headers=headers, timeout=10)
                        
                        if status_response.status_code == 200:
                            statuses = status_response.json()
                            if statuses:
                                latest_status = statuses[0]
                                deployment_state = latest_status.get('state', 'unknown')
                                
                                # 映射GitHub状态到我们的状态
                                if deployment_state == 'success':
                                    result['status'] = 'deployed'
                                    result['message'] = f'GitHub Pages successfully deployed at {pages_data.get("html_url", "N/A")}'
                                elif deployment_state in ['error', 'failure']:
                                    result['status'] = 'error'
                                    result['message'] = f'Deployment failed: {latest_status.get("description", "Unknown error")}'
                                elif deployment_state in ['pending', 'in_progress']:
                                    result['status'] = 'deploying'
                                    result['message'] = 'Deployment in progress'
                                else:
                                    result['status'] = 'unknown'
                                    result['message'] = f'Deployment state: {deployment_state}'
                                
                                # 添加详细信息
                                result['deployment_info'] = {
                                    'id': deployment_id,
                                    'state': deployment_state,
                                    'description': latest_status.get('description', ''),
                                    'created_at': latest_deployment.get('created_at', ''),
                                    'updated_at': latest_status.get('updated_at', ''),
                                    'environment_url': latest_status.get('environment_url', pages_data.get('html_url', ''))
                                }
                            else:
                                result['status'] = 'no_deployments'
                                result['message'] = 'No deployment statuses found'
                        else:
                            result['status'] = 'api_error'
                            result['message'] = f'Failed to get deployment status: {status_response.status_code}'
                    else:
                        result['status'] = 'no_deployments'
                        result['message'] = 'No GitHub Pages deployments found'
                else:
                    result['status'] = 'api_error'
                    result['message'] = f'Failed to get deployments: {deployments_response.status_code}'
                    
                # 添加Pages基本信息
                result['pages_info'] = {
                    'status': pages_status,
                    'html_url': pages_data.get('html_url', ''),
                    'source': pages_data.get('source', {}),
                    'https_enforced': pages_data.get('https_enforced', False)
                }
                
            elif pages_response.status_code == 404:
                result['status'] = 'not_enabled'
                result['message'] = 'GitHub Pages is not enabled for this repository'
            else:
                result['status'] = 'api_error'  
                result['message'] = f'GitHub API error: {pages_response.status_code}'
            
            return jsonify(result)
            
        except requests.exceptions.Timeout:
            return jsonify({
                'status': 'timeout',
                'message': 'GitHub API request timed out',
                'last_checked': datetime.now().isoformat()
            }), 408
        except requests.exceptions.RequestException as e:
            return jsonify({
                'status': 'network_error',
                'message': f'Network error: {str(e)}',
                'last_checked': datetime.now().isoformat()
            }), 503
        except Exception as e:
            logger.error(f"GitHub Pages status API error: {e}")
            return jsonify({
                'status': 'error',
                'message': 'Internal server error',
                'last_checked': datetime.now().isoformat()
            }), 500

    @app.route('/api/youtube/metadata')
    def api_youtube_metadata():
        """获取YouTube视频元数据API"""
        try:
            url = request.args.get('url')
            if not url:
                return jsonify({'error': 'URL parameter is required'}), 400
                
            # 使用YouTube处理器获取视频元数据
            handler = app.config.get('YOUTUBE_HANDLER')
            if not handler:
                # 创建临时YouTube处理器实例来获取元数据
                from ..web_frontend.handlers.youtube_handler import YouTubeHandler
                from ..utils.config import ConfigManager
                config_manager = ConfigManager()
                config = config_manager.load_config()
                handler = YouTubeHandler(config)
            
            metadata = handler.get_video_metadata(url)
            
            if metadata:
                return jsonify({
                    'title': metadata.get('title', ''),
                    'description': metadata.get('description', ''),
                    'duration': metadata.get('duration', ''),
                    'uploader': metadata.get('uploader', ''),
                    'tags': metadata.get('tags', [])
                })
            else:
                return jsonify({'error': 'Failed to fetch video metadata'}), 400
                
        except Exception as e:
            logger.error(f"YouTube metadata API error: {e}")
            return jsonify({'error': 'Failed to get video metadata'}), 500
    
    @app.route('/api/models/check')
    def api_check_model():
        """检查特定模型是否存在API"""
        try:
            from pathlib import Path
            
            model = request.args.get('model', 'large-v3')
            prefix = request.args.get('prefix', 'distil')
            
            # 构建模型路径 - 修复distil模型路径格式
            models_path = Path('./models/whisperkit-coreml')
            if prefix == 'distil' and model == 'large-v3':
                # 特殊处理 distil-large-v3 模型的路径格式
                model_dir = models_path / "distil-whisper_distil-large-v3"
            else:
                model_dir = models_path / f"{prefix}_whisper-{model}"
            
            exists = model_dir.exists()
            
            if exists:
                # 检查关键模型文件是否存在
                required_files = ['MelSpectrogram.mlmodelc', 'AudioEncoder.mlmodelc', 'TextDecoder.mlmodelc']
                missing_files = []
                
                for file_name in required_files:
                    if not (model_dir / file_name).exists():
                        missing_files.append(file_name)
                
                if missing_files:
                    return jsonify({
                        'exists': False,
                        'status': 'incomplete',
                        'message': f'Model exists but missing files: {", ".join(missing_files)}',
                        'path': str(model_dir)
                    })
                else:
                    return jsonify({
                        'exists': True,
                        'status': 'ready',
                        'message': 'Model is ready to use',
                        'path': str(model_dir)
                    })
            else:
                return jsonify({
                    'exists': False,
                    'status': 'missing',
                    'message': 'Model will be downloaded automatically on first use',
                    'path': str(model_dir)
                })
                
        except Exception as e:
            logger.error(f"Model check API error: {e}")
            return jsonify({'error': 'Failed to check model status'}), 500

    @app.route('/api/models/available')
    def api_available_models():
        """获取可用模型信息API - 完全从配置文件和本地文件读取"""
        try:
            from pathlib import Path
            from src.utils.config import ConfigManager
            import os
            import json
            
            # 从配置文件读取providers信息
            config_manager = ConfigManager()
            config = config_manager.get_full_config()
            providers = config.get('whisperkit', {}).get('providers', {})
            
            available_models = {
                'local': [],
                'api': []
            }
            
            # 处理本地模型
            local_provider = providers.get('local', {})
            if local_provider.get('enabled', False):
                models_path = Path(local_provider.get('path', './models/whisperkit-coreml'))
                
                if models_path.exists():
                    for model_dir in models_path.iterdir():
                        if model_dir.is_dir() and not model_dir.name.startswith('.'):
                            # 计算实际大小
                            try:
                                total_size = 0
                                for dirpath, dirnames, filenames in os.walk(model_dir):
                                    for filename in filenames:
                                        filepath = os.path.join(dirpath, filename)
                                        if os.path.exists(filepath):
                                            total_size += os.path.getsize(filepath)
                                
                                if total_size >= 1024**3:  # >= 1GB
                                    size_str = f"{total_size / (1024**3):.1f}GB"
                                else:
                                    size_str = f"{total_size // (1024**2)}MB"
                            except:
                                size_str = "Unknown"
                            
                            # 读取配置文件获取架构信息
                            config_file = model_dir / 'config.json'
                            config_info = {}
                            if config_file.exists():
                                try:
                                    with open(config_file, 'r') as f:
                                        model_config = json.load(f)
                                    config_info = {
                                        'vocab_size': model_config.get('vocab_size', 0),
                                        'encoder_layers': model_config.get('encoder_layers', 0),
                                        'decoder_layers': model_config.get('decoder_layers', 0),
                                        'd_model': model_config.get('d_model', 0)
                                    }
                                except:
                                    pass
                            
                            # 将文件夹名转换为正确格式
                            folder_name = model_dir.name
                            if folder_name == "distil-whisper_distil-large-v3":
                                # 特殊处理distil模型的文件夹名
                                model_value = "large-v3|distil"
                                model_display_name = "distil-whisper_distil-large-v3"
                            elif "_whisper-" in folder_name:
                                # 标准格式: prefix_whisper-model -> model|prefix
                                parts = folder_name.split("_whisper-")
                                if len(parts) == 2:
                                    prefix, model_name = parts
                                    model_value = f"{model_name}|{prefix}"
                                    model_display_name = folder_name
                                else:
                                    model_value = folder_name
                                    model_display_name = folder_name
                            else:
                                model_value = folder_name
                                model_display_name = folder_name
                            
                            available_models['local'].append({
                                'value': model_value,
                                'name': model_display_name,
                                'display_name': model_display_name,
                                'size': size_str,
                                'multilingual_support': True,  # 简化：都支持多语言
                                'english_support': True,       # 都支持英文
                                'config_info': config_info,
                                'available': True
                            })
            
            # 处理API模型
            for provider_name, provider_config in providers.items():
                if provider_name == 'local' or not provider_config.get('enabled', False):
                    continue
                
                provider_type = provider_config.get('type', '')
                
                if provider_type == 'openai_whisper_api':
                    models_list = provider_config.get('models', [])
                    for model in models_list:
                        available_models['api'].append({
                            'value': f"openai_api_{model}",
                            'name': f"OpenAI {model}",
                            'display_name': f"🌐 OpenAI {model}",
                            'provider': 'openai_api',
                            'multilingual_support': True,
                            'english_support': True,
                            'available': True,
                            'requires_api_key': True
                        })
                
                elif provider_type == 'elevenlabs_api':
                    available_models['api'].append({
                        'value': f"elevenlabs_speech",
                        'name': "ElevenLabs Speech",
                        'display_name': "🗣️ ElevenLabs Speech",
                        'provider': 'elevenlabs_api',
                        'multilingual_support': True,
                        'english_support': True,
                        'available': True,
                        'requires_api_key': True
                    })
                
                elif provider_type == 'azure_cognitive_services':
                    available_models['api'].append({
                        'value': f"azure_speech",
                        'name': "Azure Speech",
                        'display_name': "☁️ Azure Speech",
                        'provider': 'azure_speech',
                        'multilingual_support': True,
                        'english_support': True,
                        'available': True,
                        'requires_api_key': True
                    })
            
            # 从配置文件读取推荐策略
            content_types = config.get('content_classification', {}).get('content_types', {})
            recommendations = {}
            for content_type, type_config in content_types.items():
                recs = type_config.get('recommendations', [])
                recommendations[content_type] = recs
            
            return jsonify({
                'local_models': available_models['local'],
                'api_models': available_models['api'],
                'recommendations': recommendations,
                'total_models': len(available_models['local']) + len(available_models['api'])
            })
            
        except Exception as e:
            logger.error(f"Models API error: {e}")
            return jsonify({'error': 'Failed to get models info'}), 500


    @app.route('/api/models/smart-config')
    def api_models_smart_config():
        """简化的模型配置 API - 简单排序逻辑"""
        try:
            from pathlib import Path
            from src.utils.config import ConfigManager
            import json
            import os
            
            # 从配置读取推荐策略
            config_manager = ConfigManager()
            config = config_manager.get_full_config()
            
            # 获取内容类型推荐
            content_types = config.get('content_classification', {}).get('content_types', {})
            content_type_recommendations = {}
            for content_type, type_config in content_types.items():
                content_type_recommendations[content_type] = type_config.get('recommendations', [])
            
            def get_directory_size(directory_path):
                """计算目录大小并返回人类可读格式"""
                try:
                    total_size = 0
                    for dirpath, dirnames, filenames in os.walk(directory_path):
                        for filename in filenames:
                            filepath = os.path.join(dirpath, filename)
                            if os.path.exists(filepath):
                                total_size += os.path.getsize(filepath)
                    
                    if total_size >= 1024**3:  # >= 1GB
                        return f"{total_size / (1024**3):.1f}GB"
                    else:
                        return f"{total_size // (1024**2)}MB"
                except:
                    return "Unknown"
            
            # 发现所有实际存在的模型
            models_path = Path('./models/whisperkit-coreml')
            all_models = []
            
            # 动态发现所有实际存在的模型
            if models_path.exists():
                for model_dir in models_path.iterdir():
                    if model_dir.is_dir() and not model_dir.name.startswith('.'):
                        # 读取模型配置
                        config_file = model_dir / 'config.json'
                        config_info = {}
                        if config_file.exists():
                            try:
                                with open(config_file, 'r') as f:
                                    model_config = json.load(f)
                                config_info = {
                                    'vocab_size': model_config.get('vocab_size', 0),
                                    'encoder_layers': model_config.get('encoder_layers', 0),
                                    'decoder_layers': model_config.get('decoder_layers', 0),
                                    'd_model': model_config.get('d_model', 0)
                                }
                            except:
                                pass
                        
                        if config_info:
                            # 计算模型实际文件大小
                            model_size = get_directory_size(model_dir)
                            
                            # 根据vocab_size判断多语言支持 (51865+表示多语言)
                            multilingual = config_info.get('vocab_size', 0) >= 51865
                            
                            # 构建模型描述 - 将文件夹名转换为正确格式
                            folder_name = model_dir.name
                            if folder_name == "distil-whisper_distil-large-v3":
                                # 特殊处理distil模型的文件夹名
                                model_value = "large-v3|distil"
                                model_display_name = "distil-whisper_distil-large-v3"
                            elif "_whisper-" in folder_name:
                                # 标准格式: prefix_whisper-model -> model|prefix
                                parts = folder_name.split("_whisper-")
                                if len(parts) == 2:
                                    prefix, model_name = parts
                                    model_value = f"{model_name}|{prefix}"
                                    model_display_name = folder_name
                                else:
                                    model_value = folder_name
                                    model_display_name = folder_name
                            else:
                                model_value = folder_name
                                model_display_name = folder_name
                            
                            model = {
                                'value': model_value,
                                'name': model_display_name,
                                'display_name': model_display_name,
                                'downloaded': True,
                                'config_info': config_info,
                                'model_size': model_size,
                                'english_support': True,
                                'multilingual_support': multilingual
                            }
                            
                            all_models.append(model)
            
            # 添加API模型 - 从config动态读取
            providers = config.get('whisperkit', {}).get('providers', {})
            for provider_name, provider_config in providers.items():
                if provider_name == 'local' or not provider_config.get('enabled', False):
                    continue
                
                provider_type = provider_config.get('type', '')
                display_info = provider_config.get('display_info', {})
                icon = display_info.get('icon', '🔗')
                provider_display_name = display_info.get('provider_name', provider_name)
                
                # 获取模型列表
                models_list = provider_config.get('models', [])
                
                # 处理不同的模型配置格式
                if isinstance(models_list, list) and len(models_list) > 0:
                    # 检查第一个元素是否为字符串（旧格式）或字典（新格式）
                    if isinstance(models_list[0], str):
                        # 旧格式：简单字符串列表，转换为新格式
                        for model_name in models_list:
                            all_models.append({
                                'value': f"{provider_name}_{model_name}",
                                'name': f"{provider_display_name} {model_name}",
                                'display_name': f"{icon} {provider_display_name} {model_name}",
                                'provider': provider_name,
                                'multilingual_support': True,  # 默认值
                                'english_support': True,       # 默认值
                                'downloaded': False,
                                'requires_api_key': True,
                                'config_info': {'api_model': True}
                            })
                    else:
                        # 新格式：完整配置字典
                        for model_config in models_list:
                            model_name = model_config.get('name', 'unknown')
                            model_display_name = model_config.get('display_name', model_name)
                            multilingual_support = model_config.get('multilingual_support', True)
                            english_support = model_config.get('english_support', True)
                            
                            all_models.append({
                                'value': f"{provider_name}_{model_name}",
                                'name': f"{provider_display_name} {model_display_name}",
                                'display_name': f"{icon} {provider_display_name} {model_display_name}",
                                'provider': provider_name,
                                'multilingual_support': multilingual_support,
                                'english_support': english_support,
                                'downloaded': False,
                                'requires_api_key': True,
                                'config_info': {'api_model': True}
                            })
            
            # 新的按语言分组的排序函数
            def apply_language_based_model_sorting(models, content_type):
                """
                根据语言模式和内容类型生成推荐模型列表
                返回包含recommended和language_mode字段的模型列表
                """
                result_models = []
                
                # 获取当前内容类型的推荐配置
                content_recommendations = content_type_recommendations.get(content_type, {})
                
                # 支持新格式（按语言分组）和旧格式（简单列表）的兼容处理
                english_recommendations = []
                multilingual_recommendations = []
                
                if isinstance(content_recommendations, dict):
                    # 新格式：按语言分组
                    english_recommendations = content_recommendations.get('english', [])
                    multilingual_recommendations = content_recommendations.get('multilingual', [])
                elif isinstance(content_recommendations, list):
                    # 旧格式：简单列表，作为通用推荐
                    english_recommendations = content_recommendations
                    multilingual_recommendations = content_recommendations
                
                # 为每个模型添加推荐信息和语言模式
                for model in models:
                    model_copy = model.copy()
                    model_value = model_copy.get('value', '')
                    model_name = model_copy.get('name', '')
                    
                    # 检查是否为英文推荐模型 (精确匹配)
                    is_english_recommended = any(
                        rec_model == model_value or rec_model == model_name 
                        for rec_model in english_recommendations
                    )
                    
                    
                    # 检查是否为多语言推荐模型 (精确匹配)
                    is_multilingual_recommended = any(
                        rec_model == model_value or rec_model == model_name
                        for rec_model in multilingual_recommendations
                    )
                    
                    # 创建英文模式的模型副本
                    if is_english_recommended:
                        english_model = model_copy.copy()
                        english_model['recommended'] = True
                        english_model['language_mode'] = 'english'
                        result_models.append(english_model)
                    
                    # 创建多语言模式的模型副本
                    if is_multilingual_recommended:
                        multilingual_model = model_copy.copy()
                        multilingual_model['recommended'] = True
                        multilingual_model['language_mode'] = 'multilingual'
                        result_models.append(multilingual_model)
                    
                    # 如果既不是英文推荐也不是多语言推荐，添加为非推荐模型
                    if not is_english_recommended and not is_multilingual_recommended:
                        non_recommended_model = model_copy.copy()
                        non_recommended_model['recommended'] = False
                        non_recommended_model['language_mode'] = 'general'
                        result_models.append(non_recommended_model)
                
                # 排序：推荐模型优先，然后按参数复杂度排序
                def get_sort_priority(model):
                    is_recommended = model.get('recommended', False)
                    config = model.get('config_info', {})
                    d_model = config.get('d_model', 0)
                    encoder_layers = config.get('encoder_layers', 0)
                    complexity = d_model * encoder_layers
                    
                    # 推荐模型排在前面，复杂度高的排在前面
                    return (not is_recommended, -complexity)
                
                result_models.sort(key=get_sort_priority)
                return result_models
            
            # 为不同内容类型生成排序后的模型列表
            result = {}
            for content_type in content_type_recommendations.keys():
                # 获取当前内容类型的推荐配置
                content_recommendations = content_type_recommendations.get(content_type, {})
                english_recommendations = []
                multilingual_recommendations = []
                
                if isinstance(content_recommendations, dict):
                    english_recommendations = content_recommendations.get('english', [])
                    multilingual_recommendations = content_recommendations.get('multilingual', [])
                
                # 为每个模型设置推荐标志
                content_type_models = []
                for model in all_models:
                    model_copy = model.copy()
                    model_value = model_copy.get('value', '')
                    model_name = model_copy.get('name', '')
                    
                    # 设置推荐标志
                    model_copy['is_english_recommended'] = any(
                        rec_model == model_value or rec_model == model_name 
                        for rec_model in english_recommendations
                    )
                    model_copy['is_multilingual_recommended'] = any(
                        rec_model == model_value or rec_model == model_name
                        for rec_model in multilingual_recommendations
                    )
                    
                    content_type_models.append(model_copy)
                
                result[content_type] = content_type_models
            
            # 为'all'类别也添加推荐信息（合并所有内容类型的推荐）
            all_models_with_recommendations = []
            all_english_recs = set()
            all_multilingual_recs = set()
            
            # 收集所有内容类型的推荐模型
            for content_type, recommendations in content_type_recommendations.items():
                if isinstance(recommendations, dict):
                    all_english_recs.update(recommendations.get('english', []))
                    all_multilingual_recs.update(recommendations.get('multilingual', []))
                elif isinstance(recommendations, list):
                    all_english_recs.update(recommendations)
                    all_multilingual_recs.update(recommendations)
            
            # 为all列表中的每个模型添加推荐信息
            for model in all_models:
                model_copy = model.copy()
                model_value = model_copy.get('value', '')
                model_name = model_copy.get('name', '')
                
                # 检查是否为任何内容类型的推荐模型 (精确匹配)
                is_english_recommended = any(
                    rec_model == model_value or rec_model == model_name 
                    for rec_model in all_english_recs
                )
                is_multilingual_recommended = any(
                    rec_model == model_value or rec_model == model_name
                    for rec_model in all_multilingual_recs
                )
                
                # all列表不显示推荐标识，让前端根据语言模式过滤时显示
                model_copy['recommended'] = False  # all列表中不标记推荐
                model_copy['language_mode'] = 'general'  # all列表使用通用模式
                
                # 但保留推荐信息供前端使用
                model_copy['is_english_recommended'] = is_english_recommended
                model_copy['is_multilingual_recommended'] = is_multilingual_recommended
                all_models_with_recommendations.append(model_copy)
            
            # 按推荐优先级和复杂度排序
            def get_model_complexity(model):
                is_recommended = model.get('recommended', False)
                config = model.get('config_info', {})
                d_model = config.get('d_model', 0)
                encoder_layers = config.get('encoder_layers', 0)
                complexity = d_model * encoder_layers
                return (not is_recommended, -complexity)
            
            all_models_with_recommendations.sort(key=get_model_complexity)
            result['all'] = all_models_with_recommendations
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Smart models config API error: {e}")
            return jsonify({'error': 'Failed to get smart models configuration'}), 500
    
    # Private内容访问路由
    @app.route('/private/')
    @app.route('/private/<path:filepath>')
    def private_content(filepath=None):
        """访问私人内容"""
        try:
            from pathlib import Path
            import os
            
            # 私人内容根目录
            private_root = Path('./data/output/private')
            
            if not private_root.exists():
                private_root.mkdir(parents=True, exist_ok=True)
                
            # 检查index.html是否存在，不存在则从templates复制
            index_file = private_root / 'index.html'
            if not index_file.exists():
                template_file = Path('./templates/private_index.html')
                if template_file.exists():
                    import shutil
                    shutil.copy2(template_file, index_file)
                    logger.info(f"从templates复制private index.html: {index_file}")
                else:
                    # 如果模板文件也不存在，创建简单版本
                    index_content = '''
                    <html>
                    <head><title>🔒 Private Content</title></head>
                    <body>
                        <h1>🔒 Private Content</h1>
                        <p>No private content available yet.</p>
                        <p><a href="/">← Back to Main</a></p>
                    </body>
                    </html>
                    '''
                    index_file.write_text(index_content, encoding='utf-8')
            
            if filepath is None:
                # 显示私人内容目录
                filepath = 'index.html'
            
            # 安全检查：防止目录穿越攻击
            safe_path = private_root / filepath
            try:
                safe_path = safe_path.resolve()
                private_root_resolved = private_root.resolve()
                if not str(safe_path).startswith(str(private_root_resolved)):
                    return "Access denied", 403
            except:
                return "Invalid path", 400
            
            # 检查文件是否存在
            if not safe_path.exists():
                return render_template('error.html', 
                                     error_code=404,
                                     error_message=f"Private content not found: {filepath}"), 404
            
            # 如果是目录，查找index.html
            if safe_path.is_dir():
                index_file = safe_path / 'index.html'
                if index_file.exists():
                    safe_path = index_file
                else:
                    # 生成目录列表
                    files = []
                    for item in safe_path.iterdir():
                        if item.is_file() and item.suffix in ['.html', '.md']:
                            files.append(item.name)
                    
                    dir_listing = f'''
                    <html>
                    <head><title>Private Directory: {filepath}</title></head>
                    <body>
                        <h1>🔒 Private Directory: {filepath}</h1>
                        <ul>
                            <li><a href="/private/">← Back to Private Root</a></li>
                            {"".join(f'<li><a href="/private/{filepath}/{f}">{f}</a></li>' for f in files)}
                        </ul>
                    </body>
                    </html>
                    '''
                    return dir_listing
            
            # 读取并返回文件内容
            if safe_path.suffix == '.html':
                content = safe_path.read_text(encoding='utf-8')
                return content
            elif safe_path.suffix == '.md':
                # 简单的Markdown渲染
                content = safe_path.read_text(encoding='utf-8')
                html_content = f'''
                <html>
                <head><title>Private Content</title></head>
                <body>
                    <pre style="white-space: pre-wrap; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                    {content}
                    </pre>
                    <p><a href="/private/">← Back to Private Root</a></p>
                </body>
                </html>
                '''
                return html_content
            else:
                return "Unsupported file type", 400
                
        except Exception as e:
            logger.error(f"Private content access error: {e}")
            return render_template('error.html',
                                 error_code=500,
                                 error_message="Failed to access private content"), 500
    
    # 错误处理
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('error.html', 
                             error_code=404,
                             error_message="Page not found"), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return render_template('error.html',
                             error_code=500,
                             error_message="Internal server error"), 500
    
    @app.errorhandler(413)
    def too_large_error(error):
        return jsonify({'error': 'File too large'}), 413
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    
    return app


def allowed_file(filename, allowed_extensions):
    """检查文件扩展名是否允许"""
    if not filename:
        return False
    
    file_ext = Path(filename).suffix.lower()
    return file_ext in allowed_extensions


def is_valid_youtube_url(url):
    """验证YouTube URL格式"""
    youtube_domains = [
        'www.youtube.com',
        'youtube.com', 
        'youtu.be',
        'm.youtube.com'
    ]
    
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc in youtube_domains
    except:
        return False


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=8080, debug=True)