#!/usr/bin/env python3.11
"""
发布工作流编排服务
协调整个发布流程，包括内容格式化、仓库操作、模板渲染等
"""

import logging
import tempfile
import shutil
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from .github_publisher import GitHubPublisher
from .content_formatter import ContentFormatter
from .git_operations import GitOperations, GitWorkflowManager
from .template_engine import TemplateEngine


class PublishingWorkflow:
    """发布工作流服务"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化发布工作流
        
        Args:
            config: 发布配置
        """
        self.config = config
        self.logger = logging.getLogger('project_bach.publishing_workflow')
        
        # 初始化各个服务组件
        self._init_services()
        
        # 工作目录
        self.temp_dir = None
        self.repo_path = None
        
        self.logger.info("发布工作流服务初始化完成")
    
    def _init_services(self):
        """初始化服务组件"""
        try:
            # 使用SSH方式，跳过GitHub API服务
            self.github_publisher = None  # 不使用GitHub API
            
            # 内容格式化服务
            self.content_formatter = ContentFormatter(self.config.get('publishing', {}))
            
            # Git操作服务 - 使用github配置
            self.git_operations = GitOperations(self.config['github'])
            
            # Git工作流管理器
            self.git_workflow = GitWorkflowManager(
                self.git_operations, 
                self.config.get('workflow', {})
            )
            
            # 模板引擎
            self.template_engine = TemplateEngine(self.config.get('templates', {}))
            
            self.logger.info("所有服务组件初始化成功 (使用SSH模式)")
            
        except Exception as e:
            self.logger.error(f"服务组件初始化失败: {str(e)}")
            raise
    
    def publish_content(self, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """发布单个内容
        
        Args:
            content_data: 音频处理结果数据
            
        Returns:
            发布结果
        """
        self.logger.info(f"开始发布内容: {content_data.get('title', '未知')}")
        
        workflow_steps = []
        
        try:
            # 步骤1: 设置GitHub仓库
            self.logger.info("步骤1: 设置GitHub仓库")
            repo_setup = self.github_publisher.setup_repository_for_publishing()
            workflow_steps.append({
                'step': 'setup_repository',
                'success': repo_setup['success'],
                'message': repo_setup['message']
            })
            
            if not repo_setup['success']:
                return self._build_workflow_result(False, "GitHub仓库设置失败", workflow_steps)
            
            # 步骤2: 格式化内容
            self.logger.info("步骤2: 格式化内容")
            format_result = self.content_formatter.format_content(content_data)
            workflow_steps.append({
                'step': 'format_content',
                'success': format_result['success'],
                'message': '内容格式化完成' if format_result['success'] else format_result.get('error')
            })
            
            if not format_result['success']:
                return self._build_workflow_result(False, "内容格式化失败", workflow_steps)
            
            # 步骤3: 渲染HTML页面
            self.logger.info("步骤3: 渲染HTML页面")
            render_result = self.template_engine.render_content_page(format_result['content'])
            workflow_steps.append({
                'step': 'render_template',
                'success': render_result['success'],
                'message': '模板渲染完成' if render_result['success'] else render_result.get('error')
            })
            
            if not render_result['success']:
                return self._build_workflow_result(False, "模板渲染失败", workflow_steps)
            
            # 步骤4: 准备本地仓库
            self.logger.info("步骤4: 准备本地仓库")
            repo_prep = self._prepare_local_repository(repo_setup['repo_url'])
            workflow_steps.append({
                'step': 'prepare_local_repo',
                'success': repo_prep['success'],
                'message': repo_prep['message']
            })
            
            if not repo_prep['success']:
                return self._build_workflow_result(False, "本地仓库准备失败", workflow_steps)
            
            # 步骤5: 写入文件
            self.logger.info("步骤5: 写入文件到本地仓库")
            files_written = self._write_files_to_repo(
                format_result['content'], 
                render_result['content']
            )
            workflow_steps.append({
                'step': 'write_files',
                'success': len(files_written) > 0,
                'message': f'写入 {len(files_written)} 个文件',
                'files': files_written
            })
            
            # 步骤6: 提交并推送
            self.logger.info("步骤6: 提交并推送到GitHub")
            git_result = self.git_workflow.execute_publish_workflow(
                self.repo_path,
                files_written,
                content_data.get('title', '内容发布')
            )
            workflow_steps.append({
                'step': 'git_workflow',
                'success': git_result['success'],
                'message': git_result['message'],
                'commit_hash': git_result.get('commit_hash')
            })
            
            if not git_result['success']:
                return self._build_workflow_result(False, "Git工作流失败", workflow_steps)
            
            # 构建最终结果
            published_url = self._build_published_url(format_result['content']['filename'])
            
            return self._build_workflow_result(
                True, 
                "内容发布成功", 
                workflow_steps,
                {
                    'published_url': published_url,
                    'pages_url': repo_setup.get('pages_url'),
                    'commit_hash': git_result.get('commit_hash'),
                    'filename': format_result['content']['filename']
                }
            )
            
        except Exception as e:
            self.logger.error(f"发布流程异常: {str(e)}")
            return self._build_workflow_result(False, f"发布异常: {str(e)}", workflow_steps)
        finally:
            self._cleanup_temp_resources()
    
    def _prepare_local_repository(self, repo_url: str) -> Dict[str, Any]:
        """准备本地仓库"""
        try:
            # 创建临时目录
            self.temp_dir = tempfile.mkdtemp(prefix='project_bach_publish_')
            self.repo_path = Path(self.temp_dir) / 'repo'
            
            # 克隆仓库
            clone_result = self.git_operations.clone_repository(
                repo_url, str(self.repo_path), 
                branch=self.config.get('workflow', {}).get('target_branch')
            )
            
            if clone_result['success']:
                return {
                    'success': True,
                    'message': '本地仓库准备完成',
                    'local_path': str(self.repo_path)
                }
            else:
                return {
                    'success': False,
                    'message': f'仓库克隆失败: {clone_result["message"]}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'本地仓库准备异常: {str(e)}'
            }
    
    def _write_files_to_repo(self, content: Dict[str, Any], html_content: str) -> List[str]:
        """写入文件到本地仓库"""
        files_written = []
        
        try:
            # 写入HTML文件
            html_file = self.repo_path / content['filename']
            html_file.write_text(html_content, encoding='utf-8')
            files_written.append(content['filename'])
            
            self.logger.info(f"写入HTML文件: {content['filename']}")
            
            # 可以添加其他文件（如原始Markdown、元数据JSON等）
            
        except Exception as e:
            self.logger.error(f"写入文件失败: {str(e)}")
        
        return files_written
    
    def _build_published_url(self, filename: str) -> str:
        """构建发布后的URL"""
        username = self.config['github']['username']
        repo = self.config['github']['publish_repo']
        return f"https://{username}.github.io/{repo}/{filename}"
    
    def _build_workflow_result(self, success: bool, message: str, steps: List[Dict], extra_data: Optional[Dict] = None) -> Dict[str, Any]:
        """构建工作流结果"""
        result = {
            'success': success,
            'message': message,
            'steps': steps,
            'total_steps': len(steps),
            'completed_steps': sum(1 for s in steps if s['success']),
            'execution_time': datetime.now().isoformat()
        }
        
        if extra_data:
            result.update(extra_data)
        
        return result
    
    def _cleanup_temp_resources(self):
        """清理临时资源"""
        if self.temp_dir and Path(self.temp_dir).exists():
            try:
                shutil.rmtree(self.temp_dir)
                self.logger.debug(f"清理临时目录: {self.temp_dir}")
            except Exception as e:
                self.logger.warning(f"清理临时目录失败: {str(e)}")
        
        self.temp_dir = None
        self.repo_path = None
    
    def deploy_to_github_pages(self) -> Dict[str, Any]:
        """部署到GitHub Pages (需要GitHub SSH配置)
        
        Returns:
            部署结果字典
        """
        try:
            self.logger.info("检查GitHub Pages部署条件")
            
            # 获取output文件夹的所有结果文件
            output_path = Path(self.config.get('paths', {}).get('output_folder', './data/output'))
            if not output_path.exists():
                return {'success': False, 'error': '输出文件夹不存在'}
            
            result_files = list(output_path.glob('*.md'))
            if not result_files:
                return {'success': False, 'error': '没有找到待发布的结果文件'}
            
            self.logger.info(f"找到 {len(result_files)} 个结果文件待发布")
            
            # 检查GitHub SSH配置是否可用
            ssh_test_result = self._test_github_ssh_access()
            if not ssh_test_result['success']:
                self.logger.warning("⚠️  GitHub SSH访问未配置或不可用")
                github_config = self.config['github']
                username = github_config['username']  
                repo_name = github_config['repo_name']
                return {
                    'success': False,
                    'error': 'GitHub SSH访问未配置，无法自动部署',
                    'files_ready': len(result_files),
                    'setup_required': True,
                    'instructions': f'请先配置GitHub SSH密钥访问 {username}/{repo_name} 仓库'
                }
            
            # 实现真正的GitHub Pages部署逻辑
            self.logger.info("🚀 开始执行GitHub Pages部署")
            return self._execute_github_pages_deployment(result_files)
            
        except Exception as e:
            self.logger.error(f"部署检查失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _test_github_ssh_access(self) -> Dict[str, Any]:
        """测试GitHub SSH访问
        
        Returns:
            SSH测试结果
        """
        try:
            import subprocess
            
            # 测试SSH连接到GitHub
            result = subprocess.run(
                ['ssh', '-T', 'git@github.com', '-o', 'ConnectTimeout=10'],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            # GitHub SSH测试成功时返回码为1，错误信息包含用户名
            if result.returncode == 1 and 'successfully authenticated' in result.stderr:
                return {'success': True, 'message': 'GitHub SSH访问正常'}
            else:
                return {'success': False, 'message': 'GitHub SSH访问失败'}
                
        except Exception as e:
            return {'success': False, 'message': f'SSH测试异常: {str(e)}'}
    
    def _execute_github_pages_deployment(self, result_files: List[Path]) -> Dict[str, Any]:
        """执行GitHub Pages部署
        
        Args:
            result_files: 待部署的结果文件列表
            
        Returns:
            部署结果字典
        """
        import subprocess
        import tempfile
        import shutil
        from datetime import datetime
        
        try:
            github_config = self.config['github']
            username = github_config['username']
            repo_name = github_config['repo_name']
            pages_branch = github_config.get('pages_branch', 'gh-pages')
            remote_url = github_config.get('remote_url', f'git@github.com:{username}/{repo_name}.git')
            
            # 创建临时工作目录
            with tempfile.TemporaryDirectory() as temp_dir:
                self.logger.info(f"使用临时目录: {temp_dir}")
                
                # 1. 克隆gh-pages分支到临时目录
                self.logger.info(f"克隆 {pages_branch} 分支...")
                clone_cmd = ['git', 'clone', '-b', pages_branch, '--single-branch', remote_url, temp_dir]
                result = subprocess.run(clone_cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode != 0:
                    return {
                        'success': False,
                        'error': f'克隆{pages_branch}分支失败: {result.stderr}',
                        'files_ready': len(result_files)
                    }
                
                # 2. 设置Git配置
                user_config = self.git_operations._check_git_user_config()
                git_config_cmds = [
                    ['git', 'config', 'user.name', user_config['name']],
                    ['git', 'config', 'user.email', user_config['email']]
                ]
                
                for cmd in git_config_cmds:
                    subprocess.run(cmd, cwd=temp_dir, timeout=10)
                
                # 3. 复制结果文件到临时目录
                self.logger.info(f"复制 {len(result_files)} 个结果文件...")
                copied_files = []
                for result_file in result_files:
                    target_path = Path(temp_dir) / result_file.name
                    shutil.copy2(result_file, target_path)
                    copied_files.append(result_file.name)
                    self.logger.debug(f"复制文件: {result_file.name}")
                
                # 4. 更新index.html（如果需要）
                self._update_index_html(Path(temp_dir), copied_files)
                
                # 5. 检查是否有更改
                status_cmd = ['git', 'status', '--porcelain']
                result = subprocess.run(status_cmd, cwd=temp_dir, capture_output=True, text=True)
                
                if not result.stdout.strip():
                    self.logger.info("没有新的更改需要部署")
                    return {
                        'success': True,
                        'message': '没有新的更改需要部署',
                        'files_ready': len(result_files),
                        'website_url': f"https://{username}.github.io/{repo_name}"
                    }
                
                # 6. 添加并提交更改
                add_cmd = ['git', 'add', '.']
                subprocess.run(add_cmd, cwd=temp_dir, timeout=30)
                
                commit_message = f"🤖 Auto-deploy: {len(copied_files)} new audio results ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
                commit_cmd = ['git', 'commit', '-m', commit_message]
                result = subprocess.run(commit_cmd, cwd=temp_dir, capture_output=True, text=True)
                
                if result.returncode != 0:
                    return {
                        'success': False,
                        'error': f'提交失败: {result.stderr}',
                        'files_ready': len(result_files)
                    }
                
                # 7. 推送到GitHub
                self.logger.info("推送到GitHub...")
                push_cmd = ['git', 'push', 'origin', pages_branch]
                result = subprocess.run(push_cmd, cwd=temp_dir, capture_output=True, text=True, timeout=120)
                
                if result.returncode != 0:
                    return {
                        'success': False,
                        'error': f'推送失败: {result.stderr}',
                        'files_ready': len(result_files)
                    }
                
                self.logger.info("✅ GitHub Pages部署成功!")
                return {
                    'success': True,
                    'message': f'成功部署 {len(copied_files)} 个音频结果',
                    'files_deployed': copied_files,
                    'website_url': f"https://{username}.github.io/{repo_name}",
                    'commit_message': commit_message
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Git操作超时',
                'files_ready': len(result_files)
            }
        except Exception as e:
            self.logger.error(f"部署执行失败: {str(e)}")
            return {
                'success': False,
                'error': f'部署执行失败: {str(e)}',
                'files_ready': len(result_files)
            }
    
    def _update_index_html(self, temp_dir: Path, new_files: List[str]):
        """更新index.html文件
        
        Args:
            temp_dir: 临时工作目录
            new_files: 新添加的文件列表
        """
        try:
            index_path = temp_dir / 'index.html'
            
            # 如果index.html不存在，创建一个简单的
            if not index_path.exists():
                self.logger.info("创建index.html")
                github_config = self.config['github']
                username = github_config['username']
                
                html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Bach - Audio Processing Results</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
        .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
        .file-list {{ margin-top: 20px; }}
        .file-item {{ margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Project Bach - Audio Processing Results</h1>
        <p>AI-powered audio processing results generated automatically.</p>
        
        <div class="file-list">
            <h2>Latest Results:</h2>
            <!-- Results will be listed here -->
        </div>
        
        <footer style="margin-top: 40px; text-align: center; color: #666;">
            <p>Generated by Project Bach | {username}</p>
        </footer>
    </div>
</body>
</html>"""
                
                with open(index_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
            
            self.logger.debug(f"Index.html updated with {len(new_files)} new files")
            
        except Exception as e:
            self.logger.warning(f"更新index.html失败: {e}")
    
    def get_publish_status(self) -> Dict[str, Any]:
        """获取发布状态 (SSH模式)"""
        try:
            return {
                'github_ssh_mode': True,
                'services_ready': all([
                    hasattr(self, 'content_formatter'),
                    hasattr(self, 'git_operations'),
                    hasattr(self, 'template_engine')
                ])
            }
        except Exception as e:
            return {
                'error': f'状态检查失败: {str(e)}'
            }


if __name__ == '__main__':
    # 测试发布工作流
    test_config = {
        'github': {
            'token': 'test_token',
            'username': 'testuser',
            'publish_repo': 'project-bach-site',
            'pages_branch': 'gh-pages'
        },
        'publishing': {
            'template_dir': './test_templates',
            'site_title': 'Project Bach 测试',
            'site_description': 'AI音频处理结果发布测试'
        },
        'git': {
            'user_name': 'Project Bach Bot',
            'user_email': 'bot@project-bach.com',
        },
        'workflow': {
            'target_branch': 'gh-pages',
            'auto_push': True
        }
    }
    
    try:
        workflow = PublishingWorkflow(test_config)
        print("✅ 发布工作流初始化成功")
        
        # 检查状态
        status = workflow.get_publish_status()
        print(f"服务就绪: {status.get('services_ready', False)}")
        
    except Exception as e:
        print(f"❌ 发布工作流初始化失败: {e}")
    
    print("✅ 发布工作流测试完成")