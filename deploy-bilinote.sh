#!/bin/bash

# BiliNote Docker 部署脚本
# 自动配置环境并部署前后端服务

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

print_header() {
    echo -e "${PURPLE}"
    echo "╔════════════════════════════════════════╗"
    echo "║        BiliNote 一键部署脚本           ║"
    echo "║     自动配置 Docker 环境并启动服务     ║"
    echo "╚════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 Colima 状态
check_colima() {
    print_status "检查 Colima 状态..."
    
    if ! command -v colima > /dev/null; then
        print_error "未找到 Colima，请先安装 Colima"
        echo "安装命令: brew install colima"
        exit 1
    fi
    
    if ! colima status > /dev/null 2>&1; then
        print_warning "Colima 未运行，正在启动..."
        colima start
        sleep 5
    fi
    
    print_success "Colima 运行正常"
}

# 配置 Docker 环境
setup_docker_env() {
    print_status "配置 Docker 环境变量..."
    
    # 清除可能的 Podman 环境变量
    unset DOCKER_HOST 2>/dev/null || true
    
    # 设置 Colima Docker socket
    export DOCKER_HOST="unix:///Users/$(whoami)/.colima/default/docker.sock"
    
    # 测试 Docker 连接
    if ! DOCKER_HOST="$DOCKER_HOST" /usr/local/bin/docker ps > /dev/null 2>&1; then
        print_error "无法连接到 Docker daemon"
        exit 1
    fi
    
    print_success "Docker 环境配置完成"
}

# 拉取必要的镜像
pull_images() {
    print_status "拉取必要的 Docker 镜像..."
    
    local images=(
        "docker.m.daocloud.io/library/nginx:1.25-alpine"
        "docker.m.daocloud.io/library/python:3.11-slim"
        "docker.m.daocloud.io/library/node:18-alpine"
    )
    
    for image in "${images[@]}"; do
        print_status "拉取镜像: $image"
        if DOCKER_HOST="$DOCKER_HOST" /usr/local/bin/docker pull "$image"; then
            # 给镜像打标签为官方名称
            local official_name="${image#docker.m.daocloud.io/library/}"
            DOCKER_HOST="$DOCKER_HOST" /usr/local/bin/docker tag "$image" "$official_name"
            print_success "镜像拉取成功: $official_name"
        else
            print_warning "镜像拉取失败: $image，尝试使用官方镜像源"
        fi
    done
}

# 清理现有容器
cleanup_containers() {
    print_status "清理现有容器..."
    
    # 停止并删除现有容器
    DOCKER_HOST="$DOCKER_HOST" /usr/local/bin/docker-compose down --remove-orphans 2>/dev/null || true
    
    # 删除临时容器
    DOCKER_HOST="$DOCKER_HOST" /usr/local/bin/docker rm -f bilinote-backend-temp 2>/dev/null || true
    
    print_success "容器清理完成"
}

build_frontend() {
    print_status "开始构建前端..."
    cd BillNote_frontend
    
    # 使用 pnpm 安装依赖并构建
    if ! command -v pnpm &> /dev/null; then
        print_status "安装 pnpm..."
        npm install -g pnpm
    fi
    
    print_status "安装前端依赖..."
    pnpm install
    
    print_status "构建前端..."
    # 为Docker环境使用正确的环境变量
    cp .env.production .env
    NODE_OPTIONS="--max-old-space-size=4096" pnpm run build
    
    cd ..
}

# 构建并启动服务
deploy_services() {
    print_status "构建并启动 BiliNote 服务..."
    
    # 先构建前端
    build_frontend
    
    # 检查 .env 文件
    if [ ! -f ".env" ]; then
        print_warning "未找到 .env 文件，将使用默认配置"
        cat > .env << 'EOF'
BACKEND_PORT=8483
FRONTEND_PORT=3015
BACKEND_HOST=0.0.0.0
APP_PORT=3015
VITE_API_BASE_URL=http://127.0.0.1:8483
VITE_SCREENSHOT_BASE_URL=http://127.0.0.1:8483/static/screenshots
VITE_FRONTEND_PORT=3015
ENV=production
STATIC=/static
OUT_DIR=./static/screenshots
NOTE_OUTPUT_DIR=note_results
IMAGE_BASE_URL=/static/screenshots
DATA_DIR=data
TRANSCRIBER_TYPE=fast-whisper
WHISPER_MODEL_SIZE=base
GROQ_TRANSCRIBER_MODEL=whisper-large-v3-turbo
DOUYIN_COOKIES=
EOF
    fi
    
    # 设置 Docker 构建网络参数
    export DOCKER_BUILD_NETWORK_MODE=host
    export DOCKER_CLIENT_TIMEOUT=120
    export COMPOSE_HTTP_TIMEOUT=120
    
    # 使用国内镜像源配置构建
    if [ -f "docker-compose.china.yml" ]; then
        print_status "使用国内镜像源配置..."
        docker-compose -f docker-compose.china.yml up -d
    else
        print_status "使用标准配置..."
        docker-compose up -d
    fi
}

# 等待服务启动
wait_for_services() {
    print_status "等待服务启动..."
    
    # 等待后端服务
    local backend_ready=false
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://localhost:8483/docs > /dev/null 2>&1; then
            backend_ready=true
            break
        fi
        sleep 2
        attempt=$((attempt + 1))
        echo -n "."
    done
    
    echo ""
    
    if [ "$backend_ready" = true ]; then
        print_success "后端服务启动成功"
    else
        print_warning "后端服务启动超时，请检查日志"
    fi
    
    # 检查前端服务
    if curl -s http://localhost:3015 > /dev/null 2>&1; then
        print_success "前端服务启动成功"
    else
        print_warning "前端服务可能还在构建中"
    fi
}

# 显示服务状态
show_status() {
    echo ""
    print_success "🎉 BiliNote 部署完成！"
    echo ""
    echo "📋 服务信息："
    echo "   🌐 前端地址: http://localhost:3015"
    echo "   🔌 后端API: http://localhost:8483"
    echo "   📚 API文档: http://localhost:8483/docs"
    echo ""
    echo "📊 容器状态："
    DOCKER_HOST="$DOCKER_HOST" /usr/local/bin/docker-compose ps 2>/dev/null || DOCKER_HOST="$DOCKER_HOST" /usr/local/bin/docker ps
    echo ""
    echo "🔧 常用命令："
    echo "   查看日志: docker-compose logs -f"
    echo "   停止服务: docker-compose down"
    echo "   重启服务: docker-compose restart"
    echo ""
}

# 主函数
main() {
    print_header
    
    # 检查是否在项目根目录
    if [ ! -f "docker-compose.yml" ] && [ ! -f "docker-compose.china.yml" ]; then
        print_error "请在 BiliNote 项目根目录下运行此脚本"
        exit 1
    fi
    
    check_colima
    setup_docker_env
    pull_images
    cleanup_containers
    deploy_services
    wait_for_services
    show_status
}

# 错误处理
cleanup() {
    echo ""
    print_status "收到中断信号，正在清理..."
    exit 0
}

trap cleanup SIGINT SIGTERM

# 运行主函数
main "$@"