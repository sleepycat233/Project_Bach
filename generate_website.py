#!/usr/bin/env python3.11
"""
生成完整的GitHub Pages网站到public/文件夹
"""

import sys
import shutil
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.config import ConfigManager
from src.publishing.publishing_workflow import PublishingWorkflow
from src.publishing.template_engine import TemplateEngine

def main():
    """生成完整网站"""
    print("🌐 生成完整GitHub Pages网站")
    
    # 加载配置
    config_manager = ConfigManager()
    config = config_manager.get_full_config()
    
    # 创建public目录
    public_dir = project_root / 'public'
    if public_dir.exists():
        print(f"🗑️  清理旧的public目录: {public_dir}")
        shutil.rmtree(public_dir)
    
    public_dir.mkdir()
    print(f"📁 创建新的public目录: {public_dir}")
    
    # 复制静态资源
    static_dir = project_root / 'static'
    if static_dir.exists():
        static_target = public_dir / 'static'
        shutil.copytree(static_dir, static_target)
        print(f"📋 复制静态资源: {static_dir} -> {static_target}")
    
    # 初始化模板引擎
    template_engine = TemplateEngine(config.get('publishing', {}))
    
    # 读取处理结果
    output_path = Path(config.get('paths', {}).get('output_folder', './data/output'))
    public_output_path = output_path / 'public'
    
    if not public_output_path.exists():
        print(f"❌ 没有找到public输出文件夹: {public_output_path}")
        return False
        
    # 获取所有结果文件
    result_files = list(public_output_path.glob('*.html'))
    print(f"📄 找到 {len(result_files)} 个HTML结果文件")
    
    # 复制结果文件到public
    for result_file in result_files:
        target_file = public_dir / result_file.name
        shutil.copy2(result_file, target_file)
        print(f"   📋 {result_file.name}")
    
    # 生成index.html
    try:
        # 创建结果元数据
        result_metadata = []
        for result_file in result_files:
            # 解析文件名获取基本信息
            filename = result_file.stem
            parts = filename.split('_')
            if len(parts) >= 4:
                timestamp = parts[0] + '_' + parts[1]
                content_type = parts[2] 
                title = '_'.join(parts[3:])
            else:
                timestamp = "Unknown"
                content_type = "unknown"
                title = filename
                
            result_metadata.append({
                'title': title,
                'timestamp': timestamp,
                'type': content_type.lower(),
                'filename': result_file.name,
                'url': result_file.name
            })
        
        # 生成统计信息
        stats = {
            'total_processed': len(result_metadata),
            'this_month': len(result_metadata),
            'languages_supported': 2
        }
        
        # 使用模板引擎生成首页
        index_result = template_engine.render_index_page(result_metadata, stats)
        if index_result['success']:
            index_path = public_dir / 'index.html'
            index_path.write_text(index_result['content'], encoding='utf-8')
            print(f"✅ 生成index.html: {index_path}")
        else:
            print(f"❌ 模板渲染失败: {index_result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ 生成index.html失败: {e}")
        return False
    
    # 验证生成的网站
    print(f"\n📊 网站生成完成:")
    print(f"   📁 目录: {public_dir}")
    print(f"   📄 文件数量: {len(list(public_dir.rglob('*')))}")
    
    if (public_dir / 'index.html').exists():
        print(f"   ✅ 主页: index.html")
    if (public_dir / 'static').exists():
        css_files = len(list((public_dir / 'static').rglob('*.css')))
        js_files = len(list((public_dir / 'static').rglob('*.js')))
        print(f"   ✅ 静态资源: {css_files} CSS + {js_files} JS")
        
    print(f"   ✅ 结果页面: {len(result_files)} HTML文件")
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)