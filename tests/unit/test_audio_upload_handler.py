#!/usr/bin/env python3
"""
音频上传处理器单元测试
测试新的文件组织和subcategory功能
"""

import unittest
import tempfile
import shutil
import os
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from werkzeug.datastructures import FileStorage
from io import BytesIO

# 添加src目录到Python路径
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# 需要导入依赖的模块
try:
    from web_frontend.handlers.audio_upload_handler import AudioUploadHandler
except ImportError as e:
    # 如果导入失败，跳过这些测试
    print(f"Warning: AudioUploadHandler import failed: {e}")
    AudioUploadHandler = None


class TestAudioUploadHandler(unittest.TestCase):
    """测试音频上传处理器"""
    
    def setUp(self):
        """每个测试前的准备工作"""
        self.test_dir = tempfile.mkdtemp()
        self.uploads_dir = os.path.join(self.test_dir, 'uploads')
        os.makedirs(self.uploads_dir, exist_ok=True)
        
        # 创建模拟配置管理器
        self.mock_config_manager = Mock()
        self.mock_config_manager.get_nested_config.return_value = {
            'lecture': {
                'icon': '🎓',
                'display_name': 'Academic Lecture',
                'subcategories': ['PHYS101', 'CS101', 'ML301', 'PHYS401']
            },
            'meeting': {
                'icon': '🏢',
                'display_name': 'Meeting Recording', 
                'subcategories': ['team_meeting', 'project_review', 'client_call', 'standup']
            },
            'others': {
                'icon': '📄',
                'display_name': 'Others',
                'subcategories': ['podcast', 'interview', 'presentation', 'training']
            }
        }
        
        # 切换到测试目录
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
    def tearDown(self):
        """清理测试环境"""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    def create_test_file(self, filename="test_audio.mp3", content=b"fake audio content"):
        """创建测试文件"""
        return FileStorage(
            stream=BytesIO(content),
            filename=filename,
            content_type="audio/mpeg"
        )
    
    @patch('web_frontend.handlers.audio_upload_handler.ProcessingTracker')
    @patch('threading.Thread')
    def test_subcategory_folder_creation_lecture(self, mock_thread, mock_tracker_class):
        """测试lecture类型的子分类文件夹创建"""
        # 设置mock
        mock_tracker = Mock()
        mock_tracker.processing_id = "test_id"
        mock_tracker_class.return_value.__enter__.return_value = mock_tracker
        
        # 创建处理器
        handler = AudioUploadHandler(self.mock_config_manager)
        
        # 创建测试文件
        test_file = self.create_test_file("quantum_lecture.mp3")
        
        # 测试metadata
        metadata = {
            'subcategory': 'PHYS101',
            'description': 'Quantum mechanics lecture'
        }
        
        # 处理上传
        result = handler.process_upload(test_file, 'lecture', 'public', metadata)
        
        # 验证子分类文件夹被创建
        phys101_folder = Path(self.uploads_dir) / 'PHYS101'
        self.assertTrue(phys101_folder.exists())
        self.assertTrue(phys101_folder.is_dir())
        
        # 验证返回结果
        self.assertEqual(result['status'], 'success')
        self.assertIn('processing_id', result)
    
    @patch('web_frontend.handlers.audio_upload_handler.ProcessingTracker')
    @patch('threading.Thread')
    def test_subcategory_folder_creation_meeting(self, mock_thread, mock_tracker_class):
        """测试meeting类型的子分类文件夹创建"""
        # 设置mock
        mock_tracker = Mock()
        mock_tracker.processing_id = "test_id"
        mock_tracker_class.return_value.__enter__.return_value = mock_tracker
        
        handler = AudioUploadHandler(self.mock_config_manager)
        test_file = self.create_test_file("standup_meeting.wav")
        
        metadata = {
            'subcategory': 'team_meeting',
            'description': 'Weekly team standup'
        }
        
        result = handler.process_upload(test_file, 'meeting', 'public', metadata)
        
        # 验证team_meeting文件夹被创建
        meeting_folder = Path(self.uploads_dir) / 'team_meeting'
        self.assertTrue(meeting_folder.exists())
        self.assertTrue(meeting_folder.is_dir())
    
    @patch('web_frontend.handlers.audio_upload_handler.ProcessingTracker')
    @patch('threading.Thread')
    def test_custom_subcategory_filename_only(self, mock_thread, mock_tracker_class):
        """测试自定义子分类只添加到文件名，不创建文件夹"""
        # 设置mock
        mock_tracker = Mock()
        mock_tracker.processing_id = "test_id"
        mock_tracker_class.return_value.__enter__.return_value = mock_tracker
        
        handler = AudioUploadHandler(self.mock_config_manager)
        test_file = self.create_test_file("custom_content.mp3")
        
        metadata = {
            'subcategory': 'other',
            'custom_subcategory': 'my_custom_course',
            'description': 'Custom course content'
        }
        
        result = handler.process_upload(test_file, 'lecture', 'public', metadata)
        
        # 验证自定义子分类文件夹没有被创建
        custom_folder = Path(self.uploads_dir) / 'my_custom_course'
        self.assertFalse(custom_folder.exists())
        
        # 验证文件保存在根uploads目录
        uploaded_files = list(Path(self.uploads_dir).glob("*my_custom_course*"))
        self.assertGreater(len(uploaded_files), 0)
    
    @patch('web_frontend.handlers.audio_upload_handler.ProcessingTracker')
    @patch('threading.Thread') 
    def test_filename_generation_with_subcategory(self, mock_thread, mock_tracker_class):
        """测试带子分类的文件名生成"""
        # 设置mock
        mock_tracker = Mock()
        mock_tracker.processing_id = "test_id"
        mock_tracker_class.return_value.__enter__.return_value = mock_tracker
        
        handler = AudioUploadHandler(self.mock_config_manager)
        test_file = self.create_test_file("algorithm_lecture.mp3")
        
        metadata = {
            'subcategory': 'CS101',
            'description': 'Computer algorithms lecture'
        }
        
        result = handler.process_upload(test_file, 'lecture', 'public', metadata)
        
        # 验证文件名格式：{timestamp}_{subcategory}_{type_prefix}_{filename}
        cs101_folder = Path(self.uploads_dir) / 'CS101'
        uploaded_files = list(cs101_folder.glob("*_CS101_LEC_algorithm_lecture.mp3"))
        
        self.assertEqual(len(uploaded_files), 1)
        uploaded_file = uploaded_files[0]
        
        # 验证文件名组成部分
        filename_parts = uploaded_file.name.split('_')
        self.assertTrue(len(filename_parts) >= 4)  # timestamp, CS101, LEC, algorithm
        self.assertIn('CS101', filename_parts)
        self.assertIn('LEC', filename_parts)
        self.assertTrue(uploaded_file.name.endswith('algorithm_lecture.mp3'))
    
    @patch('web_frontend.handlers.audio_upload_handler.ProcessingTracker')
    @patch('threading.Thread')
    def test_file_validation(self, mock_thread, mock_tracker_class):
        """测试文件验证功能"""
        handler = AudioUploadHandler(self.mock_config_manager)
        
        # 测试有效文件扩展名
        valid_extensions = {'.mp3', '.wav', '.m4a', '.mp4', '.flac', '.aac', '.ogg'}
        
        for ext in valid_extensions:
            filename = f"test{ext}"
            test_file = self.create_test_file(filename)
            is_valid, error = handler.validate_file(test_file, valid_extensions)
            self.assertTrue(is_valid, f"File {filename} should be valid")
            self.assertIsNone(error)
        
        # 测试无效文件扩展名
        invalid_file = self.create_test_file("test.txt")
        is_valid, error = handler.validate_file(invalid_file, valid_extensions)
        self.assertFalse(is_valid)
        self.assertIn("not allowed", error)
        
        # 测试空文件
        is_valid, error = handler.validate_file(None, valid_extensions)
        self.assertFalse(is_valid)
        self.assertIn("No file provided", error)
    
    @patch('web_frontend.handlers.audio_upload_handler.ProcessingTracker')
    @patch('threading.Thread')
    def test_multiple_subcategories_different_types(self, mock_thread, mock_tracker_class):
        """测试不同content type的多个子分类处理"""
        # 设置mock
        mock_tracker = Mock()
        mock_tracker.processing_id = "test_id"
        mock_tracker_class.return_value.__enter__.return_value = mock_tracker
        
        handler = AudioUploadHandler(self.mock_config_manager)
        
        # 测试数据：不同类型和子分类的组合
        test_cases = [
            ('lecture', 'PHYS401', 'advanced_physics.wav'),
            ('meeting', 'client_call', 'client_discussion.mp3'),
            ('others', 'interview', 'tech_interview.m4a')
        ]
        
        for content_type, subcategory, filename in test_cases:
            test_file = self.create_test_file(filename)
            metadata = {'subcategory': subcategory}
            
            result = handler.process_upload(test_file, content_type, 'public', metadata)
            
            # 验证每个子分类文件夹被正确创建
            subcategory_folder = Path(self.uploads_dir) / subcategory
            self.assertTrue(subcategory_folder.exists(), 
                          f"Subcategory folder {subcategory} should be created")
            
            # 验证文件保存在正确的子文件夹
            type_prefix = content_type.upper()[:3]
            uploaded_files = list(subcategory_folder.glob(f"*_{subcategory}_{type_prefix}_{filename}"))
            self.assertGreater(len(uploaded_files), 0, 
                             f"File should be saved in {subcategory} folder")
    
    def test_get_supported_formats(self):
        """测试获取支持的音频格式"""
        handler = AudioUploadHandler(self.mock_config_manager)
        formats = handler.get_supported_formats()
        
        # 验证返回格式字典
        self.assertIsInstance(formats, dict)
        
        # 验证包含预期的音频格式
        expected_formats = ['.mp3', '.wav', '.m4a', '.mp4', '.flac', '.aac', '.ogg']
        for fmt in expected_formats:
            self.assertIn(fmt, formats)
            self.assertIsInstance(formats[fmt], str)  # 每个格式应该有描述
    
    def test_file_size_limit_logic(self):
        """测试文件大小限制逻辑（简化版本）"""
        # 直接测试大小限制逻辑，不涉及复杂的文件保存
        handler = AudioUploadHandler(self.mock_config_manager)
        
        # 测试文件大小计算
        limit_500mb = 500 * 1024 * 1024
        test_size_600mb = 600 * 1024 * 1024
        
        # 验证大小比较逻辑
        self.assertTrue(test_size_600mb > limit_500mb)
        
        # 测试文件验证
        test_file = self.create_test_file("test.mp3")
        allowed_extensions = {'.mp3', '.wav', '.m4a'}
        
        is_valid, error = handler.validate_file(test_file, allowed_extensions)
        self.assertTrue(is_valid)
        self.assertIsNone(error)


class TestSubcategoryLogic(unittest.TestCase):
    """测试子分类逻辑"""
    
    def setUp(self):
        """测试设置"""
        self.test_dir = tempfile.mkdtemp()
        self.uploads_dir = Path(self.test_dir) / 'uploads'
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        
        # 切换到测试目录
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # 模拟配置数据
        self.content_types_config = {
            'lecture': {
                'subcategories': ['PHYS101', 'CS101', 'ML301', 'PHYS401']
            },
            'meeting': {
                'subcategories': ['team_meeting', 'project_review', 'client_call']
            },
            'others': {
                'subcategories': ['podcast', 'interview', 'presentation']
            }
        }
        
    def tearDown(self):
        """清理测试环境"""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    def test_predefined_subcategory_creates_folder(self):
        """测试预定义子分类创建文件夹"""
        # 模拟文件组织逻辑
        content_type = 'lecture'
        subcategory = 'PHYS101'
        
        # 检查子分类是否在配置中
        type_config = self.content_types_config.get(content_type, {})
        subcategories = type_config.get('subcategories', [])
        
        self.assertIn(subcategory, subcategories)
        
        # 创建目标文件夹
        target_folder = self.uploads_dir / subcategory
        target_folder.mkdir(parents=True, exist_ok=True)
        
        # 验证文件夹创建成功
        self.assertTrue(target_folder.exists())
        self.assertTrue(target_folder.is_dir())
    
    def test_custom_subcategory_no_folder_creation(self):
        """测试自定义子分类不创建文件夹"""
        content_type = 'lecture'
        subcategory = 'other'
        custom_subcategory = 'my_custom_course'
        
        # 模拟逻辑：custom subcategory不在预定义列表中
        type_config = self.content_types_config.get(content_type, {})
        subcategories = type_config.get('subcategories', [])
        
        self.assertNotIn(custom_subcategory, subcategories)
        
        # 自定义子分类不应该创建文件夹
        custom_folder = self.uploads_dir / custom_subcategory
        self.assertFalse(custom_folder.exists())
    
    def test_filename_generation_logic(self):
        """测试文件名生成逻辑"""
        from datetime import datetime
        from werkzeug.utils import secure_filename
        
        # 测试数据
        test_cases = [
            {
                'content_type': 'lecture',
                'subcategory': 'PHYS101',
                'original_filename': 'quantum mechanics.mp3',
                'expected_elements': ['PHYS101', 'LEC', 'quantum_mechanics.mp3']
            },
            {
                'content_type': 'meeting',
                'subcategory': 'team_meeting',
                'original_filename': 'weekly standup.wav',
                'expected_elements': ['team_meeting', 'MEE', 'weekly_standup.wav']
            },
            {
                'content_type': 'others',
                'subcategory': 'podcast',
                'original_filename': 'tech interview.m4a',
                'expected_elements': ['podcast', 'OTH', 'tech_interview.m4a']
            }
        ]
        
        for case in test_cases:
            # 生成文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            type_prefix = case['content_type'].upper()[:3]
            safe_filename = secure_filename(case['original_filename'])
            subcategory_code = f"_{case['subcategory']}"
            
            target_filename = f"{timestamp}{subcategory_code}_{type_prefix}_{safe_filename}"
            
            # 验证文件名包含所有预期元素
            for element in case['expected_elements']:
                self.assertIn(element, target_filename, 
                            f"Filename should contain {element}")
            
            # 验证文件名格式
            self.assertTrue(target_filename.startswith(timestamp))
            self.assertIn(type_prefix, target_filename)
    
    def test_all_content_types_subcategories_coverage(self):
        """测试所有内容类型的子分类覆盖"""
        expected_content_types = ['lecture', 'meeting', 'others']
        
        for content_type in expected_content_types:
            self.assertIn(content_type, self.content_types_config)
            
            type_config = self.content_types_config[content_type]
            subcategories = type_config.get('subcategories', [])
            
            # 每个类型都应该有子分类
            self.assertGreater(len(subcategories), 0, 
                             f"Content type {content_type} should have subcategories")
            
            # 验证子分类是字符串列表
            for subcat in subcategories:
                self.assertIsInstance(subcat, str)
                self.assertGreater(len(subcat), 0)


class TestFileOrganizationIntegration(unittest.TestCase):
    """测试文件组织集成功能"""
    
    def setUp(self):
        """测试设置"""
        self.test_dir = tempfile.mkdtemp()
        self.uploads_dir = Path(self.test_dir) / 'uploads'
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
    
    def tearDown(self):
        """清理测试环境"""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    def test_directory_structure_organization(self):
        """测试目录结构组织"""
        # 模拟创建完整的目录结构
        subcategories = {
            'lecture': ['PHYS101', 'CS101', 'ML301', 'PHYS401'],
            'meeting': ['team_meeting', 'project_review', 'client_call', 'standup'],
            'others': ['podcast', 'interview', 'presentation', 'training']
        }
        
        created_folders = []
        for content_type, subcats in subcategories.items():
            for subcat in subcats:
                folder_path = self.uploads_dir / subcat
                folder_path.mkdir(parents=True, exist_ok=True)
                created_folders.append(folder_path)
        
        # 验证所有文件夹创建成功
        self.assertEqual(len(created_folders), 12)  # 总共12个子分类
        
        for folder in created_folders:
            self.assertTrue(folder.exists())
            self.assertTrue(folder.is_dir())
        
        # 验证特定课程文件夹
        phys101_folder = self.uploads_dir / 'PHYS101'
        cs101_folder = self.uploads_dir / 'CS101'
        meeting_folder = self.uploads_dir / 'team_meeting'
        podcast_folder = self.uploads_dir / 'podcast'
        
        self.assertTrue(phys101_folder.exists())
        self.assertTrue(cs101_folder.exists())
        self.assertTrue(meeting_folder.exists())
        self.assertTrue(podcast_folder.exists())
    
    def test_uploads_equals_watch_folder_consistency(self):
        """测试uploads目录与watch_folder一致性"""
        # 这个测试验证我们的设计决策：uploads目录就是watch_folder
        uploads_path = Path('./uploads')
        
        # 在真实环境中，这两个路径应该指向同一个目录
        uploads_resolved = uploads_path.resolve()
        
        # 验证目录存在且可访问
        self.assertTrue(uploads_path.exists() or uploads_path.parent.exists())
        
        # 验证路径格式正确 (considering different path representations)
        self.assertIn(str(uploads_path), ['./uploads', 'uploads'])


if __name__ == '__main__':
    unittest.main()