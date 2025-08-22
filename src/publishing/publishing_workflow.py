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
            # GitHub发布服务
            self.github_publisher = GitHubPublisher(self.config['github'])
            
            # 内容格式化服务
            self.content_formatter = ContentFormatter(self.config['publishing'])
            
            # Git操作服务
            self.git_operations = GitOperations(self.config['git'])
            
            # Git工作流管理器
            self.git_workflow = GitWorkflowManager(
                self.git_operations, 
                self.config.get('workflow', {})
            )
            
            # 模板引擎
            self.template_engine = TemplateEngine(self.config['publishing'])
            
            self.logger.info("所有服务组件初始化成功")
            
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
    
    def get_publish_status(self) -> Dict[str, Any]:
        """获取发布状态"""
        try:
            # 检查GitHub仓库状态
            repo_status = self.github_publisher.check_repository_status()
            
            # 检查模板文件
            template_validation = self.template_engine.validate_template_files()
            
            return {
                'github_repo': repo_status,
                'templates': template_validation,
                'services_ready': all([
                    hasattr(self, 'github_publisher'),
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