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
    
    # 不传入config参数，让create_app使用默认ConfigManager加载config.yaml
    app = create_app()
    
    # 设置测试模式以跳过Tailscale安全检查
    app.config['TESTING'] = True
    
    print("🚀 启动Project Bach Web界面")
    print("📱 访问地址: http://localhost:8080")
    print("🔒 私有内容: http://localhost:8080/private/")
    print("⚠️  测试模式：跳过Tailscale安全检查")
    
    app.run(host='0.0.0.0', port=8080, debug=True)

if __name__ == "__main__":
    main()