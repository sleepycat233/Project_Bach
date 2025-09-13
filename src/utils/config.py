#!/usr/bin/env python3.11
"""
配置管理模块
统一管理项目配置文件的加载、验证和访问
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any
import logging


# 默认内容类型定义 - 作为配置的单一真实来源
DEFAULT_CONTENT_TYPES = {
    'lecture': {'icon': '🎓', 'display_name': 'Academic Lecture', 'has_subcategory': True},
    'meeting': {'icon': '🏢', 'display_name': 'Meeting Recording', 'has_subcategory': True},
}


class ConfigManager:
    """统一的配置管理器"""

    def __init__(self, config_path: str = "config.yaml"):
        """初始化配置管理器

        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path

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
        return (self.config or {}).get('paths', {})

    # 其他配置建议直接使用:
    # config_manager.config.get('openrouter', {}) 或
    # config_manager.get_nested_config('openrouter')



    def get_nested_config(self, *keys) -> Any:
        """获取嵌套配置值

        Args:
            *keys: 配置键路径，如 get_nested_config('content_classification', 'content_types', 'lecture')

        Returns:
            配置值，如果路径不存在返回None
        """
        current = self.config
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current


    def get_full_config(self) -> Dict[str, Any]:
        """获取完整配置

        Returns:
            完整配置字典
        """
        return (self.config or {}).copy()

    @staticmethod
    def get_default_content_types() -> Dict[str, Any]:
        """获取默认的内容类型定义

        Returns:
            默认内容类型字典
        """
        return DEFAULT_CONTENT_TYPES

    def get_content_types_config(self) -> Dict[str, Any]:
        """获取内容类型配置的统一入口

        Returns:
            内容类型配置字典，如果配置中不存在则返回默认值
        """
        return self.get_nested_config('content_classification', 'content_types') or self.get_default_content_types()



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
