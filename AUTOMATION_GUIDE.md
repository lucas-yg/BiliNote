# BiliNote 自动化启动脚本使用指南

本项目提供了三个智能启动脚本，可以自动同步 fork 项目代码、安装依赖并启动服务。

## 🚀 脚本概览

### 1. `sync-fork.sh` - Fork 项目同步脚本
- 自动同步上游项目最新代码
- 检测并安装新的依赖
- 智能处理合并冲突
- 支持 Python 和 Node.js 依赖管理

### 2. `start.sh` - 项目启动脚本
- 集成代码同步功能
- 支持后端/前端独立启动
- 智能检测运行环境
- 交互式选择启动方式

### 3. `docker-start.sh` - Docker 容器启动脚本
- 自动同步代码并构建镜像
- 支持标准版和 GPU 版 Docker
- 完整的容器生命周期管理
- 服务状态监控和日志查看

## 📋 使用方法

### 基础同步操作

```bash
# 仅同步代码和依赖（推荐在运行项目前执行）
./sync-fork.sh
```

### 项目启动

```bash
# 交互式启动（推荐新手使用）
./start.sh

# 启动后端服务
./start.sh --backend

# 启动前端服务
./start.sh --frontend

# 跳过同步直接启动后端
./start.sh --backend --no-sync

# 仅执行同步，不启动服务
./start.sh --sync-only
```

### Docker 启动

```bash
# 交互式 Docker 启动
./docker-start.sh

# 启动标准版 Docker
./docker-start.sh --standard

# 启动 GPU 版 Docker
./docker-start.sh --gpu

# 清理后重新构建启动
./docker-start.sh --standard --clean

# 查看容器日志
./docker-start.sh --logs

# 查看服务状态
./docker-start.sh --status

# 停止服务
./docker-start.sh --stop
```

## 🔧 高级功能

### 自动依赖管理

脚本会自动检测以下依赖变化并安装：

**Python 依赖 (backend/requirements.txt)**
- 自动检测虚拟环境
- 使用 pip3/pip 安装新依赖
- 支持项目级和系统级 Python

**Node.js 依赖 (BillNote_frontend/package.json)**
- 自动检测包管理器 (bun/npm/yarn)
- 智能选择最佳安装方式
- 支持 lock 文件更新

### 智能合并处理

- 自动暂存未提交的更改
- 检测合并冲突并提供指导
- 安全的分支切换和恢复
- 完整的回滚机制

### 环境检测

- 检测 Git 仓库状态
- 验证必要命令存在
- 检测 Docker 环境和 GPU 支持
- 智能选择启动方式

## 📊 典型工作流程

### 日常开发流程

```bash
# 1. 开始工作前同步最新代码
./sync-fork.sh

# 2. 启动开发环境
./start.sh --backend    # 终端1：启动后端
./start.sh --frontend   # 终端2：启动前端
```

### 生产部署流程

```bash
# 1. 同步最新代码并启动 Docker
./docker-start.sh --standard --clean

# 2. 检查服务状态
./docker-start.sh --status

# 3. 查看日志确认启动成功
./docker-start.sh --logs
```

### GPU 环境流程

```bash
# 1. 检查 GPU 支持并启动
./docker-start.sh --gpu

# 2. 监控资源使用
./docker-start.sh --status
```

## 🛠️ 故障排除

### 常见问题

1. **代码同步失败**
   ```bash
   # 手动解决冲突后重新运行
   git status
   git add .
   git commit -m "解决合并冲突"
   ./sync-fork.sh
   ```

2. **依赖安装失败**
   ```bash
   # 手动安装 Python 依赖
   cd backend
   pip install -r requirements.txt
   
   # 手动安装 Node.js 依赖
   cd BillNote_frontend
   npm install  # 或 yarn install 或 bun install
   ```

3. **Docker 启动失败**
   ```bash
   # 检查 Docker 状态
   docker info
   
   # 清理 Docker 资源
   ./docker-start.sh --clean --standard
   ```

4. **端口冲突**
   - 前端默认端口：3000
   - 后端默认端口：8483
   - 如有冲突，请修改相应配置文件

### 权限问题

```bash
# 如果脚本无法执行，添加执行权限
chmod +x sync-fork.sh start.sh docker-start.sh
```

### 网络问题

```bash
# 如果无法访问 GitHub，检查网络连接
git remote -v
ping github.com

# 或使用 HTTPS 代替 SSH
git remote set-url upstream https://github.com/JefferyHcool/BiliNote.git
```

## 📝 自定义配置

### 修改上游仓库地址

编辑 `sync-fork.sh` 文件第85行：
```bash
git remote add upstream git@github.com:YOUR-UPSTREAM/BiliNote.git
```

### 修改默认端口

编辑对应的配置文件：
- 后端端口：`backend/main.py` 或 Docker 配置
- 前端端口：`BillNote_frontend/package.json` 或 `vite.config.ts`

### 添加自定义检查

在脚本中添加你需要的环境检查或预处理步骤。

## 🎯 最佳实践

1. **定期同步**：建议每周至少同步一次上游代码
2. **分支管理**：在个人分支进行开发，主分支仅用于同步
3. **依赖管理**：定期检查依赖安全更新
4. **备份重要**：同步前确保重要更改已提交
5. **测试环境**：使用 Docker 进行隔离测试

## 📞 获取帮助

如果遇到问题，可以：

1. 查看脚本输出的详细日志
2. 使用 `--help` 参数查看使用说明
3. 检查 GitHub 仓库的 Issues
4. 查看项目文档

---

🎉 享受自动化的开发体验！这些脚本将大大简化你的 fork 项目管理工作流程。