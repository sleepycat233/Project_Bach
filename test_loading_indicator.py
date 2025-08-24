#!/usr/bin/env python3
"""
手动测试YouTube加载指示器功能
"""

import time
import webbrowser
import requests

def test_loading_indicator():
    """手动测试加载指示器功能"""
    
    print("🎯 YouTube加载指示器功能测试")
    print("=" * 50)
    
    # 检查Web服务器是否运行
    try:
        response = requests.get("http://localhost:8080", timeout=5)
        if response.status_code == 200:
            print("✅ Web服务器运行正常")
        else:
            print(f"⚠️ Web服务器响应异常: {response.status_code}")
    except Exception as e:
        print(f"❌ Web服务器无法连接: {e}")
        return False
    
    # 测试YouTube API端点
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    try:
        api_response = requests.get(
            f"http://localhost:8080/api/youtube/metadata?url={test_url}", 
            timeout=10
        )
        if api_response.status_code == 200:
            data = api_response.json()
            print(f"✅ YouTube API正常工作，获取到标题: {data.get('title', 'N/A')}")
        else:
            print(f"⚠️ YouTube API响应异常: {api_response.status_code}")
    except Exception as e:
        print(f"❌ YouTube API测试失败: {e}")
        return False
    
    print("\n🌐 打开浏览器进行手动测试...")
    print("请按照以下步骤测试加载指示器功能:")
    print()
    print("1️⃣ 点击'📺 YouTube Video'标签")
    print("2️⃣ 在YouTube URL输入框中输入: https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    print("3️⃣ 观察输入框右侧是否出现旋转的加载指示器")
    print("4️⃣ 等待约2-8秒，观察是否变成绿色✓成功图标")
    print("5️⃣ 清空输入框，重新输入YouTube URL")
    print("6️⃣ 在加载过程中点击红色✕取消按钮测试取消功能")
    print()
    print("📱 预期行为:")
    print("   • 输入有效YouTube URL后800ms自动开始加载")
    print("   • 显示旋转的蓝色圆圈加载指示器")
    print("   • 同时显示红色✕取消按钮")
    print("   • 成功后显示绿色✓图标3秒后自动隐藏")
    print("   • 错误时显示红色✕图标5秒后自动隐藏")
    print("   • 点击取消按钮立即隐藏加载指示器")
    print()
    
    # 在默认浏览器中打开
    webbrowser.open("http://localhost:8080")
    
    input("👆 请在浏览器中测试完毕后按Enter键继续...")
    
    print("\n✅ 手动测试完成!")
    return True

if __name__ == "__main__":
    test_loading_indicator()