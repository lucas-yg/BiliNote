#!/bin/bash
# 生产环境启动脚本

echo "🚀 启动 BiliNote 生产环境"
echo "📋 检查环境配置..."

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "❌ 生产环境需要 .env 文件，请先配置"
    exit 1
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

# 构建并启动生产环境
echo "🏗️  构建生产环境镜像..."
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d

echo "✅ 生产环境启动完成!"
echo "🌍 访问地址: http://localhost:${APP_PORT:-3015}"
echo "🌐 API配置地址: http://$GATEWAY_IP:3001/v1"
echo "📊 查看日志: docker-compose -f docker-compose.prod.yml logs -f"