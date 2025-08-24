#!/usr/bin/env python3
"""
SETUP.md文档测试

测试项目设置文档的完整性：
1. WhisperKit模型下载指导
2. 安装命令正确性
3. 故障排除信息
"""

import unittest
from pathlib import Path
import re


class TestSetupDocumentation(unittest.TestCase):
    """测试SETUP.md文档更新"""
    
    def test_setup_file_exists(self):
        """测试SETUP.md文件存在"""
        setup_path = Path('./SETUP.md')
        self.assertTrue(setup_path.exists(), "SETUP.md should exist")
    
    def test_setup_contains_model_download_instructions(self):
        """测试SETUP.md包含模型下载指导"""
        setup_path = Path('./SETUP.md')
        self.assertTrue(setup_path.exists(), "SETUP.md should exist")
        
        content = setup_path.read_text()
        
        # 应该包含WhisperKit模型管理章节
        self.assertIn('WhisperKit模型管理', content)
        self.assertIn('模型下载详细说明', content)
        
        # 应该包含whisperkit-cli命令
        self.assertIn('whisperkit-cli transcribe', content)
        self.assertIn('--model', content)
        self.assertIn('--model-prefix', content)
        self.assertIn('--download-model-path', content)
        
        # 应该包含推荐模型组合
        self.assertIn('推荐模型组合', content)
        self.assertIn('distil', content)
        self.assertIn('openai', content)
        
    def test_setup_includes_ffmpeg_temp_audio(self):
        """测试SETUP.md包含ffmpeg临时音频创建"""
        setup_path = Path('./SETUP.md')
        content = setup_path.read_text()
        
        # 应该包含ffmpeg命令来创建临时音频文件
        self.assertIn('ffmpeg', content)
        self.assertIn('anullsrc', content)
        self.assertIn('temp_download.wav', content)
        
    def test_setup_includes_troubleshooting(self):
        """测试SETUP.md包含故障排除"""
        setup_path = Path('./SETUP.md')
        content = setup_path.read_text()
        
        # 应该包含WhisperKit相关的故障排除
        self.assertIn('WhisperKit模型未找到', content)
        self.assertIn('whisperkit-cli命令不存在', content)
        self.assertIn('模型下载速度慢', content)
        
    def test_setup_installation_commands_valid(self):
        """测试SETUP.md中的安装命令格式正确"""
        setup_path = Path('./SETUP.md')
        content = setup_path.read_text()
        
        # 检查命令格式
        lines = content.split('\n')
        whisperkit_lines = [line for line in lines if 'whisperkit-cli transcribe' in line]
        
        for line in whisperkit_lines:
            # 每个whisperkit-cli命令都应该包含必要的参数
            if 'whisperkit-cli transcribe' in line:
                self.assertIn('--model', line)
                self.assertIn('--model-prefix', line)
                self.assertIn('--download-model-path', line)
                self.assertIn('./models/whisperkit-coreml', line)


class TestCommandSyntaxValidation(unittest.TestCase):
    """测试命令语法验证"""
    
    def test_bash_commands_syntax(self):
        """测试bash命令语法正确性"""
        setup_path = Path('./SETUP.md')
        content = setup_path.read_text()
        
        # 提取代码块中的bash命令
        bash_blocks = re.findall(r'```bash\n(.*?)\n```', content, re.DOTALL)
        
        for block in bash_blocks:
            lines = block.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    # 基本的bash命令格式检查
                    # 确保没有明显的语法错误
                    self.assertFalse(line.endswith('\\') and not line.endswith('\\ '), 
                                   f"Potential line continuation error in: {line}")
                    
    def test_whisperkit_commands_completeness(self):
        """测试WhisperKit命令的完整性"""
        setup_path = Path('./SETUP.md')
        content = setup_path.read_text()
        
        # 查找所有whisperkit-cli命令
        whisperkit_commands = re.findall(r'whisperkit-cli transcribe[^\n]+', content)
        
        for cmd in whisperkit_commands:
            # 每个命令都应该包含关键参数
            self.assertIn('--model', cmd)
            self.assertIn('--model-prefix', cmd)
            self.assertIn('--download-model-path', cmd)
            self.assertIn('--audio-path', cmd)
            
    def test_model_paths_consistency(self):
        """测试模型路径一致性"""
        setup_path = Path('./SETUP.md')
        content = setup_path.read_text()
        
        # 查找所有模型路径
        model_paths = re.findall(r'--download-model-path\s+([^\s]+)', content)
        
        # 所有路径应该指向同一个目录
        unique_paths = set(model_paths)
        self.assertEqual(len(unique_paths), 1, 
                        f"Model paths should be consistent, found: {unique_paths}")
        
        # 路径应该是相对路径
        for path in model_paths:
            self.assertTrue(path.startswith('./'), 
                          f"Model path should be relative: {path}")


class TestDocumentationStructure(unittest.TestCase):
    """测试文档结构"""
    
    def test_markdown_headers_hierarchy(self):
        """测试Markdown标题层级结构"""
        setup_path = Path('./SETUP.md')
        content = setup_path.read_text()
        
        # 检查是否有合理的标题层级
        headers = re.findall(r'^(#+)\s+(.+)$', content, re.MULTILINE)
        
        self.assertGreater(len(headers), 0, "Should have at least one header")
        
        # 检查标题层级是否合理（不应该跳级）
        for i, (level, title) in enumerate(headers):
            if i > 0:
                prev_level = len(headers[i-1][0])
                curr_level = len(level)
                # 标题层级不应该跳跃太大
                self.assertLessEqual(curr_level - prev_level, 1, 
                                   f"Header level jump too large: {title}")
    
    def test_code_blocks_formatted(self):
        """测试代码块格式正确"""
        setup_path = Path('./SETUP.md')
        content = setup_path.read_text()
        
        # 检查代码块是否正确配对
        triple_backticks = content.count('```')
        self.assertEqual(triple_backticks % 2, 0, 
                        "Code blocks should be properly closed")
        
        # 检查是否有语言标识符
        bash_blocks = content.count('```bash')
        self.assertGreater(bash_blocks, 0, "Should have bash code blocks")
    
    def test_links_format(self):
        """测试链接格式正确"""
        setup_path = Path('./SETUP.md')
        content = setup_path.read_text()
        
        # 检查markdown链接格式
        links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
        
        for link_text, url in links:
            self.assertGreater(len(link_text), 0, "Link text should not be empty")
            if url.startswith('http'):
                # HTTP(S) URL格式基本检查
                self.assertTrue(url.startswith('http'), f"Invalid URL: {url}")


class TestInstallationSteps(unittest.TestCase):
    """测试安装步骤"""
    
    def test_prerequisite_sections(self):
        """测试先决条件章节"""
        setup_path = Path('./SETUP.md')
        content = setup_path.read_text()
        
        # 应该包含先决条件说明
        prerequisite_keywords = ['依赖', '要求', '前提', 'requirement', 'prerequisite']
        has_prerequisites = any(keyword in content.lower() for keyword in prerequisite_keywords)
        
        # 这是一个软检查，不是强制要求
        if not has_prerequisites:
            print("Warning: No clear prerequisite section found in SETUP.md")
    
    def test_step_by_step_instructions(self):
        """测试分步骤说明"""
        setup_path = Path('./SETUP.md')
        content = setup_path.read_text()
        
        # 查找步骤标识符
        step_patterns = [
            r'\d+\.',  # 1. 2. 3.
            r'步骤\s*\d+',  # 步骤1 步骤2
            r'Step\s*\d+',  # Step 1 Step 2
        ]
        
        has_steps = any(re.search(pattern, content) for pattern in step_patterns)
        
        if not has_steps:
            print("Warning: No clear step-by-step instructions found")
    
    def test_example_commands_provided(self):
        """测试提供示例命令"""
        setup_path = Path('./SETUP.md')
        content = setup_path.read_text()
        
        # 应该有具体的命令示例
        command_indicators = ['$', 'whisperkit-cli', 'ffmpeg', 'python']
        
        has_commands = any(indicator in content for indicator in command_indicators)
        self.assertTrue(has_commands, "Should provide example commands")


class TestModelConfiguration(unittest.TestCase):
    """测试模型配置说明"""
    
    def test_model_types_explained(self):
        """测试模型类型说明"""
        setup_path = Path('./SETUP.md')
        content = setup_path.read_text()
        
        # 应该解释不同的模型类型
        self.assertIn('distil', content.lower())
        self.assertIn('openai', content.lower())
        
    def test_language_support_documented(self):
        """测试语言支持说明"""
        setup_path = Path('./SETUP.md')
        content = setup_path.read_text()
        
        # 应该说明支持的语言
        language_keywords = ['英文', '中文', '多语言', 'english', 'chinese', 'multilingual']
        has_language_info = any(keyword in content.lower() for keyword in language_keywords)
        
        self.assertTrue(has_language_info, "Should document language support")
    
    def test_model_size_performance_info(self):
        """测试模型大小和性能信息"""
        setup_path = Path('./SETUP.md')
        content = setup_path.read_text()
        
        # 应该提及性能相关信息
        performance_keywords = ['性能', '速度', '大小', 'performance', 'speed', 'size']
        has_performance_info = any(keyword in content.lower() for keyword in performance_keywords)
        
        if not has_performance_info:
            print("Warning: No performance information found")


if __name__ == '__main__':
    unittest.main()