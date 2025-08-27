"""
OCR文字识别模块

集成多种OCR技术以准确识别代码文本。
"""

from .paddle_ocr import PaddleOCRService
from .tesseract_ocr import TesseractOCRService
from .ocr_optimizer import OCROptimizer

__all__ = ["PaddleOCRService", "TesseractOCRService", "OCROptimizer"]