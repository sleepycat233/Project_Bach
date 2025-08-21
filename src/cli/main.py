#!/usr/bin/env python3.11
"""
Project Bach - 简化的主入口文件
支持批量处理和自动监控两种模式
"""

import os
import sys
import time
import signal
import argparse
import logging
from pathlib import Path
from typing import List, Dict

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core.dependency_container import DependencyContainer, ServiceFactory
from src.utils.config import ConfigManager


def check_dependencies() -> List[str]:
    """检查系统依赖
    
    Returns:
        依赖问题列表，如果为空则表示所有依赖都正常
    """
    issues = []
    
    # 检查spaCy模型
    try:
        import spacy
        nlp_zh = spacy.load("zh_core_web_sm")
        print("✅ spaCy中文模型已安装")
    except ImportError:
        issues.append("❌ spaCy未安装，请运行: pip install spacy")
    except OSError:
        issues.append("❌ spaCy中文模型未安装，请运行: python -m spacy download zh_core_web_sm")
    
    try:
        nlp_en = spacy.load("en_core_web_sm")
        print("✅ spaCy英文模型已安装")
    except OSError:
        issues.append("❌ spaCy英文模型未安装，请运行: python -m spacy download en_core_web_sm")
    
    # 检查其他必要依赖
    required_packages = [
        ('yaml', 'pyyaml'),
        ('requests', 'requests'),
        ('watchdog', 'watchdog'),
        ('faker', 'faker')
    ]
    
    for import_name, package_name in required_packages:
        try:
            __import__(import_name)
            print(f"✅ {package_name} 已安装")
        except ImportError:
            issues.append(f"❌ {package_name} 未安装，请运行: pip install {package_name}")
    
    return issues


def setup_test_environment(watch_folder: Path) -> List[str]:
    """设置测试环境
    
    Args:
        watch_folder: 监控文件夹路径
        
    Returns:
        创建的测试文件列表
    """
    print("设置测试环境...")
    
    test_files = [
        "test_meeting.mp3",
        "tech_lecture.wav", 
        "discussion.m4a"
    ]
    
    created_files = []
    
    for test_file in test_files:
        test_path = watch_folder / test_file
        if not test_path.exists():
            test_path.write_bytes(b'fake audio data for testing')
            created_files.append(test_file)
            print(f"创建测试文件: {test_file}")
    
    return created_files


def run_batch_mode(container: DependencyContainer) -> bool:
    """批量处理模式
    
    Args:
        container: 依赖容器
        
    Returns:
        是否全部处理成功
    """
    print("=== 批量处理模式 ===")
    
    config_manager = container.get_config_manager()
    watch_folder = Path(config_manager.get_paths_config()['watch_folder'])
    
    # 查找音频文件
    audio_extensions = ['*.mp3', '*.wav', '*.m4a', '*.flac', '*.aac', '*.ogg']
    audio_files = []
    for ext in audio_extensions:
        audio_files.extend(watch_folder.glob(ext))
    
    if not audio_files:
        print(f"在 {watch_folder} 中没有找到音频文件")
        created_files = setup_test_environment(watch_folder)
        if created_files:
            print("已创建测试文件，请重新运行程序")
        return True
    
    # 获取音频处理器
    processor = container.get_audio_processor()
    
    # 批量处理文件
    print(f"找到 {len(audio_files)} 个音频文件，开始处理...")
    print()
    
    results = {}
    for i, audio_file in enumerate(audio_files, 1):
        print(f"[{i}/{len(audio_files)}] 正在处理: {audio_file.name}")
        
        success = processor.process_audio_file(str(audio_file))
        results[str(audio_file)] = success
        
        if success:
            print(f"✅ 处理完成: {audio_file.name}")
        else:
            print(f"❌ 处理失败: {audio_file.name}")
        print()
    
    # 输出处理摘要
    success_count = sum(1 for success in results.values() if success)
    total_count = len(audio_files)
    
    print("=== 处理摘要 ===")
    print(f"总文件数: {total_count}")
    print(f"成功处理: {success_count}")
    print(f"失败数量: {total_count - success_count}")
    print(f"成功率: {success_count/total_count*100:.1f}%")
    print()
    
    # 显示输出路径
    output_folder = config_manager.get_paths_config()['output_folder']
    log_file = config_manager.get_logging_config()['file']
    print(f"结果保存在: {output_folder}")
    print(f"日志文件: {log_file}")
    
    return success_count == total_count


def run_monitor_mode(container: DependencyContainer):
    """文件监控模式
    
    Args:
        container: 依赖容器
    """
    print("=== 自动文件监控模式 ===")
    print("监控文件夹中的新音频文件，自动处理...")
    print("按 Ctrl+C 停止监控")
    print()
    
    # 获取完全配置的音频处理器（包含文件监控）
    processor = container.get_configured_audio_processor()
    
    # 设置信号处理器
    def signal_handler(signum, frame):
        print("\n正在停止文件监控...")
        processor.stop_file_monitoring()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 启动文件监控
    if not processor.start_file_monitoring():
        print("❌ 启动文件监控失败")
        return
    
    try:
        # 保持程序运行
        while True:
            time.sleep(5)
            
            # 显示队列状态
            status = processor.get_queue_status()
            if status.get("queue_stats", {}).get("processing") > 0:
                processing_files = status.get("processing_files", [])
                if processing_files:
                    file_names = [Path(f).name for f in processing_files]
                    print(f"正在处理: {', '.join(file_names)}")
            
    except KeyboardInterrupt:
        print("\n停止监控...")
        processor.stop_file_monitoring()


def validate_config_file(config_path: str) -> bool:
    """验证配置文件
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        配置是否有效
    """
    if not os.path.exists(config_path):
        print(f"❌ 错误: 找不到 {config_path} 配置文件")
        print("请先创建配置文件并填入API密钥")
        return False
    
    try:
        config_manager = ConfigManager(config_path)
        
        # 检查API密钥配置
        openrouter_config = config_manager.get_openrouter_config()
        api_key = openrouter_config.get('key', '')
        
        if api_key == 'YOUR_API_KEY_HERE' or not api_key:
            print("⚠️  警告: 请在 config.yaml 中配置真实的 OpenRouter API 密钥")
            print("当前将使用模拟模式运行...")
        else:
            print("✅ 配置文件验证通过")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置文件验证失败: {str(e)}")
        return False


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Project Bach - 音频处理系统')
    parser.add_argument('--mode', choices=['batch', 'monitor'], default='batch',
                       help='运行模式: batch=批量处理（默认），monitor=自动监控')
    parser.add_argument('--config', default='config.yaml',
                       help='配置文件路径（默认: config.yaml）')
    
    args = parser.parse_args()
    
    print("=== Project Bach - 音频处理系统 ===")
    print(f"运行模式: {'批量处理' if args.mode == 'batch' else '自动监控'}")
    print()
    
    # 检查依赖
    print("检查系统依赖...")
    issues = check_dependencies()
    if issues:
        print("依赖检查失败:")
        for issue in issues:
            print(f"  {issue}")
        print("\n请解决上述问题后重新运行")
        return False
    
    # 验证配置文件
    if not validate_config_file(args.config):
        return False
    
    try:
        # 创建依赖容器
        container = ServiceFactory.create_container_from_config_file(args.config)
        print("✅ 依赖容器初始化成功")
        
        # 验证依赖
        validation_results = container.validate_dependencies()
        failed_deps = [name for name, success in validation_results.items() if not success]
        
        if failed_deps:
            print(f"❌ 依赖验证失败: {', '.join(failed_deps)}")
            return False
        
        print("✅ 所有依赖验证通过")
        print()
        
        # 根据模式运行
        if args.mode == 'batch':
            return run_batch_mode(container)
        else:
            run_monitor_mode(container)
            return True
            
    except Exception as e:
        print(f"❌ 程序运行失败: {str(e)}")
        
        # 在调试模式下显示详细错误
        import logging
        logger = logging.getLogger('project_bach')
        if logger.isEnabledFor(logging.DEBUG):
            import traceback
            traceback.print_exc()
        
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)