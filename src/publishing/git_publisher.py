#!/usr/bin/env python3.11
"""
简化Git发布服务
负责将处理结果自动推送到GitHub Pages
"""

import os
import subprocess
import logging
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from .template_engine import TemplateEngine


class GitPublisher:
    """简化的Git发布服务"""
    
    def __init__(self, config_manager=None):
        """初始化Git发布服务"""
        self.config_manager = config_manager
        self.logger = logging.getLogger('project_bach.git_publisher')
        
        # 基础路径配置
        self.project_root = Path.cwd()
        self.public_dir = self.project_root / "public"
        self.output_dir = self.project_root / "data" / "output"
        self.output_public_dir = self.output_dir / "public"
        
        # 初始化模板引擎
        if config_manager:
            template_config = config_manager.get_nested_config('publishing.template_engine', {})
            if not template_config:  # 如果配置为空，提供默认配置
                template_config = {'template_dir': './templates'}
            self.template_engine = TemplateEngine(template_config)
        else:
            self.template_engine = TemplateEngine({'template_dir': './templates'})
        
        self.logger.info("Git发布服务初始化完成")
    
    def publish_result(self, result_filename: str, privacy_level: str = 'public') -> bool:
        """发布单个处理结果到GitHub Pages
        
        Args:
            result_filename: 结果文件名 (不含路径)
            privacy_level: 隐私级别 ('public' 或 'private')
            
        Returns:
            是否发布成功
        """
        try:
            self.logger.info(f"开始发布结果文件: {result_filename}")
            
            # 只处理public内容
            if privacy_level != 'public':
                self.logger.info(f"跳过private内容: {result_filename}")
                return True
            
            # 确保public目录存在
            self.public_dir.mkdir(exist_ok=True)
            
            # 查找结果文件，优先在public子目录查找
            source_file = self.output_public_dir / result_filename
            if not source_file.exists():
                # 尝试在根output目录查找
                source_file = self.output_dir / result_filename
                if not source_file.exists():
                    # 尝试添加.html后缀
                    source_file = self.output_public_dir / f"{result_filename}.html"
                    if not source_file.exists():
                        source_file = self.output_dir / f"{result_filename}.html"
                        if not source_file.exists():
                            self.logger.error(f"结果文件不存在: {result_filename}")
                            return False
            
            # 复制文件到public目录
            target_file = self.public_dir / source_file.name
            shutil.copy2(source_file, target_file)
            self.logger.info(f"文件已复制到public目录: {target_file.name}")
            
            # 更新index.html
            self._update_index_html()
            
            # 执行git操作
            success = self._git_commit_and_push(source_file.name)
            
            if success:
                self.logger.info(f"结果文件发布成功: {result_filename}")
            else:
                self.logger.error(f"Git推送失败: {result_filename}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"发布结果文件失败: {result_filename}, 错误: {str(e)}")
            return False
    
    def _update_index_html(self):
        """使用模板引擎更新public/index.html文件，支持分类统计"""
        try:
            # 扫描public目录中的所有HTML文件
            html_files = list(self.public_dir.glob("*.html"))
            html_files = [f for f in html_files if f.name != "index.html"]
            
            # 按修改时间排序（最新的在前）
            html_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            # 分类统计
            video_count = 0
            lecture_count = 0
            article_count = 0
            podcast_count = 0
            
            # 准备文件列表数据和分类统计
            files_data = []
            recent_content = []
            
            for html_file in html_files:
                file_stat = html_file.stat()
                mod_time = datetime.fromtimestamp(file_stat.st_mtime)
                
                # 根据文件名判断内容类型
                content_type = 'content'
                if html_file.name.startswith('youtube_'):
                    content_type = 'video'
                    video_count += 1
                elif '_LEC_' in html_file.name or 'lecture' in html_file.name.lower():
                    content_type = 'lecture'
                    lecture_count += 1
                elif '_ART_' in html_file.name or 'article' in html_file.name.lower():
                    content_type = 'article'
                    article_count += 1
                elif '_POD_' in html_file.name or 'podcast' in html_file.name.lower():
                    content_type = 'podcast'
                    podcast_count += 1
                else:
                    # 默认分类为lecture
                    content_type = 'lecture'
                    lecture_count += 1
                
                # 生成更好的标题
                title = html_file.stem.replace('_result', '')
                if title.startswith('youtube_'):
                    title = title.replace('youtube_', '').replace('_', ' ').title()
                else:
                    title = title.replace('_', ' ').title()
                
                file_data = {
                    'filename': html_file.name,
                    'title': title,
                    'url': f"./{html_file.name}",
                    'processed_time': mod_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'timestamp': mod_time.isoformat(),
                    'content_type': content_type,
                    'created_at': mod_time.isoformat()
                }
                
                files_data.append(file_data)
                recent_content.append(file_data)
            
            # 限制最近内容显示数量
            recent_content = recent_content[:10]
            
            # 准备模板上下文 - 使用GitHub Pages模板需要的格式
            template_context = {
                'title': 'Project Bach - Content Analysis Hub',
                'description': f'共收录{len(files_data)}个处理结果',
                'lecture_count': lecture_count,
                'video_count': video_count,
                'article_count': article_count,
                'podcast_count': podcast_count,
                'recent_content': recent_content,
                'total_processed': len(files_data),
                'total_this_month': len([f for f in files_data if (datetime.now() - datetime.fromisoformat(f['created_at'].replace('Z', '+00:00').replace('+00:00', ''))).days < 30]),
                'avg_processing_time': '2m',
                'languages_supported': 2,
                'results': files_data,
                'stats': {
                    'total_files': len(files_data),
                    'updated_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            }
            
            # 尝试使用GitHub Pages模板
            try:
                render_result = self.template_engine.render_template('github_pages/index.html', template_context)
            except Exception as e:
                self.logger.warning(f"GitHub Pages模板不可用，使用简单模板: {str(e)}")
                render_result = self.template_engine.render_index_page(files_data, template_context.get('stats', {}))
            
            if render_result.get('success'):
                index_content = render_result['content']
            else:
                self.logger.error(f"模板引擎渲染失败: {render_result.get('error', 'Unknown error')}")
                raise Exception("模板引擎渲染失败")
            
            # 写入index.html
            index_file = self.public_dir / "index.html"
            index_file.write_text(index_content, encoding='utf-8')
            self.logger.info(f"已更新public/index.html，统计: Videos={video_count}, Lectures={lecture_count}")
            
        except Exception as e:
            self.logger.error(f"使用模板引擎更新index.html失败: {str(e)}")
            # 如果模板引擎失败，回退到简单HTML
            self._fallback_update_index_html()
    
    def _fallback_update_index_html(self):
        """回退方案：生成简单的index.html"""
        try:
            html_files = list(self.public_dir.glob("*.html"))
            html_files = [f for f in html_files if f.name != "index.html"]
            html_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            # 生成最简单的index页面
            index_content = f"""<!DOCTYPE html>
<html><head><title>Project Bach</title></head>
<body><h1>Project Bach Results</h1><ul>
"""
            for html_file in html_files:
                index_content += f"""<li><a href="./{html_file.name}">{html_file.stem}</a></li>
"""
            index_content += f"""</ul><p><em>Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</em></p></body></html>"""
            
            index_file = self.public_dir / "index.html"
            index_file.write_text(index_content, encoding='utf-8')
            self.logger.info("已使用fallback方式更新index.html")
            
        except Exception as e:
            self.logger.error(f"Fallback更新index.html也失败: {str(e)}")
    
    def _git_commit_and_push(self, filename: str) -> bool:
        """执行git commit和push操作
        
        Args:
            filename: 新增的文件名
            
        Returns:
            是否成功
        """
        try:
            # 切换到项目根目录
            os.chdir(self.project_root)
            
            # git add public/
            result = subprocess.run(
                ['git', 'add', 'public/'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                self.logger.error(f"git add失败: {result.stderr}")
                return False
            
            # 检查是否有变更
            result = subprocess.run(
                ['git', 'diff', '--cached', '--quiet'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                self.logger.info("没有变更需要提交")
                return True
            
            # git commit
            commit_message = f"🤖 Auto-publish: {filename} ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"
            result = subprocess.run(
                ['git', 'commit', '-m', commit_message],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                self.logger.error(f"git commit失败: {result.stderr}")
                return False
            
            self.logger.info(f"Git commit成功: {commit_message}")
            
            # git push
            result = subprocess.run(
                ['git', 'push', 'origin', 'main'],
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode != 0:
                self.logger.error(f"git push失败: {result.stderr}")
                return False
            
            self.logger.info("Git push成功，GitHub Actions将自动部署")
            return True
            
        except subprocess.TimeoutExpired:
            self.logger.error("Git操作超时")
            return False
        except Exception as e:
            self.logger.error(f"Git操作异常: {str(e)}")
            return False
    
    def check_git_status(self) -> Dict[str, Any]:
        """检查Git仓库状态
        
        Returns:
            Git状态信息
        """
        try:
            os.chdir(self.project_root)
            
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'has_changes': bool(result.stdout.strip()),
                    'changes': result.stdout.strip().split('\n') if result.stdout.strip() else []
                }
            else:
                return {
                    'success': False,
                    'error': result.stderr
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


def create_git_publisher(config_manager=None) -> GitPublisher:
    """创建Git发布服务实例
    
    Args:
        config_manager: 配置管理器
        
    Returns:
        Git发布服务实例
    """
    return GitPublisher(config_manager)