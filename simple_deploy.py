#!/usr/bin/env python3
"""
简化的GitHub Pages部署脚本
"""
import sys
import os
import json
from datetime import datetime
sys.path.append('src')

from publishing.git_operations import GitOperations
from publishing.template_engine import TemplateEngine

def create_sample_content():
    """创建示例内容用于测试部署"""
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    # 创建示例音频处理结果
    sample_results = [
        {
            "filename": "demo_audio_1.m4a",
            "title": "示例音频 1 - 会议记录",
            "processed_time": "2025-01-20 14:30:00",
            "duration": "3分钟45秒",
            "word_count": 420,
            "transcription": "这是一段示例转录内容，展示Project Bach的音频处理能力...",
            "ai_summary": "## 会议要点\n\n1. 项目进展顺利\n2. 下周安排新功能测试\n3. 团队协作效果良好"
        },
        {
            "filename": "demo_audio_2.m4a", 
            "title": "示例音频 2 - 学习笔记",
            "processed_time": "2025-01-20 15:15:00",
            "duration": "5分钟12秒",
            "word_count": 680,
            "transcription": "今天学习了新的技术概念，包括人工智能和机器学习的应用...",
            "ai_summary": "## 学习总结\n\n- 掌握了AI基础概念\n- 了解了实际应用案例\n- 计划深入学习相关技术"
        }
    ]
    
    # 生成markdown文件
    for i, result in enumerate(sample_results, 1):
        filename = f"audio_result_{i}.md"
        filepath = os.path.join(output_dir, filename)
        
        content = f"""# {result['title']}

**处理时间**: {result['processed_time']}  
**音频时长**: {result['duration']}  
**字数统计**: {result['word_count']}字

## 转录内容
{result['transcription']}

## AI生成总结
{result['ai_summary']}

---
*由Project Bach自动生成 | {result['processed_time']}*
"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
    
    return sample_results

def deploy_to_pages():
    """部署到GitHub Pages"""
    print("🚀 开始GitHub Pages部署...")
    
    # 创建示例内容
    sample_results = create_sample_content()
    print(f"✅ 创建了 {len(sample_results)} 个示例音频结果")
    
    try:
        # 初始化Git操作
        git_ops = GitOperations()
        
        # 初始化模板引擎
        template_engine = TemplateEngine()
        
        # 切换到gh-pages分支
        print("📂 切换到gh-pages分支...")
        git_ops.checkout_branch("gh-pages")
        
        # 生成主页
        print("🎨 生成网站内容...")
        stats = {
            'total_files': len(sample_results),
            'total_words': sum(r['word_count'] for r in sample_results),
            'avg_duration': '4分29秒',
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M')
        }
        
        # 生成主页HTML
        homepage_content = template_engine.render_homepage(sample_results, stats)
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(homepage_content)
        
        # 为每个音频结果生成详细页面
        for i, result in enumerate(sample_results, 1):
            page_content = template_engine.render_content_page(result)
            filename = f"audio_{i}.html"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(page_content)
        
        # 提交并推送更改
        print("📤 提交并推送更改...")
        git_ops.add_all()
        commit_msg = f"Deploy website update: {len(sample_results)} audio results ({stats['last_updated']})"
        git_ops.commit(commit_msg)
        git_ops.push("gh-pages")
        
        print("✅ 部署完成!")
        print("🔗 网站地址: https://sleepycat233.github.io/Project_Bach")
        print(f"📊 部署统计: {stats}")
        
    except Exception as e:
        print(f"❌ 部署失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 切回main分支
        try:
            git_ops.checkout_branch("main")
            print("🔄 已切换回main分支")
        except:
            pass

if __name__ == "__main__":
    deploy_to_pages()