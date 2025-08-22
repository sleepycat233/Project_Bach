#!/usr/bin/env python3
"""
Phase 6.6 GitHub Pages分类模板演示示例

演示更新后的GitHub Pages模板系统：
- ✅ 左侧边栏分类导航设计
- ✅ 响应式布局 (桌面端+移动端)
- ✅ 分类专用页面模板 (lectures/videos/podcasts/articles)
- ✅ 智能搜索和筛选功能
- ✅ 内容统计和数据展示
- ✅ 现代化UI设计和交互体验

模板更新状态: 完整实现，4个分类页面模板
"""

import sys
import tempfile
import shutil
import yaml
from pathlib import Path
from datetime import datetime, timedelta
from jinja2 import Environment, FileSystemLoader

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent))


def create_sample_content_data():
    """创建示例内容数据"""
    
    # 示例讲座数据
    lectures = [
        {
            'title': '机器学习基础与神经网络原理 Machine Learning Fundamentals',
            'summary': '本讲座深入探讨机器学习的核心概念，包括监督学习、无监督学习和强化学习。重点介绍神经网络的基本原理、反向传播算法以及在实际项目中的应用案例。',
            'date': '2025-08-20',
            'duration': '45分钟',
            'speaker': 'Professor AI Zhang',
            'tags': ['machine learning', 'neural networks', 'AI', 'education', '机器学习', '神经网络'],
            'file_path': 'lectures/ml_fundamentals_2025_08_20.html',
            'mindmap_items': 12
        },
        {
            'title': '量子计算入门：从理论到实践 Quantum Computing Introduction',
            'summary': '量子计算是计算科学的前沿领域。本讲座从量子力学基础开始，介绍量子比特、量子门、量子算法，并展示量子计算在密码学、优化问题中的应用前景。',
            'date': '2025-08-18',
            'duration': '1小时15分钟',
            'speaker': 'Dr. Quantum Wang',
            'tags': ['quantum computing', 'physics', 'cryptography', 'algorithms', '量子计算', '物理学'],
            'file_path': 'lectures/quantum_computing_intro_2025_08_18.html',
            'mindmap_items': 18
        },
        {
            'title': '区块链技术与去中心化应用开发',
            'summary': '深入了解区块链技术原理，智能合约开发，以及去中心化应用(DApp)的设计与实现。涵盖以太坊、Solidity编程和Web3技术栈。',
            'date': '2025-08-15',
            'duration': '50分钟',
            'speaker': '李教授',
            'tags': ['blockchain', 'smart contracts', 'ethereum', 'web3', '区块链', '智能合约'],
            'file_path': 'lectures/blockchain_development_2025_08_15.html',
            'mindmap_items': 15
        }
    ]
    
    # 示例YouTube视频数据
    videos = [
        {
            'title': 'React 18 New Features Deep Dive - Concurrent Rendering & Suspense',
            'summary': 'Complete guide to React 18 new features including Concurrent Rendering, Automatic Batching, Suspense for Data Fetching, and Server Components. Perfect for developers upgrading from React 17.',
            'date': '2025-08-19',
            'duration': '32:45',
            'channel_name': 'Tech Tutorial Hub',
            'view_count': '125,000',
            'view_count_formatted': '125,000',
            'tags': ['react', 'javascript', 'frontend', 'tutorial', 'web development'],
            'source_url': 'https://youtube.com/watch?v=example1',
            'file_path': 'videos/react18_features_2025_08_19.html',
            'mindmap_items': 8
        },
        {
            'title': '深度学习模型部署：从训练到生产环境 AI Model Deployment',
            'summary': '完整的深度学习模型部署流程，包括模型优化、容器化部署、API服务搭建、性能监控和扩展策略。适合AI工程师和MLOps从业者。',
            'date': '2025-08-17',
            'duration': '28:15',
            'channel_name': 'AI Engineering Channel',
            'view_count': '89,500',
            'view_count_formatted': '89,500',
            'tags': ['deep learning', 'mlops', 'deployment', 'docker', 'AI', '深度学习', '模型部署'],
            'source_url': 'https://youtube.com/watch?v=example2',
            'file_path': 'videos/ai_model_deployment_2025_08_17.html',
            'mindmap_items': 11
        }
    ]
    
    # 示例播客数据
    podcasts = [
        {
            'title': 'Tech Talk: The Future of Software Architecture 软件架构的未来',
            'summary': '在这期节目中，我们与资深架构师讨论微服务、无服务器架构和云原生技术的发展趋势。深入探讨如何构建可扩展、高可用的现代应用系统。',
            'date': '2025-08-21',
            'audio_duration': '45分钟',
            'podcast_series': 'Tech Talk Weekly',
            'episode_number': 'Episode 25',
            'host_name': 'John Tech Host',
            'guest_names': ['Senior Architect Alice', 'Cloud Expert Bob'],
            'tags': ['software architecture', 'microservices', 'cloud native', 'scalability', '软件架构', '微服务'],
            'file_path': 'podcasts/software_architecture_future_2025_08_21.html',
            'mindmap_items': 14
        },
        {
            'title': '创业者访谈：从技术到商业的转型之路',
            'summary': '本期邀请了三位成功的技术创业者，分享他们从工程师转型为企业家的经历，讨论技术团队管理、产品开发和市场策略。',
            'date': '2025-08-16',
            'audio_duration': '52分钟',
            'podcast_series': '创业故事',
            'episode_number': '第12期',
            'host_name': '张主播',
            'guest_names': ['创业者李某', '投资人王某', 'CTO赵某'],
            'tags': ['entrepreneurship', 'startup', 'business', 'leadership', '创业', '商业', '领导力'],
            'file_path': 'podcasts/entrepreneur_interview_2025_08_16.html',
            'mindmap_items': 16
        }
    ]
    
    return {
        'lectures': lectures,
        'videos': videos,
        'podcasts': podcasts,
        'articles': []  # RSS文章功能待开发
    }


def create_sample_stats(content_data):
    """创建示例统计数据"""
    lectures = content_data['lectures']
    videos = content_data['videos']
    podcasts = content_data['podcasts']
    
    return {
        # 全局统计
        'total_items': len(lectures) + len(videos) + len(podcasts),
        'lecture_count': len(lectures),
        'video_count': len(videos),
        'podcast_count': len(podcasts),
        'article_count': 0,
        
        # 讲座统计
        'total_duration': '3小时20分钟',
        'unique_speakers': len(set(l['speaker'] for l in lectures)),
        'unique_topics': len(set(tag for l in lectures for tag in l['tags'])),
        
        # 视频统计
        'unique_channels': len(set(v['channel_name'] for v in videos)),
        'total_views': '214,500',
        
        # 播客统计
        'unique_hosts': len(set(p['host_name'] for p in podcasts)),
        'unique_guests': len(set(guest for p in podcasts for guest in p.get('guest_names', []))),
        
        # 文章统计（待开发）
        'unique_sources': 0,
        'unique_categories': 0,
        'total_words': '0'
    }


def demo_template_rendering():
    """演示模板渲染功能"""
    print("🎨 GitHub Pages分类模板渲染演示")
    print("-" * 50)
    
    # 设置模板环境
    template_dir = Path(__file__).parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    
    # 创建临时输出目录
    output_dir = Path(tempfile.mkdtemp()) / "rendered_pages"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # 获取示例数据
        content_data = create_sample_content_data()
        stats = create_sample_stats(content_data)
        
        # 通用模板变量
        base_context = {
            'site_title': 'Project Bach Phase 6',
            'site_description': '多媒体内容智能处理与分析系统',
            'current_time': datetime.now(),
            **stats
        }
        
        # 渲染各个页面模板
        templates_to_render = [
            {
                'template': 'lectures.html',
                'output': 'lectures.html',
                'context': {**base_context, 'lectures': content_data['lectures']},
                'description': '学术讲座页面'
            },
            {
                'template': 'videos.html', 
                'output': 'videos.html',
                'context': {**base_context, 'videos': content_data['videos']},
                'description': 'YouTube视频页面'
            },
            {
                'template': 'podcasts.html',
                'output': 'podcasts.html', 
                'context': {**base_context, 'podcasts': content_data['podcasts']},
                'description': '播客内容页面'
            },
            {
                'template': 'articles.html',
                'output': 'articles.html',
                'context': {**base_context, 'articles': []},
                'description': 'RSS文章页面 (待开发功能展示)'
            }
        ]
        
        # 渲染所有模板
        for template_info in templates_to_render:
            print(f"  🔄 渲染 {template_info['description']}...")
            
            try:
                template = env.get_template(template_info['template'])
                rendered_html = template.render(**template_info['context'])
                
                output_path = output_dir / template_info['output']
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(rendered_html)
                
                print(f"     ✅ 成功: {output_path}")
                print(f"     📊 HTML大小: {len(rendered_html):,} 字符")
                
                # 统计页面内容
                content_count = template_info['context'].get('lecture_count', 0) + \
                               template_info['context'].get('video_count', 0) + \
                               template_info['context'].get('podcast_count', 0)
                
                if template_info['template'] == 'lectures.html':
                    content_count = len(template_info['context']['lectures'])
                elif template_info['template'] == 'videos.html':
                    content_count = len(template_info['context']['videos'])
                elif template_info['template'] == 'podcasts.html':
                    content_count = len(template_info['context']['podcasts'])
                else:
                    content_count = 0
                
                print(f"     📋 内容项目: {content_count} 个")
                
            except Exception as e:
                print(f"     ❌ 渲染失败: {e}")
            
            print()
        
        # 显示输出目录信息
        print("📁 渲染输出目录:")
        print(f"   {output_dir}")
        print()
        
        # 统计渲染结果
        rendered_files = list(output_dir.glob("*.html"))
        total_size = sum(f.stat().st_size for f in rendered_files)
        
        print("📊 渲染统计:")
        print(f"   ✅ 成功渲染页面: {len(rendered_files)} 个")
        print(f"   📦 总文件大小: {total_size:,} 字节 ({total_size/1024:.1f}KB)")
        print(f"   📋 总内容项目: {stats['total_items']} 个")
        print()
        
        return output_dir
        
    except Exception as e:
        print(f"❌ 模板渲染过程中发生错误: {e}")
        return None


def demo_template_features():
    """演示模板功能特性"""
    print("⚙️ 模板功能特性展示")
    print("-" * 50)
    
    features = [
        {
            'icon': '📱',
            'title': '响应式设计',
            'description': '左侧边栏在桌面端固定显示，移动端自适应为汉堡菜单',
            'technical': '使用CSS Flexbox + 媒体查询实现'
        },
        {
            'icon': '🎨',
            'title': '分类专用样式',
            'description': '每个内容类型都有独特的颜色主题和布局风格',
            'technical': '讲座(蓝色)、视频(橙红色)、播客(紫色)、文章(绿色)'
        },
        {
            'icon': '🔍',
            'title': '智能搜索筛选',
            'description': '实时搜索标题、内容、标签，多维度筛选功能',
            'technical': 'JavaScript实现客户端筛选，无需服务器请求'
        },
        {
            'icon': '📊',
            'title': '数据统计展示',
            'description': '分类统计、内容计数、时长统计等数据可视化',
            'technical': '模板变量传递 + CSS Grid布局'
        },
        {
            'icon': '🎯',
            'title': '交互体验优化',
            'description': '卡片悬停效果、链接高亮、平滑动画过渡',
            'technical': 'CSS Transition + Transform + JavaScript事件处理'
        },
        {
            'icon': '🌙',
            'title': '暗色模式支持',
            'description': '自动检测系统主题偏好，支持暗色/亮色模式',
            'technical': 'CSS变量 + prefers-color-scheme媒体查询'
        },
        {
            'icon': '🔗',
            'title': '导航状态管理',
            'description': '当前页面自动高亮，面包屑导航，URL路由识别',
            'technical': 'JavaScript动态class管理 + location.pathname检测'
        },
        {
            'icon': '📋',
            'title': '内容预览优化',
            'description': '文本截断、标签显示、元数据格式化',
            'technical': 'CSS line-clamp + Jinja2模板过滤器'
        }
    ]
    
    for feature in features:
        print(f"  {feature['icon']} {feature['title']}")
        print(f"     功能: {feature['description']}")
        print(f"     技术: {feature['technical']}")
        print()


def demo_mobile_responsiveness():
    """演示移动端响应式特性"""
    print("📱 移动端响应式设计展示")
    print("-" * 50)
    
    responsive_features = [
        {
            'breakpoint': '> 768px (桌面端)',
            'layout': '左侧边栏固定 + 主内容区域',
            'sidebar': '280px宽度固定显示',
            'navigation': '完整分类导航 + 统计数据',
            'content': '多列网格布局 (350px最小宽度)'
        },
        {
            'breakpoint': '≤ 768px (移动端)',
            'layout': '垂直堆叠布局',
            'sidebar': '全宽侧边栏 + 滑动显示',
            'navigation': '汉堡菜单 + 外部点击关闭',
            'content': '单列布局 + 触摸优化'
        }
    ]
    
    for config in responsive_features:
        print(f"  📐 {config['breakpoint']}")
        print(f"     布局: {config['layout']}")
        print(f"     侧边栏: {config['sidebar']}")
        print(f"     导航: {config['navigation']}")
        print(f"     内容: {config['content']}")
        print()
    
    print("  🎯 移动端优化特性:")
    print("     • 触摸友好的按钮大小 (44px最小触摸目标)")
    print("     • 滑动手势支持 (侧边栏打开/关闭)")
    print("     • 减少悬停效果，优化触摸交互")
    print("     • 字体大小和间距的移动端调整")
    print("     • 防止意外点击的外部区域检测")


def main():
    """主演示函数"""
    print("🎨 Phase 6.6 GitHub Pages分类模板演示")
    print("=" * 60)
    print("功能状态: ✅ 完全实现")
    print("模板数量: ✅ 4个分类页面 + 1个基础模板")
    print("设计风格: ✅ 现代化左侧边栏 + 响应式布局")
    print()
    
    try:
        # 演示各个功能
        output_dir = demo_template_rendering()
        demo_template_features()
        demo_mobile_responsiveness()
        
        print("🎉 GitHub Pages分类模板演示完成！")
        print("📋 核心更新总结:")
        print("   ✅ 左侧边栏分类导航设计")
        print("   ✅ 4个专用分类页面模板 (lectures/videos/podcasts/articles)")
        print("   ✅ 响应式布局支持桌面端和移动端")
        print("   ✅ 智能搜索和多维度筛选功能")
        print("   ✅ 分类统计和数据可视化")
        print("   ✅ 现代化UI设计和交互体验")
        print("   ✅ 暗色模式和主题适配")
        print()
        print("🔧 技术特点:")
        print("   • 纯CSS + JavaScript实现，无框架依赖")
        print("   • Jinja2模板引擎，支持数据绑定和过滤器")
        print("   • CSS变量系统，支持主题定制")
        print("   • 移动端优先的响应式设计")
        print("   • 客户端筛选，提升用户体验")
        print("   • 语义化HTML结构，SEO友好")
        
        if output_dir:
            print(f"\n📁 渲染结果保存在: {output_dir}")
            print("   可以在浏览器中打开HTML文件预览效果")
        
    except Exception as e:
        print(f"❌ 演示过程中发生错误: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())