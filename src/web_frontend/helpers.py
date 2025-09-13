#!/usr/bin/env python3
"""
Web Frontend辅助函数模块

提供app.py中常用的辅助函数，减少代码重复并提高可维护性。
Phase 7.1: API重构和代码优化的一部分。
"""

import json
import re
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from collections import Counter

from ..utils.config import DEFAULT_CONTENT_TYPES

logger = logging.getLogger(__name__)


def get_config_value(app, key_path: str, default=None):
    """统一配置获取助手

    Args:
        app: Flask应用实例
        key_path: 配置键路径，用点分隔 (如 'web_frontend.upload' 或 'a.b.c.d')
        default: 默认值

    Returns:
        配置值或默认值
    """
    config_manager = app.config.get('CONFIG_MANAGER')
    if config_manager:
        keys = key_path.split('.')
        return config_manager.get_nested_config(*keys) or default
    return default


def _get_content_types_config_with_fallback(config_manager):
    """获取内容类型配置，带默认值回退

    Args:
        config_manager: 配置管理器或None

    Returns:
        内容类型配置字典
    """
    if config_manager:
        return config_manager.get_content_types_config()
    return DEFAULT_CONTENT_TYPES


def get_content_types_config(app):
    """获取内容类型配置的统一入口

    Args:
        app: Flask应用实例

    Returns:
        内容类型配置字典
    """
    config_manager = app.config.get('CONFIG_MANAGER')
    return _get_content_types_config_with_fallback(config_manager)


def create_api_response(success: bool = True, data: Any = None,
                       message: Optional[str] = None, error: Optional[str] = None) -> Dict[str, Any]:
    """标准API响应格式

    Args:
        success: 操作是否成功
        data: 响应数据
        message: 成功消息
        error: 错误信息

    Returns:
        标准格式的响应字典
    """
    response = {
        'success': success,
        'timestamp': datetime.now().isoformat()
    }

    if data is not None:
        response['data'] = data
    if message:
        response['message'] = message
    if error:
        response['error'] = error

    return response


def scan_content_directory(directory_path: Path, is_private: bool = False, config_manager=None) -> tuple:
    """扫描目录获取内容文件信息

    Args:
        directory_path: 目录路径
        is_private: 是否为私有内容
        config_manager: 配置管理器，用于获取内容类型定义

    Returns:
        (content_files列表, 按类型统计的计数字典)
    """
    content_files = []
    if not directory_path.exists():
        return content_files, {}

    # 从配置获取支持的内容类型
    content_types_config = _get_content_types_config_with_fallback(config_manager)

    supported_types = {}
    for content_type, config in content_types_config.items():
        supported_types[content_type] = config.get('display_name', content_type.title())

    # 初始化计数器
    type_counts = {content_type: 0 for content_type in supported_types.keys()}
    type_counts['others'] = 0  # 确保有others类别

    for html_file in directory_path.glob('*.html'):
        # 跳过index.html
        if html_file.name == 'index.html':
            continue

        # 获取基础文件信息
        filename = html_file.name

        # 优先从JSON文件读取所有metadata
        json_filename = filename.replace('_result.html', '_result.json')
        json_file = html_file.parent / json_filename

        # 默认值
        title = filename.replace('_result.html', '').replace('_', ' ')
        content_type = 'others'
        summary = "Content summary"
        upload_metadata = {}
        formatted_date = html_file.stat().st_mtime
        formatted_date = datetime.fromtimestamp(formatted_date).strftime("%Y-%m-%d %H:%M")

        if not json_file.exists():
            logger.warning(f"Missing JSON metadata for {html_file.name} at {json_file}, skipping...")
            continue

        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)

                # 从统一的metadata结构读取
                metadata = json_data['metadata']

                # 获取content_type
                content_type = metadata['content_type']

                # 获取标题
                if content_type == 'youtube':
                    title = metadata.get('title') or metadata.get('video_metadata', {}).get('title', title)
                else:
                    title = metadata.get('title', title)

                # 获取摘要
                summary = json_data.get('summary', summary)[:150] + "..." if len(json_data.get('summary', '')) > 150 else json_data.get('summary', summary)

                # 获取处理时间
                processed_time = metadata['processed_time']
                try:
                    parsed_date = datetime.fromisoformat(processed_time.replace('Z', '+00:00'))
                    formatted_date = parsed_date.strftime("%Y-%m-%d %H:%M")
                except:
                    pass  # 使用文件时间作为fallback

                # 为organize_content_by_type使用
                upload_metadata = {
                    'subcategory': metadata.get('subcategory', '')
                }

        except Exception as e:
            logger.warning(f"Failed to parse JSON metadata from {json_file}: {e}, skipping...")
            continue

        # 更新计数器
        if content_type in type_counts:
            type_counts[content_type] += 1
        else:
            type_counts['others'] += 1

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

    return content_files, type_counts




def organize_content_by_type(content_list: List[Dict[str, Any]], config_manager=None) -> Dict[str, Any]:
    """将内容按类型和课程组织为树形结构

    Args:
        content_list: 内容文件列表
        config_manager: 配置管理器，用于获取内容类型定义

    Returns:
        组织化的内容结构
    """
    # 从配置获取支持的内容类型
    content_types_config = _get_content_types_config_with_fallback(config_manager)

    supported_types = set(content_types_config.keys())

    # 动态初始化organized结构，基于配置判断结构类型
    organized = {}
    for content_type in supported_types:
        config = content_types_config[content_type]
        has_subcategory = config.get('has_subcategory', False)

        if has_subcategory:
            # 有subcategory的类型用字典结构 (如 lectures, meetings)
            organized[f'{content_type}s'] = {}
        elif content_type == 'youtube':
            # YouTube视频特殊处理
            organized['videos'] = {}
        else:
            # 其他类型用列表结构
            organized[f'{content_type}s'] = []

    for content in content_list:
        content_type = content.get('content_type', 'others')

        # 动态处理有subcategory的内容类型
        config = content_types_config.get(content_type, {})
        has_subcategory = config.get('has_subcategory', False)

        if has_subcategory and f'{content_type}s' in organized:
            # 获取subcategory信息
            upload_metadata = content.get('upload_metadata', {})
            category_name = "General"  # 默认值

            # 尝试从upload_metadata中获取分类信息
            if upload_metadata:
                subcategory = upload_metadata.get('subcategory', '')
                if subcategory:
                    category_name = subcategory

            # 如果没有metadata，尝试从文件名解析
            if category_name == "General":
                filename = content.get('filename', '')
                # 通用模式：查找类型标识
                type_pattern = {'lecture': r'_LEC_', 'meeting': r'_MEE_'}
                if content_type in type_pattern:
                    match = re.search(rf'\d{{8}}_\d{{6}}_([A-Z]+\d+){type_pattern[content_type]}', filename)
                    if match:
                        category_name = match.group(1)

            # 添加到对应分类
            target_dict = organized[f'{content_type}s']
            if category_name not in target_dict:
                target_dict[category_name] = []

            target_dict[category_name].append({
                'title': content.get('title', 'Untitled'),
                'url': content.get('url', '#'),
                'date': content.get('date', ''),
                'filename': content.get('filename', '')
            })

        elif content_type == 'youtube' and 'videos' in organized:
            # YouTube和其他视频平台按系列组织
            series_name = "Online Videos"  # 通用视频系列名
            if series_name not in organized['videos']:
                organized['videos'][series_name] = []

            organized['videos'][series_name].append({
                'title': content.get('title', 'Untitled'),
                'url': content.get('url', '#'),
                'date': content.get('date', ''),
                'filename': content.get('filename', '')
            })

        else:
            # 其他内容类型，添加到对应列表
            target_key = f'{content_type}s'
            if target_key in organized and isinstance(organized[target_key], list):
                organized[target_key].append({
                    'title': content.get('title', 'Untitled'),
                    'url': content.get('url', '#'),
                    'date': content.get('date', ''),
                    'filename': content.get('filename', ''),
                    'content_type': content_type
                })

    # 对所有分类内的内容按日期排序 (最新在前)
    for category_name, category_content in organized.items():
        if isinstance(category_content, dict):
            # 字典类型（如lectures, meetings, videos）
            for _, items in category_content.items():
                if isinstance(items, list):
                    items.sort(key=lambda x: x.get('date', ''), reverse=True)
        elif isinstance(category_content, list):
            # 列表类型（其他内容类型）
            category_content.sort(key=lambda x: x.get('date', ''), reverse=True)

    return organized


def render_private_index(app, all_content: List[Dict[str, Any]],
                        organized_content: Dict[str, Any]) -> str:
    """渲染私有内容首页

    Args:
        app: Flask应用实例
        all_content: 所有内容列表
        organized_content: 组织化的内容结构

    Returns:
        渲染的HTML内容
    """
    from flask import render_template

    # 动态计算内容统计，基于实际存在的内容类型
    content_type_counts = Counter(c.get('content_type', 'others') for c in all_content)

    # 构建内容统计字典
    content_counts = dict(content_type_counts)
    content_counts.update({
        'public': len([c for c in all_content if not c.get('is_private', True)]),
        'private': len([c for c in all_content if c.get('is_private', True)])
    })

    total_content = len(all_content)

    # 获取GitHub Pages URL（自动从配置和环境变量生成）
    github_pages_url = get_config_value(app, 'github.pages_url', "https://github.com/Project_Bach")

    # 使用私有页面模板，传入合并的内容数据
    return render_template('web_app/private_index.html',
                          title="🔒 Private Content Hub",
                          site_title="Project Bach",
                          description="私人内容区域 - 浏览所有内容，支持公私筛选",
                          all_content=all_content,
                          organized_content=organized_content,
                          content_counts=content_counts,
                          stats={
                              'total_processed': total_content,
                              'this_month': total_content,
                              'total_hours': '0h',
                              'success_rate': '100%'
                          },
                          github_pages_url=github_pages_url,
                          is_private=True)


def serve_private_file(private_root: Path, filepath: str) -> tuple:
    """提供私有文件访问

    Args:
        private_root: 私有内容根目录
        filepath: 请求的文件路径

    Returns:
        (响应内容, HTTP状态码)
    """
    from flask import render_template

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

            return render_template('web_app/private_directory.html',
                                 filepath=filepath,
                                 files=files), 200

    # 读取并返回文件内容
    if safe_path.suffix == '.html':
        content = safe_path.read_text(encoding='utf-8')
        return content, 200
    elif safe_path.suffix == '.md':
        # 使用模板渲染Markdown
        content = safe_path.read_text(encoding='utf-8')
        return render_template('web_app/private_markdown.html',
                             content=content), 200
    else:
        return "Unsupported file type", 400


def validate_github_config(app) -> dict:
    """验证GitHub配置完整性和有效性

    Args:
        app: Flask应用实例

    Returns:
        dict: 验证结果，包含status和message
    """
    import requests
    import os

    # 调试信息
    logger.debug(f"环境变量 GITHUB_USERNAME: {os.environ.get('GITHUB_USERNAME', '未设置')}")
    logger.debug(f"环境变量 GITHUB_TOKEN: {'已设置' if os.environ.get('GITHUB_TOKEN') else '未设置'}")

    # 检查基本配置
    github_username = get_config_value(app, 'github.username')
    github_token = os.environ.get('GITHUB_TOKEN')

    # 调试配置读取结果
    logger.debug(f"从配置读取的 github.username: {github_username}")
    logger.debug(f"从环境变量读取的 GITHUB_TOKEN: {'已设置' if github_token else '未设置'}")

    result = {
        'configured': False,
        'username_valid': False,
        'token_valid': False,
        'pages_url': None,
        'message': ''
    }

    if not github_username:
        result['message'] = "GitHub username not configured"
        return result

    result['username_valid'] = True

    if not github_token:
        result['message'] = "GitHub token not configured"
        return result

    # 测试GitHub API访问
    try:
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Project-Bach'
        }

        # 测试基本API访问
        response = requests.get('https://api.github.com/user', headers=headers, timeout=5)

        if response.status_code == 200:
            result['token_valid'] = True
            result['configured'] = True
            result['pages_url'] = get_config_value(app, 'github.pages_url')
            result['message'] = "GitHub configuration valid"
        elif response.status_code == 401:
            result['message'] = "GitHub token invalid or expired"
        else:
            result['message'] = f"GitHub API error: {response.status_code}"

    except requests.exceptions.Timeout:
        result['message'] = "GitHub API timeout"
    except requests.exceptions.RequestException as e:
        result['message'] = f"GitHub API connection error: {str(e)}"
    except Exception as e:
        result['message'] = f"GitHub configuration validation error: {str(e)}"

    return result