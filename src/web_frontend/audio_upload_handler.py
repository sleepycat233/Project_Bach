#!/usr/bin/env python3
"""
音频上传处理器

处理Web界面上传的音频文件
"""

import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from werkzeug.utils import secure_filename

from ..core.processing_service import (
    ProcessingTracker,
    ProcessingStage,
    get_processing_service,
)
from ..utils.content_type_service import ContentTypeService

logger = logging.getLogger(__name__)


class AudioUploadHandler:
    """音频上传Web处理器"""

    def __init__(
        self,
        config_manager=None,
        container: Optional[object] = None,
        content_type_service: Optional[ContentTypeService] = None,
    ):
        """初始化音频上传处理器"""
        if config_manager is None:
            raise ValueError("AudioUploadHandler requires a valid config_manager")
        self.config_manager = config_manager
        self.container = container
        self.content_type_service = content_type_service

        if self.content_type_service is None and self.container is not None:
            try:
                self.content_type_service = self.container.get_content_type_service()
            except AttributeError:
                logger.debug("Dependency container does not expose content type service yet")

        if self.content_type_service is None:
            self.content_type_service = ContentTypeService(self.config_manager)

    @staticmethod
    def _to_bool(value) -> bool:
        """宽松地将任意输入转换为布尔值"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in ('1', 'true', 'yes', 'on')
        if isinstance(value, (int, float)):
            return value != 0
        return bool(value)

    def _get_post_processing_defaults(self, content_type: str, subcategory: Optional[str]) -> dict:
        """从PreferencesManager载入Post-Processing默认值"""
        defaults = {
            'enable_anonymization': False,
            'enable_summary': False,
            'enable_mindmap': False,
            'enable_diarization': False,
        }

        if not self.content_type_service:
            return defaults

        try:
            effective = self.content_type_service.get_effective_config(
                content_type,
                subcategory or None,
            ) or {}
        except Exception as error:  # pragma: no cover - 防御性日志
            logger.warning(
                "Unable to load effective config for %s/%s: %s",
                content_type,
                subcategory,
                error,
            )
            return defaults

        defaults['enable_anonymization'] = self._to_bool(
            effective.get('enable_anonymization', defaults['enable_anonymization'])
        )
        defaults['enable_summary'] = self._to_bool(
            effective.get('enable_summary', defaults['enable_summary'])
        )
        defaults['enable_mindmap'] = self._to_bool(
            effective.get('enable_mindmap', defaults['enable_mindmap'])
        )
        defaults['enable_diarization'] = self._to_bool(
            effective.get('diarization', defaults['enable_diarization'])
        )
        return defaults

    def _normalize_metadata(self, metadata: Optional[dict]) -> dict:
        """整理上传时传入的metadata，提取Post-Processing覆盖值"""
        if not metadata:
            return {}

        normalized = dict(metadata)

        # 拍平成post_processing字段
        post_processing = normalized.pop('post_processing', None)
        if isinstance(post_processing, dict):
            normalized.update(post_processing)

        for key in (
            'enable_anonymization',
            'enable_summary',
            'enable_mindmap',
            'enable_diarization',
        ):
            if key in normalized:
                normalized[key] = self._to_bool(normalized[key])

        return normalized

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

        # 合并Post-Processing默认值
        processing_config.update(
            self._get_post_processing_defaults(content_type, subcategory)
        )

        overrides = self._normalize_metadata(metadata)
        if overrides:
            processing_config.update(overrides)

        # 保持兼容的字段
        processing_config['post_processing'] = {
            'enable_anonymization': processing_config.get('enable_anonymization', False),
            'enable_summary': processing_config.get('enable_summary', False),
            'enable_mindmap': processing_config.get('enable_mindmap', False),
            'enable_diarization': processing_config.get('enable_diarization', False),
        }

        # 合并用户提供的metadata（处理参数和用户输入）
        if metadata:
            # 已经合并overrides，此处确保其余字段也被保留
            for key, value in metadata.items():
                if key not in processing_config:
                    processing_config[key] = value

        # ProcessingTracker使用完整配置
        tracker_metadata = processing_config.copy()

        processing_service = get_processing_service()

        with ProcessingTracker('audio', privacy_level, tracker_metadata) as tracker:
            try:
                tracker.update_stage(ProcessingStage.UPLOADED, 5, f"Uploading file: {filename}")

                # 使用配置文件中的watch_folder作为上传目录，文件监控系统会自动处理
                if self.config_manager and hasattr(self.config_manager, 'get'):
                    watch_folder = self.config_manager.get('paths.watch_folder', default="./data/uploads")
                else:
                    watch_folder = "./data/uploads"  # fallback
                uploads_folder = Path(watch_folder)
                uploads_folder.mkdir(parents=True, exist_ok=True)

                # 文件组织逻辑：根据content_type和subcategory创建目录结构
                target_folder = uploads_folder

                # 获取配置中的subcategories
                subcategories = []
                if self.content_type_service:
                    try:
                        subcategories = [
                            entry['value']
                            for entry in self.content_type_service.get_subcategories(content_type)
                        ]
                    except Exception as lookup_error:
                        logger.warning(
                            "Failed to load subcategories for %s: %s",
                            content_type,
                            lookup_error,
                        )

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

                normalized_path = str(target_file.resolve())

                if self.container:
                    # CLI整合模式：将处理委托给已运行的FileMonitor
                    file_monitor = self.container.get_file_monitor()

                    file_monitor.register_metadata(normalized_path, {
                        'processing_config': processing_config,
                        'privacy_level': privacy_level,
                        'processing_id': tracker.processing_id,
                        'source': 'web_upload',
                        'uploaded_time': datetime.utcnow().isoformat() + 'Z'
                    })

                    queue_metadata = {
                        'processing_id': tracker.processing_id,
                        'privacy_level': privacy_level,
                        'source': 'web_upload',
                        'uploaded_time': datetime.utcnow().isoformat() + 'Z'
                    }

                    if file_monitor.enqueue_file_for_processing(normalized_path, queue_metadata):
                        processing_service.add_log(
                            tracker.processing_id,
                            f"Queued for FileMonitor processing: {target_filename}",
                            'info',
                        )

                        tracker.update_stage(
                            ProcessingStage.UPLOADED,
                            20,
                            "Waiting for background processor",
                        )

                        return {
                            'status': 'success',
                            'processing_id': tracker.processing_id,
                            'message': 'Audio file queued for background processing by FileMonitor.',
                            'estimated_time': '15-25 seconds'
                        }

                    logger.warning(
                        "Failed to enqueue file via FileMonitor (will rely on watch folder detection): %s",
                        target_file,
                    )

                # 如果无法直接排队，返回上传成功，由后台watch folder检测
                processing_service.add_log(
                    tracker.processing_id,
                    'Upload completed; waiting for watch-folder processor to pick up the file.',
                    'info',
                )

                return {
                    'status': 'success',
                    'processing_id': tracker.processing_id,
                    'message': 'Audio file uploaded successfully. Awaiting watch-folder processing...',
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
        upload_settings = self.config_manager.get_upload_settings() if self.config_manager else None
        supported_formats_list = list(upload_settings.supported_formats) if upload_settings else ['.mp3', '.wav', '.m4a', '.mp4', '.flac', '.aac', '.ogg', '.wma']

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
