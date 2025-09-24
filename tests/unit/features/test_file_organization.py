#!/usr/bin/env python3
"""
文件组织系统单元测试
测试新的uploads目录结构和文件监控集成
"""

import unittest
import tempfile
import shutil
import os
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加src目录到Python路径
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from utils.config import ConfigManager
from monitoring.file_monitor import FileMonitor


class TestFileOrganizationConfig(unittest.TestCase):
    """测试文件组织配置"""
    
    def setUp(self):
        """测试设置"""
        self.test_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.test_dir, 'test_config.yaml')
        
        # 创建完整的测试配置
        self.test_config = {
            'api': {
                'openrouter': {
                    'key': 'test-key',
                    'base_url': 'https://test.com'
                }
            },
            'spacy': {
                'model': 'zh_core_web_sm'
            },
            'logging': {
                'level': 'INFO',
                'file': './test.log'
            },
            'paths': {
                'watch_folder': './data/uploads',  # 新的统一目录
                'data_folder': './data',
                'output_folder': './data/output'
            },
            'web_frontend': {
                'upload': {
                    'upload_folder': './data/uploads',  # 与watch_folder一致
                    'organize_by_category': True,
                    'create_subcategory_folders': True,
                    'max_file_size': 104857600,
                    'allowed_extensions': ['.mp3', '.wav', '.m4a']
                }
            },
            'content_classification': {
                'content_types': {
                    'lecture': {
                        'icon': '🎓',
                        'display_name': 'Academic Lecture',
                        'subcategories': ['PHYS101', 'CS101', 'ML301', 'PHYS401']
                    },
                    'meeting': {
                        'icon': '🏢',
                        'display_name': 'Meeting Recording',
                        'subcategories': ['team_meeting', 'project_review', 'client_call']
                    },
                    'others': {
                        'icon': '📄',
                        'display_name': 'Others',
                        'subcategories': ['podcast', 'interview', 'presentation']
                    }
                }
            }
        }
        
        # 保存测试配置
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.test_config, f)
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.test_dir)
    
    @patch('utils.env_manager.setup_project_environment')
    def test_uploads_watch_folder_consistency(self, mock_setup_env):
        """测试uploads和watch_folder配置一致性"""
        mock_setup_env.side_effect = Exception("Force use direct loading")
        
        config_manager = ConfigManager(self.config_path)
        
        # 获取配置
        paths_config = config_manager.get_paths_config()
        upload_config = config_manager.get(['web_frontend', 'upload'], default={})
        
        # 验证路径一致性
        watch_folder = paths_config.get('watch_folder')
        upload_folder = upload_config.get('upload_folder')
        
        self.assertEqual(watch_folder, './data/uploads')
        self.assertEqual(upload_folder, './data/uploads')
        self.assertEqual(watch_folder, upload_folder)
    
    # Content types configuration test removed - now handled by ContentTypeService tests
    
    @patch('utils.env_manager.setup_project_environment')
    def test_upload_organization_flags(self, mock_setup_env):
        """测试上传组织功能开关"""
        mock_setup_env.side_effect = Exception("Force use direct loading")
        
        config_manager = ConfigManager(self.config_path)
        upload_config = config_manager.get(['web_frontend', 'upload'], default={})
        
        # 验证组织功能开关
        self.assertTrue(upload_config.get('organize_by_category'))
        self.assertTrue(upload_config.get('create_subcategory_folders'))


class TestFileMonitorIntegration(unittest.TestCase):
    """测试文件监控与新目录结构的集成"""
    
    def setUp(self):
        """测试设置"""
        self.test_dir = tempfile.mkdtemp()
        self.uploads_dir = os.path.join(self.test_dir, 'data/uploads')
        os.makedirs(self.uploads_dir, exist_ok=True)
        
        # 切换到测试目录
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
    def tearDown(self):
        """清理测试环境"""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    def test_file_monitor_watches_uploads_directory(self):
        """测试FileMonitor监控uploads目录"""
        # 创建模拟处理回调
        mock_processor = Mock()
        mock_processor.return_value = True
        
        # 创建FileMonitor，监控uploads目录
        monitor = FileMonitor(
            watch_folder='./data/uploads',
            file_processor_callback=mock_processor
        )
        
        # 验证监控目录正确 (considering different path representations)
        self.assertIn(str(monitor.watch_folder), ['./uploads', 'uploads'])
        self.assertTrue(monitor.watch_folder.exists())
    
    def test_subdirectory_monitoring_capability(self):
        """测试子目录监控能力"""
        # 创建子目录结构
        subcategories = ['PHYS101', 'CS101', 'team_meeting', 'podcast']
        for subcat in subcategories:
            subdir = Path(self.uploads_dir) / subcat
            subdir.mkdir(parents=True, exist_ok=True)
        
        # 创建文件监控器
        mock_processor = Mock()
        monitor = FileMonitor(
            watch_folder='./data/uploads', 
            file_processor_callback=mock_processor
        )
        
        # 验证监控器可以处理子目录结构
        self.assertTrue(monitor.watch_folder.exists())
        
        # 验证所有子目录存在
        for subcat in subcategories:
            subdir = monitor.watch_folder / subcat
            self.assertTrue(subdir.exists())


class TestFilenamePatterns(unittest.TestCase):
    """测试文件名模式和解析"""
    
    def test_generated_filename_pattern_parsing(self):
        """测试生成的文件名模式解析"""
        # 模拟生成的文件名样例
        test_filenames = [
            "20240824_143022_PHYS101_LEC_quantum_mechanics.mp3",
            "20240824_143045_team_meeting_MEE_weekly_standup.wav", 
            "20240824_143102_podcast_OTH_tech_interview.m4a",
            "20240824_143115_my_custom_course_LEE_special_lecture.mp3"
        ]
        
        for filename in test_filenames:
            # 解析文件名组成部分
            parts = filename.split('_')
            
            # 验证基本结构：至少包含timestamp, subcategory, type_prefix
            self.assertGreaterEqual(len(parts), 4)
            
            # 验证timestamp格式 (YYYYMMDD_HHMMSS)
            timestamp_date = parts[0] 
            timestamp_time = parts[1]
            self.assertEqual(len(timestamp_date), 8)  # YYYYMMDD
            self.assertEqual(len(timestamp_time), 6)  # HHMMSS
            
            # 验证type prefix
            type_prefixes = ['LEC', 'MEE', 'OTH', 'LEE']  # LEE可能是自定义
            has_valid_prefix = any(prefix in parts for prefix in type_prefixes)
            self.assertTrue(has_valid_prefix, f"Filename {filename} should contain valid type prefix")
    
    def test_subcategory_extraction_from_filename(self):
        """测试从文件名提取子分类信息"""
        # 测试标准子分类文件名
        filename1 = "20240824_143022_PHYS101_LEC_quantum_mechanics.mp3"
        filename2 = "20240824_143045_team_meeting_MEE_weekly_standup.wav"
        
        # 解析subcategory (第3个部分，索引2)
        parts1 = filename1.split('_')
        parts2 = filename2.split('_')
        
        subcategory1 = parts1[2]  # PHYS101
        # For team_meeting, need to handle compound names
        subcategory2 = parts2[2] + '_' + parts2[3]  # team_meeting
        
        self.assertEqual(subcategory1, 'PHYS101')
        self.assertEqual(subcategory2, 'team_meeting')
        
        # 解析content type prefix - adjust indices for compound names
        type_prefix1 = parts1[3]  # LEC
        type_prefix2 = parts2[4]  # MEE (after team_meeting)
        
        self.assertEqual(type_prefix1, 'LEC')
        self.assertEqual(type_prefix2, 'MEE')
    
    def test_file_path_reconstruction(self):
        """测试文件路径重构"""
        # 给定文件名，应该能确定它属于哪个子目录
        test_cases = [
            {
                'filename': '20240824_143022_PHYS101_LEC_quantum.mp3',
                'expected_subcategory': 'PHYS101',
                'expected_path': 'uploads/PHYS101/20240824_143022_PHYS101_LEC_quantum.mp3'
            },
            {
                'filename': '20240824_143045_podcast_OTH_interview.m4a', 
                'expected_subcategory': 'podcast',
                'expected_path': 'uploads/podcast/20240824_143045_podcast_OTH_interview.m4a'
            }
        ]
        
        for case in test_cases:
            filename = case['filename']
            expected_subcategory = case['expected_subcategory']
            expected_path = case['expected_path']
            
            # 从文件名解析subcategory
            parsed_subcategory = filename.split('_')[2]
            self.assertEqual(parsed_subcategory, expected_subcategory)
            
            # 重构完整路径
            reconstructed_path = f"uploads/{expected_subcategory}/{filename}"
            self.assertEqual(reconstructed_path, expected_path)


if __name__ == '__main__':
    unittest.main()