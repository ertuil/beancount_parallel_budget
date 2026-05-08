#!/bin/bash
# 运行示例账本
# 从仓库根目录执行: ./examples/run.sh

set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$DIR")"
export PYTHONPATH="$ROOT:$PYTHONPATH"
exec bean-report "$DIR/main.beancount"