#!/usr/bin/env python3
"""
GitHub部署监控集成测试

测试我们刚刚修复的GitHub deployment monitoring功能：
1. ProcessingStage import修复
2. PUBLISHING状态保持直到deployment验证
3. _check_github_deployment调用
4. deployment_checked标志机制
5. 真实部署状态检查集成
"""

import unittest
import tempfile
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path


class TestDeploymentMonitoringIntegration(unittest.TestCase):
    """测试GitHub部署监控集成功能"""
    
    def setUp(self):
        """设置测试环境"""
        # 创建临时配置
        self.test_config = {
            'github': {
                'username': 'testuser',
                'token': 'test_token',
                'repo_name': 'Test_Bach'
            }
        }
        
    def test_processing_stage_import_fix(self):
        """测试ProcessingStage导入修复"""
        try:
            # 测试ProcessingService能正确导入ProcessingStage
            from src.web_frontend.services.processing_service import ProcessingService, ProcessingStage
            
            # 验证ProcessingStage枚举包含必要的状态
            expected_stages = ['UPLOADED', 'TRANSCRIBING', 'ANONYMIZING', 'AI_GENERATING', 'PUBLISHING', 'COMPLETED', 'FAILED']
            for stage_name in expected_stages:
                self.assertTrue(hasattr(ProcessingStage, stage_name), f"ProcessingStage missing {stage_name}")
                
            # 验证PUBLISHING状态值
            self.assertEqual(ProcessingStage.PUBLISHING.value, "publishing")
            
        except ImportError as e:
            self.fail(f"ProcessingStage import failed: {e}")
    
    @patch('src.web_frontend.services.processing_service.create_deployment_monitor')
    def test_processing_service_with_deployment_monitor(self, mock_create_monitor):
        """测试ProcessingService集成GitHub deployment monitor"""
        from src.web_frontend.services.processing_service import ProcessingService
        
        # Mock deployment monitor
        mock_monitor = Mock()
        mock_create_monitor.return_value = mock_monitor
        
        # 初始化服务
        service = ProcessingService(config=self.test_config)
        
        # 验证deployment monitor已创建
        mock_create_monitor.assert_called_once_with(self.test_config)
        self.assertEqual(service.deployment_monitor, mock_monitor)
    
    def test_publishing_stage_deployment_checking(self):
        """测试PUBLISHING状态时的deployment检查机制"""
        from src.web_frontend.services.processing_service import ProcessingService, ProcessingStage
        
        with patch('src.web_frontend.services.processing_service.create_deployment_monitor'):
            service = ProcessingService(config=self.test_config)
            
            # 添加一个处理项目到PUBLISHING状态
            processing_id = "test-publishing-item"
            service._processing_items[processing_id] = {
                'id': processing_id,
                'type': 'audio',
                'status': 'processing',
                'stage': ProcessingStage.PUBLISHING.value,  # 关键：PUBLISHING状态
                'progress': 95,
                'started_at': datetime.now().isoformat(),
                'estimated_time': 300,
                'deployment_checked': False  # 尚未检查部署
            }
            
            # Mock the deployment check method
            with patch.object(service, '_check_github_deployment') as mock_check_deployment:
                # 调用cleanup方法，应该触发deployment检查
                service._cleanup_expired_items()
                
                # 验证deployment检查被调用
                mock_check_deployment.assert_called_once_with(processing_id)
    
    def test_github_deployment_check_workflow(self):
        """测试GitHub deployment检查工作流"""
        from src.web_frontend.services.processing_service import ProcessingService
        
        mock_monitor = Mock()
        
        with patch('src.web_frontend.services.processing_service.create_deployment_monitor', return_value=mock_monitor):
            service = ProcessingService(config=self.test_config)
            
            # 设置处理项目
            processing_id = "test-deployment-check"
            service._processing_items[processing_id] = {
                'id': processing_id,
                'type': 'audio',
                'status': 'processing',
                'progress': 95,
                'started_at': (datetime.now() - timedelta(minutes=1)).isoformat(),  # 1分钟前开始
                'estimated_time': 300,
                'deployment_checked': False,
                'commit_hash': 'abc123'
            }
            
            # Mock successful deployment status
            mock_monitor.check_pages_deployment_status.return_value = {
                'deployed': True,
                'status': 'success',
                'message': 'GitHub Pages deployment verified',
                'method': 'github_api'
            }
            
            # Mock _complete_item method
            with patch.object(service, '_complete_item') as mock_complete:
                # 调用deployment检查
                service._check_github_deployment(processing_id)
                
                # 验证部署状态检查被调用
                mock_monitor.check_pages_deployment_status.assert_called_once_with('abc123')
                
                # 验证项目被标记为完成
                mock_complete.assert_called_once_with(processing_id)
                
                # 验证进度更新为100%
                item = service._processing_items.get(processing_id)
                if item:
                    self.assertEqual(item['progress'], 100)
                    self.assertEqual(item['message'], 'GitHub Pages deployment verified')
    
    def test_deployment_check_failure_retry(self):
        """测试部署检查失败时的重试机制"""
        from src.web_frontend.services.processing_service import ProcessingService
        
        mock_monitor = Mock()
        
        with patch('src.web_frontend.services.processing_service.create_deployment_monitor', return_value=mock_monitor):
            service = ProcessingService(config=self.test_config)
            
            # 设置处理项目
            processing_id = "test-deployment-retry"
            service._processing_items[processing_id] = {
                'id': processing_id,
                'type': 'audio',
                'status': 'processing',
                'progress': 95,
                'started_at': (datetime.now() - timedelta(minutes=1)).isoformat(),
                'estimated_time': 300,
                'deployment_checked': False
            }
            
            # Mock deployment still in progress
            mock_monitor.check_pages_deployment_status.return_value = {
                'deployed': False,
                'status': 'deploying',
                'message': 'GitHub Pages deployment in progress',
                'method': 'github_api'
            }
            
            # 调用deployment检查
            service._check_github_deployment(processing_id)
            
            # 验证项目未完成，等待重试
            item = service._processing_items.get(processing_id)
            self.assertIsNotNone(item)
            self.assertEqual(item['progress'], 92)  # 降到92%等待重试
            self.assertEqual(item['message'], 'Waiting for GitHub Pages deployment...')
            self.assertFalse(item['deployment_checked'])  # 标记为需要重新检查
    
    def test_deployment_check_timeout_fallback(self):
        """测试部署检查超时时的回退机制"""
        from src.web_frontend.services.processing_service import ProcessingService
        
        # 不配置deployment monitor，测试回退逻辑
        with patch('src.web_frontend.services.processing_service.create_deployment_monitor', return_value=None):
            service = ProcessingService(config=self.test_config)
            
            # 设置一个超时的处理项目
            processing_id = "test-deployment-timeout"
            service._processing_items[processing_id] = {
                'id': processing_id,
                'type': 'audio',
                'status': 'processing',
                'progress': 95,
                'started_at': (datetime.now() - timedelta(minutes=6)).isoformat(),  # 6分钟前开始，超过5分钟超时
                'estimated_time': 300,
                'deployment_checked': False
            }
            
            # Mock _complete_item method
            with patch.object(service, '_complete_item') as mock_complete:
                # 调用deployment检查
                service._check_github_deployment(processing_id)
                
                # 验证超时后项目被完成
                mock_complete.assert_called_once_with(processing_id)
                
                # 验证fallback消息
                item = service._processing_items.get(processing_id)
                if item:
                    self.assertIn('timeout_fallback', item.get('deployment_method', ''))
    
    def test_end_to_end_deployment_monitoring_flow(self):
        """测试端到端部署监控流程"""
        from src.web_frontend.services.processing_service import ProcessingService, ProcessingStage
        
        mock_monitor = Mock()
        
        with patch('src.web_frontend.services.processing_service.create_deployment_monitor', return_value=mock_monitor):
            service = ProcessingService(config=self.test_config)
            
            # 1. 添加新处理项目
            processing_id = "test-end-to-end"
            success = service.add_processing_item(processing_id, "audio")
            self.assertTrue(success)  # 应该成功添加
            
            # 2. 模拟处理进度到PUBLISHING阶段
            item = service._processing_items.get(processing_id)
            item['stage'] = ProcessingStage.PUBLISHING.value
            item['progress'] = 95
            # 设置started_at为1分钟前，确保超过30秒检查阈值
            item['started_at'] = (datetime.now() - timedelta(minutes=1)).isoformat()
            
            # 3. Mock successful deployment
            mock_monitor.check_pages_deployment_status.return_value = {
                'deployed': True,
                'status': 'success',
                'message': 'GitHub Pages deployment verified'
            }
            
            # 4. 运行cleanup，应该检查deployment
            original_complete_item = service._complete_item
            completed_items = []
            
            def mock_complete_item(pid):
                completed_items.append(pid)
                return original_complete_item(pid)
            
            with patch.object(service, '_complete_item', side_effect=mock_complete_item):
                service._cleanup_expired_items()
                
                # 5. 验证deployment检查和完成流程
                self.assertIn(processing_id, completed_items)
                mock_monitor.check_pages_deployment_status.assert_called()


class TestDeploymentMonitoringErrorHandling(unittest.TestCase):
    """测试部署监控错误处理"""
    
    def test_deployment_monitor_creation_failure(self):
        """测试deployment monitor创建失败的处理"""
        from src.web_frontend.services.processing_service import ProcessingService
        
        # Mock create_deployment_monitor抛出异常
        with patch('src.web_frontend.services.processing_service.create_deployment_monitor', side_effect=Exception("GitHub API error")):
            # 服务应该能正常初始化，但没有deployment monitor
            service = ProcessingService(config={'github': {}})
            self.assertIsNone(service.deployment_monitor)
    
    def test_deployment_check_exception_handling(self):
        """测试部署检查异常处理"""
        from src.web_frontend.services.processing_service import ProcessingService
        
        mock_monitor = Mock()
        mock_monitor.check_pages_deployment_status.side_effect = Exception("API timeout")
        
        with patch('src.web_frontend.services.processing_service.create_deployment_monitor', return_value=mock_monitor):
            service = ProcessingService(config={'github': {}})
            
            # 设置处理项目 (started_at需要超过30秒才会调用deployment monitor)
            processing_id = "test-exception-handling"
            service._processing_items[processing_id] = {
                'id': processing_id,
                'type': 'audio',
                'status': 'processing',
                'progress': 95,
                'started_at': (datetime.now() - timedelta(seconds=60)).isoformat(),  # 1分钟前开始
                'estimated_time': 300,
                'deployment_checked': False
            }
            
            # Mock _complete_item method
            with patch.object(service, '_complete_item') as mock_complete:
                # 调用deployment检查，应该处理异常
                service._check_github_deployment(processing_id)
                
                # 验证异常时项目仍被完成
                mock_complete.assert_called_once_with(processing_id)


if __name__ == '__main__':
    unittest.main()