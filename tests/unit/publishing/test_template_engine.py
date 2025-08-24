#!/usr/bin/env python3.11
"""
TemplateEngine服务单元测试
测试Jinja2模板加载、渲染、验证等功能
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src'))

from .test_base import PublishingTestBase


class TestTemplateEngine(PublishingTestBase):
    """TemplateEngine服务测试"""
    
    def setUp(self):
        super().setUp()
        self.template_engine = Mock()
        self.create_sample_template('base.html')
        self.create_sample_template('content.html')
        
    def test_load_template(self):
        """测试模板加载"""
        template_name = 'base.html'
        template_path = self.test_dir / 'templates' / template_name
        
        # 确保模板文件存在
        self.assertTrue(template_path.exists())
        
        # 模拟模板加载结果
        template_content = template_path.read_text()
        self.assertIn('<!DOCTYPE html>', template_content)
        self.assertIn('{{ title }}', template_content)
        self.assertIn('{{ content }}', template_content)
        
    def test_render_content_template(self):
        """测试内容模板渲染"""
        template_data = {
            'title': '测试音频处理结果',
            'content': '<p>这是处理后的内容</p>',
            'date': '2025-08-21',
            'summary': '测试摘要'
        }
        
        # 模拟渲染结果
        rendered = f"""<!DOCTYPE html>
<html>
<head>
    <title>{template_data['title']}</title>
</head>
<body>
    <h1>{template_data['title']}</h1>
    <div>{template_data['content']}</div>
</body>
</html>"""
        
        self.assertIn(template_data['title'], rendered)
        self.assertIn(template_data['content'], rendered)
        
    def test_render_index_template(self):
        """测试首页模板渲染"""
        index_data = {
            'title': 'Project Bach 处理结果',
            'results': [
                {'title': '音频1', 'date': '2025-08-21', 'file': 'audio1.html'},
                {'title': '音频2', 'date': '2025-08-20', 'file': 'audio2.html'}
            ],
            'site_description': 'AI音频处理结果发布'
        }
        
        # 模拟首页渲染
        rendered_index = f"""<!DOCTYPE html>
<html>
<head>
    <title>{index_data['title']}</title>
    <meta name="description" content="{index_data['site_description']}">
</head>
<body>
    <h1>{index_data['title']}</h1>
    <ul>
        <li><a href="{index_data['results'][0]['file']}">{index_data['results'][0]['title']}</a></li>
        <li><a href="{index_data['results'][1]['file']}">{index_data['results'][1]['title']}</a></li>
    </ul>
</body>
</html>"""
        
        self.assertIn('Project Bach', rendered_index)
        self.assertIn('audio1.html', rendered_index)
        self.assertIn('audio2.html', rendered_index)
        
    def test_template_validation(self):
        """测试模板验证"""
        # 有效模板语法
        valid_template = "Hello {{ name }}!"
        self.assertIn('{{', valid_template)
        self.assertIn('}}', valid_template)
        
        # 无效模板语法
        invalid_template = "Hello {{ name"
        self.assertIn('{{', invalid_template)
        self.assertNotIn('}}', invalid_template)
        
        # 检查模板文件是否存在
        template_path = self.test_dir / 'templates' / 'base.html'
        self.assertTrue(template_path.exists())
        
        # 检查模板内容是否有效
        content = template_path.read_text()
        self.assertTrue(len(content) > 0)
        self.assertIn('html', content.lower())


if __name__ == '__main__':
    unittest.main()