#!/usr/bin/env python3
"""
Phase 6 ContentFormatter演示示例

演示增强的ContentFormatter如何处理不同类型的多媒体内容：
- YouTube视频 (📺)
- 学术讲座 (🎓) 
- RSS文章 (📰)
- 播客内容 (🎙️)

用户反馈：内容主要是中英双语，以英文为主
"""

import sys
import tempfile
import shutil
import yaml
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.config import ConfigManager
from src.publishing.content_formatter import ContentFormatter


def create_test_config():
    """创建测试配置"""
    temp_dir = tempfile.mkdtemp()
    
    config_data = {
        'content_classification': {
            'content_types': {
                'lecture': {
                    'icon': '🎓',
                    'display_name': '讲座',
                    'description': '学术讲座、课程录音、教育内容'
                },
                'youtube': {
                    'icon': '📺', 
                    'display_name': '视频',
                    'description': 'YouTube视频内容、教学视频、技术分享'
                },
                'rss': {
                    'icon': '📰',
                    'display_name': '文章', 
                    'description': 'RSS订阅文章、技术博客、新闻资讯'
                },
                'podcast': {
                    'icon': '🎙️',
                    'display_name': '播客',
                    'description': '播客节目、访谈内容、讨论节目'
                }
            }
        }
    }
    
    config_path = Path(temp_dir) / "config.yaml"
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config_data, f, allow_unicode=True)
    
    return ConfigManager(str(config_path)), temp_dir


def create_sample_content_data():
    """创建示例内容数据"""
    
    # 1. YouTube视频 - 机器学习教程（中英双语，英文为主）
    youtube_content = {
        'title': 'Deep Learning Fundamentals and Neural Networks 深度学习基础',
        'summary': '''This comprehensive tutorial covers the fundamental concepts of deep learning and neural networks. 
        We'll explore how artificial neurons work, backpropagation algorithms, and practical applications in computer vision and natural language processing.
        
        本教程全面介绍了深度学习和神经网络的基本概念。我们将探讨人工神经元的工作原理、反向传播算法，以及在计算机视觉和自然语言处理中的实际应用。''',
        'mindmap': '''# Deep Learning Tutorial
## Core Concepts
- Neural Networks 神经网络
- Backpropagation 反向传播
- Gradient Descent 梯度下降

## Applications 应用
- Computer Vision 计算机视觉
- Natural Language Processing 自然语言处理
- Reinforcement Learning 强化学习''',
        'processed_time': datetime.now().isoformat(),
        'original_file': 'ml_tutorial_video.mp4',
        'source_url': 'https://www.youtube.com/watch?v=deeplearning123',
        'channel_name': 'AI Education Channel',
        'video_duration': '45 minutes',
        'view_count': '125,000',
        'classification_result': {
            'content_type': 'youtube',
            'confidence': 0.92,
            'auto_detected': True,
            'tags': ['machine learning', 'deep learning', 'neural networks', 'AI', 'tutorial', 'education']
        },
        'anonymized_names': {}
    }
    
    # 2. 学术讲座 - 量子物理讲座（中英双语，英文为主）
    lecture_content = {
        'title': 'Quantum Mechanics in Modern Physics 现代物理学中的量子力学',
        'summary': '''This academic lecture discusses the principles of quantum mechanics and their applications in modern physics research.
        Topics include wave-particle duality, quantum entanglement, and the implications for quantum computing.
        
        这场学术讲座讨论了量子力学原理及其在现代物理学研究中的应用。主题包括波粒二象性、量子纠缠，以及对量子计算的意义。''',
        'mindmap': '''# Quantum Mechanics Lecture
## Fundamental Principles 基本原理
- Wave-Particle Duality 波粒二象性
- Uncertainty Principle 不确定性原理
- Quantum Superposition 量子叠加

## Applications 应用
- Quantum Computing 量子计算
- Quantum Cryptography 量子密码学
- Quantum Sensors 量子传感器''',
        'processed_time': datetime.now().isoformat(),
        'original_file': 'quantum_physics_lecture.mp3',
        'lecturer': 'Professor Smith',
        'institution': 'MIT Physics Department',
        'course_name': 'Advanced Quantum Mechanics',
        'academic_field': 'Physics',
        'classification_result': {
            'content_type': 'lecture',
            'confidence': 0.88,
            'auto_detected': True,
            'tags': ['quantum mechanics', 'physics', 'academia', 'research', 'university']
        },
        'anonymized_names': {'Dr. Wilson': 'Professor Smith'}
    }
    
    # 3. RSS文章 - 技术博客（中英双语，英文为主）
    rss_content = {
        'title': 'The Future of Artificial Intelligence in Software Development AI在软件开发中的未来',
        'summary': '''This article explores how artificial intelligence is transforming software development practices.
        From automated code generation to intelligent debugging, AI tools are revolutionizing the way developers work.
        
        本文探讨了人工智能如何改变软件开发实践。从自动代码生成到智能调试，AI工具正在革命性地改变开发者的工作方式。''',
        'mindmap': '''# AI in Software Development
## Current Applications 当前应用
- Code Generation 代码生成
- Automated Testing 自动化测试
- Bug Detection 错误检测

## Future Trends 未来趋势
- Intelligent IDEs 智能开发环境
- Natural Language Programming 自然语言编程
- Autonomous Development 自主开发''',
        'processed_time': datetime.now().isoformat(),
        'original_file': 'ai_software_development.html',
        'source_url': 'https://tech-blog.com/ai-software-development',
        'author': 'Tech Blogger',
        'published_date': '2025-08-22',
        'category': 'Technology',
        'classification_result': {
            'content_type': 'rss',
            'confidence': 0.85,
            'auto_detected': True,
            'tags': ['artificial intelligence', 'software development', 'programming', 'technology', 'automation']
        },
        'anonymized_names': {}
    }
    
    # 4. 播客 - 技术访谈（中英双语，英文为主）
    podcast_content = {
        'title': 'Tech Talk: The Evolution of Web Development Web开发的演进',
        'summary': '''In this episode, we interview senior developers about the evolution of web development technologies.
        Discussion covers JavaScript frameworks, cloud computing, and the future of web applications.
        
        在这期节目中，我们采访了资深开发者关于Web开发技术的演进。讨论涵盖JavaScript框架、云计算和Web应用的未来。''',
        'mindmap': '''# Web Development Evolution
## Past Technologies 过去的技术
- Static HTML 静态HTML
- Server-side Rendering 服务端渲染
- AJAX Technology AJAX技术

## Current Trends 当前趋势
- React/Vue/Angular 前端框架
- Cloud Computing 云计算
- Microservices 微服务

## Future Vision 未来愿景
- WebAssembly 
- Edge Computing 边缘计算
- AI-Powered Development AI驱动开发''',
        'processed_time': datetime.now().isoformat(),
        'original_file': 'tech_podcast_ep15.mp3',
        'podcast_series': 'Tech Talk Weekly',
        'episode_number': 'Episode 15',
        'host_name': 'John Host',
        'guest_names': ['Senior Developer A', 'Senior Developer B'],
        'audio_duration': '55 minutes',
        'classification_result': {
            'content_type': 'podcast',
            'confidence': 0.91,
            'auto_detected': True,
            'tags': ['web development', 'javascript', 'cloud computing', 'interview', 'technology']
        },
        'anonymized_names': {'Mike Johnson': 'Senior Developer A', 'Sarah Chen': 'Senior Developer B'}
    }
    
    return [youtube_content, lecture_content, rss_content, podcast_content]


def main():
    """主演示函数"""
    print("🚀 Phase 6 ContentFormatter 演示")
    print("=" * 60)
    
    # 创建配置和格式化器
    config_manager, temp_dir = create_test_config()
    formatter_config = {
        'site_title': 'Project Bach Phase 6',
        'site_description': '多媒体内容智能处理与分析',
        'theme': 'enhanced'
    }
    formatter = ContentFormatter(formatter_config, config_manager)
    
    try:
        # 获取示例内容
        sample_contents = create_sample_content_data()
        
        print(f"\n📊 处理 {len(sample_contents)} 个不同类型的多媒体内容：")
        print("   📺 YouTube视频")
        print("   🎓 学术讲座") 
        print("   📰 RSS文章")
        print("   🎙️ 播客内容")
        print("\n💡 特点：中英双语内容，以英文为主\n")
        
        formatted_results = []
        
        # 处理每个内容
        for i, content_data in enumerate(sample_contents, 1):
            print(f"🔄 处理第 {i} 个内容...")
            
            # 格式化内容
            result = formatter.format_content(content_data)
            
            if result['success']:
                content = result['content']
                content_type = content['content_type']
                type_icon = formatter.content_types_config.get(content_type, {}).get('icon', '📄')
                
                print(f"   ✅ {type_icon} {content['title'][:50]}...")
                print(f"      类型: {content_type}")
                print(f"      置信度: {content_data.get('classification_result', {}).get('confidence', 'N/A')}")
                print(f"      HTML长度: {len(content['html'])} 字符")
                print(f"      关键词数: {len(content['metadata']['keywords'])}")
                
                # 显示部分关键词
                keywords = content['metadata']['keywords'][:5]
                print(f"      示例关键词: {', '.join(keywords)}")
                
                formatted_results.append({
                    'title': content['title'],
                    'content_type': content_type,
                    'date': content_data['processed_time'][:10],
                    'file': f"content_{i}.html",
                    'summary': content_data['summary']
                })
                
            else:
                print(f"   ❌ 格式化失败: {result['error']}")
            
            print()
        
        # 创建站点索引
        print("🏠 创建增强的站点索引...")
        index_result = formatter.create_site_index(formatted_results)
        
        if index_result['success']:
            index_content = index_result['content']
            print(f"   ✅ 索引创建成功")
            print(f"      总内容数: {index_content['total_items']}")
            print(f"      内容类型数: {len(index_content['content_type_stats'])}")
            print(f"      索引HTML长度: {len(index_content['html'])} 字符")
            
            # 显示类型分布
            print("\n📊 内容类型分布:")
            for content_type, stats in index_content['content_type_stats'].items():
                icon = stats['icon']
                name = stats['display_name']
                count = stats['count']
                print(f"      {icon} {name}: {count} 个")
        
        print(f"\n🎉 Phase 6 ContentFormatter 演示完成！")
        print(f"✨ 成功展示了多媒体内容类型的专门格式化能力")
        print(f"🌐 支持中英双语（以英文为主）内容处理")
        print(f"🔧 包含类型特定的元数据提取和模板生成")
        
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)


if __name__ == '__main__':
    main()