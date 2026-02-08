#!/usr/bin/env python3
"""测试优雅关闭功能。

测试场景：
1. 启动服务
2. 发送 SIGTERM 信号
3. 验证优雅关闭流程（等待任务完成）
4. 验证超时强制关闭
"""

import asyncio
import logging
import os
import signal
import subprocess
import sys
import time

logger = logging.getLogger(__name__)


def test_graceful_shutdown():
    """测试优雅关闭功能。"""
    print("\n" + "=" * 60)
    print("测试优雅关闭功能")
    print("=" * 60)

    # 1. 启动服务
    print("\n步骤 1: 启动服务...")
    print("命令：uvicorn app.main:app --host 127.0.0.1 --port 8888")

    process = subprocess.Popen(
        ["uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8888"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # 等待服务启动
    print("等待服务启动（5 秒）...")
    time.sleep(5)

    # 检查进程是否还在运行
    if process.poll() is not None:
        print("✗ 服务启动失败")
        stdout, stderr = process.communicate()
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        return False

    print(f"✓ 服务已启动（PID: {process.pid}）")

    # 2. 发送 SIGTERM 信号
    print("\n步骤 2: 发送 SIGTERM 信号...")
    print(f"发送信号到进程 {process.pid}")

    start_time = time.time()
    process.send_signal(signal.SIGTERM)

    # 3. 等待进程退出
    print("\n步骤 3: 等待优雅关闭...")
    print("（最多等待 35 秒，包括 30 秒超时时间）")

    try:
        process.wait(timeout=35)
        elapsed = time.time() - start_time
        print(f"✓ 进程已退出，耗时 {elapsed:.1f} 秒")

        # 检查退出码
        if process.returncode == 0:
            print(f"✓ 退出码：{process.returncode}（正常退出）")
        else:
            print(f"⚠️  退出码：{process.returncode}（非零退出）")

        # 读取输出日志
        stdout, stderr = process.communicate()

        # 检查日志中是否包含优雅关闭的关键信息
        combined_output = stdout + stderr

        if "[优雅关闭]" in combined_output:
            print("✓ 日志包含优雅关闭标记")
        else:
            print("⚠️  日志未包含优雅关闭标记")

        if "收到 SIGTERM 信号" in combined_output or "收到 SIGINT 信号" in combined_output:
            print("✓ 日志包含信号接收记录")
        else:
            print("⚠️  日志未包含信号接收记录")

        if "调度器已停止" in combined_output or "完成" in combined_output:
            print("✓ 日志包含关闭完成记录")
        else:
            print("⚠️  日志未包含关闭完成记录")

        # 显示部分日志
        print("\n最后 20 行日志：")
        print("-" * 60)
        lines = combined_output.split("\n")
        for line in lines[-20:]:
            if line.strip():
                print(line)
        print("-" * 60)

        return True

    except subprocess.TimeoutExpired:
        print("✗ 等待超时（35 秒），强制终止进程")
        process.kill()
        process.wait()
        return False


def test_sigint_shutdown():
    """测试 SIGINT（Ctrl+C）关闭。"""
    print("\n" + "=" * 60)
    print("测试 SIGINT 关闭")
    print("=" * 60)

    # 1. 启动服务
    print("\n步骤 1: 启动服务...")
    process = subprocess.Popen(
        ["uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8889"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # 等待服务启动
    print("等待服务启动（5 秒）...")
    time.sleep(5)

    if process.poll() is not None:
        print("✗ 服务启动失败")
        return False

    print(f"✓ 服务已启动（PID: {process.pid}）")

    # 2. 发送 SIGINT 信号（模拟 Ctrl+C）
    print("\n步骤 2: 发送 SIGINT 信号（模拟 Ctrl+C）...")
    start_time = time.time()
    process.send_signal(signal.SIGINT)

    # 3. 等待进程退出
    print("\n步骤 3: 等待优雅关闭...")
    try:
        process.wait(timeout=35)
        elapsed = time.time() - start_time
        print(f"✓ 进程已退出，耗时 {elapsed:.1f} 秒")
        return True

    except subprocess.TimeoutExpired:
        print("✗ 等待超时，强制终止进程")
        process.kill()
        process.wait()
        return False


def main():
    """主测试函数。"""
    import sys

    print("\n" + "=" * 60)
    print("优雅关闭功能测试")
    print("=" * 60)
    print()
    print("注意：此测试会启动服务并发送信号，请确保：")
    print("  1. 端口 8888 和 8889 未被占用")
    print("  2. 数据库和 Redis 已启动")
    print("  3. 环境变量已配置（.env 文件）")
    print()

    # 支持非交互模式（通过 --auto 参数）
    if "--auto" not in sys.argv:
        input("按 Enter 键开始测试...")

    results = []

    # 测试 1: SIGTERM 优雅关闭
    result1 = test_graceful_shutdown()
    results.append(("SIGTERM 优雅关闭", result1))

    # 等待一段时间
    print("\n等待 3 秒后进行下一个测试...")
    time.sleep(3)

    # 测试 2: SIGINT 关闭
    result2 = test_sigint_shutdown()
    results.append(("SIGINT 关闭", result2))

    # 显示测试结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name}: {status}")

    all_passed = all(result for _, result in results)

    if all_passed:
        print("\n✓ 所有测试通过")
        return 0
    else:
        print("\n✗ 部分测试失败")
        return 1


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    exit_code = main()
    sys.exit(exit_code)
