# === 前端构建阶段 ===
# 推荐使用 Bun 官方的 Alpine 镜像，它已经预装了 Bun
FROM oven/bun:latest-alpine AS builder

# 设置工作目录
WORKDIR /app

# 拷贝前端源码
COPY ./BillNote_frontend /app

# 安装依赖并构建
# Bun 会自动查找 package.json 并安装依赖，然后运行构建脚本
RUN bun install && bun run build

# --- 阶段2：使用 nginx 作为静态服务器 ---
FROM nginx:1.25-alpine

# 删除默认配置（可选）
RUN rm -rf /etc/nginx/conf.d/default.conf
COPY ./BillNote_frontend/deploy/default.conf /etc/nginx/conf.d/default.conf

# 拷贝构建产物
COPY --from=builder /app/dist /usr/share/nginx/html
