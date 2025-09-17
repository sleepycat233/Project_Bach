#!/usr/bin/env python3
"""
音频上传处理器

处理Web界面上传的音频文件
"""

import os
import uuid
import logging
from pathlib import Path
from werkzeug.utils import secure_filename
from ..core.processing_service import ProcessingTracker, ProcessingStage

logger = logging.getLogger(__name__)


class AudioUploadHandler:
    """音频上传Web处理器"""
    
    def __init__(self, config_manager=None):
        """初始化音频上传处理器"""
        if config_manager is None:
            raise ValueError("AudioUploadHandler requires a valid config_manager")
        self.config_manager = config_manager
    
    
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
                
                # 使用配置文件中的watch_folder作为上传目录，文件监控系统会自动处理
                if self.config_manager:
                    watch_folder = self.config_manager.get_nested_config('paths', 'watch_folder') or "./data/uploads"
                else:
                    watch_folder = "./data/uploads"  # fallback
                uploads_folder = Path(watch_folder)
                uploads_folder.mkdir(parents=True, exist_ok=True)
                
                # 文件组织逻辑：根据content_type和subcategory创建目录结构
                target_folder = uploads_folder
                
                # 获取配置中的subcategories
                subcategories = []
                # 注：content_classification.content_types已迁移到PreferencesManager
                # 此处保留空的subcategories列表作为fallback
                
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
                # 移除了'other'的特殊处理，现在所有subcategory都直接使用值
                
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
                
                # 调用真正的AudioProcessor进行完整处理
                from ..core.dependency_container import DependencyContainer
                from ..core.processing_service import get_processing_service
                
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
        """获取支持的音频格式 - 从配置文件读取"""
        upload_config = self.config_manager.get_nested_config('web_frontend', 'upload') or {}
        supported_formats_list = upload_config.get('supported_formats') or ['.mp3', '.wav', '.m4a', '.mp4', '.flac', '.aac', '.ogg', '.wma']
        
        # 生成格式名称映射
        format_names = {
            '.mp3': 'MP3 Audio',
            '.wav': 'WAV Audio', 
            '.m4a': 'M4A Audio',
            '.mp4': 'MP4 Audio',
            '.flac': 'FLAC Audio',
            '.aac': 'AAC Audio',
            '.ogg': 'OGG Audio',
            '.wma': 'WMA Audio'
        }
        
        return {fmt: format_names.get(fmt, f'{fmt.upper()} Audio') for fmt in supported_formats_list}
    
    def is_supported_format(self, filename):
        """检查文件是否为支持的音频格式"""
        if not filename:
            return False
        
        file_ext = Path(filename).suffix.lower()
        
        # 复用get_supported_formats的逻辑，获取支持的格式列表
        supported_formats = self.get_supported_formats()
        return file_ext in supported_formats.keys()
