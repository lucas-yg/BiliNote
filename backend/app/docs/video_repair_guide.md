# 视频修复和错误处理指南

## 概述

本系统现在包含了增强的视频处理能力，可以处理损坏或格式异常的视频文件。当遇到 H.264 解码错误、NAL 单元错误等问题时，系统会自动尝试修复并继续处理。

## 新增功能

### 1. 自动视频修复 (`VideoRepairTool`)

- **视频验证**: 检查视频文件完整性和流信息
- **自动修复**: 重新编码损坏的视频以修复错误
- **健壮音频提取**: 即使视频损坏也能提取音频
- **错误恢复**: 使用多种策略处理不同类型的损坏

### 2. 增强的 FFmpeg 参数

所有视频处理现在使用了更健壮的 FFmpeg 参数：

```bash
# 错误忽略参数
-err_detect ignore_err          # 忽略解码错误
-fflags +discardcorrupt        # 丢弃损坏的包
-avoid_negative_ts make_zero   # 避免负时间戳问题
-fflags +genpts               # 生成 PTS (演示时间戳)
```

### 3. 用户友好的错误信息

- 技术错误自动转换为易懂的中文描述
- 提供具体的解决建议和操作指导
- 区分不同类型的错误（网络、文件损坏、配置等）

## 错误处理流程

### 音频提取错误处理

1. **首次尝试**: 使用标准参数提取音频
2. **检测错误**: 识别 H.264/NAL 单元错误
3. **激进模式**: 使用更宽松的参数重试
4. **视频修复**: 如果需要，重新编码整个视频
5. **用户反馈**: 提供清晰的错误信息和建议

### 截图生成错误处理  

1. **增强参数**: 使用错误忽略和包丢弃参数
2. **备用策略**: 失败时尝试不同的时间点和参数
3. **占位图片**: 完全失败时生成带说明的占位图

## 常见错误和解决方案

### H.264 NAL 单元错误

**错误特征**:
```
Invalid NAL unit size (xxx > yyy)
Error splitting the input into NAL units
missing picture in access unit
```

**自动处理**:
- 系统会自动使用 `-err_detect ignore_err` 参数
- 尝试重新编码修复视频结构
- 提供用户友好的错误提示

### 连接和网络错误

**错误特征**:
```
Connection error
Server disconnected without sending a response
```

**自动处理**:
- 指数退避重试机制（3次重试）
- 智能延迟策略
- 区分临时性和永久性错误

## API 使用示例

### 安全音频提取

```python
from app.utils.video_repair import safe_extract_audio

# 自动处理损坏视频
success, error_msg = safe_extract_audio(
    video_path="./damaged_video.mp4",
    audio_path="./output.mp3",
    bitrate="128k",
    repair_if_needed=True  # 允许自动修复
)

if success:
    print("音频提取成功")
else:
    print(f"提取失败: {error_msg}")
```

### 视频验证和修复

```python
from app.utils.video_repair import validate_and_repair_video

# 验证并修复视频
success, final_path, info = validate_and_repair_video("./video.mp4")

if success:
    print(f"视频可用: {final_path}")
    print(f"信息: {info}")
else:
    print("视频无法修复")
```

## 配置参数

### 重试配置

```python
MAX_RETRIES = 3        # 最大重试次数
BASE_DELAY = 2         # 基础延迟时间（秒）
MAX_DELAY = 60         # 最大延迟时间（秒）
```

### 音频质量映射

```python
quality_map = {
    "fast": "64k",     # 快速模式
    "medium": "128k",  # 标准模式  
    "slow": "192k"     # 高质量模式
}
```

## 性能优化

1. **分段处理**: 长视频自动分段处理，避免内存溢出
2. **缓存机制**: 处理结果本地缓存，避免重复处理
3. **超时控制**: 所有操作都有合理的超时限制
4. **资源清理**: 自动清理临时文件和资源

## 日志和调试

系统提供详细的日志记录：

```python
# 启用调试日志
import logging
logging.getLogger('app.utils.video_repair').setLevel(logging.DEBUG)
```

日志内容包括：
- 重试次数和延迟时间
- 错误类型和恢复策略
- 处理性能指标
- 文件大小和质量信息

## 最佳实践

1. **预检查**: 处理前验证视频文件完整性
2. **渐进处理**: 优先使用轻量级参数，失败时再升级
3. **用户反馈**: 提供处理进度和状态反馈
4. **错误记录**: 记录失败案例用于系统改进
5. **资源管理**: 及时清理临时文件和内存

## 故障排除

### 常见问题

1. **FFmpeg 未安装**: 安装 FFmpeg 并确保在 PATH 中
2. **权限问题**: 确保对视频文件和输出目录有读写权限
3. **磁盘空间**: 确保有足够空间存储临时文件
4. **视频格式**: 某些专有格式可能需要额外的编解码器

### 性能调优

1. **并行处理**: 可以并行处理多个视频的不同部分
2. **内存限制**: 大视频会自动分段以控制内存使用
3. **CPU 使用**: 可以调整 FFmpeg 线程数以平衡性能