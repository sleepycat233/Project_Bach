#!/usr/bin/env python3.11
"""
环境变量和配置管理器
安全地处理API密钥和敏感配置信息
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import string
import secrets


class EnvironmentManager:
    """环境变量和配置管理器"""
    
    def __init__(self, project_root: Optional[str] = None):
        """
        初始化环境管理器
        
        Args:
            project_root: 项目根目录，默认为当前目录
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.logger = logging.getLogger(__name__)
        
        # 配置文件路径
        self.env_file = self.project_root / '.env'
        self.config_file = self.project_root / 'config.yaml'
        
    def load_env_file(self) -> Dict[str, str]:
        """
        加载.env文件中的环境变量，并设置到系统环境中

        Returns:
            Dict: 环境变量字典
        """
        env_vars = {}

        if self.env_file.exists():
            try:
                with open(self.env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            # 移除引号
                            value = value.strip().strip('"').strip("'")
                            key = key.strip()
                            env_vars[key] = value

                            # 设置到系统环境变量中（如果尚未设置）
                            if key not in os.environ:
                                os.environ[key] = value
                                self.logger.debug(f"设置环境变量: {key}")

                self.logger.debug(f"从{self.env_file}加载了{len(env_vars)}个环境变量")

            except Exception as e:
                self.logger.error(f"加载.env文件失败: {e}")

        return env_vars
    
    
    def generate_secure_token(self, length: int = 32) -> str:
        """
        生成安全令牌
        
        Args:
            length: 令牌长度
            
        Returns:
            str: 安全令牌
        """
        alphabet = string.ascii_letters + string.digits + '-_'
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def setup_environment(self) -> bool:
        """
        设置项目环境
        
        Returns:
            bool: 设置是否成功
        """
        success = True
        
        # 1. 检查.env文件是否存在
        if not self.env_file.exists():
            self.logger.warning(f".env文件不存在: {self.env_file}")
            self.logger.info("请复制.env.template为.env并填入真实的密钥")
            success = False
        
        # 2. 验证必需的环境变量
        env_vars = self.load_env_file()
        required_vars = ['OPENROUTER_API_KEY', 'TAILSCALE_AUTH_KEY']
        
        missing_vars = []
        for var in required_vars:
            if not env_vars.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            self.logger.warning(f"缺少必需的环境变量: {missing_vars}")
            success = False
        
        return success
    
    
    def load_config(self) -> Optional[Dict[str, Any]]:
        """
        加载配置文件
        
        Returns:
            Dict: 配置字典，失败返回None
        """
        try:
            # 检查配置文件是否存在
            if not self.config_file.exists():
                self.logger.error(f"配置文件不存在: {self.config_file}")
                return None
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 验证关键配置
            if not self._validate_config(config):
                return None
            
            return config
            
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}")
            return None
    
    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """
        验证配置有效性
        
        Args:
            config: 配置字典
            
        Returns:
            bool: 配置是否有效
        """
        try:
            # 检查基本配置结构
            if not isinstance(config, dict):
                self.logger.error("配置格式无效")
                return False
            
            # 检查必要的配置段落是否存在
            required_sections = ['paths', 'mlx_whisper', 'diarization']
            for section in required_sections:
                if section not in config:
                    self.logger.warning(f"缺少必要配置段落: {section}")
            
            self.logger.debug("配置验证通过")
            return True
            
        except Exception as e:
            self.logger.error(f"配置验证失败: {e}")
            return False
    


def setup_project_environment(project_root: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    设置项目环境并加载配置
    
    Args:
        project_root: 项目根目录
        
    Returns:
        Dict: 加载的配置，失败返回None
    """
    manager = EnvironmentManager(project_root)
    
    # 设置环境
    if not manager.setup_environment():
        logging.warning("环境设置存在问题，请检查.env文件")
    
    # 加载配置
    config = manager.load_config()
    if config:
        logging.info("项目环境设置完成")
    else:
        logging.warning("项目环境设置失败")
    
    return config


if __name__ == "__main__":
    # 测试环境管理器
    logging.basicConfig(level=logging.INFO)
    config = setup_project_environment()
    
    if config:
        print("配置加载成功:")
        print(yaml.dump(config, default_flow_style=False, allow_unicode=True))