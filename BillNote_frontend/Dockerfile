# === 前端构建阶段 ===
# 使用 Node.js Alpine 镜像
FROM node:18-alpine AS builder

# 设置工作目录
WORKDIR /app

# 安装pnpm
RUN npm install -g pnpm

# 拷贝package.json和lockfile
COPY ./BillNote_frontend/package.json ./BillNote_frontend/pnpm-lock.yaml ./

# 安装依赖
RUN pnpm install

# 拷贝前端源码
COPY ./BillNote_frontend ./

# 构建项目
RUN pnpm build

# --- 阶段2：使用 nginx 作为静态服务器 ---
FROM nginx:1.25-alpine

# 删除默认配置（可选）
RUN rm -rf /etc/nginx/conf.d/default.conf
COPY ./BillNote_frontend/deploy/default.conf /etc/nginx/conf.d/default.conf

# 拷贝构建产物
COPY --from=builder /app/dist /usr/share/nginx/html
