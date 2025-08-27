"""
代码提取器

从检测到的代码区域中提取具体的代码内容。
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional, Union
import base64
import io
from PIL import Image, ImageEnhance, ImageFilter

from app.utils.logger import get_logger

logger = get_logger(__name__)

class CodeExtractor:
    def __init__(self):
        """初始化代码提取器"""
        self.preprocessing_filters = self._setup_preprocessing_filters()
        
    def _setup_preprocessing_filters(self) -> Dict:
        """设置图像预处理滤镜"""
        return {
            'contrast_enhancement': 1.5,
            'brightness_adjustment': 1.1,
            'sharpening_kernel': np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]]),
            'noise_reduction': {
                'bilateral_d': 9,
                'sigma_color': 75,
                'sigma_space': 75
            }
        }
    
    def extract_code_from_region(self, 
                               image: np.ndarray, 
                               region_info: Dict,
                               enhance_for_ocr: bool = True) -> Dict:
        """
        从指定区域提取代码内容
        
        Args:
            image: 原始图像
            region_info: 区域信息（包含bbox等）
            enhance_for_ocr: 是否为OCR优化图像
            
        Returns:
            提取结果
        """
        try:
            bbox = region_info.get('bbox', (0, 0, image.shape[1], image.shape[0]))
            x, y, w, h = bbox
            
            # 提取区域
            region = image[y:y+h, x:x+w]
            
            if region.size == 0:
                return {'error': '无效的区域'}
            
            # 图像预处理
            processed_region = self._preprocess_for_extraction(region, enhance_for_ocr)
            
            # 分析代码结构
            structure_analysis = self._analyze_code_structure(processed_region)
            
            # 生成多种格式的图像用于不同的处理需求
            image_variants = self._generate_image_variants(region, processed_region)
            
            return {
                'original_region': self._image_to_base64(region),
                'processed_region': self._image_to_base64(processed_region),
                'image_variants': image_variants,
                'structure_analysis': structure_analysis,
                'extraction_metadata': {
                    'bbox': bbox,
                    'region_size': (w, h),
                    'enhancement_applied': enhance_for_ocr
                }
            }
            
        except Exception as e:
            logger.error(f"代码提取失败: {str(e)}")
            return {'error': str(e)}
    
    def _preprocess_for_extraction(self, region: np.ndarray, enhance_for_ocr: bool) -> np.ndarray:
        """为提取优化图像"""
        if not enhance_for_ocr:
            return region
        
        # 转换为PIL Image进行处理
        pil_image = Image.fromarray(region)
        
        # 1. 对比度增强
        enhancer = ImageEnhance.Contrast(pil_image)
        enhanced = enhancer.enhance(self.preprocessing_filters['contrast_enhancement'])
        
        # 2. 亮度调整
        brightness_enhancer = ImageEnhance.Brightness(enhanced)
        enhanced = brightness_enhancer.enhance(self.preprocessing_filters['brightness_adjustment'])
        
        # 3. 锐化
        enhanced = enhanced.filter(ImageFilter.SHARPEN)
        
        # 转换回numpy数组
        processed = np.array(enhanced)
        
        # 4. 降噪（使用OpenCV）
        if len(processed.shape) == 3:
            processed = cv2.bilateralFilter(
                processed,
                self.preprocessing_filters['noise_reduction']['bilateral_d'],
                self.preprocessing_filters['noise_reduction']['sigma_color'],
                self.preprocessing_filters['noise_reduction']['sigma_space']
            )
        
        return processed
    
    def _analyze_code_structure(self, region: np.ndarray) -> Dict:
        """分析代码结构"""
        height, width = region.shape[:2]
        
        # 转换为灰度图
        gray = cv2.cvtColor(region, cv2.COLOR_RGB2GRAY) if len(region.shape) == 3 else region
        
        # 1. 检测文本行
        text_lines = self._detect_text_lines(gray)
        
        # 2. 分析缩进结构
        indentation_analysis = self._analyze_indentation(text_lines, gray)
        
        # 3. 检测代码块
        code_blocks = self._detect_code_blocks(text_lines, indentation_analysis)
        
        # 4. 识别特殊元素
        special_elements = self._identify_special_elements(gray)
        
        return {
            'text_lines': text_lines,
            'indentation_analysis': indentation_analysis,
            'code_blocks': code_blocks,
            'special_elements': special_elements,
            'total_lines': len(text_lines),
            'structure_confidence': self._calculate_structure_confidence(text_lines, indentation_analysis)
        }
    
    def _detect_text_lines(self, gray_image: np.ndarray) -> List[Dict]:
        """检测文本行"""
        height, width = gray_image.shape
        
        # 使用形态学操作检测水平结构
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (width//20, 1))
        horizontal_lines = cv2.morphologyEx(gray_image, cv2.MORPH_CLOSE, horizontal_kernel)
        
        # 查找轮廓
        contours, _ = cv2.findContours(horizontal_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        text_lines = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # 过滤掉不合理的行
            if w > width * 0.05 and 8 <= h <= 50:
                # 计算该行的平均亮度来判断是否包含文本
                line_region = gray_image[y:y+h, x:x+w]
                avg_brightness = np.mean(line_region)
                brightness_std = np.std(line_region)
                
                text_lines.append({
                    'bbox': (x, y, w, h),
                    'y_center': y + h//2,
                    'avg_brightness': avg_brightness,
                    'brightness_std': brightness_std,
                    'has_text': brightness_std > 20  # 有文本的行通常亮度变化较大
                })
        
        # 按y坐标排序
        text_lines.sort(key=lambda line: line['y_center'])
        
        return text_lines
    
    def _analyze_indentation(self, text_lines: List[Dict], gray_image: np.ndarray) -> Dict:
        """分析缩进结构"""
        indentation_levels = []
        indentation_positions = []
        
        for line in text_lines:
            if not line.get('has_text', False):
                continue
                
            x, y, w, h = line['bbox']
            line_region = gray_image[y:y+h, :]
            
            # 从左侧开始找到第一个非背景像素
            first_text_pixel = self._find_first_text_pixel(line_region)
            
            if first_text_pixel is not None:
                indentation_positions.append(first_text_pixel)
            else:
                indentation_positions.append(0)
        
        # 量化缩进级别
        if indentation_positions:
            unique_positions = sorted(list(set(indentation_positions)))
            level_mapping = {pos: idx for idx, pos in enumerate(unique_positions)}
            indentation_levels = [level_mapping[pos] for pos in indentation_positions]
        
        return {
            'positions': indentation_positions,
            'levels': indentation_levels,
            'unique_levels': len(set(indentation_levels)) if indentation_levels else 0,
            'average_indent_size': self._calculate_average_indent_size(unique_positions) if len(unique_positions) > 1 else 0
        }
    
    def _find_first_text_pixel(self, line_region: np.ndarray) -> Optional[int]:
        """找到行中第一个文本像素的位置"""
        height, width = line_region.shape
        
        # 计算每列的平均亮度
        column_brightness = np.mean(line_region, axis=0)
        
        # 找到明显比背景亮的第一列
        background_brightness = np.mean(column_brightness[:min(50, width//4)])  # 假设左侧是背景
        threshold = background_brightness + 20  # 亮度阈值
        
        for col in range(width):
            if column_brightness[col] > threshold:
                return col
        
        return None
    
    def _calculate_average_indent_size(self, unique_positions: List[int]) -> int:
        """计算平均缩进大小"""
        if len(unique_positions) < 2:
            return 0
        
        differences = []
        for i in range(1, len(unique_positions)):
            diff = unique_positions[i] - unique_positions[i-1]
            if diff > 0:
                differences.append(diff)
        
        return int(np.mean(differences)) if differences else 0
    
    def _detect_code_blocks(self, text_lines: List[Dict], indentation_analysis: Dict) -> List[Dict]:
        """检测代码块"""
        if not indentation_analysis.get('levels'):
            return []
        
        code_blocks = []
        levels = indentation_analysis['levels']
        current_block = None
        
        for i, (line, level) in enumerate(zip(text_lines, levels)):
            if not line.get('has_text', False):
                continue
            
            if current_block is None:
                # 开始新的代码块
                current_block = {
                    'start_line': i,
                    'end_line': i,
                    'indent_level': level,
                    'lines': [line]
                }
            elif level >= current_block['indent_level']:
                # 继续当前代码块
                current_block['end_line'] = i
                current_block['lines'].append(line)
            else:
                # 结束当前代码块，开始新的
                if len(current_block['lines']) > 0:
                    code_blocks.append(current_block)
                
                current_block = {
                    'start_line': i,
                    'end_line': i,
                    'indent_level': level,
                    'lines': [line]
                }
        
        # 添加最后一个代码块
        if current_block and len(current_block['lines']) > 0:
            code_blocks.append(current_block)
        
        return code_blocks
    
    def _identify_special_elements(self, gray_image: np.ndarray) -> Dict:
        """识别特殊元素（如注释、字符串等）"""
        elements = {
            'comments': [],
            'strings': [],
            'brackets': [],
            'operators': []
        }
        
        # 这里可以使用更复杂的模式识别
        # 目前返回基础结构
        
        return elements
    
    def _calculate_structure_confidence(self, text_lines: List[Dict], indentation_analysis: Dict) -> float:
        """计算结构识别的置信度"""
        confidence_factors = []
        
        # 文本行数量因子
        if len(text_lines) > 0:
            line_factor = min(1.0, len(text_lines) / 10.0)
            confidence_factors.append(line_factor)
        
        # 缩进结构因子
        if indentation_analysis.get('unique_levels', 0) > 1:
            indent_factor = min(1.0, indentation_analysis['unique_levels'] / 5.0)
            confidence_factors.append(indent_factor)
        
        # 有效文本行比例
        text_lines_with_content = sum(1 for line in text_lines if line.get('has_text', False))
        if len(text_lines) > 0:
            content_ratio = text_lines_with_content / len(text_lines)
            confidence_factors.append(content_ratio)
        
        return np.mean(confidence_factors) if confidence_factors else 0.0
    
    def _generate_image_variants(self, original: np.ndarray, processed: np.ndarray) -> Dict:
        """生成不同用途的图像变体"""
        variants = {}
        
        # 1. 高对比度版本（用于OCR）
        high_contrast = self._create_high_contrast_version(processed)
        variants['high_contrast'] = self._image_to_base64(high_contrast)
        
        # 2. 灰度版本
        gray = cv2.cvtColor(processed, cv2.COLOR_RGB2GRAY) if len(processed.shape) == 3 else processed
        variants['grayscale'] = self._image_to_base64(gray)
        
        # 3. 二值化版本（用于文本检测）
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        variants['binary'] = self._image_to_base64(binary)
        
        # 4. 放大版本（提高OCR精度）
        height, width = original.shape[:2]
        if width < 1000:  # 只对小图像进行放大
            scale_factor = 2
            enlarged = cv2.resize(processed, (width * scale_factor, height * scale_factor), 
                                interpolation=cv2.INTER_CUBIC)
            variants['enlarged'] = self._image_to_base64(enlarged)
        
        return variants
    
    def _create_high_contrast_version(self, image: np.ndarray) -> np.ndarray:
        """创建高对比度版本"""
        if len(image.shape) == 3:
            # 转换为LAB色彩空间进行对比度增强
            lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
            l, a, b = cv2.split(lab)
            
            # 对L通道应用CLAHE（对比度限制自适应直方图均衡）
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            
            # 合并通道并转换回RGB
            lab = cv2.merge([l, a, b])
            enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
        else:
            # 灰度图像的对比度增强
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(image)
        
        return enhanced
    
    def _image_to_base64(self, image: np.ndarray) -> str:
        """将图像转换为base64字符串"""
        try:
            if len(image.shape) == 2:
                # 灰度图像
                pil_image = Image.fromarray(image, mode='L')
            else:
                # RGB图像
                pil_image = Image.fromarray(image)
            
            buffer = io.BytesIO()
            pil_image.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return f"data:image/png;base64,{img_base64}"
        
        except Exception as e:
            logger.error(f"图像转base64失败: {str(e)}")
            return ""
    
    def extract_multiple_regions(self, 
                                image: np.ndarray, 
                                regions_info: List[Dict],
                                enhance_for_ocr: bool = True) -> List[Dict]:
        """批量提取多个区域的代码"""
        results = []
        
        for i, region_info in enumerate(regions_info):
            logger.info(f"提取代码区域 {i+1}/{len(regions_info)}")
            
            result = self.extract_code_from_region(image, region_info, enhance_for_ocr)
            result['region_index'] = i
            result['region_type'] = region_info.get('type', 'unknown')
            
            results.append(result)
        
        return results
    
    def compare_extracted_regions(self, prev_extractions: List[Dict], curr_extractions: List[Dict]) -> Dict:
        """比较前后两次提取的结果"""
        if len(prev_extractions) != len(curr_extractions):
            return {
                'comparison_valid': False,
                'reason': 'Region count mismatch',
                'prev_count': len(prev_extractions),
                'curr_count': len(curr_extractions)
            }
        
        comparisons = []
        total_changes = 0
        
        for i, (prev, curr) in enumerate(zip(prev_extractions, curr_extractions)):
            if 'error' in prev or 'error' in curr:
                continue
            
            # 比较结构分析结果
            prev_structure = prev.get('structure_analysis', {})
            curr_structure = curr.get('structure_analysis', {})
            
            line_change = abs(prev_structure.get('total_lines', 0) - curr_structure.get('total_lines', 0))
            structure_change = abs(prev_structure.get('structure_confidence', 0) - curr_structure.get('structure_confidence', 0))
            
            region_comparison = {
                'region_index': i,
                'line_count_change': line_change,
                'structure_confidence_change': structure_change,
                'significant_change': line_change > 0 or structure_change > 0.1
            }
            
            if region_comparison['significant_change']:
                total_changes += 1
            
            comparisons.append(region_comparison)
        
        return {
            'comparison_valid': True,
            'region_comparisons': comparisons,
            'total_regions_changed': total_changes,
            'overall_change_detected': total_changes > 0
        }