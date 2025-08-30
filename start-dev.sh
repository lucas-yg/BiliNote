#!/bin/bash
# 开发环境启动脚本

echo "🚀 启动 BiliNote 开发环境"
echo "📋 检查环境配置..."

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "⚠️  .env 文件不存在，从 .env.example 复制"
    cp .env.example .env
fi

# 检查Docker网关IP
echo "📋 检测Docker网关IP..."
GATEWAY_IP=$(docker network inspect bridge --format='{{range .IPAM.Config}}{{.Gateway}}{{end}}' 2>/dev/null || echo "172.18.0.1")
echo "✅ Docker网关IP: $GATEWAY_IP"

# 更新环境变量
if ! grep -q "HOST_GATEWAY=" .env; then
    echo "HOST_GATEWAY=$GATEWAY_IP" >> .env
    echo "✅ 已添加 HOST_GATEWAY 到 .env"
else
    sed -i.bak "s/HOST_GATEWAY=.*/HOST_GATEWAY=$GATEWAY_IP/" .env
    echo "✅ 已更新 HOST_GATEWAY 为 $GATEWAY_IP"
fi

# 启动开发环境
echo "🏗️  启动开发环境服务..."
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml up -d

echo "✅ 开发环境启动完成!"
echo "📝 前端地址: http://localhost:${APP_PORT:-3015}"
echo "🔧 后端地址: http://localhost:${BACKEND_PORT:-8483}"
echo "🌐 API配置地址: http://$GATEWAY_IP:3001/v1"