# 进入Colima虚拟机
colima ssh

# 使用Docker容器下载Buildx
docker run --rm -v ~/.docker/cli-plugins:/output alpine:latest sh -c "apk add --no-cache curl && curl -SL https://ghproxy.com/https://github.com/docker/buildx/releases/download/v0.11.2/buildx-v0.11.2.linux-arm64 -o /output/docker-buildx"

# 设置可执行权限
chmod +x ~/.docker/cli-plugins/docker-buildx

# 验证安装
docker buildx version

# 退出虚拟机
exit