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
import json
import ipaddress
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import logging

# 导入处理器和服务
from .audio_upload_handler import AudioUploadHandler
from .youtube_handler import YouTubeHandler
from ..core.processing_service import get_processing_service
from ..utils.config import ConfigManager, UploadSettings
from ..core.dependency_container import get_global_container
from ..utils.content_type_service import ContentTypeService
from .helpers import get_config_value, create_api_response, scan_content_directory, organize_content_by_type, render_private_index, serve_private_file, get_content_types_config, validate_github_config

logger = logging.getLogger(__name__)


def create_app(config=None):
    """创建Flask应用工厂函数"""
    import os
    # 设置模板文件夹和静态文件夹为项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    template_dir = os.path.join(project_root, 'templates')
    static_dir = os.path.join(project_root, 'static')
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

    # 默认配置
    app.config.update({
        'SECRET_KEY': os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production'),
        'TAILSCALE_NETWORK': '100.64.0.0/10'
    })

    # 应用测试配置
    if config:
        app.config.update(config)

    # 初始化配置管理器
    config_manager = app.config.get('CONFIG_MANAGER')
    try:
        if not config_manager:
            config_manager = ConfigManager()
            app.config['CONFIG_MANAGER'] = config_manager

        upload_settings = config_manager.get_upload_settings()
        app.config['MAX_CONTENT_LENGTH'] = upload_settings.max_file_size

    except Exception as e:
        logger.warning(f"Failed to load config manager: {e}")
        config_manager = None
        app.config['CONFIG_MANAGER'] = None
        app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1GB fallback


    # 初始化处理服务
    if config_manager:
        global_container = get_global_container()
        content_type_service = None

        if global_container:
            content_type_service = global_container.get_content_type_service()
        else:
            content_type_service = ContentTypeService(config_manager)

        app.config['CONTENT_TYPE_SERVICE'] = content_type_service
        app.config['AUDIO_HANDLER'] = AudioUploadHandler(
            config_manager,
            container=global_container,
            content_type_service=content_type_service,
        )
        app.config['YOUTUBE_HANDLER'] = YouTubeHandler(config_manager)
    else:
        logger.error("配置管理器加载失败，无法初始化处理服务")
        app.config['AUDIO_HANDLER'] = None
        app.config['YOUTUBE_HANDLER'] = None
        app.config['CONTENT_TYPE_SERVICE'] = None
    app.config['PROCESSING_SERVICE'] = get_processing_service()

    # Tailscale安全中间件
    @app.before_request
    def security_middleware():
        if app.config.get('TESTING'):
            return  # 测试环境跳过安全检查

        # 检查配置中的Tailscale访问限制
        config_manager = app.config.get('CONFIG_MANAGER')
        tailscale_only_enabled = True
        if config_manager:
            security_settings = config_manager.get_security_settings()
            tailscale_only_enabled = security_settings.tailscale_only

        if not tailscale_only_enabled:
            return  # 配置显式禁用Tailscale网络限制

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

    # ------------------------------------------------------------------
    # MLX Whisper模型助手函数
    # ------------------------------------------------------------------

    def _check_model_downloaded(repo_name: str) -> bool:
        """检查MLX模型是否已在本地缓存中存在。"""
        try:
            import os
            from huggingface_hub import snapshot_download
            from huggingface_hub.utils import LocalEntryNotFoundError

            try:
                cache_path = snapshot_download(repo_name, local_files_only=True)
                return os.path.exists(cache_path)
            except LocalEntryNotFoundError:
                return False
        except Exception as exc:  # pragma: no cover - 安全兜底
            logger.warning("Failed to check download status for %s: %s", repo_name, exc)
            return False

    def _build_mlx_model_catalog() -> dict:
        """返回MLX可用模型的基础信息和下载状态。"""
        config_manager = app.config.get('CONFIG_MANAGER')
        if not config_manager:
            raise RuntimeError('Configuration manager not initialized')

        full_config = config_manager.get_full_config()
        mlx_config = full_config.get('mlx_whisper', {}) or {}
        available_models = mlx_config.get('available_models') or []
        default_model = str(mlx_config.get('default_model', 'whisper-tiny-mlx'))

        cache = app.config.setdefault('HUGGINGFACE_CACHE', {})
        catalog = []

        for entry in available_models:
            if isinstance(entry, dict):
                model_data = dict(entry)
                value = str(model_data.get('value') or model_data.get('name') or model_data.get('repo', ''))
                if not value and 'display_name' in model_data:
                    value = model_data['display_name']
                repo_name = model_data.get('repo')
                if not repo_name:
                    repo_name = value if '/' in value else f"mlx-community/{value}"
                value = repo_name.split('/')[-1]
                model_data.setdefault('value', value)
                model_data.setdefault('name', model_data.get('display_name', value))
                model_data.setdefault('display_name', model_data['name'])
                model_data.setdefault('config_info', model_data.get('config_info') or {})
            else:
                repo_name = entry if '/' in entry else f"mlx-community/{entry}"
                value = repo_name.split('/')[-1]
                model_data = {
                    'value': value,
                    'name': value,
                    'display_name': value,
                    'repo': repo_name,
                    'config_info': {},
                }

            repo_name = model_data.get('repo') or f"mlx-community/{model_data['value']}"
            is_default = model_data.get('is_default')
            if is_default is None:
                is_default = model_data['value'] == default_model or model_data.get('name') == default_model

            if repo_name in cache:
                downloaded = cache[repo_name]
            else:
                downloaded = _check_model_downloaded(repo_name)
                cache[repo_name] = downloaded

            catalog.append({
                **model_data,
                'repo': repo_name,
                'is_default': bool(is_default),
                'downloaded': downloaded,
            })

        return {
            'default_model': default_model,
            'models': catalog,
        }

    def _collect_recommendation_payload() -> dict:
        """收集所有内容类型及媒体预设的推荐模型集合。"""
        content_type_service: ContentTypeService = app.config.get('CONTENT_TYPE_SERVICE')
        if not content_type_service:
            raise RuntimeError('Content type service is not initialized')

        content_types = content_type_service.get_all()
        ordered_content_types = list(content_types.keys())

        preferences_manager = content_type_service.get_preferences_manager()
        media_defaults = {}
        if hasattr(preferences_manager, 'prefs'):
            media_defaults = preferences_manager.prefs.get('_media_defaults', {}) or {}

        for media_type in media_defaults.keys():
            if media_type not in ordered_content_types:
                ordered_content_types.append(media_type)

        recommendations = {}
        english_union = []
        multilingual_union = []
        english_seen = set()
        multilingual_seen = set()

        for content_type in ordered_content_types:
            recs = content_type_service.get_content_type_recommendations(content_type) or {}
            normalized = {
                'english': [str(item) for item in recs.get('english', [])],
                'multilingual': [str(item) for item in recs.get('multilingual', [])],
            }
            recommendations[content_type] = normalized

            for model_name in normalized['english']:
                if model_name not in english_seen:
                    english_seen.add(model_name)
                    english_union.append(model_name)
            for model_name in normalized['multilingual']:
                if model_name not in multilingual_seen:
                    multilingual_seen.add(model_name)
                    multilingual_union.append(model_name)

        return {
            'ordered_content_types': ordered_content_types,
            'recommendations': recommendations,
            'english_union': english_union,
            'multilingual_union': multilingual_union,
        }

    # 主页路由
    @app.route('/')
    def index():
        """主页 - 显示上传界面和分类选项"""
        config_manager = app.config.get('CONFIG_MANAGER')

        # 获取内容类型配置
        content_types = get_content_types_config(app)

        # 获取完整配置用于模板
        config_dict = config_manager.get_full_config() if config_manager else {}

        return render_template('web_app/upload.html',
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

            # 验证文件类型 - 使用AudioUploadHandler的格式检查
            handler = app.config['AUDIO_HANDLER']
            if handler and not handler.is_supported_format(file.filename):
                return jsonify({'error': 'Invalid file type'}), 400

            # 获取隐私级别
            privacy_level = request.form.get('privacy_level', 'public')

            # 处理子分类信息 - 简化版本，只使用subcategory字段
            subcategory = request.form.get('subcategory', '')
            audio_language = request.form.get('audio_language', 'english')

            # 处理MLX模型选择
            whisper_model = request.form.get('whisper_model', 'whisper-tiny')
            # MLX模型使用简单的模型名称，无需前缀

            # 解析Post-Processing选项（复用偏好默认值作为fallback）
            def _checkbox_to_bool(field_name: str, default: bool = False) -> bool:
                raw_value = request.form.get(field_name)
                if raw_value is None:
                    return default
                if isinstance(raw_value, str):
                    return raw_value.strip().lower() in ('on', 'true', '1', 'yes')
                return bool(raw_value)

            post_processing_defaults = {}
            if handler and getattr(handler, 'content_type_service', None):
                try:
                    post_processing_defaults = handler.content_type_service.get_effective_config(
                        content_type,
                        subcategory or None,
                    ) or {}
                except Exception as prefs_error:  # pragma: no cover - defensive logging
                    logger.warning(
                        "Failed to load post-processing defaults for %s/%s: %s",
                        content_type,
                        subcategory,
                        prefs_error,
                    )
            if post_processing_defaults:
                logger.debug(
                    "Post-processing defaults for %s/%s: %s",
                    content_type,
                    subcategory,
                    post_processing_defaults,
                )

            post_processing_overrides = {
                'enable_anonymization': _checkbox_to_bool('enable_anonymization'),
                'enable_summary': _checkbox_to_bool('enable_summary'),
                'enable_mindmap': _checkbox_to_bool('enable_mindmap'),
                'enable_diarization': _checkbox_to_bool('enable_diarization'),
            }

            # 处理上传 - 使用清晰的参数分离
            handler = app.config['AUDIO_HANDLER']
            result = handler.process_upload(
                file=file,
                content_type=content_type,        # 核心业务分类
                subcategory=subcategory,          # 细分业务场景
                privacy_level=privacy_level,      # 系统级配置
                metadata={                        # 处理参数和用户输入
                    'audio_language': audio_language,
                    'description': request.form.get('description', ''),
                    'whisper_model': whisper_model,
                    **post_processing_overrides,
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

            # 获取强制使用Whisper选项
            force_whisper = request.form.get('force_whisper') == 'on'

            # 处理YouTube URL
            handler = app.config['YOUTUBE_HANDLER']
            result = handler.process_url(
                url=youtube_url,
                content_type=content_type,
                metadata={
                    'tags': request.form.get('tags', ''),
                    'description': request.form.get('description', ''),
                    'force_whisper': force_whisper
                },
                privacy_level=privacy_level,
                force_whisper=force_whisper
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
            return render_template('web_app/error.html',
                                 error_code=404,
                                 error_message=f"Processing session not found: {processing_id}"), 404

        return render_template('web_app/status.html',
                             processing_id=processing_id,
                             status=status)

    # API路由
    @app.route('/api/status/processing')
    def api_processing_status():
        """获取所有活跃处理状态API"""
        try:
            service = app.config['PROCESSING_SERVICE']
            active_sessions = service.list_active_sessions()
            return jsonify(create_api_response(success=True, data={'active_sessions': active_sessions}))
        except Exception as e:
            logger.error(f"Processing status API error: {e}")
            return jsonify(create_api_response(success=False, error='Failed to get status')), 500

    @app.route('/api/status/<processing_id>')
    def api_single_status(processing_id):
        """获取单个处理状态API"""
        try:
            service = app.config['PROCESSING_SERVICE']
            status = service.get_status(processing_id)

            if status is None:
                return jsonify(create_api_response(success=False, error='Processing session not found')), 404

            return jsonify(create_api_response(success=True, data=status))
        except Exception as e:
            logger.error(f"Single status API error: {e}")
            return jsonify(create_api_response(success=False, error='Failed to get status')), 500

    @app.route('/api/categories')
    def api_categories():
        """内容分类API"""
        try:
            content_types = get_content_types_config(app)
            return jsonify(create_api_response(success=True, data=content_types))
        except Exception as e:
            logger.error(f"Categories API error: {e}")
            return jsonify(create_api_response(success=False, error=str(e))), 500

    @app.route('/api/config/github-status')
    def api_github_config_status():
        """检查GitHub配置状态API"""
        try:
            config_status = validate_github_config(app)
            return jsonify(create_api_response(success=True, data=config_status))
        except Exception as e:
            logger.error(f"GitHub config status API error: {e}")
            return jsonify(create_api_response(
                success=False,
                error=str(e),
                data={'configured': False, 'message': f'Validation error: {str(e)}'}
            )), 500

    @app.route('/api/debug/config')
    def api_debug_config():
        """调试配置状态API"""
        import os
        try:
            config_manager = app.config.get('CONFIG_MANAGER')
            debug_info = {
                'env_github_username': os.environ.get('GITHUB_USERNAME'),
                'env_github_token_set': bool(os.environ.get('GITHUB_TOKEN')),
                'config_github_username': get_config_value(app, 'github.username'),
                'config_github_pages_url': get_config_value(app, 'github.pages_url'),
                'config_manager_exists': config_manager is not None,
                'full_github_config': config_manager.get('github', default={}) if config_manager else None
            }
            return jsonify(create_api_response(success=True, data=debug_info))
        except Exception as e:
            logger.error(f"Debug config API error: {e}")
            return jsonify(create_api_response(success=False, error=str(e))), 500

    @app.route('/api/config/frontend')
    def api_frontend_config():
        """前端配置API - 提供动态配置给JavaScript"""
        try:
            config_manager = app.config.get('CONFIG_MANAGER')

            def format_file_size(bytes_value: int) -> str:
                if bytes_value >= 1024 ** 3:
                    return f"{bytes_value // (1024 ** 3)}GB"
                if bytes_value >= 1024 ** 2:
                    return f"{bytes_value // (1024 ** 2)}MB"
                return f"{bytes_value // 1024}KB"

            upload_settings = config_manager.get_upload_settings() if config_manager else UploadSettings()

            frontend_config = {
                'upload': {
                    'max_file_size': upload_settings.max_file_size,
                    'max_file_size_display': format_file_size(upload_settings.max_file_size),
                    'supported_formats': list(upload_settings.supported_formats),
                    'allowed_extensions': list(upload_settings.allowed_extensions)
                }
            }

            return jsonify(create_api_response(success=True, data=frontend_config))

        except Exception as e:
            logger.error(f"Frontend config API error: {e}")
            return jsonify(create_api_response(
                success=False,
                error=str(e),
                data={'upload': {'max_file_size': 1073741824, 'max_file_size_display': '1GB'}}  # fallback
            )), 500

    @app.route('/api/results/recent')
    def api_recent_results():
        """最近结果API"""
        try:
            from ..storage.result_storage import ResultStorage

            limit = request.args.get('limit', 10, type=int)
            storage = ResultStorage()
            results = storage.get_recent_results(limit=limit)

            return jsonify(create_api_response(success=True, data=results))
        except Exception as e:
            logger.error(f"Recent results API error: {e}")
            return jsonify(create_api_response(success=False, error='Failed to get recent results')), 500


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
                return jsonify({'error': 'YouTube handler not available'}), 503

            metadata = handler.get_video_metadata(url)

            if metadata:
                # 转换字幕信息为前端期望的格式
                subtitle_info = metadata.get('subtitle_info', {})
                subtitles_list = []

                # 处理手动字幕
                if subtitle_info.get('subtitles'):
                    for lang_code, subtitle_data in subtitle_info['subtitles'].items():
                        # subtitle_data可能是列表（不同格式），我们只需要语言信息
                        language_name = lang_code
                        if isinstance(subtitle_data, list) and subtitle_data:
                            # 尝试从第一个格式中获取名称
                            first_format = subtitle_data[0]
                            if isinstance(first_format, dict):
                                language_name = first_format.get('name', lang_code)
                        elif isinstance(subtitle_data, dict):
                            language_name = subtitle_data.get('name', lang_code)

                        subtitles_list.append({
                            'language_code': lang_code,
                            'language': language_name,
                            'auto_generated': False
                        })

                # 处理自动生成字幕
                if subtitle_info.get('auto_captions'):
                    for lang_code, caption_data in subtitle_info['auto_captions'].items():
                        # caption_data可能是列表，处理方式同上
                        language_name = lang_code
                        if isinstance(caption_data, list) and caption_data:
                            first_format = caption_data[0]
                            if isinstance(first_format, dict):
                                language_name = first_format.get('name', lang_code)
                        elif isinstance(caption_data, dict):
                            language_name = caption_data.get('name', lang_code)

                        subtitles_list.append({
                            'language_code': lang_code,
                            'language': language_name,
                            'auto_generated': True
                        })

                return jsonify({
                    'title': metadata.get('title', ''),
                    'description': metadata.get('description', ''),
                    'duration': metadata.get('duration', ''),
                    'uploader': metadata.get('uploader', ''),
                    'tags': metadata.get('tags', []),
                    'subtitles': subtitles_list  # 前端期望的字段名
                })
            else:
                return jsonify({'error': 'Failed to fetch video metadata'}), 400

        except Exception as e:
            logger.error(f"YouTube metadata API error: {e}")
            return jsonify({'error': 'Failed to get video metadata'}), 500


    @app.route('/api/models/available')
    def api_models_available():
        """提供MLX Whisper模型列表及其下载状态。"""
        try:
            catalog = _build_mlx_model_catalog()
            return jsonify(create_api_response(success=True, data=catalog))
        except Exception as exc:
            logger.error("Available models API error: %s", exc)
            return jsonify(create_api_response(success=False, error='Failed to list available models')), 500

    @app.route('/api/models/smart-config')
    def api_models_smart_config():
        """兼容层：返回旧版smart-config结构。"""
        try:
            catalog = _build_mlx_model_catalog()
            rec_payload = _collect_recommendation_payload()

            base_models = catalog['models']
            all_english = set(rec_payload['english_union'])
            all_multilingual = set(rec_payload['multilingual_union'])

            def _with_flags(model_entry, english_set, multilingual_set):
                value = model_entry.get('value') or model_entry.get('name')
                return {
                    **model_entry,
                    'is_english_recommended': value in english_set,
                    'is_multilingual_recommended': value in multilingual_set,
                }

            all_models = []
            for model in base_models:
                entry = _with_flags(model, all_english, all_multilingual)
                if entry['is_english_recommended'] and not entry['is_multilingual_recommended']:
                    entry['language_mode'] = 'english'
                elif entry['is_multilingual_recommended'] and not entry['is_english_recommended']:
                    entry['language_mode'] = 'multilingual'
                else:
                    entry['language_mode'] = 'general'
                entry.setdefault('config_info', {})
                entry['recommended'] = False
                all_models.append(entry)

            all_models.sort(
                key=lambda m: (
                    not (m.get('is_english_recommended') or m.get('is_multilingual_recommended')),
                    not m.get('is_default', False),
                    m.get('name', ''),
                )
            )

            result = {'all': all_models}

            for content_type in rec_payload['ordered_content_types']:
                recommendation_sets = rec_payload['recommendations'].get(content_type, {})
                english_set = set(recommendation_sets.get('english', []))
                multilingual_set = set(recommendation_sets.get('multilingual', []))

                models_with_flags = [
                    _with_flags(model, english_set, multilingual_set)
                    for model in base_models
                ]

                models_with_flags.sort(
                    key=lambda m: (
                        not (m.get('is_english_recommended') or m.get('is_multilingual_recommended')),
                        not m.get('is_default', False),
                        m.get('name', ''),
                    )
                )

                result[content_type] = models_with_flags

            return jsonify(create_api_response(success=True, data=result))

        except Exception as exc:
            logger.error("Smart models config API error: %s", exc)
            return jsonify(create_api_response(success=False, error='Failed to get smart models configuration')), 500


    # PreferencesManager API路由 - Phase 7.2
    @app.route('/api/preferences/subcategories/<content_type>')
    def api_get_subcategories(content_type):
        """获取指定content_type的subcategory列表API"""
        try:
            content_type_service: ContentTypeService = app.config.get('CONTENT_TYPE_SERVICE')
            if not content_type_service:
                raise RuntimeError('Content type service is not initialized')

            subcategories = content_type_service.get_subcategories(content_type)

            return jsonify({'data': subcategories})
        except Exception as e:
            logger.error(f"Get subcategories API error: {e}")
            return jsonify({'error': f'Failed to get subcategories: {str(e)}'}), 500

    @app.route('/api/preferences/config/<content_type>')
    @app.route('/api/preferences/config/<content_type>/<subcategory>')
    def api_get_preferences_config(content_type, subcategory=None):
        """获取有效配置API（支持继承机制）"""
        try:
            content_type_service: ContentTypeService = app.config.get('CONTENT_TYPE_SERVICE')
            if not content_type_service:
                raise RuntimeError('Content type service is not initialized')

            config = content_type_service.get_effective_config(content_type, subcategory)

            return jsonify({'data': config})
        except Exception as e:
            logger.error(f"Get preferences config API error: {e}")
            return jsonify({'error': f'Failed to get preferences config: {str(e)}'}), 500

    @app.route('/api/preferences/recommendations/_all', methods=['GET'])
    def api_get_all_recommendations():
        """获取所有内容类型/媒体的推荐模型集合。"""
        try:
            payload = _collect_recommendation_payload()
            data = {
                'ordered_content_types': payload['ordered_content_types'],
                'recommendations': payload['recommendations'],
                'all': {
                    'english': payload['english_union'],
                    'multilingual': payload['multilingual_union'],
                }
            }
            return jsonify(create_api_response(success=True, data=data))
        except Exception as exc:
            logger.error("Get all recommendations API error: %s", exc)
            return jsonify(create_api_response(success=False, error=str(exc))), 500

    @app.route('/api/preferences/recommendations/<content_type>', methods=['GET'])
    def api_get_recommendations(content_type):
        """获取指定内容类型的推荐模型配置"""
        try:
            content_type_service: ContentTypeService = app.config.get('CONTENT_TYPE_SERVICE')
            if not content_type_service:
                raise RuntimeError('Content type service is not initialized')

            recommendations = content_type_service.get_content_type_recommendations(content_type)
            return jsonify(create_api_response(success=True, data=recommendations))
        except Exception as e:
            logger.error(f"Get recommendations API error: {e}")
            return jsonify(create_api_response(success=False, error=str(e))), 500

    @app.route('/api/preferences/recommendations/<content_type>', methods=['POST'])
    def api_save_recommendations(content_type):
        """保存内容类型的推荐模型配置"""
        try:
            payload = request.get_json() or {}
            if not isinstance(payload, dict):
                return jsonify(create_api_response(success=False, error='Invalid payload')), 400

            content_type_service: ContentTypeService = app.config.get('CONTENT_TYPE_SERVICE')
            if not content_type_service:
                raise RuntimeError('Content type service is not initialized')

            content_type_service.save_content_type_recommendations(content_type, payload)
            updated = content_type_service.get_content_type_recommendations(content_type)

            return jsonify(create_api_response(
                success=True,
                data=updated,
                message=f'Recommendations for "{content_type}" updated successfully'
            ))
        except Exception as e:
            logger.error(f"Save recommendations API error: {e}")
            return jsonify(create_api_response(success=False, error=str(e))), 500

    @app.route('/api/preferences/subcategory', methods=['POST'])
    def api_create_subcategory():
        """创建新subcategory API"""
        try:
            # 获取请求数据
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Request data is required'}), 400
                
            content_type = data.get('content_type')
            subcategory = data.get('subcategory')
            display_name = data.get('display_name')
            config = data.get('config', {})
            
            if not content_type or not subcategory or not display_name:
                return jsonify(create_api_response(success=False, error='content_type, subcategory and display_name are required')), 400
            
            content_type_service: ContentTypeService = app.config.get('CONTENT_TYPE_SERVICE')
            if not content_type_service:
                raise RuntimeError('Content type service is not initialized')

            content_type_service.save_subcategory(content_type, subcategory, display_name, config)

            return jsonify(create_api_response(
                success=True,
                message=f'Subcategory "{display_name}" created successfully'
            ))
            
        except Exception as e:
            logger.error(f"Create subcategory API error: {e}")
            return jsonify(create_api_response(success=False, error=f'Failed to create subcategory: {str(e)}')), 500

    # Private内容访问路由
    @app.route('/private/')
    @app.route('/private/<path:filepath>')
    def private_content(filepath=None):
        """访问私人内容"""
        try:
            from pathlib import Path

            # 私人内容根目录
            output_folder = get_config_value(app, 'paths.output_folder', './data/output')
            private_root = Path(output_folder) / 'private'

            if not private_root.exists():
                private_root.mkdir(parents=True, exist_ok=True)

            if filepath is None:
                # 获取配置管理器
                config_manager = app.config.get('CONFIG_MANAGER')
                
                # 扫描私有内容
                content_type_service = app.config.get('CONTENT_TYPE_SERVICE')
                private_files, private_counts = scan_content_directory(
                    private_root,
                    is_private=True,
                    content_type_service=content_type_service,
                )

                # 扫描公有内容（output/public目录）
                public_root = Path(output_folder) / 'public'
                public_files, public_counts = scan_content_directory(
                    public_root,
                    is_private=False,
                    content_type_service=content_type_service,
                )

                # 合并所有内容
                all_content_files = private_files + public_files

                # 按日期倒序排列 (最新的在前)
                all_content_files.sort(key=lambda x: x['date'], reverse=True)

                # 转换为模板期望的格式
                all_content = []
                for file_info in all_content_files:
                    # 确定URL
                    if file_info['is_private']:
                        url = f"/private/{file_info['filename']}"
                    else:
                        # 公有内容的GitHub Pages链接（动态从配置读取）
                        github_pages_url = get_config_value(app, 'github.pages_url')
                        if github_pages_url:
                            # 使用配置中的完整URL
                            url = f"{github_pages_url.rstrip('/')}/{file_info['filename']}"
                        else:
                            # 从环境变量构建GitHub Pages URL
                            github_username = get_config_value(app, 'github.username')
                            if github_username:
                                url = f"https://{github_username}.github.io/Project_Bach/{file_info['filename']}"
                            else:
                                # 如果没有GitHub配置，公开内容功能不可用
                                logger.warning(f"没有GitHub配置，公开内容 {file_info['filename']} 无法生成有效链接")
                                url = "#github-not-configured"

                    all_content.append({
                        'title': file_info['title'],
                        'url': url,
                        'file': f"/private/{file_info['filename']}" if file_info['is_private'] else url,
                        'date': file_info['date'],
                        'created_at': file_info['date'],
                        'file_size': file_info['size'],
                        'summary': file_info['summary'],
                        'content_type': file_info['content_type'],
                        'is_private': file_info['is_private'],
                        'filename': file_info['filename'],
                        'upload_metadata': file_info.get('upload_metadata', {})
                    })

                # 生成组织化的内容结构
                organized_content = organize_content_by_type(
                    all_content,
                    content_type_service=content_type_service,
                )

                # 渲染私有内容首页
                return render_private_index(app, all_content, organized_content)

            # 使用辅助函数处理文件访问
            return serve_private_file(private_root, filepath)

        except Exception as e:
            logger.error(f"Private content access error: {e}")
            return render_template('web_app/error.html',
                                 error_code=500,
                                 error_message="Failed to access private content"), 500

    # 错误处理
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('web_app/error.html',
                             error_code=404,
                             error_message="Page not found"), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('web_app/error.html',
                             error_code=500,
                             error_message="Internal server error"), 500

    @app.errorhandler(413)
    def too_large_error(error):
        return jsonify({'error': 'File too large'}), 413

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({'error': 'Rate limit exceeded'}), 429

    # 添加模板过滤器
    @app.template_filter('format_date')
    def format_date(date_string, format_str=None):
        """格式化日期字符串"""
        try:
            if isinstance(date_string, str):
                return date_string
            return str(date_string)
        except:
            return "Unknown"

    @app.template_filter('file_size')
    def format_file_size(size_bytes):
        """格式化文件大小"""
        try:
            if size_bytes < 1024:
                return f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                return f"{size_bytes / 1024:.1f} KB"
            elif size_bytes < 1024 * 1024 * 1024:
                return f"{size_bytes / (1024 * 1024):.1f} MB"
            else:
                return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
        except:
            return "Unknown"

    @app.template_filter('truncate_words')
    def truncate_words(text, max_words=30):
        """截断文本到指定单词数"""
        try:
            if not text:
                return ""
            words = text.split()
            if len(words) <= max_words:
                return text
            return ' '.join(words[:max_words]) + '...'
        except:
            return str(text)[:100] + '...' if len(str(text)) > 100 else str(text)

    return app




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
