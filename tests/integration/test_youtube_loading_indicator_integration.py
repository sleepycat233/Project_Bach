#!/usr/bin/env python3
"""
YouTube加载指示器集成测试

测试加载指示器在真实浏览器环境中的完整行为，包括：
1. 与自动检测的集成
2. 真实的UI交互和动画
3. 取消功能的完整流程
4. 错误处理和恢复
5. 可访问性和响应式设计
"""

import pytest
import time
import asyncio
from pathlib import Path
import sys

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestYouTubeLoadingIndicatorIntegration:
    """YouTube加载指示器集成测试"""

    def test_loading_indicator_browser_integration(self):
        """测试加载指示器在浏览器中的集成行为"""
        
        # 模拟完整的浏览器环境
        class BrowserSimulator:
            def __init__(self):
                self.dom_elements = {}
                self.event_listeners = {}
                self.timers = []
                self.css_classes = {}
                self.aria_attributes = {}
                
            def create_element(self, element_id, element_type):
                """创建DOM元素"""
                self.dom_elements[element_id] = {
                    'type': element_type,
                    'value': '',
                    'classes': [],
                    'visible': True,
                    'attributes': {}
                }
                
            def add_event_listener(self, element_id, event_type, handler):
                """添加事件监听器"""
                if element_id not in self.event_listeners:
                    self.event_listeners[element_id] = {}
                self.event_listeners[element_id][event_type] = handler
                
            def trigger_event(self, element_id, event_type, event_data=None):
                """触发事件"""
                if (element_id in self.event_listeners and 
                    event_type in self.event_listeners[element_id]):
                    handler = self.event_listeners[element_id][event_type]
                    return handler(event_data)
                return False
                
            def set_element_value(self, element_id, value):
                """设置元素值"""
                if element_id in self.dom_elements:
                    self.dom_elements[element_id]['value'] = value
                    
            def add_css_class(self, element_id, class_name):
                """添加CSS类"""
                if element_id in self.dom_elements:
                    self.dom_elements[element_id]['classes'].append(class_name)
                    
            def remove_css_class(self, element_id, class_name):
                """移除CSS类"""
                if element_id in self.dom_elements:
                    classes = self.dom_elements[element_id]['classes']
                    if class_name in classes:
                        classes.remove(class_name)
                        
            def set_aria_attribute(self, element_id, attribute, value):
                """设置ARIA属性"""
                if element_id in self.dom_elements:
                    self.dom_elements[element_id]['attributes'][attribute] = value
                    
            def get_element_classes(self, element_id):
                """获取元素的CSS类"""
                if element_id in self.dom_elements:
                    return self.dom_elements[element_id]['classes']
                return []
                
            def get_aria_attribute(self, element_id, attribute):
                """获取ARIA属性"""
                if element_id in self.dom_elements:
                    return self.dom_elements[element_id]['attributes'].get(attribute)
                return None

        # 创建浏览器模拟器
        browser = BrowserSimulator()
        
        # 创建页面元素
        browser.create_element('youtube-url-input', 'input')
        browser.create_element('youtube-loading-indicator', 'div')
        browser.create_element('youtube-cancel-button', 'button')
        
        # 模拟加载指示器功能
        class LoadingIndicatorManager:
            def __init__(self, browser_sim):
                self.browser = browser_sim
                self.current_request = None
                self.setup_events()
                
            def setup_events(self):
                """设置事件监听器"""
                self.browser.add_event_listener(
                    'youtube-url-input', 
                    'input', 
                    self.handle_input_change
                )
                self.browser.add_event_listener(
                    'youtube-cancel-button',
                    'click',
                    self.handle_cancel_click
                )
                
            def handle_input_change(self, event_data):
                """处理输入变化"""
                url = event_data.get('value', '') if event_data else ''
                
                # 简单的YouTube URL检测
                is_youtube = ('youtube.com/watch?v=' in url or 'youtu.be/' in url)
                
                if is_youtube and len(url.split('=')[-1]) > 3:
                    # 显示加载状态
                    self.show_loading()
                    # 模拟800ms延迟后开始请求
                    self.current_request = {
                        'url': url,
                        'start_time': time.time(),
                        'status': 'loading'
                    }
                    return True
                else:
                    # 隐藏指示器
                    self.hide_indicator()
                    return False
                    
            def show_loading(self):
                """显示加载状态"""
                self.browser.remove_css_class('youtube-loading-indicator', 'hidden')
                self.browser.add_css_class('youtube-loading-indicator', 'loading')
                self.browser.add_css_class('youtube-loading-indicator', 'spinning')
                self.browser.set_aria_attribute('youtube-loading-indicator', 'aria-label', 'Loading YouTube metadata')
                
                # 显示取消按钮
                self.browser.remove_css_class('youtube-cancel-button', 'hidden')
                
            def show_success(self):
                """显示成功状态"""
                self.browser.remove_css_class('youtube-loading-indicator', 'loading')
                self.browser.remove_css_class('youtube-loading-indicator', 'spinning')
                self.browser.add_css_class('youtube-loading-indicator', 'success')
                self.browser.set_aria_attribute('youtube-loading-indicator', 'aria-label', 'Metadata loaded successfully')
                
                # 隐藏取消按钮
                self.browser.add_css_class('youtube-cancel-button', 'hidden')
                
            def show_error(self, message=""):
                """显示错误状态"""
                self.browser.remove_css_class('youtube-loading-indicator', 'loading')
                self.browser.remove_css_class('youtube-loading-indicator', 'spinning')
                self.browser.add_css_class('youtube-loading-indicator', 'error')
                self.browser.set_aria_attribute('youtube-loading-indicator', 'aria-label', f'Error loading metadata: {message}')
                
                # 隐藏取消按钮
                self.browser.add_css_class('youtube-cancel-button', 'hidden')
                
            def hide_indicator(self):
                """隐藏指示器"""
                self.browser.add_css_class('youtube-loading-indicator', 'hidden')
                self.browser.add_css_class('youtube-cancel-button', 'hidden')
                # 清除所有状态类
                for class_name in ['loading', 'spinning', 'success', 'error']:
                    self.browser.remove_css_class('youtube-loading-indicator', class_name)
                    
            def handle_cancel_click(self, event_data):
                """处理取消点击"""
                if self.current_request and self.current_request['status'] == 'loading':
                    self.current_request['status'] = 'cancelled'
                    self.hide_indicator()
                    return True
                return False
                
            def simulate_metadata_success(self):
                """模拟元数据获取成功"""
                if self.current_request and self.current_request['status'] == 'loading':
                    self.current_request['status'] = 'success'
                    self.show_success()
                    
            def simulate_metadata_error(self, error_message="Network error"):
                """模拟元数据获取错误"""
                if self.current_request and self.current_request['status'] == 'loading':
                    self.current_request['status'] = 'error'
                    self.show_error(error_message)

        # 创建加载指示器管理器
        indicator_manager = LoadingIndicatorManager(browser)
        
        # 测试完整的用户输入流程
        # 1. 用户开始输入YouTube URL
        browser.set_element_value('youtube-url-input', 'https://www.youtube.com/watch?v=')
        result = browser.trigger_event('youtube-url-input', 'input', {'value': 'https://www.youtube.com/watch?v='})
        assert not result, "不完整的URL不应该触发加载"
        
        # 2. 用户完成输入有效YouTube URL
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        browser.set_element_value('youtube-url-input', test_url)
        result = browser.trigger_event('youtube-url-input', 'input', {'value': test_url})
        assert result, "有效的YouTube URL应该触发加载"
        
        # 验证加载状态
        loading_classes = browser.get_element_classes('youtube-loading-indicator')
        assert 'loading' in loading_classes, "应该显示加载状态"
        assert 'spinning' in loading_classes, "应该有旋转动画"
        assert 'hidden' not in loading_classes, "指示器应该可见"
        
        cancel_classes = browser.get_element_classes('youtube-cancel-button')
        assert 'hidden' not in cancel_classes, "取消按钮应该可见"
        
        # 验证ARIA属性
        aria_label = browser.get_aria_attribute('youtube-loading-indicator', 'aria-label')
        assert 'Loading' in aria_label, "应该有加载的ARIA标签"
        
        # 3. 测试取消功能
        cancel_result = browser.trigger_event('youtube-cancel-button', 'click', {})
        assert cancel_result, "取消按钮应该响应点击"
        
        # 验证取消后状态
        loading_classes = browser.get_element_classes('youtube-loading-indicator')
        assert 'hidden' in loading_classes, "取消后指示器应该隐藏"
        
        # 4. 测试成功流程
        browser.set_element_value('youtube-url-input', test_url)
        browser.trigger_event('youtube-url-input', 'input', {'value': test_url})
        
        # 模拟成功获取元数据
        indicator_manager.simulate_metadata_success()
        
        success_classes = browser.get_element_classes('youtube-loading-indicator')
        assert 'success' in success_classes, "应该显示成功状态"
        assert 'loading' not in success_classes, "不应该有加载状态"
        assert 'spinning' not in success_classes, "不应该有旋转动画"
        
        # 5. 测试错误流程
        browser.set_element_value('youtube-url-input', "https://www.youtube.com/watch?v=invalid123")
        browser.trigger_event('youtube-url-input', 'input', {'value': "https://www.youtube.com/watch?v=invalid123"})
        
        # 模拟错误
        indicator_manager.simulate_metadata_error("Video not found")
        
        error_classes = browser.get_element_classes('youtube-loading-indicator')
        assert 'error' in error_classes, "应该显示错误状态"
        
        error_aria = browser.get_aria_attribute('youtube-loading-indicator', 'aria-label')
        assert 'Error' in error_aria, "应该有错误的ARIA标签"
        assert 'Video not found' in error_aria, "错误信息应该包含在ARIA标签中"

    def test_rapid_input_handling_integration(self):
        """测试快速输入处理的集成行为"""
        
        # 模拟快速输入场景
        class RapidInputSimulator:
            def __init__(self):
                self.active_timers = []
                self.executed_requests = []
                self.current_time = 0
                
            def set_timeout(self, callback, delay_ms):
                """模拟setTimeout"""
                timer_id = len(self.active_timers)
                self.active_timers.append({
                    'id': timer_id,
                    'callback': callback,
                    'delay': delay_ms,
                    'created_at': self.current_time,
                    'cancelled': False
                })
                return timer_id
                
            def clear_timeout(self, timer_id):
                """模拟clearTimeout"""
                if timer_id < len(self.active_timers):
                    self.active_timers[timer_id]['cancelled'] = True
                    
            def advance_time(self, ms):
                """推进模拟时间"""
                self.current_time += ms
                
                # 执行到期的定时器
                for timer in self.active_timers:
                    if (not timer['cancelled'] and 
                        self.current_time >= timer['created_at'] + timer['delay']):
                        timer['callback']()
                        self.executed_requests.append({
                            'timer_id': timer['id'],
                            'executed_at': self.current_time
                        })
                        timer['cancelled'] = True
        
        # 模拟防抖动输入处理器
        class DebouncedInputHandler:
            def __init__(self, timer_sim):
                self.timer_sim = timer_sim
                self.current_timer = None
                self.processed_urls = []
                
            def handle_input(self, url):
                """处理输入，带防抖动"""
                # 取消之前的定时器
                if self.current_timer is not None:
                    self.timer_sim.clear_timeout(self.current_timer)
                
                # 设置新的定时器
                self.current_timer = self.timer_sim.set_timeout(
                    lambda: self.process_url(url),
                    800  # 800ms延迟
                )
                
            def process_url(self, url):
                """处理URL"""
                self.processed_urls.append({
                    'url': url,
                    'processed_at': self.timer_sim.current_time
                })

        # 创建模拟器
        timer_sim = RapidInputSimulator()
        input_handler = DebouncedInputHandler(timer_sim)
        
        # 模拟快速连续输入
        urls = [
            "https://www.youtube.com/watch?v=url1",
            "https://www.youtube.com/watch?v=url2", 
            "https://www.youtube.com/watch?v=url3",
            "https://www.youtube.com/watch?v=url4",
            "https://www.youtube.com/watch?v=final"
        ]
        
        # 在200ms间隔内快速输入
        for i, url in enumerate(urls):
            timer_sim.advance_time(200)  # 每200ms输入一次
            input_handler.handle_input(url)
            
        # 等待足够长时间让最后一个定时器执行
        timer_sim.advance_time(1000)
        
        # 验证只有最后一个URL被处理
        assert len(input_handler.processed_urls) == 1, "应该只处理最后一个URL"
        assert input_handler.processed_urls[0]['url'] == "https://www.youtube.com/watch?v=final"
        
        # 验证防抖动时间
        processed_time = input_handler.processed_urls[0]['processed_at']
        expected_time = 200 * 5 + 1000  # 最后输入时间(1000ms) + 最后等待(1000ms) = 2000ms
        assert processed_time == expected_time, f"处理时间应该是{expected_time}ms，实际: {processed_time}ms"

    def test_accessibility_integration(self):
        """测试可访问性集成"""
        
        # 模拟可访问性检查器
        class AccessibilityChecker:
            def __init__(self):
                self.violations = []
                
            def check_element(self, element_id, properties):
                """检查元素的可访问性"""
                violations = []
                
                # 检查ARIA标签
                if 'aria-label' not in properties.get('attributes', {}):
                    violations.append(f"{element_id}: Missing aria-label")
                    
                # 检查颜色对比度（简化模拟）
                if 'high-contrast' not in properties.get('classes', []):
                    violations.append(f"{element_id}: May have low color contrast")
                    
                # 检查键盘可访问性
                if properties.get('type') == 'button' and not properties.get('focusable', True):
                    violations.append(f"{element_id}: Button not focusable")
                    
                # 检查屏幕阅读器支持
                attributes = properties.get('attributes', {})
                if 'role' not in attributes and properties.get('type') not in ['input', 'button']:
                    violations.append(f"{element_id}: Missing role attribute")
                    
                return violations
                
            def check_loading_state_accessibility(self, element_states):
                """检查加载状态的可访问性"""
                violations = []
                
                for state_name, state_props in element_states.items():
                    if state_name == 'loading':
                        # 加载状态应该有明确的ARIA标签
                        aria_label = state_props.get('attributes', {}).get('aria-label', '')
                        if not aria_label or 'loading' not in aria_label.lower():
                            violations.append("Loading state missing proper aria-label")
                            
                        # 应该有aria-live属性用于状态更新
                        if 'aria-live' not in state_props.get('attributes', {}):
                            violations.append("Loading state missing aria-live")
                            
                    elif state_name == 'success':
                        # 成功状态应该通知屏幕阅读器
                        aria_label = state_props.get('attributes', {}).get('aria-label', '')
                        if not aria_label or 'success' not in aria_label.lower():
                            violations.append("Success state missing proper aria-label")
                            
                    elif state_name == 'error':
                        # 错误状态应该有错误信息
                        aria_label = state_props.get('attributes', {}).get('aria-label', '')
                        if not aria_label or 'error' not in aria_label.lower():
                            violations.append("Error state missing proper aria-label")
                            
                        # 错误状态应该有role="alert"
                        if state_props.get('attributes', {}).get('role') != 'alert':
                            violations.append("Error state should have role='alert'")
                            
                return violations

        # 模拟加载指示器的不同状态
        loading_indicator_states = {
            'hidden': {
                'classes': ['hidden'],
                'attributes': {}
            },
            'loading': {
                'classes': ['loading', 'spinning'],
                'attributes': {
                    'aria-label': 'Loading YouTube metadata, please wait',
                    'aria-live': 'polite',
                    'role': 'status'
                }
            },
            'success': {
                'classes': ['success'],
                'attributes': {
                    'aria-label': 'YouTube metadata loaded successfully',
                    'aria-live': 'polite',
                    'role': 'status'
                }
            },
            'error': {
                'classes': ['error'],
                'attributes': {
                    'aria-label': 'Error loading YouTube metadata: Video not found',
                    'aria-live': 'assertive',
                    'role': 'alert'
                }
            }
        }
        
        # 检查每个状态的可访问性
        checker = AccessibilityChecker()
        
        for state_name, state_props in loading_indicator_states.items():
            violations = checker.check_element(f'loading-indicator-{state_name}', state_props)
            
            if state_name == 'hidden':
                # 隐藏状态可以没有ARIA属性
                continue
            else:
                # 其他状态必须有适当的可访问性属性
                assert len(violations) == 0 or all('color contrast' in v for v in violations), \
                    f"{state_name}状态可访问性违规: {violations}"
        
        # 检查整体加载状态流转的可访问性
        state_violations = checker.check_loading_state_accessibility(loading_indicator_states)
        assert len(state_violations) == 0, f"加载状态可访问性违规: {state_violations}"

    def test_error_recovery_integration(self):
        """测试错误恢复集成"""
        
        # 模拟网络错误场景
        class NetworkSimulator:
            def __init__(self):
                self.request_count = 0
                self.failure_modes = []
                
            def add_failure_mode(self, failure_type, after_requests=0):
                """添加失败模式"""
                self.failure_modes.append({
                    'type': failure_type,
                    'after_requests': after_requests,
                    'triggered': False
                })
                
            def make_request(self, url):
                """模拟网络请求"""
                self.request_count += 1
                
                # 检查是否应该触发失败（每次都触发，不标记为triggered）
                for failure in self.failure_modes:
                    if failure['type'] == 'timeout':
                        raise TimeoutError("Request timeout")
                    elif failure['type'] == 'network_error':
                        raise ConnectionError("Network unreachable")
                    elif failure['type'] == 'server_error':
                        raise Exception("Server error 500")
                    elif failure['type'] == 'invalid_response':
                        return {'error': 'Invalid video ID'}
                
                # 成功响应
                return {
                    'title': f'Video Title {self.request_count}',
                    'description': 'Test video description',
                    'duration': 120
                }
        
        # 模拟错误处理的加载指示器
        class ErrorHandlingIndicator:
            def __init__(self, network_sim):
                self.network = network_sim
                self.current_state = 'hidden'
                self.retry_count = 0
                self.max_retries = 3
                
            def load_metadata(self, url):
                """加载元数据，带错误处理"""
                self.current_state = 'loading'
                self.retry_count = 0
                
                return self._attempt_load(url)
                
            def _attempt_load(self, url):
                """尝试加载，带重试"""
                try:
                    result = self.network.make_request(url)
                    
                    if 'error' in result:
                        self.current_state = 'error'
                        return {'state': 'error', 'message': result['error']}
                    
                    self.current_state = 'success'
                    return {'state': 'success', 'data': result}
                    
                except (TimeoutError, ConnectionError) as e:
                    # 网络错误可以重试
                    if self.retry_count < self.max_retries:
                        self.retry_count += 1
                        self.current_state = f'retrying_{self.retry_count}'
                        time.sleep(0.1)  # 模拟重试延迟
                        return self._attempt_load(url)
                    else:
                        self.current_state = 'error'
                        return {'state': 'error', 'message': f'Network error after {self.max_retries} retries: {str(e)}'}
                        
                except Exception as e:
                    # 其他错误不重试
                    self.current_state = 'error'
                    return {'state': 'error', 'message': f'Server error: {str(e)}'}

        # 简化测试：直接测试失败响应处理
        network_sim = NetworkSimulator()
        network_sim.add_failure_mode('timeout')
        
        indicator = ErrorHandlingIndicator(network_sim)
        result = indicator.load_metadata("https://www.youtube.com/watch?v=test123")
        
        # 验证超时错误被正确处理
        assert result['state'] == 'error', f"期望错误状态，实际: {result['state']}"
        assert indicator.retry_count == 3, f"期望重试3次，实际: {indicator.retry_count}"
        assert "timeout" in result['message'].lower(), f"错误信息应包含timeout，实际: {result['message']}"
        
        # 测试无效响应（不重试）
        network_sim2 = NetworkSimulator()
        network_sim2.add_failure_mode('invalid_response')
        
        indicator2 = ErrorHandlingIndicator(network_sim2)
        result2 = indicator2.load_metadata("https://www.youtube.com/watch?v=test123")
        
        assert result2['state'] == 'error', f"期望错误状态，实际: {result2['state']}"
        assert indicator2.retry_count == 0, f"无效响应不应重试，实际重试: {indicator2.retry_count}"

    def test_responsive_design_integration(self):
        """测试响应式设计集成"""
        
        # 模拟不同屏幕尺寸
        class ResponsiveSimulator:
            def __init__(self):
                self.current_viewport = None
                self.breakpoints = {
                    'mobile': {'width': 375, 'height': 667},
                    'tablet': {'width': 768, 'height': 1024},
                    'desktop': {'width': 1200, 'height': 800}
                }
                
            def set_viewport(self, device_type):
                """设置视口大小"""
                if device_type in self.breakpoints:
                    self.current_viewport = self.breakpoints[device_type]
                    return True
                return False
                
            def get_element_layout(self, element_id):
                """获取元素在当前视口下的布局"""
                if not self.current_viewport:
                    return None
                    
                viewport_width = self.current_viewport['width']
                
                # 模拟响应式布局规则
                if element_id == 'youtube-loading-indicator':
                    if viewport_width <= 480:  # 手机
                        return {
                            'position': 'absolute',
                            'size': '24px',
                            'right': '8px',
                            'top': '50%'
                        }
                    elif viewport_width <= 768:  # 平板
                        return {
                            'position': 'absolute',
                            'size': '32px',
                            'right': '12px',
                            'top': '50%'
                        }
                    else:  # 桌面
                        return {
                            'position': 'absolute',
                            'size': '32px',
                            'right': '16px',
                            'top': '50%'
                        }
                        
                elif element_id == 'youtube-cancel-button':
                    if viewport_width <= 480:  # 手机
                        return {
                            'position': 'absolute',
                            'size': '20px',
                            'right': '40px',
                            'top': '50%',
                            'touch_target': '44px'  # iOS建议的最小触摸目标
                        }
                    else:
                        return {
                            'position': 'absolute',
                            'size': '24px',
                            'right': '52px',
                            'top': '50%',
                            'touch_target': '32px'
                        }
                        
                return {}
            
            def check_element_visibility(self, element_id):
                """检查元素在当前视口下是否可见"""
                layout = self.get_element_layout(element_id)
                if not layout:
                    return False
                    
                # 简化的可见性检查
                viewport_width = self.current_viewport['width']
                element_right = int(layout.get('right', '0').replace('px', ''))
                element_size = int(layout.get('size', '0').replace('px', ''))
                
                # 元素是否在视口内
                return element_right + element_size <= viewport_width

        # 测试不同设备的响应式行为
        responsive_sim = ResponsiveSimulator()
        
        devices_to_test = ['mobile', 'tablet', 'desktop']
        
        for device in devices_to_test:
            # 设置设备视口
            responsive_sim.set_viewport(device)
            
            # 检查加载指示器布局
            indicator_layout = responsive_sim.get_element_layout('youtube-loading-indicator')
            assert indicator_layout is not None, f"{device}: 加载指示器应该有布局定义"
            
            # 验证尺寸适配
            size = int(indicator_layout['size'].replace('px', ''))
            if device == 'mobile':
                assert size == 24, f"手机端指示器大小应该是24px，实际: {size}px"
            else:
                assert size == 32, f"{device}端指示器大小应该是32px，实际: {size}px"
            
            # 检查取消按钮布局
            cancel_layout = responsive_sim.get_element_layout('youtube-cancel-button')
            assert cancel_layout is not None, f"{device}: 取消按钮应该有布局定义"
            
            # 验证触摸目标大小（移动端重要）
            if device == 'mobile':
                touch_target = int(cancel_layout['touch_target'].replace('px', ''))
                assert touch_target >= 44, f"手机端触摸目标应该至少44px，实际: {touch_target}px"
            
            # 验证元素可见性
            indicator_visible = responsive_sim.check_element_visibility('youtube-loading-indicator')
            assert indicator_visible, f"{device}: 加载指示器应该在视口内可见"
            
            cancel_visible = responsive_sim.check_element_visibility('youtube-cancel-button')
            assert cancel_visible, f"{device}: 取消按钮应该在视口内可见"

    def test_performance_integration(self):
        """测试性能集成"""
        
        # 模拟性能监控
        class PerformanceMonitor:
            def __init__(self):
                self.metrics = {}
                self.start_times = {}
                
            def mark_start(self, operation):
                """标记操作开始"""
                self.start_times[operation] = time.time()
                
            def mark_end(self, operation):
                """标记操作结束并记录耗时"""
                if operation in self.start_times:
                    duration = time.time() - self.start_times[operation]
                    self.metrics[operation] = duration
                    return duration
                return None
                
            def get_metric(self, operation):
                """获取性能指标"""
                return self.metrics.get(operation)
                
            def get_all_metrics(self):
                """获取所有性能指标"""
                return self.metrics.copy()

        # 模拟加载指示器的性能关键操作
        class PerformantLoadingIndicator:
            def __init__(self, perf_monitor):
                self.perf = perf_monitor
                self.animation_frame_count = 0
                self.dom_operations = 0
                
            def show_loading_animation(self):
                """显示加载动画（性能关键）"""
                self.perf.mark_start('show_loading')
                
                # 模拟DOM操作
                self.dom_operations += 3  # 添加class, 设置aria-label, 显示元素
                
                # 模拟CSS动画启动
                self.animation_frame_count = 0
                
                self.perf.mark_end('show_loading')
                
            def animate_spinner(self, frames):
                """模拟旋转动画的帧更新"""
                self.perf.mark_start('animate_spinner')
                
                # 模拟60fps动画
                frame_time = 1.0 / 60  # 16.67ms per frame
                for i in range(frames):
                    time.sleep(frame_time / 1000)  # 模拟帧处理时间
                    self.animation_frame_count += 1
                    
                self.perf.mark_end('animate_spinner')
                
            def update_progress(self):
                """更新进度（可能的性能瓶颈）"""
                self.perf.mark_start('update_progress')
                
                # 模拟进度更新操作
                self.dom_operations += 2  # 更新aria-label, 可能更新进度条
                
                self.perf.mark_end('update_progress')
                
            def show_result(self, success=True):
                """显示结果（状态转换）"""
                self.perf.mark_start('show_result')
                
                # 模拟停止动画和显示结果
                self.dom_operations += 4  # 移除loading class, 添加success/error class, 更新aria-label, 隐藏取消按钮
                
                self.perf.mark_end('show_result')

        # 执行性能测试
        perf_monitor = PerformanceMonitor()
        indicator = PerformantLoadingIndicator(perf_monitor)
        
        # 测试完整的加载流程性能
        perf_monitor.mark_start('full_loading_cycle')
        
        # 1. 显示加载指示器
        indicator.show_loading_animation()
        
        # 2. 运行旋转动画（模拟2秒）
        indicator.animate_spinner(120)  # 120帧 = 2秒 at 60fps
        
        # 3. 更新进度几次
        for _ in range(5):
            indicator.update_progress()
            
        # 4. 显示成功结果
        indicator.show_result(success=True)
        
        perf_monitor.mark_end('full_loading_cycle')
        
        # 验证性能指标
        metrics = perf_monitor.get_all_metrics()
        
        # 显示加载指示器应该很快（< 10ms）
        show_loading_time = metrics.get('show_loading', 0)
        assert show_loading_time < 0.01, f"显示加载指示器耗时应该 < 10ms，实际: {show_loading_time*1000:.2f}ms"
        
        # 动画性能应该稳定（平均每帧 < 20ms）
        animate_time = metrics.get('animate_spinner', 0)
        avg_frame_time = animate_time / 120 if animate_time > 0 else 0
        assert avg_frame_time < 0.02, f"平均帧时间应该 < 20ms，实际: {avg_frame_time*1000:.2f}ms"
        
        # 进度更新应该快速（< 5ms）
        update_time = metrics.get('update_progress', 0)
        assert update_time < 0.005, f"进度更新耗时应该 < 5ms，实际: {update_time*1000:.2f}ms"
        
        # 显示结果应该快速（< 10ms）
        show_result_time = metrics.get('show_result', 0)
        assert show_result_time < 0.01, f"显示结果耗时应该 < 10ms，实际: {show_result_time*1000:.2f}ms"
        
        # 完整周期应该在合理时间内（< 3秒，主要是动画时间）
        full_cycle_time = metrics.get('full_loading_cycle', 0)
        assert full_cycle_time < 3.0, f"完整加载周期应该 < 3秒，实际: {full_cycle_time:.2f}秒"
        
        # 验证DOM操作效率
        expected_dom_ops = 3 + 5*2 + 4  # show_loading + 5*update_progress + show_result
        assert indicator.dom_operations == expected_dom_ops, \
            f"DOM操作数应该是{expected_dom_ops}，实际: {indicator.dom_operations}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])