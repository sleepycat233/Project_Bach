#!/usr/bin/env python3.11
"""
模板引擎服务
基于Jinja2的模板渲染系统，支持主题和响应式布局
"""

import logging
import jinja2
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import markdown


class TemplateEngine:
    """模板引擎服务"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化模板引擎
        
        Args:
            config: 模板配置
        """
        self.config = config
        self.logger = logging.getLogger('project_bach.template_engine')
        
        # 模板配置
        self.template_dir = Path(config.get('base_dir', config.get('template_dir', './templates')))
        self.theme = config.get('theme', 'default')
        self.site_title = config.get('site_title', 'Project Bach')
        self.site_description = config.get('site_description', 'AI-powered Content Processing Results')
        
        # 创建模板目录
        self.template_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化Jinja2环境
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.template_dir)),
            autoescape=jinja2.select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # 注册自定义过滤器
        self._register_custom_filters()
        
        # 创建默认模板
        self._ensure_default_templates()
        
        self.logger.info(f"模板引擎初始化完成，主题: {self.theme}")
    
    def _register_custom_filters(self):
        """注册自定义Jinja2过滤器"""
        
        def markdown_filter(text):
            """Markdown转HTML过滤器"""
            if not text:
                return ''
            return markdown.markdown(text, extensions=['extra', 'codehilite'])
        
        def truncate_words_filter(text, length=50):
            """按词数截断文本"""
            if not text:
                return ''
            words = text.split()
            if len(words) <= length:
                return text
            return ' '.join(words[:length]) + '...'
        
        def format_date_filter(date_str, format_str='%Y-%m-%d'):
            """格式化日期"""
            try:
                if isinstance(date_str, str):
                    dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                else:
                    dt = date_str
                return dt.strftime(format_str)
            except:
                return str(date_str)
        
        def file_size_filter(size_bytes):
            """格式化文件大小"""
            try:
                size_bytes = int(size_bytes)
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if size_bytes < 1024:
                        return f"{size_bytes:.1f} {unit}"
                    size_bytes /= 1024
                return f"{size_bytes:.1f} TB"
            except:
                return str(size_bytes)
        
        def json_pretty_filter(data):
            """美化JSON格式"""
            try:
                return json.dumps(data, indent=2, ensure_ascii=False)
            except:
                return str(data)
        
        # 时间距离过滤器
        def timeago_filter(value):
            """时间距离过滤器"""
            if not value:
                return "Recently"
            try:
                if isinstance(value, str):
                    from datetime import datetime
                    dt = datetime.fromisoformat(value.replace('Z', '+00:00').replace('+00:00', ''))
                else:
                    dt = value
                now = datetime.now()
                diff = now - dt
                if diff.days > 0:
                    return f"{diff.days} days ago"
                elif diff.seconds > 3600:
                    return f"{diff.seconds // 3600} hours ago"
                else:
                    return f"{diff.seconds // 60} minutes ago"
            except:
                return "Recently"
        
        # 注册过滤器
        self.env.filters['markdown'] = markdown_filter
        self.env.filters['truncate_words'] = truncate_words_filter
        self.env.filters['format_date'] = format_date_filter
        self.env.filters['file_size'] = file_size_filter
        self.env.filters['json_pretty'] = json_pretty_filter
        self.env.filters['timeago'] = timeago_filter
    
    def _ensure_default_templates(self):
        """确保默认模板存在"""
        # 不再硬编码模板，直接使用文件系统中的模板
        # 这些硬编码模板已被删除，现在使用templates/目录下的实际文件
        templates = {}
        
        for template_name, template_content in templates.items():
            template_path = self.template_dir / template_name
            if not template_path.exists():
                template_path.write_text(template_content, encoding='utf-8')
                self.logger.info(f"创建默认模板: {template_name}")
    
    def _get_base_template(self) -> str:
        """获取基础模板内容"""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{{ description or site_description }}">
    <meta name="keywords" content="{{ keywords | join(', ') if keywords else '' }}">
    <meta name="author" content="{{ author or 'Project Bach' }}">

    <title>{{ title }}{% if title != site_title %} - {{ site_title }}{% endif %}</title>
    
    <!-- 响应式样式 -->
    <style>
        /* CSS变量定义 */
        :root {
            --primary-color: #007AFF;
            --secondary-color: #5856D6;
            --success-color: #34C759;
            --warning-color: #FF9500;
            --error-color: #FF3B30;
            --bg-color: #FFFFFF;
            --text-color: #1D1D1F;
            --text-secondary: #8E8E93;
            --border-color: #D1D1D6;
            --card-bg: #F2F2F7;
        }
        
        /* 暗色模式支持 - 已暂时禁用，默认使用light mode */
        /*
        @media (prefers-color-scheme: dark) {
            :root {
                --bg-color: #000000;
                --text-color: #FFFFFF;
                --text-secondary: #8E8E93;
                --border-color: #38383A;
                --card-bg: #1C1C1E;
            }
        }
        */
        
        /* 基础样式 */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            line-height: 1.6;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        /* 响应式布局 */
        @media (max-width: 768px) {
            .container {
                padding: 15px;
            }
        }
        
        /* 头部样式 */
        .header {
            border-bottom: 2px solid var(--primary-color);
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 2.5em;
            font-weight: 700;
            color: var(--primary-color);
            margin-bottom: 10px;
        }
        
        .header p {
            color: var(--text-secondary);
            font-size: 1.1em;
        }
        
        /* 导航样式 */
        .nav {
            margin-top: 20px;
        }
        
        .nav a {
            color: var(--primary-color);
            text-decoration: none;
            margin-right: 20px;
            padding: 8px 16px;
            border-radius: 8px;
            transition: background-color 0.2s;
        }
        
        .nav a:hover {
            background-color: var(--card-bg);
        }
        
        /* 主内容样式 */
        .content {
            margin-top: 30px;
        }
        
        /* 卡片样式 */
        .card {
            background-color: var(--card-bg);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid var(--border-color);
        }
        
        /* 表格样式 */
        .table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        
        .table th,
        .table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }
        
        .table th {
            font-weight: 600;
            background-color: var(--card-bg);
        }
        
        .table-striped tr:nth-child(even) {
            background-color: var(--card-bg);
        }
        
        /* 代码样式 */
        .code-block {
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 16px;
            font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
            font-size: 0.9em;
            overflow-x: auto;
        }
        
        /* 引用样式 */
        .quote {
            border-left: 4px solid var(--primary-color);
            padding: 16px 20px;
            margin: 20px 0;
            background-color: var(--card-bg);
            font-style: italic;
        }
        
        /* 按钮样式 */
        .btn {
            display: inline-block;
            padding: 10px 20px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 500;
            transition: all 0.2s;
            border: none;
            cursor: pointer;
        }
        
        .btn-primary {
            background-color: var(--primary-color);
            color: white;
        }
        
        .btn-primary:hover {
            opacity: 0.8;
        }
        
        /* 页脚样式 */
        .footer {
            margin-top: 60px;
            padding-top: 30px;
            border-top: 1px solid var(--border-color);
            text-align: center;
            color: var(--text-secondary);
        }
        
        .footer a {
            color: var(--primary-color);
            text-decoration: none;
        }
        
        /* 工具提示 */
        .tooltip {
            position: relative;
            cursor: help;
        }
        
        /* 响应式图片 */
        img {
            max-width: 100%;
            height: auto;
        }
        
        /* 滚动条样式 */
        ::-webkit-scrollbar {
            width: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: var(--card-bg);
        }
        
        ::-webkit-scrollbar-thumb {
            background: var(--border-color);
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: var(--text-secondary);
        }
    </style>
    
    {% block extra_head %}{% endblock %}
</head>
<body>
    <div class="container">
        <!-- 页面头部 -->
        <header class="header">
            <h1>{{ site_title }}</h1>
            <p>{{ site_description }}</p>
            
            <nav class="nav">
                <a href="index.html">🏠 Home</a>
                <a href="archive.html">📋 Archive</a>
                <a href="stats.html">📊 Statistics</a>
                <a href="about.html">ℹ️ About</a>
            </nav>
        </header>
        
        <!-- 主内容区域 -->
        <main class="content">
            {% block content %}{% endblock %}
        </main>
        
        <!-- 页脚 -->
        <footer class="footer">
            <p><strong>{{ site_title }}</strong> - AI-powered Content Processing & Analysis</p>
            <p><em>Last updated: {{ current_time | format_date('%Y-%m-%d %H:%M:%S') }}</em></p>
            <p>
                <a href="https://github.com/project-bach" target="_blank">🔗 GitHub</a> |
                <a href="mailto:contact@project-bach.com">📧 Contact</a>
            </p>
        </footer>
    </div>
    
    {% block extra_scripts %}{% endblock %}
</body>
</html>'''
    
    def _get_content_template(self) -> str:
        """获取内容页模板"""
        return '''{% extends "base.html" %}

{% block content %}
<article class="card">
    <header>
        <h1>{{ content.title }}</h1>
        <div class="meta" style="margin-top: 15px; color: var(--text-secondary);">
            <span>📅 {{ content.processed_time | format_date }}</span>
            <span style="margin-left: 20px;">🎵 {{ content.original_file }}</span>
            {% if content.file_size %}
            <span style="margin-left: 20px;">📦 {{ content.file_size | file_size }}</span>
            {% endif %}
            {% if content.audio_duration %}
            <span style="margin-left: 20px;">⏱️ {{ content.audio_duration }}</span>
            {% endif %}
        </div>
    </header>
    
    <div style="margin-top: 30px;">
        <section class="summary">
            <h2>📄 Content Summary</h2>
            <div style="margin-top: 15px; padding: 20px; background-color: var(--card-bg); border-radius: 8px;">
                {{ content.summary | markdown | safe }}
            </div>
        </section>

        <section class="mindmap" style="margin-top: 30px;">
            <h2>🧠 Mind Map</h2>
            <div style="margin-top: 15px; padding: 20px; background-color: var(--card-bg); border-radius: 8px;">
                {{ content.mindmap | markdown | safe }}
            </div>
        </section>
        
        {% if content.anonymized_names and content.anonymized_names | length > 0 %}
        <section class="anonymization" style="margin-top: 30px;">
            <h2>🔒 Name Anonymization</h2>
            <div style="margin-top: 15px;">
                <p>This processing anonymized <strong>{{ content.anonymized_names | length }}</strong> personal names:</p>

                <table class="table table-striped" style="margin-top: 15px;">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Anonymized Name</th>
                            <th>Type</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for original, anonymous in content.anonymized_names.items() %}
                        <tr>
                            <td>{{ loop.index }}</td>
                            <td>{{ anonymous }}</td>
                            <td>Name</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>

                <p style="margin-top: 15px; font-style: italic; color: var(--text-secondary);">
                    💡 For privacy protection, all personal names have been replaced with virtual names
                </p>
            </div>
        </section>
        {% endif %}
        
        {% if content.statistics %}
        <section class="statistics" style="margin-top: 30px;">
            <h2>📊 Processing Statistics</h2>
            <table class="table table-striped" style="margin-top: 15px;">
                <tbody>
                    <tr>
                        <td>Summary Length</td>
                        <td>{{ content.summary | length }} characters</td>
                    </tr>
                    <tr>
                        <td>Mind Map Length</td>
                        <td>{{ content.mindmap | length }} characters</td>
                    </tr>
                    <tr>
                        <td>Anonymized Names</td>
                        <td>{{ content.anonymized_names | length }} names</td>
                    </tr>
                    {% if content.processing_duration %}
                    <tr>
                        <td>Processing Time</td>
                        <td>{{ content.processing_duration }}</td>
                    </tr>
                    {% endif %}
                </tbody>
            </table>
        </section>
        {% endif %}
    </div>
</article>

<!-- 返回按钮 -->
<div style="margin-top: 30px; text-align: center;">
    <a href="index.html" class="btn btn-primary">🔙 Back to Home</a>
</div>
{% endblock %}'''
    
    def _get_index_template(self) -> str:
        """获取首页模板"""
        return '''{% extends "base.html" %}

{% block content %}
<div class="index">
    <div class="card">
        <h2>🎵 Audio Processing Results</h2>
        <p>Intelligent Audio Processing & Content Analysis Platform</p>

        <div style="margin-top: 20px;">
            <span style="background-color: var(--success-color); color: white; padding: 4px 12px; border-radius: 16px; font-size: 0.9em;">
                📊 Total {{ results | length }} processing results
            </span>
        </div>
    </div>
    
    {% if results and results | length > 0 %}
    <div class="results-section">
        <h2 style="margin-top: 30px;">📋 Latest Results</h2>
        
        {% for result in results[:10] %}
        <article class="card result-item" style="margin-top: 20px;">
            <h3>
                <a href="{{ result.file }}" style="color: var(--primary-color); text-decoration: none;">
                    {{ result.title }}
                </a>
            </h3>
            <div class="meta" style="color: var(--text-secondary); font-size: 0.9em; margin-top: 8px;">
                <span>📅 {{ result.date | format_date }}</span>
                {% if result.file_size %}
                <span style="margin-left: 15px;">📦 {{ result.file_size | file_size }}</span>
                {% endif %}
            </div>
            <p style="margin-top: 12px; color: var(--text-secondary);">
                {{ result.summary | truncate_words(30) }}
            </p>
            <div style="margin-top: 15px;">
                <a href="{{ result.file }}" class="btn btn-primary" style="font-size: 0.9em; padding: 6px 16px;">
                    View Details →
                </a>
            </div>
        </article>
        {% endfor %}
        
        {% if results | length > 10 %}
        <div style="text-align: center; margin-top: 30px;">
            <a href="archive.html" class="btn btn-primary">View All {{ results | length }} Results →</a>
        </div>
        {% endif %}
    </div>
    
    <!-- 统计概览 -->
    <div class="stats-overview card" style="margin-top: 30px;">
        <h2>📊 Statistics Overview</h2>
        <table class="table table-striped" style="margin-top: 15px;">
            <tbody>
                <tr>
                    <td>Total Processed</td>
                    <td><strong>{{ results | length }}</strong></td>
                </tr>
                <tr>
                    <td>This Month</td>
                    <td><strong>{{ stats.this_month if stats else 0 }}</strong></td>
                </tr>
                <tr>
                    <td>This Week</td>
                    <td><strong>{{ stats.this_week if stats else 0 }}</strong></td>
                </tr>
                <tr>
                    <td>Last Updated</td>
                    <td>{{ current_time | format_date('%Y-%m-%d %H:%M:%S') }}</td>
                </tr>
            </tbody>
        </table>
    </div>
    
    {% else %}
    <div class="card empty-state" style="text-align: center; margin-top: 30px;">
        <h3>🎵 No Processing Results Yet</h3>
        <p style="color: var(--text-secondary); margin-top: 15px;">
            No audio files have been processed yet. Please place audio files in the monitoring folder to start processing.
        </p>
    </div>
    {% endif %}
    
    <!-- 快速导航 -->
    <div class="quick-nav card" style="margin-top: 30px;">
        <h2>🔍 Quick Navigation</h2>
        <div style="margin-top: 20px; display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
            <a href="archive.html" style="text-decoration: none;">
                <div style="padding: 20px; background-color: var(--card-bg); border-radius: 8px; text-align: center; transition: transform 0.2s;">
                    <div style="font-size: 2em;">📋</div>
                    <div style="margin-top: 10px; font-weight: 500; color: var(--text-color);">Complete Archive</div>
                    <div style="color: var(--text-secondary); font-size: 0.9em;">View all results</div>
                </div>
            </a>
            <a href="stats.html" style="text-decoration: none;">
                <div style="padding: 20px; background-color: var(--card-bg); border-radius: 8px; text-align: center;">
                    <div style="font-size: 2em;">📈</div>
                    <div style="margin-top: 10px; font-weight: 500; color: var(--text-color);">Data Statistics</div>
                    <div style="color: var(--text-secondary); font-size: 0.9em;">Processing result analysis</div>
                </div>
            </a>
            <a href="search.html" style="text-decoration: none;">
                <div style="padding: 20px; background-color: var(--card-bg); border-radius: 8px; text-align: center;">
                    <div style="font-size: 2em;">🔎</div>
                    <div style="margin-top: 10px; font-weight: 500; color: var(--text-color);">Search Function</div>
                    <div style="color: var(--text-secondary); font-size: 0.9em;">Quick content search</div>
                </div>
            </a>
            <a href="about.html" style="text-decoration: none;">
                <div style="padding: 20px; background-color: var(--card-bg); border-radius: 8px; text-align: center;">
                    <div style="font-size: 2em;">ℹ️</div>
                    <div style="margin-top: 10px; font-weight: 500; color: var(--text-color);">About Project</div>
                    <div style="color: var(--text-secondary); font-size: 0.9em;">Project Bach</div>
                </div>
            </a>
        </div>
    </div>
</div>
{% endblock %}'''
    
    def _get_error_template(self) -> str:
        """获取错误页面模板"""
        return '''{% extends "base.html" %}

{% block content %}
<div class="error-page card" style="text-align: center; margin-top: 30px;">
    <div style="font-size: 4em; color: var(--error-color);">⚠️</div>
    <h1 style="margin-top: 20px; color: var(--error-color);">An Error Occurred</h1>

    {% if error_message %}
    <p style="margin-top: 15px; color: var(--text-secondary);">{{ error_message }}</p>
    {% endif %}

    <div style="margin-top: 30px;">
        <a href="index.html" class="btn btn-primary">🔙 Back to Home</a>
    </div>
</div>
{% endblock %}'''
    
    def load_template(self, template_name: str) -> Optional[jinja2.Template]:
        """加载模板
        
        Args:
            template_name: 模板名称
            
        Returns:
            模板对象
        """
        try:
            template = self.env.get_template(template_name)
            self.logger.debug(f"加载模板成功: {template_name}")
            return template
        except jinja2.TemplateNotFound:
            self.logger.error(f"模板未找到: {template_name}")
            return None
        except Exception as e:
            self.logger.error(f"加载模板失败 {template_name}: {str(e)}")
            return None
    
    def render_template(self, template_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """渲染模板
        
        Args:
            template_name: 模板名称
            context: 模板上下文变量
            
        Returns:
            渲染结果
        """
        self.logger.info(f"渲染模板: {template_name}")
        
        try:
            template = self.load_template(template_name)
            if not template:
                return {
                    'success': False,
                    'error': f'模板未找到: {template_name}'
                }
            
            # 添加默认上下文变量和静态Flask对象
            full_context = self._build_context(context)
            full_context.update(self._get_static_flask_context())
            
            # 渲染模板
            rendered_content = template.render(**full_context)
            
            return {
                'success': True,
                'content': rendered_content,
                'template_name': template_name,
                'context_keys': list(full_context.keys())
            }
            
        except jinja2.TemplateError as e:
            self.logger.error(f"模板渲染错误 {template_name}: {str(e)}")
            return {
                'success': False,
                'error': f'模板渲染错误: {str(e)}',
                'template_name': template_name
            }
        except Exception as e:
            self.logger.error(f"模板渲染异常 {template_name}: {str(e)}")
            return {
                'success': False,
                'error': f'渲染异常: {str(e)}',
                'template_name': template_name
            }
    
    def _get_static_flask_context(self) -> Dict[str, Any]:
        """获取静态Flask上下文对象
        
        Returns:
            静态Flask上下文
        """
        class StaticRequest:
            """静态request对象"""
            @property
            def endpoint(self):
                return 'index'
            
            @property
            def url_rule(self):
                return type('Rule', (), {'rule': '/'})()
        
        return {
            'url_for': self._static_url_for,
            'request': StaticRequest(),
            'config': {},
            'session': {}
        }
    
    def _static_url_for(self, endpoint: str, **kwargs) -> str:
        """静态版本的url_for函数，用于GitHub Pages环境
        
        Args:
            endpoint: 路由端点名称或'static'
            **kwargs: Flask url_for的其他参数，特别是filename
            
        Returns:
            静态URL路径
        """
        # 处理静态资源文件 url_for('static', filename='css/style.css')
        if endpoint == 'static':
            filename = kwargs.get('filename', '')
            # 确保返回正确的静态文件路径，不要加上.html后缀
            return f'static/{filename}'
        
        # 处理页面路由
        page_mappings = {
            'lectures': 'lectures.html',
            'videos': 'videos.html', 
            'articles': 'articles.html',
            'podcasts': 'podcasts.html',
            'upload_page': 'upload.html',
            'all_content': 'archive.html',
            'index': 'index.html'
        }
        return page_mappings.get(endpoint, f'{endpoint}.html')
    
    def _build_context(self, custom_context: Dict[str, Any]) -> Dict[str, Any]:
        """构建完整的模板上下文
        
        Args:
            custom_context: 自定义上下文
            
        Returns:
            完整上下文
        """
        # 基础上下文
        base_context = {
            'site_title': self.site_title,
            'site_description': self.site_description,
            'theme': self.theme,
            'current_time': datetime.now(),
            'build_time': datetime.now().isoformat(),
        }
        
        # 合并上下文
        full_context = {**base_context, **custom_context}
        
        return full_context
    
    def render_content_page(self, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """渲染内容页面
        
        Args:
            content_data: 内容数据
            
        Returns:
            渲染结果
        """
        context = {
            'title': content_data.get('title', '未知标题'),
            'description': content_data.get('summary', '')[:200],
            'keywords': content_data.get('keywords', []),
            'content': content_data
        }
        
        return self.render_template('github_pages/content.html', context)
    
    def render_index_page(self, results: List[Dict[str, Any]], stats: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """渲染首页
        
        Args:
            results: 结果列表
            stats: 统计信息
            
        Returns:
            渲染结果
        """
        context = {
            'title': self.site_title,
            'description': f'Total {len(results)} audio processing results',
            'keywords': ['audio processing', 'AI analysis', 'result index'],
            'results': results,
            'stats': stats or {}
        }
        
        return self.render_template('github_pages/index.html', context)
    
    def render_error_page(self, error_message: str, error_code: Optional[int] = None) -> Dict[str, Any]:
        """渲染错误页面
        
        Args:
            error_message: 错误消息
            error_code: 错误代码
            
        Returns:
            渲染结果
        """
        context = {
            'title': f'Error {error_code}' if error_code else 'An Error Occurred',
            'description': 'An error occurred while processing the page',
            'error_message': error_message,
            'error_code': error_code
        }
        
        return self.render_template('web_app/error.html', context)
    
    def validate_template_files(self) -> Dict[str, Any]:
        """验证模板文件
        
        Returns:
            验证结果
        """
        required_templates = ['github_pages/index.html', 'github_pages/content.html', 'web_app/error.html']
        validation_results = {}
        all_valid = True
        
        for template_name in required_templates:
            template_path = self.template_dir / template_name
            
            if not template_path.exists():
                validation_results[template_name] = {
                    'exists': False,
                    'valid': False,
                    'error': '文件不存在'
                }
                all_valid = False
                continue
            
            try:
                # 尝试加载模板
                template = self.env.get_template(template_name)
                
                # 尝试渲染测试（空上下文）
                try:
                    template.render(
                        site_title='Test',
                        site_description='Test',
                        current_time=datetime.now()
                    )
                    validation_results[template_name] = {
                        'exists': True,
                        'valid': True,
                        'size_bytes': template_path.stat().st_size
                    }
                except jinja2.UndefinedError as e:
                    # 未定义变量错误是正常的，因为我们用的是空上下文
                    validation_results[template_name] = {
                        'exists': True,
                        'valid': True,
                        'size_bytes': template_path.stat().st_size,
                        'note': '需要完整上下文'
                    }
                    
            except jinja2.TemplateSyntaxError as e:
                validation_results[template_name] = {
                    'exists': True,
                    'valid': False,
                    'error': f'语法错误: {str(e)}'
                }
                all_valid = False
            except Exception as e:
                validation_results[template_name] = {
                    'exists': True,
                    'valid': False,
                    'error': f'加载失败: {str(e)}'
                }
                all_valid = False
        
        return {
            'all_valid': all_valid,
            'templates': validation_results,
            'template_dir': str(self.template_dir)
        }
    
    def get_theme_info(self) -> Dict[str, Any]:
        """获取主题信息
        
        Returns:
            主题信息
        """
        return {
            'current_theme': self.theme,
            'template_dir': str(self.template_dir),
            'available_templates': [
                f.name for f in self.template_dir.glob('*.html')
            ] if self.template_dir.exists() else [],
            'custom_filters': [
                'markdown', 'truncate_words', 'format_date', 
                'file_size', 'json_pretty'
            ]
        }


if __name__ == '__main__':
    # 测试模板引擎
    test_config = {
        'template_dir': './test_templates',
        'theme': 'default',
        'site_title': 'Project Bach 测试',
        'site_description': 'AI音频处理结果发布测试'
    }
    
    # 创建模板引擎
    template_engine = TemplateEngine(test_config)
    
    # 验证模板
    validation_result = template_engine.validate_template_files()
    print(f"模板验证结果: {validation_result['all_valid']}")
    
    if validation_result['all_valid']:
        # 测试内容页面渲染
        test_content = {
            'title': '测试音频处理结果',
            'summary': '这是一个测试摘要，包含了音频处理的主要内容。',
            'mindmap': '''# 测试思维导图
## 主要内容
- 音频分析
- 内容提取''',
            'processed_time': '2025-08-21T10:30:00',
            'original_file': 'test.mp3',
            'anonymized_names': {'张三': '王明'},
            'file_size': '5242880',  # 5MB
            'audio_duration': '8分32秒'
        }
        
        content_result = template_engine.render_content_page(test_content)
        
        if content_result['success']:
            print("✅ 内容页面渲染成功")
            print(f"HTML长度: {len(content_result['content'])} 字符")
        else:
            print(f"❌ 内容页面渲染失败: {content_result['error']}")
        
        # 测试首页渲染
        test_results = [
            {'title': '音频1', 'date': '2025-08-21', 'file': 'audio1.html', 'summary': '音频1摘要'},
            {'title': '音频2', 'date': '2025-08-20', 'file': 'audio2.html', 'summary': '音频2摘要'}
        ]
        
        index_result = template_engine.render_index_page(test_results, {'this_month': 2, 'this_week': 1})
        
        if index_result['success']:
            print("✅ 首页渲染成功")
        else:
            print(f"❌ 首页渲染失败: {index_result['error']}")
    else:
        print("❌ 模板验证失败")
        for template, result in validation_result['templates'].items():
            if not result['valid']:
                print(f"  {template}: {result.get('error', '未知错误')}")
    
    # 获取主题信息
    theme_info = template_engine.get_theme_info()
    print(f"当前主题: {theme_info['current_theme']}")
    print(f"可用模板: {len(theme_info['available_templates'])} 个")
    
    print("✅ 模板引擎测试完成")