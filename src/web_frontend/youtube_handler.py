#!/usr/bin/env python3
"""
YouTube URL处理器

处理Web界面提交的YouTube URL，集成现有的YouTubeProcessor
"""

import uuid
import logging
from urllib.parse import urlparse, parse_qs
from ..core.processing_service import ProcessingTracker, ProcessingStage
from ..core.audio_processor import AudioProcessor

logger = logging.getLogger(__name__)


class YouTubeHandler:
    """YouTube URL Web处理器"""
    
    def __init__(self, config_manager=None):
        """初始化YouTube处理器"""
        self.config_manager = config_manager
        self.youtube_processor = None
        self._init_processor()
    
    def _init_processor(self):
        """初始化YouTubeProcessor"""
        try:
            if self.config_manager:
                from .youtube_processor import YouTubeProcessor
                self.youtube_processor = YouTubeProcessor(self.config_manager)
            else:
                logger.warning("No config manager provided, using simulation mode")
                self.youtube_processor = None
        except (ImportError, Exception) as e:
            logger.warning(f"YouTubeProcessor not available: {e}")
            self.youtube_processor = None
    
    def process_url(self, url, content_type='youtube', metadata=None, privacy_level='public', force_whisper=False):
        """
        处理YouTube URL
        
        Args:
            url: YouTube视频URL
            content_type: 内容类型
            metadata: 额外元数据
            privacy_level: 隐私级别 ('public' 或 'private')
            force_whisper: 是否强制使用Whisper转录（即使有手动字幕）
            
        Returns:
            dict: 处理结果
        """
        # 验证YouTube URL
        if not self.is_valid_youtube_url(url):
            return {
                'status': 'error',
                'message': 'Invalid YouTube URL format'
            }
        
        # 提取视频ID
        video_id = self.extract_video_id(url)
        if not video_id:
            return {
                'status': 'error', 
                'message': 'Could not extract video ID from URL'
            }
        
        # 使用ProcessingTracker跟踪处理状态
        tracker_metadata = {
            'url': url,
            'video_id': video_id,
            'content_type': content_type
        }
        if metadata:
            tracker_metadata.update(metadata)
            
        with ProcessingTracker('youtube', privacy_level, tracker_metadata) as tracker:
            try:
                # 获取processing service用于日志记录
                try:
                    from ..core.processing_service import get_processing_service
                    processing_service = get_processing_service()
                except ImportError:
                    processing_service = None
                
                tracker.update_stage(ProcessingStage.TRANSCRIBING, 10, "Downloading and extracting YouTube subtitles")
                
                if processing_service:
                    processing_service.add_log(tracker.processing_id, f"Processing YouTube video: {url} (Privacy level: {privacy_level})", 'info')
                
                # 启动后台异步处理
                import threading
                def background_process():
                    try:
                        # 使用YouTubeProcessor + AudioProcessor完整处理流程
                        if self.youtube_processor:
                            logger.info(f"Processing YouTube video: {url} (Privacy level: {privacy_level})")
                            result = self.youtube_processor.process_youtube_url(url, force_whisper)
                            
                            if result.get('success'):
                                tracker.update_stage(ProcessingStage.AI_GENERATING, 50, "YouTube content extracted, starting AI content generation")
                                
                                # 添加upload_metadata到result中，供AudioProcessor使用
                                if metadata:
                                    result['upload_metadata'] = metadata
                                    # 确保content_type包含在metadata中
                                    result['upload_metadata']['content_type'] = content_type
                                else:
                                    # 即使没有metadata，也要设置基本的upload_metadata
                                    result['upload_metadata'] = {'content_type': content_type}
                                
                                # 集成AudioProcessor进行AI内容生成
                                from ..core.dependency_container import DependencyContainer
                                container = DependencyContainer(self.config_manager)
                                audio_processor = container.get_configured_audio_processor()
                                
                                # 调用完整的YouTube内容处理
                                success = audio_processor.process_youtube_content(
                                    youtube_result=result,
                                    privacy_level=privacy_level
                                )
                                
                                if success:
                                    video_metadata = result.get('video_metadata', {})

                                    # 生成结果URL
                                    result_url = AudioProcessor.build_result_url(
                                        self.config_manager,
                                        f"youtube_{video_id}",
                                        privacy_level,
                                    )
                                    
                                    if processing_service:
                                        processing_service.add_log(tracker.processing_id, f"YouTube processing completed, result: {result_url}", 'success')
                                    tracker.set_completed(result_url)
                                else:
                                    error_msg = 'YouTube processing failed during AI content generation'
                                    if processing_service:
                                        processing_service.add_log(tracker.processing_id, error_msg, 'error')
                                    tracker.set_error(error_msg)
                            else:
                                error_msg = f'YouTube URL processing failed: {result.get("error", "Unknown error")}'
                                if processing_service:
                                    processing_service.add_log(tracker.processing_id, error_msg, 'error')
                                tracker.set_error(error_msg)
                        else:
                            # 模拟处理（当processor不可用时）
                            logger.info(f"Simulating YouTube processing for {url}")
                            tracker.update_stage(ProcessingStage.AI_GENERATING, 80, "Simulating AI content generation")
                            
                            # 模拟处理时间
                            import time
                            time.sleep(2)
                            
                            result_url = AudioProcessor.build_result_url(
                                self.config_manager,
                                f"youtube_{video_id}",
                                privacy_level,
                            )
                            if processing_service:
                                processing_service.add_log(tracker.processing_id, f"Mock YouTube processing completed, result: {result_url}", 'success')
                            tracker.set_completed(result_url)
                            
                    except Exception as proc_e:
                        error_msg = f'YouTube processing exception: {str(proc_e)}'
                        if processing_service:
                            processing_service.add_log(tracker.processing_id, error_msg, 'error')
                        tracker.set_error(error_msg)
                        logger.error(f"Background YouTube processing error: {proc_e}")
                
                # 启动后台线程
                thread = threading.Thread(target=background_process, daemon=True)
                thread.start()
                
                # 立即返回成功状态，用户可以查看处理进度
                return {
                    'status': 'success',
                    'processing_id': tracker.processing_id,
                    'video_id': video_id,
                    'estimated_time': 30,
                    'privacy_level': privacy_level,
                    'message': f'YouTube video added to processing queue ({"Private" if privacy_level == "private" else "Public"})'
                }
                    
            except Exception as e:
                error_msg = f'YouTube processing failed: {str(e)}'
                if processing_service:
                    processing_service.add_log(tracker.processing_id, error_msg, 'error')
                tracker.set_error(error_msg)
                logger.error(f"YouTube URL processing error: {e}")
                return {
                    'status': 'error',
                    'message': error_msg
                }
    
    def is_valid_youtube_url(self, url):
        """
        验证YouTube URL格式
        
        Args:
            url: 要验证的URL
            
        Returns:
            bool: 是否为有效的YouTube URL
        """
        try:
            parsed = urlparse(url)
            
            # 支持的YouTube域名
            youtube_domains = [
                'www.youtube.com',
                'youtube.com',
                'youtu.be',
                'm.youtube.com',
                'youtube-nocookie.com'
            ]
            
            # 检查域名
            if parsed.netloc not in youtube_domains:
                return False
            
            # 检查是否包含有效的视频ID
            video_id = self.extract_video_id(url)
            return video_id is not None and len(video_id) > 0
            
        except:
            return False
    
    def extract_video_id(self, url):
        """
        从YouTube URL提取视频ID
        
        Args:
            url: YouTube URL
            
        Returns:
            str: 视频ID，如果提取失败返回None
        """
        try:
            parsed = urlparse(url)
            
            # 处理不同格式的YouTube URL
            if parsed.netloc == 'youtu.be':
                # https://youtu.be/VIDEO_ID
                return parsed.path[1:]  # 移除开头的'/'
            elif 'youtube.com' in parsed.netloc:
                # https://www.youtube.com/watch?v=VIDEO_ID
                query_params = parse_qs(parsed.query)
                if 'v' in query_params:
                    return query_params['v'][0]
            
            return None
        except:
            return None
    
    def get_video_info(self, url):
        """
        获取YouTube视频基本信息（如果可用）
        
        Args:
            url: YouTube URL
            
        Returns:
            dict: 视频信息
        """
        try:
            video_id = self.extract_video_id(url)
            if not video_id:
                return None
            
            if self.youtube_processor:
                return self.youtube_processor.get_video_info(url)
            else:
                # 返回模拟信息
                return {
                    'video_id': video_id,
                    'title': 'Video Title (Preview)',
                    'duration': 'Unknown',
                    'channel': 'Unknown Channel'
                }
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return None
    
    def get_video_metadata(self, url):
        """
        获取YouTube视频元数据（标题、描述等）用于转录context
        
        Args:
            url: YouTube URL
            
        Returns:
            dict: 视频元数据，包含title, description, duration, uploader, tags
        """
        try:
            video_id = self.extract_video_id(url)
            if not video_id:
                return None
            
            # 超快速元数据获取：使用最优化的yt-dlp调用
            try:
                import subprocess
                import json
                
                # 获取配置中的超时设置 - 增加超时时间以处理网络延迟
                timeout = 25  # 默认25秒，处理网络波动和复杂视频
                if self.config_manager:
                    try:
                        youtube_config = self.config_manager.get_nested_config('youtube')
                        if youtube_config and 'metadata' in youtube_config:
                            timeout = youtube_config['metadata'].get('quick_metadata_timeout', 15)
                    except:
                        pass
                
                # 最优化的yt-dlp调用 - 只获取必需信息，无额外检查
                cmd = [
                    'yt-dlp', 
                    '--dump-json', 
                    '--no-download',
                    '--no-warnings',
                    '--quiet',
                    '--no-check-certificate',
                    '--extractor-retries', '1',  # 减少重试
                    '--fragment-retries', '1',   # 减少片段重试  
                    url
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
                
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    video_info_line = lines[0] if lines else ''
                    
                    if video_info_line.strip():
                        video_info = json.loads(video_info_line)
                        
                        # 最小化的元数据，减少处理时间
                        metadata = {
                            'title': video_info.get('title', ''),
                            'description': video_info.get('description', '')[:2000] if video_info.get('description') else '',  # 增加到2000字符，保留完整描述
                            'duration': video_info.get('duration', ''),
                            'uploader': video_info.get('uploader', ''),
                            'tags': video_info.get('tags', [])[:10] if video_info.get('tags') else []  # 恢复到10个标签
                        }
                        
                        # 字幕检测 - 直接从已获取的video_info中提取
                        subtitle_info = self.subtitle_detection(video_info)
                        metadata['subtitle_info'] = subtitle_info
                        
                        return metadata
                        
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, json.JSONDecodeError) as e:
                logger.warning(f"Ultra-fast metadata retrieval failed: {e}")
                # 不返回None，继续执行到fallback逻辑
            
            # 如果超快速方法失败，直接返回基本模拟数据，避免延迟
            logger.info(f"Returning fallback metadata for video: {video_id}")
            return {
                'title': f'YouTube Video {video_id}',
                'description': 'Metadata temporarily unavailable - will be processed during transcription',
                'duration': 'Unknown',
                'uploader': 'Unknown',
                'tags': [],
                'subtitle_info': {
                    'available': False,
                    'subtitles': {},
                    'auto_captions': {},
                    'total_languages': 0,
                    'fallback_to_transcription': True
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting video metadata: {e}")
            # 即使发生异常也返回fallback数据，确保API不返回None
            video_id = self.extract_video_id(url) if url else "unknown"
            return {
                'title': f'YouTube Video {video_id}',
                'description': 'Metadata temporarily unavailable - will be processed during transcription',
                'duration': 'Unknown',
                'uploader': 'Unknown', 
                'tags': [],
                'subtitle_info': {
                    'available': False,
                    'has_manual_subtitles': False,
                    'subtitles': {},
                    'auto_captions': {},
                    'available_subtitles': [],
                    'total_languages': 0,
                    'fallback_to_transcription': True
                }
            }
    
    def estimate_processing_time(self, duration_seconds):
        """
        根据视频时长估算处理时间
        
        Args:
            duration_seconds: 视频时长（秒）
            
        Returns:
            int: 估算的处理时间（秒）
        """
        if not duration_seconds:
            return 600  # 默认10分钟
        
        # 估算：下载时间 + 音频提取时间 + 转录时间
        # 假设转录速度约为实时的5倍
        base_time = 60  # 基础开销
        download_time = duration_seconds * 0.1  # 下载时间约为视频时长的10%
        transcription_time = duration_seconds * 0.2  # 转录时间约为视频时长的20%
        
        total_time = base_time + download_time + transcription_time
        return max(int(total_time), 120)  # 最少2分钟
    
    def subtitle_detection(self, video_info):
        """超快速字幕检测 - 直接从video_info提取，无额外API调用
        
        Args:
            video_info: yt-dlp返回的视频信息字典
            
        Returns:
            dict: 字幕信息
        """
        try:
            # 获取优先语言配置
            preferred_languages = ["zh-CN", "zh", "en"]
            if self.config_manager:
                try:
                    youtube_config = self.config_manager.get_nested_config('youtube')
                    if youtube_config and 'metadata' in youtube_config:
                        preferred_languages = youtube_config['metadata'].get('preferred_subtitle_languages', preferred_languages)
                except:
                    pass
            
            subtitles = {}
            auto_captions = {}
            
            # 检查手动字幕 - 只检查优先语言
            video_subtitles = video_info.get('subtitles', {})
            for lang in preferred_languages:
                if lang in video_subtitles:
                    subtitles[lang] = video_subtitles[lang]
            
            # 检查自动字幕 - 总是检查配置的语言（用于完整性）
            video_auto_captions = video_info.get('automatic_captions', {})
            for lang in preferred_languages:
                if lang in video_auto_captions:
                    auto_captions[lang] = video_auto_captions[lang]
            
            has_subtitles = bool(subtitles)  # 只考虑手动字幕为"有字幕"
            
            return {
                'available': has_subtitles,
                'has_manual_subtitles': has_subtitles,
                'subtitles': subtitles,
                'auto_captions': auto_captions,
                'available_subtitles': list(subtitles.keys()) if subtitles else list(auto_captions.keys()),
                'total_languages': len(subtitles) + len(auto_captions),
                'ultra_quick': True  # 标记为超快速检测
            }
        except Exception as e:
            logger.warning(f"Ultra-quick subtitle detection failed: {e}")
            return {
                'available': False,
                'has_manual_subtitles': False,
                'subtitles': {},
                'auto_captions': {},
                'available_subtitles': [],
                'total_languages': 0,
                'fallback_to_transcription': True
            }
    
    def _quick_subtitle_detection(self, url, video_info):
        """快速字幕检测 - 只检测配置中的优先语言
        
        Args:
            url: YouTube URL
            video_info: 视频信息字典
            
        Returns:
            包含字幕信息的字典
        """
        try:
            # 获取配置中的优先语言
            preferred_languages = ["zh-CN", "zh", "en"]  # 默认值
            if self.config_manager:
                try:
                    youtube_config = self.config_manager.get_nested_config('youtube')
                    if youtube_config and 'metadata' in youtube_config:
                        preferred_languages = youtube_config['metadata'].get('preferred_subtitle_languages', preferred_languages)
                except:
                    pass
            
            # 从video_info中检查字幕信息（如果yt-dlp已经获取了）
            if 'subtitles' in video_info:
                subtitles = {}
                auto_captions = {}
                
                # 检查手动字幕
                video_subtitles = video_info.get('subtitles', {})
                for lang in preferred_languages:
                    if lang in video_subtitles:
                        subtitles[lang] = video_subtitles[lang]
                
                # 如果没有手动字幕，检查自动字幕
                if not subtitles and 'automatic_captions' in video_info:
                    video_auto_captions = video_info.get('automatic_captions', {})
                    for lang in preferred_languages:
                        if lang in video_auto_captions:
                            auto_captions[lang] = video_auto_captions[lang]
                
                has_subtitles = bool(subtitles or auto_captions)
                
                return {
                    'available': has_subtitles,
                    'subtitles': subtitles,
                    'auto_captions': auto_captions,
                    'total_languages': len(subtitles) + len(auto_captions),
                    'preferred_only': True  # 标记这是快速检测结果
                }
            
            # 如果video_info中没有字幕信息，跳过详细检测
            return {
                'available': False,
                'subtitles': {},
                'auto_captions': {},
                'total_languages': 0,
                'fallback_to_transcription': True  # 标记需要回退到转录
            }
            
        except Exception as e:
            logger.warning(f"快速字幕检测失败: {e}")
            return {
                'available': False,
                'subtitles': {},
                'auto_captions': {},
                'total_languages': 0,
                'fallback_to_transcription': True
            }
    
    def _parse_subtitle_output(self, output):
        """解析yt-dlp输出中的字幕信息
        
        Args:
            output: yt-dlp命令的输出
            
        Returns:
            包含字幕信息的字典
        """
        try:
            lines = output.split('\n')
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
            
        except Exception as e:
            logger.error(f"解析字幕信息异常: {e}")
            return {'available': False, 'subtitles': {}, 'auto_captions': {}, 'total_languages': 0}
    
    def _get_subtitles_via_ytdlp(self, url):
        """使用yt-dlp直接获取字幕信息
        
        Args:
            url: YouTube URL
            
        Returns:
            包含字幕信息的字典
        """
        try:
            import subprocess
            cmd = [
                'yt-dlp',
                '--list-subs',
                '--no-warnings',
                '--no-playlist',
                url
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=False
            )
            
            if result.returncode != 0:
                logger.warning(f"获取字幕信息失败: {result.stderr}")
                return {
                    'available': False,
                    'subtitles': {},
                    'auto_captions': {},
                    'total_languages': 0
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
            logger.error(f"获取字幕信息超时: {url}")
            return {'available': False, 'subtitles': {}, 'auto_captions': {}, 'total_languages': 0}
        except Exception as e:
            logger.error(f"获取字幕信息异常: {e}")
            return {'available': False, 'subtitles': {}, 'auto_captions': {}, 'total_languages': 0}
