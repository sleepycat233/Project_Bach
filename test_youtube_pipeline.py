#!/usr/bin/env python3.11
"""
测试YouTube完整处理流程脚本

功能：
1. 处理用户提供的YouTube视频（私有模式）
2. 使用字幕优先策略（字幕 → Whisper备用）
3. 生成AI摘要和思维导图
4. 创建包含视频嵌入的HTML页面
5. 保存到私有目录
"""

import sys
import logging
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'src'))

from src.core.dependency_container import DependencyContainer
from src.web_frontend.processors.youtube_processor import YouTubeProcessor
from src.utils.config import ConfigManager

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('data/logs/youtube_test.log')
        ]
    )

def main():
    """主函数"""
    setup_logging()
    logger = logging.getLogger('youtube_test')
    
    # 测试URL（用户提供的中文政治视频）
    test_url = "https://www.youtube.com/watch?v=j82i6BU05P8"
    
    logger.info("🚀 开始YouTube完整处理流程测试")
    logger.info(f"📺 测试视频: {test_url}")
    logger.info("🔒 隐私级别: Private (本地保存)")
    
    try:
        # 1. 初始化配置和依赖
        logger.info("步骤1: 初始化系统组件")
        config_manager = ConfigManager()
        container = DependencyContainer(config_manager)
        
        # 2. 初始化YouTube处理器
        logger.info("步骤2: 初始化YouTube处理器")
        youtube_processor = YouTubeProcessor(config_manager)
        
        # 3. 获取音频处理器
        audio_processor = container.get_audio_processor()
        
        # 4. 处理YouTube视频
        logger.info("步骤3: 下载和处理YouTube视频")
        youtube_result = youtube_processor.process_youtube_url(url=test_url)
        
        if not youtube_result.get('success'):
            logger.error(f"❌ YouTube处理失败: {youtube_result.get('error')}")
            return False
        
        logger.info("✅ YouTube处理成功")
        video_metadata = youtube_result.get('video_metadata', {})
        logger.info(f"📊 视频标题: {video_metadata.get('title', 'Unknown')}")
        logger.info(f"⏱️  视频时长: {video_metadata.get('duration_string', 'Unknown')}")
        logger.info(f"📝 转录方式: {youtube_result.get('transcription_method', 'Unknown')}")
        
        # 5. 完整内容处理（转录 → 匿名化 → AI生成）
        logger.info("步骤4: AI内容生成和HTML创建")
        success = audio_processor.process_youtube_content(
            youtube_result=youtube_result,
            privacy_level='private'
        )
        
        if success:
            logger.info("🎉 完整处理流程成功!")
            
            # 6. 显示结果位置
            video_id = video_metadata.get('video_id', 'unknown')
            private_html_path = f"data/output/private/youtube_{video_id}_result.html"
            
            logger.info("📄 生成的文件:")
            logger.info(f"   HTML页面: {private_html_path}")
            logger.info(f"   私有访问: http://100.x.x.x:8080/private/youtube_{video_id}_result.html")
            
            # 7. 验证文件是否存在
            if Path(private_html_path).exists():
                logger.info("✅ HTML文件创建成功")
                file_size = Path(private_html_path).stat().st_size
                logger.info(f"📊 文件大小: {file_size:,} bytes")
            else:
                logger.warning("⚠️  HTML文件未找到")
                
        else:
            logger.error("❌ 完整处理流程失败")
            return False
            
    except Exception as e:
        logger.error(f"💥 测试过程中发生异常: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return False
    
    logger.info("🏁 YouTube处理流程测试完成")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)