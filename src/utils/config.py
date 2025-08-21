#!/usr/bin/env python3.11
"""
配置管理模块
统一管理项目配置文件的加载、验证和访问
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging


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
                # 验证通过环境管理器加载的配置
                self.validate_config(self.config)
                return
        except Exception as e:
            logging.warning(f"环境管理器加载失败，回退到直接加载: {e}")
        
        # 回退到原有方式
        self.config = self.load_config(config_path)
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
        required_keys = ['api', 'paths', 'spacy', 'logging']
        missing_keys = []
        
        for key in required_keys:
            if key not in config:
                missing_keys.append(key)
        
        if missing_keys:
            raise ValueError(f"配置文件缺少必要项: {', '.join(missing_keys)}")
        
        # 验证API配置
        api_config = config.get('api', {})
        openrouter_config = api_config.get('openrouter', {})
        if not openrouter_config.get('key') or not openrouter_config.get('base_url'):
            raise ValueError("OpenRouter API配置不完整，需要key和base_url")
        
        # 验证路径配置
        paths_config = config.get('paths', {})
        required_paths = ['watch_folder', 'data_folder', 'output_folder']
        for path_key in required_paths:
            if path_key not in paths_config:
                raise ValueError(f"路径配置缺少: {path_key}")
        
        return True
    
    def get_api_config(self) -> Dict[str, Any]:
        """获取API配置
        
        Returns:
            API配置字典
        """
        return self.config.get('api', {})
    
    def get_openrouter_config(self) -> Dict[str, Any]:
        """获取OpenRouter API配置
        
        Returns:
            OpenRouter配置字典
        """
        return self.get_api_config().get('openrouter', {})
    
    def get_paths_config(self) -> Dict[str, str]:
        """获取路径配置
        
        Returns:
            路径配置字典
        """
        return self.config.get('paths', {})
    
    def get_spacy_config(self) -> Dict[str, Any]:
        """获取spaCy配置
        
        Returns:
            spaCy配置字典
        """
        return self.config.get('spacy', {})
    
    def get_whisperkit_config(self) -> Dict[str, Any]:
        """获取WhisperKit配置
        
        Returns:
            WhisperKit配置字典
        """
        return self.config.get('whisperkit', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置
        
        Returns:
            日志配置字典
        """
        return self.config.get('logging', {})
    
    def get_full_config(self) -> Dict[str, Any]:
        """获取完整配置
        
        Returns:
            完整配置字典
        """
        return self.config.copy()
    
    def update_config(self, key_path: str, value: Any) -> None:
        """更新配置项
        
        Args:
            key_path: 配置项路径，支持点分隔符如'api.openrouter.key'
            value: 新值
        """
        keys = key_path.split('.')
        current = self.config
        
        # 导航到目标位置
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # 设置最终值
        current[keys[-1]] = value
    
    def save_config(self, path: Optional[str] = None) -> None:
        """保存配置到文件
        
        Args:
            path: 保存路径，默认为原路径
        """
        save_path = path or self.config_path
        
        with open(save_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)


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
                os.path.join(data_folder, 'transcripts'),
                os.path.join(data_folder, 'logs')
            ])
        
        for directory in directories:
            if directory:
                Path(directory).mkdir(parents=True, exist_ok=True)
        
        logging.getLogger('project_bach').info("目录结构创建完成")


# 兼容性函数，保持原有接口
def load_config(path: str) -> Dict[str, Any]:
    """加载配置文件（兼容性函数）
    
    Args:
        path: 配置文件路径
        
    Returns:
        配置字典
    """
    manager = ConfigManager(path)
    return manager.get_full_config()