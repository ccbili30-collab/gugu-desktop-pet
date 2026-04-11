#!/bin/bash
# 咕咕桌宠 macOS 启动脚本
# 双击即可运行，或通过终端执行：bash start_mac.command

set -e

# 进入脚本所在目录（项目根）
cd "$(dirname "$0")"

# 优先用 python3，找不到则报错
if ! command -v python3 &>/dev/null; then
    osascript -e 'display alert "找不到 python3，请先安装 Python 3.10+" as critical'
    exit 1
fi

# 激活虚拟环境（如果存在）
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "[start_mac] 启动咕咕桌宠..."
python3 app/launcher_mac.py
