#!/usr/bin/env python3.11
"""
Project Bach Web服务模块
提供基于Web的音频处理服务
"""

from .app import create_app
from .upload_handler import AudioUploadHandler
from .task_manager import TaskManager
from .auth import AuthManager

__all__ = [
    'create_app',
    'AudioUploadHandler',
    'TaskManager', 
    'AuthManager'
]