#!/usr/bin/env python3.11
"""
结果文件存储模块
负责最终处理结果的保存、读取和管理
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any
from datetime import datetime


class ResultStorage:
    """结果文件存储服务"""

    def __init__(self, output_folder: str):
        """初始化结果存储

        Args:
            output_folder: 输出文件夹路径
        """
        self.output_folder = Path(output_folder)
        self.logger = logging.getLogger('project_bach.result_storage')

        # 确保目录存在
        self.output_folder.mkdir(parents=True, exist_ok=True)

        # 确保隐私目录存在
        self.public_folder = self.output_folder / 'public'
        self.private_folder = self.output_folder / 'private'
        self.public_folder.mkdir(parents=True, exist_ok=True)
        self.private_folder.mkdir(parents=True, exist_ok=True)

    def save_json_result(self, filename: str, results: Dict[str, Any], privacy_level: str = 'public') -> str:
        """保存JSON格式的结果文件

        Args:
            filename: 文件名（不包含扩展名）
            results: 结果数据字典
            privacy_level: 隐私级别 ('public' 或 'private')

        Returns:
            保存的文件路径
        """
        # 新结构不需要额外添加metadata，因为results已经包含metadata字段
        json_data = results

        # 根据隐私级别选择保存目录
        if privacy_level == 'private':
            file_path = self.private_folder / f"{filename}_result.json"
        else:
            file_path = self.public_folder / f"{filename}_result.json"

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2, default=str)

            self.logger.debug(f"JSON结果已保存: {file_path}")
            return str(file_path)

        except Exception as e:
            error_msg = f"保存JSON结果失败: {file_path}, 错误: {str(e)}"
            self.logger.error(error_msg)
            raise OSError(error_msg)

    def save_html_result(self, filename: str, results: Dict[str, Any], privacy_level: str = 'public') -> str:
        """保存HTML格式的结果文件

        Args:
            filename: 文件名（不包含扩展名）
            results: 结果数据字典
            privacy_level: 隐私级别 ('public' 或 'private')

        Returns:
            保存的文件路径
        """
        html_content = self._generate_html_content(filename, results)

        # 根据隐私级别选择保存目录
        if privacy_level == 'private':
            file_path = self.private_folder / f"{filename}_result.html"
        else:
            file_path = self.public_folder / f"{filename}_result.html"

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            self.logger.debug(f"HTML结果已保存: {file_path}")
            return str(file_path)

        except Exception as e:
            error_msg = f"保存HTML结果失败: {file_path}, 错误: {str(e)}"
            self.logger.error(error_msg)
            raise OSError(error_msg)

    def _generate_html_content(self, filename: str, results: Dict[str, Any]) -> str:
        """生成HTML格式的内容

        Args:
            filename: 文件名
            results: 结果数据

        Returns:
            HTML格式的字符串
        """
        # 从统一的metadata结构读取数据
        metadata = results['metadata']
        processed_time = metadata['processed_time']
        original_file = metadata['original_file']
        summary = results.get('summary', '摘要生成失败')
        mindmap = results.get('mindmap', '思维导图生成失败')
        anonymization_mapping = results.get('anonymization_mapping', {})

        # 从统一的metadata结构读取数据
        content_type = metadata['content_type']
        video_metadata = metadata.get('video_metadata', {})
        video_url = metadata['original_file'] if content_type == 'youtube' else ''
        privacy_level = metadata['privacy_level']


        # 转换Markdown思维导图为HTML
        mindmap_html = self._markdown_to_html(mindmap)

        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{filename} - 处理结果</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            border-bottom: 2px solid #eee;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .meta-info {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 30px;
        }}
        .section {{
            margin-bottom: 30px;
        }}
        .section h2 {{
            color: #2c3e50;
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
        }}
        .mindmap {{
            background: #fff;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 20px;
        }}
        .footer {{
            text-align: center;
            font-style: italic;
            color: #666;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #eee;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{filename} - 处理结果</h1>
    </div>

    <div class="meta-info">
        <strong>处理时间:</strong> {processed_time}<br>
        <strong>原始文件:</strong> {original_file}
    </div>

    {self._generate_video_embed_section(content_type, video_metadata, video_url)}

    <div class="section">
        <h2>内容摘要</h2>
        <p>{summary}</p>
    </div>

    <div class="section">
        <h2>思维导图</h2>
        <div class="mindmap">
            {mindmap_html}
        </div>
    </div>

    <div class="section">
        <h2>处理信息</h2>
        <p><strong>匿名化映射:</strong> {anonymization_mapping if anonymization_mapping else '无'}</p>
    </div>

    <div class="footer">
        由 Project Bach 自动生成
    </div>
</body>
</html>"""
        return html_content

    def _markdown_to_html(self, markdown_text: str) -> str:
        """简单的Markdown到HTML转换

        Args:
            markdown_text: Markdown文本

        Returns:
            HTML文本
        """
        if not markdown_text:
            return ""

        lines = markdown_text.split('\n')
        html_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                html_lines.append('<br>')
            elif line.startswith('### '):
                html_lines.append(f'<h3>{line[4:]}</h3>')
            elif line.startswith('## '):
                html_lines.append(f'<h2>{line[3:]}</h2>')
            elif line.startswith('# '):
                html_lines.append(f'<h1>{line[2:]}</h1>')
            elif line.startswith('- '):
                html_lines.append(f'<li>{line[2:]}</li>')
            else:
                html_lines.append(f'<p>{line}</p>')

        return '\n'.join(html_lines)

    def _generate_video_embed_section(self, content_type: str, video_metadata: Dict[str, Any], video_url: str) -> str:
        """生成YouTube视频嵌入部分

        Args:
            content_type: 内容类型
            video_metadata: 视频元数据
            video_url: 视频URL

        Returns:
            视频嵌入HTML代码
        """
        if content_type != 'youtube' or not video_metadata.get('video_id'):
            return ""

        video_id = video_metadata['video_id']
        video_title = video_metadata.get('title', 'YouTube Video')
        channel = video_metadata.get('uploader', 'Unknown Channel')
        duration = video_metadata.get('duration_string', 'Unknown')

        # YouTube嵌入iframe
        embed_html = f"""
    <div class="section">
        <h2>📺 YouTube 视频</h2>
        <div style="margin-bottom: 15px;">
            <strong>标题:</strong> {video_title}<br>
            <strong>频道:</strong> {channel}<br>
            <strong>时长:</strong> {duration}<br>
            <strong>视频链接:</strong> <a href="{video_url}" target="_blank">{video_url}</a>
        </div>
        <div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; background: #000;">
            <iframe
                src="https://www.youtube.com/embed/{video_id}"
                frameborder="0"
                allowfullscreen
                style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;">
            </iframe>
        </div>
    </div>
        """
        return embed_html



