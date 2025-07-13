#!/bin/bash

# BiliNote Docker 智能启动脚本
# 功能：自动同步代码、构建镜像、启动容器

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
    echo "║        BiliNote Docker 启动器          ║"
    echo "║    自动同步 + 构建 + 容器化部署        ║"
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

# 检查Docker环境
check_docker() {
    if ! command -v docker > /dev/null; then
        print_error "未找到 Docker，请先安装 Docker"
        exit 1
    fi
    
    if ! command -v docker-compose > /dev/null; then
        print_error "未找到 docker-compose，请先安装 docker-compose"
        exit 1
    fi
    
    # 检查Docker是否运行
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker 未运行，请启动 Docker"
        exit 1
    fi
    
    print_success "Docker 环境检查通过"
}

# 检查GPU支持
check_gpu_support() {
    if command -v nvidia-smi > /dev/null 2>&1; then
        print_success "检测到 NVIDIA GPU"
        return 0
    else
        print_warning "未检测到 NVIDIA GPU"
        return 1
    fi
}

# 同步代码
sync_code() {
    print_status "执行代码同步..."
    
    if [ -f "./sync-fork.sh" ]; then
        if ./sync-fork.sh; then
            print_success "代码同步完成"
        else
            print_warning "代码同步失败，继续使用当前代码"
        fi
    else
        print_warning "未找到 sync-fork.sh，跳过同步"
    fi
}

# 清理旧容器和镜像
cleanup_docker() {
    print_status "清理旧的 Docker 资源..."
    
    # 停止并删除相关容器
    docker-compose down --remove-orphans 2>/dev/null || true
    
    # 可选：删除悬空镜像
    if docker images -f "dangling=true" -q | grep -q .; then
        print_status "清理悬空镜像..."
        docker rmi $(docker images -f "dangling=true" -q) 2>/dev/null || true
    fi
    
    print_success "Docker 清理完成"
}

# 构建并启动标准版本
start_standard() {
    print_status "启动标准版 Docker 容器..."
    
    if [ ! -f "docker-compose.yml" ]; then
        print_error "未找到 docker-compose.yml 文件"
        exit 1
    fi
    
    print_status "构建并启动容器..."
    docker-compose up --build -d
    
    print_success "标准版容器启动成功"
    show_service_info
}

# 构建并启动GPU版本
start_gpu() {
    print_status "启动 GPU 版 Docker 容器..."
    
    if [ ! -f "docker-compose.gpu.yml" ]; then
        print_error "未找到 docker-compose.gpu.yml 文件"
        exit 1
    fi
    
    # 检查GPU支持
    if ! check_gpu_support; then
        print_warning "未检测到GPU，建议使用标准版本"
        read -p "是否仍要继续启动GPU版本？(y/N): " choice
        case "$choice" in 
            y|Y ) 
                print_status "继续启动GPU版本..."
                ;;
            * ) 
                print_status "切换到标准版本..."
                start_standard
                return
                ;;
        esac
    fi
    
    print_status "构建并启动GPU容器..."
    docker-compose -f docker-compose.gpu.yml up --build -d
    
    print_success "GPU版容器启动成功"
    show_service_info
}

# 显示服务信息
show_service_info() {
    echo ""
    print_success "🎉 BiliNote 服务已启动！"
    echo ""
    echo "📋 服务信息："
    echo "   🌐 前端地址: http://localhost:3000"
    echo "   🔌 后端API: http://localhost:8483"
    echo "   📚 API文档: http://localhost:8483/docs"
    echo ""
    echo "📊 容器状态："
    docker-compose ps
    echo ""
    echo "🔧 常用命令："
    echo "   查看日志: docker-compose logs -f"
    echo "   停止服务: docker-compose down"
    echo "   重启服务: docker-compose restart"
    echo ""
}

# 显示日志
show_logs() {
    print_status "显示容器日志..."
    
    echo "选择要查看的服务日志："
    echo "1) 全部服务"
    echo "2) 前端服务"
    echo "3) 后端服务"
    echo ""
    
    read -p "请选择 (1-3): " log_choice
    
    case $log_choice in
        1)
            docker-compose logs -f
            ;;
        2)
            docker-compose logs -f frontend 2>/dev/null || docker-compose logs -f
            ;;
        3)
            docker-compose logs -f backend 2>/dev/null || docker-compose logs -f
            ;;
        *)
            print_error "无效选择"
            ;;
    esac
}

# 停止服务
stop_services() {
    print_status "停止 Docker 服务..."
    docker-compose down
    print_success "服务已停止"
}

# 重启服务
restart_services() {
    print_status "重启 Docker 服务..."
    docker-compose restart
    print_success "服务已重启"
    show_service_info
}

# 显示使用说明
show_usage() {
    echo "使用方法:"
    echo "  $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --standard      启动标准版 Docker"
    echo "  --gpu          启动 GPU 版 Docker"
    echo "  --no-sync      跳过代码同步"
    echo "  --clean        清理后重新构建"
    echo "  --logs         查看容器日志"
    echo "  --stop         停止服务"
    echo "  --restart      重启服务"
    echo "  --status       显示服务状态"
    echo "  --help, -h     显示此帮助信息"
    echo ""
    echo "交互模式:"
    echo "  不带参数运行将进入交互选择模式"
}

# 交互式选择
interactive_mode() {
    echo ""
    echo "请选择操作:"
    echo "1) 启动标准版 Docker"
    echo "2) 启动 GPU 版 Docker"
    echo "3) 查看服务日志"
    echo "4) 停止服务"
    echo "5) 重启服务"
    echo "6) 显示服务状态"
    echo "7) 清理并重建"
    echo "8) 退出"
    echo ""
    
    read -p "请输入选择 (1-8): " choice
    
    case $choice in
        1) return 1 ;;
        2) return 2 ;;
        3) return 3 ;;
        4) return 4 ;;
        5) return 5 ;;
        6) return 6 ;;
        7) return 7 ;;
        8) exit 0 ;;
        *)
            print_error "无效选择，请重新选择"
            interactive_mode
            ;;
    esac
}

# 显示服务状态
show_status() {
    print_status "Docker 服务状态："
    echo ""
    
    if docker-compose ps | grep -q "Up"; then
        print_success "服务正在运行"
        docker-compose ps
        echo ""
        echo "📊 资源使用情况："
        docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
    else
        print_warning "服务未运行"
        docker-compose ps
    fi
}

# 主函数
main() {
    print_header
    check_docker
    
    # 解析命令行参数
    SYNC_ENABLED=true
    CLEAN_BUILD=false
    ACTION=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --standard)
                ACTION="standard"
                shift
                ;;
            --gpu)
                ACTION="gpu"
                shift
                ;;
            --no-sync)
                SYNC_ENABLED=false
                shift
                ;;
            --clean)
                CLEAN_BUILD=true
                shift
                ;;
            --logs)
                ACTION="logs"
                shift
                ;;
            --stop)
                ACTION="stop"
                shift
                ;;
            --restart)
                ACTION="restart"
                shift
                ;;
            --status)
                ACTION="status"
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
    
    # 如果没有指定动作，进入交互模式
    if [ -z "$ACTION" ]; then
        interactive_mode
        action_choice=$?
        case $action_choice in
            1) ACTION="standard" ;;
            2) ACTION="gpu" ;;
            3) ACTION="logs" ;;
            4) ACTION="stop" ;;
            5) ACTION="restart" ;;
            6) ACTION="status" ;;
            7) 
                ACTION="standard"
                CLEAN_BUILD=true
                ;;
        esac
    fi
    
    # 执行代码同步（仅在启动动作时）
    if [[ "$ACTION" == "standard" || "$ACTION" == "gpu" ]] && [ "$SYNC_ENABLED" = true ]; then
        echo ""
        print_status "📥 开始代码同步..."
        sync_code
    fi
    
    # 清理构建（如果需要）
    if [ "$CLEAN_BUILD" = true ] && [[ "$ACTION" == "standard" || "$ACTION" == "gpu" ]]; then
        echo ""
        print_status "🧹 清理 Docker 环境..."
        cleanup_docker
    fi
    
    # 执行相应动作
    echo ""
    case $ACTION in
        "standard")
            start_standard
            ;;
        "gpu")
            start_gpu
            ;;
        "logs")
            show_logs
            ;;
        "stop")
            stop_services
            ;;
        "restart")
            restart_services
            ;;
        "status")
            show_status
            ;;
        *)
            print_error "未知的动作: $ACTION"
            exit 1
            ;;
    esac
}

# 处理中断信号
cleanup() {
    echo ""
    print_status "收到中断信号..."
    exit 0
}

trap cleanup SIGINT SIGTERM

# 运行主函数
main "$@"