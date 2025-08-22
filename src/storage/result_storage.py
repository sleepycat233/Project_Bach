#!/usr/bin/env python3.11
"""
结果文件存储模块
负责最终处理结果的保存、读取和管理
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
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
        
    def save_markdown_result(self, filename: str, results: Dict[str, Any], privacy_level: str = 'public') -> str:
        """保存Markdown格式的结果文件
        
        Args:
            filename: 文件名（不包含扩展名）
            results: 结果数据字典
            privacy_level: 隐私级别 ('public' 或 'private')
            
        Returns:
            保存的文件路径
        """
        markdown_content = self._generate_markdown_content(filename, results)
        
        # 根据隐私级别选择保存目录
        if privacy_level == 'private':
            file_path = self.private_folder / f"{filename}_result.md"
        else:
            file_path = self.public_folder / f"{filename}_result.md"
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            self.logger.info(f"结果已保存: {file_path}")
            return str(file_path)
            
        except Exception as e:
            error_msg = f"保存结果文件失败: {file_path}, 错误: {str(e)}"
            self.logger.error(error_msg)
            raise OSError(error_msg)
    
    def save_json_result(self, filename: str, results: Dict[str, Any], privacy_level: str = 'public') -> str:
        """保存JSON格式的结果文件
        
        Args:
            filename: 文件名（不包含扩展名）
            results: 结果数据字典
            privacy_level: 隐私级别 ('public' 或 'private')
            
        Returns:
            保存的文件路径
        """
        # 添加元数据
        json_data = {
            **results,
            'metadata': {
                'filename': filename,
                'created_time': datetime.now().isoformat(),
                'format_version': '1.0',
                'privacy_level': privacy_level
            }
        }
        
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
    
    def _generate_markdown_content(self, filename: str, results: Dict[str, Any]) -> str:
        """生成Markdown格式的内容
        
        Args:
            filename: 文件名
            results: 结果数据
            
        Returns:
            Markdown格式的字符串
        """
        processed_time = results.get('processed_time', datetime.now().isoformat())
        original_file = results.get('original_file', 'N/A')
        summary = results.get('summary', '摘要生成失败')
        mindmap = results.get('mindmap', '思维导图生成失败')
        anonymization_mapping = results.get('anonymization_mapping', {})
        
        # 格式化匿名化映射
        if anonymization_mapping:
            mapping_str = str(anonymization_mapping)
        else:
            mapping_str = '无'
        
        markdown_content = f"""# {filename} - 处理结果

**处理时间**: {processed_time}  
**原始文件**: {original_file}

## 内容摘要

{summary}

## 思维导图

{mindmap}

## 处理信息

**匿名化映射**: {mapping_str}

---
*由 Project Bach 自动生成*
"""
        return markdown_content
    
    def _generate_html_content(self, filename: str, results: Dict[str, Any]) -> str:
        """生成HTML格式的内容
        
        Args:
            filename: 文件名
            results: 结果数据
            
        Returns:
            HTML格式的字符串
        """
        processed_time = results.get('processed_time', datetime.now().isoformat())
        original_file = results.get('original_file', 'N/A')
        summary = results.get('summary', '摘要生成失败')
        mindmap = results.get('mindmap', '思维导图生成失败')
        anonymization_mapping = results.get('anonymization_mapping', {})
        
        # YouTube特殊处理
        content_type = results.get('content_type', 'audio')
        video_metadata = results.get('video_metadata', {})
        video_url = results.get('video_url', '')
        privacy_level = results.get('privacy_level', 'public')
        
        # 获取匿名化transcript (仅公开内容显示)
        anonymized_transcript = results.get('anonymized_transcript', '') if privacy_level == 'public' else ''
        
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
    
    {self._generate_transcript_section(anonymized_transcript, privacy_level)}
    
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
    
    def _generate_transcript_section(self, anonymized_transcript: str, privacy_level: str) -> str:
        """生成transcript复制功能部分
        
        Args:
            anonymized_transcript: 匿名化后的转录文本
            privacy_level: 隐私级别
            
        Returns:
            HTML代码
        """
        if not anonymized_transcript or privacy_level != 'public':
            return ""
        
        # 截取transcript前500字符用于预览
        preview_text = anonymized_transcript[:500] + ("..." if len(anonymized_transcript) > 500 else "")
        
        transcript_section = f"""
    <div class="section">
        <h2>📝 转录文本 (匿名化)</h2>
        <div style="background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 5px; padding: 15px; margin-bottom: 15px;">
            <div id="transcript-preview" style="max-height: 150px; overflow-y: auto; margin-bottom: 15px; font-family: monospace; line-height: 1.4; color: #495057;">
                {preview_text}
            </div>
            <div style="display: flex; gap: 10px; align-items: center;">
                <button id="copy-transcript-btn" onclick="copyTranscript()" 
                        style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 14px;">
                    📋 复制完整转录文本
                </button>
                <button id="toggle-transcript-btn" onclick="toggleTranscript()" 
                        style="background: #6c757d; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 14px;">
                    👁️ 显示完整文本
                </button>
                <span id="copy-status" style="color: #28a745; font-weight: bold; display: none;">✅ 已复制!</span>
            </div>
        </div>
        
        <!-- 隐藏的完整transcript用于复制 -->
        <textarea id="full-transcript" style="position: absolute; left: -9999px; opacity: 0;" readonly>{anonymized_transcript}</textarea>
        
        <script>
        let isFullTextVisible = false;
        const originalText = `{preview_text}`;
        const fullText = `{anonymized_transcript}`;
        
        function copyTranscript() {{
            const textarea = document.getElementById('full-transcript');
            textarea.select();
            textarea.setSelectionRange(0, 99999);
            document.execCommand('copy');
            
            const status = document.getElementById('copy-status');
            const btn = document.getElementById('copy-transcript-btn');
            
            status.style.display = 'inline';
            btn.innerHTML = '✅ 已复制!';
            btn.style.background = '#28a745';
            
            setTimeout(() => {{
                status.style.display = 'none';
                btn.innerHTML = '📋 复制完整转录文本';
                btn.style.background = 'linear-gradient(135deg, #28a745 0%, #20c997 100%)';
            }}, 2000);
        }}
        
        function toggleTranscript() {{
            const preview = document.getElementById('transcript-preview');
            const btn = document.getElementById('toggle-transcript-btn');
            
            if (!isFullTextVisible) {{
                preview.innerHTML = fullText;
                preview.style.maxHeight = '400px';
                btn.innerHTML = '👁️ 隐藏完整文本';
                isFullTextVisible = true;
            }} else {{
                preview.innerHTML = originalText;
                preview.style.maxHeight = '150px';
                btn.innerHTML = '👁️ 显示完整文本';
                isFullTextVisible = false;
            }}
        }}
        </script>
    </div>
        """
        return transcript_section
    
    def load_result(self, filename: str, format: str = 'json') -> Optional[Dict[str, Any]]:
        """加载结果文件
        
        Args:
            filename: 文件名（不包含扩展名）
            format: 文件格式 ('json', 'markdown', 'html')
            
        Returns:
            结果数据或None
        """
        if format == 'json':
            file_path = self.output_folder / f"{filename}_result.json"
            try:
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
            except Exception as e:
                self.logger.error(f"加载JSON结果失败: {file_path}, 错误: {str(e)}")
        
        elif format in ['markdown', 'html']:
            ext = 'md' if format == 'markdown' else 'html'
            file_path = self.output_folder / f"{filename}_result.{ext}"
            try:
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return {'content': f.read(), 'format': format}
            except Exception as e:
                self.logger.error(f"加载{format}结果失败: {file_path}, 错误: {str(e)}")
        
        return None
    
    def list_results(self, format: Optional[str] = None) -> List[str]:
        """列出所有结果文件
        
        Args:
            format: 可选的格式过滤器 ('json', 'markdown', 'html')
            
        Returns:
            文件名列表（不包含路径和扩展名）
        """
        try:
            if format == 'json':
                pattern = "*_result.json"
            elif format == 'markdown':
                pattern = "*_result.md"
            elif format == 'html':
                pattern = "*_result.html"
            else:
                pattern = "*_result.*"
            
            files = list(self.output_folder.glob(pattern))
            
            # 提取基础文件名
            base_names = set()
            for file_path in files:
                name = file_path.stem
                if name.endswith('_result'):
                    base_name = name[:-7]  # 移除 '_result'
                    base_names.add(base_name)
            
            return sorted(list(base_names))
            
        except Exception as e:
            self.logger.error(f"列出结果文件失败: {str(e)}")
            return []
    
    def delete_result(self, filename: str, format: Optional[str] = None) -> bool:
        """删除结果文件
        
        Args:
            filename: 文件名（不包含扩展名）
            format: 可选的格式，如果为None则删除所有格式的文件
            
        Returns:
            是否成功删除
        """
        try:
            if format:
                # 删除特定格式的文件
                ext = {'json': 'json', 'markdown': 'md', 'html': 'html'}.get(format, format)
                file_path = self.output_folder / f"{filename}_result.{ext}"
                if file_path.exists():
                    file_path.unlink()
                    self.logger.info(f"删除结果文件: {file_path}")
                    return True
                else:
                    self.logger.warning(f"要删除的文件不存在: {file_path}")
                    return False
            else:
                # 删除所有格式的文件
                deleted_count = 0
                for ext in ['json', 'md', 'html']:
                    file_path = self.output_folder / f"{filename}_result.{ext}"
                    if file_path.exists():
                        file_path.unlink()
                        deleted_count += 1
                        self.logger.info(f"删除结果文件: {file_path}")
                
                return deleted_count > 0
                
        except Exception as e:
            self.logger.error(f"删除结果文件失败: {filename}, 错误: {str(e)}")
            return False
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """获取存储统计信息
        
        Returns:
            存储统计信息字典
        """
        try:
            stats = {
                'total_files': 0,
                'total_size': 0,
                'formats': {'json': 0, 'markdown': 0, 'html': 0},
                'oldest_file': None,
                'newest_file': None
            }
            
            for file_path in self.output_folder.glob("*_result.*"):
                stats['total_files'] += 1
                file_stat = file_path.stat()
                stats['total_size'] += file_stat.st_size
                
                # 统计格式
                if file_path.suffix == '.json':
                    stats['formats']['json'] += 1
                elif file_path.suffix == '.md':
                    stats['formats']['markdown'] += 1
                elif file_path.suffix == '.html':
                    stats['formats']['html'] += 1
                
                # 记录时间信息
                file_time = datetime.fromtimestamp(file_stat.st_mtime)
                if stats['oldest_file'] is None or file_time < stats['oldest_file']:
                    stats['oldest_file'] = file_time
                if stats['newest_file'] is None or file_time > stats['newest_file']:
                    stats['newest_file'] = file_time
            
            return stats
            
        except Exception as e:
            self.logger.error(f"获取存储统计失败: {str(e)}")
            return {'error': str(e)}