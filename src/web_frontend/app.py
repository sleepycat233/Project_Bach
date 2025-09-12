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
    config_manager = None
    try:
        if config:
            # 使用提供的配置创建配置管理器
            from types import SimpleNamespace
            config_manager = SimpleNamespace()
            config_manager.config = config
            # 为测试环境添加必需的方法
            config_manager.get_nested_config = lambda section, key=None: config.get(section, {}).get(key, {}) if key else config.get(section, {})
            config_manager.get_full_config = lambda: config
        else:
            # 使用默认配置管理器
            config_manager = ConfigManager()
        app.config['CONFIG_MANAGER'] = config_manager
        
        # 从配置读取文件大小限制 - ConfigManager负责提供默认值
        upload_config = config_manager.get_nested_config('web_frontend', 'upload') or {}
        max_file_size = upload_config.get('max_file_size') or (500 * 1024 * 1024)
        app.config['MAX_CONTENT_LENGTH'] = max_file_size
            
    except Exception as e:
        logger.warning(f"Failed to load config manager: {e}")
        app.config['CONFIG_MANAGER'] = None
        app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024


    # 初始化处理服务
    if config_manager:
        app.config['AUDIO_HANDLER'] = AudioUploadHandler(config_manager)
        app.config['YOUTUBE_HANDLER'] = YouTubeHandler(config_manager)
    else:
        logger.error("配置管理器加载失败，无法初始化处理服务")
        app.config['AUDIO_HANDLER'] = None
        app.config['YOUTUBE_HANDLER'] = None
    app.config['PROCESSING_SERVICE'] = get_processing_service()

    # Tailscale安全中间件
    @app.before_request
    def security_middleware():
        if app.config.get('TESTING'):
            return  # 测试环境跳过安全检查

        # 检查配置管理器中的Tailscale设置
        config_manager = app.config.get('CONFIG_MANAGER')
        if config_manager and config_manager.config.get('tailscale', {}).get('enabled', True) == False:
            return  # Tailscale安全检查被禁用

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

            # 处理子分类信息
            subcategory = request.form.get('subcategory', '')
            custom_subcategory = request.form.get('custom_subcategory', '')
            audio_language = request.form.get('audio_language', 'english')

            # 处理MLX模型选择
            whisper_model = request.form.get('whisper_model', 'whisper-tiny')
            # MLX模型使用简单的模型名称，无需前缀

            # 如果选择了other，使用自定义子分类名
            if subcategory == 'other' and custom_subcategory:
                subcategory = custom_subcategory

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
                    'whisper_model': whisper_model
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
        try:
            from ..utils.config import ConfigManager
            config_manager = ConfigManager()
            content_types = config_manager.get_nested_config('content_classification', 'content_types') or {}
            return jsonify(content_types)
        except Exception as e:
            logger.error(f"Categories API error: {e}")
            # 最基本的回退，确保网站能继续工作
            basic_categories = {
                'lecture': {'icon': '🎓', 'display_name': 'Academic Lecture'},
                'others': {'icon': '📄', 'display_name': 'Others'}
            }
            return jsonify(basic_categories)

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


    @app.route('/api/models/smart-config')
    def api_models_smart_config():
        """MLX Whisper智能模型配置API

        基于配置文件的动态推荐系统，为不同内容类型和语言模式提供智能模型推荐。
        返回 {all: [...], lecture: [...], meeting: [...]} 格式的分类模型列表。
        包含推荐标记、下载状态检查、按优先级排序等功能。
        """
        try:
            from src.utils.config import ConfigManager

            def _check_model_downloaded(repo_name):
                """检查MLX模型是否已在HuggingFace缓存中下载"""
                try:
                    import os
                    from huggingface_hub import snapshot_download
                    from huggingface_hub.utils import LocalEntryNotFoundError

                    # 尝试获取本地缓存路径，如果不存在会抛出异常
                    try:
                        cache_path = snapshot_download(repo_name, local_files_only=True)
                        return os.path.exists(cache_path)
                    except LocalEntryNotFoundError:
                        return False
                except Exception as e:
                    # 如果检查失败，默认为未下载
                    logger.warning(f"Failed to check download status for {repo_name}: {e}")
                    return False

            # 构建MLX模型基础信息
            config_manager = ConfigManager()
            config = config_manager.get_full_config()
            mlx_config = config.get('mlx_whisper', {})
            available_models = mlx_config.get('available_models', [])
            default_model = mlx_config.get('default_model', 'whisper-tiny')

            base_models = []
            for model in available_models:
                if isinstance(model, str):
                    # 解析模型名称
                    if '/' in model:
                        model_name = model.split('/')[-1]
                        repo_name = model
                    else:
                        model_name = model
                        repo_name = f"mlx-community/{model}"

                    is_default = model_name == default_model

                    base_models.append({
                        'value': model_name,
                        'name': model_name,
                        'repo': repo_name,
                        'is_default': is_default
                    })

            # 为Smart Config API添加专用字段
            all_models = []
            for model in base_models:
                # 检查真实下载状态
                is_downloaded = _check_model_downloaded(model['repo'])

                all_models.append({
                    **model,  # 基础信息
                    # 'display_name': f"{model['name']}" + (" (default)" if model['is_default'] else ""),
                    'downloaded': is_downloaded,  # 真实下载状态
                    'config_info': {}  # MLX模型无需复杂配置信息
                })

            # 从配置读取推荐策略
            config = config_manager.get_full_config()
            content_types = config.get('content_classification', {}).get('content_types', {})
            content_type_recommendations = {}
            for content_type, type_config in content_types.items():
                content_type_recommendations[content_type] = type_config.get('recommendations', [])


            def _set_recommendation_flags(model, english_recs, multilingual_recs):
                """为模型设置推荐标志的共用函数"""
                model_value = model.get('value', '')
                model_name = model.get('name', '')

                model['is_english_recommended'] = any(
                    rec_model == model_value or rec_model == model_name
                    for rec_model in english_recs
                )
                model['is_multilingual_recommended'] = any(
                    rec_model == model_value or rec_model == model_name
                    for rec_model in multilingual_recs
                )
                return model

            # 收集所有内容类型的推荐模型（合并用于'all'类别）
            all_english_recs = set()
            all_multilingual_recs = set()

            for content_type, recommendations in content_type_recommendations.items():
                # 只支持新格式：{"english": [...], "multilingual": [...]}
                all_english_recs.update(recommendations.get('english', []))
                all_multilingual_recs.update(recommendations.get('multilingual', []))

            # 生成结果
            result = {}

            # 为每个内容类型生成专用模型列表
            for content_type in content_type_recommendations.keys():
                content_recommendations = content_type_recommendations.get(content_type, {})
                english_recommendations = content_recommendations.get('english', [])
                multilingual_recommendations = content_recommendations.get('multilingual', [])

                content_type_models = []
                for model in all_models:
                    model_copy = model.copy()
                    _set_recommendation_flags(model_copy, english_recommendations, multilingual_recommendations)
                    content_type_models.append(model_copy)

                result[content_type] = content_type_models

            # 为'all'类别生成模型列表
            all_models_with_recommendations = []
            for model in all_models:
                model_copy = model.copy()
                _set_recommendation_flags(model_copy, all_english_recs, all_multilingual_recs)

                # all列表不显示推荐标识，让前端根据语言模式过滤时显示
                model_copy['recommended'] = False
                model_copy['language_mode'] = 'general'

                all_models_with_recommendations.append(model_copy)

            # 按推荐优先级和默认模型排序
            def get_model_complexity(model):
                is_english_recommended = model.get('is_english_recommended', False)
                is_multilingual_recommended = model.get('is_multilingual_recommended', False)
                is_default = model.get('is_default', False)
                model_name = model.get('name', '')

                # 任何推荐的模型都排在前面，然后是默认模型，最后按名称排序
                is_any_recommended = is_english_recommended or is_multilingual_recommended
                return (not is_any_recommended, not is_default, model_name)

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
            import re
            from datetime import datetime

            # 私人内容根目录
            config_manager = app.config.get('CONFIG_MANAGER')
            if config_manager and hasattr(config_manager, 'config'):
                output_folder = config_manager.config.get('paths', {}).get('output_folder', './data/output')
            else:
                output_folder = './data/output'
            private_root = Path(output_folder) / 'private'

            if not private_root.exists():
                private_root.mkdir(parents=True, exist_ok=True)

            if filepath is None:
                # 获取公有和私有内容
                def scan_directory_for_content(directory_path, is_private=False):
                    """扫描目录获取内容文件信息"""
                    content_files = []
                    if not directory_path.exists():
                        return content_files, 0, 0

                    lecture_count = 0
                    youtube_count = 0

                    for html_file in directory_path.glob('*.html'):
                        # 跳过index.html
                        if html_file.name == 'index.html':
                            continue

                        # 解析文件名获取信息
                        filename = html_file.name

                        # 解析日期 (格式: 20250824_034746_...)
                        date_match = re.match(r'(\d{8})_(\d{6})_', filename)
                        if date_match:
                            date_str = date_match.group(1)
                            time_str = date_match.group(2)
                            try:
                                parsed_date = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
                                formatted_date = parsed_date.strftime("%Y-%m-%d %H:%M")
                            except:
                                formatted_date = "Unknown"
                        else:
                            formatted_date = "Unknown"

                        # 生成显示标题和确定内容类型
                        content_type = 'others'
                        if 'youtube' in filename:
                            title = filename.replace('youtube_', '').replace('_result.html', '').replace('_', ' ')
                            content_type = 'youtube'
                            youtube_count += 1
                        elif 'LEC' in filename:
                            # 提取讲座标题
                            title_match = re.search(r'LEC_(.+?)_result\.html', filename)
                            if title_match:
                                title = title_match.group(1).replace('_', ' ')
                            else:
                                title = filename.replace('_result.html', '').replace('_', ' ')
                            content_type = 'lecture'
                            lecture_count += 1
                        else:
                            title = filename.replace('_result.html', '').replace('_', ' ')
                            lecture_count += 1
                            content_type = 'lecture'  # 默认为lecture类型

                        # 尝试从HTML文件中提取摘要
                        summary = "Content summary"
                        try:
                            content = html_file.read_text(encoding='utf-8')
                            # 查找第一个段落内容
                            summary_match = re.search(r'<p[^>]*>(.*?)</p>', content, re.DOTALL)
                            if summary_match:
                                summary_text = re.sub(r'<[^>]+>', '', summary_match.group(1))
                                summary = summary_text.strip()[:150] + "..." if len(summary_text) > 150 else summary_text.strip()
                        except:
                            pass

                        # 尝试从对应的JSON文件读取upload_metadata
                        json_filename = filename.replace('_result.html', '_result.json')
                        json_file = html_file.parent / json_filename
                        upload_metadata = {}

                        if json_file.exists():
                            try:
                                with open(json_file, 'r', encoding='utf-8') as f:
                                    json_data = json.load(f)
                                    upload_metadata = json_data.get('upload_metadata', {})
                            except Exception as e:
                                logger.warning(f"Failed to read JSON metadata from {json_filename}: {e}")

                        content_files.append({
                            'filename': filename,
                            'title': title,
                            'date': formatted_date,
                            'size': html_file.stat().st_size,
                            'content_type': content_type,
                            'summary': summary,
                            'is_private': is_private,
                            'upload_metadata': upload_metadata
                        })

                    return content_files, lecture_count, youtube_count

                # 扫描私有内容
                private_files, private_lecture_count, private_youtube_count = scan_directory_for_content(private_root, is_private=True)

                # 扫描公有内容（output/public目录）
                public_root = Path(output_folder) / 'public'
                public_files, public_lecture_count, public_youtube_count = scan_directory_for_content(public_root, is_private=False)

                # 合并所有内容
                all_content_files = private_files + public_files

                # 按日期倒序排列 (最新的在前)
                all_content_files.sort(key=lambda x: x['date'], reverse=True)

                # 统计计数
                total_lecture_count = private_lecture_count + public_lecture_count
                total_youtube_count = private_youtube_count + public_youtube_count

                # 转换为模板期望的格式
                all_content = []
                for file_info in all_content_files:
                    # 确定URL
                    if file_info['is_private']:
                        url = f"/private/{file_info['filename']}"
                    else:
                        # 公有内容的GitHub Pages链接（如果可用）
                        github_url = f"https://sleepycat233.github.io/Project_Bach/{file_info['filename']}"
                        url = github_url

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
                        'filename': file_info['filename']
                    })

                # 生成organized_content数据结构
                def organize_content_by_type(content_list):
                    """将内容按类型和课程组织为树形结构"""
                    organized = {
                        'lectures': {},
                        'videos': {},
                        'articles': [],
                        'podcasts': []
                    }

                    for content in content_list:
                        content_type = content.get('content_type', 'others')

                        if content_type == 'lecture':
                            # 优先从upload_metadata中获取课程信息
                            upload_metadata = content.get('upload_metadata', {})
                            course_name = "General"  # 默认值

                            # 尝试从upload_metadata中获取课程信息
                            if upload_metadata:
                                # 从subcategory中获取课程代码 (如CS101, PHYS101)
                                subcategory = upload_metadata.get('subcategory', '')
                                if subcategory and subcategory != 'other':
                                    course_name = subcategory
                                # 或者从custom_subcategory中获取
                                elif subcategory == 'other':
                                    custom_subcategory = upload_metadata.get('custom_subcategory', '')
                                    if custom_subcategory:
                                        course_name = custom_subcategory

                            # 如果没有metadata，回退到从文件名解析
                            if course_name == "General":
                                filename = content.get('filename', '')
                                course_match = re.search(r'\d{8}_\d{6}_([A-Z]+\d+)_LEC_', filename)
                                if course_match:
                                    course_name = course_match.group(1)  # 例如 CS101, PHYS101

                            if course_name not in organized['lectures']:
                                organized['lectures'][course_name] = []

                            organized['lectures'][course_name].append({
                                'title': content.get('title', 'Untitled'),
                                'url': content.get('url', '#'),
                                'date': content.get('date', ''),
                                'filename': filename
                            })

                        elif content_type == 'youtube':
                            # YouTube视频按系列组织 (如果需要的话)
                            series_name = "YouTube Videos"  # 默认系列名
                            if series_name not in organized['videos']:
                                organized['videos'][series_name] = []

                            organized['videos'][series_name].append({
                                'title': content.get('title', 'Untitled'),
                                'url': content.get('url', '#'),
                                'date': content.get('date', ''),
                                'filename': content.get('filename', '')
                            })

                    # 对每个课程内的内容按日期排序 (最新在前)
                    for course_name, lectures in organized['lectures'].items():
                        lectures.sort(key=lambda x: x.get('date', ''), reverse=True)

                    for series_name, videos in organized['videos'].items():
                        videos.sort(key=lambda x: x.get('date', ''), reverse=True)

                    return organized

                # 生成组织化的内容结构
                organized_content = organize_content_by_type(all_content)

                # 计算内容统计
                content_counts = {
                    'lecture': len([c for c in all_content if c.get('content_type') == 'lecture']),
                    'youtube': len([c for c in all_content if c.get('content_type') == 'youtube']),
                    'rss': len([c for c in all_content if c.get('content_type') == 'rss']),
                    'podcast': len([c for c in all_content if c.get('content_type') == 'podcast']),
                    'public': len([c for c in all_content if not c.get('is_private', True)]),
                    'private': len([c for c in all_content if c.get('is_private', True)])
                }

                total_content = len(all_content)

                # 获取GitHub Pages URL
                github_pages_url = "https://sleepycat233.github.io/Project_Bach"  # 默认值
                if config_manager and hasattr(config_manager, 'config'):
                    github_pages_url = config_manager.config.get('github', {}).get('website', {}).get('pages_url', github_pages_url)

                # 使用新的私有页面模板，传入合并的内容数据
                return render_template('web_app/private_index.html',
                                     title="🔒 Private Content Hub",
                                     site_title="Project Bach",
                                     description="私人内容区域 - 浏览所有内容，支持公私筛选",
                                     all_content=all_content,  # 传入合并的内容数据
                                     organized_content=organized_content,  # 传入组织化的内容结构
                                     content_counts=content_counts,
                                     stats={
                                         'total_processed': total_content,
                                         'this_month': total_content,
                                         'total_hours': '0h',
                                         'success_rate': '100%'
                                     },
                                     github_pages_url=github_pages_url,  # 传入GitHub Pages URL
                                     is_private=True)

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
                return render_template('web_app/error.html',
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