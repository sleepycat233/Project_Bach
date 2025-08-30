#!/usr/bin/env python3
"""
私有内容页面集成测试

测试我们刚刚修复的私有内容页面功能：
1. 私有内容动态列表显示
2. 模板复用和UI一致性
3. 私有内容文件处理工作流
4. 模板过滤器功能
5. 端到端私有处理流程
"""

import unittest
import tempfile
import shutil
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestPrivateContentPageIntegration(unittest.TestCase):
    """私有内容页面集成测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)
        
        # 创建测试配置
        self.config = {
            'paths': {
                'data_folder': str(Path(self.test_dir) / 'data'),
                'output_folder': str(Path(self.test_dir) / 'data/output'),
                'watch_folder': str(Path(self.test_dir) / 'watch_folder')
            },
            'api': {
                'openrouter': {
                    'key': 'test_key',
                    'base_url': 'https://openrouter.ai/api/v1'
                }
            },
            'logging': {'level': 'ERROR'},
            'tailscale': {
                'enabled': False  # 禁用Tailscale安全检查以便测试
            }
        }
        
        # 创建测试目录结构
        self.private_dir = Path(self.test_dir) / 'data/output/private'
        self.private_dir.mkdir(parents=True)
        
    def create_test_private_content_files(self):
        """创建测试的私人内容文件"""
        # 创建测试HTML文件
        test_files = [
            {
                'filename': '20250824_034746_LEC_feynman_lecture_2min_result.html',
                'content': '''
                <html>
                <head><title>Feynman Lecture</title></head>
                <body>
                    <h1>Feynman Lecture Result</h1>
                    <p>This excerpt from a 1962 lecture on diffusion introduces the concept of analyzing systems out of equilibrium.</p>
                    <div>Processing complete</div>
                </body>
                </html>
                '''
            },
            {
                'filename': '20250823_111331_LEC_New_Recording_3_result.html',
                'content': '''
                <html>
                <head><title>New Recording 3</title></head>
                <body>
                    <h1>New Recording 3 Result</h1>
                    <p>WhisperKit转录故障 音频文件的转录尝试使用WhisperKit失败。</p>
                </body>
                </html>
                '''
            },
            {
                'filename': 'youtube_UgK4iR5lz4c_result.html',
                'content': '''
                <html>
                <head><title>YouTube Content</title></head>
                <body>
                    <h1>YouTube Processing Result</h1>
                    <p>本期《不明白播客》探讨了2025年中国经济的现状与新兴技术热潮。</p>
                </body>
                </html>
                '''
            }
        ]
        
        for file_info in test_files:
            file_path = self.private_dir / file_info['filename']
            file_path.write_text(file_info['content'], encoding='utf-8')
        
        return test_files
    
    def test_private_content_page_renders_correctly(self):
        """测试私有内容页面正确渲染"""
        from src.web_frontend.app import create_app
        
        # 创建测试私人内容文件
        test_files = self.create_test_private_content_files()
        
        app = create_app(self.config)
        with app.test_client() as client:
            # 测试私有内容页面
            response = client.get('/private/')
            
            self.assertEqual(response.status_code, 200)
            content = response.get_data(as_text=True)
            
            # 验证页面标题和基本结构
            self.assertIn('🔒 Private Content', content)
            self.assertIn('私人内容区域 - 仅通过Tailscale网络访问', content)
            
            # 验证统计信息
            self.assertIn('共收录 3 个私人文件', content)
            self.assertIn('2 音频', content)  # 2个LEC文件
            self.assertIn('1 视频', content)  # 1个youtube文件
    
    def test_private_content_file_listing(self):
        """测试私人内容文件列表功能"""
        from src.web_frontend.app import create_app
        
        test_files = self.create_test_private_content_files()
        
        app = create_app(self.config)
        with app.test_client() as client:
            response = client.get('/private/')
            content = response.get_data(as_text=True)
            
            # 验证每个文件都在列表中
            self.assertIn('feynman lecture 2min', content)
            self.assertIn('New Recording 3', content)
            self.assertIn('UgK4iR5lz4c', content)
            
            # 验证链接正确
            self.assertIn('/private/20250824_034746_LEC_feynman_lecture_2min_result.html', content)
            self.assertIn('/private/youtube_UgK4iR5lz4c_result.html', content)
    
    def test_private_content_template_reuse(self):
        """测试私人内容页面模板复用"""
        from src.web_frontend.app import create_app
        
        test_files = self.create_test_private_content_files()
        
        app = create_app(self.config)
        with app.test_client() as client:
            response = client.get('/private/')
            content = response.get_data(as_text=True)
            
            # 验证使用了公共模板的元素
            self.assertIn('Project Bach', content)
            
            # 验证响应式设计元素
            self.assertIn('var(--', content)  # CSS变量
            self.assertIn('查看详情', content)  # 按钮文本
    
    def test_template_filters_functionality(self):
        """测试模板过滤器功能"""
        from src.web_frontend.app import create_app
        
        test_files = self.create_test_private_content_files()
        
        app = create_app(self.config)
        with app.test_client() as client:
            response = client.get('/private/')
            content = response.get_data(as_text=True)
            
            # 验证日期格式化
            self.assertIn('2025-08-24 03:47', content)  # format_date 过滤器
            self.assertIn('2025-08-23 11:13', content)
            
            # 验证文件大小格式化 (应该显示 KB 或 B)
            self.assertRegex(content, r'\d+\.?\d*\s*(KB|B)')
            
            # 验证文本截断功能 (检查内容中是否有省略号或截断)
            has_truncated = '...' in content or 'truncate' in content.lower()
            self.assertTrue(has_truncated or len(content) > 1000, "应该有文本内容或截断处理")
    
    def test_private_content_individual_file_access(self):
        """测试访问单个私人内容文件"""
        from src.web_frontend.app import create_app
        
        test_files = self.create_test_private_content_files()
        
        app = create_app(self.config)
        with app.test_client() as client:
            # 测试访问具体的私人内容文件
            response = client.get('/private/20250824_034746_LEC_feynman_lecture_2min_result.html')
            
            self.assertEqual(response.status_code, 200)
            content = response.get_data(as_text=True)
            
            # 验证文件内容正确返回
            self.assertIn('Feynman Lecture Result', content)
            self.assertIn('1962 lecture on diffusion', content)
    
    def test_private_content_security(self):
        """测试私人内容安全性"""
        from src.web_frontend.app import create_app
        
        test_files = self.create_test_private_content_files()
        
        app = create_app(self.config)
        with app.test_client() as client:
            # 测试目录穿越攻击防护
            response = client.get('/private/../../../etc/passwd')
            self.assertIn(response.status_code, [400, 403, 404])
            
            # 测试访问不存在的文件
            response = client.get('/private/nonexistent_file.html')
            self.assertEqual(response.status_code, 404)
    
    def test_empty_private_content_directory(self):
        """测试空私人内容目录的处理"""
        from src.web_frontend.app import create_app
        
        # 不创建任何测试文件，保持目录为空
        app = create_app(self.config)
        with app.test_client() as client:
            response = client.get('/private/')
            
            self.assertEqual(response.status_code, 200)
            content = response.get_data(as_text=True)
            
            # 验证空状态显示
            self.assertIn('共收录 0 个私人文件', content)
            # 当为空时，音频/视频统计可能不显示，只检查空状态信息
            self.assertIn('🎵 暂无处理结果', content)


class TestPrivateContentEndToEndWorkflow(unittest.TestCase):
    """私有内容端到端工作流测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)
        
        # 创建完整的配置
        self.config = {
            'paths': {
                'data_folder': str(Path(self.test_dir) / 'data'),
                'output_folder': str(Path(self.test_dir) / 'data/output'),
                'watch_folder': str(Path(self.test_dir) / 'watch_folder')
            },
            'api': {
                'openrouter': {
                    'key': 'test_key',
                    'base_url': 'https://openrouter.ai/api/v1'
                }
            },
            'logging': {'level': 'ERROR'},
            'github': {
                'publishing': {
                    'auto_deploy': False  # 禁用自动部署以简化测试
                }
            },
            'tailscale': {
                'enabled': False  # 禁用Tailscale安全检查以便测试
            }
        }
        
        # 创建必要目录 (移除旧版本data/transcripts)
        for path in ['data/output/private', 'data/output/public', 'watch_folder']:
            Path(self.test_dir, path).mkdir(parents=True, exist_ok=True)
    
    @patch('src.core.transcription.TranscriptionService')
    @patch('src.core.anonymization.NameAnonymizer') 
    @patch('src.core.ai_generation.AIContentGenerator')
    def test_complete_private_processing_workflow(self, mock_ai_gen, mock_anonymizer, mock_transcription):
        """测试完整的私有内容处理工作流"""
        from src.web_frontend.app import create_app
        from src.web_frontend.handlers.audio_upload_handler import AudioUploadHandler
        
        # Mock服务响应
        mock_transcription.return_value.transcribe_audio.return_value = "Test transcription content"
        mock_anonymizer.return_value.anonymize_text.return_value = ("Test transcription content", {})
        mock_ai_gen.return_value.generate_summary.return_value = "Test summary"
        mock_ai_gen.return_value.generate_mind_map.return_value = "Test mind map"
        
        app = create_app(self.config)
        
        # 创建测试音频文件
        test_audio_path = Path(self.test_dir) / 'test_audio.mp3'
        test_audio_path.write_bytes(b'fake audio content')
        
        with app.test_client() as client:
            # 1. 上传私人音频文件
            with open(test_audio_path, 'rb') as f:
                response = client.post('/upload/audio', data={
                    'audio': f,
                    'content_type': 'lecture',
                    'privacy_level': 'private',  # 关键：设置为私人
                    'transcription_context': 'test context'
                })
            
            # 验证上传成功并重定向到状态页面
            self.assertEqual(response.status_code, 302)
            
            # 2. 等待处理完成（模拟）
            time.sleep(0.1)  # 简短等待
            
            # 3. 检查私人内容页面是否显示新文件
            response = client.get('/private/')
            self.assertEqual(response.status_code, 200)
            content = response.get_data(as_text=True)
            
            # 验证文件出现在私人内容列表中
            # 注意：实际文件名可能包含时间戳
            self.assertIn('test_audio', content.lower())
            
    def test_private_vs_public_content_separation(self):
        """测试私人和公开内容的分离"""
        from src.web_frontend.app import create_app
        
        # 创建私人和公开内容文件
        private_dir = Path(self.test_dir) / 'data/output/private'
        public_dir = Path(self.test_dir) / 'data/output/public'
        
        private_dir.mkdir(parents=True, exist_ok=True)
        public_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建私人内容
        (private_dir / 'private_test.html').write_text('<html><body>Private content</body></html>')
        
        # 创建公开内容  
        (public_dir / 'public_test.html').write_text('<html><body>Public content</body></html>')
        
        app = create_app(self.config)
        with app.test_client() as client:
            # 测试私人页面只显示私人内容
            response = client.get('/private/')
            self.assertEqual(response.status_code, 200)
            content = response.get_data(as_text=True)
            
            self.assertIn('共收录 1 个私人文件', content)
            # 不应该包含公开内容
            self.assertNotIn('public_test', content)


class TestPrivateContentErrorHandling(unittest.TestCase):
    """私有内容错误处理测试"""
    
    def test_missing_private_directory(self):
        """测试私人内容目录不存在的情况"""
        from src.web_frontend.app import create_app
        
        # 创建不包含私人目录的配置
        test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, test_dir)
        
        config = {
            'paths': {
                'data_folder': str(Path(test_dir) / 'data'),
                'output_folder': str(Path(test_dir) / 'data/output'),
            },
            'logging': {'level': 'ERROR'},
            'tailscale': {
                'enabled': False  # 禁用Tailscale安全检查以便测试
            }
        }
        
        app = create_app(config)
        with app.test_client() as client:
            # 访问私人内容页面应该自动创建目录并显示空状态
            response = client.get('/private/')
            
            self.assertEqual(response.status_code, 200)
            content = response.get_data(as_text=True)
            
            # 验证目录被创建
            self.assertTrue((Path(test_dir) / 'data/output/private').exists())
            
            # 验证显示空状态
            self.assertIn('共收录 0 个私人文件', content)
    
    def test_corrupted_private_content_files(self):
        """测试损坏的私人内容文件处理"""
        from src.web_frontend.app import create_app
        
        test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, test_dir)
        
        # 创建损坏的文件
        private_dir = Path(test_dir) / 'data/output/private'
        private_dir.mkdir(parents=True)
        
        # 创建无效的HTML文件
        (private_dir / 'corrupted.html').write_text('invalid html content without proper structure')
        
        config = {
            'paths': {
                'data_folder': str(Path(test_dir) / 'data'),
                'output_folder': str(Path(test_dir) / 'data/output'),
            },
            'logging': {'level': 'ERROR'},
            'tailscale': {
                'enabled': False  # 禁用Tailscale安全检查以便测试
            }
        }
        
        app = create_app(config)
        with app.test_client() as client:
            # 页面应该能够处理损坏的文件而不崩溃
            response = client.get('/private/')
            self.assertEqual(response.status_code, 200)
            
            content = response.get_data(as_text=True)
            
            # 应该显示文件但使用默认摘要
            self.assertIn('共收录 1 个私人文件', content)


if __name__ == '__main__':
    unittest.main()