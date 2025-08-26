#!/usr/bin/env python3.11
"""
部署静态资源同步GitHub Action
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.publishing.github_actions import GitHubActionsManager
from src.utils.config import ConfigManager

def main():
    """主函数"""
    print("🚀 部署静态资源同步GitHub Action")
    
    try:
        # 加载配置
        config_manager = ConfigManager()
        github_config = config_manager.get_nested_config('github')
        
        # 确保必需的配置存在
        if not github_config.get('username'):
            print("❌ 错误: GitHub用户名未配置")
            return False
            
        if not github_config.get('publish_repo'):
            github_config['publish_repo'] = 'Project_Bach'  # 使用当前仓库
            
        # 创建Actions管理器
        actions_manager = GitHubActionsManager(github_config)
        
        # 确定工作流目录
        workflow_dir = project_root / '.github' / 'workflows'
        
        print(f"📁 工作流目录: {workflow_dir}")
        
        # 创建静态资源同步工作流
        print("⚙️  生成静态资源同步工作流...")
        result = actions_manager.create_static_sync_workflow(workflow_dir)
        
        if result['success']:
            print(f"✅ 静态资源同步工作流创建成功!")
            print(f"📄 工作流文件: {result['workflow_file']}")
            
            # 验证工作流配置
            workflow_file = Path(result['workflow_file'])
            if workflow_file.exists():
                workflow_content = workflow_file.read_text()
                validation = actions_manager.validate_workflow_config(workflow_content)
                
                if validation['valid']:
                    print("✅ 工作流配置验证通过")
                    if validation.get('warnings'):
                        print(f"⚠️  警告: {validation['warnings']}")
                else:
                    print(f"❌ 工作流配置无效: {validation['message']}")
                    return False
            
            print("\n📋 接下来的步骤:")
            print("1. git add .github/workflows/sync-static-assets.yml")
            print("2. git commit -m 'feat: Add auto-sync for static assets'")
            print("3. git push origin main")
            print("\n🎯 工作流将在以下情况触发:")
            print("   • main分支的static/或templates/目录有变更时")
            print("   • 手动触发 (workflow_dispatch)")
            print(f"\n🔗 GitHub Pages: https://{github_config['username']}.github.io/Project_Bach")
            
            return True
            
        else:
            print(f"❌ 创建工作流失败: {result['message']}")
            return False
            
    except Exception as e:
        print(f"❌ 部署失败: {str(e)}")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)