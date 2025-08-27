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

# 使用默认 Docker builder
echo "📋 使用默认 Docker builder..."
docker buildx use default

# 构建并启动服务
echo "🏗️  构建并启动服务..."
docker-compose -f docker-compose.china.yml build

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