#!/usr/bin/env python3
"""
部署audio1处理结果到GitHub Pages
"""
import sys
import os
sys.path.append('src')

# 创建最小配置，避免API验证
class MinimalConfig:
    def __init__(self):
        self.github = {
            'username': 'sleepycat233',
            'repo_name': 'Project_Bach',
            'pages_branch': 'gh-pages'
        }
        self.paths = {
            'output_dir': 'output',
            'templates_dir': 'templates'
        }

def deploy_audio1():
    """直接使用Git命令部署audio1结果"""
    from publishing.template_engine import TemplateEngine
    
    print("🚀 开始部署audio1结果到GitHub Pages...")
    
    try:
        # 创建模板引擎
        template_engine = TemplateEngine()
        
        # 读取audio1结果
        with open('output/audio1_result.md', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析结果数据
        result_data = {
            'filename': 'audio1.m4a',
            'title': 'audio1 - 处理结果',
            'processed_time': '2025-08-20T20:55:34.819885',
            'content': content,
            'word_count': len(content.replace(' ', ''))
        }
        
        print("📊 音频处理结果信息:")
        print(f"  - 文件名: {result_data['filename']}")
        print(f"  - 处理时间: {result_data['processed_time']}")
        print(f"  - 内容长度: {result_data['word_count']}字")
        
        # 切换到gh-pages分支
        os.system('git checkout gh-pages')
        
        # 生成详细页面HTML
        page_content = template_engine.render_content_page(result_data)
        with open('audio1.html', 'w', encoding='utf-8') as f:
            f.write(page_content)
        
        # 更新主页，包含audio1链接
        homepage_content = template_engine.render_homepage([result_data], {
            'total_files': 1,
            'total_words': result_data['word_count'], 
            'avg_duration': '未知',
            'last_updated': '2025-08-22 10:30'
        })
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(homepage_content)
        
        # 提交并推送
        os.system('git add .')
        os.system('git commit -m "Deploy audio1 processing result to GitHub Pages"')
        os.system('git push origin gh-pages')
        
        # 切回main分支
        os.system('git checkout main')
        
        print("✅ 部署完成!")
        print("🔗 网站地址: https://sleepycat233.github.io/Project_Bach")
        print("📄 详细页面: https://sleepycat233.github.io/Project_Bach/audio1.html")
        
    except Exception as e:
        print(f"❌ 部署失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    deploy_audio1()