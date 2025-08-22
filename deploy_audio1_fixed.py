#!/usr/bin/env python3
"""
使用PublishingWorkflow部署audio1结果
"""
import sys
import os
sys.path.append('src')

def deploy_with_workflow():
    """使用完整的PublishingWorkflow部署"""
    print("🚀 使用PublishingWorkflow部署audio1结果...")
    
    # 创建临时配置文件
    temp_config_content = '''
github:
  username: "sleepycat233"
  repo_name: "Project_Bach"
  pages_branch: "gh-pages"

paths:
  output_dir: "output"
  templates_dir: "templates"
  
openrouter:
  api_key: "dummy"
  base_url: "https://openrouter.ai/api/v1"
  model: "google/gemma-2-9b-it"
'''
    
    with open('temp_config.yaml', 'w') as f:
        f.write(temp_config_content)
    
    try:
        from utils.config import ConfigManager
        from publishing.publishing_workflow import PublishingWorkflow
        
        # 加载配置
        config_manager = ConfigManager('temp_config.yaml')
        config = config_manager.get_config()
        
        # 创建发布工作流
        workflow = PublishingWorkflow(config)
        
        # 部署到GitHub Pages
        result = workflow.deploy_to_github_pages()
        
        if result.get('success'):
            print("✅ 部署成功!")
            print(f"📊 统计: {result.get('stats', {})}")
            print("🔗 网站地址: https://sleepycat233.github.io/Project_Bach")
        else:
            print(f"❌ 部署失败: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ 部署过程出错: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理临时文件
        if os.path.exists('temp_config.yaml'):
            os.remove('temp_config.yaml')

if __name__ == "__main__":
    deploy_with_workflow()