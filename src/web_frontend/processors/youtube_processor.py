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
            
            # 5. 下载音频
            download_result = self.download_audio(url, video_id)
            if not download_result['success']:
                return {
                    'success': False,
                    'error': f"音频下载失败: {download_result['error']}"
                }
            
            # 6. 格式化元数据
            video_metadata = self.format_video_metadata(video_info)
            
            # 7. 返回成功结果
            result = {
                'success': True,
                'video_metadata': video_metadata,
                'audio_file_path': download_result['output_file'],
                'content_type': 'youtube',
                'source_url': url,
                'processed_time': datetime.now().isoformat()
            }
            
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