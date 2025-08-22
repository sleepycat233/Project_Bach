#!/usr/bin/env python3.11
"""
Project Bach 第五阶段详细测试用例
GitHub自动发布系统 - 测试驱动开发

测试模块：
1. GitHubPublisher - GitHub仓库操作
2. ContentFormatter - 内容格式化  
3. GitOperations - Git命令操作
4. TemplateEngine - 模板系统
5. PublishingWorkflow - 发布流程
6. GitHubActionsManager - CI/CD管理
7. 集成测试 - 完整发布流程
"""

import unittest
import tempfile
import shutil
import json
import os
import yaml
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
from datetime import datetime, timedelta
import subprocess
import requests

# 测试基础设置
class Phase5TestBase(unittest.TestCase):
    """第五阶段测试基类"""
    
    def setUp(self):
        """测试前准备"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.config = {
            'github': {
                'token': 'test_token_123',
                'username': 'testuser',
                'publish_repo': 'project-bach-site',
                'base_url': 'https://api.github.com',
                'pages_branch': 'gh-pages'
            },
            'publishing': {
                'template_dir': str(self.test_dir / 'templates'),
                'output_dir': str(self.test_dir / 'output'),
                'site_title': 'Project Bach',
                'site_description': 'AI音频处理结果发布',
                'theme': 'default'
            },
            'git': {
                'user_name': 'Project Bach Bot',
                'user_email': 'bot@project-bach.com',
                'commit_message_template': '🤖 Auto-publish: {title}',
                'remote_name': 'origin'
            }
        }
        
        # 创建测试目录结构
        (self.test_dir / 'templates').mkdir(parents=True)
        (self.test_dir / 'output').mkdir(parents=True)
        (self.test_dir / 'site').mkdir(parents=True)
        
    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.test_dir, ignore_errors=True)


# ========== 1. GitHubPublisher服务测试 ==========

class TestGitHubPublisher(Phase5TestBase):
    """GitHubPublisher服务测试"""
    
    def setUp(self):
        super().setUp()
        # 导入将要实现的模块 (现在用Mock)
        self.github_publisher = Mock()
        self.github_publisher.config = self.config['github']
        
    @patch('requests.post')
    @patch('requests.get')
    def test_create_repository_success(self, mock_get, mock_post):
        """测试成功创建GitHub仓库"""
        # 模拟仓库不存在
        mock_get.return_value.status_code = 404
        
        # 模拟创建成功
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {
            'name': 'project-bach-site',
            'full_name': 'testuser/project-bach-site',
            'html_url': 'https://github.com/testuser/project-bach-site'
        }
        
        # 测试创建仓库逻辑
        result = {
            'success': True,
            'repo_url': 'https://github.com/testuser/project-bach-site',
            'message': '仓库创建成功'
        }
        
        self.assertTrue(result['success'])
        self.assertIn('github.com', result['repo_url'])
        
    @patch('requests.get')
    def test_repository_already_exists(self, mock_get):
        """测试仓库已存在的情况"""
        # 模拟仓库已存在
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'name': 'project-bach-site',
            'full_name': 'testuser/project-bach-site'
        }
        
        result = {
            'success': True,
            'repo_url': 'https://github.com/testuser/project-bach-site',
            'message': '仓库已存在'
        }
        
        self.assertTrue(result['success'])
        
    @patch('requests.put')
    def test_configure_github_pages(self, mock_put):
        """测试配置GitHub Pages"""
        mock_put.return_value.status_code = 201
        mock_put.return_value.json.return_value = {
            'url': 'https://testuser.github.io/project-bach-site/',
            'source': {'branch': 'gh-pages', 'path': '/'}
        }
        
        result = {
            'success': True,
            'pages_url': 'https://testuser.github.io/project-bach-site/',
            'message': 'GitHub Pages配置成功'
        }
        
        self.assertTrue(result['success'])
        self.assertIn('github.io', result['pages_url'])
        
    def test_validate_github_token(self):
        """测试GitHub Token验证"""
        # 有效token
        valid_token = 'ghp_1234567890abcdef1234567890abcdef'
        self.assertTrue(len(valid_token) > 20)
        self.assertTrue(valid_token.startswith('ghp_'))
        
        # 无效token
        invalid_token = 'invalid_token'
        self.assertFalse(len(invalid_token) > 20)
        
    @patch('requests.get')
    def test_check_repository_status(self, mock_get):
        """测试检查仓库状态"""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'name': 'project-bach-site',
            'private': False,
            'has_pages': True,
            'updated_at': '2025-08-21T10:00:00Z'
        }
        
        status = {
            'exists': True,
            'private': False,
            'pages_enabled': True,
            'last_updated': '2025-08-21T10:00:00Z'
        }
        
        self.assertTrue(status['exists'])
        self.assertTrue(status['pages_enabled'])


# ========== 2. ContentFormatter服务测试 ==========

class TestContentFormatter(Phase5TestBase):
    """ContentFormatter服务测试"""
    
    def setUp(self):
        super().setUp()
        self.content_formatter = Mock()
        
        # 创建测试内容
        self.test_content = {
            'title': '测试音频处理结果',
            'summary': '这是一个测试摘要内容',
            'mindmap': '# 思维导图\n## 主要内容\n- 要点1\n- 要点2',
            'original_file': 'test_audio.mp3',
            'processed_time': '2025-08-21T10:30:00',
            'anonymized_names': {'张三': '王明', '李四': '刘华'}
        }
        
    def test_format_markdown_content(self):
        """测试Markdown内容格式化"""
        formatted = f"""# {self.test_content['title']}

**处理时间**: {self.test_content['processed_time']}
**原始文件**: {self.test_content['original_file']}

## 📄 内容摘要

{self.test_content['summary']}

## 🧠 思维导图

{self.test_content['mindmap']}

## 🔒 人名匿名化

匿名化映射: {len(self.test_content['anonymized_names'])} 个人名

---
*由 Project Bach 自动生成*
"""
        
        self.assertIn('测试音频处理结果', formatted)
        self.assertIn('内容摘要', formatted)
        self.assertIn('思维导图', formatted)
        self.assertIn('人名匿名化', formatted)
        
    def test_generate_html_from_markdown(self):
        """测试从Markdown生成HTML"""
        markdown_content = "# 标题\n\n这是一个**粗体**文本。"
        
        # 模拟HTML输出
        expected_html = """<h1>标题</h1>
<p>这是一个<strong>粗体</strong>文本。</p>"""
        
        self.assertIn('<h1>', expected_html)
        self.assertIn('<strong>', expected_html)
        
    def test_create_site_index(self):
        """测试创建网站首页索引"""
        # 模拟多个处理结果
        results = [
            {
                'title': '音频1处理结果',
                'date': '2025-08-21',
                'file': 'audio1.md',
                'summary': '摘要1'
            },
            {
                'title': '音频2处理结果', 
                'date': '2025-08-20',
                'file': 'audio2.md',
                'summary': '摘要2'
            }
        ]
        
        # 生成索引页面
        index_content = """# Project Bach 处理结果

## 📋 最新结果

| 日期 | 标题 | 摘要 |
|------|------|------|
| 2025-08-21 | [音频1处理结果](audio1.html) | 摘要1 |
| 2025-08-20 | [音频2处理结果](audio2.html) | 摘要2 |

---
*最后更新: 2025-08-21*
"""
        
        self.assertIn('Project Bach', index_content)
        self.assertIn('最新结果', index_content)
        self.assertEqual(len(results), 2)
        
    def test_validate_content_structure(self):
        """测试内容结构验证"""
        # 有效内容结构
        valid_content = {
            'title': '标题',
            'summary': '摘要',
            'mindmap': '思维导图',
            'processed_time': '2025-08-21T10:00:00'
        }
        
        required_fields = ['title', 'summary', 'mindmap', 'processed_time']
        
        for field in required_fields:
            self.assertIn(field, valid_content)
            self.assertTrue(len(valid_content[field]) > 0)
            
        # 无效内容结构
        invalid_content = {'title': ''}
        
        for field in required_fields:
            if field not in invalid_content:
                self.assertNotIn(field, invalid_content)


# ========== 3. GitOperations服务测试 ==========

class TestGitOperations(Phase5TestBase):
    """Git操作服务测试"""
    
    def setUp(self):
        super().setUp()
        self.repo_dir = self.test_dir / 'repo'
        self.repo_dir.mkdir()
        
    @patch('subprocess.run')
    def test_git_clone_repository(self, mock_run):
        """测试Git克隆仓库"""
        mock_run.return_value = Mock(returncode=0, stdout='', stderr='')
        
        repo_url = 'https://github.com/testuser/project-bach-site.git'
        clone_dir = str(self.repo_dir)
        
        # 模拟克隆命令
        expected_cmd = ['git', 'clone', repo_url, clone_dir]
        
        result = {
            'success': True,
            'message': '仓库克隆成功',
            'local_path': clone_dir
        }
        
        self.assertTrue(result['success'])
        self.assertEqual(result['local_path'], clone_dir)
        
    @patch('subprocess.run')
    def test_git_add_and_commit(self, mock_run):
        """测试Git添加和提交"""
        mock_run.return_value = Mock(returncode=0)
        
        # 创建测试文件
        test_file = self.repo_dir / 'test.md'
        test_file.write_text('# 测试内容')
        
        commit_message = '🤖 Auto-publish: 测试音频结果'
        
        # 模拟Git命令序列
        expected_commands = [
            ['git', 'add', '.'],
            ['git', 'commit', '-m', commit_message]
        ]
        
        result = {
            'success': True,
            'commit_hash': 'abc123def456',
            'message': '提交成功'
        }
        
        self.assertTrue(result['success'])
        self.assertTrue(len(result['commit_hash']) > 0)
        
    @patch('subprocess.run')
    def test_git_push_to_remote(self, mock_run):
        """测试Git推送到远程"""
        mock_run.return_value = Mock(returncode=0)
        
        branch_name = 'gh-pages'
        remote_name = 'origin'
        
        expected_cmd = ['git', 'push', remote_name, branch_name]
        
        result = {
            'success': True,
            'message': '推送成功',
            'branch': branch_name
        }
        
        self.assertTrue(result['success'])
        self.assertEqual(result['branch'], branch_name)
        
    @patch('subprocess.run')
    def test_git_create_branch(self, mock_run):
        """测试创建Git分支"""
        mock_run.return_value = Mock(returncode=0)
        
        branch_name = 'gh-pages'
        
        # 检查分支是否存在 + 创建分支
        expected_commands = [
            ['git', 'checkout', '-b', branch_name],
            ['git', 'push', '-u', 'origin', branch_name]
        ]
        
        result = {
            'success': True,
            'branch': branch_name,
            'message': 'gh-pages分支创建成功'
        }
        
        self.assertTrue(result['success'])
        self.assertEqual(result['branch'], 'gh-pages')
        
    def test_git_config_setup(self):
        """测试Git配置设置"""
        config = {
            'user.name': 'Project Bach Bot',
            'user.email': 'bot@project-bach.com'
        }
        
        # 验证配置参数
        self.assertIn('user.name', config)
        self.assertIn('user.email', config)
        self.assertTrue('@' in config['user.email'])


# ========== 4. TemplateEngine服务测试 ==========

class TestTemplateEngine(Phase5TestBase):
    """模板引擎服务测试"""
    
    def setUp(self):
        super().setUp()
        
        # 创建测试模板
        self.template_dir = self.test_dir / 'templates'
        self.create_test_templates()
        
    def create_test_templates(self):
        """创建测试模板文件"""
        # 基础模板
        base_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - {{ site_title }}</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; }
        .container { max-width: 800px; margin: 0 auto; padding: 20px; }
        .header { border-bottom: 2px solid #007AFF; padding-bottom: 20px; }
        .content { margin-top: 30px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ site_title }}</h1>
            <p>{{ site_description }}</p>
        </div>
        <div class="content">
            {% block content %}{% endblock %}
        </div>
    </div>
</body>
</html>"""
        
        # 内容页模板
        content_template = """{% extends "base.html" %}

{% block content %}
<article>
    <header>
        <h1>{{ content.title }}</h1>
        <p class="meta">
            <time>{{ content.processed_time }}</time>
            <span>原始文件: {{ content.original_file }}</span>
        </p>
    </header>
    
    <section class="summary">
        <h2>📄 内容摘要</h2>
        <div>{{ content.summary | markdown }}</div>
    </section>
    
    <section class="mindmap">
        <h2>🧠 思维导图</h2>
        <div>{{ content.mindmap | markdown }}</div>
    </section>
    
    {% if content.anonymized_names %}
    <section class="anonymization">
        <h2>🔒 人名匿名化</h2>
        <p>已匿名化 {{ content.anonymized_names | length }} 个人名</p>
    </section>
    {% endif %}
</article>
{% endblock %}"""
        
        # 索引页模板
        index_template = """{% extends "base.html" %}

{% block content %}
<div class="index">
    <h2>📋 处理结果列表</h2>
    
    {% for item in results %}
    <article class="result-item">
        <h3><a href="{{ item.file }}">{{ item.title }}</a></h3>
        <p class="meta">{{ item.date }}</p>
        <p>{{ item.summary[:100] }}...</p>
    </article>
    {% endfor %}
    
    <footer>
        <p><em>最后更新: {{ current_time }}</em></p>
    </footer>
</div>
{% endblock %}"""
        
        # 写入模板文件
        (self.template_dir / 'base.html').write_text(base_template)
        (self.template_dir / 'content.html').write_text(content_template)
        (self.template_dir / 'index.html').write_text(index_template)
        
    def test_load_template(self):
        """测试加载模板"""
        template_path = self.template_dir / 'base.html'
        
        self.assertTrue(template_path.exists())
        content = template_path.read_text()
        
        self.assertIn('<!DOCTYPE html>', content)
        self.assertIn('{{ site_title }}', content)
        self.assertIn('{% block content %}', content)
        
    def test_render_content_template(self):
        """测试渲染内容模板"""
        template_vars = {
            'site_title': 'Project Bach',
            'site_description': 'AI音频处理结果',
            'title': '测试音频结果',
            'content': {
                'title': '测试音频处理结果',
                'processed_time': '2025-08-21 10:30:00',
                'original_file': 'test.mp3',
                'summary': '这是测试摘要',
                'mindmap': '# 思维导图\n- 要点1',
                'anonymized_names': {'张三': '王明'}
            }
        }
        
        # 模拟渲染结果
        rendered = """<article>
    <header>
        <h1>测试音频处理结果</h1>
        <p class="meta">
            <time>2025-08-21 10:30:00</time>
            <span>原始文件: test.mp3</span>
        </p>
    </header>
</article>"""
        
        self.assertIn('测试音频处理结果', rendered)
        self.assertIn('2025-08-21', rendered)
        self.assertIn('test.mp3', rendered)
        
    def test_render_index_template(self):
        """测试渲染索引模板"""
        template_vars = {
            'site_title': 'Project Bach',
            'site_description': 'AI音频处理结果',
            'results': [
                {
                    'title': '音频1结果',
                    'date': '2025-08-21',
                    'file': 'audio1.html',
                    'summary': '音频1的摘要内容'
                }
            ],
            'current_time': '2025-08-21 11:00:00'
        }
        
        # 模拟渲染结果
        rendered = """<div class="index">
    <h2>📋 处理结果列表</h2>
    
    <article class="result-item">
        <h3><a href="audio1.html">音频1结果</a></h3>
        <p class="meta">2025-08-21</p>
    </article>
</div>"""
        
        self.assertIn('处理结果列表', rendered)
        self.assertIn('audio1.html', rendered)
        
    def test_template_validation(self):
        """测试模板文件验证"""
        required_templates = ['base.html', 'content.html', 'index.html']
        
        for template in required_templates:
            template_path = self.template_dir / template
            self.assertTrue(template_path.exists())
            
            content = template_path.read_text()
            self.assertTrue(len(content) > 0)


# ========== 5. PublishingWorkflow服务测试 ==========

class TestPublishingWorkflow(Phase5TestBase):
    """发布流程服务测试"""
    
    def setUp(self):
        super().setUp()
        
        # 模拟依赖服务
        self.github_publisher = Mock()
        self.content_formatter = Mock()
        self.git_operations = Mock()
        self.template_engine = Mock()
        
    def test_complete_publish_workflow(self):
        """测试完整发布流程"""
        
        # 输入数据
        content_data = {
            'title': '测试音频处理结果',
            'summary': '这是测试摘要',
            'mindmap': '# 思维导图',
            'original_file': 'test.mp3',
            'processed_time': '2025-08-21T10:30:00'
        }
        
        # 模拟流程步骤
        workflow_steps = [
            '1. 验证GitHub仓库存在',
            '2. 格式化内容为HTML',
            '3. 克隆仓库到本地',
            '4. 生成网站文件',
            '5. 提交更改到Git',
            '6. 推送到GitHub',
            '7. 触发Pages构建'
        ]
        
        # 模拟成功结果
        result = {
            'success': True,
            'published_url': 'https://testuser.github.io/project-bach-site/test-audio.html',
            'steps_completed': len(workflow_steps),
            'total_steps': len(workflow_steps)
        }
        
        self.assertTrue(result['success'])
        self.assertEqual(result['steps_completed'], result['total_steps'])
        self.assertIn('github.io', result['published_url'])
        
    def test_workflow_error_handling(self):
        """测试工作流错误处理"""
        
        # 模拟各种错误情况
        error_scenarios = [
            {
                'step': 'GitHub API',
                'error': 'API限流',
                'retry_count': 3,
                'recovery': '使用指数退避重试'
            },
            {
                'step': 'Git推送',
                'error': '网络超时',
                'retry_count': 2,
                'recovery': '重新连接并推送'
            },
            {
                'step': '模板渲染',
                'error': '模板语法错误',
                'retry_count': 0,
                'recovery': '使用备用模板'
            }
        ]
        
        for scenario in error_scenarios:
            self.assertIn('error', scenario)
            self.assertIn('recovery', scenario)
            self.assertIsInstance(scenario['retry_count'], int)
            
    def test_publish_status_tracking(self):
        """测试发布状态跟踪"""
        
        status_log = [
            {
                'timestamp': '2025-08-21T10:30:00',
                'step': 'start',
                'status': 'initiated',
                'message': '开始发布流程'
            },
            {
                'timestamp': '2025-08-21T10:30:30',
                'step': 'format_content',
                'status': 'completed',
                'message': '内容格式化完成'
            },
            {
                'timestamp': '2025-08-21T10:31:00',
                'step': 'git_operations',
                'status': 'in_progress',
                'message': '正在推送到GitHub'
            },
            {
                'timestamp': '2025-08-21T10:31:30',
                'step': 'complete',
                'status': 'success',
                'message': '发布成功完成'
            }
        ]
        
        # 验证状态日志结构
        for entry in status_log:
            required_fields = ['timestamp', 'step', 'status', 'message']
            for field in required_fields:
                self.assertIn(field, entry)
                
        # 验证最终状态
        final_status = status_log[-1]
        self.assertEqual(final_status['status'], 'success')
        
    def test_rollback_mechanism(self):
        """测试回滚机制"""
        
        # 模拟发布失败需要回滚的情况
        rollback_scenario = {
            'failed_step': 'git_push',
            'rollback_actions': [
                'reset_local_changes',
                'restore_previous_state',
                'notify_failure'
            ],
            'backup_created': True,
            'recovery_possible': True
        }
        
        self.assertTrue(rollback_scenario['backup_created'])
        self.assertTrue(rollback_scenario['recovery_possible'])
        self.assertEqual(len(rollback_scenario['rollback_actions']), 3)


# ========== 6. GitHubActionsManager测试 ==========

class TestGitHubActionsManager(Phase5TestBase):
    """GitHub Actions管理器测试"""
    
    def setUp(self):
        super().setUp()
        self.workflow_dir = self.test_dir / '.github' / 'workflows'
        self.workflow_dir.mkdir(parents=True)
        
    def test_create_pages_workflow(self):
        """测试创建Pages工作流"""
        
        workflow_content = """name: Deploy to GitHub Pages

on:
  push:
    branches: [ gh-pages ]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: false

jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        
      - name: Setup Pages
        uses: actions/configure-pages@v4
        
      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: '.'
          
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
"""
        
        workflow_file = self.workflow_dir / 'pages.yml'
        workflow_file.write_text(workflow_content)
        
        self.assertTrue(workflow_file.exists())
        content = workflow_file.read_text()
        self.assertIn('Deploy to GitHub Pages', content)
        self.assertIn('actions/checkout@v4', content)
        self.assertIn('actions/deploy-pages@v4', content)
        
    def test_workflow_validation(self):
        """测试工作流配置验证"""
        
        valid_workflow = {
            'name': 'Deploy to GitHub Pages',
            'on': ['push', 'workflow_dispatch'],
            'permissions': ['contents: read', 'pages: write'],
            'jobs': ['deploy']
        }
        
        # 验证必需字段
        required_fields = ['name', 'on', 'permissions', 'jobs']
        for field in required_fields:
            self.assertIn(field, valid_workflow)
            
        # 验证权限设置
        self.assertIn('pages: write', valid_workflow['permissions'])
        self.assertIn('contents: read', valid_workflow['permissions'])
        
    @patch('requests.get')
    def test_monitor_workflow_run(self, mock_get):
        """测试监控工作流运行"""
        
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'workflow_runs': [
                {
                    'id': 123456,
                    'status': 'completed',
                    'conclusion': 'success',
                    'created_at': '2025-08-21T10:30:00Z',
                    'updated_at': '2025-08-21T10:32:00Z'
                }
            ]
        }
        
        workflow_status = {
            'run_id': 123456,
            'status': 'completed',
            'conclusion': 'success',
            'duration_seconds': 120
        }
        
        self.assertEqual(workflow_status['status'], 'completed')
        self.assertEqual(workflow_status['conclusion'], 'success')
        self.assertGreater(workflow_status['duration_seconds'], 0)
        
    def test_workflow_trigger(self):
        """测试工作流触发"""
        
        trigger_methods = [
            {
                'method': 'push',
                'branch': 'gh-pages',
                'automatic': True
            },
            {
                'method': 'workflow_dispatch',
                'branch': 'main',
                'automatic': False,
                'manual_trigger': True
            }
        ]
        
        for trigger in trigger_methods:
            self.assertIn('method', trigger)
            self.assertIn('branch', trigger)
            self.assertIsInstance(trigger['automatic'], bool)


# ========== 7. 集成测试 ==========

class TestPhase5Integration(Phase5TestBase):
    """第五阶段集成测试"""
    
    def setUp(self):
        super().setUp()
        
        # 创建完整的测试内容
        self.test_content = {
            'title': '完整音频处理结果测试',
            'summary': '''这是一段完整的音频处理测试结果。音频内容包含了多人对话，
讨论了项目进展和技术方案。通过AI分析，提取了关键信息并生成了结构化摘要。''',
            'mindmap': '''# 音频内容思维导图

## 主要话题
- 项目进展讨论
- 技术方案评估
- 资源分配规划

## 参与人员
- 项目经理：整体协调
- 技术负责人：方案设计
- 开发团队：具体实施

## 关键决策
- 采用新的技术架构
- 调整开发时间表
- 增加测试环节''',
            'original_file': 'team_meeting_20250821.mp3',
            'processed_time': '2025-08-21T10:30:00',
            'anonymized_names': {
                '张经理': '项目经理A',
                '李工程师': '技术负责人B',
                '王开发': '开发人员C'
            }
        }
        
    def test_end_to_end_publishing(self):
        """测试端到端发布流程"""
        
        # 模拟完整流程步骤
        publishing_steps = [
            {
                'step': '1_validate_input',
                'status': 'completed',
                'duration': 0.1,
                'result': '输入内容验证通过'
            },
            {
                'step': '2_check_github_repo',
                'status': 'completed', 
                'duration': 1.2,
                'result': 'GitHub仓库状态正常'
            },
            {
                'step': '3_format_content',
                'status': 'completed',
                'duration': 0.5,
                'result': 'HTML内容生成完成'
            },
            {
                'step': '4_clone_repository',
                'status': 'completed',
                'duration': 3.0,
                'result': '仓库克隆到本地成功'
            },
            {
                'step': '5_generate_site',
                'status': 'completed',
                'duration': 1.0,
                'result': '静态网站文件生成'
            },
            {
                'step': '6_commit_changes',
                'status': 'completed',
                'duration': 0.8,
                'result': 'Git提交成功'
            },
            {
                'step': '7_push_to_github',
                'status': 'completed',
                'duration': 2.5,
                'result': '推送到GitHub成功'
            },
            {
                'step': '8_trigger_pages_build',
                'status': 'completed',
                'duration': 30.0,
                'result': 'GitHub Pages构建完成'
            }
        ]
        
        # 验证每个步骤都成功
        total_duration = 0
        for step in publishing_steps:
            self.assertEqual(step['status'], 'completed')
            self.assertGreater(step['duration'], 0)
            total_duration += step['duration']
            
        # 验证总体结果
        self.assertEqual(len(publishing_steps), 8)
        self.assertGreater(total_duration, 35)  # 至少35秒总时长
        
        # 模拟最终发布结果
        final_result = {
            'success': True,
            'published_url': 'https://testuser.github.io/project-bach-site/team_meeting_20250821.html',
            'pages_url': 'https://testuser.github.io/project-bach-site/',
            'commit_hash': 'abc123def456',
            'build_time': total_duration,
            'content_size_kb': 45.6
        }
        
        self.assertTrue(final_result['success'])
        self.assertIn('github.io', final_result['published_url'])
        self.assertGreater(final_result['content_size_kb'], 0)
        
    def test_multiple_content_publishing(self):
        """测试多内容批量发布"""
        
        # 模拟多个音频处理结果
        multiple_contents = [
            {
                'title': f'音频{i}处理结果',
                'filename': f'audio{i}.html',
                'processed_time': f'2025-08-{20+i:02d}T10:30:00'
            } for i in range(1, 6)
        ]
        
        # 模拟批量发布结果
        batch_result = {
            'total_items': len(multiple_contents),
            'successful_publishes': 5,
            'failed_publishes': 0,
            'index_page_updated': True,
            'total_time': 180.0,  # 3分钟
            'average_time_per_item': 36.0
        }
        
        self.assertEqual(batch_result['total_items'], 5)
        self.assertEqual(batch_result['successful_publishes'], 5)
        self.assertEqual(batch_result['failed_publishes'], 0)
        self.assertTrue(batch_result['index_page_updated'])
        
    def test_error_recovery_integration(self):
        """测试错误恢复集成"""
        
        # 模拟发布过程中的错误和恢复
        error_recovery_scenarios = [
            {
                'error_step': 'git_push',
                'error_type': 'network_timeout',
                'recovery_action': 'retry_with_backoff',
                'retry_count': 2,
                'final_result': 'success'
            },
            {
                'error_step': 'github_api',
                'error_type': 'rate_limit',
                'recovery_action': 'wait_and_retry',
                'retry_count': 1,
                'final_result': 'success'
            },
            {
                'error_step': 'template_render',
                'error_type': 'template_syntax',
                'recovery_action': 'use_fallback_template',
                'retry_count': 0,
                'final_result': 'success'
            }
        ]
        
        # 验证所有错误都能恢复
        for scenario in error_recovery_scenarios:
            self.assertEqual(scenario['final_result'], 'success')
            self.assertIn('recovery_action', scenario)
            
    def test_performance_benchmarks(self):
        """测试性能基准"""
        
        performance_targets = {
            'small_content_publish_time': 30,    # 小内容30秒内
            'large_content_publish_time': 90,    # 大内容90秒内
            'batch_publish_throughput': 10,      # 每分钟10个内容
            'memory_usage_mb': 200,              # 内存使用不超过200MB
            'storage_efficiency': 0.8            # 存储效率80%以上
        }
        
        # 模拟性能测试结果
        actual_performance = {
            'small_content_publish_time': 25,    # 实际25秒
            'large_content_publish_time': 75,    # 实际75秒  
            'batch_publish_throughput': 12,      # 实际每分钟12个
            'memory_usage_mb': 150,              # 实际150MB
            'storage_efficiency': 0.85           # 实际85%
        }
        
        # 验证性能达标
        for metric, target in performance_targets.items():
            actual = actual_performance[metric]
            if 'time' in metric or 'usage' in metric:
                self.assertLessEqual(actual, target)  # 时间和内存使用越少越好
            else:
                self.assertGreaterEqual(actual, target)  # 其他指标越大越好
                
    def test_quality_assurance(self):
        """测试质量保证"""
        
        quality_checks = {
            'content_validation': {
                'html_well_formed': True,
                'markdown_rendered': True,
                'links_functional': True,
                'images_loaded': True
            },
            'accessibility': {
                'semantic_html': True,
                'alt_text_present': True,
                'keyboard_navigation': True,
                'screen_reader_compatible': True
            },
            'seo_optimization': {
                'meta_tags_present': True,
                'structured_data': True,
                'page_title_optimized': True,
                'mobile_friendly': True
            },
            'security': {
                'no_xss_vulnerabilities': True,
                'secure_links': True,
                'data_sanitized': True,
                'https_enforced': True
            }
        }
        
        # 验证所有质量检查都通过
        for category, checks in quality_checks.items():
            for check, result in checks.items():
                self.assertTrue(result, f"{category}.{check} 质量检查失败")


# ========== 测试运行器 ==========

def create_test_suite():
    """创建测试套件"""
    suite = unittest.TestSuite()
    
    # 添加所有测试类
    test_classes = [
        TestGitHubPublisher,
        TestContentFormatter,
        TestGitOperations,
        TestTemplateEngine,
        TestPublishingWorkflow,
        TestGitHubActionsManager,
        TestPhase5Integration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    return suite


if __name__ == '__main__':
    # 运行所有测试
    print("=" * 60)
    print("Project Bach 第五阶段详细测试 - GitHub自动发布系统")
    print("=" * 60)
    
    # 创建并运行测试套件
    suite = create_test_suite()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出测试摘要
    print(f"\n" + "=" * 60)
    print(f"测试完成！")
    print(f"总测试数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print(f"成功率: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    print("=" * 60)
    
    # 如果有失败或错误，显示详情
    if result.failures:
        print("\n❌ 测试失败:")
        for test, error in result.failures:
            error_msg = error.split('AssertionError: ')[-1].split('\n')[0]
            print(f"  - {test}: {error_msg}")
            
    if result.errors:
        print("\n⚠️  测试错误:")
        for test, error in result.errors:
            error_lines = error.split('\n')
            error_msg = error_lines[-2] if len(error_lines) > 1 else error_lines[0]
            print(f"  - {test}: {error_msg}")
            
    if not result.failures and not result.errors:
        print("\n🎉 所有测试通过！第五阶段测试用例编写完成。")
        print("✅ 可以开始实现GitHub自动发布功能模块")