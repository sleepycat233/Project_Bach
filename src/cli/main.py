#!/usr/bin/env python3.11
"""
Project Bach - 主入口文件
启动文件监控和Web服务器
"""

import os
import sys
import time
import signal
import argparse
import logging
import threading
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core.dependency_container import (
    DependencyContainer,
    ServiceFactory,
    set_global_container,
)
from src.utils.config import ConfigManager
from src.web_frontend.app import create_app
from src.network.tailscale_manager import TailscaleManager


def run_monitor_and_web_server(container: DependencyContainer):
    """运行文件监控和Web服务器

    Args:
        container: 依赖容器
    """
    print("=== Project Bach 服务器启动 ===")
    print("启动文件监控和Web服务器...")
    print("按 Ctrl+C 停止服务")
    print()

    # 获取配置
    config_manager = container.get_config_manager()
    if not config_manager:
        print("❌ 无法获取配置管理器")
        return

    # 检查Tailscale连接状态（可选）
    print("🔍 检查Tailscale网络连接...")
    tailscale_manager = TailscaleManager()

    if not tailscale_manager.check_tailscale_installed():
        print("⚠️  Tailscale未安装，跳过远程模式（可选功能）")
    else:
        status = tailscale_manager.check_status()
        if not status.get('connected', False):
            print("⚠️  Tailscale未连接，尝试自动连接...")
            if tailscale_manager.connect():
                print("✅ Tailscale连接成功")
                status = tailscale_manager.check_status()
            else:
                print("⚠️  自动连接失败，将继续以本地模式运行")
                print("   如需远程访问请手动执行: tailscale up")
                status = None
        else:
            print("✅ Tailscale已连接")

        if status and status.get('connected', False):
            tailscale_ips = status.get('tailscale_ips', [])
            ip_display = tailscale_ips[0] if tailscale_ips else '未知'
            print(f"   节点IP: {ip_display}")

            network_info = tailscale_manager.get_network_info()
            peers = network_info.get('peers', [])
            if peers:
                print(f"   已发现 {len(peers)} 个节点")
                for peer in peers[:3]:
                    host = peer.get('hostname') or peer.get('dns_name') or peer.get('id')
                    peer_ip = peer.get('tailscale_ips', [None])[0]
                    print(f"     • {host} ({peer_ip or '无IP'}) {'在线' if peer.get('online') else '离线'}")

                first_online_peer_ip = next(
                    (
                        p.get('tailscale_ips', [None])[0]
                        for p in peers
                        if p.get('online') and p.get('tailscale_ips')
                    ),
                    None,
                )
                if first_online_peer_ip:
                    latency = tailscale_manager.ping_peer(first_online_peer_ip)
                    if latency is not None:
                        print(f"   Ping {first_online_peer_ip}: {latency:.2f} ms")
                    else:
                        print(f"   Ping {first_online_peer_ip} 失败或超时")
                else:
                    print("   未找到在线节点，跳过Ping")

    print()

    # 获取完全配置的音频处理器（包含文件监控）
    processor = container.get_configured_audio_processor()

    # 创建Flask应用
    app = create_app()  # 不传递config_manager，让Flask应用自己创建

    # Web服务器配置
    web_config = (config_manager.config or {}).get('web_frontend', {}).get('app', {})
    host = web_config.get('host', '0.0.0.0')
    port = web_config.get('port', 8080)

    # 设置信号处理器
    def signal_handler(_signum, _frame):
        print("\n正在停止服务...")
        processor.stop_file_monitoring()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 启动文件监控
    if not processor.start_file_monitoring():
        print("❌ 启动文件监控失败")
        return

    print("✅ 文件监控已启动")

    # 在后台线程中启动Web服务器
    def run_web_server():
        print(f"🚀 启动Web服务器: http://{host}:{port}")
        print(f"🔒 私有内容: http://{host}:{port}/private/")
        print("⚠️  生产模式：需要Tailscale网络访问")
        app.run(host=host, port=port, debug=False, use_reloader=False)

    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    try:
        # 保持程序运行，显示状态
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
        print("\n停止服务...")
        processor.stop_file_monitoring()

def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Project Bach - 音频处理和Web服务器')
    parser.add_argument('--config', default='config.yaml',
                       help='配置文件路径（默认: config.yaml）')

    args = parser.parse_args()

    print("=== Project Bach - 音频处理和Web服务器 ===")
    print()

    try:
        # 创建依赖容器（自动处理所有依赖检查和验证）
        container = ServiceFactory.create_container_from_config_file(args.config)
        # 记录全局容器，供Flask应用在同一进程内复用依赖
        set_global_container(container)
        print("✅ 系统初始化成功")

        # 运行集成的监控和Web服务器
        run_monitor_and_web_server(container)
        return True

    except Exception as e:
        print(f"❌ 程序运行失败: {str(e)}")

        # 在调试模式下显示详细错误
        import logging
        logger = logging.getLogger('project_bach')
        if logger.isEnabledFor(logging.DEBUG):
            import traceback
            print("=== 详细错误信息 ===")
            traceback.print_exc()
            print("=== 错误信息结束 ===")

        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
