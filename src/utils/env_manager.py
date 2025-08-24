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
        self.config_template = self.project_root / 'config.template.yaml'
        self.config_file = self.project_root / 'config.yaml'
        
    def load_env_file(self) -> Dict[str, str]:
        """
        加载.env文件中的环境变量
        
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
                            env_vars[key.strip()] = value
                            
                self.logger.debug(f"从{self.env_file}加载了{len(env_vars)}个环境变量")
                
            except Exception as e:
                self.logger.error(f"加载.env文件失败: {e}")
        
        return env_vars
    
    def create_env_template(self) -> bool:
        """
        创建.env模板文件
        
        Returns:
            bool: 是否创建成功
        """
        try:
            env_template = """# Project Bach 环境变量配置
# 请复制此文件为.env并填入真实的密钥

# OpenRouter API密钥 (从 https://openrouter.ai 获取)
OPENROUTER_API_KEY=sk-or-v1-your-actual-api-key-here

# Tailscale认证密钥 (从 Tailscale 控制台获取)
TAILSCALE_AUTH_KEY=tskey-auth-your-actual-auth-key-here

# 安全文件服务器令牌 (自动生成，或自定义)
SECURE_FILE_SERVER_TOKEN=your-secure-token-here

# GitHub配置 (用于API访问和Pages部署)
GITHUB_USERNAME=your-github-username
GITHUB_TOKEN=ghp_your-github-personal-access-token-here

# 可选：调试模式
DEBUG=false

# 可选：日志级别
LOG_LEVEL=INFO
"""
            
            env_template_file = self.project_root / '.env.template'
            with open(env_template_file, 'w', encoding='utf-8') as f:
                f.write(env_template)
            
            self.logger.info(f"创建环境变量模板: {env_template_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"创建.env模板失败: {e}")
            return False
    
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
        
        # 1. 创建.env模板（如果不存在）
        if not (self.project_root / '.env.template').exists():
            if not self.create_env_template():
                success = False
        
        # 2. 检查.env文件是否存在
        if not self.env_file.exists():
            self.logger.warning(f".env文件不存在: {self.env_file}")
            self.logger.info("请复制.env.template为.env并填入真实的密钥")
            
            # 创建一个基本的.env文件
            try:
                with open(self.env_file, 'w', encoding='utf-8') as f:
                    f.write("# 请填入真实的API密钥\n")
                    f.write("OPENROUTER_API_KEY=\n")
                    f.write("TAILSCALE_AUTH_KEY=\n")
                    f.write(f"SECURE_FILE_SERVER_TOKEN={self.generate_secure_token()}\n")
                    f.write("GITHUB_USERNAME=\n")
                    f.write("GITHUB_TOKEN=\n")
                
                self.logger.info(f"创建了基础.env文件: {self.env_file}")
                
            except Exception as e:
                self.logger.error(f"创建.env文件失败: {e}")
                success = False
        
        # 3. 验证必需的环境变量
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
    
    def substitute_variables(self, template_content: str, variables: Dict[str, str]) -> str:
        """
        替换模板中的变量
        
        Args:
            template_content: 模板内容
            variables: 变量字典
            
        Returns:
            str: 替换后的内容
        """
        result = template_content
        
        for key, value in variables.items():
            # 替换 ${VAR_NAME} 格式的变量
            placeholder = f"${{{key}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))
                self.logger.debug(f"替换变量: {placeholder} -> {'*' * len(str(value))}")
        
        return result
    
    def generate_config_from_template(self) -> bool:
        """
        从模板生成配置文件
        
        Returns:
            bool: 生成是否成功
        """
        try:
            # 检查模板文件是否存在
            if not self.config_template.exists():
                self.logger.error(f"配置模板不存在: {self.config_template}")
                return False
            
            # 加载环境变量
            env_vars = self.load_env_file()
            
            # 添加系统环境变量
            for key in ['OPENROUTER_API_KEY', 'TAILSCALE_AUTH_KEY', 'SECURE_FILE_SERVER_TOKEN', 'GITHUB_USERNAME', 'GITHUB_TOKEN']:
                if key in os.environ:
                    env_vars[key] = os.environ[key]
            
            # 读取模板内容
            with open(self.config_template, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # 替换变量
            config_content = self.substitute_variables(template_content, env_vars)
            
            # 写入配置文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                f.write(config_content)
            
            self.logger.info(f"从模板生成配置文件: {self.config_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"生成配置文件失败: {e}")
            return False
    
    def load_config(self) -> Optional[Dict[str, Any]]:
        """
        加载配置文件
        
        Returns:
            Dict: 配置字典，失败返回None
        """
        try:
            # 如果配置文件不存在，尝试从模板生成
            if not self.config_file.exists():
                if not self.generate_config_from_template():
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
            # 检查关键配置项
            api_key = config.get('api', {}).get('openrouter', {}).get('key')
            if not api_key or api_key.startswith('${'):
                self.logger.warning("OpenRouter API密钥未正确配置")
                return False
            
            tailscale_key = config.get('network', {}).get('tailscale', {}).get('auth_key')
            if not tailscale_key or tailscale_key.startswith('${'):
                self.logger.warning("Tailscale认证密钥未正确配置")
                return False
            
            self.logger.debug("配置验证通过")
            return True
            
        except Exception as e:
            self.logger.error(f"配置验证失败: {e}")
            return False
    
    def mask_sensitive_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        隐藏配置中的敏感信息用于日志输出
        
        Args:
            config: 原始配置
            
        Returns:
            Dict: 隐藏敏感信息的配置
        """
        import copy
        masked_config = copy.deepcopy(config)
        
        # 需要隐藏的字段
        sensitive_fields = [
            ['api', 'openrouter', 'key'],
            ['network', 'tailscale', 'auth_key'],
            ['network', 'secure_file_server', 'auth_token'],
            ['github', 'token']
        ]
        
        for field_path in sensitive_fields:
            current = masked_config
            for i, key in enumerate(field_path):
                if isinstance(current, dict) and key in current:
                    if i == len(field_path) - 1:
                        # 最后一级，隐藏值
                        value = current[key]
                        if value and len(str(value)) > 4:
                            current[key] = str(value)[:4] + '*' * (len(str(value)) - 4)
                    else:
                        current = current[key]
        
        return masked_config


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
        logging.error("项目环境设置失败")
    
    return config


if __name__ == "__main__":
    # 测试环境管理器
    logging.basicConfig(level=logging.INFO)
    config = setup_project_environment()
    
    if config:
        manager = EnvironmentManager()
        masked_config = manager.mask_sensitive_config(config)
        print("配置加载成功（敏感信息已隐藏）:")
        print(yaml.dump(masked_config, default_flow_style=False, allow_unicode=True))