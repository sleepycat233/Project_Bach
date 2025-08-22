#!/usr/bin/env python3.11
"""
Project Bach Publishing测试基类
提供所有publishing模块测试的共用设置和工具
"""

import unittest
import tempfile
import shutil
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class PublishingTestBase(unittest.TestCase):
    """Publishing模块测试基类"""
    
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

    def create_sample_content(self):
        """创建示例内容文件"""
        content = {
            'title': 'Test Audio Processing',
            'summary': 'This is a test summary',
            'mindmap': '# Test Mindmap\n- Point 1\n- Point 2',
            'date': '2025-08-22',
            'file_path': 'test_result.md',
            'audio_path': 'test.mp3'
        }
        return content

    def create_sample_template(self, template_name="base.html"):
        """创建示例模板文件"""
        template_content = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
</head>
<body>
    <h1>{{ title }}</h1>
    <div>{{ content }}</div>
</body>
</html>
"""
        template_path = self.test_dir / 'templates' / template_name
        template_path.write_text(template_content)
        return template_path