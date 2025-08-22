#!/usr/bin/env python3.11
"""
内容格式化服务
负责将音频处理结果格式化为Web发布格式
"""

import markdown
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import re
import html


class ContentFormatter:
    """内容格式化服务"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化内容格式化服务
        
        Args:
            config: 格式化配置
        """
        self.config = config
        self.logger = logging.getLogger('project_bach.content_formatter')
        
        # 配置Markdown扩展
        self.markdown_extensions = [
            'markdown.extensions.extra',     # 额外语法支持
            'markdown.extensions.codehilite', # 代码高亮
            'markdown.extensions.toc',       # 目录生成
            'markdown.extensions.tables',    # 表格支持
        ]
        
        # 初始化Markdown处理器
        self.md_processor = markdown.Markdown(
            extensions=self.markdown_extensions,
            extension_configs={
                'codehilite': {
                    'css_class': 'highlight',
                    'use_pygments': True
                },
                'toc': {
                    'anchorlink': True
                }
            }
        )
        
        self.logger.info("内容格式化服务初始化完成")
    
    def format_content(self, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """格式化音频处理结果为发布内容
        
        Args:
            content_data: 音频处理结果数据
            
        Returns:
            格式化后的内容
        """
        self.logger.info(f"格式化内容: {content_data.get('title', '未知')}")
        
        try:
            # 验证输入数据
            validation_result = self.validate_content_structure(content_data)
            if not validation_result['valid']:
                raise ValueError(f"内容结构无效: {validation_result['message']}")
            
            # 生成Markdown内容
            markdown_content = self._generate_markdown_content(content_data)
            
            # 转换为HTML
            html_content = self.generate_html_from_markdown(markdown_content)
            
            # 提取元数据
            metadata = self._extract_metadata(content_data)
            
            # 生成文件名
            filename = self._generate_filename(content_data)
            
            return {
                'success': True,
                'content': {
                    'markdown': markdown_content,
                    'html': html_content,
                    'metadata': metadata,
                    'filename': filename,
                    'title': content_data['title'],
                    'formatted_time': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            self.logger.error(f"内容格式化失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_markdown_content(self, content_data: Dict[str, Any]) -> str:
        """生成Markdown内容
        
        Args:
            content_data: 原始内容数据
            
        Returns:
            Markdown格式内容
        """
        # 处理时间格式化
        processed_time = content_data.get('processed_time', datetime.now().isoformat())
        if isinstance(processed_time, str):
            try:
                dt = datetime.fromisoformat(processed_time.replace('Z', '+00:00'))
                formatted_time = dt.strftime('%Y年%m月%d日 %H:%M:%S')
            except:
                formatted_time = processed_time
        else:
            formatted_time = str(processed_time)
        
        # 构建Markdown内容
        markdown_content = f"""# {content_data['title']}

**处理时间**: {formatted_time}  
**原始文件**: `{content_data.get('original_file', '未知')}`  
**处理状态**: ✅ 完成

---

## 📄 内容摘要

{self._clean_text(content_data.get('summary', ''))[:2000]}

---

## 🧠 思维导图

{self._format_mindmap(content_data.get('mindmap', ''))}

---

## 🔒 人名匿名化信息

{self._format_anonymization_info(content_data.get('anonymized_names', {}))}

---

## 📊 处理统计

{self._generate_statistics(content_data)}

---

<div class="footer">
<p><em>由 <a href="https://github.com/project-bach">Project Bach</a> 自动生成</em></p>
<p><small>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small></p>
</div>
"""
        
        return markdown_content
    
    def _clean_text(self, text: str) -> str:
        """清理文本内容
        
        Args:
            text: 原始文本
            
        Returns:
            清理后的文本
        """
        if not text:
            return "暂无内容"
        
        # 移除多余的空白行
        text = re.sub(r'\n\s*\n', '\n\n', text.strip())
        
        # 转义HTML特殊字符
        text = html.escape(text)
        
        # 还原Markdown语法
        text = text.replace('&gt;', '>')
        text = text.replace('&lt;', '<')
        text = text.replace('&#x27;', "'")
        
        return text
    
    def _format_mindmap(self, mindmap_text: str) -> str:
        """格式化思维导图内容
        
        Args:
            mindmap_text: 思维导图文本
            
        Returns:
            格式化后的思维导图
        """
        if not mindmap_text:
            return "暂未生成思维导图"
        
        # 确保思维导图格式正确
        if not mindmap_text.strip().startswith('#'):
            # 如果不是标准Markdown格式，进行基础格式化
            lines = mindmap_text.strip().split('\n')
            formatted_lines = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # 简单的层级识别
                if line.startswith('- '):
                    formatted_lines.append(line)
                elif line.startswith('  - '):
                    formatted_lines.append(line)
                elif ':' in line:
                    formatted_lines.append(f"## {line}")
                else:
                    formatted_lines.append(f"- {line}")
            
            return '\n'.join(formatted_lines)
        
        return self._clean_text(mindmap_text)
    
    def _format_anonymization_info(self, anonymized_names: Dict[str, str]) -> str:
        """格式化人名匿名化信息
        
        Args:
            anonymized_names: 人名映射字典
            
        Returns:
            格式化后的匿名化信息
        """
        if not anonymized_names:
            return "本次处理未检测到需要匿名化的人名"
        
        info = f"本次处理中共匿名化了 **{len(anonymized_names)}** 个人名:\n\n"
        info += "| 序号 | 匿名化后 | 检测类型 |\n"
        info += "|------|----------|----------|\n"
        
        for idx, (original, anonymous) in enumerate(anonymized_names.items(), 1):
            # 判断是中文还是英文名
            name_type = "中文" if any('\u4e00' <= char <= '\u9fff' for char in original) else "英文"
            info += f"| {idx} | {anonymous} | {name_type} |\n"
        
        info += "\n> 💡 为保护隐私，所有人名已被替换为虚拟姓名"
        
        return info
    
    def _generate_statistics(self, content_data: Dict[str, Any]) -> str:
        """生成处理统计信息
        
        Args:
            content_data: 内容数据
            
        Returns:
            统计信息Markdown
        """
        # 计算各种统计指标
        summary_length = len(content_data.get('summary', ''))
        mindmap_length = len(content_data.get('mindmap', ''))
        anonymized_count = len(content_data.get('anonymized_names', {}))
        
        # 估算处理时间
        processing_time = content_data.get('processing_duration', '未知')
        
        stats = f"""| 指标 | 数值 |
|------|------|
| 摘要长度 | {summary_length} 字符 |
| 思维导图长度 | {mindmap_length} 字符 |
| 匿名化人名数 | {anonymized_count} 个 |
| 处理时长 | {processing_time} |
| 文件大小 | {content_data.get('file_size', '未知')} |
| 音频时长 | {content_data.get('audio_duration', '未知')} |
"""
        
        return stats
    
    def _extract_metadata(self, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取内容元数据
        
        Args:
            content_data: 内容数据
            
        Returns:
            元数据字典
        """
        return {
            'title': content_data['title'],
            'description': content_data.get('summary', '')[:200] + '...' if len(content_data.get('summary', '')) > 200 else content_data.get('summary', ''),
            'keywords': self._extract_keywords(content_data),
            'author': 'Project Bach',
            'created': content_data.get('processed_time', datetime.now().isoformat()),
            'language': 'zh-CN',
            'type': 'audio-analysis'
        }
    
    def _extract_keywords(self, content_data: Dict[str, Any]) -> List[str]:
        """提取关键词
        
        Args:
            content_data: 内容数据
            
        Returns:
            关键词列表
        """
        keywords = ['音频处理', 'AI分析', '内容摘要']
        
        # 从标题提取
        title = content_data.get('title', '')
        if '会议' in title:
            keywords.append('会议')
        if '讲座' in title:
            keywords.append('讲座')
        if '培训' in title:
            keywords.append('培训')
        
        # 从摘要提取常见词汇
        summary = content_data.get('summary', '')
        if '项目' in summary:
            keywords.append('项目管理')
        if '技术' in summary:
            keywords.append('技术讨论')
        if '决策' in summary:
            keywords.append('决策分析')
        
        return list(set(keywords))
    
    def _generate_filename(self, content_data: Dict[str, Any]) -> str:
        """生成文件名
        
        Args:
            content_data: 内容数据
            
        Returns:
            安全的文件名
        """
        # 基于原始文件名生成
        original_file = content_data.get('original_file', 'unknown')
        
        # 移除扩展名
        base_name = Path(original_file).stem
        
        # 清理文件名，移除特殊字符
        safe_name = re.sub(r'[^\w\-_\u4e00-\u9fff]', '_', base_name)
        
        # 添加时间戳避免冲突
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        return f"{safe_name}_{timestamp}.html"
    
    def generate_html_from_markdown(self, markdown_content: str) -> str:
        """将Markdown转换为HTML
        
        Args:
            markdown_content: Markdown内容
            
        Returns:
            HTML内容
        """
        try:
            # 重置Markdown处理器状态
            self.md_processor.reset()
            
            # 转换为HTML
            html_content = self.md_processor.convert(markdown_content)
            
            # 添加额外的CSS类
            html_content = self._enhance_html(html_content)
            
            return html_content
            
        except Exception as e:
            self.logger.error(f"Markdown转HTML失败: {str(e)}")
            # 返回基础HTML
            return f"""<div class="error">
                <h2>内容转换失败</h2>
                <p>无法将Markdown内容转换为HTML格式。</p>
                <pre>{html.escape(markdown_content)}</pre>
            </div>"""
    
    def _enhance_html(self, html_content: str) -> str:
        """增强HTML内容
        
        Args:
            html_content: 基础HTML
            
        Returns:
            增强后的HTML
        """
        # 为表格添加CSS类
        html_content = re.sub(r'<table>', '<table class="table table-striped">', html_content)
        
        # 为代码块添加CSS类
        html_content = re.sub(r'<pre>', '<pre class="code-block">', html_content)
        
        # 为引用添加CSS类
        html_content = re.sub(r'<blockquote>', '<blockquote class="quote">', html_content)
        
        # 为链接添加target="_blank"
        html_content = re.sub(r'<a href="http', '<a target="_blank" href="http', html_content)
        
        return html_content
    
    def create_site_index(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """创建网站首页索引
        
        Args:
            results: 所有处理结果列表
            
        Returns:
            索引页面内容
        """
        self.logger.info(f"创建网站索引，包含{len(results)}个结果")
        
        try:
            # 按日期排序（最新的在前）
            sorted_results = sorted(
                results, 
                key=lambda x: x.get('date', ''), 
                reverse=True
            )
            
            # 生成索引Markdown
            index_markdown = self._generate_index_markdown(sorted_results)
            
            # 转换为HTML
            index_html = self.generate_html_from_markdown(index_markdown)
            
            # 生成元数据
            metadata = {
                'title': 'Project Bach - 音频处理结果',
                'description': f'共收录{len(results)}个音频处理结果',
                'keywords': ['音频处理', 'AI分析', '结果索引'],
                'author': 'Project Bach',
                'created': datetime.now().isoformat(),
                'language': 'zh-CN',
                'type': 'index'
            }
            
            return {
                'success': True,
                'content': {
                    'markdown': index_markdown,
                    'html': index_html,
                    'metadata': metadata,
                    'filename': 'index.html',
                    'title': 'Project Bach - 音频处理结果',
                    'total_items': len(results)
                }
            }
            
        except Exception as e:
            self.logger.error(f"创建索引失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_index_markdown(self, results: List[Dict[str, Any]]) -> str:
        """生成索引页面Markdown
        
        Args:
            results: 结果列表
            
        Returns:
            索引Markdown内容
        """
        # 页面头部
        markdown = f"""# Project Bach 音频处理结果

> 🎵 智能音频处理与内容分析平台  
> 📊 **共收录 {len(results)} 个处理结果**

---

## 📋 最新结果

"""
        
        if not results:
            markdown += "暂无处理结果。\n"
        else:
            # 结果表格
            markdown += """| 日期 | 标题 | 摘要预览 | 操作 |
|------|------|----------|------|
"""
            
            for result in results[:20]:  # 只显示最新20个
                title = result.get('title', '未知标题')[:30]
                date = result.get('date', '未知日期')
                preview = result.get('summary', '暂无摘要')[:50] + '...' if len(result.get('summary', '')) > 50 else result.get('summary', '暂无摘要')
                filename = result.get('file', '#')
                
                markdown += f"| {date} | [{title}]({filename}) | {preview} | [查看详情]({filename}) |\n"
            
            # 如果结果太多，显示更多链接
            if len(results) > 20:
                markdown += f"\n> 📑 共{len(results)}个结果，仅显示最新20个。[查看全部 →](archive.html)\n"
        
        # 统计信息
        markdown += f"""

---

## 📊 统计概览

| 指标 | 数值 |
|------|------|
| 总处理数 | {len(results)} |
| 本月新增 | {self._count_this_month(results)} |
| 本周新增 | {self._count_this_week(results)} |
| 最后更新 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |

---

## 🔍 快速导航

- [📈 数据统计](stats.html) - 处理结果统计分析
- [🏷️ 标签云](tags.html) - 内容标签分类
- [🔎 搜索功能](search.html) - 搜索处理结果
- [ℹ️ 关于项目](about.html) - Project Bach 介绍

---

<div class="footer">
<p><strong>Project Bach</strong> - AI音频处理与内容分析</p>
<p><em>最后更新: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</em></p>
<p><a href="https://github.com/project-bach" target="_blank">🔗 GitHub</a> | <a href="mailto:contact@project-bach.com">📧 联系我们</a></p>
</div>
"""
        
        return markdown
    
    def _count_this_month(self, results: List[Dict[str, Any]]) -> int:
        """统计本月结果数"""
        current_month = datetime.now().strftime('%Y-%m')
        return sum(1 for r in results if r.get('date', '').startswith(current_month))
    
    def _count_this_week(self, results: List[Dict[str, Any]]) -> int:
        """统计本周结果数"""
        # 简单实现：最近7天
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        return sum(1 for r in results if r.get('date', '') >= week_ago)
    
    def validate_content_structure(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """验证内容结构
        
        Args:
            content: 内容数据
            
        Returns:
            验证结果
        """
        required_fields = ['title', 'summary', 'mindmap', 'processed_time']
        missing_fields = []
        empty_fields = []
        
        for field in required_fields:
            if field not in content:
                missing_fields.append(field)
            elif not content[field] or (isinstance(content[field], str) and not content[field].strip()):
                empty_fields.append(field)
        
        if missing_fields:
            return {
                'valid': False,
                'message': f'缺少必需字段: {missing_fields}'
            }
        
        if empty_fields:
            return {
                'valid': False,
                'message': f'字段内容为空: {empty_fields}'
            }
        
        # 检查内容长度
        if len(content['title']) > 200:
            return {
                'valid': False,
                'message': '标题过长（最多200字符）'
            }
        
        if len(content['summary']) > 10000:
            return {
                'valid': False,
                'message': '摘要过长（最多10000字符）'
            }
        
        return {
            'valid': True,
            'message': '内容结构有效'
        }


# 工具函数
def clean_html_content(html: str) -> str:
    """清理HTML内容
    
    Args:
        html: HTML内容
        
    Returns:
        清理后的HTML
    """
    # 移除潜在的危险标签和属性
    import re
    
    # 移除script标签
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    
    # 移除on*事件属性
    html = re.sub(r'on\w+="[^"]*"', '', html, flags=re.IGNORECASE)
    
    # 移除javascript:链接
    html = re.sub(r'href="javascript:[^"]*"', 'href="#"', html, flags=re.IGNORECASE)
    
    return html


if __name__ == '__main__':
    # 测试内容格式化服务
    test_config = {
        'site_title': 'Project Bach',
        'site_description': 'AI音频处理结果发布',
        'theme': 'default'
    }
    
    formatter = ContentFormatter(test_config)
    
    # 测试内容数据
    test_content = {
        'title': '测试音频处理结果',
        'summary': '这是一个测试摘要，包含了音频处理的主要内容和关键信息。',
        'mindmap': '''# 测试思维导图
## 主要内容
- 音频分析
- 内容提取
- 结果生成

## 技术方案
- AI处理
- 自然语言处理
- 内容格式化''',
        'processed_time': '2025-08-21T10:30:00',
        'original_file': 'test_audio.mp3',
        'anonymized_names': {
            '张三': '王明',
            '李四': '刘华'
        },
        'file_size': '5.2MB',
        'audio_duration': '8分32秒'
    }
    
    # 格式化测试
    result = formatter.format_content(test_content)
    
    if result['success']:
        print("✅ 内容格式化测试成功")
        print(f"标题: {result['content']['title']}")
        print(f"文件名: {result['content']['filename']}")
        print(f"HTML长度: {len(result['content']['html'])} 字符")
    else:
        print(f"❌ 内容格式化测试失败: {result['error']}")
        
    # 测试索引创建
    test_results = [
        {'title': '音频1', 'date': '2025-08-21', 'file': 'audio1.html', 'summary': '音频1摘要'},
        {'title': '音频2', 'date': '2025-08-20', 'file': 'audio2.html', 'summary': '音频2摘要'}
    ]
    
    index_result = formatter.create_site_index(test_results)
    
    if index_result['success']:
        print("✅ 索引创建测试成功")
        print(f"包含项目数: {index_result['content']['total_items']}")
    else:
        print(f"❌ 索引创建测试失败: {index_result['error']}")