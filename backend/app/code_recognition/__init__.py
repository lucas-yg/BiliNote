"""
BiliNote 代码识别模块

用于从编程教学视频中识别和转录代码内容的多模态解决方案。

主要功能:
- 自动检测代码编辑器界面
- 提取完整的代码文件内容
- 识别代码修改过程
- 生成代码演示的步骤说明
- 支持多种IDE和编辑器
"""

from .services.code_recognition_service import CodeRecognitionService

__all__ = ["CodeRecognitionService"]