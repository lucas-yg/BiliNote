"""
PaddleOCR集成服务

使用PaddleOCR进行代码文本识别，特别优化了对代码文本的识别准确性。
"""

import numpy as np
from typing import List, Dict, Tuple, Optional, Union
import cv2
import base64
import io
from PIL import Image

try:
    from paddleocr import PaddleOCR
    PADDLE_OCR_AVAILABLE = True
except ImportError:
    PADDLE_OCR_AVAILABLE = False

from app.utils.logger import get_logger

logger = get_logger(__name__)

class PaddleOCRService:
    def __init__(self, use_gpu: bool = False, lang: str = 'ch'):
        """
        初始化PaddleOCR服务
        
        Args:
            use_gpu: 是否使用GPU加速
            lang: 语言设置，'ch'为中文，'en'为英文
        """
        self.use_gpu = use_gpu
        self.lang = lang
        self.ocr_model = None
        self.is_initialized = False
        
        if not PADDLE_OCR_AVAILABLE:
            logger.warning("PaddleOCR未安装，无法使用PaddleOCR服务")
            return
        
        self._initialize_model()
    
    def _initialize_model(self):
        """初始化OCR模型"""
        try:
            self.ocr_model = PaddleOCR(
                use_angle_cls=True,  # 使用方向分类器
                lang=self.lang,
                use_gpu=self.use_gpu,
                show_log=False  # 关闭日志输出
            )
            self.is_initialized = True
            logger.info(f"PaddleOCR初始化成功 (GPU: {self.use_gpu}, 语言: {self.lang})")
        except Exception as e:
            logger.error(f"PaddleOCR初始化失败: {str(e)}")
            self.is_initialized = False
    
    def recognize_text(self, image: Union[np.ndarray, str]) -> Dict:
        """
        识别图像中的文本
        
        Args:
            image: numpy数组格式的图像或base64编码的图像字符串
            
        Returns:
            识别结果字典
        """
        if not self.is_initialized:
            return {
                'success': False,
                'error': 'PaddleOCR未正确初始化',
                'text_results': []
            }
        
        try:
            # 处理输入图像
            img_array = self._process_input_image(image)
            if img_array is None:
                return {
                    'success': False,
                    'error': '图像处理失败',
                    'text_results': []
                }
            
            # 执行OCR识别
            results = self.ocr_model.ocr(img_array, cls=True)
            
            # 处理识别结果
            processed_results = self._process_ocr_results(results)
            
            return {
                'success': True,
                'text_results': processed_results,
                'total_text_boxes': len(processed_results),
                'full_text': self._extract_full_text(processed_results)
            }
            
        except Exception as e:
            logger.error(f"PaddleOCR文本识别失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'text_results': []
            }
    
    def _process_input_image(self, image: Union[np.ndarray, str]) -> Optional[np.ndarray]:
        """处理输入图像"""
        try:
            if isinstance(image, str):
                # 处理base64编码的图像
                if image.startswith('data:image'):
                    image = image.split(',')[1]
                
                img_data = base64.b64decode(image)
                img_array = np.frombuffer(img_data, np.uint8)
                img_array = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            else:
                # numpy数组格式的图像
                img_array = image.copy()
            
            if img_array is None:
                logger.error("图像解码失败")
                return None
                
            # 确保图像是BGR格式（PaddleOCR期望的格式）
            if len(img_array.shape) == 3 and img_array.shape[2] == 3:
                # 如果是RGB格式，转换为BGR
                if self._is_rgb_format(img_array):
                    img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
            return img_array
            
        except Exception as e:
            logger.error(f"图像处理失败: {str(e)}")
            return None
    
    def _is_rgb_format(self, image: np.ndarray) -> bool:
        """简单判断图像是否为RGB格式"""
        # 这是一个简化的判断，实际中可能需要更复杂的逻辑
        # 这里假设如果蓝色通道的均值明显小于红色通道，则可能是RGB格式
        if len(image.shape) != 3:
            return False
        
        r_mean = np.mean(image[:, :, 0])
        b_mean = np.mean(image[:, :, 2])
        
        # 如果红色通道均值明显大于蓝色通道，可能是RGB格式
        return r_mean > b_mean * 1.5
    
    def _process_ocr_results(self, raw_results: List) -> List[Dict]:
        """处理OCR原始结果"""
        processed_results = []
        
        if not raw_results or not raw_results[0]:
            return processed_results
        
        for line in raw_results[0]:
            if not line:
                continue
            
            bbox_points = line[0]  # 边界框坐标点
            text_info = line[1]    # 文本和置信度
            
            text = text_info[0] if text_info else ""
            confidence = text_info[1] if len(text_info) > 1 else 0.0
            
            # 计算边界框
            bbox = self._calculate_bbox_from_points(bbox_points)
            
            # 过滤低置信度和空文本
            if confidence >= 0.5 and text.strip():
                processed_results.append({
                    'text': text.strip(),
                    'confidence': float(confidence),
                    'bbox': bbox,
                    'bbox_points': bbox_points
                })
        
        # 按y坐标排序（从上到下）
        processed_results.sort(key=lambda x: x['bbox'][1])
        
        return processed_results
    
    def _calculate_bbox_from_points(self, points: List[List[int]]) -> Tuple[int, int, int, int]:
        """从坐标点计算边界框"""
        if not points or len(points) != 4:
            return (0, 0, 0, 0)
        
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        
        return (int(x_min), int(y_min), int(x_max - x_min), int(y_max - y_min))
    
    def _extract_full_text(self, text_results: List[Dict]) -> str:
        """提取完整文本"""
        if not text_results:
            return ""
        
        # 按行分组
        lines = self._group_text_by_lines(text_results)
        
        # 组合成完整文本
        full_text_lines = []
        for line_texts in lines:
            line_text = " ".join(text['text'] for text in line_texts)
            full_text_lines.append(line_text)
        
        return "\n".join(full_text_lines)
    
    def _group_text_by_lines(self, text_results: List[Dict]) -> List[List[Dict]]:
        """将文本结果按行分组"""
        if not text_results:
            return []
        
        # 按y坐标排序
        sorted_results = sorted(text_results, key=lambda x: x['bbox'][1])
        
        lines = []
        current_line = [sorted_results[0]]
        current_y = sorted_results[0]['bbox'][1]
        
        for result in sorted_results[1:]:
            result_y = result['bbox'][1]
            
            # 如果y坐标差距较小，认为是同一行
            if abs(result_y - current_y) <= 20:  # 20像素的容差
                current_line.append(result)
            else:
                # 开始新的一行
                # 对当前行按x坐标排序
                current_line.sort(key=lambda x: x['bbox'][0])
                lines.append(current_line)
                
                current_line = [result]
                current_y = result_y
        
        # 添加最后一行
        if current_line:
            current_line.sort(key=lambda x: x['bbox'][0])
            lines.append(current_line)
        
        return lines
    
    def recognize_code_text(self, image: Union[np.ndarray, str], enhance_image: bool = True) -> Dict:
        """
        专门用于识别代码文本，包含额外的预处理步骤
        
        Args:
            image: 输入图像
            enhance_image: 是否对图像进行增强处理
            
        Returns:
            代码文本识别结果
        """
        try:
            # 预处理图像以提高代码识别准确性
            if enhance_image:
                processed_image = self._enhance_for_code_recognition(image)
            else:
                processed_image = image
            
            # 执行基础OCR识别
            ocr_result = self.recognize_text(processed_image)
            
            if not ocr_result['success']:
                return ocr_result
            
            # 后处理：优化代码文本识别结果
            enhanced_results = self._post_process_code_text(ocr_result['text_results'])
            
            return {
                'success': True,
                'text_results': enhanced_results,
                'code_text': self._format_as_code(enhanced_results),
                'total_text_boxes': len(enhanced_results),
                'confidence_stats': self._calculate_confidence_stats(enhanced_results)
            }
            
        except Exception as e:
            logger.error(f"代码文本识别失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'text_results': []
            }
    
    def _enhance_for_code_recognition(self, image: Union[np.ndarray, str]) -> np.ndarray:
        """为代码识别增强图像"""
        # 获取图像数组
        img_array = self._process_input_image(image)
        if img_array is None:
            return image if isinstance(image, np.ndarray) else np.array([])
        
        # 转换为灰度图
        gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
        
        # 1. 对比度增强
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # 2. 降噪
        denoised = cv2.bilateralFilter(enhanced, 9, 75, 75)
        
        # 3. 锐化
        kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        sharpened = cv2.filter2D(denoised, -1, kernel)
        
        # 转换回BGR格式
        enhanced_bgr = cv2.cvtColor(sharpened, cv2.COLOR_GRAY2BGR)
        
        return enhanced_bgr
    
    def _post_process_code_text(self, text_results: List[Dict]) -> List[Dict]:
        """后处理代码文本识别结果"""
        enhanced_results = []
        
        for result in text_results:
            text = result['text']
            
            # 代码文本的特殊处理
            processed_text = self._clean_code_text(text)
            
            if processed_text:  # 过滤空文本
                result_copy = result.copy()
                result_copy['text'] = processed_text
                result_copy['original_text'] = text
                enhanced_results.append(result_copy)
        
        return enhanced_results
    
    def _clean_code_text(self, text: str) -> str:
        """清理代码文本"""
        if not text:
            return ""
        
        # 移除明显的OCR错误
        # 1. 修复常见的OCR误识别
        replacements = {
            '０': '0', '１': '1', '２': '2', '３': '3', '４': '4',
            '５': '5', '６': '6', '７': '7', '８': '8', '９': '9',
            '（': '(', '）': ')',
            '｛': '{', '｝': '}',
            '［': '[', '］': ']',
            '；': ';', '：': ':',
            '，': ',', '。': '.',
            '"': '"', '"': '"',
            ''': "'", ''': "'",
        }
        
        cleaned_text = text
        for old, new in replacements.items():
            cleaned_text = cleaned_text.replace(old, new)
        
        return cleaned_text.strip()
    
    def _format_as_code(self, text_results: List[Dict]) -> str:
        """将识别结果格式化为代码"""
        if not text_results:
            return ""
        
        # 按行分组
        lines = self._group_text_by_lines(text_results)
        
        # 重构代码格式
        code_lines = []
        for line_texts in lines:
            # 检测缩进
            if line_texts:
                first_text = line_texts[0]
                indent_level = self._estimate_indent_level(first_text['bbox'][0])
                indent = "    " * indent_level  # 4个空格的缩进
                
                line_content = " ".join(text['text'] for text in line_texts)
                code_lines.append(indent + line_content)
        
        return "\n".join(code_lines)
    
    def _estimate_indent_level(self, x_position: int) -> int:
        """估算缩进级别"""
        # 简单的缩进估算，基于x坐标位置
        # 这里假设每个缩进级别大约对应30-40像素
        indent_pixel_size = 35
        return max(0, (x_position - 20) // indent_pixel_size)  # 减去左边距
    
    def _calculate_confidence_stats(self, text_results: List[Dict]) -> Dict:
        """计算置信度统计"""
        if not text_results:
            return {'average': 0.0, 'min': 0.0, 'max': 0.0, 'total_boxes': 0}
        
        confidences = [result['confidence'] for result in text_results]
        
        return {
            'average': np.mean(confidences),
            'min': np.min(confidences),
            'max': np.max(confidences),
            'total_boxes': len(confidences)
        }
    
    def batch_recognize_regions(self, regions: List[Dict]) -> List[Dict]:
        """批量识别多个区域的文本"""
        results = []
        
        for i, region in enumerate(regions):
            logger.info(f"PaddleOCR识别区域 {i+1}/{len(regions)}")
            
            if 'image_base64' in region:
                image_input = region['image_base64']
            else:
                logger.warning(f"区域 {i} 缺少图像数据")
                continue
            
            # 执行代码文本识别
            ocr_result = self.recognize_code_text(image_input)
            
            result = {
                'region_index': i,
                'region_type': region.get('region_type', 'unknown'),
                'ocr_result': ocr_result
            }
            
            results.append(result)
        
        return results
    
    def is_available(self) -> bool:
        """检查PaddleOCR是否可用"""
        return PADDLE_OCR_AVAILABLE and self.is_initialized