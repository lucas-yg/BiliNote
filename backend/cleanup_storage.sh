#!/bin/bash

# BiliNote 存储清理脚本
# 用于清理上传文件和处理缓存，释放磁盘空间

set -e

echo "🧹 开始清理 BiliNote 存储文件..."

# 切换到 backend 目录
cd "$(dirname "$0")"

# 定义保留天数
UPLOADS_RETENTION_DAYS=7    # 上传文件保留7天
DATA_RETENTION_DAYS=3       # 处理数据保留3天
FRAMES_RETENTION_DAYS=1     # 截图帧保留1天

# 函数：安全删除文件
cleanup_directory() {
    local dir="$1"
    local days="$2"
    local description="$3"
    
    if [ -d "$dir" ]; then
        echo "🔍 清理 $description (${days}天前的文件)..."
        
        # 统计清理前的大小
        before_size=$(du -sh "$dir" 2>/dev/null | cut -f1 || echo "0")
        
        # 删除指定天数前的文件
        find "$dir" -type f -mtime +${days} -delete 2>/dev/null || true
        
        # 删除空目录
        find "$dir" -type d -empty -delete 2>/dev/null || true
        
        # 统计清理后的大小
        after_size=$(du -sh "$dir" 2>/dev/null | cut -f1 || echo "0")
        
        echo "   ✅ $description: $before_size → $after_size"
    else
        echo "   ⚠️  目录不存在: $dir"
    fi
}

# 1. 清理上传文件
cleanup_directory "uploads" $UPLOADS_RETENTION_DAYS "上传文件"

# 2. 清理数据文件
cleanup_directory "data/data" $DATA_RETENTION_DAYS "处理数据"

# 3. 清理截图帧
cleanup_directory "data/output_frames" $FRAMES_RETENTION_DAYS "截图帧"
cleanup_directory "data/grid_output" $FRAMES_RETENTION_DAYS "网格截图"

# 4. 清理临时文件
echo "🔍 清理临时文件..."
find . -name "*.tmp" -delete 2>/dev/null || true
find . -name "*.temp" -delete 2>/dev/null || true
find . -name ".DS_Store" -delete 2>/dev/null || true

# 5. 清理Python缓存
echo "🔍 清理Python缓存..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

# 6. 显示清理后的磁盘使用情况
echo ""
echo "📊 清理完成！当前存储使用情况:"
echo "----------------------------------------"
[ -d "uploads" ] && echo "uploads:      $(du -sh uploads 2>/dev/null | cut -f1)"
[ -d "data" ] && echo "data:         $(du -sh data 2>/dev/null | cut -f1)"
[ -d "note_results" ] && echo "note_results: $(du -sh note_results 2>/dev/null | cut -f1)"
[ -d "models" ] && echo "models:       $(du -sh models 2>/dev/null | cut -f1)"
echo "----------------------------------------"
echo "Backend 总大小: $(du -sh . 2>/dev/null | cut -f1)"
echo ""
echo "✨ 清理完成！建议定期运行此脚本释放磁盘空间。"
echo "💡 可以将此脚本添加到 crontab 中实现自动清理："
echo "   0 2 * * * /path/to/cleanup_storage.sh"