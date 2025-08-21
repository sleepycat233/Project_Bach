#!/usr/bin/env python3.11
"""
API限流管理器
根据OpenRouter的限制策略实现本地限流
"""

import time
import logging
import requests
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from threading import Lock
import json


class RateLimiter:
    """API限流器"""
    
    def __init__(self, api_key: str, rate_limit_config: Optional[Dict] = None):
        """初始化限流器
        
        Args:
            api_key: OpenRouter API密钥
            rate_limit_config: 限流配置字典，如果为None则使用默认配置
        """
        self.api_key = api_key
        self.logger = logging.getLogger('project_bach.rate_limiter')
        
        # 从配置加载限制设置
        if rate_limit_config:
            self.limits = {
                'free_models': rate_limit_config.get('free_tier', {
                    'requests_per_10s': 10,
                    'requests_per_minute': 60,
                    'daily_credit_limit': 5
                }),
                'paid_models': rate_limit_config.get('paid_tier', {
                    'requests_per_10s': 10,
                    'requests_per_minute': 60,
                    'credit_to_requests_ratio': 100
                })
            }
        else:
            # 默认配置（向后兼容）
            self.limits = {
                'free_models': {
                    'requests_per_10s': 10,  # 实际限制：每10秒10个请求
                    'requests_per_minute': 60,  # 理论最大：6 * 10 = 60/分钟
                    'daily_credit_limit': 5,  # 免费层每日5个credits
                },
                'paid_models': {
                    'requests_per_10s': 10,  # 付费账户10秒限制相同
                    'requests_per_minute': 60,  # 每分钟限制相同
                    'credit_to_requests_ratio': 100,  # 每个credit允许100个请求/天
                }
            }
        
        # 请求跟踪
        self.request_history: Dict[str, list] = {}
        self.daily_usage = {}
        self.last_reset = datetime.now().date()
        self.lock = Lock()
        
        # 账户信息缓存
        self.account_info = None
        self.last_account_check = None
        
    def check_account_status(self) -> Dict:
        """检查账户状态和限制
        
        Returns:
            账户信息字典
        """
        try:
            response = requests.get(
                "https://openrouter.ai/api/v1/auth/key",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                self.account_info = response.json()
                self.last_account_check = datetime.now()
                
                self.logger.info(f"账户状态检查成功")
                self.logger.info(f"账户信息: {json.dumps(self.account_info, indent=2, default=str)}")
                
                return self.account_info
            else:
                self.logger.error(f"账户状态检查失败: {response.status_code} - {response.text}")
                return {'error': f'Status {response.status_code}'}
                
        except Exception as e:
            self.logger.error(f"检查账户状态异常: {str(e)}")
            return {'error': str(e)}
    
    def get_rate_limit_info(self) -> Dict:
        """获取当前限制信息
        
        Returns:
            限制信息字典
        """
        # 如果账户信息过期或不存在，重新获取
        if (self.account_info is None or 
            self.last_account_check is None or 
            datetime.now() - self.last_account_check > timedelta(hours=1)):
            self.check_account_status()
        
        info = {
            'account_info': self.account_info,
            'configured_limits': self.limits,
            'current_usage': self._get_current_usage(),
            'estimated_daily_limit': self._estimate_daily_limit()
        }
        
        return info
    
    def _estimate_daily_limit(self) -> int:
        """估算每日限制
        
        Returns:
            预估的每日请求限制
        """
        if self.account_info and 'data' in self.account_info:
            account_data = self.account_info['data']
            is_free_tier = account_data.get('is_free_tier', True)
            credits = account_data.get('limit', 5)
            
            if is_free_tier:
                # 免费账户：5个credits
                return self.limits['free_models']['daily_credit_limit']
            else:
                # 付费账户：根据配置的比例计算  
                ratio = self.limits['paid_models'].get('credit_to_requests_ratio', 100)
                # 用户说10个credits=1000个请求，而API显示0.1（这是$0.10=10个credits）
                # 所以 0.1 * 10000 = 1000个请求
                return int(credits * 10000)
        
        # 默认使用免费层限制
        return self.limits['free_models']['daily_credit_limit']
    
    def _get_current_usage(self) -> Dict:
        """获取当前使用量
        
        Returns:
            使用量统计
        """
        now = datetime.now()
        
        # 重置日统计
        if now.date() != self.last_reset:
            self.daily_usage = {}
            self.last_reset = now.date()
        
        # 10秒级统计
        ten_seconds_ago = now - timedelta(seconds=10)
        recent_10s_requests = len([
            t for t in self.request_history.get('free', [])
            if datetime.fromtimestamp(t) > ten_seconds_ago
        ])
        
        # 分钟级统计
        minute_key = now.strftime('%Y-%m-%d %H:%M')
        minute_requests = len([
            t for t in self.request_history.get('free', [])
            if datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M') == minute_key
        ])
        
        # 日级统计
        daily_requests = self.daily_usage.get('free', 0)
        
        return {
            'requests_last_10s': recent_10s_requests,
            'requests_this_minute': minute_requests,
            'requests_today': daily_requests,
            'limit_10s': self.limits['free_models']['requests_per_10s'],
            'minute_limit': self.limits['free_models']['requests_per_minute'],
            'daily_limit': self._estimate_daily_limit()
        }
    
    def can_make_request(self, model_type: str = 'free', model_name: str = None) -> Tuple[bool, str]:
        """检查是否可以发送请求
        
        Args:
            model_type: 模型类型
            model_name: 具体的模型名称（用于判断是否为免费模型）
            
        Returns:
            (是否可以请求, 原因说明)
        """
        with self.lock:
            now = datetime.now()
            current_time = now.timestamp()
            
            # 重置日统计
            if now.date() != self.last_reset:
                self.daily_usage = {}
                self.last_reset = now.date()
            
            # 初始化请求历史
            if model_type not in self.request_history:
                self.request_history[model_type] = []
            
            # 清理过期的请求记录（保留最近1小时）
            cutoff_time = current_time - 3600
            self.request_history[model_type] = [
                t for t in self.request_history[model_type] if t > cutoff_time
            ]
            
            # 检查10秒级限制（最严格）
            ten_seconds_ago = current_time - 10
            recent_10s_requests = [
                t for t in self.request_history[model_type] if t > ten_seconds_ago
            ]
            
            limit_10s = self.limits['free_models']['requests_per_10s']
            if len(recent_10s_requests) >= limit_10s:
                wait_time = 10 - (current_time - min(recent_10s_requests))
                return False, f"10秒级限制：{len(recent_10s_requests)}/{limit_10s}，请等待 {wait_time:.1f} 秒"
            
            # 检查日级限制
            daily_requests = self.daily_usage.get(model_type, 0)
            
            # 检查是否为付费账户使用免费模型
            is_free_model_in_paid_account = self._is_free_model_in_paid_account(model_name)
            
            if is_free_model_in_paid_account:
                # 免费模型在付费账户中不受日级credit限制，只受请求频率限制
                return True, "免费模型在付费账户中可以发送请求"
            else:
                # 普通限制检查
                daily_limit = self._estimate_daily_limit()
                if daily_requests >= daily_limit:
                    return False, f"日级限制：{daily_requests}/{daily_limit}，今日额度已用完"
            
            return True, "可以发送请求"
    
    def _is_free_model_in_paid_account(self, model_name: str = None) -> bool:
        """检查是否为付费账户使用免费模型
        
        Args:
            model_name: 模型名称
            
        Returns:
            是否为付费账户使用免费模型
        """
        if not model_name:
            return False
            
        # 检查是否为付费账户
        if self.account_info and 'data' in self.account_info:
            is_free_tier = self.account_info['data'].get('is_free_tier', True)
            if not is_free_tier:  # 付费账户
                # 检查是否为免费模型（以:free结尾）
                if model_name.endswith(':free'):
                    return True
        
        return False
    
    def record_request(self, model_type: str = 'free', model_name: str = None):
        """记录请求
        
        Args:
            model_type: 模型类型
            model_name: 模型名称
        """
        with self.lock:
            current_time = time.time()
            
            # 记录到历史
            if model_type not in self.request_history:
                self.request_history[model_type] = []
            self.request_history[model_type].append(current_time)
            
            # 更新日统计（免费模型在付费账户中不计入credit消耗）
            is_free_model_in_paid_account = self._is_free_model_in_paid_account(model_name)
            if not is_free_model_in_paid_account:
                self.daily_usage[model_type] = self.daily_usage.get(model_type, 0) + 1
            
            self.logger.debug(f"记录 {model_type} 请求，今日总计: {self.daily_usage.get(model_type, 0)}，免费模型: {is_free_model_in_paid_account}")
    
    def get_wait_time(self, model_type: str = 'free') -> float:
        """获取需要等待的时间
        
        Args:
            model_type: 模型类型
            
        Returns:
            等待时间（秒）
        """
        can_request, reason = self.can_make_request(model_type)
        
        if can_request:
            return 0.0
        
        # 解析等待时间
        if "等待" in reason:
            try:
                import re
                match = re.search(r'等待 ([\d.]+) 秒', reason)
                if match:
                    return float(match.group(1))
            except:
                pass
        
        # 默认等待1分钟
        return 60.0
    
    def wait_if_needed(self, model_type: str = 'free') -> bool:
        """如果需要的话等待
        
        Args:
            model_type: 模型类型
            
        Returns:
            是否等待了
        """
        wait_time = self.get_wait_time(model_type)
        
        if wait_time > 0:
            self.logger.info(f"API限流等待 {wait_time:.1f} 秒...")
            time.sleep(wait_time)
            return True
        
        return False


class RateLimitedAPIClient:
    """带限流的API客户端包装器"""
    
    def __init__(self, api_client, rate_limiter: RateLimiter):
        """初始化限流API客户端
        
        Args:
            api_client: 原始API客户端
            rate_limiter: 限流器
        """
        self.api_client = api_client
        self.rate_limiter = rate_limiter
        self.logger = logging.getLogger('project_bach.rate_limited_client')
    
    def generate_content(self, model_type: str, *args, **kwargs):
        """生成内容（带限流）
        
        Args:
            model_type: 模型类型
            *args, **kwargs: 传递给原始API客户端的参数
        """
        # 获取实际的模型名称（从API客户端配置中）
        model_name = self.api_client.models.get(model_type, '')
        
        # 检查并等待
        can_request, reason = self.rate_limiter.can_make_request('free', model_name)
        if not can_request:
            self.rate_limiter.wait_if_needed('free')
        
        # 记录请求
        self.rate_limiter.record_request('free', model_name)
        
        try:
            # 调用原始API
            result = self.api_client.generate_content(model_type, *args, **kwargs)
            self.logger.debug(f"API调用成功: {model_type} ({model_name})")
            return result
            
        except Exception as e:
            self.logger.error(f"API调用失败: {str(e)}")
            raise


def create_rate_limited_client(original_client, api_key: str, rate_limit_config: Optional[Dict] = None):
    """创建带限流的API客户端
    
    Args:
        original_client: 原始API客户端
        api_key: API密钥
        rate_limit_config: 限流配置字典
        
    Returns:
        (带限流的API客户端, 限流器实例)
    """
    rate_limiter = RateLimiter(api_key, rate_limit_config)
    return RateLimitedAPIClient(original_client, rate_limiter), rate_limiter