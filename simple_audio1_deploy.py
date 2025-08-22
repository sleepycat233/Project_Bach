#!/usr/bin/env python3
"""
简单直接的audio1结果部署
"""
import os
import subprocess
import json
from datetime import datetime

def run_command(cmd, description=""):
    """执行shell命令"""
    if description:
        print(f"📋 {description}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ 命令执行失败: {cmd}")
        print(f"❌ 错误: {e.stderr}")
        raise

def parse_audio_result():
    """解析audio1结果文件"""
    with open('output/audio1_result.md', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取基本信息
    lines = content.split('\n')
    title = "audio1 - 处理结果"
    processed_time = "2025-08-20 20:55"
    
    for line in lines:
        if line.startswith('**处理时间**'):
            processed_time = line.split('**: ')[1].strip()[:16]  # 截取到分钟
            break
    
    return {
        'filename': 'audio1.m4a',
        'title': title,
        'processed_time': processed_time,
        'content': content,
        'word_count': len([c for c in content if c.isalnum()]),  # 统计字符数
        'summary': content.split('## 内容摘要')[1].split('## 思维导图')[0].strip() if '## 内容摘要' in content else "音频处理结果"
    }

def create_audio1_html(result_data):
    """创建audio1详细页面"""
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{result_data['title']} - Project Bach</title>
    <style>
        :root {{
            --bg-color: #ffffff;
            --text-color: #333333;
            --border-color: #e1e5e9;
            --accent-color: #0066cc;
            --card-bg: #f8f9fa;
        }}
        
        [data-theme="dark"] {{
            --bg-color: #1a1a1a;
            --text-color: #e4e6ea;
            --border-color: #3a3b3c;
            --accent-color: #4fc3f7;
            --card-bg: #242526;
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            line-height: 1.6;
            transition: all 0.3s ease;
        }}
        
        .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
        
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 2px solid var(--accent-color);
        }}
        
        .header h1 {{
            font-size: 2rem;
            color: var(--accent-color);
            margin-bottom: 10px;
        }}
        
        .meta {{
            background: var(--card-bg);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            border: 1px solid var(--border-color);
        }}
        
        .content {{
            background: var(--card-bg);
            padding: 30px;
            border-radius: 10px;
            border: 1px solid var(--border-color);
            white-space: pre-wrap;
            font-family: 'Courier New', monospace;
        }}
        
        .back-link {{
            display: inline-block;
            background: var(--accent-color);
            color: white;
            padding: 10px 20px;
            text-decoration: none;
            border-radius: 5px;
            margin-bottom: 20px;
            transition: all 0.3s ease;
        }}
        
        .back-link:hover {{ opacity: 0.8; }}
        
        .theme-toggle {{
            position: fixed;
            top: 20px;
            right: 20px;
            background: var(--accent-color);
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 20px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s ease;
        }}
        
        .theme-toggle:hover {{ opacity: 0.8; }}
    </style>
</head>
<body>
    <button class="theme-toggle" onclick="toggleTheme()">🌙 深色模式</button>
    
    <div class="container">
        <div class="header">
            <h1>{result_data['title']}</h1>
        </div>
        
        <a href="index.html" class="back-link">← 返回首页</a>
        
        <div class="meta">
            <p><strong>文件名:</strong> {result_data['filename']}</p>
            <p><strong>处理时间:</strong> {result_data['processed_time']}</p>
            <p><strong>内容长度:</strong> {result_data['word_count']}字符</p>
        </div>
        
        <div class="content">{result_data['content']}</div>
    </div>

    <script>
        function toggleTheme() {{
            const body = document.body;
            const themeToggle = document.querySelector('.theme-toggle');
            
            if (body.getAttribute('data-theme') === 'dark') {{
                body.removeAttribute('data-theme');
                themeToggle.textContent = '🌙 深色模式';
                localStorage.setItem('theme', 'light');
            }} else {{
                body.setAttribute('data-theme', 'dark');
                themeToggle.textContent = '☀️ 浅色模式';
                localStorage.setItem('theme', 'dark');
            }}
        }}
        
        function initTheme() {{
            const savedTheme = localStorage.getItem('theme');
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            
            if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {{
                document.body.setAttribute('data-theme', 'dark');
                document.querySelector('.theme-toggle').textContent = '☀️ 浅色模式';
            }}
        }}
        
        initTheme();
    </script>
</body>
</html>"""
    return html_content

def update_homepage(result_data):
    """更新主页，包含audio1链接"""
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Bach - 智能音频处理系统</title>
    <style>
        :root {{
            --bg-color: #ffffff;
            --text-color: #333333;
            --border-color: #e1e5e9;
            --accent-color: #0066cc;
            --card-bg: #f8f9fa;
        }}
        
        [data-theme="dark"] {{
            --bg-color: #1a1a1a;
            --text-color: #e4e6ea;
            --border-color: #3a3b3c;
            --accent-color: #4fc3f7;
            --card-bg: #242526;
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            line-height: 1.6;
            transition: all 0.3s ease;
        }}
        
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        
        .header {{ text-align: center; margin-bottom: 40px; }}
        .header h1 {{ font-size: 2.5rem; margin-bottom: 10px; color: var(--accent-color); }}
        .header p {{ font-size: 1.2rem; opacity: 0.8; }}
        
        .theme-toggle {{
            position: fixed; top: 20px; right: 20px;
            background: var(--accent-color); color: white; border: none;
            padding: 10px 15px; border-radius: 20px; cursor: pointer;
            font-size: 14px; transition: all 0.3s ease;
        }}
        .theme-toggle:hover {{ opacity: 0.8; }}
        
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        
        .stat-card {{
            background: var(--card-bg);
            padding: 20px; border-radius: 10px;
            border: 1px solid var(--border-color);
            text-align: center;
        }}
        
        .stat-card h3 {{ font-size: 2rem; color: var(--accent-color); margin-bottom: 5px; }}
        
        .results {{
            background: var(--card-bg);
            border-radius: 10px; border: 1px solid var(--border-color);
            padding: 20px;
        }}
        
        .results h2 {{ margin-bottom: 20px; color: var(--accent-color); }}
        
        .result-item {{
            display: flex; justify-content: space-between; align-items: center;
            padding: 15px 0; border-bottom: 1px solid var(--border-color);
        }}
        
        .result-item:last-child {{ border-bottom: none; }}
        
        .result-info h3 {{ margin-bottom: 5px; }}
        .result-meta {{ font-size: 0.9rem; opacity: 0.7; }}
        
        .view-btn {{
            background: var(--accent-color); color: white; text-decoration: none;
            padding: 8px 16px; border-radius: 5px; font-size: 0.9rem;
            transition: all 0.3s ease;
        }}
        .view-btn:hover {{ opacity: 0.8; }}
        
        .footer {{ text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid var(--border-color); opacity: 0.7; }}
        
        @media (max-width: 768px) {{
            .stats {{ grid-template-columns: 1fr; }}
            .result-item {{ flex-direction: column; align-items: flex-start; gap: 10px; }}
            .header h1 {{ font-size: 2rem; }}
        }}
    </style>
</head>
<body>
    <button class="theme-toggle" onclick="toggleTheme()">🌙 深色模式</button>
    
    <div class="container">
        <div class="header">
            <h1>Project Bach</h1>
            <p>智能音频处理与内容生成系统</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <h3>1</h3>
                <p>已处理音频</p>
            </div>
            <div class="stat-card">
                <h3>{result_data['word_count']}</h3>
                <p>总字符数</p>
            </div>
            <div class="stat-card">
                <h3>未知</h3>
                <p>平均时长</p>
            </div>
            <div class="stat-card">
                <h3>{datetime.now().strftime('%Y-%m-%d')}</h3>
                <p>最后更新</p>
            </div>
        </div>
        
        <div class="results">
            <h2>处理结果</h2>
            <div class="result-item">
                <div class="result-info">
                    <h3>{result_data['title']}</h3>
                    <div class="result-meta">处理时间: {result_data['processed_time']} | 字符数: {result_data['word_count']}</div>
                </div>
                <a href="audio1.html" class="view-btn">查看详情</a>
            </div>
        </div>
        
        <div class="footer">
            <p><strong>Project Bach</strong> © 2025 | 基于 WhisperKit + OpenRouter + spaCy 构建</p>
            <p style="margin-top: 10px;">
                <a href="https://github.com/sleepycat233/Project_Bach" style="color: var(--accent-color); text-decoration: none;">
                    📂 查看源代码
                </a>
            </p>
        </div>
    </div>

    <script>
        function toggleTheme() {{
            const body = document.body;
            const themeToggle = document.querySelector('.theme-toggle');
            
            if (body.getAttribute('data-theme') === 'dark') {{
                body.removeAttribute('data-theme');
                themeToggle.textContent = '🌙 深色模式';
                localStorage.setItem('theme', 'light');
            }} else {{
                body.setAttribute('data-theme', 'dark');
                themeToggle.textContent = '☀️ 浅色模式';
                localStorage.setItem('theme', 'dark');
            }}
        }}
        
        function initTheme() {{
            const savedTheme = localStorage.getItem('theme');
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            
            if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {{
                document.body.setAttribute('data-theme', 'dark');
                document.querySelector('.theme-toggle').textContent = '☀️ 浅色模式';
            }}
        }}
        
        initTheme();
    </script>
</body>
</html>"""
    return html_content

def deploy_audio1():
    """部署audio1结果到GitHub Pages"""
    print("🚀 开始部署audio1结果到GitHub Pages...")
    
    try:
        # 解析结果数据
        result_data = parse_audio_result()
        print("📊 音频处理结果:")
        print(f"  - 标题: {result_data['title']}")
        print(f"  - 处理时间: {result_data['processed_time']}")
        print(f"  - 字符数: {result_data['word_count']}")
        
        # 切换到gh-pages分支
        run_command("git checkout gh-pages", "切换到gh-pages分支")
        
        # 生成HTML文件
        print("🎨 生成网站内容...")
        
        # 创建audio1详细页面
        audio1_html = create_audio1_html(result_data)
        with open('audio1.html', 'w', encoding='utf-8') as f:
            f.write(audio1_html)
        
        # 更新主页
        homepage_html = update_homepage(result_data)
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(homepage_html)
        
        # 提交并推送
        run_command("git add .", "添加文件到暂存区")
        
        # 检查是否有更改
        status_output = run_command("git status --porcelain")
        if not status_output:
            print("✅ 没有更改需要提交")
            return
        
        commit_msg = f"Deploy audio1 result: {result_data['processed_time']}"
        run_command(f'git commit -m "{commit_msg}"', "提交更改")
        run_command("git push origin gh-pages", "推送到远程仓库")
        
        # 切回main分支
        run_command("git checkout main", "切换回main分支")
        
        print("✅ 部署完成!")
        print("🔗 主页: https://sleepycat233.github.io/Project_Bach")
        print("📄 详细页面: https://sleepycat233.github.io/Project_Bach/audio1.html")
        
    except Exception as e:
        print(f"❌ 部署失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    deploy_audio1()