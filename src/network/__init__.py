#!/usr/bin/env python3.11
"""
网络集成模块
包含Tailscale VPN管理、文件传输和网络安全功能
"""

from .tailscale_manager import TailscaleManager
__all__ = [
    'TailscaleManager',
]
