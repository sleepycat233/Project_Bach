#!/usr/bin/env python3.11
"""
GitHub发布管理器
负责GitHub仓库操作、Pages配置和发布管理
"""

import requests
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta


class GitHubPublisher:
    """GitHub发布服务"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化GitHub发布服务
        
        Args:
            config: GitHub配置字典
        """
        self.config = config
        self.logger = logging.getLogger('project_bach.github_publisher')
        
        # GitHub API配置
        self.token = config['token']
        self.username = config['username']
        self.base_url = config.get('base_url', 'https://api.github.com')
        self.publish_repo = config['publish_repo']
        self.pages_branch = config.get('pages_branch', 'gh-pages')
        
        # 设置请求头
        self.headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Project-Bach-Publisher/1.0'
        }
        
        # 验证配置
        self._validate_config()
        
    def _validate_config(self):
        """验证GitHub配置"""
        if not self.validate_github_token(self.token):
            raise ValueError(f"无效的GitHub Token: {self.token[:10]}...")
            
        if not self.username or not self.publish_repo:
            raise ValueError("缺少必需的GitHub配置: username或publish_repo")
            
        self.logger.info(f"GitHub发布服务初始化完成: {self.username}/{self.publish_repo}")
    
    def validate_github_token(self, token: str) -> bool:
        """验证GitHub Token格式和有效性
        
        Args:
            token: GitHub Token
            
        Returns:
            是否有效
        """
        # 检查Token格式
        if not token or len(token) < 20:
            return False
            
        # 检查Token前缀
        valid_prefixes = ['ghp_', 'gho_', 'ghu_', 'ghs_', 'ghr_']
        if not any(token.startswith(prefix) for prefix in valid_prefixes):
            return False
            
        # 通过API验证Token有效性
        try:
            response = requests.get(
                f"{self.base_url}/user",
                headers=self.headers,
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            self.logger.warning(f"Token验证失败: {str(e)}")
            return False
    
    def create_repository(self) -> Dict[str, Any]:
        """创建GitHub仓库
        
        Returns:
            创建结果字典
        """
        self.logger.info(f"检查仓库是否存在: {self.username}/{self.publish_repo}")
        
        # 首先检查仓库是否已存在
        repo_status = self.check_repository_status()
        if repo_status['exists']:
            return {
                'success': True,
                'repo_url': f"https://github.com/{self.username}/{self.publish_repo}",
                'message': '仓库已存在',
                'created': False
            }
        
        # 创建新仓库
        repo_data = {
            'name': self.publish_repo,
            'description': 'Project Bach 音频处理结果发布站点',
            'private': False,
            'auto_init': True,
            'gitignore_template': 'Jekyll',
            'license_template': 'mit'
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/user/repos",
                headers=self.headers,
                json=repo_data,
                timeout=30
            )
            
            if response.status_code == 201:
                repo_info = response.json()
                self.logger.info(f"仓库创建成功: {repo_info['html_url']}")
                
                return {
                    'success': True,
                    'repo_url': repo_info['html_url'],
                    'clone_url': repo_info['clone_url'],
                    'ssh_url': repo_info['ssh_url'],
                    'message': '仓库创建成功',
                    'created': True
                }
            else:
                error_msg = response.json().get('message', '未知错误')
                self.logger.error(f"仓库创建失败: {response.status_code} - {error_msg}")
                
                return {
                    'success': False,
                    'message': f'仓库创建失败: {error_msg}',
                    'error_code': response.status_code
                }
                
        except Exception as e:
            self.logger.error(f"仓库创建异常: {str(e)}")
            return {
                'success': False,
                'message': f'仓库创建异常: {str(e)}'
            }
    
    def check_repository_status(self) -> Dict[str, Any]:
        """检查仓库状态
        
        Returns:
            仓库状态信息
        """
        try:
            response = requests.get(
                f"{self.base_url}/repos/{self.username}/{self.publish_repo}",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                repo_info = response.json()
                
                # 检查Pages状态
                pages_status = self._check_pages_status()
                
                return {
                    'exists': True,
                    'private': repo_info['private'],
                    'has_pages': pages_status['enabled'],
                    'pages_url': pages_status.get('url'),
                    'default_branch': repo_info['default_branch'],
                    'last_updated': repo_info['updated_at'],
                    'size_kb': repo_info['size']
                }
            elif response.status_code == 404:
                return {
                    'exists': False,
                    'message': '仓库不存在'
                }
            else:
                return {
                    'exists': False,
                    'error': f'检查失败: {response.status_code}'
                }
                
        except Exception as e:
            self.logger.error(f"检查仓库状态异常: {str(e)}")
            return {
                'exists': False,
                'error': f'检查异常: {str(e)}'
            }
    
    def configure_github_pages(self) -> Dict[str, Any]:
        """配置GitHub Pages
        
        Returns:
            配置结果
        """
        self.logger.info(f"配置GitHub Pages: {self.username}/{self.publish_repo}")
        
        # Pages配置数据
        pages_config = {
            'source': {
                'branch': self.pages_branch,
                'path': '/'
            },
            'build_type': 'legacy'  # 使用传统构建方式
        }
        
        try:
            # 先检查Pages是否已启用
            current_status = self._check_pages_status()
            
            if current_status['enabled']:
                self.logger.info(f"GitHub Pages已启用: {current_status['url']}")
                return {
                    'success': True,
                    'pages_url': current_status['url'],
                    'message': 'GitHub Pages已启用',
                    'configured': False
                }
            
            # 启用GitHub Pages
            response = requests.post(
                f"{self.base_url}/repos/{self.username}/{self.publish_repo}/pages",
                headers=self.headers,
                json=pages_config,
                timeout=30
            )
            
            if response.status_code in [201, 409]:  # 201=创建成功, 409=已存在
                if response.status_code == 201:
                    pages_info = response.json()
                    pages_url = pages_info['html_url']
                else:
                    # 已存在的情况，获取当前配置
                    pages_url = f"https://{self.username}.github.io/{self.publish_repo}/"
                
                self.logger.info(f"GitHub Pages配置成功: {pages_url}")
                
                return {
                    'success': True,
                    'pages_url': pages_url,
                    'source_branch': self.pages_branch,
                    'message': 'GitHub Pages配置成功',
                    'configured': True
                }
            else:
                error_msg = response.json().get('message', '未知错误')
                self.logger.error(f"Pages配置失败: {response.status_code} - {error_msg}")
                
                return {
                    'success': False,
                    'message': f'Pages配置失败: {error_msg}',
                    'error_code': response.status_code
                }
                
        except Exception as e:
            self.logger.error(f"Pages配置异常: {str(e)}")
            return {
                'success': False,
                'message': f'Pages配置异常: {str(e)}'
            }
    
    def _check_pages_status(self) -> Dict[str, Any]:
        """检查GitHub Pages状态
        
        Returns:
            Pages状态信息
        """
        try:
            response = requests.get(
                f"{self.base_url}/repos/{self.username}/{self.publish_repo}/pages",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                pages_info = response.json()
                return {
                    'enabled': True,
                    'url': pages_info['html_url'],
                    'source_branch': pages_info['source']['branch'],
                    'status': pages_info.get('status', 'unknown'),
                    'cname': pages_info.get('cname')
                }
            else:
                return {
                    'enabled': False,
                    'status': 'not_configured'
                }
                
        except Exception as e:
            self.logger.debug(f"检查Pages状态失败: {str(e)}")
            return {
                'enabled': False,
                'status': 'unknown',
                'error': str(e)
            }
    
    def setup_repository_for_publishing(self) -> Dict[str, Any]:
        """设置仓库用于发布
        
        完整的仓库准备流程：
        1. 创建/检查仓库
        2. 配置GitHub Pages  
        3. 验证设置
        
        Returns:
            设置结果
        """
        self.logger.info("开始设置GitHub仓库用于发布")
        
        setup_steps = []
        
        try:
            # 步骤1：创建/检查仓库
            self.logger.info("步骤1: 创建/检查仓库")
            repo_result = self.create_repository()
            setup_steps.append({
                'step': 'create_repository',
                'success': repo_result['success'],
                'message': repo_result['message']
            })
            
            if not repo_result['success']:
                return {
                    'success': False,
                    'message': '仓库设置失败',
                    'steps': setup_steps
                }
            
            # 等待仓库创建完成
            if repo_result.get('created'):
                self.logger.info("等待仓库初始化完成...")
                time.sleep(5)
            
            # 步骤2：配置GitHub Pages
            self.logger.info("步骤2: 配置GitHub Pages")
            pages_result = self.configure_github_pages()
            setup_steps.append({
                'step': 'configure_pages',
                'success': pages_result['success'],
                'message': pages_result['message']
            })
            
            if not pages_result['success']:
                return {
                    'success': False,
                    'message': 'GitHub Pages配置失败',
                    'steps': setup_steps
                }
            
            # 步骤3：验证最终状态
            self.logger.info("步骤3: 验证仓库状态")
            final_status = self.check_repository_status()
            setup_steps.append({
                'step': 'verify_status',
                'success': final_status['exists'] and final_status['has_pages'],
                'message': '仓库状态验证完成'
            })
            
            # 返回完整结果
            return {
                'success': True,
                'message': '仓库设置完成',
                'repo_url': repo_result['repo_url'],
                'pages_url': pages_result['pages_url'],
                'pages_branch': self.pages_branch,
                'setup_steps': setup_steps,
                'ready_for_publishing': True
            }
            
        except Exception as e:
            self.logger.error(f"仓库设置异常: {str(e)}")
            return {
                'success': False,
                'message': f'仓库设置异常: {str(e)}',
                'steps': setup_steps
            }
    
    def get_repository_info(self) -> Dict[str, Any]:
        """获取仓库详细信息
        
        Returns:
            仓库信息字典
        """
        status = self.check_repository_status()
        
        if status['exists']:
            return {
                'repository': {
                    'name': self.publish_repo,
                    'full_name': f"{self.username}/{self.publish_repo}",
                    'url': f"https://github.com/{self.username}/{self.publish_repo}",
                    'private': status['private'],
                    'default_branch': status['default_branch'],
                    'size_kb': status['size_kb'],
                    'last_updated': status['last_updated']
                },
                'pages': {
                    'enabled': status['has_pages'],
                    'url': status.get('pages_url'),
                    'branch': self.pages_branch
                },
                'publisher': {
                    'username': self.username,
                    'token_valid': self.validate_github_token(self.token)
                }
            }
        else:
            return {
                'repository': {
                    'exists': False,
                    'message': status.get('message', '仓库不存在')
                }
            }


class GitHubAPIRateLimiter:
    """GitHub API限流管理器"""
    
    def __init__(self, github_publisher: GitHubPublisher):
        """初始化限流管理器
        
        Args:
            github_publisher: GitHub发布服务实例
        """
        self.publisher = github_publisher
        self.logger = logging.getLogger('project_bach.github_rate_limiter')
        self.last_request_time = None
        self.min_request_interval = 1.0  # 最小请求间隔（秒）
        
    def check_rate_limit(self) -> Dict[str, Any]:
        """检查当前API速率限制状态
        
        Returns:
            速率限制信息
        """
        try:
            response = requests.get(
                f"{self.publisher.base_url}/rate_limit",
                headers=self.publisher.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                rate_info = response.json()
                core_limit = rate_info['resources']['core']
                
                # 计算重置时间
                reset_time = datetime.fromtimestamp(core_limit['reset'])
                time_to_reset = (reset_time - datetime.now()).total_seconds()
                
                return {
                    'limit': core_limit['limit'],
                    'remaining': core_limit['remaining'],
                    'used': core_limit['used'],
                    'reset_time': reset_time.isoformat(),
                    'time_to_reset_seconds': max(0, time_to_reset),
                    'rate_limited': core_limit['remaining'] < 10  # 剩余少于10次认为受限
                }
            else:
                return {
                    'error': f'无法获取速率限制信息: {response.status_code}'
                }
                
        except Exception as e:
            self.logger.warning(f"检查速率限制失败: {str(e)}")
            return {
                'error': f'检查失败: {str(e)}'
            }
    
    def wait_if_rate_limited(self):
        """如果被限流则等待"""
        rate_status = self.check_rate_limit()
        
        if rate_status.get('rate_limited'):
            wait_time = min(rate_status.get('time_to_reset_seconds', 60), 300)  # 最多等5分钟
            self.logger.warning(f"API速率限制，等待 {wait_time:.1f} 秒")
            time.sleep(wait_time)
        
        # 确保请求间隔
        if self.last_request_time:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.min_request_interval:
                time.sleep(self.min_request_interval - elapsed)
        
        self.last_request_time = time.time()


# 工具函数
def validate_github_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """验证GitHub配置
    
    Args:
        config: GitHub配置字典
        
    Returns:
        验证结果
    """
    required_fields = ['token', 'username', 'publish_repo']
    missing_fields = []
    
    for field in required_fields:
        if not config.get(field):
            missing_fields.append(field)
    
    if missing_fields:
        return {
            'valid': False,
            'message': f'缺少必需字段: {missing_fields}'
        }
    
    # 验证token格式
    token = config['token']
    if len(token) < 20 or not any(token.startswith(p) for p in ['ghp_', 'gho_', 'ghu_', 'ghs_', 'ghr_']):
        return {
            'valid': False,
            'message': 'GitHub Token格式无效'
        }
    
    return {
        'valid': True,
        'message': 'GitHub配置有效'
    }


if __name__ == '__main__':
    # 测试GitHub发布服务
    test_config = {
        'token': 'ghp_test_token_for_development_only',
        'username': 'testuser',
        'publish_repo': 'project-bach-site',
        'base_url': 'https://api.github.com',
        'pages_branch': 'gh-pages'
    }
    
    # 验证配置
    config_result = validate_github_config(test_config)
    print(f"配置验证: {config_result}")
    
    if config_result['valid']:
        # 创建发布服务实例（仅测试初始化）
        try:
            publisher = GitHubPublisher(test_config)
            print(f"GitHub发布服务初始化成功")
            
            # 获取仓库信息（不实际调用API）
            print(f"目标仓库: {publisher.username}/{publisher.publish_repo}")
            print(f"Pages分支: {publisher.pages_branch}")
            
        except Exception as e:
            print(f"初始化失败: {e}")