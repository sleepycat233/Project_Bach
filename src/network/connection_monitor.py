#!/usr/bin/env python3.11
"""
网络连接监控器
监控网络连接状态、延迟和健康度
"""

import time
import threading
import logging
from typing import Dict, Any, List, Optional, Callable
import subprocess


class NetworkConnectionMonitor:
    """网络连接监控器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化网络连接监控器
        
        Args:
            config: 配置字典，包含监控参数
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # 监控状态
        self._monitoring = False
        self._monitor_thread = None
        self._last_check_time = None
        self._connection_history = []
        self._lock = threading.Lock()
        
        # 配置参数
        self.check_interval = self.config.get('check_interval', 30)
        self.timeout = self.config.get('timeout', 5)
        self.max_retries = self.config.get('max_retries', 3)
        self.target_hosts = self.config.get('target_hosts', [])
        self.alert_on_disconnect = self.config.get('alert_on_disconnect', True)
    
    def ping_host(self, host: str, timeout: Optional[int] = None) -> Optional[float]:
        """
        Ping指定主机
        
        Args:
            host: 目标主机IP或域名
            timeout: 超时时间（秒）
            
        Returns:
            float: 延迟时间（秒），失败返回None
        """
        if timeout is None:
            timeout = self.timeout
        
        try:
            # 尝试使用系统ping命令
            result = subprocess.run(
                ['ping', '-c', '1', '-W', str(timeout * 1000), host],
                capture_output=True,
                text=True,
                timeout=timeout + 2
            )
            
            if result.returncode == 0:
                # 解析ping结果获取延迟
                output = result.stdout
                if 'time=' in output:
                    import re
                    match = re.search(r'time=(\d+\.?\d*)\s*ms', output)
                    if match:
                        latency_ms = float(match.group(1))
                        latency_s = latency_ms / 1000.0
                        self.logger.debug(f"Ping {host}: {latency_ms:.1f}ms")
                        return latency_s
                
                # 如果无法解析延迟，返回0表示连通但未知延迟
                self.logger.debug(f"Ping {host} 成功但无法解析延迟")
                return 0.0
            else:
                self.logger.debug(f"Ping {host} 失败: {result.stderr.strip()}")
                return None
                
        except subprocess.TimeoutExpired:
            self.logger.warning(f"Ping {host} 超时 ({timeout}s)")
            return None
        except FileNotFoundError:
            self.logger.error("系统ping命令不可用")
            return None
        except Exception as e:
            self.logger.error(f"Ping {host} 时出错: {e}")
            return None
    
    def check_all_hosts(self) -> Dict[str, Optional[float]]:
        """
        检查所有目标主机的连接状态
        
        Returns:
            Dict: 主机IP -> 延迟时间的字典
        """
        results = {}
        
        for host in self.target_hosts:
            latency = self.ping_host(host)
            results[host] = latency
            
            if latency is None and self.alert_on_disconnect:
                self.logger.warning(f"主机 {host} 连接失败")
            elif latency is not None:
                self.logger.debug(f"主机 {host} 连接正常，延迟: {latency*1000:.1f}ms")
        
        return results
    
    def start_monitoring(self) -> bool:
        """
        开始监控网络连接
        
        Returns:
            bool: 是否成功启动监控
        """
        if self._monitoring:
            self.logger.warning("网络监控已在运行")
            return True
        
        if not self.target_hosts:
            self.logger.error("未配置监控目标主机")
            return False
        
        try:
            self._monitoring = True
            self._monitor_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True,
                name="NetworkMonitor"
            )
            self._monitor_thread.start()
            
            self.logger.info(f"网络监控已启动，监控间隔: {self.check_interval}s")
            return True
            
        except Exception as e:
            self.logger.error(f"启动网络监控失败: {e}")
            self._monitoring = False
            return False
    
    def stop_monitoring(self) -> bool:
        """
        停止监控网络连接
        
        Returns:
            bool: 是否成功停止监控
        """
        if not self._monitoring:
            self.logger.info("网络监控未在运行")
            return True
        
        try:
            self._monitoring = False
            
            if self._monitor_thread and self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=5)
            
            self.logger.info("网络监控已停止")
            return True
            
        except Exception as e:
            self.logger.error(f"停止网络监控失败: {e}")
            return False
    
    def _monitoring_loop(self):
        """监控循环（内部方法）"""
        while self._monitoring:
            try:
                # 执行连接检查
                check_time = time.time()
                results = self.check_all_hosts()
                
                # 记录检查结果
                with self._lock:
                    self._last_check_time = check_time
                    
                    # 保留最近100条记录
                    self._connection_history.append({
                        'timestamp': check_time,
                        'results': results
                    })
                    
                    if len(self._connection_history) > 100:
                        self._connection_history.pop(0)
                
                # 分析连接状态
                successful_hosts = [host for host, latency in results.items() if latency is not None]
                failed_hosts = [host for host, latency in results.items() if latency is None]
                
                if len(successful_hosts) == len(self.target_hosts):
                    self.logger.debug("所有目标主机连接正常")
                elif len(failed_hosts) == len(self.target_hosts):
                    self.logger.error("所有目标主机连接失败")
                else:
                    self.logger.warning(f"部分主机连接失败: {failed_hosts}")
                
                # 等待下次检查
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"监控循环出错: {e}")
                time.sleep(5)  # 出错后短暂等待
    
    def get_connection_status(self) -> Dict[str, Any]:
        """
        获取当前连接状态
        
        Returns:
            Dict: 连接状态信息
        """
        with self._lock:
            if not self._last_check_time:
                return {
                    'status': 'unknown',
                    'last_check': None,
                    'monitoring_active': self._monitoring
                }
            
            # 获取最新检查结果
            latest_result = self._connection_history[-1] if self._connection_history else None
            
            if not latest_result:
                return {
                    'status': 'unknown',
                    'last_check': self._last_check_time,
                    'monitoring_active': self._monitoring
                }
            
            results = latest_result['results']
            successful_count = sum(1 for latency in results.values() if latency is not None)
            total_count = len(results)
            
            # 确定整体状态
            if successful_count == total_count:
                status = 'connected'
            elif successful_count == 0:
                status = 'disconnected'
            else:
                status = 'partial'
            
            # 计算平均延迟
            latencies = [latency for latency in results.values() if latency is not None]
            avg_latency = sum(latencies) / len(latencies) if latencies else None
            
            return {
                'status': status,
                'last_check': self._last_check_time,
                'monitoring_active': self._monitoring,
                'successful_hosts': successful_count,
                'total_hosts': total_count,
                'success_rate': successful_count / total_count if total_count > 0 else 0,
                'average_latency': avg_latency,
                'host_results': results
            }
    
    def calculate_health_score(self, success_rate: float, avg_latency: float) -> str:
        """
        计算连接健康评分
        
        Args:
            success_rate: 成功率 (0-1)
            avg_latency: 平均延迟 (秒)
            
        Returns:
            str: 健康评分 (excellent/good/fair/poor)
        """
        # 将延迟转换为毫秒
        latency_ms = avg_latency * 1000 if avg_latency else float('inf')
        
        if success_rate >= 0.95 and latency_ms <= 50:
            return 'excellent'
        elif success_rate >= 0.85 and latency_ms <= 100:
            return 'good'
        elif success_rate >= 0.70 and latency_ms <= 200:
            return 'fair'
        else:
            return 'poor'
    
    def get_connection_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取连接历史记录
        
        Args:
            limit: 返回记录数量限制
            
        Returns:
            List: 连接历史记录
        """
        with self._lock:
            history = self._connection_history[-limit:] if self._connection_history else []
            
            # 为每条记录添加健康评分
            enhanced_history = []
            for record in history:
                results = record['results']
                
                # 计算该次检查的统计
                latencies = [latency for latency in results.values() if latency is not None]
                success_rate = len(latencies) / len(results) if results else 0
                avg_latency = sum(latencies) / len(latencies) if latencies else 0
                
                health_score = self.calculate_health_score(success_rate, avg_latency)
                
                enhanced_record = record.copy()
                enhanced_record.update({
                    'success_rate': success_rate,
                    'average_latency': avg_latency,
                    'health_score': health_score
                })
                
                enhanced_history.append(enhanced_record)
            
            return enhanced_history
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取监控统计信息
        
        Returns:
            Dict: 统计信息
        """
        with self._lock:
            if not self._connection_history:
                return {
                    'total_checks': 0,
                    'monitoring_duration': 0,
                    'overall_success_rate': 0,
                    'average_latency': None,
                    'best_latency': None,
                    'worst_latency': None
                }
            
            total_checks = len(self._connection_history)
            first_check = self._connection_history[0]['timestamp']
            last_check = self._connection_history[-1]['timestamp']
            monitoring_duration = last_check - first_check
            
            # 计算总体统计
            all_latencies = []
            successful_checks = 0
            
            for record in self._connection_history:
                results = record['results']
                latencies = [latency for latency in results.values() if latency is not None]
                
                if len(latencies) == len(results):  # 所有主机都成功
                    successful_checks += 1
                
                all_latencies.extend(latencies)
            
            overall_success_rate = successful_checks / total_checks if total_checks > 0 else 0
            average_latency = sum(all_latencies) / len(all_latencies) if all_latencies else None
            best_latency = min(all_latencies) if all_latencies else None
            worst_latency = max(all_latencies) if all_latencies else None
            
            return {
                'total_checks': total_checks,
                'monitoring_duration': monitoring_duration,
                'overall_success_rate': overall_success_rate,
                'average_latency': average_latency,
                'best_latency': best_latency,
                'worst_latency': worst_latency,
                'total_hosts_monitored': len(self.target_hosts)
            }