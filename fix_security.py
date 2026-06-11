#!/usr/bin/env python3
"""
波胆教父 - 安全修复入口脚本
运行 web_app/fix_security.py 中的安全修复
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_app'))

if __name__ == "__main__":
    from fix_security import main
    main()
