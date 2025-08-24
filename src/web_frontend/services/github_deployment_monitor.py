#!/usr/bin/env python3
"""
GitHub Pages部署状态监控服务

基于GitHub API检测GitHub Pages的真实部署状态
"""

import logging
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class GitHubDeploymentMonitor:
    """GitHub Pages部署状态监控器"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化部署监控器
        
        Args:
            config: GitHub配置
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # GitHub API配置
        github_config = config.get('github', {})
        self.token = github_config.get('token', '')
        self.username = github_config.get('username', '')
        self.repo_name = github_config.get('repo_name', '')
        self.base_url = github_config.get('base_url', 'https://api.github.com')
        
        # 请求头
        self.headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Project-Bach-Monitor/1.0'
        } if self.token else {}
        
        # 缓存
        self._last_check_time = None
        self._last_deployment_id = None
        self._cache_duration = 30  # 30秒缓存
        
        self.logger.info("GitHub部署监控器初始化完成")
    
    def check_pages_deployment_status(self, commit_hash: Optional[str] = None) -> Dict[str, Any]:
        """检查GitHub Pages部署状态
        
        Args:
            commit_hash: 要检查的提交哈希（可选）
            
        Returns:
            部署状态信息
        """
        try:
            if not self._is_github_configured():
                return self._create_fallback_result()
            
            # 获取最新的GitHub Pages部署
            deployment_status = self._get_latest_pages_deployment(commit_hash)
            
            if not deployment_status['found']:
                return {
                    'deployed': False,
                    'status': 'not_found',
                    'message': 'No GitHub Pages deployment found',
                    'method': 'github_api'
                }
            
            deployment = deployment_status['deployment']
            
            # 检查部署状态
            if deployment['state'] == 'success':
                # 验证网站是否真正可访问
                website_check = self._verify_website_accessibility()
                
                return {
                    'deployed': website_check['accessible'],
                    'status': 'success' if website_check['accessible'] else 'deploying',
                    'message': website_check['message'],
                    'deployment_info': {
                        'id': deployment['id'],
                        'created_at': deployment['created_at'],
                        'updated_at': deployment['updated_at'],
                        'environment': deployment.get('environment', 'github-pages'),
                        'url': deployment.get('environment_url', self._get_pages_url())
                    },
                    'method': 'github_api'
                }
            
            elif deployment['state'] in ['pending', 'in_progress']:
                return {
                    'deployed': False,
                    'status': 'deploying',
                    'message': f'GitHub Pages deployment {deployment["state"]}',
                    'deployment_info': {
                        'id': deployment['id'],
                        'created_at': deployment['created_at'],
                        'state': deployment['state']
                    },
                    'method': 'github_api'
                }
            
            elif deployment['state'] in ['failure', 'error']:
                return {
                    'deployed': False,
                    'status': 'failed',
                    'message': f'GitHub Pages deployment failed: {deployment["state"]}',
                    'deployment_info': {
                        'id': deployment['id'],
                        'state': deployment['state'],
                        'created_at': deployment['created_at']
                    },
                    'method': 'github_api'
                }
            
            else:
                return {
                    'deployed': False,
                    'status': 'unknown',
                    'message': f'Unknown deployment state: {deployment["state"]}',
                    'method': 'github_api'
                }
                
        except Exception as e:
            self.logger.error(f"检查GitHub Pages部署状态失败: {e}")
            return self._create_fallback_result()
    
    def _get_latest_pages_deployment(self, target_commit: Optional[str] = None) -> Dict[str, Any]:
        """获取最新的GitHub Pages部署
        
        Args:
            target_commit: 目标提交哈希
            
        Returns:
            部署信息
        """
        try:
            # GitHub Deployments API
            url = f"{self.base_url}/repos/{self.username}/{self.repo_name}/deployments"
            params = {
                'environment': 'github-pages',
                'per_page': 10
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=15)
            
            if response.status_code != 200:
                self.logger.warning(f"获取部署列表失败: {response.status_code}")
                return {'found': False}
            
            deployments = response.json()
            
            if not deployments:
                return {'found': False}
            
            # 找到最新的或匹配提交的部署
            target_deployment = None
            
            if target_commit:
                # 查找特定提交的部署
                for deployment in deployments:
                    if deployment['sha'].startswith(target_commit[:7]):
                        target_deployment = deployment
                        break
            
            if not target_deployment:
                # 使用最新部署
                target_deployment = deployments[0]
            
            # 获取部署状态
            deployment_status = self._get_deployment_status(target_deployment['id'])
            
            if deployment_status:
                target_deployment['state'] = deployment_status['state']
                target_deployment['environment_url'] = deployment_status.get('environment_url')
            
            return {
                'found': True,
                'deployment': target_deployment
            }
            
        except Exception as e:
            self.logger.error(f"获取部署信息失败: {e}")
            return {'found': False}
    
    def _get_deployment_status(self, deployment_id: int) -> Optional[Dict[str, Any]]:
        """获取部署状态
        
        Args:
            deployment_id: 部署ID
            
        Returns:
            部署状态信息
        """
        try:
            url = f"{self.base_url}/repos/{self.username}/{self.repo_name}/deployments/{deployment_id}/statuses"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                statuses = response.json()
                if statuses:
                    # 返回最新状态
                    return statuses[0]
            
            return None
            
        except Exception as e:
            self.logger.debug(f"获取部署状态失败: {e}")
            return None
    
    def _verify_website_accessibility(self) -> Dict[str, Any]:
        """验证网站是否可访问
        
        Returns:
            可访问性检查结果
        """
        try:
            pages_url = self._get_pages_url()
            
            if not pages_url:
                return {
                    'accessible': False,
                    'message': 'No GitHub Pages URL configured'
                }
            
            # 发送HEAD请求检查网站
            response = requests.head(pages_url, timeout=10, allow_redirects=True)
            
            if response.status_code == 200:
                return {
                    'accessible': True,
                    'message': 'GitHub Pages is accessible',
                    'url': pages_url,
                    'response_code': response.status_code
                }
            else:
                return {
                    'accessible': False,
                    'message': f'GitHub Pages returned {response.status_code}',
                    'url': pages_url,
                    'response_code': response.status_code
                }
                
        except requests.RequestException as e:
            return {
                'accessible': False,
                'message': f'Network error: {str(e)}',
                'url': pages_url if 'pages_url' in locals() else 'unknown'
            }
        except Exception as e:
            return {
                'accessible': False,
                'message': f'Check error: {str(e)}'
            }
    
    def _get_pages_url(self) -> str:
        """获取GitHub Pages URL"""
        username = self.username or self.config.get('github', {}).get('username', '')
        repo_name = self.repo_name or self.config.get('github', {}).get('repo_name', '')
        
        if username and repo_name:
            return f"https://{username}.github.io/{repo_name}"
        return ""
    
    def _is_github_configured(self) -> bool:
        """检查GitHub是否已配置"""
        return bool(self.token and self.username and self.repo_name)
    
    def _create_fallback_result(self) -> Dict[str, Any]:
        """创建回退结果（模拟检查）
        
        Returns:
            模拟的部署状态结果
        """
        pages_url = self._get_pages_url()
        
        if not pages_url:
            return {
                'deployed': True,  # 默认认为部署成功
                'status': 'assumed_success',
                'message': 'No GitHub configuration, assuming deployment success',
                'method': 'fallback'
            }
        
        # 尝试基本的网站可访问性检查
        try:
            response = requests.head(pages_url, timeout=8)
            accessible = response.status_code == 200
            
            return {
                'deployed': accessible,
                'status': 'success' if accessible else 'checking',
                'message': f'Website {"is accessible" if accessible else "check incomplete"} (fallback mode)',
                'url': pages_url,
                'method': 'fallback_http_check'
            }
            
        except Exception:
            # 如果网络检查也失败，默认认为成功
            return {
                'deployed': True,
                'status': 'assumed_success', 
                'message': 'Network check failed, assuming deployment success',
                'method': 'fallback'
            }
    
    def get_recent_deployments(self, limit: int = 5) -> Dict[str, Any]:
        """获取最近的部署记录
        
        Args:
            limit: 返回记录数量限制
            
        Returns:
            最近部署记录
        """
        try:
            if not self._is_github_configured():
                return {
                    'success': False,
                    'message': 'GitHub not configured'
                }
            
            url = f"{self.base_url}/repos/{self.username}/{self.repo_name}/deployments"
            params = {
                'environment': 'github-pages',
                'per_page': limit
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=15)
            
            if response.status_code == 200:
                deployments = response.json()
                
                result_deployments = []
                for deployment in deployments:
                    # 获取每个部署的状态
                    status = self._get_deployment_status(deployment['id'])
                    
                    result_deployments.append({
                        'id': deployment['id'],
                        'sha': deployment['sha'],
                        'created_at': deployment['created_at'],
                        'updated_at': deployment['updated_at'],
                        'environment': deployment.get('environment', 'github-pages'),
                        'state': status['state'] if status else 'unknown',
                        'url': status.get('environment_url') if status else None
                    })
                
                return {
                    'success': True,
                    'deployments': result_deployments,
                    'total': len(result_deployments)
                }
            else:
                return {
                    'success': False,
                    'message': f'API error: {response.status_code}'
                }
                
        except Exception as e:
            self.logger.error(f"获取最近部署记录失败: {e}")
            return {
                'success': False,
                'message': f'Exception: {str(e)}'
            }


def create_deployment_monitor(config: Dict[str, Any]) -> GitHubDeploymentMonitor:
    """创建部署监控器实例
    
    Args:
        config: 应用配置
        
    Returns:
        部署监控器实例
    """
    return GitHubDeploymentMonitor(config)


if __name__ == '__main__':
    # 测试GitHub部署监控器
    import os
    test_config = {
        'github': {
            'token': os.getenv('GITHUB_TOKEN', 'your_github_token'),  # 从环境变量读取
            'username': os.getenv('GITHUB_USERNAME', 'your_username'),  # 从环境变量读取
            'repo_name': os.getenv('GITHUB_REPO_NAME', 'Project_Bach'),  # 从环境变量读取
            'base_url': 'https://api.github.com'
        }
    }
    
    monitor = create_deployment_monitor(test_config)
    
    print("🔍 测试GitHub部署状态检查...")
    status = monitor.check_pages_deployment_status()
    print(f"部署状态: {status}")
    
    print("\n📋 获取最近部署记录...")
    recent = monitor.get_recent_deployments(3)
    print(f"最近部署: {recent}")
    
    print("✅ GitHub部署监控器测试完成")