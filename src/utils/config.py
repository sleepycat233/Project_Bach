#!/usr/bin/env python3.11
"""
配置管理模块
统一管理项目配置文件的加载、验证和访问
"""

import yaml
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional, Sequence, Union, Tuple
import logging

DEFAULT_MAX_FILE_SIZE = 1024 * 1024 * 1024  # 1GB
DEFAULT_SUPPORTED_FORMATS: Tuple[str, ...] = (
    '.mp3', '.wav', '.m4a', '.mp4', '.flac', '.aac', '.ogg'
)
DEFAULT_UPLOAD_FOLDER = './data/uploads'
DEFAULT_ORGANIZE_BY_CATEGORY = False
DEFAULT_CREATE_SUBCATEGORY_FOLDERS = False
DEFAULT_TAILSCALE_ONLY = True


@dataclass(frozen=True)
class UploadSettings:
    """Typed view over web_frontend.upload configuration."""

    max_file_size: int = DEFAULT_MAX_FILE_SIZE
    supported_formats: Tuple[str, ...] = DEFAULT_SUPPORTED_FORMATS
    upload_folder: str = DEFAULT_UPLOAD_FOLDER
    organize_by_category: bool = DEFAULT_ORGANIZE_BY_CATEGORY
    create_subcategory_folders: bool = DEFAULT_CREATE_SUBCATEGORY_FOLDERS

    @property
    def allowed_extensions(self) -> Tuple[str, ...]:
        return tuple(fmt.lstrip('.') for fmt in self.supported_formats)


@dataclass(frozen=True)
class SecuritySettings:
    """Typed view over web_frontend.security configuration."""

    tailscale_only: bool = DEFAULT_TAILSCALE_ONLY


class ConfigManager:
    """统一的配置管理器"""

    def __init__(self, config_path: str = "config.yaml"):
        """初始化配置管理器

        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)

        # 首先尝试使用环境管理器
        try:
            from .env_manager import setup_project_environment
            self.config = setup_project_environment()
            if self.config:
                # 环境管理器加载成功，但仍需要应用环境变量覆盖
                self.apply_env_overrides()
                # 验证通过环境管理器加载的配置
                self.validate_config(self.config)
                return
        except Exception as e:
            logging.warning(f"环境管理器加载失败，回退到直接加载: {e}")

        # 回退到原有方式
        self.config = self.load_config(config_path)

        # 应用环境变量覆盖
        self.apply_env_overrides()

        self.validate_config(self.config)

    def load_config(self, path: str) -> Dict[str, Any]:
        """加载配置文件

        Args:
            path: 配置文件路径

        Returns:
            配置字典

        Raises:
            FileNotFoundError: 配置文件不存在
            ValueError: 配置文件格式错误或缺少必要项
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            if config is None:
                raise ValueError("配置文件为空")

            return config

        except FileNotFoundError:
            raise FileNotFoundError(f"配置文件未找到: {path}")
        except yaml.YAMLError as e:
            raise ValueError(f"配置文件格式错误: {e}")

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置文件完整性

        Args:
            config: 配置字典

        Returns:
            验证是否通过

        Raises:
            ValueError: 缺少必要的配置项
        """
        required_keys = ['paths', 'logging']  # openrouter、spacy、audio等都是可选的
        missing_keys = []

        for key in required_keys:
            if key not in config:
                missing_keys.append(key)

        if missing_keys:
            raise ValueError(f"配置文件缺少必要项: {', '.join(missing_keys)}")

        # 验证OpenRouter配置 (如果配置存在，则验证base_url)
        openrouter_config = config.get('openrouter', {})
        if openrouter_config and not openrouter_config.get('base_url'):
            raise ValueError("OpenRouter API配置不完整，需要base_url")

        # 环境变量中的API key是可选的
        # 系统可以在没有OPENROUTER_API_KEY的情况下运行（仅转录功能）
        # AI功能（摘要、思维导图）需要时才检查密钥

        # 验证路径配置
        paths_config = config.get('paths', {})
        required_paths = ['watch_folder', 'data_folder', 'output_folder']
        for path_key in required_paths:
            if path_key not in paths_config:
                raise ValueError(f"路径配置缺少: {path_key}")

        return True

    def apply_env_overrides(self):
        """应用环境变量覆盖配置"""
        import os

        # 确保config不为None
        if self.config is None:
            self.config = {}

        # GitHub用户名和令牌
        if 'GITHUB_USERNAME' in os.environ:
            if 'github' not in self.config:
                self.config['github'] = {}
            self.config['github']['username'] = os.environ['GITHUB_USERNAME']

            # 自动生成GitHub Pages URL
            username = os.environ['GITHUB_USERNAME']
            repo_name = self.config.get('github', {}).get('repo_name', 'Project_Bach')

            # 检查是否启用GitHub Pages
            pages_enabled = self.config.get('github', {}).get('pages', {}).get('enabled', True)
            if pages_enabled:
                self.config['github']['pages_url'] = f"https://{username}.github.io/{repo_name}"

        if 'GITHUB_TOKEN' in os.environ:
            if 'github' not in self.config:
                self.config['github'] = {}
            self.config['github']['token'] = os.environ['GITHUB_TOKEN']

        # OpenRouter API Key
        if 'OPENROUTER_API_KEY' in os.environ:
            if 'openrouter' not in self.config:
                self.config['openrouter'] = {}
            self.config['openrouter']['key'] = os.environ['OPENROUTER_API_KEY']

    # 保留使用频率最高的路径配置方法（8次使用）
    def get_paths_config(self) -> Dict[str, str]:
        """获取路径配置

        Returns:
            路径配置字典
        """
        paths_config = (self.config or {}).get('paths', {})
        if not paths_config:
            self.logger.warning("配置文件缺少 'paths' 配置，使用空字典")
        return paths_config

    # 其他配置建议直接使用:
    # config_manager.config.get('openrouter', {}) 或 config_manager.get('openrouter')

    def get(self, *path: Union[str, Sequence[str]], default=None) -> Any:
        """通用配置读取，支持点路径或序列路径。

        示例::

            config_manager.get('openrouter.base_url')
            config_manager.get(['paths', 'data_folder'])

        Args:
            *path: 点号分隔的字符串或键序列
            default: 路径不存在时返回的默认值
        """
        if len(path) == 1 and isinstance(path[0], (str, list, tuple)):
            keys = path[0]
        else:
            keys = path

        if isinstance(keys, str):
            key_list = [segment for segment in keys.split('.') if segment]
        else:
            key_list = list(keys)

        if not key_list:
            return self.config if default is None else default

        current: Any = self.config
        traversed: list[str] = []
        for key in key_list:
            if isinstance(current, dict) and key in current:
                current = current[key]
                traversed.append(str(key))
            else:
                missing_path = '.'.join(key_list)
                missing_at = '.'.join(traversed + [str(key)]) if traversed else str(key)
                self.logger.warning(
                    "配置路径不存在: %s (在 %s 处中断)",
                    missing_path,
                    missing_at,
                )
                return default

        return current if current is not None else default

    def get_upload_settings(self) -> UploadSettings:
        """获取上传配置（带默认值）。"""

        raw = self.get('web_frontend.upload', default={}) or {}

        supported_formats = tuple(
            raw.get('supported_formats', DEFAULT_SUPPORTED_FORMATS)
        )

        return UploadSettings(
            max_file_size=raw.get('max_file_size', DEFAULT_MAX_FILE_SIZE),
            supported_formats=supported_formats if supported_formats else DEFAULT_SUPPORTED_FORMATS,
            upload_folder=raw.get('upload_folder', DEFAULT_UPLOAD_FOLDER),
            organize_by_category=raw.get('organize_by_category', DEFAULT_ORGANIZE_BY_CATEGORY),
            create_subcategory_folders=raw.get('create_subcategory_folders', DEFAULT_CREATE_SUBCATEGORY_FOLDERS),
        )

    def get_security_settings(self) -> SecuritySettings:
        """获取安全配置（带默认值）。"""

        raw = self.get('web_frontend.security', default={}) or {}
        return SecuritySettings(
            tailscale_only=raw.get('tailscale_only', DEFAULT_TAILSCALE_ONLY)
        )


    def get_full_config(self) -> Dict[str, Any]:
        """获取完整配置

        Returns:
            完整配置字典
        """
        return (self.config or {}).copy()
    
class LoggingSetup:
    """日志配置工具"""

    @staticmethod
    def setup_logging(config: Dict[str, Any]) -> logging.Logger:
        """设置日志系统

        Args:
            config: 日志配置字典

        Returns:
            配置好的logger实例
        """
        log_file = Path(config.get('file', './app.log'))
        log_level = config.get('level', 'INFO')

        # 创建日志目录
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # 配置日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # 清除现有的handlers
        logger = logging.getLogger('project_bach')
        logger.handlers.clear()

        # 设置日志级别
        logger.setLevel(getattr(logging, log_level.upper()))

        # 文件handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # 控制台handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        logger.info("日志系统初始化完成")
        return logger


class DirectoryManager:
    """目录管理工具"""

    @staticmethod
    def setup_directories(paths_config: Dict[str, str]) -> None:
        """创建必要的目录结构

        Args:
            paths_config: 路径配置字典
        """
        directories = [
            paths_config.get('watch_folder'),
            paths_config.get('data_folder'),
            paths_config.get('output_folder'),
        ]

        # 添加子目录
        data_folder = paths_config.get('data_folder')
        if data_folder:
            directories.extend([
                # 移除transcripts，现在使用output下的分层结构
                os.path.join(data_folder, 'logs')
            ])

        for directory in directories:
            if directory:
                Path(directory).mkdir(parents=True, exist_ok=True)

        logging.getLogger('project_bach').info("目录结构创建完成")
