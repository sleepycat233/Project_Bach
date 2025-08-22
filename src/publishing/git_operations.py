#!/usr/bin/env python3.11
"""
Git操作服务
封装Git命令操作，支持仓库管理、提交、推送等功能
"""

import subprocess
import logging
import os
import shutil
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime


class GitOperations:
    """Git操作服务"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化Git操作服务
        
        Args:
            config: Git配置
        """
        self.config = config
        self.logger = logging.getLogger('project_bach.git_operations')
        
        # Git配置
        self.remote_name = config.get('remote_name', 'origin')
        self.commit_message_template = config.get('commit_message_template', '🤖 Auto-publish: {title}')
        
        # 检查并设置Git用户信息（如果系统没有设置的话）
        self.default_user_name = config.get('default_user_name', 'Project Bach Bot')
        self.default_user_email = config.get('default_user_email', 'bot@project-bach.com')
        
        # 超时配置
        self.default_timeout = config.get('timeout', 300)  # 5分钟
        self.clone_timeout = config.get('clone_timeout', 600)  # 10分钟
        
        self.logger.info("Git操作服务初始化完成")
    
    def _check_git_user_config(self) -> Dict[str, str]:
        """检查Git全局用户配置
        
        Returns:
            包含用户名和邮箱的字典
        """
        user_config = {}
        
        try:
            # 检查全局用户名
            result = subprocess.run(
                ['git', 'config', '--global', 'user.name'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                user_config['name'] = result.stdout.strip()
            else:
                user_config['name'] = self.default_user_name
                self.logger.info(f"未找到全局Git用户名，使用默认值: {self.default_user_name}")
            
            # 检查全局邮箱
            result = subprocess.run(
                ['git', 'config', '--global', 'user.email'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                user_config['email'] = result.stdout.strip()
            else:
                user_config['email'] = self.default_user_email
                self.logger.info(f"未找到全局Git邮箱，使用默认值: {self.default_user_email}")
                
        except Exception as e:
            self.logger.warning(f"检查Git全局配置失败: {e}，使用默认值")
            user_config['name'] = self.default_user_name
            user_config['email'] = self.default_user_email
        
        return user_config
    
    def clone_repository(self, repo_url: str, local_path: str, branch: Optional[str] = None) -> Dict[str, Any]:
        """克隆Git仓库
        
        Args:
            repo_url: 仓库URL
            local_path: 本地路径
            branch: 指定分支（可选）
            
        Returns:
            克隆结果
        """
        self.logger.info(f"克隆仓库: {repo_url} -> {local_path}")
        
        try:
            # 如果目标目录已存在，先删除
            if os.path.exists(local_path):
                self.logger.warning(f"目标目录已存在，删除: {local_path}")
                shutil.rmtree(local_path)
            
            # 构建克隆命令
            cmd = ['git', 'clone', repo_url, local_path]
            
            if branch:
                cmd.extend(['--branch', branch])
                self.logger.info(f"指定克隆分支: {branch}")
            
            # 执行克隆
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.clone_timeout,
                cwd=None
            )
            
            if result.returncode == 0:
                self.logger.info(f"仓库克隆成功: {local_path}")
                
                # 配置本地仓库
                config_result = self._configure_local_repo(local_path)
                
                return {
                    'success': True,
                    'local_path': local_path,
                    'branch': branch or 'default',
                    'message': '仓库克隆成功',
                    'config_applied': config_result['success']
                }
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                self.logger.error(f"仓库克隆失败: {error_msg}")
                
                return {
                    'success': False,
                    'message': f'克隆失败: {error_msg}',
                    'stderr': result.stderr,
                    'stdout': result.stdout
                }
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"克隆超时（{self.clone_timeout}秒）")
            return {
                'success': False,
                'message': f'克隆超时（{self.clone_timeout}秒）'
            }
        except Exception as e:
            self.logger.error(f"克隆异常: {str(e)}")
            return {
                'success': False,
                'message': f'克隆异常: {str(e)}'
            }
    
    def _configure_local_repo(self, repo_path: str) -> Dict[str, Any]:
        """配置本地仓库
        
        Args:
            repo_path: 仓库路径
            
        Returns:
            配置结果
        """
        try:
            # 检查并配置Git用户信息
            user_config = self._check_git_user_config()
            
            # 配置Git设置
            config_commands = [
                ['git', 'config', 'user.name', user_config['name']],
                ['git', 'config', 'user.email', user_config['email']],
                ['git', 'config', 'core.autocrlf', 'input'],  # 处理换行符
                ['git', 'config', 'core.safecrlf', 'warn'],
            ]
            
            for cmd in config_commands:
                result = subprocess.run(
                    cmd,
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode != 0:
                    self.logger.warning(f"配置命令失败: {' '.join(cmd)} - {result.stderr}")
            
            self.logger.info(f"本地仓库配置完成: {self.user_name} <{self.user_email}>")
            return {'success': True}
            
        except Exception as e:
            self.logger.error(f"仓库配置失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def add_files(self, repo_path: str, files: Optional[List[str]] = None) -> Dict[str, Any]:
        """添加文件到Git暂存区
        
        Args:
            repo_path: 仓库路径
            files: 文件列表，None表示添加所有文件
            
        Returns:
            添加结果
        """
        try:
            if files is None or files == []:
                # 添加所有文件
                cmd = ['git', 'add', '.']
                self.logger.info("添加所有文件到暂存区")
            else:
                # 添加指定文件
                cmd = ['git', 'add'] + files
                self.logger.info(f"添加指定文件到暂存区: {files}")
            
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                # 检查暂存区状态
                status_result = self.get_status(repo_path)
                
                return {
                    'success': True,
                    'message': '文件添加成功',
                    'staged_files': status_result.get('staged_files', [])
                }
            else:
                error_msg = result.stderr.strip()
                self.logger.error(f"文件添加失败: {error_msg}")
                
                return {
                    'success': False,
                    'message': f'文件添加失败: {error_msg}',
                    'stderr': result.stderr
                }
                
        except Exception as e:
            self.logger.error(f"文件添加异常: {str(e)}")
            return {
                'success': False,
                'message': f'文件添加异常: {str(e)}'
            }
    
    def commit_changes(self, repo_path: str, message: str, allow_empty: bool = False) -> Dict[str, Any]:
        """提交更改
        
        Args:
            repo_path: 仓库路径
            message: 提交消息
            allow_empty: 是否允许空提交
            
        Returns:
            提交结果
        """
        self.logger.info(f"提交更改: {message}")
        
        try:
            # 构建提交命令
            cmd = ['git', 'commit', '-m', message]
            
            if allow_empty:
                cmd.append('--allow-empty')
            
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                # 获取提交哈希
                commit_hash = self._get_latest_commit_hash(repo_path)
                
                self.logger.info(f"提交成功: {commit_hash}")
                
                return {
                    'success': True,
                    'commit_hash': commit_hash,
                    'message': '提交成功',
                    'commit_message': message
                }
            else:
                # 检查是否是"没有更改"的情况
                if "nothing to commit" in result.stdout:
                    self.logger.info("没有需要提交的更改")
                    return {
                        'success': True,
                        'message': '没有需要提交的更改',
                        'no_changes': True
                    }
                
                error_msg = result.stderr.strip() or result.stdout.strip()
                self.logger.error(f"提交失败: {error_msg}")
                
                return {
                    'success': False,
                    'message': f'提交失败: {error_msg}',
                    'stderr': result.stderr,
                    'stdout': result.stdout
                }
                
        except Exception as e:
            self.logger.error(f"提交异常: {str(e)}")
            return {
                'success': False,
                'message': f'提交异常: {str(e)}'
            }
    
    def push_to_remote(self, repo_path: str, branch: str, remote: Optional[str] = None, force: bool = False) -> Dict[str, Any]:
        """推送到远程仓库
        
        Args:
            repo_path: 仓库路径
            branch: 分支名
            remote: 远程名（默认使用配置的remote_name）
            force: 是否强制推送
            
        Returns:
            推送结果
        """
        remote = remote or self.remote_name
        self.logger.info(f"推送到远程: {remote}/{branch}")
        
        try:
            # 构建推送命令
            cmd = ['git', 'push', remote, branch]
            
            if force:
                cmd.append('--force')
                self.logger.warning("使用强制推送")
            
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=self.default_timeout
            )
            
            if result.returncode == 0:
                self.logger.info(f"推送成功: {remote}/{branch}")
                
                return {
                    'success': True,
                    'message': '推送成功',
                    'remote': remote,
                    'branch': branch,
                    'forced': force
                }
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                self.logger.error(f"推送失败: {error_msg}")
                
                return {
                    'success': False,
                    'message': f'推送失败: {error_msg}',
                    'stderr': result.stderr,
                    'stdout': result.stdout,
                    'remote': remote,
                    'branch': branch
                }
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"推送超时（{self.default_timeout}秒）")
            return {
                'success': False,
                'message': f'推送超时（{self.default_timeout}秒）'
            }
        except Exception as e:
            self.logger.error(f"推送异常: {str(e)}")
            return {
                'success': False,
                'message': f'推送异常: {str(e)}'
            }
    
    def create_branch(self, repo_path: str, branch_name: str, checkout: bool = True) -> Dict[str, Any]:
        """创建新分支
        
        Args:
            repo_path: 仓库路径
            branch_name: 分支名
            checkout: 是否切换到新分支
            
        Returns:
            创建结果
        """
        self.logger.info(f"创建分支: {branch_name}")
        
        try:
            # 检查分支是否已存在
            existing_branches = self._list_branches(repo_path)
            if branch_name in existing_branches['local']:
                self.logger.info(f"分支已存在: {branch_name}")
                
                if checkout:
                    # 切换到已存在的分支
                    checkout_result = self.checkout_branch(repo_path, branch_name)
                    return {
                        'success': True,
                        'message': f'分支已存在，已切换: {branch_name}',
                        'branch': branch_name,
                        'created': False,
                        'checkout_success': checkout_result['success']
                    }
                else:
                    return {
                        'success': True,
                        'message': f'分支已存在: {branch_name}',
                        'branch': branch_name,
                        'created': False
                    }
            
            # 创建新分支
            if checkout:
                cmd = ['git', 'checkout', '-b', branch_name]
            else:
                cmd = ['git', 'branch', branch_name]
            
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.logger.info(f"分支创建成功: {branch_name}")
                
                return {
                    'success': True,
                    'message': f'分支创建成功: {branch_name}',
                    'branch': branch_name,
                    'created': True,
                    'checked_out': checkout
                }
            else:
                error_msg = result.stderr.strip()
                self.logger.error(f"分支创建失败: {error_msg}")
                
                return {
                    'success': False,
                    'message': f'分支创建失败: {error_msg}',
                    'stderr': result.stderr
                }
                
        except Exception as e:
            self.logger.error(f"分支创建异常: {str(e)}")
            return {
                'success': False,
                'message': f'分支创建异常: {str(e)}'
            }
    
    def checkout_branch(self, repo_path: str, branch_name: str) -> Dict[str, Any]:
        """切换分支
        
        Args:
            repo_path: 仓库路径
            branch_name: 分支名
            
        Returns:
            切换结果
        """
        self.logger.info(f"切换分支: {branch_name}")
        
        try:
            cmd = ['git', 'checkout', branch_name]
            
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                current_branch = self._get_current_branch(repo_path)
                
                return {
                    'success': True,
                    'message': f'分支切换成功: {branch_name}',
                    'branch': current_branch,
                    'target_branch': branch_name
                }
            else:
                error_msg = result.stderr.strip()
                self.logger.error(f"分支切换失败: {error_msg}")
                
                return {
                    'success': False,
                    'message': f'分支切换失败: {error_msg}',
                    'stderr': result.stderr
                }
                
        except Exception as e:
            self.logger.error(f"分支切换异常: {str(e)}")
            return {
                'success': False,
                'message': f'分支切换异常: {str(e)}'
            }
    
    def get_status(self, repo_path: str) -> Dict[str, Any]:
        """获取仓库状态
        
        Args:
            repo_path: 仓库路径
            
        Returns:
            仓库状态信息
        """
        try:
            # 获取状态信息
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # 解析状态输出
                status_lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
                
                staged_files = []
                unstaged_files = []
                untracked_files = []
                
                for line in status_lines:
                    if len(line) >= 3:
                        status_code = line[:2]
                        filename = line[3:]
                        
                        if status_code[0] in 'MADRC':  # 暂存区有变化
                            staged_files.append(filename)
                        if status_code[1] in 'MADRC':  # 工作区有变化
                            unstaged_files.append(filename)
                        if status_code == '??':  # 未跟踪文件
                            untracked_files.append(filename)
                
                # 获取当前分支
                current_branch = self._get_current_branch(repo_path)
                
                return {
                    'success': True,
                    'current_branch': current_branch,
                    'staged_files': staged_files,
                    'unstaged_files': unstaged_files,
                    'untracked_files': untracked_files,
                    'clean': len(status_lines) == 0
                }
            else:
                return {
                    'success': False,
                    'message': '获取状态失败',
                    'stderr': result.stderr
                }
                
        except Exception as e:
            self.logger.error(f"获取状态异常: {str(e)}")
            return {
                'success': False,
                'message': f'获取状态异常: {str(e)}'
            }
    
    def _get_current_branch(self, repo_path: str) -> str:
        """获取当前分支名
        
        Args:
            repo_path: 仓库路径
            
        Returns:
            分支名
        """
        try:
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return 'unknown'
                
        except Exception:
            return 'unknown'
    
    def _get_latest_commit_hash(self, repo_path: str) -> str:
        """获取最新提交哈希
        
        Args:
            repo_path: 仓库路径
            
        Returns:
            提交哈希
        """
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return result.stdout.strip()[:8]  # 返回短哈希
            else:
                return 'unknown'
                
        except Exception:
            return 'unknown'
    
    def _list_branches(self, repo_path: str) -> Dict[str, List[str]]:
        """列出所有分支
        
        Args:
            repo_path: 仓库路径
            
        Returns:
            分支列表
        """
        try:
            # 本地分支
            local_result = subprocess.run(
                ['git', 'branch', '--format=%(refname:short)'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            local_branches = []
            if local_result.returncode == 0:
                local_branches = [b.strip() for b in local_result.stdout.strip().split('\n') if b.strip()]
            
            # 远程分支
            remote_result = subprocess.run(
                ['git', 'branch', '-r', '--format=%(refname:short)'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            remote_branches = []
            if remote_result.returncode == 0:
                remote_branches = [b.strip() for b in remote_result.stdout.strip().split('\n') if b.strip()]
            
            return {
                'local': local_branches,
                'remote': remote_branches
            }
            
        except Exception:
            return {
                'local': [],
                'remote': []
            }
    
    def create_commit_message(self, title: str, additional_info: Optional[str] = None) -> str:
        """创建提交消息
        
        Args:
            title: 内容标题
            additional_info: 额外信息
            
        Returns:
            格式化的提交消息
        """
        # 使用配置的模板
        base_message = self.commit_message_template.format(title=title)
        
        # 添加额外信息
        if additional_info:
            base_message += f"\n\n{additional_info}"
        
        # 添加时间戳
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        base_message += f"\n\nGenerated at: {timestamp}"
        
        return base_message
    
    def setup_git_credentials(self, repo_path: str, token: Optional[str] = None) -> Dict[str, Any]:
        """设置Git认证
        
        Args:
            repo_path: 仓库路径
            token: GitHub Token（可选）
            
        Returns:
            设置结果
        """
        try:
            if token:
                # 设置GitHub Token认证
                result = subprocess.run(
                    ['git', 'config', 'credential.helper', 'store'],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    self.logger.info("Git认证配置成功")
                    return {'success': True, 'method': 'token'}
                else:
                    self.logger.warning("Git认证配置失败")
                    return {'success': False, 'error': result.stderr}
            else:
                self.logger.info("未提供认证信息，使用默认配置")
                return {'success': True, 'method': 'default'}
                
        except Exception as e:
            self.logger.error(f"认证配置异常: {str(e)}")
            return {'success': False, 'error': str(e)}


class GitWorkflowManager:
    """Git工作流管理器"""
    
    def __init__(self, git_ops: GitOperations, config: Dict[str, Any]):
        """初始化工作流管理器
        
        Args:
            git_ops: Git操作服务
            config: 工作流配置
        """
        self.git_ops = git_ops
        self.config = config
        self.logger = logging.getLogger('project_bach.git_workflow')
        
        # 工作流配置
        self.target_branch = config.get('target_branch', 'gh-pages')
        self.auto_create_branch = config.get('auto_create_branch', True)
        self.auto_push = config.get('auto_push', True)
        
    def execute_publish_workflow(self, repo_path: str, files_to_add: List[str], commit_title: str) -> Dict[str, Any]:
        """执行发布工作流
        
        完整的发布流程：
        1. 检查/切换到目标分支
        2. 添加文件
        3. 提交更改
        4. 推送到远程
        
        Args:
            repo_path: 仓库路径
            files_to_add: 要添加的文件列表
            commit_title: 提交标题
            
        Returns:
            工作流执行结果
        """
        self.logger.info(f"执行发布工作流: {commit_title}")
        
        workflow_steps = []
        
        try:
            # 步骤1: 检查/切换分支
            self.logger.info(f"步骤1: 切换到目标分支 {self.target_branch}")
            
            if self.auto_create_branch:
                branch_result = self.git_ops.create_branch(repo_path, self.target_branch, checkout=True)
            else:
                branch_result = self.git_ops.checkout_branch(repo_path, self.target_branch)
            
            workflow_steps.append({
                'step': 'switch_branch',
                'success': branch_result['success'],
                'message': branch_result['message'],
                'branch': self.target_branch
            })
            
            if not branch_result['success']:
                return {
                    'success': False,
                    'message': f'分支操作失败: {branch_result["message"]}',
                    'steps': workflow_steps
                }
            
            # 步骤2: 添加文件
            self.logger.info("步骤2: 添加文件到暂存区")
            add_result = self.git_ops.add_files(repo_path, files_to_add)
            
            workflow_steps.append({
                'step': 'add_files',
                'success': add_result['success'],
                'message': add_result['message'],
                'files_count': len(add_result.get('staged_files', []))
            })
            
            if not add_result['success']:
                return {
                    'success': False,
                    'message': f'文件添加失败: {add_result["message"]}',
                    'steps': workflow_steps
                }
            
            # 步骤3: 提交更改
            self.logger.info("步骤3: 提交更改")
            commit_message = self.git_ops.create_commit_message(commit_title, f"发布文件: {len(files_to_add)} 个")
            commit_result = self.git_ops.commit_changes(repo_path, commit_message)
            
            workflow_steps.append({
                'step': 'commit_changes',
                'success': commit_result['success'],
                'message': commit_result['message'],
                'commit_hash': commit_result.get('commit_hash'),
                'no_changes': commit_result.get('no_changes', False)
            })
            
            if not commit_result['success'] and not commit_result.get('no_changes'):
                return {
                    'success': False,
                    'message': f'提交失败: {commit_result["message"]}',
                    'steps': workflow_steps
                }
            
            # 步骤4: 推送到远程（如果启用）
            if self.auto_push and not commit_result.get('no_changes'):
                self.logger.info("步骤4: 推送到远程")
                push_result = self.git_ops.push_to_remote(repo_path, self.target_branch)
                
                workflow_steps.append({
                    'step': 'push_to_remote',
                    'success': push_result['success'],
                    'message': push_result['message'],
                    'remote': push_result.get('remote'),
                    'branch': push_result.get('branch')
                })
                
                if not push_result['success']:
                    return {
                        'success': False,
                        'message': f'推送失败: {push_result["message"]}',
                        'steps': workflow_steps
                    }
            elif commit_result.get('no_changes'):
                workflow_steps.append({
                    'step': 'push_to_remote',
                    'success': True,
                    'message': '没有更改需要推送',
                    'skipped': True
                })
            
            # 工作流完成
            return {
                'success': True,
                'message': '发布工作流执行成功',
                'steps': workflow_steps,
                'commit_hash': commit_result.get('commit_hash'),
                'no_changes': commit_result.get('no_changes', False)
            }
            
        except Exception as e:
            self.logger.error(f"工作流执行异常: {str(e)}")
            return {
                'success': False,
                'message': f'工作流执行异常: {str(e)}',
                'steps': workflow_steps
            }


if __name__ == '__main__':
    # 测试Git操作服务
    test_config = {
        'user_name': 'Project Bach Bot',
        'user_email': 'bot@project-bach.com',
        'remote_name': 'origin',
        'commit_message_template': '🤖 Auto-publish: {title}',
        'timeout': 300
    }
    
    git_ops = GitOperations(test_config)
    
    # 测试提交消息生成
    test_message = git_ops.create_commit_message('测试音频结果', '包含摘要和思维导图')
    print(f"生成的提交消息:\n{test_message}")
    
    # 测试工作流管理器
    workflow_config = {
        'target_branch': 'gh-pages',
        'auto_create_branch': True,
        'auto_push': True
    }
    
    workflow_manager = GitWorkflowManager(git_ops, workflow_config)
    print(f"工作流管理器初始化完成，目标分支: {workflow_manager.target_branch}")
    
    print("✅ Git操作服务测试完成")