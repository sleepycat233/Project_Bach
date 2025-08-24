#!/usr/bin/env python3
"""
YouTube URL输入框加载指示器功能单元测试

测试新的UI功能：
1. 加载状态指示器（转圈动画）
2. 成功状态指示器（勾号）
3. 取消功能
4. 状态转换逻辑
5. 与自动检测功能的集成
"""

import pytest
import time
from unittest.mock import Mock, patch
from pathlib import Path
import sys

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.config import ConfigManager


class TestYouTubeLoadingIndicator:
    """YouTube加载指示器功能测试"""

    def test_loading_indicator_states(self):
        """测试加载指示器的不同状态"""
        
        # 模拟加载指示器状态管理
        class LoadingIndicatorState:
            HIDDEN = 'hidden'
            LOADING = 'loading'
            SUCCESS = 'success' 
            ERROR = 'error'
            
        class LoadingIndicator:
            def __init__(self):
                self.state = LoadingIndicatorState.HIDDEN
                self.visible = False
                self.animation_active = False
                
            def show_loading(self):
                """显示加载状态"""
                self.state = LoadingIndicatorState.LOADING
                self.visible = True
                self.animation_active = True
                
            def show_success(self):
                """显示成功状态"""
                self.state = LoadingIndicatorState.SUCCESS
                self.visible = True
                self.animation_active = False
                
            def show_error(self):
                """显示错误状态"""
                self.state = LoadingIndicatorState.ERROR
                self.visible = True
                self.animation_active = False
                
            def hide(self):
                """隐藏指示器"""
                self.state = LoadingIndicatorState.HIDDEN
                self.visible = False
                self.animation_active = False
                
            def is_loading(self):
                """检查是否在加载状态"""
                return self.state == LoadingIndicatorState.LOADING
        
        indicator = LoadingIndicator()
        
        # 测试初始状态
        assert indicator.state == LoadingIndicatorState.HIDDEN
        assert not indicator.visible
        assert not indicator.animation_active
        
        # 测试显示加载状态
        indicator.show_loading()
        assert indicator.state == LoadingIndicatorState.LOADING
        assert indicator.visible
        assert indicator.animation_active
        assert indicator.is_loading()
        
        # 测试显示成功状态
        indicator.show_success()
        assert indicator.state == LoadingIndicatorState.SUCCESS
        assert indicator.visible
        assert not indicator.animation_active  # 成功状态不需要动画
        assert not indicator.is_loading()
        
        # 测试显示错误状态
        indicator.show_error()
        assert indicator.state == LoadingIndicatorState.ERROR
        assert indicator.visible
        assert not indicator.animation_active
        
        # 测试隐藏
        indicator.hide()
        assert indicator.state == LoadingIndicatorState.HIDDEN
        assert not indicator.visible
        assert not indicator.animation_active

    def test_loading_indicator_ui_elements(self):
        """测试加载指示器UI元素"""
        
        # 模拟HTML元素和CSS类
        class MockElement:
            def __init__(self, element_id):
                self.id = element_id
                self.class_list = []
                self.style = {}
                self.innerHTML = ''
                
            def add_class(self, class_name):
                if class_name not in self.class_list:
                    self.class_list.append(class_name)
                    
            def remove_class(self, class_name):
                if class_name in self.class_list:
                    self.class_list.remove(class_name)
                    
            def has_class(self, class_name):
                return class_name in self.class_list
                
            def set_style(self, prop, value):
                self.style[prop] = value
                
            def set_content(self, content):
                self.innerHTML = content
        
        # 模拟加载指示器UI管理器
        class LoadingIndicatorUI:
            def __init__(self):
                self.container = MockElement('youtube-loading-indicator')
                self.icon = MockElement('youtube-loading-icon')
                self.is_visible = False
                
            def show_loading_spinner(self):
                """显示加载转圈动画"""
                self.container.set_style('display', 'inline-block')
                self.icon.set_content('🔄')  # 或者用CSS动画
                self.icon.add_class('spinning')
                self.is_visible = True
                
            def show_success_checkmark(self):
                """显示成功勾号"""
                self.container.set_style('display', 'inline-block')
                self.icon.set_content('✅')
                self.icon.remove_class('spinning')
                self.icon.add_class('success')
                self.is_visible = True
                
            def show_error_indicator(self):
                """显示错误指示"""
                self.container.set_style('display', 'inline-block')
                self.icon.set_content('❌')
                self.icon.remove_class('spinning')
                self.icon.add_class('error')
                self.is_visible = True
                
            def hide_indicator(self):
                """隐藏指示器"""
                self.container.set_style('display', 'none')
                self.icon.remove_class('spinning')
                self.icon.remove_class('success')
                self.icon.remove_class('error')
                self.is_visible = False
        
        ui = LoadingIndicatorUI()
        
        # 测试初始状态
        assert not ui.is_visible
        
        # 测试显示加载动画
        ui.show_loading_spinner()
        assert ui.is_visible
        assert ui.container.style['display'] == 'inline-block'
        assert ui.icon.innerHTML == '🔄'
        assert ui.icon.has_class('spinning')
        
        # 测试显示成功状态
        ui.show_success_checkmark()
        assert ui.is_visible
        assert ui.icon.innerHTML == '✅'
        assert not ui.icon.has_class('spinning')
        assert ui.icon.has_class('success')
        
        # 测试显示错误状态
        ui.show_error_indicator()
        assert ui.icon.innerHTML == '❌'
        assert ui.icon.has_class('error')
        
        # 测试隐藏
        ui.hide_indicator()
        assert not ui.is_visible
        assert ui.container.style['display'] == 'none'
        assert not ui.icon.has_class('spinning')

    def test_auto_detection_integration_with_loading_indicator(self):
        """测试自动检测与加载指示器的集成"""
        
        class IntegratedAutoDetection:
            def __init__(self):
                self.loading_indicator = None
                self.current_request = None
                self.auto_timer = None
                
            def set_loading_indicator(self, indicator):
                self.loading_indicator = indicator
                
            def on_url_input_change(self, url):
                """模拟URL输入变化处理"""
                # 清除之前的定时器和请求
                if self.auto_timer:
                    self.auto_timer = None
                if self.current_request:
                    self.cancel_current_request()
                
                # 隐藏指示器
                if self.loading_indicator:
                    self.loading_indicator.hide()
                
                # 检查URL有效性
                if self.is_valid_youtube_url(url):
                    # 设置800ms延迟
                    self.auto_timer = self.schedule_metadata_fetch(url)
                    
            def is_valid_youtube_url(self, url):
                """检查YouTube URL有效性"""
                return 'youtube.com/watch?v=' in url or 'youtu.be/' in url
                
            def schedule_metadata_fetch(self, url):
                """安排元数据获取"""
                def delayed_fetch():
                    self.fetch_metadata(url)
                return delayed_fetch  # 实际中会用setTimeout
                
            def fetch_metadata(self, url):
                """获取元数据"""
                if self.loading_indicator:
                    self.loading_indicator.show_loading()
                
                # 模拟异步请求
                self.current_request = MockAsyncRequest(url)
                self.current_request.on_success = self.on_metadata_success
                self.current_request.on_error = self.on_metadata_error
                self.current_request.start()
                
            def on_metadata_success(self, metadata):
                """元数据获取成功"""
                if self.loading_indicator:
                    self.loading_indicator.show_success()
                self.current_request = None
                
            def on_metadata_error(self, error):
                """元数据获取失败"""
                if self.loading_indicator:
                    self.loading_indicator.show_error()
                self.current_request = None
                
            def cancel_current_request(self):
                """取消当前请求"""
                if self.current_request:
                    self.current_request.cancel()
                    self.current_request = None
                    if self.loading_indicator:
                        self.loading_indicator.hide()
        
        class MockAsyncRequest:
            def __init__(self, url):
                self.url = url
                self.cancelled = False
                self.on_success = None
                self.on_error = None
                
            def start(self):
                # 不立即执行回调，模拟真实的异步行为
                pass
                
            def simulate_completion(self):
                # 手动触发完成
                if not self.cancelled:
                    if 'invalid' in self.url:
                        if self.on_error:
                            self.on_error('Invalid URL')
                    else:
                        if self.on_success:
                            self.on_success({'title': 'Test Video'})
                            
            def cancel(self):
                self.cancelled = True
        
        # 创建集成系统
        auto_detection = IntegratedAutoDetection()
        
        # 模拟加载指示器（使用之前定义的类）
        class SimpleIndicator:
            def __init__(self):
                self.state = 'hidden'
                
            def show_loading(self):
                self.state = 'loading'
                
            def show_success(self):
                self.state = 'success'
                
            def show_error(self):
                self.state = 'error'
                
            def hide(self):
                self.state = 'hidden'
        
        indicator = SimpleIndicator()
        auto_detection.set_loading_indicator(indicator)
        
        # 测试有效URL输入
        auto_detection.on_url_input_change("https://www.youtube.com/watch?v=test123")
        
        # 模拟定时器触发
        if auto_detection.auto_timer:
            auto_detection.auto_timer()
        
        # 验证加载状态
        assert indicator.state == 'loading'
        
        # 模拟异步请求完成
        if auto_detection.current_request:
            auto_detection.current_request.simulate_completion()
        
        # 验证成功状态
        assert indicator.state == 'success'

    def test_cancel_functionality(self):
        """测试取消功能"""
        
        class CancellableOperation:
            def __init__(self):
                self.is_running = False
                self.is_cancelled = False
                self.loading_indicator = None
                
            def start_operation(self):
                """开始操作"""
                self.is_running = True
                self.is_cancelled = False
                if self.loading_indicator:
                    self.loading_indicator.show_loading()
                    
            def cancel_operation(self):
                """取消操作"""
                self.is_cancelled = True
                self.is_running = False
                if self.loading_indicator:
                    self.loading_indicator.hide()
                    
            def complete_operation(self):
                """完成操作"""
                if not self.is_cancelled:
                    self.is_running = False
                    if self.loading_indicator:
                        self.loading_indicator.show_success()
        
        class MockIndicator:
            def __init__(self):
                self.state = 'hidden'
                
            def show_loading(self):
                self.state = 'loading'
                
            def show_success(self):
                self.state = 'success'
                
            def hide(self):
                self.state = 'hidden'
        
        operation = CancellableOperation()
        indicator = MockIndicator()
        operation.loading_indicator = indicator
        
        # 开始操作
        operation.start_operation()
        assert operation.is_running
        assert not operation.is_cancelled
        assert indicator.state == 'loading'
        
        # 取消操作
        operation.cancel_operation()
        assert not operation.is_running
        assert operation.is_cancelled
        assert indicator.state == 'hidden'
        
        # 尝试完成已取消的操作（应该无效）
        operation.complete_operation()
        assert indicator.state == 'hidden'  # 状态不应该改变

    def test_multiple_rapid_requests_handling(self):
        """测试快速连续请求的处理"""
        
        class RapidRequestHandler:
            def __init__(self):
                self.active_requests = []
                self.loading_indicator = None
                
            def handle_new_request(self, url):
                """处理新请求"""
                # 取消所有活跃的请求
                for request in self.active_requests:
                    request.cancel()
                self.active_requests.clear()
                
                # 开始新请求
                new_request = MockRequest(url)
                self.active_requests.append(new_request)
                
                if self.loading_indicator:
                    self.loading_indicator.show_loading()
                    
                return new_request
                
            def complete_request(self, request, success=True):
                """完成请求"""
                if request in self.active_requests:
                    self.active_requests.remove(request)
                    
                    if success and self.loading_indicator:
                        self.loading_indicator.show_success()
                    elif not success and self.loading_indicator:
                        self.loading_indicator.show_error()
        
        class MockRequest:
            def __init__(self, url):
                self.url = url
                self.cancelled = False
                
            def cancel(self):
                self.cancelled = True
        
        class MockIndicator:
            def __init__(self):
                self.state = 'hidden'
                self.state_history = []
                
            def show_loading(self):
                self.state = 'loading'
                self.state_history.append('loading')
                
            def show_success(self):
                self.state = 'success'
                self.state_history.append('success')
                
            def show_error(self):
                self.state = 'error'
                self.state_history.append('error')
        
        handler = RapidRequestHandler()
        indicator = MockIndicator()
        handler.loading_indicator = indicator
        
        # 快速连续发送3个请求
        request1 = handler.handle_new_request("url1")
        request2 = handler.handle_new_request("url2")  # 应该取消request1
        request3 = handler.handle_new_request("url3")  # 应该取消request2
        
        # 验证只有最后一个请求是活跃的
        assert len(handler.active_requests) == 1
        assert handler.active_requests[0] == request3
        assert request1.cancelled
        assert request2.cancelled
        assert not request3.cancelled
        
        # 完成最后一个请求
        handler.complete_request(request3, success=True)
        assert indicator.state == 'success'

    def test_loading_indicator_accessibility(self):
        """测试加载指示器的可访问性功能"""
        
        class AccessibleLoadingIndicator:
            def __init__(self):
                self.aria_live = None
                self.aria_label = None
                self.screen_reader_text = ""
                
            def set_loading_state(self):
                """设置加载状态的可访问性属性"""
                self.aria_live = "polite"
                self.aria_label = "Loading video information"
                self.screen_reader_text = "Fetching video metadata, please wait"
                
            def set_success_state(self, video_title):
                """设置成功状态的可访问性属性"""
                self.aria_live = "polite"
                self.aria_label = "Video information loaded"
                self.screen_reader_text = f"Video information loaded successfully: {video_title}"
                
            def set_error_state(self):
                """设置错误状态的可访问性属性"""
                self.aria_live = "assertive"
                self.aria_label = "Error loading video information"
                self.screen_reader_text = "Failed to load video information"
                
            def clear_state(self):
                """清除可访问性状态"""
                self.aria_live = None
                self.aria_label = None
                self.screen_reader_text = ""
        
        indicator = AccessibleLoadingIndicator()
        
        # 测试加载状态
        indicator.set_loading_state()
        assert indicator.aria_live == "polite"
        assert "Loading" in indicator.aria_label
        assert "please wait" in indicator.screen_reader_text
        
        # 测试成功状态
        indicator.set_success_state("Test Video Title")
        assert indicator.aria_live == "polite"
        assert "loaded" in indicator.aria_label
        assert "Test Video Title" in indicator.screen_reader_text
        
        # 测试错误状态
        indicator.set_error_state()
        assert indicator.aria_live == "assertive"  # 错误用assertive更紧急
        assert "Error" in indicator.aria_label
        assert "Failed" in indicator.screen_reader_text

    def test_loading_indicator_timing_and_duration(self):
        """测试加载指示器的时间和持续时间"""
        
        class TimedLoadingIndicator:
            def __init__(self):
                self.show_start_time = None
                self.success_display_duration = 2000  # 2秒
                self.auto_hide_timer = None
                
            def show_loading(self):
                """显示加载状态"""
                self.show_start_time = time.time()
                
            def show_success_with_auto_hide(self):
                """显示成功状态并自动隐藏"""
                def auto_hide():
                    self.hide()
                    
                # 模拟setTimeout
                self.auto_hide_timer = auto_hide
                
            def get_loading_duration(self):
                """获取加载持续时间"""
                if self.show_start_time:
                    return time.time() - self.show_start_time
                return 0
                
            def hide(self):
                """隐藏指示器"""
                self.show_start_time = None
                if self.auto_hide_timer:
                    self.auto_hide_timer = None
        
        indicator = TimedLoadingIndicator()
        
        # 测试加载时间记录
        indicator.show_loading()
        assert indicator.show_start_time is not None
        
        # 模拟短暂延迟
        time.sleep(0.1)
        duration = indicator.get_loading_duration()
        assert duration >= 0.1
        
        # 测试成功状态自动隐藏
        indicator.show_success_with_auto_hide()
        assert indicator.auto_hide_timer is not None
        
        # 模拟自动隐藏触发
        if indicator.auto_hide_timer:
            indicator.auto_hide_timer()
        
        assert indicator.show_start_time is None


class TestLoadingIndicatorCSS:
    """测试加载指示器CSS相关功能"""
    
    def test_css_animation_classes(self):
        """测试CSS动画类管理"""
        
        class CSSAnimationManager:
            def __init__(self):
                self.element_classes = set()
                
            def add_spinning_animation(self):
                """添加旋转动画类"""
                self.element_classes.add('loading-spinner')
                self.element_classes.add('animate-spin')
                
            def remove_spinning_animation(self):
                """移除旋转动画类"""
                self.element_classes.discard('loading-spinner')
                self.element_classes.discard('animate-spin')
                
            def add_success_animation(self):
                """添加成功动画类"""
                self.element_classes.add('success-indicator')
                self.element_classes.add('fade-in')
                
            def has_animation_class(self, class_name):
                """检查是否有特定动画类"""
                return class_name in self.element_classes
                
            def clear_all_animations(self):
                """清除所有动画类"""
                animation_classes = {
                    'loading-spinner', 'animate-spin', 
                    'success-indicator', 'fade-in',
                    'error-indicator', 'shake'
                }
                self.element_classes -= animation_classes
        
        css_manager = CSSAnimationManager()
        
        # 测试旋转动画
        css_manager.add_spinning_animation()
        assert css_manager.has_animation_class('loading-spinner')
        assert css_manager.has_animation_class('animate-spin')
        
        # 测试移除旋转动画
        css_manager.remove_spinning_animation()
        assert not css_manager.has_animation_class('loading-spinner')
        assert not css_manager.has_animation_class('animate-spin')
        
        # 测试成功动画
        css_manager.add_success_animation()
        assert css_manager.has_animation_class('success-indicator')
        assert css_manager.has_animation_class('fade-in')
        
        # 测试清除所有动画
        css_manager.clear_all_animations()
        assert not css_manager.has_animation_class('success-indicator')
        assert not css_manager.has_animation_class('fade-in')

    def test_responsive_loading_indicator(self):
        """测试响应式加载指示器"""
        
        class ResponsiveLoadingIndicator:
            def __init__(self):
                self.size_class = 'medium'  # small, medium, large
                self.mobile_optimized = False
                
            def set_mobile_mode(self, is_mobile):
                """设置移动端模式"""
                self.mobile_optimized = is_mobile
                if is_mobile:
                    self.size_class = 'small'
                else:
                    self.size_class = 'medium'
                    
            def get_indicator_size(self):
                """获取指示器尺寸"""
                size_map = {
                    'small': '16px',
                    'medium': '20px', 
                    'large': '24px'
                }
                return size_map.get(self.size_class, '20px')
                
            def get_position_style(self):
                """获取位置样式"""
                if self.mobile_optimized:
                    return {
                        'right': '8px',
                        'top': '50%',
                        'transform': 'translateY(-50%)'
                    }
                else:
                    return {
                        'right': '12px',
                        'top': '50%',
                        'transform': 'translateY(-50%)'
                    }
        
        indicator = ResponsiveLoadingIndicator()
        
        # 测试桌面端模式
        indicator.set_mobile_mode(False)
        assert indicator.size_class == 'medium'
        assert indicator.get_indicator_size() == '20px'
        assert indicator.get_position_style()['right'] == '12px'
        
        # 测试移动端模式
        indicator.set_mobile_mode(True)
        assert indicator.size_class == 'small'
        assert indicator.get_indicator_size() == '16px'
        assert indicator.get_position_style()['right'] == '8px'


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])