#!/usr/bin/env python3.11
"""
AI内容生成模块
负责通过OpenRouter API生成摘要和思维导图
"""

import os
import requests
import logging
from typing import Dict, Any, Optional
import time
try:
    from ..utils.rate_limiter import create_rate_limited_client
except ImportError:
    # 兼容性处理：当作为顶级模块运行时
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from utils.rate_limiter import create_rate_limited_client


class AIContentGenerator:
    """AI内容生成服务"""
    
    def __init__(self, api_config: Dict[str, Any], enable_rate_limiting: bool = True):
        """初始化AI内容生成服务
        
        Args:
            api_config: API配置字典
            enable_rate_limiting: 是否启用限流
        """
        self.config = api_config
        self.logger = logging.getLogger('project_bach.ai_generation')
        
        # 创建原始客户端
        raw_client = OpenRouterClient(api_config.get('openrouter', {}))
        
        # 如果启用限流，包装客户端
        if enable_rate_limiting:
            api_key = os.environ.get('OPENROUTER_API_KEY', '')
            if api_key and api_key != 'YOUR_API_KEY_HERE':
                # 获取限流配置
                rate_limit_tier = api_config.get('openrouter', {}).get('rate_limit_tier', 'free')
                self.client, self.rate_limiter = create_rate_limited_client(
                    raw_client, api_key, rate_limit_tier
                )
                self.logger.info("AI生成服务已启用限流保护")
            else:
                self.client = raw_client
                self.rate_limiter = None
                self.logger.warning("API密钥未配置，禁用限流保护")
        else:
            self.client = raw_client
            self.rate_limiter = None
        
    def generate_summary(self, text: str) -> str:
        """生成内容摘要
        
        Args:
            text: 待总结的文本
            
        Returns:
            生成的摘要
        """
        # 获取模型名称（考虑限流包装器）
        if hasattr(self.client, 'models'):
            model_name = self.client.models.get('summary', 'unknown')
        elif hasattr(self.client, 'api_client') and hasattr(self.client.api_client, 'models'):
            model_name = self.client.api_client.models.get('summary', 'unknown')
        else:
            model_name = 'unknown'
        self.logger.info(f"开始生成内容摘要，使用模型: {model_name}")
        
        try:
            prompt = f"Please generate a concise summary (within 300 words) for the following content:\n\n{text}"
            
            result = self.client.generate_content(
                model_type='summary',
                prompt=prompt,
                max_tokens=500,
                temperature=0.7
            )
            
            # 记录结果预览
            preview = result.strip().replace('\n', ' ')[:50] + "..." if len(result) > 50 else result.strip().replace('\n', ' ')
            self.logger.info(f"摘要生成成功，长度: {len(result)} 字符，内容预览: {preview}")
            return result
            
        except Exception as e:
            error_msg = f"摘要生成失败: {str(e)}"
            self.logger.error(error_msg)
            return error_msg
    
    def generate_mindmap(self, text: str) -> str:
        """生成思维导图
        
        Args:
            text: 待处理的文本
            
        Returns:
            生成的思维导图（Markdown格式）
        """
        # 获取模型名称（考虑限流包装器）
        if hasattr(self.client, 'models'):
            model_name = self.client.models.get('mindmap', 'unknown')
        elif hasattr(self.client, 'api_client') and hasattr(self.client.api_client, 'models'):
            model_name = self.client.api_client.models.get('mindmap', 'unknown')
        else:
            model_name = 'unknown'
        self.logger.info(f"开始生成思维导图，使用模型: {model_name}")
        
        try:
            prompt = (
                f"Please organize the following content into a mind map structure in Markdown format, "
                f"using #, ##, ### heading levels and - list items:\n\n{text}"
            )
            
            result = self.client.generate_content(
                model_type='mindmap',
                prompt=prompt,
                max_tokens=800,
                temperature=0.5
            )
            
            # 记录结果预览
            preview = result.strip().replace('\n', ' ')[:50] + "..." if len(result) > 50 else result.strip().replace('\n', ' ')
            self.logger.info(f"思维导图生成成功，长度: {len(result)} 字符，内容预览: {preview}")
            return result
            
        except Exception as e:
            error_msg = f"思维导图生成失败: {str(e)}"
            self.logger.error(error_msg)
            return error_msg
    
    def generate_custom_content(self, text: str, task_description: str, 
                              model_type: str = 'summary', **kwargs) -> str:
        """生成自定义内容
        
        Args:
            text: 输入文本
            task_description: 任务描述
            model_type: 使用的模型类型
            **kwargs: 额外参数
            
        Returns:
            生成的内容
        """
        # 获取模型名称（考虑限流包装器）
        if hasattr(self.client, 'models'):
            model_name = self.client.models.get(model_type, 'unknown')
        elif hasattr(self.client, 'api_client') and hasattr(self.client.api_client, 'models'):
            model_name = self.client.api_client.models.get(model_type, 'unknown')
        else:
            model_name = 'unknown'
        self.logger.info(f"开始生成自定义内容: {task_description}，使用模型: {model_name}")
        
        try:
            prompt = f"{task_description}\n\n{text}"
            
            result = self.client.generate_content(
                model_type=model_type,
                prompt=prompt,
                **kwargs
            )
            
            # 记录结果预览
            preview = result.strip().replace('\n', ' ')[:50] + "..." if len(result) > 50 else result.strip().replace('\n', ' ')
            self.logger.info(f"自定义内容生成成功，长度: {len(result)} 字符，内容预览: {preview}")
            return result
            
        except Exception as e:
            error_msg = f"自定义内容生成失败: {str(e)}"
            self.logger.error(error_msg)
            return error_msg
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """获取限流状态信息
        
        Returns:
            限流状态字典
        """
        if self.rate_limiter:
            return self.rate_limiter.get_rate_limit_info()
        else:
            return {"rate_limiting": "disabled"}


class OpenRouterClient:
    """OpenRouter API客户端"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化OpenRouter客户端
        
        Args:
            config: OpenRouter配置字典
        """
        self.config = config
        self.logger = logging.getLogger('project_bach.openrouter')
        self.session = requests.Session()
        
        # 从环境变量获取API密钥
        api_key = os.environ.get('OPENROUTER_API_KEY', '')
        
        # 设置默认headers
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
        
        self.base_url = config.get('base_url', 'https://openrouter.ai/api/v1')
        self.models = config.get('models', {})
        
        # 请求限制和重试配置
        self.request_timeout = 30
        self.max_retries = 3
        self.retry_delay = 1.0
    
    def generate_content(self, model_type: str, prompt: str, 
                        max_tokens: int = 500, temperature: float = 0.7,
                        **kwargs) -> str:
        """生成内容
        
        Args:
            model_type: 模型类型 ('summary', 'mindmap', 等)
            prompt: 输入提示
            max_tokens: 最大token数
            temperature: 温度参数
            **kwargs: 额外参数
            
        Returns:
            生成的内容
            
        Raises:
            APIException: API调用失败
        """
        model_name = self.models.get(model_type)
        if not model_name:
            raise APIException(f"未找到模型类型: {model_type}")
        
        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs
        }
        
        return self._make_request(payload)
    
    def _make_request(self, payload: Dict[str, Any]) -> str:
        """发送API请求
        
        Args:
            payload: 请求载荷
            
        Returns:
            API响应内容
            
        Raises:
            APIException: API调用失败
        """
        url = f"{self.base_url}/chat/completions"
        
        for attempt in range(self.max_retries):
            try:
                self.logger.debug(f"发送API请求 (尝试 {attempt + 1}/{self.max_retries})")
                
                response = self.session.post(
                    url,
                    json=payload,
                    timeout=self.request_timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    model_used = payload.get('model', 'unknown')
                    tokens_used = result.get('usage', {}).get('total_tokens', 'unknown')
                    self.logger.debug(f"API请求成功，模型: {model_used}，消耗tokens: {tokens_used}")
                    return content.strip()
                else:
                    error_info = self._extract_error_info(response)
                    
                    # 对于4xx错误，不重试
                    if 400 <= response.status_code < 500:
                        raise APIException(
                            f"API调用失败，状态码: {response.status_code}，{error_info}"
                        )
                    
                    # 对于5xx错误，记录并准备重试
                    self.logger.warning(
                        f"API请求失败 (尝试 {attempt + 1}/{self.max_retries}): "
                        f"状态码 {response.status_code}, {error_info}"
                    )
                
            except requests.exceptions.Timeout:
                self.logger.warning(f"API请求超时 (尝试 {attempt + 1}/{self.max_retries})")
                
            except requests.exceptions.RequestException as e:
                self.logger.warning(
                    f"网络请求异常 (尝试 {attempt + 1}/{self.max_retries}): {str(e)}"
                )
            
            # 如果不是最后一次尝试，等待后重试
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay * (attempt + 1))  # 指数退避
        
        # 所有重试都失败
        raise APIException(f"API调用失败，已重试 {self.max_retries} 次")
    
    def _extract_error_info(self, response: requests.Response) -> str:
        """提取错误信息
        
        Args:
            response: HTTP响应对象
            
        Returns:
            错误信息字符串
        """
        try:
            error_data = response.json()
            error_message = error_data.get('error', {}).get('message', 'Unknown error')
            return f"错误: {error_message}"
        except:
            # 如果无法解析JSON，返回原始响应文本
            return f"响应: {response.text[:200]}"
    
    def test_connection(self) -> bool:
        """测试API连接
        
        Returns:
            连接是否成功
        """
        try:
            test_payload = {
                "model": self.models.get('summary', 'gpt-3.5-turbo'),
                "messages": [
                    {
                        "role": "user",
                        "content": "Hello, this is a connection test."
                    }
                ],
                "max_tokens": 10
            }
            
            self._make_request(test_payload)
            self.logger.info("API连接测试成功")
            return True
            
        except Exception as e:
            self.logger.error(f"API连接测试失败: {str(e)}")
            return False
    
    def get_available_models(self) -> Dict[str, str]:
        """获取可用的模型列表
        
        Returns:
            模型类型到模型名称的映射
        """
        return self.models.copy()
    
    def update_model(self, model_type: str, model_name: str):
        """更新模型配置
        
        Args:
            model_type: 模型类型
            model_name: 模型名称
        """
        self.models[model_type] = model_name
        self.logger.info(f"更新模型配置: {model_type} -> {model_name}")


class APIException(Exception):
    """API异常类"""
    
    def __init__(self, message: str, status_code: Optional[int] = None, 
                 response_data: Optional[Dict] = None):
        """初始化API异常
        
        Args:
            message: 错误消息
            status_code: HTTP状态码
            response_data: 响应数据
        """
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class ContentGenerator:
    """内容生成器工厂类"""
    
    @staticmethod
    def create_summary_generator(api_config: Dict[str, Any]) -> AIContentGenerator:
        """创建摘要生成器
        
        Args:
            api_config: API配置
            
        Returns:
            配置好的AI内容生成器
        """
        return AIContentGenerator(api_config)
    
    @staticmethod
    def create_mindmap_generator(api_config: Dict[str, Any]) -> AIContentGenerator:
        """创建思维导图生成器
        
        Args:
            api_config: API配置
            
        Returns:
            配置好的AI内容生成器
        """
        return AIContentGenerator(api_config)


class ContentValidator:
    """内容验证器"""
    
    @staticmethod
    def validate_summary(summary: str) -> bool:
        """验证摘要质量
        
        Args:
            summary: 摘要文本
            
        Returns:
            是否通过验证
        """
        if not summary or not isinstance(summary, str):
            return False
        
        # 检查长度
        if len(summary.strip()) < 10:
            return False
        
        # 检查是否包含错误信息
        error_keywords = ['失败', 'error', '错误', '异常']
        if any(keyword in summary.lower() for keyword in error_keywords):
            return False
        
        return True
    
    @staticmethod
    def validate_mindmap(mindmap: str) -> bool:
        """验证思维导图质量
        
        Args:
            mindmap: 思维导图文本
            
        Returns:
            是否通过验证
        """
        if not mindmap or not isinstance(mindmap, str):
            return False
        
        # 检查是否包含Markdown标记
        markdown_markers = ['#', '-', '*']
        if not any(marker in mindmap for marker in markdown_markers):
            return False
        
        # 检查是否包含错误信息
        error_keywords = ['失败', 'error', '错误', '异常']
        if any(keyword in mindmap.lower() for keyword in error_keywords):
            return False
        
        return True