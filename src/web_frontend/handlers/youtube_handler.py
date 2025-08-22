#!/usr/bin/env python3
"""
YouTube URL处理器

处理Web界面提交的YouTube URL，集成现有的YouTubeProcessor
"""

import uuid
import logging
from urllib.parse import urlparse, parse_qs
from ...core.processing_service import ProcessingTracker, ProcessingStage

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
                from ..processors.youtube_processor import YouTubeProcessor
                self.youtube_processor = YouTubeProcessor(self.config_manager)
            else:
                logger.warning("No config manager provided, using simulation mode")
                self.youtube_processor = None
        except (ImportError, Exception) as e:
            logger.warning(f"YouTubeProcessor not available: {e}")
            self.youtube_processor = None
    
    def process_url(self, url, content_type='youtube', metadata=None, privacy_level='public'):
        """
        处理YouTube URL
        
        Args:
            url: YouTube视频URL
            content_type: 内容类型
            metadata: 额外元数据
            privacy_level: 隐私级别 ('public' 或 'private')
            
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
                tracker.update_stage(ProcessingStage.TRANSCRIBING, 10, "正在下载和提取YouTube字幕")
                
                # 使用YouTubeProcessor + AudioProcessor完整处理流程
                if self.youtube_processor:
                    logger.info(f"处理YouTube视频: {url} (隐私级别: {privacy_level})")
                    result = self.youtube_processor.process_youtube_url(url)
                    
                    if result.get('success'):
                        tracker.update_stage(ProcessingStage.AI_GENERATING, 50, "YouTube内容提取完成，开始AI内容生成")
                        
                        # 集成AudioProcessor进行AI内容生成
                        from ...core.dependency_container import DependencyContainer
                        container = DependencyContainer(self.config_manager)
                        audio_processor = container.get_audio_processor()
                        
                        # 调用完整的YouTube内容处理
                        success = audio_processor.process_youtube_content(
                            youtube_result=result,
                            privacy_level=privacy_level
                        )
                        
                        if success:
                            video_metadata = result.get('video_metadata', {})
                            
                            # 生成结果URL
                            if privacy_level == 'public':
                                result_url = f"https://sleepycat233.github.io/Project_Bach/youtube_{video_id}_result.html"
                            else:
                                result_url = f"/private/youtube_{video_id}_result.html"
                            
                            tracker.set_completed(result_url)
                            
                            return {
                                'status': 'success',
                                'processing_id': tracker.processing_id,
                                'video_id': video_id,
                                'video_title': video_metadata.get('title', 'Unknown Title'),
                                'estimated_time': self.estimate_processing_time(video_metadata.get('duration', 0)),
                                'privacy_level': privacy_level,
                                'result_url': result_url,
                                'message': f'YouTube video processed and AI analysis completed ({"Private" if privacy_level == "private" else "Public"})'
                            }
                        else:
                            tracker.set_error('AI content generation failed')
                            return {
                                'status': 'error',
                                'message': 'AI content generation failed'
                            }
                    else:
                        error_msg = result.get('error', 'YouTube processing failed')
                        tracker.set_error(error_msg)
                        return {
                            'status': 'error',
                            'message': error_msg
                        }
                else:
                    # 模拟处理（当processor不可用时）
                    logger.info(f"Simulating YouTube processing for {url}")
                    
                    tracker.update_stage(ProcessingStage.AI_GENERATING, 80, "模拟AI内容生成")
                    tracker.set_completed()
                    
                    return {
                        'status': 'success',
                        'processing_id': tracker.processing_id,
                        'video_id': video_id,
                        'video_title': 'Test Video Title',
                        'estimated_time': 600,
                        'message': 'YouTube video queued (simulation mode)'
                    }
                    
            except Exception as e:
                error_msg = f'YouTube processing failed: {str(e)}'
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
            
            return parsed.netloc in youtube_domains
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