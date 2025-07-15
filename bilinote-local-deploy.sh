#!/bin/bash

# BiliNote 本地部署脚本 (不使用容器)
# 功能: 同步最新代码 -> 安装依赖 -> 本地启动

set -e  # 遇到错误就退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        log_error "$1 命令未找到，请安装后重试"
        exit 1
    fi
}

# 检查Python和虚拟环境
check_python() {
    log_info "检查Python环境..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装，请先安装Python3"
        exit 1
    fi
    
    log_success "Python3 检查通过"
}

# 同步代码
sync_code() {
    log_info "同步最新代码..."
    
    if [ -d ".git" ]; then
        git pull origin master
        log_success "代码同步完成"
    else
        log_warn "当前目录不是git仓库，跳过代码同步"
    fi
}

# 安装后端依赖
install_backend_deps() {
    log_info "安装后端依赖..."
    
    cd backend
    
    # 创建虚拟环境
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        log_success "虚拟环境创建完成"
    fi
    
    # 激活虚拟环境并安装依赖
    source venv/bin/activate
    pip install -r requirements.txt
    log_success "后端依赖安装完成"
    
    cd ..
}

# 安装前端依赖
install_frontend_deps() {
    log_info "安装前端依赖..."
    
    if [ -d "frontend" ]; then
        cd frontend
        
        if command -v npm &> /dev/null; then
            npm install
            log_success "前端依赖安装完成"
        elif command -v yarn &> /dev/null; then
            yarn install
            log_success "前端依赖安装完成"
        else
            log_warn "npm/yarn 未找到，跳过前端依赖安装"
        fi
        
        cd ..
    else
        log_warn "前端目录不存在，跳过前端依赖安装"
    fi
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    # 启动后端
    cd backend
    source venv/bin/activate
    
    log_info "启动后端服务器..."
    uvicorn main:app --host 0.0.0.0 --port 8483 --reload &
    backend_pid=$!
    
    cd ..
    
    # 启动前端 (如果存在)
    if [ -d "frontend" ] && command -v npm &> /dev/null; then
        cd frontend
        log_info "启动前端开发服务器..."
        npm run dev &
        frontend_pid=$!
        cd ..
    fi
    
    log_success "服务启动完成!"
    log_info "后端地址: http://localhost:8483"
    
    if [ ! -z "$frontend_pid" ]; then
        log_info "前端地址: http://localhost:3000 (或查看终端输出)"
    fi
    
    log_info "按 Ctrl+C 停止服务"
    
    # 等待中断信号
    trap 'kill $backend_pid 2>/dev/null; [ ! -z "$frontend_pid" ] && kill $frontend_pid 2>/dev/null; exit' INT
    wait
}

# 主函数
main() {
    echo "🚀 BiliNote 本地部署脚本"
    echo "================================"
    
    check_python
    sync_code
    install_backend_deps
    install_frontend_deps
    start_services
}

# 执行
main "$@"