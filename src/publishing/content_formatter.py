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

from src.utils.config import ConfigManager


class ContentFormatter:
    """内容格式化服务
    
    Phase 6 增强版本，支持多媒体内容类型的专门格式化:
    - lecture (🎓 学术讲座)
    - youtube (📺 YouTube视频) 
    - rss (📰 RSS文章)
    - podcast (🎙️ 播客内容)
    """
    
    def __init__(self, config: Dict[str, Any], config_manager: Optional[ConfigManager] = None):
        """初始化内容格式化服务
        
        Args:
            config: 格式化配置
            config_manager: 配置管理器实例（用于获取内容类型配置）
        """
        self.config = config
        self.config_manager = config_manager
        self.logger = logging.getLogger('project_bach.content_formatter')
        
        # 加载内容类型配置
        if config_manager:
            try:
                self.content_types_config = config_manager.get_content_types_config()
                self.classification_config = config_manager.get_classification_config()
                self.logger.info(f"加载内容类型配置: {list(self.content_types_config.keys())}")
            except Exception as e:
                self.logger.warning(f"无法加载内容类型配置: {e}，使用默认配置")
                self.content_types_config = self._get_default_content_types()
                self.classification_config = {}
        else:
            self.content_types_config = self._get_default_content_types()
            self.classification_config = {}
        
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
        
        self.logger.info("Phase 6 内容格式化服务初始化完成")
    
    def format_content(self, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """格式化多媒体内容处理结果为发布内容
        
        Phase 6 增强版本，支持不同内容类型的专门格式化
        
        Args:
            content_data: 多媒体内容处理结果数据
            
        Returns:
            格式化后的内容
        """
        self.logger.info(f"格式化内容: {content_data.get('title', '未知')}")
        
        try:
            # 验证输入数据
            validation_result = self.validate_content_structure(content_data)
            if not validation_result['valid']:
                raise ValueError(f"内容结构无效: {validation_result['message']}")
            
            # 检测和应用内容类型特定格式化
            content_type = self._detect_content_type(content_data)
            self.logger.info(f"检测到内容类型: {content_type}")
            
            # 生成类型特定的Markdown内容
            markdown_content = self._generate_type_specific_markdown(content_data, content_type)
            
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
                    'content_type': content_type,
                    'formatted_time': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            self.logger.error(f"内容格式化失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_default_content_types(self) -> Dict[str, Any]:
        """获取默认内容类型配置（兼容模式）
        
        Returns:
            默认内容类型配置
        """
        return {
            'lecture': {
                'icon': '🎓',
                'display_name': '讲座',
                'description': '学术讲座、课程录音、教育内容'
            },
            'youtube': {
                'icon': '📺', 
                'display_name': '视频',
                'description': 'YouTube视频内容、教学视频、技术分享'
            },
            'rss': {
                'icon': '📰',
                'display_name': '文章', 
                'description': 'RSS订阅文章、技术博客、新闻资讯'
            },
            'podcast': {
                'icon': '🎙️',
                'display_name': '播客',
                'description': '播客节目、访谈内容、讨论节目'
            }
        }
    
    def _detect_content_type(self, content_data: Dict[str, Any]) -> str:
        """检测内容类型
        
        Args:
            content_data: 内容数据
            
        Returns:
            检测到的内容类型
        """
        # 优先使用已有的分类结果
        if 'classification_result' in content_data:
            classification = content_data['classification_result']
            if isinstance(classification, dict) and 'content_type' in classification:
                return classification['content_type']
        
        # 如果有直接的content_type字段
        if 'content_type' in content_data:
            return content_data['content_type']
        
        # 基于文件名或其他信息进行简单推断
        original_file = content_data.get('original_file', '').lower()
        
        if any(keyword in original_file for keyword in ['youtube', 'video', 'tutorial']):
            return 'youtube'
        elif any(keyword in original_file for keyword in ['rss', 'feed', 'article', 'news']):
            return 'rss'
        elif any(keyword in original_file for keyword in ['podcast', 'interview', 'talk']):
            return 'podcast'
        elif any(keyword in original_file for keyword in ['lecture', 'course', 'professor', 'class']):
            return 'lecture'
        
        # 默认为lecture类型
        return 'lecture'
    
    def _generate_type_specific_markdown(self, content_data: Dict[str, Any], content_type: str) -> str:
        """生成类型特定的Markdown内容
        
        Args:
            content_data: 内容数据
            content_type: 内容类型
            
        Returns:
            类型特定的Markdown内容
        """
        # 获取类型配置
        type_config = self.content_types_config.get(content_type, {})
        type_icon = type_config.get('icon', '📄')
        type_name = type_config.get('display_name', content_type.title())
        
        # 根据类型生成不同的内容结构
        if content_type == 'youtube':
            return self._generate_youtube_markdown(content_data, type_icon, type_name)
        elif content_type == 'rss':
            return self._generate_rss_markdown(content_data, type_icon, type_name)
        elif content_type == 'podcast':
            return self._generate_podcast_markdown(content_data, type_icon, type_name)
        elif content_type == 'lecture':
            return self._generate_lecture_markdown(content_data, type_icon, type_name)
        else:
            # 通用格式
            return self._generate_generic_markdown(content_data, type_icon, type_name)
    
    def _generate_youtube_markdown(self, content_data: Dict[str, Any], icon: str, type_name: str) -> str:
        """生成YouTube视频专用Markdown格式
        
        Args:
            content_data: 内容数据
            icon: 类型图标
            type_name: 类型显示名称
            
        Returns:
            YouTube格式的Markdown
        """
        # 处理时间格式化
        formatted_time = self._format_time(content_data.get('processed_time'))
        
        # 提取YouTube特有信息
        source_url = content_data.get('source_url', '')
        video_title = content_data.get('video_title', content_data.get('title', ''))
        channel_name = content_data.get('channel_name', '')
        video_duration = content_data.get('video_duration', content_data.get('audio_duration', ''))
        view_count = content_data.get('view_count', '')
        
        markdown = f"""# {icon} {video_title}

**内容类型**: {type_name}  
**处理时间**: {formatted_time}  
**原始视频**: `{content_data.get('original_file', '未知')}`  
**视频链接**: {source_url if source_url else '未提供'}  
**频道名称**: {channel_name if channel_name else '未知'}  
**视频时长**: {video_duration if video_duration else '未知'}  
**观看次数**: {view_count if view_count else '未知'}  
**处理状态**: ✅ 完成

---

## 📹 视频信息

{self._format_video_metadata(content_data)}

---

## 📄 内容摘要

{self._clean_text(content_data.get('summary', ''))[:2000]}

---

## 🧠 知识提取

{self._format_mindmap(content_data.get('mindmap', ''))}

---

## 🏷️ 内容标签

{self._format_content_tags(content_data)}

---

## 📊 处理统计

{self._generate_statistics(content_data)}

---

<div class="footer youtube-footer">
<p><em>📺 YouTube视频由 <a href="https://github.com/project-bach">Project Bach</a> 智能分析</em></p>
<p><small>分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small></p>
</div>
"""
        return markdown
    
    def _generate_rss_markdown(self, content_data: Dict[str, Any], icon: str, type_name: str) -> str:
        """生成RSS文章专用Markdown格式"""
        formatted_time = self._format_time(content_data.get('processed_time'))
        
        # RSS特有信息
        source_url = content_data.get('source_url', '')
        author = content_data.get('author', '')
        published_date = content_data.get('published_date', '')
        category = content_data.get('category', '')
        
        markdown = f"""# {icon} {content_data.get('title', '未知标题')}

**内容类型**: {type_name}  
**处理时间**: {formatted_time}  
**原始文章**: `{content_data.get('original_file', '未知')}`  
**文章链接**: {source_url if source_url else '未提供'}  
**作者**: {author if author else '未知'}  
**发布日期**: {published_date if published_date else '未知'}  
**分类**: {category if category else '未分类'}  
**处理状态**: ✅ 完成

---

## 📰 文章摘要

{self._clean_text(content_data.get('summary', ''))[:2000]}

---

## 🔍 关键信息提取

{self._format_mindmap(content_data.get('mindmap', ''))}

---

## 🏷️ 文章标签

{self._format_content_tags(content_data)}

---

## 📊 处理统计

{self._generate_statistics(content_data)}

---

<div class="footer rss-footer">
<p><em>📰 RSS文章由 <a href="https://github.com/project-bach">Project Bach</a> 智能分析</em></p>
<p><small>分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small></p>
</div>
"""
        return markdown
    
    def _generate_podcast_markdown(self, content_data: Dict[str, Any], icon: str, type_name: str) -> str:
        """生成播客专用Markdown格式"""
        formatted_time = self._format_time(content_data.get('processed_time'))
        
        # 播客特有信息
        episode_number = content_data.get('episode_number', '')
        host_name = content_data.get('host_name', '')
        guest_names = content_data.get('guest_names', [])
        podcast_series = content_data.get('podcast_series', '')
        
        markdown = f"""# {icon} {content_data.get('title', '未知标题')}

**内容类型**: {type_name}  
**处理时间**: {formatted_time}  
**原始文件**: `{content_data.get('original_file', '未知')}`  
**播客系列**: {podcast_series if podcast_series else '未知'}  
**集数**: {episode_number if episode_number else '未知'}  
**主持人**: {host_name if host_name else '未知'}  
**嘉宾**: {', '.join(guest_names) if guest_names else '无'}  
**音频时长**: {content_data.get('audio_duration', '未知')}  
**处理状态**: ✅ 完成

---

## 🎙️ 节目摘要

{self._clean_text(content_data.get('summary', ''))[:2000]}

---

## 💬 对话要点

{self._format_mindmap(content_data.get('mindmap', ''))}

---

## 👥 人物信息

{self._format_anonymization_info(content_data.get('anonymized_names', {}))}

---

## 🏷️ 话题标签

{self._format_content_tags(content_data)}

---

## 📊 处理统计

{self._generate_statistics(content_data)}

---

<div class="footer podcast-footer">
<p><em>🎙️ 播客内容由 <a href="https://github.com/project-bach">Project Bach</a> 智能分析</em></p>
<p><small>分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small></p>
</div>
"""
        return markdown
    
    def _generate_lecture_markdown(self, content_data: Dict[str, Any], icon: str, type_name: str) -> str:
        """生成学术讲座专用Markdown格式"""
        formatted_time = self._format_time(content_data.get('processed_time'))
        
        # 讲座特有信息
        lecturer = content_data.get('lecturer', '')
        institution = content_data.get('institution', '')
        course_name = content_data.get('course_name', '')
        academic_field = content_data.get('academic_field', '')
        
        markdown = f"""# {icon} {content_data.get('title', '未知标题')}

**内容类型**: {type_name}  
**处理时间**: {formatted_time}  
**原始文件**: `{content_data.get('original_file', '未知')}`  
**讲师**: {lecturer if lecturer else '未知'}  
**机构**: {institution if institution else '未知'}  
**课程名称**: {course_name if course_name else '未知'}  
**学科领域**: {academic_field if academic_field else '未知'}  
**讲座时长**: {content_data.get('audio_duration', '未知')}  
**处理状态**: ✅ 完成

---

## 📚 讲座摘要

{self._clean_text(content_data.get('summary', ''))[:2000]}

---

## 🧠 知识框架

{self._format_mindmap(content_data.get('mindmap', ''))}

---

## 👥 人名处理

{self._format_anonymization_info(content_data.get('anonymized_names', {}))}

---

## 🔬 学术标签

{self._format_content_tags(content_data)}

---

## 📊 处理统计

{self._generate_statistics(content_data)}

---

<div class="footer lecture-footer">
<p><em>🎓 学术讲座由 <a href="https://github.com/project-bach">Project Bach</a> 智能分析</em></p>
<p><small>分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small></p>
</div>
"""
        return markdown
    
    def _generate_generic_markdown(self, content_data: Dict[str, Any], icon: str, type_name: str) -> str:
        """生成通用Markdown格式（兼容原有格式）"""
        return self._generate_markdown_content(content_data)
    
    def _format_time(self, timestamp: Any) -> str:
        """格式化时间戳
        
        Args:
            timestamp: 时间戳
            
        Returns:
            格式化的时间字符串
        """
        if not timestamp:
            return datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')
        
        if isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                return dt.strftime('%Y年%m月%d日 %H:%M:%S')
            except:
                return str(timestamp)
        else:
            return str(timestamp)
    
    def _format_video_metadata(self, content_data: Dict[str, Any]) -> str:
        """格式化视频元数据"""
        metadata_items = []
        
        if content_data.get('video_description'):
            metadata_items.append(f"**视频描述**: {content_data['video_description'][:300]}...")
        
        if content_data.get('upload_date'):
            metadata_items.append(f"**上传日期**: {content_data['upload_date']}")
        
        if content_data.get('video_tags'):
            tags = content_data['video_tags']
            if isinstance(tags, list):
                metadata_items.append(f"**原始标签**: {', '.join(tags[:10])}")
        
        return '\n'.join(metadata_items) if metadata_items else '暂无详细视频信息'
    
    def _format_content_tags(self, content_data: Dict[str, Any]) -> str:
        """格式化内容标签"""
        # 优先使用分类结果中的标签
        if 'classification_result' in content_data:
            classification = content_data['classification_result']
            if isinstance(classification, dict) and 'tags' in classification:
                tags = classification['tags']
                if tags:
                    return '`' + '` `'.join(tags) + '`'
        
        # 回退到其他标签来源
        if 'extracted_tags' in content_data:
            tags = content_data['extracted_tags']
            if tags:
                return '`' + '` `'.join(tags) + '`'
        
        return '暂无自动提取的标签'
    
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
        
        Phase 6 增强版本，支持多媒体内容类型的专门元数据
        
        Args:
            content_data: 内容数据
            
        Returns:
            元数据字典
        """
        # 检测内容类型
        content_type = self._detect_content_type(content_data)
        type_config = self.content_types_config.get(content_type, {})
        
        # 基础元数据
        metadata = {
            'title': content_data['title'],
            'description': content_data.get('summary', '')[:200] + '...' if len(content_data.get('summary', '')) > 200 else content_data.get('summary', ''),
            'keywords': self._extract_enhanced_keywords(content_data, content_type),
            'author': 'Project Bach',
            'created': content_data.get('processed_time', datetime.now().isoformat()),
            'language': 'zh-CN',
            'type': f'{content_type}-analysis',
            'content_type': content_type,
            'content_type_display': type_config.get('display_name', content_type.title()),
            'content_type_icon': type_config.get('icon', '📄')
        }
        
        # 类型特定的元数据
        if content_type == 'youtube':
            metadata.update({
                'source_platform': 'YouTube',
                'video_url': content_data.get('source_url', ''),
                'channel': content_data.get('channel_name', ''),
                'video_duration': content_data.get('video_duration', content_data.get('audio_duration', '')),
                'view_count': content_data.get('view_count', '')
            })
        elif content_type == 'rss':
            metadata.update({
                'source_platform': 'RSS',
                'article_url': content_data.get('source_url', ''),
                'article_author': content_data.get('author', ''),
                'published_date': content_data.get('published_date', ''),
                'category': content_data.get('category', '')
            })
        elif content_type == 'podcast':
            metadata.update({
                'source_platform': 'Podcast',
                'episode_number': content_data.get('episode_number', ''),
                'host': content_data.get('host_name', ''),
                'guests': content_data.get('guest_names', []),
                'series': content_data.get('podcast_series', ''),
                'duration': content_data.get('audio_duration', '')
            })
        elif content_type == 'lecture':
            metadata.update({
                'source_platform': 'Academic',
                'lecturer': content_data.get('lecturer', ''),
                'institution': content_data.get('institution', ''),
                'course': content_data.get('course_name', ''),
                'field': content_data.get('academic_field', ''),
                'duration': content_data.get('audio_duration', '')
            })
        
        # 添加分类结果信息
        if 'classification_result' in content_data:
            classification = content_data['classification_result']
            if isinstance(classification, dict):
                metadata.update({
                    'auto_detected': classification.get('auto_detected', True),
                    'classification_confidence': classification.get('confidence', 0.0),
                    'extracted_tags': classification.get('tags', [])
                })
        
        return metadata
    
    def _extract_keywords(self, content_data: Dict[str, Any]) -> List[str]:
        """提取关键词（兼容版本）
        
        Args:
            content_data: 内容数据
            
        Returns:
            关键词列表
        """
        return self._extract_enhanced_keywords(content_data, 'lecture')
    
    def _extract_enhanced_keywords(self, content_data: Dict[str, Any], content_type: str) -> List[str]:
        """提取增强关键词
        
        Phase 6 版本，根据内容类型提取专门关键词
        
        Args:
            content_data: 内容数据
            content_type: 内容类型
            
        Returns:
            关键词列表
        """
        # 基础关键词
        keywords = ['多媒体处理', 'AI分析', '内容摘要']
        
        # 根据内容类型添加特定关键词
        if content_type == 'youtube':
            keywords.extend(['YouTube', '视频处理', '在线内容', '教学视频'])
        elif content_type == 'rss':
            keywords.extend(['RSS订阅', '文章分析', '新闻处理', '博客内容'])
        elif content_type == 'podcast':
            keywords.extend(['播客', '音频节目', '访谈内容', '对话分析'])
        elif content_type == 'lecture':
            keywords.extend(['学术讲座', '教育内容', '课程录音', '知识传播'])
        
        # 从标题提取
        title = content_data.get('title', '')
        title_keywords = {
            '会议': '会议',
            '讲座': '讲座',
            '培训': '培训',
            '课程': '课程',
            '教程': '教程',
            '访谈': '访谈',
            '对话': '对话',
            '新闻': '新闻',
            '技术': '技术分享',
            '科学': '科学研究',
            '医学': '医学内容',
            '商业': '商业分析',
            '经济': '经济讨论',
            'AI': '人工智能',
            '机器学习': '机器学习',
            '数据': '数据分析'
        }
        
        for term, keyword in title_keywords.items():
            if term in title:
                keywords.append(keyword)
        
        # 从摘要提取专业词汇
        summary = content_data.get('summary', '')
        summary_keywords = {
            '项目': '项目管理',
            '技术': '技术讨论',
            '决策': '决策分析',
            '研究': '学术研究',
            '开发': '软件开发',
            '设计': '设计思维',
            '创新': '创新理念',
            '产品': '产品管理',
            '市场': '市场分析',
            '用户': '用户体验',
            '数据': '数据科学',
            '算法': '算法分析',
            '系统': '系统设计',
            '架构': '技术架构',
            '安全': '网络安全',
            '云计算': '云计算',
            '区块链': '区块链',
            '物联网': '物联网',
            '大数据': '大数据',
            '深度学习': '深度学习'
        }
        
        for term, keyword in summary_keywords.items():
            if term in summary:
                keywords.append(keyword)
        
        # 从分类结果获取标签
        if 'classification_result' in content_data:
            classification = content_data['classification_result']
            if isinstance(classification, dict) and 'tags' in classification:
                classification_tags = classification['tags']
                if isinstance(classification_tags, list):
                    keywords.extend(classification_tags[:5])  # 最多添加5个分类标签
        
        # 去重并限制数量
        unique_keywords = list(set(keywords))
        return unique_keywords[:15]  # 最多返回15个关键词
    
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
        
        Phase 6 增强版本，支持内容类型分类显示
        
        Args:
            results: 所有处理结果列表
            
        Returns:
            索引页面内容
        """
        self.logger.info(f"创建Phase 6网站索引，包含{len(results)}个结果")
        
        try:
            # 按日期排序（最新的在前）
            sorted_results = sorted(
                results, 
                key=lambda x: x.get('date', ''), 
                reverse=True
            )
            
            # 按内容类型分组统计
            type_stats = self._analyze_content_types(sorted_results)
            
            # 生成索引Markdown
            index_markdown = self._generate_enhanced_index_markdown(sorted_results, type_stats)
            
            # 转换为HTML
            index_html = self.generate_html_from_markdown(index_markdown)
            
            # 生成元数据
            metadata = {
                'title': 'Project Bach - 多媒体内容处理结果',
                'description': f'共收录{len(results)}个多媒体内容处理结果，包含{len(type_stats)}种内容类型',
                'keywords': ['多媒体处理', 'AI分析', '内容分类', '结果索引'] + list(type_stats.keys()),
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
                    'title': 'Project Bach - 多媒体内容处理结果',
                    'total_items': len(results),
                    'content_type_stats': type_stats
                }
            }
            
        except Exception as e:
            self.logger.error(f"创建索引失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _analyze_content_types(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析内容类型统计
        
        Args:
            results: 处理结果列表
            
        Returns:
            内容类型统计字典
        """
        type_stats = {}
        
        for result in results:
            # 尝试从不同字段获取内容类型
            content_type = None
            
            # 优先级1: content_type字段
            if 'content_type' in result:
                content_type = result['content_type']
            # 优先级2: classification_result中的content_type
            elif 'classification_result' in result:
                classification = result['classification_result']
                if isinstance(classification, dict) and 'content_type' in classification:
                    content_type = classification['content_type']
            # 优先级3: 从文件名推断
            elif 'file' in result or 'original_file' in result:
                filename = result.get('file', result.get('original_file', '')).lower()
                content_type = self._infer_type_from_filename(filename)
            
            # 默认为lecture
            if not content_type:
                content_type = 'lecture'
            
            # 统计
            if content_type not in type_stats:
                type_config = self.content_types_config.get(content_type, {})
                type_stats[content_type] = {
                    'count': 0,
                    'icon': type_config.get('icon', '📄'),
                    'display_name': type_config.get('display_name', content_type.title()),
                    'description': type_config.get('description', ''),
                    'recent_items': []
                }
            
            type_stats[content_type]['count'] += 1
            
            # 记录最近的条目（最多5个）
            if len(type_stats[content_type]['recent_items']) < 5:
                type_stats[content_type]['recent_items'].append({
                    'title': result.get('title', '未知标题')[:30],
                    'date': result.get('date', ''),
                    'file': result.get('file', '#')
                })
        
        return type_stats
    
    def _infer_type_from_filename(self, filename: str) -> str:
        """从文件名推断内容类型"""
        if any(keyword in filename for keyword in ['youtube', 'video', 'tutorial']):
            return 'youtube'
        elif any(keyword in filename for keyword in ['rss', 'feed', 'article', 'news']):
            return 'rss'
        elif any(keyword in filename for keyword in ['podcast', 'interview', 'talk']):
            return 'podcast'
        elif any(keyword in filename for keyword in ['lecture', 'course', 'professor', 'class']):
            return 'lecture'
        else:
            return 'lecture'
    
    def _generate_enhanced_index_markdown(self, results: List[Dict[str, Any]], type_stats: Dict[str, Any]) -> str:
        """生成增强的索引页面Markdown
        
        Args:
            results: 结果列表
            type_stats: 内容类型统计
            
        Returns:
            增强的索引Markdown内容
        """
        # 页面头部
        markdown = f"""# Project Bach 多媒体内容处理结果

> 🎵 智能多媒体内容处理与分析平台  
> 📊 **共收录 {len(results)} 个处理结果**  
> 🏷️ **包含 {len(type_stats)} 种内容类型**

---

## 📋 内容类型概览

"""
        
        # 内容类型统计卡片
        for content_type, stats in type_stats.items():
            icon = stats['icon']
            name = stats['display_name']
            count = stats['count']
            description = stats['description']
            
            markdown += f"""### {icon} {name} ({count}个)

{description}

"""
            
            # 显示最近的条目
            if stats['recent_items']:
                markdown += "**最新内容**:\n"
                for item in stats['recent_items']:
                    markdown += f"- [{item['title']}]({item['file']}) - {item['date']}\n"
                markdown += "\n"
        
        markdown += "---\n\n"
        
        # 最新结果表格
        markdown += """## 📋 最新结果

"""
        
        if not results:
            markdown += "暂无处理结果。\n"
        else:
            # 结果表格（增加类型列）
            markdown += """| 类型 | 日期 | 标题 | 摘要预览 | 操作 |
|------|------|------|----------|------|
"""
            
            for result in results[:20]:  # 只显示最新20个
                # 获取内容类型图标
                content_type = result.get('content_type', 'lecture')
                type_icon = type_stats.get(content_type, {}).get('icon', '📄')
                
                title = result.get('title', '未知标题')[:30]
                date = result.get('date', '未知日期')
                preview = result.get('summary', '暂无摘要')[:50] + '...' if len(result.get('summary', '')) > 50 else result.get('summary', '暂无摘要')
                filename = result.get('file', '#')
                
                markdown += f"| {type_icon} | {date} | [{title}]({filename}) | {preview} | [查看详情]({filename}) |\n"
            
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
| 内容类型数 | {len(type_stats)} |
| 本月新增 | {self._count_this_month(results)} |
| 本周新增 | {self._count_this_week(results)} |
| 最后更新 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |

### 🏷️ 类型分布

"""
        
        # 类型分布统计
        for content_type, stats in sorted(type_stats.items(), key=lambda x: x[1]['count'], reverse=True):
            percentage = (stats['count'] / len(results)) * 100
            markdown += f"- {stats['icon']} **{stats['display_name']}**: {stats['count']} 个 ({percentage:.1f}%)\n"
        
        markdown += f"""

---

## 🔍 快速导航

### 📱 按内容类型浏览
"""
        
        # 按类型导航链接
        for content_type, stats in type_stats.items():
            markdown += f"- [{stats['icon']} {stats['display_name']}](#{content_type}.html) - {stats['count']} 个内容\n"
        
        markdown += f"""

### 🛠️ 功能页面
- [📈 数据统计](stats.html) - 处理结果统计分析
- [🏷️ 标签云](tags.html) - 内容标签分类
- [🔎 搜索功能](search.html) - 搜索处理结果
- [ℹ️ 关于项目](about.html) - Project Bach 介绍

---

<div class="footer enhanced-footer">
<p><strong>Project Bach</strong> - 智能多媒体内容处理与分析平台</p>
<p><em>最后更新: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</em></p>
<p>
    <a href="https://github.com/project-bach" target="_blank">🔗 GitHub</a> | 
    <a href="mailto:contact@project-bach.com">📧 联系我们</a> |
    <span class="version">Phase 6 Enhanced</span>
</p>
</div>
"""
        
        return markdown
    
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