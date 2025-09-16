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
        summary = results.get('summary', 'Summary generation failed')
        mindmap = results.get('mindmap', 'Mind map generation failed')
        anonymization_mapping = results.get('anonymization_mapping', {})
        # 获取transcript数据
        anonymized_transcript = results.get('anonymized_transcript', '')
        original_transcript = results.get('original_transcript', '')

        # 从统一的metadata结构读取数据
        content_type = metadata['content_type']
        video_metadata = metadata.get('video_metadata', {})
        video_url = metadata['original_file'] if content_type == 'youtube' else ''
        privacy_level = metadata['privacy_level']


        # 转换Markdown思维导图为HTML
        mindmap_html = self._markdown_to_html(mindmap)

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{filename} - Processing Result</title>
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
        .transcript {{
            background: #f8f9fa;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 20px;
            max-height: 400px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            line-height: 1.5;
            white-space: pre-wrap;
        }}
        .transcript-controls {{
            margin-bottom: 15px;
        }}
        .transcript-controls button {{
            background: #007bff;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            margin-right: 10px;
            font-size: 0.9em;
        }}
        .transcript-controls button:hover {{
            background: #0056b3;
        }}
        .transcript-controls button.secondary {{
            background: #6c757d;
        }}
        .transcript-controls button.secondary:hover {{
            background: #545b62;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{filename} - Processing Result</h1>
    </div>

    <div class="meta-info">
        <strong>Processing Time:</strong> {processed_time}<br>
        <strong>Original File:</strong> {original_file}
    </div>

    {self._generate_video_embed_section(content_type, video_metadata, video_url)}

    <div class="section">
        <h2>Content Summary</h2>
        <p>{summary}</p>
    </div>

    <div class="section">
        <h2>Mind Map</h2>
        <div class="mindmap">
            {mindmap_html}
        </div>
    </div>

    {self._generate_transcript_section(anonymized_transcript, original_transcript, privacy_level)}

    <div class="section">
        <h2>Processing Information</h2>
        <p><strong>Anonymization Mapping:</strong> {anonymization_mapping if anonymization_mapping else 'None'}</p>
    </div>

    <div class="footer">
        Generated by Project Bach
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
        <h2>📺 YouTube Video</h2>
        <div style="margin-bottom: 15px;">
            <strong>Title:</strong> {video_title}<br>
            <strong>Channel:</strong> {channel}<br>
            <strong>Duration:</strong> {duration}<br>
            <strong>Video Link:</strong> <a href="{video_url}" target="_blank">{video_url}</a>
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

    def _generate_transcript_section(self, anonymized_transcript: str, original_transcript: str, privacy_level: str) -> str:
        """生成transcript部分

        Args:
            anonymized_transcript: 匿名化的转录文本
            original_transcript: 原始转录文本
            privacy_level: 隐私级别

        Returns:
            transcript部分的HTML代码
        """
        # 如果没有transcript数据，返回空字符串
        if not anonymized_transcript and not original_transcript:
            return ""

        # 优先使用匿名化的transcript，如果没有则使用原始transcript
        display_transcript = anonymized_transcript if anonymized_transcript else original_transcript

        # 如果是私有内容，可以提供原始和匿名化版本的切换
        show_toggle = (privacy_level == 'private' and
                      anonymized_transcript and
                      original_transcript and
                      anonymized_transcript != original_transcript)

        # 截断过长的transcript用于预览（前500字符）
        preview_text = display_transcript[:500] + "..." if len(display_transcript) > 500 else display_transcript

        transcript_html = f"""
    <div class="section">
        <h2>📝 Transcript</h2>
        <div class="transcript-controls">
            <button onclick="toggleTranscript()" id="toggleBtn">Show Full Transcript</button>
            <button onclick="copyTranscript()" class="secondary">Copy to Clipboard</button>
            {"<button onclick='switchTranscriptType()' class='secondary' id='switchBtn'>Show Original</button>" if show_toggle else ""}
        </div>
        <div class="transcript" id="transcriptContainer">
            <div id="transcriptPreview">{self._escape_html(preview_text)}</div>
            <div id="transcriptFull" style="display: none;">{self._escape_html(display_transcript)}</div>
            {"<div id='transcriptOriginal' style='display: none;'>" + self._escape_html(original_transcript) + "</div>" if show_toggle else ""}
        </div>
    </div>

    <script>
        let isFullTranscriptShown = false;
        let showingAnonymized = true;

        function toggleTranscript() {{
            const preview = document.getElementById('transcriptPreview');
            const full = document.getElementById('transcriptFull');
            const toggleBtn = document.getElementById('toggleBtn');

            if (isFullTranscriptShown) {{
                preview.style.display = 'block';
                full.style.display = 'none';
                toggleBtn.textContent = 'Show Full Transcript';
                isFullTranscriptShown = false;
            }} else {{
                preview.style.display = 'none';
                full.style.display = 'block';
                toggleBtn.textContent = 'Show Preview';
                isFullTranscriptShown = true;
            }}
        }}

        function copyTranscript() {{
            const container = document.getElementById('transcriptContainer');
            const visibleText = isFullTranscriptShown ?
                document.getElementById('transcriptFull').textContent :
                document.getElementById('transcriptPreview').textContent;

            navigator.clipboard.writeText(visibleText).then(() => {{
                alert('Transcript copied to clipboard!');
            }}).catch(err => {{
                console.error('Failed to copy: ', err);
            }});
        }}

        {"function switchTranscriptType() {" if show_toggle else ""}
        {"    const anonymized = document.getElementById('transcriptFull');" if show_toggle else ""}
        {"    const original = document.getElementById('transcriptOriginal');" if show_toggle else ""}
        {"    const switchBtn = document.getElementById('switchBtn');" if show_toggle else ""}
        {"    " if show_toggle else ""}
        {"    if (showingAnonymized) {" if show_toggle else ""}
        {"        anonymized.style.display = 'none';" if show_toggle else ""}
        {"        original.style.display = 'block';" if show_toggle else ""}
        {"        switchBtn.textContent = 'Show Anonymized';" if show_toggle else ""}
        {"        showingAnonymized = false;" if show_toggle else ""}
        {"    } else {" if show_toggle else ""}
        {"        anonymized.style.display = 'block';" if show_toggle else ""}
        {"        original.style.display = 'none';" if show_toggle else ""}
        {"        switchBtn.textContent = 'Show Original';" if show_toggle else ""}
        {"        showingAnonymized = true;" if show_toggle else ""}
        {"    }" if show_toggle else ""}
        {"}" if show_toggle else ""}
    </script>
        """

        return transcript_html

    def _escape_html(self, text: str) -> str:
        """转义HTML字符

        Args:
            text: 要转义的文本

        Returns:
            转义后的文本
        """
        if not text:
            return ""

        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&#x27;'))


