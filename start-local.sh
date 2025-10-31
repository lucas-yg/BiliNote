#!/bin/bash
###
 # @Author: yangyuguang 2556885696@qq.com
 # @Date: 2025-10-31 14:56:15
 # @LastEditors: yangyuguang 2556885696@qq.com
 # @LastEditTime: 2025-10-31 14:56:20
 # @FilePath: /BiliNote/start-local.sh
 # @Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
### 
# 本地开发环境启动脚本 - 分别启动后端和前端

echo "🚀 启动 BiliNote 本地开发环境"
echo "📋 检查环境配置..."

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "⚠️  .env 文件不存在，从 .env.example 复制"
    cp .env.example .env
fi

# 启动后端
echo "🔧 启动后端服务..."
cd backend
if [ ! -d "venv" ]; then
    echo "📦 创建Python虚拟环境..."
    python3 -m venv venv
fi

echo "📦 激活虚拟环境并安装依赖..."
source venv/bin/activate
pip install -r requirements.txt

echo "🚀 启动后端 (端口 8483)..."
python main.py &
BACKEND_PID=$!
cd ..

# 等待后端启动
echo "⏳ 等待后端启动..."
sleep 3

# 启动前端
echo "🌐 启动前端服务..."
cd BillNote_frontend

echo "📦 安装前端依赖..."
npm install

echo "🚀 启动前端开发服务器 (端口 5173)..."
npm run dev &
FRONTEND_PID=$!
cd ..

echo "✅ 本地开发环境启动完成!"
echo "📝 前端地址: http://localhost:5173"
echo "🔧 后端地址: http://localhost:8483"
echo "🔧 后端API文档: http://localhost:8483/docs"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 等待用户中断
trap "echo '🛑 停止服务...'; kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait