#!/bin/bash

# BiliNote Fork 项目自动同步脚本
# 功能：同步上游代码、检测依赖变化、自动安装新依赖

set -e  # 遇到错误立即退出

echo "🚀 BiliNote Fork 自动同步开始..."

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
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

# 检查是否在git仓库中
check_git_repo() {
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        print_error "当前目录不是git仓库"
        exit 1
    fi
}

# 检查是否有upstream
check_upstream() {
    if ! git remote | grep -q "upstream"; then
        print_warning "未找到upstream，正在添加..."
        git remote add upstream git@github.com:JefferyHcool/BiliNote.git
        print_success "已添加upstream: git@github.com:JefferyHcool/BiliNote.git"
    fi
}

# 检查是否有未提交的更改
check_uncommitted_changes() {
    if ! git diff-index --quiet HEAD -- 2>/dev/null; then
        print_warning "检测到未提交的更改"
        echo "未提交的文件："
        git status --porcelain
        read -p "是否要暂存这些更改并继续同步？(y/N): " choice
        case "$choice" in 
            y|Y ) 
                print_status "暂存当前更改..."
                git stash push -m "Auto-stash before sync $(date)"
                echo "STASHED=true" > /tmp/bilinote_sync_state
                ;;
            * ) 
                print_error "请先处理未提交的更改"
                exit 1
                ;;
        esac
    fi
}

# 获取主分支名称
get_main_branch() {
    if git show-ref --verify --quiet refs/heads/main; then
        echo "main"
    elif git show-ref --verify --quiet refs/heads/master; then
        echo "master"
    else
        print_error "未找到主分支(main/master)"
        exit 1
    fi
}

# 备份依赖文件
backup_dependencies() {
    print_status "备份当前依赖文件..."
    
    # 备份Python依赖
    if [ -f "backend/requirements.txt" ]; then
        cp backend/requirements.txt backend/requirements.txt.backup
    fi
    
    # 备份Node.js依赖
    if [ -f "BillNote_frontend/package.json" ]; then
        cp BillNote_frontend/package.json BillNote_frontend/package.json.backup
    fi
    
    if [ -f "BillNote_frontend/bun.lock" ]; then
        cp BillNote_frontend/bun.lock BillNote_frontend/bun.lock.backup
    fi
}

# 检测依赖变化
check_dependency_changes() {
    local has_changes=false
    
    print_status "检查依赖文件变化..."
    
    # 检查Python依赖
    if [ -f "backend/requirements.txt" ] && [ -f "backend/requirements.txt.backup" ]; then
        if ! diff -q backend/requirements.txt backend/requirements.txt.backup > /dev/null; then
            print_warning "检测到 backend/requirements.txt 发生变化"
            echo "变化详情："
            diff backend/requirements.txt.backup backend/requirements.txt || true
            has_changes=true
        fi
    fi
    
    # 检查Node.js依赖
    if [ -f "BillNote_frontend/package.json" ] && [ -f "BillNote_frontend/package.json.backup" ]; then
        if ! diff -q BillNote_frontend/package.json BillNote_frontend/package.json.backup > /dev/null; then
            print_warning "检测到 BillNote_frontend/package.json 发生变化"
            has_changes=true
        fi
    fi
    
    if [ "$has_changes" = true ]; then
        echo "DEPS_CHANGED=true" >> /tmp/bilinote_sync_state
        return 0
    else
        print_success "依赖文件无变化"
        return 1
    fi
}

# 安装Python依赖
install_python_deps() {
    print_status "更新Python依赖..."
    
    cd backend
    
    # 检查是否存在虚拟环境
    if [ -d "venv" ]; then
        print_status "激活现有虚拟环境..."
        source venv/bin/activate
    elif [ -d "../venv" ]; then
        print_status "激活项目虚拟环境..."
        source ../venv/bin/activate
    else
        print_warning "未找到虚拟环境，使用系统Python"
    fi
    
    # 安装依赖
    if command -v pip3 > /dev/null; then
        pip3 install -r requirements.txt
    elif command -v pip > /dev/null; then
        pip install -r requirements.txt
    else
        print_error "未找到pip命令"
        cd ..
        return 1
    fi
    
    cd ..
    print_success "Python依赖更新完成"
}

# 安装Node.js依赖
install_node_deps() {
    print_status "更新Node.js依赖..."
    
    cd BillNote_frontend
    
    # 检查包管理器
    if command -v bun > /dev/null && [ -f "bun.lock" ]; then
        print_status "使用 bun 安装依赖..."
        bun install
    elif command -v npm > /dev/null; then
        print_status "使用 npm 安装依赖..."
        npm install
    elif command -v yarn > /dev/null; then
        print_status "使用 yarn 安装依赖..."
        yarn install
    else
        print_error "未找到Node.js包管理器 (bun/npm/yarn)"
        cd ..
        return 1
    fi
    
    cd ..
    print_success "Node.js依赖更新完成"
}

# 清理备份文件
cleanup_backups() {
    print_status "清理备份文件..."
    rm -f backend/requirements.txt.backup
    rm -f BillNote_frontend/package.json.backup
    rm -f BillNote_frontend/bun.lock.backup
    rm -f /tmp/bilinote_sync_state
}

# 恢复暂存的更改
restore_stashed_changes() {
    if [ -f "/tmp/bilinote_sync_state" ] && grep -q "STASHED=true" /tmp/bilinote_sync_state; then
        print_status "恢复之前暂存的更改..."
        git stash pop
        print_success "已恢复暂存的更改"
    fi
}

# 主同步流程
sync_fork() {
    print_status "开始同步fork项目..."
    
    # 获取当前分支
    CURRENT_BRANCH=$(git branch --show-current)
    MAIN_BRANCH=$(get_main_branch)
    
    print_status "当前分支: $CURRENT_BRANCH"
    print_status "主分支: $MAIN_BRANCH"
    
    # 拉取上游代码
    print_status "拉取上游仓库最新代码..."
    git fetch upstream
    
    # 切换到主分支
    if [ "$CURRENT_BRANCH" != "$MAIN_BRANCH" ]; then
        print_status "切换到主分支 ($MAIN_BRANCH)..."
        git checkout $MAIN_BRANCH
    fi
    
    # 检查是否有新的提交
    LOCAL_COMMIT=$(git rev-parse HEAD)
    UPSTREAM_COMMIT=$(git rev-parse upstream/$MAIN_BRANCH)
    
    if [ "$LOCAL_COMMIT" = "$UPSTREAM_COMMIT" ]; then
        print_success "已经是最新版本，无需同步"
        if [ "$CURRENT_BRANCH" != "$MAIN_BRANCH" ]; then
            print_status "切换回原分支 ($CURRENT_BRANCH)..."
            git checkout $CURRENT_BRANCH
        fi
        return 0
    fi
    
    print_status "发现新的提交，开始合并..."
    echo "新增提交:"
    git log --oneline $LOCAL_COMMIT..$UPSTREAM_COMMIT
    
    # 备份依赖文件
    backup_dependencies
    
    # 合并上游代码
    print_status "合并上游代码..."
    if git merge upstream/$MAIN_BRANCH --no-edit; then
        print_success "代码合并成功"
    else
        print_error "代码合并失败，可能存在冲突"
        print_status "请手动解决冲突后重新运行脚本"
        exit 1
    fi
    
    # 推送到自己的仓库
    print_status "推送到自己的仓库..."
    git push origin $MAIN_BRANCH
    
    # 检查依赖变化并安装
    if check_dependency_changes; then
        print_status "检测到依赖变化，开始安装新依赖..."
        
        # 安装Python依赖
        if [ -f "backend/requirements.txt" ]; then
            install_python_deps
        fi
        
        # 安装Node.js依赖
        if [ -f "BillNote_frontend/package.json" ]; then
            install_node_deps
        fi
    fi
    
    # 切换回原分支
    if [ "$CURRENT_BRANCH" != "$MAIN_BRANCH" ]; then
        print_status "切换回原分支 ($CURRENT_BRANCH)..."
        git checkout $CURRENT_BRANCH
        
        # 可选：将主分支的更改合并到当前分支
        read -p "是否要将最新更改合并到当前分支 $CURRENT_BRANCH？(y/N): " merge_choice
        case "$merge_choice" in 
            y|Y ) 
                print_status "合并主分支到当前分支..."
                git merge $MAIN_BRANCH --no-edit
                ;;
        esac
    fi
    
    print_success "Fork同步完成！"
}

# 主函数
main() {
    # 初始化状态文件
    echo "" > /tmp/bilinote_sync_state
    
    # 检查环境
    check_git_repo
    check_upstream
    check_uncommitted_changes
    
    # 执行同步
    sync_fork
    
    # 恢复暂存的更改
    restore_stashed_changes
    
    # 清理
    cleanup_backups
    
    print_success "🎉 所有操作完成！项目已更新到最新版本"
    echo ""
    echo "📋 摘要："
    echo "   - 代码已同步到最新版本"
    echo "   - 依赖已检查并更新"
    echo "   - 项目已准备好运行"
    echo ""
    echo "🚀 现在可以安全地启动项目或运行Docker"
}

# 处理中断信号
trap cleanup_backups EXIT

# 运行主函数
main "$@"