#!/usr/bin/env python3.11
"""
简化的Flask前端启动脚本
用于测试和开发
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.web_frontend.app import create_app

def main():
    """启动开发服务器"""
    
    # 简化配置，跳过安全检查
    test_config = {
        'TESTING': True,  # 跳过Tailscale安全检查
        'SECRET_KEY': 'dev-secret-key',
        'WTF_CSRF_ENABLED': False,
        'UPLOAD_FOLDER': './temp/uploads',
        'MAX_CONTENT_LENGTH': 500 * 1024 * 1024,  # 500MB
        'ALLOWED_EXTENSIONS': {'.mp3', '.wav', '.m4a', '.mp4', '.flac', '.aac', '.ogg'},
        'TAILSCALE_NETWORK': '100.64.0.0/10',
        'RATE_LIMIT_PER_MINUTE': 60
    }
    
    app = create_app(test_config)
    
    print("🚀 启动Project Bach Web界面")
    print("📱 访问地址: http://localhost:8080")
    print("🔒 私有内容: http://localhost:8080/private/")
    print("⚠️  测试模式：跳过Tailscale安全检查")
    
    app.run(host='0.0.0.0', port=8080, debug=True)

if __name__ == "__main__":
    main()