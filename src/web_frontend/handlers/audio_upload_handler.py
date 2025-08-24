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
from ...core.processing_service import ProcessingTracker, ProcessingStage

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
    
    def process_upload(self, file, content_type, privacy_level='public', metadata=None):
        """
        处理文件上传
        
        Args:
            file: Werkzeug FileStorage对象
            content_type: 内容类型 (lecture/podcast/youtube等)
            metadata: 额外元数据
            
        Returns:
            dict: 处理结果
        """
        # 安全化文件名
        filename = secure_filename(file.filename)
        if not filename:
            filename = f"upload_{uuid.uuid4().hex[:8]}.mp3"
        
        # 使用ProcessingTracker创建状态跟踪
        tracker_metadata = {
            'filename': filename,
            'content_type': content_type,
            'file_size': file.content_length
        }
        if metadata:
            tracker_metadata.update(metadata)
            
        with ProcessingTracker('audio', privacy_level, tracker_metadata) as tracker:
            try:
                tracker.update_stage(ProcessingStage.UPLOADED, 5, f"Uploading file: {filename}")
                
                # 创建临时文件路径
                temp_dir = Path("/tmp/project_bach_uploads")
                temp_dir.mkdir(parents=True, exist_ok=True)
                temp_file_path = temp_dir / filename
                
                # 保存上传的文件
                file.save(str(temp_file_path))
                tracker.update_stage(ProcessingStage.UPLOADED, 10, f"File saved successfully: {filename}")
                
                # 验证文件大小
                file_size = temp_file_path.stat().st_size
                if file_size > 500 * 1024 * 1024:  # 500MB限制
                    temp_file_path.unlink()
                    tracker.set_error('File size exceeds 500MB limit')
                    return {
                        'status': 'error',
                        'message': 'File size exceeds 500MB limit'
                    }
                
                # 调用真正的AudioProcessor进行完整处理
                from ...core.dependency_container import DependencyContainer
                from ...core.processing_service import get_processing_service
                
                # 获取完整的音频处理器
                container = DependencyContainer(self.config_manager)
                audio_processor = container.get_audio_processor()
                processing_service = get_processing_service()
                
                # 将文件移动到watch_folder，支持课程子文件夹组织
                watch_folder = Path("./watch_folder")
                watch_folder.mkdir(parents=True, exist_ok=True)
                
                # 文件组织逻辑：
                # - 选择具体课程代码 → 创建课程子文件夹
                # - 选择"Other"(自定义) → 放在最外层
                target_folder = watch_folder
                
                if metadata:
                    subcategory = metadata.get('subcategory', '')
                    # 从config获取当前content type的子分类列表
                    subcategories = []
                    if self.config_manager:
                        content_types = self.config_manager.get_nested_config('content_classification', 'content_types') or {}
                        type_config = content_types.get(content_type, {})
                        subcategories = type_config.get('subcategories', [])
                    
                    # 如果有有效的子分类，创建子文件夹
                    if subcategory and subcategory in subcategories:
                        target_folder = watch_folder / subcategory
                        target_folder.mkdir(parents=True, exist_ok=True)
                        logger.info(f"Created subcategory folder for {subcategory}: {target_folder}")
                    # 如果是"Other"、自定义子分类，或者没有子分类，保持在最外层
                    else:
                        logger.info(f"File will be placed in root folder: {watch_folder}")
                
                # 生成带时间戳和课程代码的文件名
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                type_prefix = content_type.upper()[:3]  # LEC, POD, MEE
                safe_filename = secure_filename(file.filename)
                
                # 添加子分类代码到文件名
                subcategory_code = ""
                if metadata:
                    subcategory = metadata.get('subcategory', '')
                    # 如果有子分类，添加到文件名
                    if subcategory and subcategory != 'other':
                        subcategory_code = f"_{subcategory}"
                
                target_filename = f"{timestamp}{subcategory_code}_{type_prefix}_{safe_filename}"
                target_file = target_folder / target_filename
                
                # 如果目标文件已存在，添加计数器
                counter = 1
                while target_file.exists():
                    name_stem = f"{timestamp}{subcategory_code}_{type_prefix}_{Path(safe_filename).stem}_{counter}"
                    target_file = target_folder / f"{name_stem}{Path(safe_filename).suffix}"
                    counter += 1
                
                # 移动文件到watch目录
                import shutil
                shutil.move(str(temp_file_path), str(target_file))
                tracker.update_stage(ProcessingStage.TRANSCRIBING, 20, f"File moved to processing directory: {target_file}")
                
                # 使用processing_service更新状态跟踪
                processing_service.add_log(tracker.processing_id, f"Starting complete audio processing: {filename}", 'info')
                
                # 立即返回处理ID，后台异步处理
                processing_service.add_log(tracker.processing_id, f"File uploaded, starting background processing: {target_filename}", 'info')
                
                # 启动后台异步处理
                import threading
                def background_process():
                    try:
                        # 调用AudioProcessor的process_audio_file方法，传递完整metadata和processing_id
                        success = audio_processor.process_audio_file(
                            str(target_file),
                            privacy_level=privacy_level,
                            metadata=metadata,
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