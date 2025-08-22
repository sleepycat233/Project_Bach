#!/usr/bin/env python3.11
"""
安全文件服务器
只允许访问指定文件夹，提供安全的文件传输服务
"""

import os
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import base64


class SecureFileHandler(BaseHTTPRequestHandler):
    """安全文件处理器，只允许访问指定目录"""
    
    def __init__(self, *args, allowed_dirs=None, auth_token=None, **kwargs):
        self.allowed_dirs = allowed_dirs or []
        self.auth_token = auth_token
        super().__init__(*args, **kwargs)
    
    def _is_path_allowed(self, requested_path: str) -> bool:
        """检查请求路径是否在允许的目录范围内"""
        try:
            # 规范化路径，防止目录遍历攻击
            real_path = os.path.realpath(requested_path)
            
            for allowed_dir in self.allowed_dirs:
                allowed_real_path = os.path.realpath(allowed_dir)
                if real_path.startswith(allowed_real_path):
                    return True
            return False
        except Exception:
            return False
    
    def _authenticate(self) -> bool:
        """验证请求认证"""
        if not self.auth_token:
            return True  # 如果没有设置token，则不需要认证
        
        auth_header = self.headers.get('Authorization')
        if not auth_header:
            return False
        
        try:
            # 期望格式: "Bearer <token>"
            if auth_header.startswith('Bearer '):
                provided_token = auth_header[7:]
                return provided_token == self.auth_token
        except Exception:
            pass
        
        return False
    
    def do_GET(self):
        """处理文件下载请求"""
        if not self._authenticate():
            self.send_error(401, "Unauthorized")
            return
        
        # 解析请求路径
        file_path = self.path.lstrip('/')
        if not file_path:
            self._list_allowed_directories()
            return
        
        if not self._is_path_allowed(file_path):
            self.send_error(403, "Access denied - path not allowed")
            return
        
        if not os.path.exists(file_path):
            self.send_error(404, "File not found")
            return
        
        if os.path.isdir(file_path):
            self._list_directory(file_path)
        else:
            self._send_file(file_path)
    
    def do_PUT(self):
        """处理文件上传请求"""
        if not self._authenticate():
            self.send_error(401, "Unauthorized")
            return
        
        file_path = self.path.lstrip('/')
        
        if not self._is_path_allowed(file_path):
            self.send_error(403, "Access denied - path not allowed")
            return
        
        try:
            # 确保目标目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 读取上传的内容
            content_length = int(self.headers['Content-Length'])
            file_data = self.rfile.read(content_length)
            
            # 写入文件
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {
                'status': 'success',
                'message': f'File uploaded: {file_path}',
                'size': len(file_data)
            }
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_error(500, f"Upload failed: {str(e)}")
    
    def _list_allowed_directories(self):
        """列出允许访问的目录"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        dirs_info = []
        for allowed_dir in self.allowed_dirs:
            if os.path.exists(allowed_dir):
                dirs_info.append({
                    'path': allowed_dir,
                    'exists': True,
                    'type': 'directory'
                })
        
        response = {
            'allowed_directories': dirs_info,
            'message': 'These are the directories you can access'
        }
        self.wfile.write(json.dumps(response, indent=2).encode())
    
    def _list_directory(self, dir_path: str):
        """列出目录内容"""
        try:
            items = []
            for item in os.listdir(dir_path):
                item_path = os.path.join(dir_path, item)
                items.append({
                    'name': item,
                    'path': item_path,
                    'is_dir': os.path.isdir(item_path),
                    'size': os.path.getsize(item_path) if os.path.isfile(item_path) else 0
                })
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {
                'directory': dir_path,
                'items': items
            }
            self.wfile.write(json.dumps(response, indent=2).encode())
            
        except Exception as e:
            self.send_error(500, f"Cannot list directory: {str(e)}")
    
    def _send_file(self, file_path: str):
        """发送文件内容"""
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/octet-stream')
            self.send_header('Content-Length', str(len(file_data)))
            self.send_header('Content-Disposition', f'attachment; filename="{os.path.basename(file_path)}"')
            self.end_headers()
            
            self.wfile.write(file_data)
            
        except Exception as e:
            self.send_error(500, f"Cannot send file: {str(e)}")


class SecureFileServer:
    """安全文件服务器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # 配置参数
        self.host = self.config.get('host', '0.0.0.0')
        self.port = self.config.get('port', 8080)
        self.allowed_dirs = self.config.get('allowed_dirs', [])
        self.auth_token = self.config.get('auth_token')
        
        # 生成认证token（如果没有提供）
        if not self.auth_token:
            self.auth_token = self._generate_auth_token()
            self.logger.info(f"Generated auth token: {self.auth_token}")
    
    def _generate_auth_token(self) -> str:
        """生成认证令牌"""
        import secrets
        return secrets.token_urlsafe(32)
    
    def start_server(self):
        """启动文件服务器"""
        try:
            # 创建处理器类，传入配置
            def handler_factory(*args, **kwargs):
                return SecureFileHandler(
                    *args, 
                    allowed_dirs=self.allowed_dirs,
                    auth_token=self.auth_token,
                    **kwargs
                )
            
            server = HTTPServer((self.host, self.port), handler_factory)
            
            self.logger.info(f"启动安全文件服务器: http://{self.host}:{self.port}")
            self.logger.info(f"允许访问的目录: {self.allowed_dirs}")
            self.logger.info(f"认证令牌: {self.auth_token}")
            
            server.serve_forever()
            
        except Exception as e:
            self.logger.error(f"启动文件服务器失败: {e}")
            raise


# 使用示例
if __name__ == "__main__":
    # 配置只允许访问watch_folder
    config = {
        'host': '0.0.0.0',
        'port': 8080,
        'allowed_dirs': [
            './watch_folder',
            './data/output'  # 只允许访问这两个目录
        ],
        'auth_token': 'your-secure-token-here'
    }
    
    server = SecureFileServer(config)
    server.start_server()