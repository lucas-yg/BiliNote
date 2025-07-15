#!/bin/bash

# BiliNote 简易启动脚本
# 使用 pnpm 直接启动前后端服务，无需 Docker

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查参数
if [[ "$1" == "--frontend" ]]; then
    print_status "启动前端开发服务器..."
    cd BillNote_frontend
    
    # 检查 pnpm 是否安装
    if ! command -v pnpm &> /dev/null; then
        print_error "未找到 pnpm，请先安装: npm install -g pnpm"
        exit 1
    fi
    
    # 安装依赖（如果需要）
    if [ ! -d "node_modules" ]; then
        print_status "安装前端依赖..."
        pnpm install
    fi
    
    print_success "启动前端开发服务器..."
    pnpm run dev
    
elif [[ "$1" == "--backend" ]]; then
    print_status "启动后端服务..."
    cd backend
    
    # 检查 Python 环境
    if ! command -v python3 &> /dev/null; then
        print_error "未找到 Python3，请先安装"
        exit 1
    fi
    
    # 安装依赖（如果需要）
    if [ ! -d "venv" ]; then
        print_status "创建虚拟环境..."
        python3 -m venv venv
    fi
    
    source venv/bin/activate
    
    if [ ! -f "venv/installed" ]; then
        print_status "安装后端依赖..."
        pip install -r requirements.txt
        touch venv/installed
    fi
    
    print_success "启动后端服务..."
    python main.py
    
elif [[ "$1" == "--all" ]]; then
    print_status "启动前后端服务..."
    
    # 启动后端（后台）
    print_status "启动后端服务..."
    cd backend
    source venv/bin/activate 2>/dev/null || python3 -m venv venv && source venv/bin/activate
    pip install -r requirements.txt 2>/dev/null || true
    nohup python main.py > backend.log 2>&1 &
    BACKEND_PID=$!
    cd ..
    
    # 启动前端
    print_status "启动前端服务..."
    cd BillNote_frontend
    pnpm install 2>/dev/null || true
    pnpm run dev
    
    # 清理后台进程
    trap "kill $BACKEND_PID 2>/dev/null || true" EXIT
    
else
    echo "使用方法："
    echo "  ./start-simple.sh --frontend    # 启动前端开发服务器"
    echo "  ./start-simple.sh --backend     # 启动后端服务"
    echo "  ./start-simple.sh --all         # 启动前后端服务"
    echo ""
    echo "访问地址："
    echo "  前端: http://localhost:5173"
    echo "  后端: http://localhost:8483"
fi