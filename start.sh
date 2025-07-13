#!/bin/bash

# BiliNote 智能启动脚本
# 功能：自动同步代码、安装依赖、启动项目

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
    echo "║          BiliNote 智能启动器           ║"
    echo "║     自动同步 + 依赖管理 + 项目启动     ║"
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

# 检查必要的命令
check_requirements() {
    local missing_commands=()
    
    if ! command -v git > /dev/null; then
        missing_commands+=("git")
    fi
    
    if ! command -v python3 > /dev/null && ! command -v python > /dev/null; then
        missing_commands+=("python3")
    fi
    
    if [ ${#missing_commands[@]} -ne 0 ]; then
        print_error "缺少必要的命令: ${missing_commands[*]}"
        exit 1
    fi
}

# 运行同步脚本
run_sync() {
    print_status "执行代码同步..."
    
    if [ -f "./sync-fork.sh" ]; then
        if ./sync-fork.sh; then
            print_success "代码同步完成"
            return 0
        else
            print_error "代码同步失败"
            return 1
        fi
    else
        print_warning "未找到sync-fork.sh，跳过同步步骤"
        return 0
    fi
}

# 启动后端服务
start_backend() {
    print_status "启动后端服务..."
    
    cd backend
    
    # 检查虚拟环境
    if [ -d "venv" ]; then
        print_status "激活虚拟环境..."
        source venv/bin/activate
    fi
    
    # 启动服务
    if command -v uvicorn > /dev/null; then
        print_success "使用 uvicorn 启动后端服务"
        uvicorn main:app --host 0.0.0.0 --port 8483 --reload
    elif [ -f "main.py" ]; then
        print_success "使用 python 启动后端服务"
        python main.py
    else
        print_error "无法启动后端服务"
        cd ..
        exit 1
    fi
}

# 启动前端服务
start_frontend() {
    print_status "启动前端服务..."
    
    cd BillNote_frontend
    
    # 检查包管理器并启动
    if command -v bun > /dev/null && [ -f "bun.lock" ]; then
        print_success "使用 bun 启动前端服务"
        bun run dev
    elif command -v npm > /dev/null; then
        print_success "使用 npm 启动前端服务"
        npm run dev
    elif command -v yarn > /dev/null; then
        print_success "使用 yarn 启动前端服务"
        yarn dev
    else
        print_error "无法启动前端服务"
        cd ..
        exit 1
    fi
}

# Docker启动
start_docker() {
    print_status "使用 Docker 启动项目..."
    
    # 检查docker-compose文件
    if [ -f "docker-compose.yml" ]; then
        print_success "找到 docker-compose.yml，启动服务..."
        docker-compose up --build
    elif [ -f "docker-compose.gpu.yml" ]; then
        print_warning "仅找到 GPU 版本的 docker-compose，启动 GPU 服务..."
        docker-compose -f docker-compose.gpu.yml up --build
    else
        print_error "未找到 docker-compose 文件"
        exit 1
    fi
}

# 显示使用说明
show_usage() {
    echo "使用方法:"
    echo "  $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --sync-only     仅执行代码同步，不启动服务"
    echo "  --backend       启动后端服务"
    echo "  --frontend      启动前端服务"
    echo "  --docker        使用 Docker 启动"
    echo "  --docker-gpu    使用 Docker GPU 版本启动"
    echo "  --no-sync       跳过代码同步直接启动"
    echo "  --help, -h      显示此帮助信息"
    echo ""
    echo "交互模式:"
    echo "  不带参数运行将进入交互选择模式"
}

# 交互式选择启动方式
interactive_mode() {
    echo ""
    echo "请选择启动方式:"
    echo "1) 后端服务 (Backend)"
    echo "2) 前端服务 (Frontend)"  
    echo "3) Docker 标准版"
    echo "4) Docker GPU 版"
    echo "5) 仅同步代码"
    echo "6) 退出"
    echo ""
    
    read -p "请输入选择 (1-6): " choice
    
    case $choice in
        1)
            return 1 # backend
            ;;
        2)
            return 2 # frontend
            ;;
        3)
            return 3 # docker
            ;;
        4)
            return 4 # docker-gpu
            ;;
        5)
            return 5 # sync-only
            ;;
        6)
            print_status "退出启动器"
            exit 0
            ;;
        *)
            print_error "无效选择，请重新选择"
            interactive_mode
            ;;
    esac
}

# 主函数
main() {
    print_header
    check_requirements
    
    # 解析命令行参数
    SYNC_ENABLED=true
    START_MODE=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --sync-only)
                START_MODE="sync-only"
                shift
                ;;
            --backend)
                START_MODE="backend"
                shift
                ;;
            --frontend)
                START_MODE="frontend"
                shift
                ;;
            --docker)
                START_MODE="docker"
                shift
                ;;
            --docker-gpu)
                START_MODE="docker-gpu"
                shift
                ;;
            --no-sync)
                SYNC_ENABLED=false
                shift
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            *)
                print_error "未知参数: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # 如果没有指定启动模式，进入交互模式
    if [ -z "$START_MODE" ]; then
        interactive_mode
        mode_choice=$?
        case $mode_choice in
            1) START_MODE="backend" ;;
            2) START_MODE="frontend" ;;
            3) START_MODE="docker" ;;
            4) START_MODE="docker-gpu" ;;
            5) START_MODE="sync-only" ;;
        esac
    fi
    
    # 执行代码同步
    if [ "$SYNC_ENABLED" = true ]; then
        echo ""
        print_status "📥 开始代码同步流程..."
        if ! run_sync; then
            read -p "代码同步失败，是否继续启动项目？(y/N): " continue_choice
            case "$continue_choice" in 
                y|Y ) 
                    print_warning "跳过同步，继续启动项目"
                    ;;
                * ) 
                    print_error "取消启动"
                    exit 1
                    ;;
            esac
        fi
    else
        print_warning "跳过代码同步步骤"
    fi
    
    # 根据选择启动相应服务
    echo ""
    print_status "🚀 开始启动项目..."
    
    case $START_MODE in
        "sync-only")
            print_success "代码同步完成，未启动服务"
            ;;
        "backend")
            start_backend
            ;;
        "frontend")
            start_frontend
            ;;
        "docker")
            start_docker
            ;;
        "docker-gpu")
            print_status "使用 Docker GPU 版本启动..."
            docker-compose -f docker-compose.gpu.yml up --build
            ;;
        *)
            print_error "未知的启动模式: $START_MODE"
            exit 1
            ;;
    esac
}

# 处理中断信号
cleanup() {
    echo ""
    print_status "收到中断信号，正在清理..."
    # 这里可以添加清理逻辑
    exit 0
}

trap cleanup SIGINT SIGTERM

# 运行主函数
main "$@"