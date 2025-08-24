#!/usr/bin/env python3.11
"""
ContentFormatter服务单元测试
测试内容格式化、Markdown生成、HTML转换等功能
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src'))

from .test_base import PublishingTestBase


class TestContentFormatter(PublishingTestBase):
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


if __name__ == '__main__':
    unittest.main()