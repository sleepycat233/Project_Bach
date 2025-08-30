#!/usr/bin/env python3
"""
Phase 6.5 音频上传处理器

支持用户手动上传音频文件并选择内容分类：
- 文件验证和格式检查
- 手动内容类型选择（lecture/podcast等）
- 集成现有音频处理流程
- 元数据提取和管理
"""

import shutil
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.utils.config import ConfigManager


class AudioUploadProcessor:
    """音频上传处理器
    
    功能：
    1. 音频文件验证和格式检查
    2. 用户手动内容类型选择
    3. 文件安全管理和存储
    4. 集成现有音频处理流程
    5. 元数据提取和格式化
    """
    
    # 支持的音频格式
    SUPPORTED_FORMATS = {'.mp3', '.wav', '.m4a', '.mp4', '.flac', '.aac', '.ogg', '.wma'}
    
    # 文件大小限制 (字节)
    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
    MIN_FILE_SIZE = 1024  # 1KB
    
    def __init__(self, config_manager: ConfigManager):
        """初始化音频上传处理器
        
        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger('project_bach.audio_upload_processor')
        
        # 加载内容分类配置
        self.content_types_config = config_manager.get_nested_config('content_classification', 'content_types')
        if not self.content_types_config:
            raise ValueError("内容分类配置缺失，请检查config.yaml中的content_classification部分")
        
        # 设置监控目录路径 (上传文件直接放到监控目录)
        paths_config = config_manager.get_paths_config()
        self.watch_dir = Path(paths_config.get('watch_folder', './data/uploads'))
        self.watch_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载音频上传配置
        upload_config = config_manager.get_nested_config('audio_upload') or {}
        self.auto_process = upload_config.get('auto_process', True)
        self.filename_sanitization = upload_config.get('filename_sanitization', True)
        
        self.logger.info("音频上传处理器初始化完成")
    
    def validate_audio_file(self, file_path: Path) -> Dict[str, Any]:
        """验证音频文件
        
        Args:
            file_path: 音频文件路径
            
        Returns:
            验证结果字典
        """
        try:
            # 检查文件是否存在
            if not file_path.exists():
                return {
                    'valid': False,
                    'error': '文件不存在'
                }
            
            # 检查是否为文件
            if not file_path.is_file():
                return {
                    'valid': False,
                    'error': '路径不是有效文件'
                }
            
            # 检查文件扩展名
            file_extension = file_path.suffix.lower()
            if file_extension not in self.SUPPORTED_FORMATS:
                return {
                    'valid': False,
                    'error': f'不支持的文件格式: {file_extension}',
                    'supported_formats': list(self.SUPPORTED_FORMATS)
                }
            
            # 检查文件大小
            file_size = file_path.stat().st_size
            if file_size > self.MAX_FILE_SIZE:
                return {
                    'valid': False,
                    'error': f'文件大小({file_size}字节)超过限制({self.MAX_FILE_SIZE}字节)'
                }
            
            if file_size < self.MIN_FILE_SIZE:
                return {
                    'valid': False,
                    'error': f'文件大小({file_size}字节)小于最小限制({self.MIN_FILE_SIZE}字节)'
                }
            
            # 获取文件信息
            file_info = {
                'size': file_size,
                'size_mb': round(file_size / (1024 * 1024), 2),
                'extension': file_extension,
                'name': file_path.name,
                'stem': file_path.stem
            }
            
            return {
                'valid': True,
                'file_info': file_info,
                'message': '文件验证通过'
            }
            
        except Exception as e:
            self.logger.error(f"文件验证异常: {e}")
            return {
                'valid': False,
                'error': f'文件验证异常: {e}'
            }
    
    def get_available_content_types(self) -> Dict[str, Dict[str, str]]:
        """获取可用的内容类型选项
        
        Returns:
            内容类型字典，包含图标、显示名称和描述
        """
        available_types = {}
        
        for content_type, config in self.content_types_config.items():
            available_types[content_type] = {
                'icon': config.get('icon', '📄'),
                'display_name': config.get('display_name', content_type),
                'description': config.get('description', ''),
                'auto_detect_available': bool(config.get('auto_detect_patterns'))
            }
        
        return available_types
    
    def sanitize_filename(self, filename: str) -> str:
        """文件名安全化处理
        
        Args:
            filename: 原始文件名
            
        Returns:
            安全化后的文件名
        """
        if not self.filename_sanitization:
            return filename
        
        # 移除或替换不安全字符
        unsafe_chars = '<>:"/\\|?*'
        safe_filename = filename
        
        for char in unsafe_chars:
            safe_filename = safe_filename.replace(char, '_')
        
        # 移除多余的空格和点
        safe_filename = safe_filename.strip('. ')
        
        # 确保文件名不为空
        if not safe_filename:
            safe_filename = f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return safe_filename
    
    def process_uploaded_file(
        self,
        source_file_path: Path,
        selected_content_type: str,
        custom_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """处理上传的音频文件
        
        Args:
            source_file_path: 源文件路径
            selected_content_type: 用户选择的内容类型
            custom_metadata: 自定义元数据
            
        Returns:
            处理结果字典
        """
        try:
            self.logger.info(f"开始处理上传文件: {source_file_path}")
            
            # 1. 验证文件
            validation_result = self.validate_audio_file(source_file_path)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': f"文件验证失败: {validation_result['error']}"
                }
            
            file_info = validation_result['file_info']
            
            # 2. 验证内容类型选择
            if selected_content_type not in self.content_types_config:
                available_types = list(self.content_types_config.keys())
                return {
                    'success': False,
                    'error': f"无效的内容类型: {selected_content_type}",
                    'available_types': available_types
                }
            
            # 3. 生成目标文件名 (日期时间前缀 + 内容类型 + 原文件名)
            safe_filename = self.sanitize_filename(source_file_path.name)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # 添加内容类型标识
            type_config = self.content_types_config[selected_content_type]
            type_prefix = selected_content_type.upper()[:3]  # LEC, POD, YOU, RSS
            
            target_filename = f"{timestamp}_{type_prefix}_{safe_filename}"
            
            # 如果有课程信息，创建课程子文件夹
            course_folder = self.watch_dir
            if custom_metadata and custom_metadata.get('lecture_series'):
                course_code = custom_metadata['lecture_series']
                course_folder = self.watch_dir / course_code
                course_folder.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"为课程 {course_code} 创建文件夹: {course_folder}")
            
            target_path = course_folder / target_filename
            
            # 确保文件名唯一
            counter = 1
            while target_path.exists():
                name_stem = target_path.stem + f"_{counter}"
                target_path = target_path.parent / f"{name_stem}{target_path.suffix}"
                counter += 1
            
            # 4. 复制文件到watch目录
            shutil.copy2(source_file_path, target_path)
            self.logger.info(f"文件已复制到: {target_path}")
            
            # 5. 创建处理元数据
            processing_metadata = {
                'source_file': str(source_file_path),
                'target_file': str(target_path),
                'selected_content_type': selected_content_type,
                'content_type_config': type_config,
                'file_info': file_info,
                'upload_time': datetime.now().isoformat(),
                'auto_process': self.auto_process,
                'processing_status': 'queued'
            }
            
            # 添加自定义元数据
            if custom_metadata:
                processing_metadata['custom_metadata'] = custom_metadata
            
            # 7. 创建分类结果（手动选择）
            classification_result = {
                'content_type': selected_content_type,
                'confidence': 1.0,  # 手动选择置信度最高
                'auto_detected': False,
                'manual_selection': True,
                'selection_source': 'user_upload',
                'tags': custom_metadata.get('tags', []) if custom_metadata else []
            }
            
            processing_metadata['classification_result'] = classification_result
            
            # 7. 返回成功结果
            result = {
                'success': True,
                'target_file_path': str(target_path),
                'processing_metadata': processing_metadata,
                'message': f"文件上传成功，类型: {type_config['display_name']}"
            }
            
            self.logger.info(f"文件处理完成: {target_filename}")
            return result
            
        except Exception as e:
            self.logger.error(f"处理上传文件异常: {e}")
            return {
                'success': False,
                'error': f"处理异常: {e}"
            }
    
    def create_upload_metadata_file(
        self,
        target_file_path: Path,
        processing_metadata: Dict[str, Any]
    ) -> Optional[Path]:
        """创建上传元数据文件
        
        Args:
            target_file_path: 目标音频文件路径
            processing_metadata: 处理元数据
            
        Returns:
            元数据文件路径或None
        """
        try:
            import json
            
            metadata_filename = target_file_path.stem + '_upload_metadata.json'
            metadata_path = target_file_path.parent / metadata_filename
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(processing_metadata, f, ensure_ascii=False, indent=2)
            
            self.logger.debug(f"上传元数据已保存: {metadata_path}")
            return metadata_path
            
        except Exception as e:
            self.logger.warning(f"保存上传元数据失败: {e}")
            return None
    
    def get_upload_statistics(self) -> Dict[str, Any]:
        """获取上传统计信息
        
        Returns:
            统计信息字典
        """
        try:
            # 统计watch目录中的文件
            watch_files = list(self.watch_dir.glob('*'))
            audio_files = [f for f in watch_files if f.suffix.lower() in self.SUPPORTED_FORMATS]
            
            # 统计watch目录中的文件
            
            return {
                'total_audio_files': len(audio_files),
                'watch_directory': str(self.watch_dir),
                'supported_formats': list(self.SUPPORTED_FORMATS),
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"获取上传统计信息异常: {e}")
            return {
                'error': f"统计信息获取失败: {e}",
                'last_updated': datetime.now().isoformat()
            }
    
    def cleanup_old_files(self, days_to_keep: int = 30) -> Dict[str, Any]:
        """清理旧的上传文件
        
        Args:
            days_to_keep: 保留天数
            
        Returns:
            清理结果字典
        """
        try:
            from datetime import timedelta
            
            cutoff_time = datetime.now() - timedelta(days=days_to_keep)
            cutoff_timestamp = cutoff_time.timestamp()
            
            cleaned_files = []
            total_cleaned_size = 0
            
            # 清理upload目录中的旧文件
            for file_path in self.watch_dir.iterdir():
                if file_path.is_file():
                    file_stat = file_path.stat()
                    if file_stat.st_mtime < cutoff_timestamp:
                        file_size = file_stat.st_size
                        try:
                            file_path.unlink()
                            cleaned_files.append({
                                'path': str(file_path),
                                'size': file_size,
                                'modified_time': datetime.fromtimestamp(file_stat.st_mtime).isoformat()
                            })
                            total_cleaned_size += file_size
                            self.logger.debug(f"清理旧文件: {file_path}")
                        except Exception as e:
                            self.logger.warning(f"清理文件失败 {file_path}: {e}")
            
            return {
                'success': True,
                'cleaned_files_count': len(cleaned_files),
                'total_cleaned_size': total_cleaned_size,
                'total_cleaned_size_mb': round(total_cleaned_size / (1024 * 1024), 2),
                'cleaned_files': cleaned_files,
                'cutoff_date': cutoff_time.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"清理旧文件异常: {e}")
            return {
                'success': False,
                'error': f"清理异常: {e}"
            }
    
    def process_file(self, file_path: str, content_type: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Web界面兼容方法 - 处理音频文件
        
        Args:
            file_path: 音频文件路径
            content_type: 内容类型
            metadata: 元数据
            
        Returns:
            处理结果字典
        """
        return self.process_uploaded_file(
            source_file_path=Path(file_path),
            selected_content_type=content_type,
            custom_metadata=metadata
        )


if __name__ == '__main__':
    # 测试音频上传处理器
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent.parent.parent))
    
    from src.utils.config import ConfigManager
    
    # 创建配置管理器
    config_manager = ConfigManager('./config.yaml')
    
    # 创建音频上传处理器
    processor = AudioUploadProcessor(config_manager)
    
    print("🎵 音频上传处理器测试")
    print(f"支持格式: {processor.SUPPORTED_FORMATS}")
    print(f"最大文件大小: {processor.MAX_FILE_SIZE / (1024*1024):.1f}MB")
    
    # 获取可用内容类型
    content_types = processor.get_available_content_types()
    print("\n📋 可用内容类型:")
    for content_type, config in content_types.items():
        print(f"  {config['icon']} {config['display_name']}: {config['description']}")
    
    # 获取统计信息
    stats = processor.get_upload_statistics()
    print(f"\n📊 当前统计: {stats['total_audio_files']} 个音频文件")
    
    print("\n✅ 音频上传处理器初始化成功")