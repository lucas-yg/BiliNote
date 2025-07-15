#!/bin/bash

# BiliNote 后端清理启动脚本
set -e

echo "🧹 清理 Python 缓存文件..."

# 清理 Python 字节码文件
echo "  - 清理 .pyc 文件..."
find . -name "*.pyc" -delete 2>/dev/null || true

# 清理 __pycache__ 目录
echo "  - 清理 __pycache__ 目录..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# 清理 .pytest_cache 目录（如果存在）
if [ -d ".pytest_cache" ]; then
    echo "  - 清理 pytest 缓存..."
    rm -rf .pytest_cache
fi

# 清理 note_results 目录中的旧文件（可选）
if [ -d "note_results" ]; then
    echo "  - 清理旧的笔记结果文件..."
    find note_results -name "*.json" -mtime +7 -delete 2>/dev/null || true
    find note_results -name "*.status.json" -mtime +7 -delete 2>/dev/null || true
fi

echo "✅ 清理完成！"
echo ""
echo "🚀 启动后端服务..."

# 检查并激活虚拟环境
if [ -d "backend/venv" ]; then
    echo "📦 激活虚拟环境 (backend/venv)..."
    source backend/venv/bin/activate
elif [ -d "venv" ]; then
    echo "📦 激活虚拟环境 (venv)..."
    source venv/bin/activate
else
    echo "⚠️  警告：未找到虚拟环境，使用系统 Python"
fi

# 显示Python版本信息
echo "🐍 Python 版本: $(python3 --version 2>/dev/null || python --version)"

# 启动服务
if command -v uvicorn > /dev/null; then
    echo "🌟 使用 uvicorn 启动服务 (http://localhost:8483)"
    echo "📚 API 文档地址: http://localhost:8483/docs"
    echo ""
    uvicorn main:app --host 0.0.0.0 --port 8483 --reload
else
    echo "❌ 错误：未找到 uvicorn，请确保已安装依赖"
    echo "💡 尝试运行: pip install uvicorn"
    exit 1
fi