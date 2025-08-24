#!/usr/bin/env python3
"""
Phase 6 YouTube处理器

集成yt-dlp实现YouTube视频的音频提取和元数据获取
支持多种YouTube URL格式，包含时长验证和质量控制
"""

import re
import json
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse, parse_qs
from datetime import datetime

from src.utils.config import ConfigManager


class YouTubeProcessor:
    """YouTube视频处理器
    
    功能：
    1. YouTube URL验证和视频ID提取
    2. 视频信息获取（yt-dlp集成）
    3. 音频下载和格式转换
    4. 元数据提取和格式化
    5. 时长和质量验证
    """
    
    def __init__(self, config_manager: ConfigManager):
        """初始化YouTube处理器
        
        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger('project_bach.youtube_processor')
        
        # 加载YouTube配置
        self.youtube_config = config_manager.get_nested_config('youtube')
        if not self.youtube_config:
            raise ValueError("YouTube配置缺失，请检查config.yaml中的youtube部分")
        
        # 下载器配置
        downloader_config = self.youtube_config.get('downloader', {})
        self.max_duration = downloader_config.get('max_duration', 7200)  # 2小时
        self.min_duration = downloader_config.get('min_duration', 60)    # 1分钟
        self.preferred_quality = downloader_config.get('preferred_quality', 'best[height<=720]')
        self.extract_audio_only = downloader_config.get('extract_audio_only', True)
        self.output_format = downloader_config.get('output_format', 'mp3')
        self.timeout = downloader_config.get('timeout', 600)
        
        # 输出目录
        output_dir = downloader_config.get('output_dir', './temp/youtube')
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 验证配置
        validation_config = self.youtube_config.get('validation', {})
        self.check_availability = validation_config.get('check_availability', True)
        self.validate_duration = validation_config.get('validate_duration', True)
        self.skip_private = validation_config.get('skip_private', True)
        self.skip_age_restricted = validation_config.get('skip_age_restricted', False)
        
        # 元数据配置
        metadata_config = self.youtube_config.get('metadata', {})
        self.extract_thumbnail = metadata_config.get('extract_thumbnail', True)
        self.extract_description = metadata_config.get('extract_description', True)
        self.extract_tags = metadata_config.get('extract_tags', True)
        self.extract_comments = metadata_config.get('extract_comments', False)
        
        # 字幕配置
        subtitle_config = self.youtube_config.get('subtitles', {
            'enabled': True,
            'strategy': 'manual_only',  # 'manual_only', 'native_first', 'whisper_only', 'subtitles_only'
            'preferred_languages': ['zh-Hans', 'zh-CN', 'zh-Hant', 'zh-TW', 'en'],
            'fallback_to_whisper': True,
            'prefer_native_over_translated': True,  # 优先原语言而非翻译
            'allow_auto_captions': False,  # 默认禁用自动字幕
            'subtitle_formats': ['vtt', 'srt']
        })
        self.subtitles_enabled = subtitle_config.get('enabled', True)
        self.subtitle_strategy = subtitle_config.get('strategy', 'manual_only')
        self.preferred_languages = subtitle_config.get('preferred_languages', ['zh-Hans', 'zh-CN', 'zh-Hant', 'zh-TW', 'en'])
        self.fallback_to_whisper = subtitle_config.get('fallback_to_whisper', True)
        self.prefer_native_over_translated = subtitle_config.get('prefer_native_over_translated', True)
        self.allow_auto_captions = subtitle_config.get('allow_auto_captions', False)
        self.subtitle_formats = subtitle_config.get('subtitle_formats', ['vtt', 'srt'])
        
        # YouTube URL模式
        self.youtube_patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
            r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})',
            r'(?:https?://)?(?:m\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
            r'(?:https?://)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})'
        ]
        
        self.logger.info("YouTube处理器初始化完成")
    
    def validate_youtube_url(self, url: str) -> bool:
        """验证YouTube URL格式
        
        Args:
            url: YouTube URL
            
        Returns:
            是否为有效的YouTube URL
        """
        if not url or not isinstance(url, str):
            return False
        
        for pattern in self.youtube_patterns:
            if re.search(pattern, url):
                return True
        
        return False
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """从YouTube URL提取视频ID
        
        Args:
            url: YouTube URL
            
        Returns:
            视频ID，如果无法提取则返回None
        """
        if not url:
            return None
        
        for pattern in self.youtube_patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def get_video_info(self, url: str) -> Dict[str, Any]:
        """获取YouTube视频信息
        
        Args:
            url: YouTube URL
            
        Returns:
            包含视频信息或错误信息的字典
        """
        try:
            # 构建yt-dlp命令
            cmd = [
                'yt-dlp',
                '--dump-json',
                '--no-warnings',
                '--no-playlist',
                url
            ]
            
            self.logger.info(f"获取视频信息: {url}")
            
            # 执行命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() or "获取视频信息失败"
                self.logger.error(f"yt-dlp错误: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }
            
            # 解析JSON输出
            try:
                video_info = json.loads(result.stdout)
                self.logger.info(f"成功获取视频信息: {video_info.get('title', 'Unknown')}")
                return {
                    'success': True,
                    'info': video_info
                }
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON解析错误: {e}")
                return {
                    'success': False,
                    'error': f"JSON解析错误: {e}"
                }
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"获取视频信息超时: {url}")
            return {
                'success': False,
                'error': "获取视频信息超时"
            }
        except Exception as e:
            self.logger.error(f"获取视频信息异常: {e}")
            return {
                'success': False,
                'error': f"获取视频信息异常: {e}"
            }
    
    def validate_video_info(self, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """验证视频信息
        
        Args:
            video_info: yt-dlp返回的视频信息
            
        Returns:
            验证结果字典
        """
        # 检查时长
        duration = video_info.get('duration')
        if duration is not None and self.validate_duration:
            if duration > self.max_duration:
                return {
                    'valid': False,
                    'message': f"视频时长({duration}秒)超过限制({self.max_duration}秒)"
                }
            elif duration < self.min_duration:
                return {
                    'valid': False,
                    'message': f"视频时长({duration}秒)少于最小限制({self.min_duration}秒)"
                }
        
        # 检查可用性
        availability = video_info.get('availability', '').lower()
        if self.check_availability:
            if availability in ['private', 'needs_auth', 'premium_only']:
                if self.skip_private and availability == 'private':
                    return {
                        'valid': False,
                        'message': "跳过私有视频"
                    }
        
        # 检查年龄限制
        age_limit = video_info.get('age_limit', 0)
        if self.skip_age_restricted and age_limit > 0:
            return {
                'valid': False,
                'message': f"跳过年龄限制视频 (年龄限制: {age_limit}+)"
            }
        
        return {
            'valid': True,
            'message': "视频信息验证通过"
        }
    
    def download_audio(self, url: str, video_id: str) -> Dict[str, Any]:
        """下载YouTube视频的音频
        
        Args:
            url: YouTube URL
            video_id: 视频ID
            
        Returns:
            下载结果字典
        """
        try:
            # 生成输出文件名
            output_filename = f"{video_id}.%(ext)s"
            output_path = self.output_dir / output_filename
            
            # 构建yt-dlp下载命令
            cmd = [
                'yt-dlp',
                '--extract-audio',
                '--audio-format', self.output_format,
                '--audio-quality', '0',  # 最佳质量
                '--no-playlist',
                '--no-warnings',
                '-o', str(output_path),
            ]
            
            # 添加质量选择
            if not self.extract_audio_only:
                cmd.extend(['--format', self.preferred_quality])
            
            cmd.append(url)
            
            self.logger.info(f"开始下载音频: {video_id}")
            
            # 执行下载命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() or "音频下载失败"
                self.logger.error(f"下载失败: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }
            
            # 确定实际输出文件路径
            actual_output_file = self.output_dir / f"{video_id}.{self.output_format}"
            
            if not actual_output_file.exists():
                # 尝试查找可能的文件名
                possible_files = list(self.output_dir.glob(f"{video_id}.*"))
                if possible_files:
                    actual_output_file = possible_files[0]
                else:
                    return {
                        'success': False,
                        'error': "下载文件未找到"
                    }
            
            self.logger.info(f"音频下载成功: {actual_output_file}")
            return {
                'success': True,
                'output_file': str(actual_output_file)
            }
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"音频下载超时: {video_id}")
            return {
                'success': False,
                'error': "音频下载超时"
            }
        except Exception as e:
            self.logger.error(f"音频下载异常: {e}")
            return {
                'success': False,
                'error': f"音频下载异常: {e}"
            }
    
    def format_video_metadata(self, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """格式化视频元数据
        
        Args:
            video_info: yt-dlp返回的视频信息
            
        Returns:
            格式化后的元数据
        """
        # 基础信息
        metadata = {
            'video_id': video_info.get('id', ''),
            'title': video_info.get('title', ''),
            'channel_name': video_info.get('uploader', ''),
            'description': video_info.get('description', ''),
            'upload_date': video_info.get('upload_date', ''),
            'duration': video_info.get('duration', 0),
            'view_count': video_info.get('view_count', 0),
            'like_count': video_info.get('like_count', 0),
            'tags': video_info.get('tags', []),
            'categories': video_info.get('categories', []),
            'thumbnail_url': ''
        }
        
        # 格式化时长
        if metadata['duration']:
            metadata['duration_formatted'] = self.format_duration(metadata['duration'])
        else:
            metadata['duration_formatted'] = '未知'
        
        # 格式化观看次数
        if metadata['view_count']:
            metadata['view_count_formatted'] = self.format_view_count(metadata['view_count'])
        else:
            metadata['view_count_formatted'] = '未知'
        
        # 格式化上传日期
        if metadata['upload_date']:
            try:
                date_obj = datetime.strptime(metadata['upload_date'], '%Y%m%d')
                metadata['upload_date_formatted'] = date_obj.strftime('%Y-%m-%d')
            except:
                metadata['upload_date_formatted'] = metadata['upload_date']
        else:
            metadata['upload_date_formatted'] = '未知'
        
        # 缩略图
        thumbnails = video_info.get('thumbnails', [])
        if thumbnails:
            # 选择最高质量的缩略图
            best_thumbnail = max(thumbnails, key=lambda x: x.get('width', 0) * x.get('height', 0))
            metadata['thumbnail_url'] = best_thumbnail.get('url', '')
        
        # 描述预览（前200字符）
        if metadata['description']:
            metadata['description_preview'] = metadata['description'][:200] + '...' if len(metadata['description']) > 200 else metadata['description']
        else:
            metadata['description_preview'] = '无描述'
        
        return metadata
    
    def format_duration(self, seconds: int) -> str:
        """格式化时长
        
        Args:
            seconds: 秒数
            
        Returns:
            格式化的时长字符串 (如 "1:23:45" 或 "5:30")
        """
        if seconds <= 0:
            return "0:00"
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
    
    def format_view_count(self, count: int) -> str:
        """格式化观看次数
        
        Args:
            count: 观看次数
            
        Returns:
            格式化的观看次数字符串 (如 "1,234,567")
        """
        return f"{count:,}"
    
    def get_available_subtitles(self, url: str) -> Dict[str, Any]:
        """获取视频可用字幕信息
        
        Args:
            url: YouTube URL
            
        Returns:
            包含可用字幕信息的字典
        """
        try:
            cmd = [
                'yt-dlp',
                '--list-subs',
                '--no-warnings',
                '--no-playlist',
                url
            ]
            
            self.logger.info(f"获取字幕信息: {url}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=False
            )
            
            if result.returncode != 0:
                self.logger.warning(f"获取字幕信息失败: {result.stderr}")
                return {
                    'available': False,
                    'subtitles': {},
                    'auto_captions': {}
                }
            
            # 解析输出获取字幕信息
            lines = result.stdout.split('\n')
            subtitles = {}
            auto_captions = {}
            current_section = None
            
            for line in lines:
                line = line.strip()
                if 'Available subtitles' in line:
                    current_section = 'subtitles'
                elif 'Available automatic captions' in line:
                    current_section = 'auto_captions'
                elif line and current_section and not line.startswith('Language'):
                    # 解析字幕语言行
                    parts = line.split()
                    if len(parts) >= 2:
                        lang = parts[0]
                        formats = parts[1:]
                        if current_section == 'subtitles':
                            subtitles[lang] = formats
                        else:
                            auto_captions[lang] = formats
            
            has_subtitles = bool(subtitles or auto_captions)
            
            return {
                'available': has_subtitles,
                'subtitles': subtitles,
                'auto_captions': auto_captions,
                'total_languages': len(subtitles) + len(auto_captions)
            }
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"获取字幕信息超时: {url}")
            return {'available': False, 'subtitles': {}, 'auto_captions': {}}
        except Exception as e:
            self.logger.error(f"获取字幕信息异常: {e}")
            return {'available': False, 'subtitles': {}, 'auto_captions': {}}
    
    def download_subtitles(self, url: str, video_id: str) -> Dict[str, Any]:
        """下载YouTube视频字幕
        
        Args:
            url: YouTube URL
            video_id: 视频ID
            
        Returns:
            字幕下载结果字典
        """
        if not self.subtitles_enabled:
            return {
                'success': False,
                'error': '字幕功能已禁用',
                'fallback_to_whisper': True
            }
        
        try:
            # 首先检查可用字幕
            subtitle_info = self.get_available_subtitles(url)
            if not subtitle_info['available']:
                self.logger.info(f"视频无可用字幕: {video_id}")
                return {
                    'success': False,
                    'error': '无可用字幕',
                    'fallback_to_whisper': self.fallback_to_whisper
                }
            
            # 确定最佳字幕语言（基于视频内容语言智能选择）
            # 需要先获取视频信息用于语言检测
            video_info_result = self.get_video_info(url)
            video_info = video_info_result.get('info', {}) if video_info_result.get('success') else {}
            
            best_lang = self._select_best_subtitle_language(
                subtitle_info['subtitles'], 
                subtitle_info['auto_captions'],
                video_info
            )
            
            if not best_lang:
                self.logger.info(f"未找到首选语言字幕: {video_id}")
                return {
                    'success': False,
                    'error': '未找到首选语言字幕',
                    'fallback_to_whisper': self.fallback_to_whisper
                }
            
            # 生成字幕文件名
            subtitle_filename = f"{video_id}_{best_lang}.%(ext)s"
            subtitle_path = self.output_dir / subtitle_filename
            
            # 构建字幕下载命令
            cmd = [
                'yt-dlp',
                '--write-subs',
                '--write-auto-subs',
                '--sub-langs', best_lang,
                '--sub-format', '/'.join(self.subtitle_formats),
                '--skip-download',  # 只下载字幕，不下载视频
                '--no-warnings',
                '--no-playlist',
                '-o', str(subtitle_path),
                url
            ]
            
            self.logger.info(f"开始下载字幕: {video_id} (语言: {best_lang})")
            
            # 执行下载命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() or "字幕下载失败"
                self.logger.error(f"字幕下载失败: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'fallback_to_whisper': self.fallback_to_whisper
                }
            
            # 查找下载的字幕文件
            subtitle_files = []
            for fmt in self.subtitle_formats:
                possible_file = self.output_dir / f"{video_id}_{best_lang}.{fmt}"
                if possible_file.exists():
                    subtitle_files.append(possible_file)
            
            if not subtitle_files:
                # 尝试查找可能的文件名变体
                possible_files = list(self.output_dir.glob(f"{video_id}*.vtt")) + \
                               list(self.output_dir.glob(f"{video_id}*.srt"))
                if possible_files:
                    subtitle_files = possible_files
                else:
                    return {
                        'success': False,
                        'error': '字幕文件未找到',
                        'fallback_to_whisper': self.fallback_to_whisper
                    }
            
            # 读取字幕内容并转换为纯文本
            subtitle_text = self._extract_text_from_subtitle(subtitle_files[0])
            
            if not subtitle_text or len(subtitle_text.strip()) < 10:
                return {
                    'success': False,
                    'error': '字幕内容为空或过短',
                    'fallback_to_whisper': self.fallback_to_whisper
                }
            
            self.logger.info(f"字幕下载成功: {subtitle_files[0]} ({len(subtitle_text)}字符)")
            return {
                'success': True,
                'subtitle_file': str(subtitle_files[0]),
                'subtitle_text': subtitle_text,
                'language': best_lang,
                'subtitle_info': subtitle_info
            }
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"字幕下载超时: {video_id}")
            return {
                'success': False,
                'error': "字幕下载超时",
                'fallback_to_whisper': self.fallback_to_whisper
            }
        except Exception as e:
            self.logger.error(f"字幕下载异常: {e}")
            return {
                'success': False,
                'error': f"字幕下载异常: {e}",
                'fallback_to_whisper': self.fallback_to_whisper
            }
    
    def _select_best_subtitle_language(self, subtitles: Dict, auto_captions: Dict, video_info: Dict = None) -> Optional[str]:
        """智能选择最佳字幕语言 - 优先原语言策略
        
        Args:
            subtitles: 手动字幕字典
            auto_captions: 自动字幕字典
            video_info: 视频信息，用于语言检测
            
        Returns:
            最佳字幕语言代码，如果没有找到则返回None
        """
        # 根据策略决定处理方式
        if self.subtitle_strategy == 'whisper_only':
            self.logger.info("配置为仅使用Whisper，跳过字幕")
            return None
        elif self.subtitle_strategy == 'manual_only':
            self.logger.info("配置为仅使用手动字幕，禁用自动字幕")
            # 只考虑手动字幕，忽略自动字幕
        elif self.subtitle_strategy == 'subtitles_only':
            self.logger.info("配置为仅使用字幕，不回退到Whisper")
            # 继续执行字幕选择逻辑
        # 默认 'manual_only' 策略
        
        # 1. 检测视频原始语言
        detected_language = self._detect_video_language(video_info) if video_info else None
        
        if detected_language and self.prefer_native_over_translated:
            self.logger.info(f"检测到视频原语言: {detected_language}，优先选择原语言字幕")
            
            # 获取原语言的所有变体
            native_language_variants = self._get_language_variants(detected_language)
            
            # 第一优先级：原语言手动字幕（最准确）
            for lang in native_language_variants:
                if lang in subtitles:
                    self.logger.info(f"✓ 选择原语言手动字幕: {lang} (最佳选择)")
                    return lang
            
            # 第二优先级：原语言自动字幕（仅在允许时）
            if self.allow_auto_captions or self.subtitle_strategy not in ['manual_only']:
                for lang in native_language_variants:
                    if lang in auto_captions:
                        self.logger.info(f"✓ 选择原语言自动字幕: {lang} (较好选择)")
                        return lang
            
            self.logger.info(f"原语言({detected_language})字幕不可用，回退到其他策略")
        
        # 2. 如果原语言不可用，按配置首选语言查找
        self.logger.info("按配置首选语言查找字幕")
        
        # 手动字幕优先
        for lang in self.preferred_languages:
            if lang in subtitles:
                self.logger.info(f"选择配置首选手动字幕语言: {lang}")
                return lang
        
        # 自动字幕次之（仅在允许时）
        if self.allow_auto_captions or self.subtitle_strategy not in ['manual_only']:
            for lang in self.preferred_languages:
                if lang in auto_captions:
                    self.logger.info(f"选择配置首选自动字幕语言: {lang}")
                    return lang
        
        # 3. 通用备选语言（如果允许自动翻译且manual_only策略允许自动字幕）
        if self.auto_translate and (self.allow_auto_captions or self.subtitle_strategy not in ['manual_only']):
            self.logger.info("尝试自动翻译字幕")
            fallback_langs = ['zh', 'en', 'zh-CN', 'zh-TW', 'en-US', 'en-GB']
            
            # 首先尝试手动字幕
            for lang in fallback_langs:
                if lang in subtitles:
                    self.logger.info(f"选择备选手动字幕语言: {lang} (自动翻译)")
                    return lang
            
            # 然后尝试自动字幕（仅在允许时）        
            if self.allow_auto_captions or self.subtitle_strategy not in ['manual_only']:
                for lang in fallback_langs:
                    if lang in auto_captions:
                        self.logger.info(f"选择备选自动字幕语言: {lang} (自动翻译)")
                        return lang
        
        # 4. 最后选择任意可用的语言（如果允许）
        if self.auto_translate:
            # 优先手动字幕
            if subtitles:
                first_lang = list(subtitles.keys())[0]
                self.logger.info(f"选择首个手动字幕语言: {first_lang} (最后备选)")
                return first_lang
            
            # 自动字幕（仅在允许时）    
            if (self.allow_auto_captions or self.subtitle_strategy not in ['manual_only']) and auto_captions:
                first_lang = list(auto_captions.keys())[0]
                self.logger.info(f"选择首个自动字幕语言: {first_lang} (最后备选)")
                return first_lang
        
        self.logger.info("未找到合适的字幕语言")
        return None
    
    def _detect_video_language(self, video_info: Dict) -> Optional[str]:
        """检测视频内容语言
        
        Args:
            video_info: yt-dlp返回的视频信息
            
        Returns:
            检测到的语言代码 ('zh', 'en', 等)
        """
        try:
            # 检查视频标题
            title = video_info.get('title', '').lower()
            description = video_info.get('description', '').lower()
            uploader = video_info.get('uploader', '').lower()
            
            # 中文检测关键词
            chinese_keywords = [
                '中文', '汉语', '普通话', '国语', '粤语', '台语', 
                '中国', '台湾', '香港', '大陆', '繁体', '简体',
                'chinese', 'mandarin', 'cantonese', 'taiwan', 'china'
            ]
            
            # 英文检测关键词
            english_keywords = [
                'english', 'tutorial', 'lecture', 'course', 'lesson',
                'interview', 'presentation', 'conference', 'talk',
                'university', 'college', 'academy', 'education'
            ]
            
            # 检查中文字符
            chinese_char_count = sum(1 for char in title + description if '\u4e00' <= char <= '\u9fff')
            total_char_count = len(title + description)
            
            # 如果中文字符比例较高
            if total_char_count > 0 and chinese_char_count / total_char_count > 0.3:
                self.logger.info("基于字符分析检测为中文内容")
                return 'zh'
            
            # 检查关键词
            text_to_check = f"{title} {description} {uploader}"
            
            chinese_score = sum(1 for keyword in chinese_keywords if keyword in text_to_check)
            english_score = sum(1 for keyword in english_keywords if keyword in text_to_check)
            
            if chinese_score > english_score and chinese_score > 0:
                self.logger.info(f"基于关键词检测为中文内容 (中文: {chinese_score}, 英文: {english_score})")
                return 'zh'
            elif english_score > chinese_score and english_score > 0:
                self.logger.info(f"基于关键词检测为英文内容 (中文: {chinese_score}, 英文: {english_score})")
                return 'en'
            
            # 检查语言字段
            language = video_info.get('language')
            if language:
                if language.startswith('zh'):
                    return 'zh'
                elif language.startswith('en'):
                    return 'en'
            
            self.logger.info("无法确定视频语言，使用默认策略")
            return None
            
        except Exception as e:
            self.logger.error(f"语言检测异常: {e}")
            return None
    
    def _get_language_variants(self, base_language: str) -> List[str]:
        """获取语言的所有变体
        
        Args:
            base_language: 基础语言代码 ('zh', 'en')
            
        Returns:
            语言变体列表，按优先级排序
        """
        if base_language == 'zh':
            return ['zh-Hans', 'zh-CN', 'zh', 'zh-Hant', 'zh-TW', 'zh-HK', 'zh-SG']
        elif base_language == 'en':
            return ['en', 'en-US', 'en-GB', 'en-AU', 'en-CA', 'en-IN']
        else:
            return [base_language]
    
    def _extract_text_from_subtitle(self, subtitle_file: Path) -> str:
        """从字幕文件提取纯文本
        
        Args:
            subtitle_file: 字幕文件路径
            
        Returns:
            提取的纯文本
        """
        try:
            with open(subtitle_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 处理不同字幕格式
            if subtitle_file.suffix.lower() == '.vtt':
                return self._parse_vtt_content(content)
            elif subtitle_file.suffix.lower() == '.srt':
                return self._parse_srt_content(content)
            else:
                # 尝试自动检测格式
                if 'WEBVTT' in content:
                    return self._parse_vtt_content(content)
                else:
                    return self._parse_srt_content(content)
                    
        except Exception as e:
            self.logger.error(f"读取字幕文件失败 {subtitle_file}: {e}")
            return ""
    
    def _parse_vtt_content(self, content: str) -> str:
        """解析VTT格式字幕内容
        
        Args:
            content: VTT文件内容
            
        Returns:
            提取的纯文本
        """
        lines = content.split('\n')
        text_lines = []
        
        for line in lines:
            line = line.strip()
            # 跳过时间戳行和空行
            if not line or 'WEBVTT' in line or '-->' in line or line.isdigit():
                continue
            # 移除HTML标签
            clean_line = re.sub(r'<[^>]+>', '', line)
            if clean_line:
                text_lines.append(clean_line)
        
        return ' '.join(text_lines)
    
    def _parse_srt_content(self, content: str) -> str:
        """解析SRT格式字幕内容
        
        Args:
            content: SRT文件内容
            
        Returns:
            提取的纯文本
        """
        lines = content.split('\n')
        text_lines = []
        
        for line in lines:
            line = line.strip()
            # 跳过序号行、时间戳行和空行
            if not line or line.isdigit() or '-->' in line:
                continue
            # 移除HTML标签
            clean_line = re.sub(r'<[^>]+>', '', line)
            if clean_line:
                text_lines.append(clean_line)
        
        return ' '.join(text_lines)
    
    def cleanup_temp_files(self, file_paths: List[Path]) -> None:
        """清理临时文件
        
        Args:
            file_paths: 要清理的文件路径列表
        """
        for file_path in file_paths:
            try:
                if file_path.exists():
                    file_path.unlink()
                    self.logger.debug(f"清理临时文件: {file_path}")
            except Exception as e:
                self.logger.warning(f"清理文件失败 {file_path}: {e}")
    
    def process_youtube_url(self, url: str) -> Dict[str, Any]:
        """处理YouTube URL的完整流程
        
        Args:
            url: YouTube URL
            
        Returns:
            处理结果字典，包含视频元数据和音频文件路径
        """
        self.logger.info(f"开始处理YouTube URL: {url}")
        
        try:
            # 1. 验证URL格式
            if not self.validate_youtube_url(url):
                return {
                    'success': False,
                    'error': 'YouTube URL格式无效'
                }
            
            # 2. 提取视频ID
            video_id = self.extract_video_id(url)
            if not video_id:
                return {
                    'success': False,
                    'error': '无法提取视频ID'
                }
            
            # 3. 获取视频信息
            info_result = self.get_video_info(url)
            if not info_result['success']:
                return {
                    'success': False,
                    'error': f"获取视频信息失败: {info_result['error']}"
                }
            
            video_info = info_result['info']
            
            # 4. 验证视频信息
            validation_result = self.validate_video_info(video_info)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': f"视频验证失败: {validation_result['message']}"
                }
            
            # 5. 尝试下载字幕（如果启用）
            subtitle_result = None
            audio_file_path = None
            
            if self.subtitles_enabled:
                subtitle_result = self.download_subtitles(url, video_id)
                
                if subtitle_result['success']:
                    self.logger.info(f"使用字幕代替音频转录: {video_id}")
                    # 字幕下载成功，不需要下载音频进行转录
                else:
                    self.logger.info(f"字幕下载失败，回退到音频转录: {subtitle_result.get('error', '')}")
                    if subtitle_result.get('fallback_to_whisper', True):
                        # 下载音频用于Whisper转录
                        download_result = self.download_audio(url, video_id)
                        if not download_result['success']:
                            return {
                                'success': False,
                                'error': f"字幕和音频下载均失败: 字幕({subtitle_result.get('error', '')}) 音频({download_result['error']})"
                            }
                        audio_file_path = download_result['output_file']
                    else:
                        return {
                            'success': False,
                            'error': f"字幕下载失败且未启用Whisper回退: {subtitle_result.get('error', '')}"
                        }
            else:
                # 字幕功能未启用，直接下载音频
                download_result = self.download_audio(url, video_id)
                if not download_result['success']:
                    return {
                        'success': False,
                        'error': f"音频下载失败: {download_result['error']}"
                    }
                audio_file_path = download_result['output_file']
            
            # 6. 格式化元数据
            video_metadata = self.format_video_metadata(video_info)
            
            # 7. 返回成功结果
            result = {
                'success': True,
                'video_metadata': video_metadata,
                'content_type': 'youtube',
                'source_url': url,
                'processed_time': datetime.now().isoformat()
            }
            
            # 添加字幕信息（如果有）
            if subtitle_result and subtitle_result['success']:
                result.update({
                    'transcription_method': 'subtitles',
                    'subtitle_language': subtitle_result['language'],
                    'subtitle_file': subtitle_result['subtitle_file'],
                    'transcript_text': subtitle_result['subtitle_text'],
                    'subtitle_info': subtitle_result['subtitle_info']
                })
            else:
                result.update({
                    'transcription_method': 'whisper',
                    'audio_file_path': audio_file_path
                })
            
            self.logger.info(f"YouTube URL处理完成: {video_metadata['title']}")
            return result
            
        except Exception as e:
            self.logger.error(f"处理YouTube URL异常: {e}")
            return {
                'success': False,
                'error': f"处理异常: {e}"
            }


if __name__ == '__main__':
    # 测试YouTube处理器
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent.parent.parent))
    
    from src.utils.config import ConfigManager
    
    # 创建配置管理器
    config_manager = ConfigManager('./config.yaml')
    
    # 创建YouTube处理器
    processor = YouTubeProcessor(config_manager)
    
    # 测试URL
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    print(f"测试YouTube处理器")
    print(f"URL: {test_url}")
    
    # 验证URL
    is_valid = processor.validate_youtube_url(test_url)
    print(f"URL验证: {'有效' if is_valid else '无效'}")
    
    # 提取视频ID
    video_id = processor.extract_video_id(test_url)
    print(f"视频ID: {video_id}")
    
    if is_valid and video_id:
        print("开始获取视频信息...")
        # 注意：实际测试需要确保yt-dlp已安装
        # result = processor.process_youtube_url(test_url)
        # print(f"处理结果: {result['success']}")
        print("测试完成（实际下载已跳过）")