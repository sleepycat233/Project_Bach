#!/usr/bin/env python3
"""
音频上传处理器

处理Web界面上传的音频文件，集成现有的AudioUploadProcessor
"""

import os
import uuid
import logging
from pathlib import Path
from werkzeug.utils import secure_filename
try:
    from ...core.processing_service import ProcessingTracker, ProcessingStage
except ImportError:
    # Fallback for testing environment
    try:
        from core.processing_service import ProcessingTracker, ProcessingStage
    except ImportError:
        # Create mock classes for testing
        class ProcessingTracker:
            def __init__(self, type_name, privacy_level, metadata):
                self.processing_id = "test_id"
                self.metadata = metadata
            
            def __enter__(self):
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
                
            def update_stage(self, stage, progress, message):
                pass
                
            def set_error(self, message):
                pass
                
            def set_completed(self, result_url):
                pass
        
        class ProcessingStage:
            UPLOADED = "uploaded"

logger = logging.getLogger(__name__)


class AudioUploadHandler:
    """音频上传Web处理器"""
    
    def __init__(self, config_manager=None):
        """初始化音频上传处理器"""
        self.config_manager = config_manager
        self.upload_processor = None
        self._init_processor()
    
    def _init_processor(self):
        """初始化AudioUploadProcessor"""
        try:
            if self.config_manager:
                from ..processors.audio_upload_processor import AudioUploadProcessor
                self.upload_processor = AudioUploadProcessor(self.config_manager)
            else:
                logger.warning("No config manager provided, using simulation mode")
                self.upload_processor = None
        except (ImportError, Exception) as e:
            logger.warning(f"AudioUploadProcessor not available: {e}")
            self.upload_processor = None
    
    def process_upload(self, file, content_type: str, subcategory: str = None,
                       privacy_level: str = 'private', metadata: dict = None):
        """
        处理文件上传
        
        Args:
            file: Werkzeug FileStorage对象
            content_type: 内容类型 ('meeting', 'lecture'等) - 核心业务分类
            subcategory: 子分类 ('client_call', 'standup'等) - 细分业务场景
            privacy_level: 隐私级别 ('public', 'private') - 系统级配置
            metadata: 处理元数据 (description, audio_language, whisper_model等)
            
        Returns:
            dict: 处理结果
        """
        # 安全化文件名
        filename = secure_filename(file.filename)
        if not filename:
            filename = f"upload_{uuid.uuid4().hex[:8]}.mp3"
        
        # 构建完整的处理配置，合并核心参数和用户metadata
        processing_config = {
            # 核心业务参数
            'content_type': content_type,
            'subcategory': subcategory,
            'privacy_level': privacy_level,
            
            # 系统信息
            'filename': filename,
            'file_size': file.content_length or 0,
        }
        
        # 合并用户提供的metadata（处理参数和用户输入）
        if metadata:
            processing_config.update(metadata)
        
        # ProcessingTracker使用完整配置
        tracker_metadata = processing_config.copy()
            
        with ProcessingTracker('audio', privacy_level, tracker_metadata) as tracker:
            try:
                tracker.update_stage(ProcessingStage.UPLOADED, 5, f"Uploading file: {filename}")
                
                # 直接保存到data/uploads目录的正确子目录，文件监控系统会自动处理
                uploads_folder = Path("./data/uploads")
                uploads_folder.mkdir(parents=True, exist_ok=True)
                
                # 文件组织逻辑：根据content_type和subcategory创建目录结构
                target_folder = uploads_folder
                
                # 获取配置中的subcategories
                subcategories = []
                if metadata and self.config_manager:
                    content_types = self.config_manager.get_nested_config('content_classification', 'content_types') or {}
                    type_config = content_types.get(content_type, {})
                    subcategories = type_config.get('subcategories', [])
                
                # 确定目标文件夹和子分类代码
                subcategory = metadata.get('subcategory', '') if metadata else ''
                subcategory_code = ""
                
                if subcategory and subcategory != 'other':
                    if subcategory in subcategories:
                        # 有效的预定义子分类，创建子文件夹
                        target_folder = uploads_folder / subcategory
                        target_folder.mkdir(parents=True, exist_ok=True)
                        subcategory_code = f"_{subcategory}"
                        logger.info(f"Created subcategory folder for {subcategory}: {target_folder}")
                    else:
                        # 自定义子分类，添加到文件名但保持在根目录
                        subcategory_code = f"_{subcategory}"
                        logger.info(f"Using custom subcategory in filename: {subcategory}")
                elif subcategory == 'other':
                    # 处理'other'情况下的custom_subcategory
                    custom_subcategory = metadata.get('custom_subcategory', '') if metadata else ''
                    if custom_subcategory:
                        subcategory_code = f"_{custom_subcategory}"
                        logger.info(f"Using custom subcategory in filename: {custom_subcategory}")
                
                # 生成最终文件名
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                type_prefix = content_type.upper()[:3]  # LEC, MEE, OTH
                safe_filename = secure_filename(file.filename)
                
                target_filename = f"{timestamp}{subcategory_code}_{type_prefix}_{safe_filename}"
                target_file = target_folder / target_filename
                
                # 如果目标文件已存在，添加计数器
                counter = 1
                while target_file.exists():
                    name_stem = f"{timestamp}{subcategory_code}_{type_prefix}_{Path(safe_filename).stem}_{counter}"
                    target_file = target_folder / f"{name_stem}{Path(safe_filename).suffix}"
                    counter += 1
                
                # 直接保存文件到最终位置
                file.save(str(target_file))
                tracker.update_stage(ProcessingStage.UPLOADED, 15, f"File saved to organized directory: {target_file}")
                
                # 验证文件大小
                file_size = target_file.stat().st_size
                if file_size > 500 * 1024 * 1024:  # 500MB限制
                    target_file.unlink()
                    tracker.set_error('File size exceeds 500MB limit')
                    return {
                        'status': 'error',
                        'message': 'File size exceeds 500MB limit'
                    }
                
                # 调用真正的AudioProcessor进行完整处理
                try:
                    from ...core.dependency_container import DependencyContainer
                    from ...core.processing_service import get_processing_service
                except ImportError:
                    try:
                        from core.dependency_container import DependencyContainer
                        from core.processing_service import get_processing_service
                    except ImportError:
                        # Mock for testing
                        class DependencyContainer:
                            def __init__(self, config_manager):
                                pass
                            def get_audio_processor(self):
                                return MockAudioProcessor()
                        def get_processing_service():
                            return MockProcessingService()
                
                class MockAudioProcessor:
                    def process_audio_file(self, file_path, **kwargs):
                        return True
                
                class MockProcessingService:
                    def add_log(self, processing_id, message, level):
                        pass
                
                # 获取完整的音频处理器
                container = DependencyContainer(self.config_manager)
                audio_processor = container.get_configured_audio_processor()
                processing_service = get_processing_service()
                
                # 使用processing_service更新状态跟踪
                processing_service.add_log(tracker.processing_id, f"Starting complete audio processing: {filename}", 'info')
                
                # 立即返回处理ID，后台异步处理
                processing_service.add_log(tracker.processing_id, f"File uploaded, starting background processing: {target_filename}", 'info')
                
                # 启动后台异步处理
                import threading
                def background_process():
                    try:
                        # 调用AudioProcessor，传递完整的处理配置
                        # processing_config已经包含了所有必要信息
                        success = audio_processor.process_audio_file(
                            str(target_file),
                            privacy_level=privacy_level,
                            metadata=processing_config,  # 传递完整配置
                            processing_id=tracker.processing_id
                        )
                        
                        if success:
                            # 生成结果URL
                            file_stem = target_file.stem
                            if privacy_level == 'public':
                                result_url = f"https://sleepycat233.github.io/Project_Bach/{file_stem}_result.html"
                            else:
                                result_url = f"/private/{file_stem}_result.html"
                            
                            processing_service.add_log(tracker.processing_id, f"Audio processing completed, result: {result_url}", 'success')
                            tracker.set_completed(result_url)
                        else:
                            error_msg = 'Complete audio processing failed'
                            processing_service.add_log(tracker.processing_id, error_msg, 'error')
                            tracker.set_error(error_msg)
                            
                    except Exception as proc_e:
                        error_msg = f'Audio processing exception: {str(proc_e)}'
                        processing_service.add_log(tracker.processing_id, error_msg, 'error')
                        tracker.set_error(error_msg)
                        logger.error(f"Background audio processing error: {proc_e}")
                
                # 启动后台线程
                thread = threading.Thread(target=background_process, daemon=True)
                thread.start()
                
                # 立即返回成功状态，用户可以查看处理进度
                return {
                    'status': 'success',
                    'processing_id': tracker.processing_id,
                    'message': f'Audio file uploaded successfully. Processing in background...',
                    'estimated_time': '15-25 seconds'
                }
                    
            except Exception as e:
                error_msg = f'Upload processing failed: {str(e)}'
                tracker.set_error(error_msg)
                logger.error(f"Audio upload processing error: {e}")
                
                # 确保清理临时文件
                try:
                    if 'temp_file_path' in locals() and temp_file_path.exists():
                        temp_file_path.unlink()
                except:
                    pass
                
                return {
                    'status': 'error',
                    'message': error_msg
                }
    
    def validate_file(self, file, allowed_extensions):
        """
        验证上传文件
        
        Args:
            file: Werkzeug FileStorage对象
            allowed_extensions: 允许的文件扩展名集合
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if not file or not file.filename:
            return False, "No file provided"
        
        # 检查文件扩展名
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in allowed_extensions:
            return False, f"File type {file_ext} not allowed"
        
        return True, None
    
    def get_supported_formats(self):
        """获取支持的音频格式"""
        return {
            '.mp3': 'MP3 Audio',
            '.wav': 'WAV Audio', 
            '.m4a': 'M4A Audio',
            '.mp4': 'MP4 Audio',
            '.flac': 'FLAC Audio',
            '.aac': 'AAC Audio',
            '.ogg': 'OGG Audio'
        }