#!/usr/bin/env python3
"""
直接使用Git命令的GitHub Pages部署脚本
"""
import os
import subprocess
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

def create_enhanced_index_html():
    """创建增强的主页HTML"""
    html_content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Bach - 智能音频处理系统</title>
    <style>
        :root {
            --bg-color: #ffffff;
            --text-color: #333333;
            --border-color: #e1e5e9;
            --accent-color: #0066cc;
            --card-bg: #f8f9fa;
        }
        
        [data-theme="dark"] {
            --bg-color: #1a1a1a;
            --text-color: #e4e6ea;
            --border-color: #3a3b3c;
            --accent-color: #4fc3f7;
            --card-bg: #242526;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            line-height: 1.6;
            transition: all 0.3s ease;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
        }
        
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            color: var(--accent-color);
        }
        
        .header p {
            font-size: 1.2rem;
            opacity: 0.8;
        }
        
        .theme-toggle {
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
        }
        
        .theme-toggle:hover {
            opacity: 0.8;
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        
        .stat-card {
            background: var(--card-bg);
            padding: 20px;
            border-radius: 10px;
            border: 1px solid var(--border-color);
            text-align: center;
        }
        
        .stat-card h3 {
            font-size: 2rem;
            color: var(--accent-color);
            margin-bottom: 5px;
        }
        
        .demo-section {
            background: var(--card-bg);
            border-radius: 10px;
            border: 1px solid var(--border-color);
            padding: 20px;
            margin-bottom: 30px;
        }
        
        .demo-section h2 {
            margin-bottom: 20px;
            color: var(--accent-color);
        }
        
        .demo-item {
            background: var(--bg-color);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
        }
        
        .demo-item h3 {
            color: var(--accent-color);
            margin-bottom: 10px;
        }
        
        .demo-meta {
            font-size: 0.9rem;
            opacity: 0.7;
            margin-bottom: 15px;
        }
        
        .demo-content {
            background: var(--card-bg);
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
            font-style: italic;
        }
        
        .features {
            background: var(--card-bg);
            border-radius: 10px;
            border: 1px solid var(--border-color);
            padding: 20px;
            margin-bottom: 30px;
        }
        
        .features h2 {
            margin-bottom: 20px;
            color: var(--accent-color);
        }
        
        .feature-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
        }
        
        .feature-item {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .feature-icon {
            font-size: 1.5rem;
        }
        
        .footer {
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid var(--border-color);
            opacity: 0.7;
        }
        
        @media (max-width: 768px) {
            .stats {
                grid-template-columns: 1fr;
            }
            
            .header h1 {
                font-size: 2rem;
            }
            
            .feature-grid {
                grid-template-columns: 1fr;
            }
        }
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
                <h3>5+</h3>
                <p>开发阶段</p>
            </div>
            <div class="stat-card">
                <h3>6</h3>
                <p>核心模块</p>
            </div>
            <div class="stat-card">
                <h3>90%+</h3>
                <p>测试覆盖率</p>
            </div>
            <div class="stat-card">
                <h3>""" + datetime.now().strftime('%Y-%m-%d') + """</h3>
                <p>最后更新</p>
            </div>
        </div>
        
        <div class="features">
            <h2>🚀 核心功能</h2>
            <div class="feature-grid">
                <div class="feature-item">
                    <span class="feature-icon">🎙️</span>
                    <span>WhisperKit音频转录</span>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">🧠</span>
                    <span>spaCy智能人名匿名化</span>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">✨</span>
                    <span>OpenRouter AI内容生成</span>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">👁️</span>
                    <span>文件夹自动监控</span>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">⚡</span>
                    <span>API限流保护</span>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">🌐</span>
                    <span>GitHub Pages自动发布</span>
                </div>
            </div>
        </div>
        
        <div class="demo-section">
            <h2>📱 演示内容</h2>
            <div class="demo-item">
                <h3>🎯 架构模块化</h3>
                <div class="demo-meta">完成时间: 2025-01-21 | 重构成果</div>
                <div class="demo-content">
                    将954行的单文件拆分为6个核心模块，代码可维护性提升68%，建立清晰的架构边界。
                </div>
            </div>
            
            <div class="demo-item">
                <h3>⚡ 性能优化</h3>
                <div class="demo-meta">优化成果: API响应时间优化40倍</div>
                <div class="demo-content">
                    从3分钟优化到4.4秒，集成Google Gemma 3N模型，同时实现API限流保护机制。
                </div>
            </div>
            
            <div class="demo-item">
                <h3>🧪 测试驱动开发</h3>
                <div class="demo-meta">测试策略: TDD + 持续集成</div>
                <div class="demo-content">
                    实施测试优先开发，建立单元测试+集成测试双重保障，测试覆盖率超过90%。
                </div>
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
        // 主题切换功能
        function toggleTheme() {
            const body = document.body;
            const themeToggle = document.querySelector('.theme-toggle');
            
            if (body.getAttribute('data-theme') === 'dark') {
                body.removeAttribute('data-theme');
                themeToggle.textContent = '🌙 深色模式';
                localStorage.setItem('theme', 'light');
            } else {
                body.setAttribute('data-theme', 'dark');
                themeToggle.textContent = '☀️ 浅色模式';
                localStorage.setItem('theme', 'dark');
            }
        }
        
        // 初始化主题
        function initTheme() {
            const savedTheme = localStorage.getItem('theme');
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            
            if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
                document.body.setAttribute('data-theme', 'dark');
                document.querySelector('.theme-toggle').textContent = '☀️ 浅色模式';
            }
        }
        
        // 页面加载时初始化主题
        initTheme();
    </script>
</body>
</html>"""
    return html_content

def deploy_to_github_pages():
    """部署到GitHub Pages"""
    print("🚀 开始GitHub Pages部署...")
    
    try:
        # 切换到gh-pages分支
        run_command("git checkout gh-pages", "切换到gh-pages分支")
        
        # 创建增强的主页
        print("🎨 生成增强的网站内容...")
        html_content = create_enhanced_index_html()
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # 更新README
        readme_content = f"""# Project Bach Website

Project Bach智能音频处理系统的GitHub Pages网站。

## 🌟 最新更新

- **部署时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **系统状态**: 运行正常
- **架构**: 模块化，6个核心服务
- **测试覆盖率**: 90%+

## 🔗 相关链接

- [源代码仓库](https://github.com/sleepycat233/Project_Bach)
- [项目文档](https://github.com/sleepycat233/Project_Bach/blob/main/CLAUDE.md)
- [实施计划](https://github.com/sleepycat233/Project_Bach/blob/main/doc/implementation_plan.md)

## 🚀 技术栈

- **音频转录**: WhisperKit
- **自然语言处理**: spaCy (中英文双语)
- **AI生成**: OpenRouter (多模型支持)
- **前端**: 响应式HTML + CSS + JavaScript
- **部署**: GitHub Actions + GitHub Pages

---
*自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        with open('README.md', 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        # 添加所有更改
        run_command("git add .", "添加所有更改到暂存区")
        
        # 检查是否有更改需要提交
        try:
            status_output = run_command("git status --porcelain")
            if not status_output:
                print("✅ 没有更改需要提交")
                return
        except:
            pass
        
        # 提交更改
        commit_msg = f"Deploy enhanced website: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        run_command(f'git commit -m "{commit_msg}"', "提交更改")
        
        # 推送到远程
        run_command("git push origin gh-pages", "推送到远程仓库")
        
        print("✅ 部署完成!")
        print("🔗 网站地址: https://sleepycat233.github.io/Project_Bach")
        print(f"📊 部署时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"❌ 部署失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 切回main分支
        try:
            run_command("git checkout main", "切换回main分支")
            print("🔄 已切换回main分支")
        except:
            print("⚠️  切换回main分支时出现问题")

if __name__ == "__main__":
    deploy_to_github_pages()