#!/usr/bin/env python3.11
"""
Tailscale VPN连接管理器
处理Tailscale网络连接、状态检查和节点管理
"""

import subprocess
import json
import logging
import time
import os
from typing import Dict, Any, List, Optional


class TailscaleManager:
    """Tailscale VPN连接管理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化Tailscale管理器
        
        Args:
            config: 配置字典，包含auth_key、machine_name等
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
    def check_tailscale_installed(self) -> bool:
        """
        检查Tailscale是否已安装
        
        Returns:
            bool: 是否已安装
        """
        try:
            result = subprocess.run(
                ['tailscale', 'version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                self.logger.info(f"Tailscale已安装: {result.stdout.strip()}")
                return True
            else:
                self.logger.warning("Tailscale命令执行失败")
                return False
        except FileNotFoundError:
            self.logger.error("Tailscale未安装或不在PATH中")
            return False
        except subprocess.TimeoutExpired:
            self.logger.error("Tailscale版本检查超时")
            return False
        except Exception as e:
            self.logger.error(f"检查Tailscale安装状态时出错: {e}")
            return False
    
    def check_status(self) -> Dict[str, Any]:
        """
        检查Tailscale连接状态
        
        Returns:
            Dict: 包含连接状态信息
        """
        try:
            result = subprocess.run(
                ['tailscale', 'status', '--json'],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode != 0:
                self.logger.error(f"获取Tailscale状态失败: {result.stderr}")
                return {'connected': False, 'node_id': None, 'error': result.stderr}
            
            status_data = json.loads(result.stdout)
            backend_state = status_data.get('BackendState', 'Unknown')
            tailscale_ips = status_data.get('TailscaleIPs', [])
            self_info = status_data.get('Self')
            
            is_connected = (
                backend_state == 'Running' and 
                len(tailscale_ips) > 0 and 
                self_info is not None
            )
            
            node_id = self_info.get('ID') if self_info else None
            
            self.logger.info(f"Tailscale状态: {'已连接' if is_connected else '未连接'}")
            
            return {
                'connected': is_connected,
                'node_id': node_id,
                'backend_state': backend_state,
                'tailscale_ips': tailscale_ips,
                'self_info': self_info
            }
            
        except json.JSONDecodeError as e:
            self.logger.error(f"解析Tailscale状态JSON失败: {e}")
            return {'connected': False, 'node_id': None, 'error': str(e)}
        except subprocess.TimeoutExpired:
            self.logger.error("Tailscale状态检查超时")
            return {'connected': False, 'node_id': None, 'error': '超时'}
        except Exception as e:
            self.logger.error(f"检查Tailscale状态时出错: {e}")
            return {'connected': False, 'node_id': None, 'error': str(e)}
    
    def connect(self) -> bool:
        """
        连接到Tailscale网络
        
        Returns:
            bool: 连接是否成功
        """
        if not self.check_tailscale_installed():
            self.logger.error("Tailscale未安装，无法连接")
            return False
        
        auth_key = os.environ.get('TAILSCALE_AUTH_KEY')
        machine_name = self.config.get('machine_name', 'project-bach')
        timeout = self.config.get('timeout', 30)
        
        if not auth_key:
            self.logger.error("缺少TAILSCALE_AUTH_KEY环境变量，无法登录")
            return False
        
        try:
            # 构建登录命令
            cmd = ['tailscale', 'up', '--authkey', auth_key]
            
            if machine_name:
                cmd.extend(['--hostname', machine_name])
            
            self.logger.info(f"开始连接Tailscale网络，机器名: {machine_name}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                self.logger.info("Tailscale连接成功")
                
                # 等待连接稳定
                time.sleep(1)
                
                # 验证连接状态（尝试，但不因为状态检查失败而返回失败）
                try:
                    status = self.check_status()
                    if status['connected']:
                        self.logger.info(f"Tailscale连接已确认，节点ID: {status['node_id']}")
                    else:
                        self.logger.info("Tailscale登录成功，连接状态检查可能需要更多时间")
                except Exception as e:
                    self.logger.debug(f"连接后状态检查失败，但登录本身成功: {e}")
                
                return True
            else:
                self.logger.error(f"Tailscale连接失败: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"Tailscale连接超时 ({timeout}秒)")
            return False
        except Exception as e:
            self.logger.error(f"连接Tailscale时出错: {e}")
            return False
    
    def disconnect(self) -> bool:
        """
        断开Tailscale连接
        
        Returns:
            bool: 断开是否成功
        """
        try:
            self.logger.info("断开Tailscale连接")
            
            result = subprocess.run(
                ['tailscale', 'down'],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0:
                self.logger.info("Tailscale已断开连接")
                return True
            else:
                self.logger.error(f"Tailscale断开失败: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("Tailscale断开连接超时")
            return False
        except Exception as e:
            self.logger.error(f"断开Tailscale时出错: {e}")
            return False
    
    def get_network_info(self) -> Dict[str, Any]:
        """
        获取网络节点信息
        
        Returns:
            Dict: 包含网络节点列表和状态
        """
        try:
            result = subprocess.run(
                ['tailscale', 'status', '--json'],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode != 0:
                self.logger.error(f"获取网络信息失败: {result.stderr}")
                return {'peers': [], 'network_status': 'error', 'error': result.stderr}
            
            status_data = json.loads(result.stdout)
            peer_data = status_data.get('Peer', {})
            
            peers = []
            for peer_id, peer_info in peer_data.items():
                peer = {
                    'id': peer_info.get('ID', peer_id),
                    'hostname': peer_info.get('HostName', 'Unknown'),
                    'dns_name': peer_info.get('DNSName', ''),
                    'os': peer_info.get('OS', 'Unknown'),
                    'tailscale_ips': peer_info.get('TailscaleIPs', []),
                    'online': peer_info.get('Online', False)
                }
                peers.append(peer)
            
            network_status = 'active' if len(peers) > 0 else 'isolated'
            
            self.logger.info(f"发现 {len(peers)} 个网络节点")
            
            return {
                'peers': peers,
                'network_status': network_status,
                'total_peers': len(peers)
            }
            
        except json.JSONDecodeError as e:
            self.logger.error(f"解析网络信息JSON失败: {e}")
            return {'peers': [], 'network_status': 'error', 'error': str(e)}
        except subprocess.TimeoutExpired:
            self.logger.error("获取网络信息超时")
            return {'peers': [], 'network_status': 'timeout', 'error': '超时'}
        except Exception as e:
            self.logger.error(f"获取网络信息时出错: {e}")
            return {'peers': [], 'network_status': 'error', 'error': str(e)}
    
    def validate_config(self) -> bool:
        """
        验证配置有效性
        
        Returns:
            bool: 配置是否有效
        """
        if not self.config:
            self.logger.error("配置为空")
            return False
        
        auth_key = os.environ.get('TAILSCALE_AUTH_KEY', '')
        if not auth_key:
            self.logger.error("缺少TAILSCALE_AUTH_KEY环境变量")
            return False
        
        if not auth_key.startswith('tskey-'):
            self.logger.error("TAILSCALE_AUTH_KEY格式无效，应以'tskey-'开头")
            return False
        
        machine_name = self.config.get('machine_name', '')
        if machine_name:
            # 验证机器名格式（字母数字和连字符）
            import re
            if not re.match(r'^[a-zA-Z0-9\-]+$', machine_name):
                self.logger.error("machine_name包含无效字符")
                return False
        
        timeout = self.config.get('timeout', 30)
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            self.logger.error("timeout必须是正数")
            return False
        
        self.logger.info("Tailscale配置验证通过")
        return True
    
    def ping_peer(self, peer_ip: str, timeout: int = 5) -> Optional[float]:
        """
        Ping指定的Tailscale节点
        
        Args:
            peer_ip: 节点IP地址
            timeout: 超时时间（秒）
            
        Returns:
            float: 延迟时间（毫秒），失败返回None
        """
        try:
            result = subprocess.run(
                ['tailscale', 'ping', peer_ip],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                # 解析ping结果获取延迟
                output = result.stdout.strip()
                if 'time=' in output:
                    import re
                    match = re.search(r'time=(\d+\.?\d*)ms', output)
                    if match:
                        latency = float(match.group(1))
                        self.logger.debug(f"Ping {peer_ip}: {latency}ms")
                        return latency
                
                self.logger.debug(f"Ping {peer_ip} 成功但无法解析延迟")
                return 0.0
            else:
                self.logger.warning(f"Ping {peer_ip} 失败: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            self.logger.warning(f"Ping {peer_ip} 超时")
            return None
        except Exception as e:
            self.logger.error(f"Ping {peer_ip} 时出错: {e}")
            return None