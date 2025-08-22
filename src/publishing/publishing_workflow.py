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
            
            # 获取output文件夹的public子目录的所有结果文件
            output_path = Path(self.config.get('paths', {}).get('output_folder', './data/output'))
            public_output_path = output_path / 'public'
            
            if not output_path.exists():
                return {'success': False, 'error': '输出文件夹不存在'}
            
            if not public_output_path.exists():
                return {'success': False, 'error': 'public输出文件夹不存在'}
            
            result_files = list(public_output_path.glob('*.md'))
            if not result_files:
                return {'success': False, 'error': '没有找到待发布的public结果文件'}
            
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
                
                # 3. 为每个结果文件生成HTML页面
                self.logger.info(f"为 {len(result_files)} 个结果文件生成HTML页面...")
                generated_files = []
                result_metadata = []
                
                for result_file in result_files:
                    # 解析Markdown文件内容
                    content_data = self._parse_markdown_result(result_file)
                    if content_data:
                        # 使用模板引擎生成HTML
                        html_result = self.template_engine.render_content_page(content_data)
                        if html_result['success']:
                            # 写入HTML文件到临时目录
                            html_filename = result_file.stem + '.html'
                            html_path = Path(temp_dir) / html_filename
                            html_path.write_text(html_result['content'], encoding='utf-8')
                            generated_files.append(html_filename)
                            
                            # 保存元数据用于index页面
                            result_metadata.append({
                                'title': content_data.get('title', '未命名'),
                                'file': html_filename,
                                'date': content_data.get('processed_time', ''),
                                'summary': content_data.get('summary', '')[:100] + '...' if content_data.get('summary') else ''
                            })
                            
                            self.logger.debug(f"生成HTML文件: {html_filename}")
                        else:
                            self.logger.warning(f"模板渲染失败: {result_file.name}")
                    else:
                        self.logger.warning(f"解析失败: {result_file.name}")
                
                # 4. 生成并更新index.html页面
                self._generate_index_html(Path(temp_dir), result_metadata)
                
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
                
                commit_message = f"🤖 Auto-deploy: {len(generated_files)} new audio results ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
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
                    'message': f'成功部署 {len(generated_files)} 个音频结果HTML页面',
                    'files_deployed': generated_files,
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
    
    def _parse_markdown_result(self, result_file: Path) -> Optional[Dict[str, Any]]:
        """解析Markdown结果文件，提取内容用于HTML生成
        
        Args:
            result_file: 结果文件路径
            
        Returns:
            解析后的内容数据，失败返回None
        """
        try:
            content = result_file.read_text(encoding='utf-8')
            
            # 简单解析Markdown格式的结果文件
            lines = content.split('\n')
            data = {
                'title': '未命名',
                'processed_time': '',
                'original_file': '',
                'summary': '',
                'mindmap': '',
                'anonymized_names': {}
            }
            
            current_section = None
            content_lines = []
            
            for line in lines:
                line = line.strip()
                
                if line.startswith('# '):
                    data['title'] = line[2:]
                elif line.startswith('**处理时间**:'):
                    data['processed_time'] = line.split(':', 1)[1].strip()
                elif line.startswith('**原始文件**:'):
                    data['original_file'] = line.split(':', 1)[1].strip()
                elif line.startswith('## 内容摘要'):
                    current_section = 'summary'
                    content_lines = []
                elif line.startswith('## 思维导图'):
                    if current_section == 'summary':
                        data['summary'] = '\n'.join(content_lines).strip()
                    current_section = 'mindmap'
                    content_lines = []
                elif line.startswith('## '):
                    # 保存当前部分
                    if current_section == 'summary':
                        data['summary'] = '\n'.join(content_lines).strip()
                    elif current_section == 'mindmap':
                        data['mindmap'] = '\n'.join(content_lines).strip()
                    current_section = None
                    content_lines = []
                elif current_section:
                    content_lines.append(line)
            
            # 保存最后一个部分
            if current_section == 'summary':
                data['summary'] = '\n'.join(content_lines).strip()
            elif current_section == 'mindmap':
                data['mindmap'] = '\n'.join(content_lines).strip()
            
            return data
            
        except Exception as e:
            self.logger.error(f"解析Markdown文件失败 {result_file}: {e}")
            return None
    
    def _generate_index_html(self, temp_dir: Path, result_metadata: List[Dict[str, Any]]):
        """生成index.html页面
        
        Args:
            temp_dir: 临时工作目录
            result_metadata: 结果元数据列表
        """
        try:
            # 使用模板引擎生成index页面
            stats = {
                'this_month': len(result_metadata),
                'this_week': len(result_metadata)
            }
            
            index_result = self.template_engine.render_index_page(result_metadata, stats)
            if index_result['success']:
                index_path = temp_dir / 'index.html'
                index_path.write_text(index_result['content'], encoding='utf-8')
                self.logger.info(f"生成index.html页面，包含 {len(result_metadata)} 个结果")
            else:
                # 如果模板渲染失败，创建简单的HTML页面
                self._create_simple_index_html(temp_dir, result_metadata)
                
        except Exception as e:
            self.logger.warning(f"生成index.html失败，使用简单版本: {e}")
            self._create_simple_index_html(temp_dir, result_metadata)
    
    def _create_simple_index_html(self, temp_dir: Path, result_metadata: List[Dict[str, Any]]):
        """创建简单的index.html页面
        
        Args:
            temp_dir: 临时工作目录
            result_metadata: 结果元数据列表
        """
        try:
            github_config = self.config['github']
            username = github_config['username']
            
            results_html = ""
            for result in result_metadata:
                results_html += f"""
                <div class="file-item">
                    <h3><a href="{result['file']}">{result['title']}</a></h3>
                    <p><small>{result['date']}</small></p>
                    <p>{result['summary']}</p>
                </div>
                """
            
            html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Bach - Audio Processing Results</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        .file-list {{ margin-top: 20px; }}
        .file-item {{ margin: 15px 0; padding: 15px; border: 1px solid #ddd; border-radius: 8px; background: #f9f9f9; }}
        .file-item h3 {{ margin: 0 0 10px 0; }}
        .file-item a {{ color: #007AFF; text-decoration: none; }}
        .file-item a:hover {{ text-decoration: underline; }}
        footer {{ margin-top: 40px; text-align: center; color: #666; border-top: 1px solid #eee; padding-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎵 Project Bach - 音频处理结果</h1>
        <p>AI智能音频处理与内容分析平台，共收录 <strong>{len(result_metadata)}</strong> 个处理结果。</p>
        
        <div class="file-list">
            <h2>📋 最新结果</h2>
            {results_html}
        </div>
        
        <footer>
            <p><strong>Project Bach</strong> - AI音频处理与内容分析</p>
            <p>Generated by Project Bach | {username}</p>
        </footer>
    </div>
</body>
</html>"""
            
            index_path = temp_dir / 'index.html'
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.logger.info(f"创建简单index.html页面，包含 {len(result_metadata)} 个结果")
            
        except Exception as e:
            self.logger.error(f"创建简单index.html失败: {e}")
    
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