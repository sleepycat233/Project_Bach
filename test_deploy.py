#!/usr/bin/env python3
"""
测试GitHub Pages部署功能
"""
import sys
import os
sys.path.append('src')

from publishing.publishing_workflow import PublishingWorkflow
from utils.config import ConfigManager

def main():
    print("🚀 开始测试GitHub Pages部署...")
    
    # 加载配置
    config_manager = ConfigManager()
    config = config_manager.get_config()
    
    # 创建发布工作流
    workflow = PublishingWorkflow(config)
    
    try:
        # 执行完整部署流程
        result = workflow.deploy_to_github_pages()
        
        if result['success']:
            print(f"✅ 部署成功!")
            print(f"📊 部署统计: {result.get('stats', {})}")
            print(f"🔗 网站URL: {result.get('website_url', 'https://sleepycat233.github.io/Project_Bach')}")
        else:
            print(f"❌ 部署失败: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ 部署过程中发生错误: {e}")

if __name__ == "__main__":
    main()