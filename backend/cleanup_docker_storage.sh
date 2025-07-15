#!/bin/bash

# BiliNote Docker 环境存储清理脚本
# 清理Docker运行时产生的视频文件

set -e

echo "🧹 开始清理 BiliNote Docker 环境中的视频文件..."

# 切换到 backend 目录
cd "$(dirname "$0")"

# 获取Docker容器状态
if docker ps | grep -q bilinote-backend; then
    echo "📋 检测到 bilinote-backend 容器正在运行"
    CONTAINER_RUNNING=true
else
    echo "⚠️  bilinote-backend 容器未运行"
    CONTAINER_RUNNING=false
fi

# 函数：统计目录大小
get_directory_size() {
    local dir="$1"
    if [ -d "$dir" ]; then
        du -sh "$dir" 2>/dev/null | cut -f1
    else
        echo "0"
    fi
}

# 函数：统计文件数量
count_files() {
    local dir="$1"
    local pattern="$2"
    if [ -d "$dir" ]; then
        find "$dir" -name "$pattern" 2>/dev/null | wc -l
    else
        echo "0"
    fi
}

# 统计清理前的情况
echo "📊 清理前的存储情况:"
echo "----------------------------------------"
echo "uploads 目录大小: $(get_directory_size "uploads")"
echo "data 目录大小: $(get_directory_size "data")"
echo "note_results 目录大小: $(get_directory_size "note_results")"
echo ""

# 统计各类文件数量
video_count=$(count_files "uploads" "*.mp4") 
audio_count=$(count_files "uploads" "*.mp3")
other_media_count=$(($(count_files "uploads" "*.avi") + $(count_files "uploads" "*.mkv") + $(count_files "uploads" "*.mov") + $(count_files "uploads" "*.flv") + $(count_files "uploads" "*.webm") + $(count_files "uploads" "*.wav") + $(count_files "uploads" "*.m4a")))

echo "视频文件 (.mp4): $video_count 个"
echo "音频文件 (.mp3): $audio_count 个"
echo "其他媒体文件: $other_media_count 个"
echo "----------------------------------------"

# 清理函数
cleanup_media_files() {
    local dir="$1"
    local description="$2"
    
    if [ -d "$dir" ]; then
        echo "🔍 清理 $description..."
        
        # 清理各种视频和音频文件
        for ext in mp4 mp3 avi mkv mov flv webm wav m4a; do
            find "$dir" -name "*.$ext" -delete 2>/dev/null || true
        done
        
        echo "   ✅ $description 清理完成"
    else
        echo "   ⚠️  目录不存在: $dir"
    fi
}

# 执行清理
echo ""
echo "🚀 开始清理媒体文件..."

# 1. 清理上传目录
cleanup_media_files "uploads" "上传的视频和音频文件"

# 2. 清理数据目录
cleanup_media_files "data" "处理过程中的媒体文件"

# 3. 清理note_results目录中的媒体文件
cleanup_media_files "note_results" "结果目录中的媒体文件"

# 4. 清理根目录下的媒体文件
echo "🔍 清理根目录下的媒体文件..."
for ext in mp4 mp3 avi mkv mov flv webm wav m4a; do
    find . -maxdepth 1 -name "*.$ext" -delete 2>/dev/null || true
done

# 5. 如果Docker容器正在运行，也清理容器内的文件
if [ "$CONTAINER_RUNNING" = true ]; then
    echo "🔍 清理 Docker 容器内的媒体文件..."
    
    # 清理容器内的媒体文件
    docker exec bilinote-backend find /app -name "*.mp4" -delete 2>/dev/null || true
    docker exec bilinote-backend find /app -name "*.mp3" -delete 2>/dev/null || true
    docker exec bilinote-backend find /app -name "*.avi" -delete 2>/dev/null || true
    docker exec bilinote-backend find /app -name "*.mkv" -delete 2>/dev/null || true
    docker exec bilinote-backend find /app -name "*.mov" -delete 2>/dev/null || true
    docker exec bilinote-backend find /app -name "*.flv" -delete 2>/dev/null || true
    docker exec bilinote-backend find /app -name "*.webm" -delete 2>/dev/null || true
    docker exec bilinote-backend find /app -name "*.wav" -delete 2>/dev/null || true
    docker exec bilinote-backend find /app -name "*.m4a" -delete 2>/dev/null || true
    
    echo "   ✅ Docker 容器内文件清理完成"
fi

# 6. 清理临时文件
echo "🔍 清理临时文件..."
find . -name "*.tmp" -delete 2>/dev/null || true
find . -name "*.temp" -delete 2>/dev/null || true
find . -name ".DS_Store" -delete 2>/dev/null || true

# 7. 清理Python缓存
echo "🔍 清理Python缓存..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

# 统计清理后的情况
echo ""
echo "📊 清理完成！当前存储使用情况:"
echo "----------------------------------------"
echo "uploads 目录大小: $(get_directory_size "uploads")"
echo "data 目录大小: $(get_directory_size "data")"
echo "note_results 目录大小: $(get_directory_size "note_results")"
echo "----------------------------------------"
echo "Backend 总大小: $(get_directory_size ".")"
echo ""

# 统计释放的空间
remaining_video=$(count_files "uploads" "*.mp4")
remaining_audio=$(count_files "uploads" "*.mp3")
remaining_other=$(($(count_files "uploads" "*.avi") + $(count_files "uploads" "*.mkv") + $(count_files "uploads" "*.mov") + $(count_files "uploads" "*.flv") + $(count_files "uploads" "*.webm") + $(count_files "uploads" "*.wav") + $(count_files "uploads" "*.m4a")))

echo "剩余文件统计:"
echo "视频文件 (.mp4): $remaining_video 个"
echo "音频文件 (.mp3): $remaining_audio 个"
echo "其他媒体文件: $remaining_other 个"
echo ""

if [ $remaining_video -eq 0 ] && [ $remaining_audio -eq 0 ] && [ $remaining_other -eq 0 ]; then
    echo "✨ 清理完成！所有媒体文件已被删除。"
else
    echo "⚠️  仍有 $((remaining_video + remaining_audio + remaining_other)) 个媒体文件未被删除，请检查权限或文件占用情况。"
fi

echo ""
echo "💡 建议:"
echo "1. 可以将此脚本添加到 crontab 中实现定期清理"
echo "2. 在 Docker 环境中，媒体文件会同步到宿主机，建议定期清理"
echo "3. 如需保留某些文件，请在清理前备份重要内容"