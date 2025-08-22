#!/usr/bin/env python3
"""
Phase 6 测试运行器

提供便捷的命令来运行不同类型的测试
"""

import pytest
import sys
from pathlib import Path

def run_unit_tests():
    """运行单元测试"""
    print("🧪 Running Phase 6 Unit Tests...")
    test_dir = Path(__file__).parent / "unit"
    
    args = [
        str(test_dir),
        "-v",
        "--tb=short",
        "--durations=10",
        "-x"  # 遇到第一个失败就停止
    ]
    
    return pytest.main(args)

def run_integration_tests():
    """运行集成测试"""
    print("🔗 Running Phase 6 Integration Tests...")
    test_dir = Path(__file__).parent / "integration"
    
    args = [
        str(test_dir),
        "-v",
        "--tb=short",
        "--durations=10"
    ]
    
    return pytest.main(args)

def run_all_tests():
    """运行所有Phase 6测试"""
    print("🚀 Running All Phase 6 Tests...")
    test_dirs = [
        str(Path(__file__).parent / "unit"),
        str(Path(__file__).parent / "integration")
    ]
    
    args = test_dirs + [
        "-v",
        "--tb=short",
        "--durations=15",
        "--cov=src",
        "--cov-report=term-missing"
    ]
    
    return pytest.main(args)

def run_specific_component(component_name):
    """运行特定组件的测试"""
    print(f"🎯 Running {component_name} Tests...")
    
    component_files = {
        'classifier': 'unit/test_content_classifier.py',
        'youtube': 'unit/test_youtube_processor.py', 
        'rss': 'unit/test_rss_processor.py',
        'flask': 'unit/test_flask_web_app.py',
        'integration': 'integration/test_phase6_integration.py'
    }
    
    if component_name not in component_files:
        print(f"❌ Unknown component: {component_name}")
        print(f"Available components: {', '.join(component_files.keys())}")
        return 1
    
    test_file = Path(__file__).parent / component_files[component_name]
    
    args = [
        str(test_file),
        "-v",
        "--tb=short"
    ]
    
    return pytest.main(args)

if __name__ == "__main__":
    """
    用法示例:
    python test_runner_phase6.py unit          # 运行单元测试
    python test_runner_phase6.py integration   # 运行集成测试
    python test_runner_phase6.py all           # 运行所有测试
    python test_runner_phase6.py classifier    # 运行分类器测试
    python test_runner_phase6.py youtube       # 运行YouTube处理器测试
    python test_runner_phase6.py rss           # 运行RSS处理器测试
    python test_runner_phase6.py flask         # 运行Flask Web应用测试
    """
    
    if len(sys.argv) < 2:
        print("Usage: python test_runner_phase6.py <test_type>")
        print("Test types: unit, integration, all, classifier, youtube, rss, flask")
        sys.exit(1)
    
    test_type = sys.argv[1].lower()
    
    if test_type == "unit":
        exit_code = run_unit_tests()
    elif test_type == "integration":
        exit_code = run_integration_tests()
    elif test_type == "all":
        exit_code = run_all_tests()
    elif test_type in ["classifier", "youtube", "rss", "flask"]:
        exit_code = run_specific_component(test_type)
    else:
        print(f"❌ Unknown test type: {test_type}")
        print("Available types: unit, integration, all, classifier, youtube, rss, flask")
        exit_code = 1
    
    sys.exit(exit_code)