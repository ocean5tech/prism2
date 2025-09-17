#!/usr/bin/env python3
"""
在虚拟环境中测试真实数据管道
"""

import subprocess
import sys
import os

def test_real_pipeline():
    """在虚拟环境中运行真实数据收集测试"""
    print("🚀 启动真实数据管道测试")
    print("=" * 60)

    # 确保我们在正确的目录
    os.chdir('/home/wyatt/prism2/rag-service')

    # 检查虚拟环境
    venv_python = './venv/bin/python'
    if not os.path.exists(venv_python):
        print("❌ 虚拟环境不存在，请先创建虚拟环境")
        return False

    try:
        # 在虚拟环境中运行真实数据收集
        print("📊 在虚拟环境中执行真实数据收集...")
        result = subprocess.run([
            venv_python,
            'real_data_collector.py'
        ], capture_output=True, text=True, timeout=300)

        print("标准输出:")
        print(result.stdout)

        if result.stderr:
            print("错误输出:")
            print(result.stderr)

        if result.returncode == 0:
            print("✅ 真实数据管道测试成功")
            return True
        else:
            print(f"❌ 真实数据管道测试失败，返回码: {result.returncode}")
            return False

    except subprocess.TimeoutExpired:
        print("⏰ 测试超时 (5分钟)")
        return False
    except Exception as e:
        print(f"❌ 测试执行失败: {e}")
        return False

if __name__ == "__main__":
    success = test_real_pipeline()
    if success:
        print("\n🎉 真实数据管道测试完成")
    else:
        print("\n❌ 真实数据管道测试失败")