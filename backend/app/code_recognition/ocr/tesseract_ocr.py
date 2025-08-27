"""
Tesseract OCR集成服务

使用Tesseract OCR进行文本识别，作为PaddleOCR的备选方案。
"""

import numpy as np
from typing import List, Dict, Tuple, Optional, Union
import cv2
import base64
import io
import re
from PIL import Image

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

from app.utils.logger import get_logger

logger = get_logger(__name__)

class TesseractOCRService:
    def __init__(self, tesseract_cmd: Optional[str] = None, lang: str = 'eng'):
        """
        初始化Tesseract OCR服务
        
        Args:
            tesseract_cmd: Tesseract可执行文件路径
            lang: 语言设置，默认为英文
        """
        self.lang = lang
        self.is_initialized = False
        
        if not TESSERACT_AVAILABLE:
            logger.warning("pytesseract未安装，无法使用Tesseract OCR服务")
            return
        
        # 设置Tesseract路径
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        
        self._initialize_service()
    
    def _initialize_service(self):
        """初始化OCR服务"""
        try:
            # 测试Tesseract是否可用
            version = pytesseract.get_tesseract_version()
            self.is_initialized = True
            logger.info(f"Tesseract OCR初始化成功，版本: {version}")
        except Exception as e:
            logger.error(f"Tesseract OCR初始化失败: {str(e)}")
            self.is_initialized = False
    
    def recognize_text(self, image: Union[np.ndarray, str], config: Optional[str] = None) -> Dict:
        """
        识别图像中的文本
        
        Args:
            image: numpy数组格式的图像或base64编码的图像字符串
            config: Tesseract配置参数
            
        Returns:
            识别结果字典
        """
        if not self.is_initialized:
            return {
                'success': False,
                'error': 'Tesseract OCR未正确初始化',
                'text': '',
                'detailed_results': []
            }
        
        try:
            # 处理输入图像
            pil_image = self._process_input_image(image)
            if pil_image is None:
                return {
                    'success': False,
                    'error': '图像处理失败',
                    'text': '',
                    'detailed_results': []
                }
            
            # 设置默认配置
            if config is None:
                config = self._get_default_config()
            
            # 执行OCR识别
            text_result = pytesseract.image_to_string(pil_image, lang=self.lang, config=config)
            
            # 获取详细结果（包含坐标和置信度）
            detailed_data = pytesseract.image_to_data(pil_image, lang=self.lang, config=config, output_type=pytesseract.Output.DICT)
            
            # 处理详细结果
            detailed_results = self._process_detailed_results(detailed_data)
            
            return {
                'success': True,
                'text': text_result.strip(),
                'detailed_results': detailed_results,
                'total_words': len(detailed_results),
                'confidence_stats': self._calculate_confidence_stats(detailed_results)
            }
            
        except Exception as e:
            logger.error(f"Tesseract OCR文本识别失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'text': '',
                'detailed_results': []
            }
    
    def _process_input_image(self, image: Union[np.ndarray, str]) -> Optional[Image.Image]:
        """处理输入图像"""
        try:
            if isinstance(image, str):
                # 处理base64编码的图像
                if image.startswith('data:image'):
                    image = image.split(',')[1]
                
                img_data = base64.b64decode(image)
                pil_image = Image.open(io.BytesIO(img_data))
            else:
                # numpy数组格式的图像
                if len(image.shape) == 3:
                    # 确保是RGB格式
                    if image.shape[2] == 3:
                        # 假设输入是BGR格式（OpenCV默认）
                        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    else:
                        image_rgb = image
                    pil_image = Image.fromarray(image_rgb)
                else:
                    # 灰度图像
                    pil_image = Image.fromarray(image, mode='L')
            
            return pil_image
            
        except Exception as e:
            logger.error(f"图像处理失败: {str(e)}")
            return None
    
    def _get_default_config(self) -> str:
        """获取默认的Tesseract配置"""
        # 优化代码识别的配置参数
        return r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
    
    def _get_code_config(self) -> str:
        """获取专门用于代码识别的配置"""
        # PSM 6: 统一的文本块
        # OEM 3: 默认，基于LSTM OCR引擎
        return r'--oem 3 --psm 6'
    
    def _process_detailed_results(self, data: Dict) -> List[Dict]:
        """处理详细识别结果"""
        results = []
        
        n_boxes = len(data['text'])
        for i in range(n_boxes):
            if int(data['conf'][i]) > 0:  # 过滤置信度为0的结果
                text = data['text'][i].strip()
                if text:  # 过滤空文本
                    results.append({
                        'text': text,
                        'confidence': float(data['conf'][i]) / 100.0,  # 转换为0-1范围
                        'bbox': (
                            int(data['left'][i]),
                            int(data['top'][i]),
                            int(data['width'][i]),
                            int(data['height'][i])
                        ),
                        'word_num': int(data['word_num'][i]),
                        'line_num': int(data['line_num'][i]),
                        'par_num': int(data['par_num'][i])
                    })
        
        return results
    
    def _calculate_confidence_stats(self, results: List[Dict]) -> Dict:
        """计算置信度统计"""
        if not results:
            return {'average': 0.0, 'min': 0.0, 'max': 0.0, 'total_words': 0}
        
        confidences = [result['confidence'] for result in results]
        
        return {
            'average': np.mean(confidences),
            'min': np.min(confidences),
            'max': np.max(confidences),
            'total_words': len(confidences)
        }
    
    def recognize_code_text(self, image: Union[np.ndarray, str], enhance_image: bool = True) -> Dict:
        """
        专门用于识别代码文本
        
        Args:
            image: 输入图像
            enhance_image: 是否对图像进行增强处理
            
        Returns:
            代码文本识别结果
        """
        try:
            # 图像预处理
            if enhance_image:
                processed_image = self._enhance_for_code_recognition(image)
            else:
                processed_image = self._process_input_image(image)
            
            if processed_image is None:
                return {
                    'success': False,
                    'error': '图像处理失败',
                    'code_text': '',
                    'lines': []
                }
            
            # 使用代码专用配置
            config = self._get_code_config()
            
            # 执行识别
            ocr_result = self.recognize_text(processed_image, config)
            
            if not ocr_result['success']:
                return ocr_result
            
            # 后处理：将结果格式化为代码
            formatted_result = self._format_as_code_text(ocr_result)
            
            return {
                'success': True,
                'code_text': formatted_result['code_text'],
                'lines': formatted_result['lines'],
                'raw_text': ocr_result['text'],
                'detailed_results': ocr_result['detailed_results'],
                'confidence_stats': ocr_result['confidence_stats']
            }
            
        except Exception as e:
            logger.error(f"代码文本识别失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'code_text': '',
                'lines': []
            }
    
    def _enhance_for_code_recognition(self, image: Union[np.ndarray, str]) -> Optional[Image.Image]:
        """为代码识别增强图像"""
        try:
            # 先转换为PIL Image
            if isinstance(image, str):
                pil_image = self._process_input_image(image)
            else:
                # 转换numpy数组为PIL Image
                if len(image.shape) == 3:
                    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(image_rgb)
                else:
                    pil_image = Image.fromarray(image, mode='L')
            
            if pil_image is None:
                return None
            
            # 转换为numpy数组进行处理
            img_array = np.array(pil_image)
            
            if len(img_array.shape) == 3:
                # 转换为灰度图
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # 1. 自适应阈值处理
            binary = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            
            # 2. 形态学操作去除噪声
            kernel = np.ones((1, 1), np.uint8)
            cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            
            # 3. 反色处理（如果背景是暗色）
            if np.mean(cleaned) < 127:
                cleaned = cv2.bitwise_not(cleaned)
            
            # 4. 放大图像提高识别精度
            height, width = cleaned.shape
            if width < 1000:  # 只对小图像进行放大
                scale_factor = 2
                cleaned = cv2.resize(cleaned, (width * scale_factor, height * scale_factor), 
                                   interpolation=cv2.INTER_CUBIC)
            
            # 转换回PIL Image
            enhanced_pil = Image.fromarray(cleaned, mode='L')
            
            return enhanced_pil
            
        except Exception as e:
            logger.error(f"图像增强失败: {str(e)}")
            return self._process_input_image(image)
    
    def _format_as_code_text(self, ocr_result: Dict) -> Dict:
        """将OCR结果格式化为代码文本"""
        detailed_results = ocr_result.get('detailed_results', [])
        
        if not detailed_results:
            return {'code_text': '', 'lines': []}
        
        # 按行分组
        lines_dict = {}
        for result in detailed_results:
            line_num = result['line_num']
            if line_num not in lines_dict:
                lines_dict[line_num] = []
            lines_dict[line_num].append(result)
        
        # 处理每一行
        formatted_lines = []
        for line_num in sorted(lines_dict.keys()):
            line_results = sorted(lines_dict[line_num], key=lambda x: x['bbox'][0])  # 按x坐标排序
            
            # 重构行文本
            line_text = self._reconstruct_line_text(line_results)
            
            # 估算缩进
            first_word = line_results[0] if line_results else None
            indent_level = self._estimate_indent_level(first_word['bbox'][0]) if first_word else 0
            
            formatted_line = {
                'line_number': line_num,
                'text': line_text,
                'indent_level': indent_level,
                'formatted_text': '    ' * indent_level + line_text,  # 4空格缩进
                'confidence': np.mean([r['confidence'] for r in line_results])
            }
            
            formatted_lines.append(formatted_line)
        
        # 生成最终代码文本
        code_text = '\\n'.join(line['formatted_text'] for line in formatted_lines)
        
        return {
            'code_text': code_text,
            'lines': formatted_lines
        }
    
    def _reconstruct_line_text(self, line_results: List[Dict]) -> str:
        """重构单行文本"""
        if not line_results:
            return ""
        
        # 按x坐标排序
        sorted_results = sorted(line_results, key=lambda x: x['bbox'][0])
        
        # 检测单词间距，插入适当的空格
        reconstructed = []
        for i, result in enumerate(sorted_results):
            if i == 0:
                reconstructed.append(result['text'])
            else:
                prev_result = sorted_results[i-1]
                prev_right = prev_result['bbox'][0] + prev_result['bbox'][2]
                curr_left = result['bbox'][0]
                
                gap = curr_left - prev_right
                
                # 根据间距判断是否需要添加空格
                if gap > 10:  # 像素间距阈值
                    num_spaces = max(1, gap // 15)  # 估算空格数量
                    reconstructed.append(' ' * min(num_spaces, 4))  # 限制最多4个空格
                
                reconstructed.append(result['text'])
        
        return ''.join(reconstructed)
    
    def _estimate_indent_level(self, x_position: int) -> int:
        """估算缩进级别"""
        # 假设每个缩进级别约为30像素
        indent_pixel_size = 30
        return max(0, (x_position - 10) // indent_pixel_size)
    
    def recognize_with_preprocessing_variants(self, image: Union[np.ndarray, str]) -> Dict:
        """
        使用多种预处理方式识别文本，选择最佳结果
        
        Args:
            image: 输入图像
            
        Returns:
            最佳识别结果
        """
        if not self.is_initialized:
            return {
                'success': False,
                'error': 'Tesseract OCR未正确初始化'
            }
        
        preprocessing_variants = [
            ('original', lambda img: img),
            ('enhanced', lambda img: self._enhance_for_code_recognition(img)),
            ('binary', lambda img: self._apply_binary_threshold(img)),
            ('contrast', lambda img: self._enhance_contrast(img))
        ]
        
        best_result = None
        best_confidence = 0.0
        
        for variant_name, preprocess_func in preprocessing_variants:
            try:
                logger.info(f"尝试预处理方式: {variant_name}")
                
                processed_image = preprocess_func(image)
                if processed_image is None:
                    continue
                
                result = self.recognize_code_text(processed_image, enhance_image=False)
                
                if result['success']:
                    avg_confidence = result['confidence_stats']['average']
                    
                    if avg_confidence > best_confidence:
                        best_confidence = avg_confidence
                        best_result = result
                        best_result['best_preprocessing'] = variant_name
                
            except Exception as e:
                logger.warning(f"预处理方式 {variant_name} 失败: {str(e)}")
                continue
        
        if best_result is None:
            return {
                'success': False,
                'error': '所有预处理方式都失败了'
            }
        
        return best_result
    
    def _apply_binary_threshold(self, image: Union[np.ndarray, str]) -> Optional[Image.Image]:
        """应用二值化阈值"""
        try:
            pil_image = self._process_input_image(image)
            if pil_image is None:
                return None
            
            img_array = np.array(pil_image.convert('L'))
            
            # 使用OTSU阈值
            _, binary = cv2.threshold(img_array, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            return Image.fromarray(binary, mode='L')
            
        except Exception as e:
            logger.error(f"二值化处理失败: {str(e)}")
            return None
    
    def _enhance_contrast(self, image: Union[np.ndarray, str]) -> Optional[Image.Image]:
        """增强对比度"""
        try:
            pil_image = self._process_input_image(image)
            if pil_image is None:
                return None
            
            # 转换为数组
            img_array = np.array(pil_image.convert('L'))
            
            # 对比度拉伸
            min_val, max_val = np.percentile(img_array, [2, 98])
            enhanced = np.clip((img_array - min_val) / (max_val - min_val) * 255, 0, 255).astype(np.uint8)
            
            return Image.fromarray(enhanced, mode='L')
            
        except Exception as e:
            logger.error(f"对比度增强失败: {str(e)}")
            return None
    
    def batch_recognize_regions(self, regions: List[Dict]) -> List[Dict]:
        """批量识别多个区域的文本"""
        results = []
        
        for i, region in enumerate(regions):
            logger.info(f"Tesseract OCR识别区域 {i+1}/{len(regions)}")
            
            if 'image_base64' in region:
                image_input = region['image_base64']
            else:
                logger.warning(f"区域 {i} 缺少图像数据")
                continue
            
            # 使用多种预处理方式获取最佳结果
            ocr_result = self.recognize_with_preprocessing_variants(image_input)
            
            result = {
                'region_index': i,
                'region_type': region.get('region_type', 'unknown'),
                'ocr_result': ocr_result
            }
            
            results.append(result)
        
        return results
    
    def is_available(self) -> bool:
        """检查Tesseract OCR是否可用"""
        return TESSERACT_AVAILABLE and self.is_initialized