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
        
    def save_markdown_result(self, filename: str, results: Dict[str, Any]) -> str:
        """保存Markdown格式的结果文件
        
        Args:
            filename: 文件名（不包含扩展名）
            results: 结果数据字典
            
        Returns:
            保存的文件路径
        """
        markdown_content = self._generate_markdown_content(filename, results)
        file_path = self.output_folder / f"{filename}_result.md"
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            self.logger.info(f"结果已保存: {file_path}")
            return str(file_path)
            
        except Exception as e:
            error_msg = f"保存结果文件失败: {file_path}, 错误: {str(e)}"
            self.logger.error(error_msg)
            raise OSError(error_msg)
    
    def save_json_result(self, filename: str, results: Dict[str, Any]) -> str:
        """保存JSON格式的结果文件
        
        Args:
            filename: 文件名（不包含扩展名）
            results: 结果数据字典
            
        Returns:
            保存的文件路径
        """
        # 添加元数据
        json_data = {
            **results,
            'metadata': {
                'filename': filename,
                'created_time': datetime.now().isoformat(),
                'format_version': '1.0'
            }
        }
        
        file_path = self.output_folder / f"{filename}_result.json"
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2, default=str)
            
            self.logger.debug(f"JSON结果已保存: {file_path}")
            return str(file_path)
            
        except Exception as e:
            error_msg = f"保存JSON结果失败: {file_path}, 错误: {str(e)}"
            self.logger.error(error_msg)
            raise OSError(error_msg)
    
    def save_html_result(self, filename: str, results: Dict[str, Any]) -> str:
        """保存HTML格式的结果文件
        
        Args:
            filename: 文件名（不包含扩展名）
            results: 结果数据字典
            
        Returns:
            保存的文件路径
        """
        html_content = self._generate_html_content(filename, results)
        file_path = self.output_folder / f"{filename}_result.html"
        
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