#!/usr/bin/env python3.11
"""
GitHub Actions管理器
负责CI/CD工作流配置、监控和管理
"""

import logging
import requests
import yaml
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path


class GitHubActionsManager:
    """GitHub Actions管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化GitHub Actions管理器
        
        Args:
            config: GitHub配置
        """
        self.config = config
        self.logger = logging.getLogger('project_bach.github_actions')
        
        # GitHub配置
        self.token = config['token']
        self.username = config['username']
        self.repo = config['publish_repo']
        self.base_url = config.get('base_url', 'https://api.github.com')
        
        # 请求头
        self.headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Project-Bach-Actions/1.0'
        }
        
        self.logger.info("GitHub Actions管理器初始化完成")
    
    def create_static_sync_workflow(self, workflow_dir: Path) -> Dict[str, Any]:
        """创建静态资源同步工作流
        
        Args:
            workflow_dir: 工作流目录
            
        Returns:
            创建结果
        """
        self.logger.info("创建静态资源同步工作流配置")
        
        try:
            # 确保工作流目录存在
            workflow_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成静态资源同步工作流配置
            workflow_content = self._generate_static_sync_workflow()
            
            # 写入工作流文件
            workflow_file = workflow_dir / 'sync-static-assets.yml'
            workflow_file.write_text(workflow_content, encoding='utf-8')
            
            self.logger.info(f"静态资源同步工作流文件创建: {workflow_file}")
            
            return {
                'success': True,
                'workflow_file': str(workflow_file),
                'message': '静态资源同步工作流创建成功'
            }
            
        except Exception as e:
            self.logger.error(f"创建静态资源同步工作流失败: {str(e)}")
            return {
                'success': False,
                'message': f'创建静态资源同步工作流失败: {str(e)}'
            }
    
    def create_pages_workflow(self, workflow_dir: Path) -> Dict[str, Any]:
        """创建GitHub Pages工作流配置
        
        Args:
            workflow_dir: 工作流目录
            
        Returns:
            创建结果
        """
        self.logger.info("创建GitHub Pages工作流配置")
        
        try:
            # 确保工作流目录存在
            workflow_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成Pages工作流配置
            workflow_content = self._generate_pages_workflow()
            
            # 写入工作流文件
            workflow_file = workflow_dir / 'pages.yml'
            workflow_file.write_text(workflow_content, encoding='utf-8')
            
            self.logger.info(f"Pages工作流文件创建: {workflow_file}")
            
            return {
                'success': True,
                'workflow_file': str(workflow_file),
                'message': 'GitHub Pages工作流创建成功'
            }
            
        except Exception as e:
            self.logger.error(f"创建工作流失败: {str(e)}")
            return {
                'success': False,
                'message': f'创建工作流失败: {str(e)}'
            }
    
    def _generate_pages_workflow(self) -> str:
        """生成Pages工作流YAML内容"""
        workflow = {
            'name': 'Deploy to GitHub Pages',
            'on': {
                'push': {
                    'branches': ['gh-pages']
                },
                'workflow_dispatch': None
            },
            'permissions': {
                'contents': 'read',
                'pages': 'write',
                'id-token': 'write'
            },
            'concurrency': {
                'group': 'pages',
                'cancel-in-progress': False
            },
            'jobs': {
                'deploy': {
                    'environment': {
                        'name': 'github-pages',
                        'url': '${{ steps.deployment.outputs.page_url }}'
                    },
                    'runs-on': 'ubuntu-latest',
                    'steps': [
                        {
                            'name': 'Checkout',
                            'uses': 'actions/checkout@v4'
                        },
                        {
                            'name': 'Setup Pages',
                            'uses': 'actions/configure-pages@v4'
                        },
                        {
                            'name': 'Upload artifact',
                            'uses': 'actions/upload-pages-artifact@v3',
                            'with': {
                                'path': '.'
                            }
                        },
                        {
                            'name': 'Deploy to GitHub Pages',
                            'id': 'deployment',
                            'uses': 'actions/deploy-pages@v4'
                        }
                    ]
                }
            }
        }
        
        return yaml.dump(workflow, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    def _generate_static_sync_workflow(self) -> str:
        """生成静态资源同步工作流YAML内容"""
        workflow = {
            'name': 'Sync Static Assets to GitHub Pages',
            'on': {
                'push': {
                    'branches': ['main'],
                    'paths': [
                        'static/**',
                        'templates/**'
                    ]
                },
                'workflow_dispatch': None
            },
            'permissions': {
                'contents': 'write',
                'actions': 'read'
            },
            'jobs': {
                'sync-static-assets': {
                    'runs-on': 'ubuntu-latest',
                    'steps': [
                        {
                            'name': 'Checkout main branch',
                            'uses': 'actions/checkout@v4',
                            'with': {
                                'ref': 'main',
                                'fetch-depth': 0
                            }
                        },
                        {
                            'name': 'Configure Git',
                            'run': '\n'.join([
                                'git config --global user.name "GitHub Actions"',
                                'git config --global user.email "actions@github.com"'
                            ])
                        },
                        {
                            'name': 'Checkout gh-pages branch',
                            'run': 'git checkout gh-pages'
                        },
                        {
                            'name': 'Create static directory if not exists',
                            'run': 'mkdir -p static'
                        },
                        {
                            'name': 'Sync static assets from main',
                            'run': '\n'.join([
                                'git checkout main -- static/',
                                'echo "✅ Static assets synced from main branch"'
                            ])
                        },
                        {
                            'name': 'Check for changes',
                            'id': 'check-changes',
                            'run': '\n'.join([
                                'if git diff --quiet; then',
                                '  echo "changes=false" >> $GITHUB_OUTPUT',
                                '  echo "No changes to commit"',
                                'else',
                                '  echo "changes=true" >> $GITHUB_OUTPUT',
                                '  echo "Changes detected in static assets"',
                                'fi'
                            ])
                        },
                        {
                            'name': 'Commit and push changes',
                            'if': 'steps.check-changes.outputs.changes == \'true\'',
                            'run': '\n'.join([
                                'git add static/',
                                'git commit -m "🔄 Auto-sync: Update static assets from main branch',
                                '',
                                '- Synced CSS, JS, and other static files',
                                '- Triggered by changes in main branch',
                                '- Auto-generated by GitHub Actions"',
                                'git push origin gh-pages'
                            ])
                        },
                        {
                            'name': 'Summary',
                            'run': '\n'.join([
                                'echo "### Static Assets Sync Summary 📊" >> $GITHUB_STEP_SUMMARY',
                                'echo "" >> $GITHUB_STEP_SUMMARY',
                                'if [ "${{ steps.check-changes.outputs.changes }}" = "true" ]; then',
                                '  echo "✅ Static assets were updated and synced to gh-pages branch" >> $GITHUB_STEP_SUMMARY',
                                '  echo "🔗 [View GitHub Pages](https://sleepycat233.github.io/Project_Bach/)" >> $GITHUB_STEP_SUMMARY',
                                'else',
                                '  echo "ℹ️ No changes detected in static assets" >> $GITHUB_STEP_SUMMARY',
                                'fi',
                                'echo "" >> $GITHUB_STEP_SUMMARY',
                                'echo "**Synced directories:**" >> $GITHUB_STEP_SUMMARY',
                                'echo "- `static/css/` - CSS stylesheets" >> $GITHUB_STEP_SUMMARY',
                                'echo "- `static/js/` - JavaScript files" >> $GITHUB_STEP_SUMMARY',
                                'echo "- `static/assets/` - Images and other assets" >> $GITHUB_STEP_SUMMARY'
                            ])
                        }
                    ]
                }
            }
        }
        
        return yaml.dump(workflow, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    def get_workflow_runs(self, workflow_id: Optional[str] = None, per_page: int = 10) -> Dict[str, Any]:
        """获取工作流运行记录
        
        Args:
            workflow_id: 工作流ID（可选）
            per_page: 每页返回数量
            
        Returns:
            工作流运行信息
        """
        try:
            if workflow_id:
                url = f"{self.base_url}/repos/{self.username}/{self.repo}/actions/workflows/{workflow_id}/runs"
            else:
                url = f"{self.base_url}/repos/{self.username}/{self.repo}/actions/runs"
            
            params = {'per_page': per_page}
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                return {
                    'success': True,
                    'total_count': data['total_count'],
                    'workflow_runs': [
                        {
                            'id': run['id'],
                            'name': run['name'],
                            'status': run['status'],
                            'conclusion': run['conclusion'],
                            'created_at': run['created_at'],
                            'updated_at': run['updated_at'],
                            'run_number': run['run_number'],
                            'url': run['html_url']
                        }
                        for run in data['workflow_runs']
                    ]
                }
            else:
                return {
                    'success': False,
                    'message': f'获取工作流运行失败: {response.status_code}',
                    'error': response.text
                }
                
        except Exception as e:
            self.logger.error(f"获取工作流运行异常: {str(e)}")
            return {
                'success': False,
                'message': f'获取工作流运行异常: {str(e)}'
            }
    
    def trigger_workflow(self, workflow_id: str, ref: str = 'main', inputs: Optional[Dict] = None) -> Dict[str, Any]:
        """手动触发工作流
        
        Args:
            workflow_id: 工作流ID
            ref: 分支或标签
            inputs: 输入参数
            
        Returns:
            触发结果
        """
        self.logger.info(f"手动触发工作流: {workflow_id}")
        
        try:
            url = f"{self.base_url}/repos/{self.username}/{self.repo}/actions/workflows/{workflow_id}/dispatches"
            
            payload = {
                'ref': ref
            }
            
            if inputs:
                payload['inputs'] = inputs
            
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            
            if response.status_code == 204:
                return {
                    'success': True,
                    'message': '工作流触发成功',
                    'workflow_id': workflow_id,
                    'ref': ref
                }
            else:
                return {
                    'success': False,
                    'message': f'工作流触发失败: {response.status_code}',
                    'error': response.text
                }
                
        except Exception as e:
            self.logger.error(f"触发工作流异常: {str(e)}")
            return {
                'success': False,
                'message': f'触发工作流异常: {str(e)}'
            }
    
    def monitor_workflow_run(self, run_id: int) -> Dict[str, Any]:
        """监控特定的工作流运行
        
        Args:
            run_id: 运行ID
            
        Returns:
            运行状态信息
        """
        try:
            url = f"{self.base_url}/repos/{self.username}/{self.repo}/actions/runs/{run_id}"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                run_data = response.json()
                
                # 计算运行时长
                created_at = datetime.fromisoformat(run_data['created_at'].replace('Z', '+00:00'))
                if run_data['updated_at']:
                    updated_at = datetime.fromisoformat(run_data['updated_at'].replace('Z', '+00:00'))
                    duration = (updated_at - created_at).total_seconds()
                else:
                    duration = (datetime.now() - created_at).total_seconds()
                
                return {
                    'success': True,
                    'run_id': run_data['id'],
                    'status': run_data['status'],
                    'conclusion': run_data['conclusion'],
                    'created_at': run_data['created_at'],
                    'updated_at': run_data['updated_at'],
                    'duration_seconds': duration,
                    'url': run_data['html_url'],
                    'workflow_name': run_data['name']
                }
            else:
                return {
                    'success': False,
                    'message': f'获取运行信息失败: {response.status_code}'
                }
                
        except Exception as e:
            self.logger.error(f"监控工作流运行异常: {str(e)}")
            return {
                'success': False,
                'message': f'监控异常: {str(e)}'
            }
    
    def validate_workflow_config(self, workflow_content: str) -> Dict[str, Any]:
        """验证工作流配置
        
        Args:
            workflow_content: 工作流YAML内容
            
        Returns:
            验证结果
        """
        try:
            # 解析YAML
            workflow_data = yaml.safe_load(workflow_content)
            
            # 基本结构验证
            required_keys = ['name', 'on', 'jobs']
            missing_keys = [key for key in required_keys if key not in workflow_data]
            
            if missing_keys:
                return {
                    'valid': False,
                    'message': f'缺少必需字段: {missing_keys}'
                }
            
            # 验证权限设置（对于Pages工作流）
            permissions = workflow_data.get('permissions', {})
            recommended_permissions = ['contents', 'pages', 'id-token']
            
            missing_permissions = [
                perm for perm in recommended_permissions 
                if perm not in permissions
            ]
            
            warnings = []
            if missing_permissions:
                warnings.append(f'建议添加权限: {missing_permissions}')
            
            return {
                'valid': True,
                'message': '工作流配置有效',
                'warnings': warnings,
                'structure': {
                    'has_permissions': bool(permissions),
                    'job_count': len(workflow_data['jobs']),
                    'trigger_events': list(workflow_data['on'].keys()) if isinstance(workflow_data['on'], dict) else [workflow_data['on']]
                }
            }
            
        except yaml.YAMLError as e:
            return {
                'valid': False,
                'message': f'YAML格式错误: {str(e)}'
            }
        except Exception as e:
            return {
                'valid': False,
                'message': f'验证异常: {str(e)}'
            }
    
    def get_workflow_status_summary(self) -> Dict[str, Any]:
        """获取工作流状态摘要
        
        Returns:
            状态摘要
        """
        try:
            # 获取最近的工作流运行
            runs_result = self.get_workflow_runs(per_page=20)
            
            if not runs_result['success']:
                return {
                    'success': False,
                    'message': '无法获取工作流运行信息'
                }
            
            runs = runs_result['workflow_runs']
            
            # 统计各种状态
            status_counts = {}
            conclusion_counts = {}
            
            for run in runs:
                status = run['status']
                conclusion = run['conclusion']
                
                status_counts[status] = status_counts.get(status, 0) + 1
                if conclusion:
                    conclusion_counts[conclusion] = conclusion_counts.get(conclusion, 0) + 1
            
            # 计算成功率
            total_completed = sum(conclusion_counts.values())
            success_rate = 0
            if total_completed > 0:
                success_count = conclusion_counts.get('success', 0)
                success_rate = (success_count / total_completed) * 100
            
            return {
                'success': True,
                'summary': {
                    'total_runs': len(runs),
                    'status_breakdown': status_counts,
                    'conclusion_breakdown': conclusion_counts,
                    'success_rate_percent': round(success_rate, 1),
                    'last_run': runs[0] if runs else None
                }
            }
            
        except Exception as e:
            self.logger.error(f"获取状态摘要异常: {str(e)}")
            return {
                'success': False,
                'message': f'获取状态摘要异常: {str(e)}'
            }


if __name__ == '__main__':
    # 测试GitHub Actions管理器
    test_config = {
        'token': 'test_token',
        'username': 'testuser',
        'publish_repo': 'project-bach-site',
        'base_url': 'https://api.github.com'
    }
    
    actions_manager = GitHubActionsManager(test_config)
    
    # 测试工作流配置生成
    test_workflow_dir = Path('./test_workflows')
    
    # 测试静态资源同步工作流
    print("=== 测试静态资源同步工作流 ===")
    sync_result = actions_manager.create_static_sync_workflow(test_workflow_dir)
    
    if sync_result['success']:
        print(f"✅ 静态资源同步工作流创建成功: {sync_result['workflow_file']}")
        
        # 验证工作流配置
        sync_workflow_file = Path(sync_result['workflow_file'])
        if sync_workflow_file.exists():
            sync_workflow_content = sync_workflow_file.read_text()
            sync_validation = actions_manager.validate_workflow_config(sync_workflow_content)
            print(f"工作流配置验证: {'有效' if sync_validation['valid'] else '无效'}")
            
            if sync_validation.get('warnings'):
                print(f"警告: {sync_validation['warnings']}")
    else:
        print(f"❌ 静态资源同步工作流创建失败: {sync_result['message']}")
    
    print("\n=== 测试GitHub Pages工作流 ===")
    result = actions_manager.create_pages_workflow(test_workflow_dir)
    
    if result['success']:
        print(f"✅ 工作流文件创建成功: {result['workflow_file']}")
        
        # 测试配置验证
        workflow_file = Path(result['workflow_file'])
        if workflow_file.exists():
            workflow_content = workflow_file.read_text()
            validation = actions_manager.validate_workflow_config(workflow_content)
            print(f"工作流配置验证: {'有效' if validation['valid'] else '无效'}")
            
            if validation.get('warnings'):
                print(f"警告: {validation['warnings']}")
    else:
        print(f"❌ 工作流文件创建失败: {result['message']}")
    
    print("✅ GitHub Actions管理器测试完成")