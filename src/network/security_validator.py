#!/usr/bin/env python3.11
"""
网络安全验证器
处理网络安全验证、IP过滤和连接权限管理
"""

import socket
import subprocess
import json
import time
import logging
import ipaddress
from typing import Dict, Any, List, Optional, Set
import threading
import ssl


class NetworkSecurityValidator:
    """网络安全验证器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化网络安全验证器
        
        Args:
            config: 安全配置字典
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # 安全配置参数
        self.allowed_networks = self.config.get('allowed_networks', ['100.64.0.0/10'])
        self.blocked_ips = set(self.config.get('blocked_ips', []))
        self.require_encryption = self.config.get('require_encryption', True)
        self.max_connection_attempts = self.config.get('max_connection_attempts', 3)
        self.connection_timeout = self.config.get('connection_timeout', 10)
        
        # 连接频率限制
        self.max_connections_per_minute = self.config.get('max_connections_per_minute', 60)
        self.connection_window_seconds = self.config.get('connection_window_seconds', 60)
        
        # 连接尝试记录
        self._connection_attempts = {}
        self._lock = threading.Lock()
    
    def validate_config(self) -> bool:
        """
        验证安全配置的有效性
        
        Returns:
            bool: 配置是否有效
        """
        try:
            # 验证网络CIDR格式
            for network in self.allowed_networks:
                ipaddress.ip_network(network)
            
            # 验证IP地址格式
            for ip in self.blocked_ips:
                ipaddress.ip_address(ip)
            
            # 验证数值参数
            if not isinstance(self.max_connection_attempts, int) or self.max_connection_attempts <= 0:
                self.logger.error("max_connection_attempts必须是正整数")
                return False
            
            if not isinstance(self.connection_timeout, (int, float)) or self.connection_timeout <= 0:
                self.logger.error("connection_timeout必须是正数")
                return False
            
            self.logger.info("网络安全配置验证通过")
            return True
            
        except Exception as e:
            self.logger.error(f"安全配置验证失败: {e}")
            return False
    
    def is_ip_in_allowed_network(self, ip_address: str) -> bool:
        """
        检查IP地址是否在允许的网络范围内
        
        Args:
            ip_address: IP地址字符串
            
        Returns:
            bool: 是否在允许的网络中
        """
        try:
            ip = ipaddress.ip_address(ip_address)
            
            for network_str in self.allowed_networks:
                network = ipaddress.ip_network(network_str)
                if ip in network:
                    self.logger.debug(f"IP {ip_address} 在允许的网络 {network_str} 中")
                    return True
            
            self.logger.warning(f"IP {ip_address} 不在任何允许的网络中")
            return False
            
        except Exception as e:
            self.logger.error(f"检查IP网络归属时出错: {e}")
            return False
    
    def is_ip_allowed(self, ip_address: str) -> bool:
        """
        检查IP地址是否被允许连接
        
        Args:
            ip_address: IP地址字符串
            
        Returns:
            bool: 是否允许连接
        """
        # 检查是否在黑名单中
        if ip_address in self.blocked_ips:
            self.logger.warning(f"IP {ip_address} 在黑名单中")
            return False
        
        # 检查是否在允许的网络范围内
        return self.is_ip_in_allowed_network(ip_address)
    
    def validate_connection(self, target_ip: str) -> bool:
        """
        验证到目标IP的连接
        
        Args:
            target_ip: 目标IP地址
            
        Returns:
            bool: 连接是否有效
        """
        # 首先检查IP是否被允许
        if not self.is_ip_allowed(target_ip):
            return False
        
        # 检查连接频率限制
        if not self._check_rate_limit(target_ip):
            self.logger.warning(f"连接到 {target_ip} 被频率限制")
            return False
        
        # 尝试建立连接验证
        try:
            # 尝试连接常用端口（如SSH）
            test_ports = [22, 80, 443]
            connection_successful = False
            
            for port in test_ports:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                        sock.settimeout(self.connection_timeout)
                        result = sock.connect_ex((target_ip, port))
                        if result == 0:
                            connection_successful = True
                            self.logger.debug(f"成功连接到 {target_ip}:{port}")
                            break
                except Exception:
                    continue
                
                if connection_successful:
                    self._record_connection_attempt(target_ip, True)
                    return True
                else:
                    self.logger.warning(f"无法连接到 {target_ip} 的任何测试端口")
                    self._record_connection_attempt(target_ip, False)
                    return False
                    
        except Exception as e:
            self.logger.error(f"验证连接到 {target_ip} 时出错: {e}")
            self._record_connection_attempt(target_ip, False)
            return False
    
    def _check_rate_limit(self, ip_address: str) -> bool:
        """
        检查连接频率限制
        
        Args:
            ip_address: IP地址
            
        Returns:
            bool: 是否通过频率检查
        """
        current_time = time.time()
        
        with self._lock:
            if ip_address not in self._connection_attempts:
                self._connection_attempts[ip_address] = []
            
            attempts = self._connection_attempts[ip_address]
            
            # 清理过期的尝试记录
            window_start = current_time - self.connection_window_seconds
            attempts[:] = [t for t in attempts if t > window_start]
            
            # 检查是否超过限制
            if len(attempts) >= self.max_connections_per_minute:
                return False
            
            return True
    
    def _record_connection_attempt(self, ip_address: str, success: bool):
        """
        记录连接尝试
        
        Args:
            ip_address: IP地址
            success: 连接是否成功
        """
        current_time = time.time()
        
        with self._lock:
            if ip_address not in self._connection_attempts:
                self._connection_attempts[ip_address] = []
            
            self._connection_attempts[ip_address].append(current_time)
    
    def check_encryption(self) -> bool:
        """
        检查网络加密状态
        
        Returns:
            bool: 是否启用加密
        """
        if not self.require_encryption:
            return True
        
        try:
            # 检查Tailscale的加密状态
            result = subprocess.run(
                ['tailscale', 'status', '--json'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                status_data = json.loads(result.stdout)
                self_info = status_data.get('Self', {})
                capabilities = self_info.get('Capabilities', [])
                
                # 检查是否支持加密功能
                has_encryption = any(cap in capabilities for cap in ['encrypt', 'wireguard'])
                
                if has_encryption:
                    self.logger.info("Tailscale加密已启用")
                    return True
                else:
                    self.logger.warning("Tailscale加密未启用")
                    return False
            else:
                self.logger.error(f"检查Tailscale加密状态失败: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"检查网络加密时出错: {e}")
            return False
    
    def is_port_secure(self, port: int) -> bool:
        """
        检查端口是否安全
        
        Args:
            port: 端口号
            
        Returns:
            bool: 端口是否被认为是安全的
        """
        # 定义安全端口（加密协议）
        secure_ports = {22, 443, 993, 995, 587, 465}
        
        # 定义常用但相对安全的端口
        common_safe_ports = {80, 8080, 8443, 3000, 5000}
        
        # 定义明确不安全的端口（明文协议）
        insecure_ports = {21, 23, 25, 53, 110, 143}
        
        if port in secure_ports:
            return True
        elif port in insecure_ports:
            return False
        elif port in common_safe_ports:
            return True
        else:
            # 对于其他端口，采用保守策略
            return port > 1024  # 非特权端口通常更安全
    
    def validate_ssl_certificate(self, hostname: str, port: int = 443) -> bool:
        """
        验证SSL证书
        
        Args:
            hostname: 主机名
            port: 端口号
            
        Returns:
            bool: 证书是否有效
        """
        try:
            context = ssl.create_default_context()
            
            with socket.create_connection((hostname, port), timeout=self.connection_timeout) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    
                    if cert:
                        self.logger.debug(f"SSL证书验证成功: {hostname}")
                        return True
                    else:
                        self.logger.warning(f"SSL证书验证失败: {hostname}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"SSL证书验证时出错 {hostname}: {e}")
            return False
    
    def check_firewall_rules(self) -> Dict[str, Any]:
        """
        检查防火墙规则状态
        
        Returns:
            Dict: 防火墙状态信息
        """
        try:
            # 在macOS上检查pfctl状态
            result = subprocess.run(
                ['pfctl', '-s', 'rules'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                rules_output = result.stdout
                
                # 简单解析防火墙规则
                rules = []
                for line in rules_output.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        rules.append(line)
                
                return {
                    'active': True,
                    'rules_count': len(rules),
                    'rules': rules[:10],  # 只返回前10条规则
                    'status': 'active'
                }
            else:
                self.logger.warning("无法获取防火墙规则状态")
                return {
                    'active': False,
                    'status': 'unknown',
                    'error': result.stderr
                }
                
        except FileNotFoundError:
            # pfctl不可用，可能在其他系统上
            self.logger.info("pfctl不可用，跳过防火墙检查")
            return {
                'active': False,
                'status': 'unavailable',
                'reason': 'pfctl not found'
            }
        except Exception as e:
            self.logger.error(f"检查防火墙状态时出错: {e}")
            return {
                'active': False,
                'status': 'error',
                'error': str(e)
            }
    
    def analyze_activity(self, activity: Dict[str, Any]) -> int:
        """
        分析可疑活动并返回威胁等级
        
        Args:
            activity: 活动描述字典
            
        Returns:
            int: 威胁等级 (1-10, 10为最高威胁)
        """
        activity_type = activity.get('type', 'unknown')
        threat_level = 1
        
        if activity_type == 'port_scan':
            ports = activity.get('ports', [])
            threat_level = min(10, 5 + len(ports) // 2)  # 扫描端口越多威胁越高
            
        elif activity_type == 'brute_force':
            attempts = activity.get('attempts', 0)
            threat_level = min(10, 6 + attempts // 5)  # 尝试次数越多威胁越高
            
        elif activity_type == 'unusual_traffic':
            bytes_transferred = activity.get('bytes', 0)
            duration = activity.get('duration', 1)
            rate = bytes_transferred / duration
            
            # 异常高流量
            if rate > 10 * 1024 * 1024:  # 10MB/s
                threat_level = 7
            elif rate > 1 * 1024 * 1024:  # 1MB/s
                threat_level = 5
            else:
                threat_level = 3
        
        self.logger.debug(f"活动 {activity_type} 威胁等级: {threat_level}")
        return threat_level
    
    def check_ip_reputation(self, ip_address: str) -> str:
        """
        检查IP地址信誉
        
        Args:
            ip_address: IP地址
            
        Returns:
            str: 信誉级别 (trusted/public/local/private/suspicious)
        """
        try:
            ip = ipaddress.ip_address(ip_address)
            
            # Tailscale网段 (100.64.0.0/10)
            if ip in ipaddress.ip_network('100.64.0.0/10'):
                return 'trusted'
            
            # 私有网络地址
            if ip.is_private:
                if ip in ipaddress.ip_network('192.168.0.0/16'):
                    return 'local'
                elif ip in ipaddress.ip_network('10.0.0.0/8'):
                    return 'private'
                else:
                    return 'private'
            
            # 公共地址
            if ip.is_global:
                return 'public'
            
            # 其他情况
            return 'unknown'
            
        except Exception as e:
            self.logger.error(f"检查IP信誉时出错: {e}")
            return 'unknown'
    
    def get_security_statistics(self) -> Dict[str, Any]:
        """
        获取安全统计信息
        
        Returns:
            Dict: 安全统计数据
        """
        with self._lock:
            total_attempts = sum(len(attempts) for attempts in self._connection_attempts.values())
            unique_ips = len(self._connection_attempts)
            
            # 计算最近一小时的活动
            current_time = time.time()
            hour_ago = current_time - 3600
            recent_attempts = 0
            
            for attempts in self._connection_attempts.values():
                recent_attempts += sum(1 for t in attempts if t > hour_ago)
            
            return {
                'total_connection_attempts': total_attempts,
                'unique_source_ips': unique_ips,
                'recent_hour_attempts': recent_attempts,
                'blocked_ips_count': len(self.blocked_ips),
                'allowed_networks_count': len(self.allowed_networks),
                'encryption_required': self.require_encryption,
                'rate_limit_enabled': self.max_connections_per_minute > 0
            }


def validate_cidr(cidr: str) -> bool:
    """
    验证CIDR网络地址格式
    
    Args:
        cidr: CIDR格式的网络地址
        
    Returns:
        bool: 格式是否有效
    """
    try:
        ipaddress.ip_network(cidr)
        return True
    except Exception:
        return False