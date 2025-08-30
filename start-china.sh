#!/bin/bash

# BiliNote 启动脚本 (中国版 - 使用 Docker Buildx)

set -e

echo "🚀 启动 BiliNote 项目 (使用 Docker Buildx)"

# 设置 Docker Host 为 Colima
export DOCKER_HOST=unix:///Users/yyg/.colima/default/docker.sock

# 检查 Colima 是否运行
echo "📋 检查 Colima 状态..."
if ! colima status > /dev/null 2>&1; then
    echo "❌ Colima 未运行，请先启动: colima start"
    exit 1
fi
echo "✅ Colima 运行正常"

# 检查环境变量文件
if [ ! -f ".env" ]; then
    echo "❌ 未找到 .env 文件，请先配置环境变量"
    exit 1
fi

# 使用默认 Docker builder (更稳定)
echo "📋 使用默认 Docker builder..."
docker buildx use default

# 构建并启动服务 (使用缓存优化)
echo "🏗️  构建并启动服务 (优化缓存)..."
echo "💡 使用Docker BuildKit优化构建缓存..."
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# 使用docker-compose构建 (稳定且支持基本缓存)
echo "📦 构建镜像 (使用Docker层缓存和内存优化)..."
# 清理构建缓存以释放内存
echo "🧹 清理Docker构建缓存..."
docker builder prune -f

# 内存优化构建 - 限制并发构建数量
echo "🚀 开始内存优化构建..."
DOCKER_BUILDKIT=1 docker-compose -f docker-compose.china.yml build --parallel --memory=2g

echo "🚀 启动容器..."
docker-compose -f docker-compose.china.yml up -d

echo "📊 服务状态:"
docker-compose -f docker-compose.china.yml ps

echo ""
echo "✅ BiliNote 启动完成!"
echo "🌐 访问地址: http://localhost:${APP_PORT:-3000}"
echo ""
echo "📝 常用命令:"
echo "  - 查看日志: docker-compose -f docker-compose.china.yml logs -f"
echo "  - 停止服务: docker-compose -f docker-compose.china.yml down"
echo "  - 重新构建: docker buildx bake -f docker-compose.china.yml --load"