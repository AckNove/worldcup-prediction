#!/usr/bin/env python3
"""
波胆教父 - 生产环境启动脚本
用于生产环境部署
"""
import os
import sys
import subprocess


def main():
    print("=" * 60)
    print("波胆教父 · 2026世界杯AI量化预测系统")
    print("生产环境启动")
    print("=" * 60)
    print()

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000

    print(f"[检查] Python 版本: {sys.version}")
    print(f"[检查] 工作目录: {os.getcwd()}")
    print(f"[检查] 监听端口: {port}")
    print()

    server_script = os.path.join(os.path.dirname(__file__), 'server.py')
    if not os.path.exists(server_script):
        print(f"[错误] 未找到 server.py: {server_script}")
        return 1

    print(f"[启动] 正在启动服务器...")
    print(f"[访问] http://localhost:{port}/")
    print()
    print("=" * 60)
    print("服务器日志:")
    print("=" * 60)

    try:
        subprocess.run([sys.executable, server_script, str(port)])
    except KeyboardInterrupt:
        print()
        print("=" * 60)
        print("[停止] 服务器已停止")
        print("=" * 60)
        return 0
    except Exception as e:
        print(f"[错误] {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
