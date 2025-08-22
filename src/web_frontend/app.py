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
        # 获取内容类型配置
        content_types = {
            'lecture': {'icon': '🎓', 'name': 'Academic Lecture'},
            'youtube': {'icon': '📺', 'name': 'YouTube Video'}
        }
        
        return render_template('upload.html', content_types=content_types)
    
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
            
            # 处理上传
            handler = app.config['AUDIO_HANDLER']
            result = handler.process_upload(
                file=file,
                content_type=content_type,
                privacy_level=privacy_level,
                metadata={
                    'lecture_series': request.form.get('lecture_series', ''),
                    'tags': request.form.get('tags', ''),
                    'description': request.form.get('description', '')
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
            
            content_type = request.form.get('content_type', 'youtube')
            
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