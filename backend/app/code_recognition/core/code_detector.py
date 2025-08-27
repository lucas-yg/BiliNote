"""
代码检测器

使用计算机视觉技术检测代码编辑器界面中的各种元素。
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
import re
from PIL import Image, ImageFilter

from app.utils.logger import get_logger

logger = get_logger(__name__)

class CodeDetector:
    def __init__(self):
        """初始化代码检测器"""
        self.text_patterns = self._compile_text_patterns()
        self.ui_features = self._define_ui_features()
        
    def _compile_text_patterns(self) -> Dict:
        """编译用于检测代码特征的正则表达式"""
        return {
            'keywords': re.compile(r'\b(def|class|import|if|else|for|while|try|except|return|function|var|let|const|public|private|static)\b'),
            'operators': re.compile(r'[+\-*/%=<>!&|^~]'),
            'brackets': re.compile(r'[(){}\[\]]'),
            'strings': re.compile(r'["\'][^"\']*["\']'),
            'comments': re.compile(r'(//.*|#.*|/\*.*?\*/)'),
            'indentation': re.compile(r'^[\s\t]+'),
        }
    
    def _define_ui_features(self) -> Dict:
        """定义UI特征检测参数"""
        return {
            'line_numbers': {
                'position': 'left',
                'width_ratio': 0.05,  # 行号区域通常占编辑器宽度的5%
                'background_color_range': [(40, 40, 40), (80, 80, 80)]
            },
            'syntax_highlighting': {
                'keyword_colors': [(86, 156, 214), (197, 134, 192)],  # 蓝色和紫色
                'string_colors': [(214, 157, 133), (206, 145, 120)],   # 橙色系
                'comment_colors': [(106, 153, 85), (87, 166, 74)]      # 绿色系
            },
            'cursor': {
                'width': 1,
                'colors': [(255, 255, 255), (200, 200, 200)]
            }
        }
    
    def detect_code_elements(self, image: np.ndarray, region_bbox: Tuple[int, int, int, int]) -> Dict:
        """
        检测代码区域中的各种元素
        
        Args:
            image: 输入图像（RGB格式）
            region_bbox: 代码区域边界框 (x, y, width, height)
            
        Returns:
            检测到的代码元素信息
        """
        x, y, width, height = region_bbox
        code_region = image[y:y+height, x:x+width]
        
        elements = {
            'line_numbers': self._detect_line_numbers(code_region),
            'syntax_highlighting': self._detect_syntax_highlighting(code_region),
            'cursor_position': self._detect_cursor(code_region),
            'text_structure': self._analyze_text_structure(code_region),
            'scroll_indicators': self._detect_scroll_indicators(code_region)
        }
        
        return elements
    
    def _detect_line_numbers(self, region: np.ndarray) -> Dict:
        """检测行号区域"""
        height, width = region.shape[:2]
        
        # 检查左侧区域是否为行号
        left_strip_width = int(width * 0.1)  # 检查左侧10%区域
        left_strip = region[:, :left_strip_width]
        
        # 行号区域特征：
        # 1. 相对统一的背景色
        # 2. 垂直排列的数字模式
        # 3. 与主编辑器区域有明显分界线
        
        avg_color = np.mean(left_strip.reshape(-1, 3), axis=0)
        color_std = np.std(left_strip.reshape(-1, 3), axis=0)
        
        # 检测分界线
        edge_column = left_strip_width - 1
        if edge_column < width - 1:
            color_diff = np.abs(region[:, edge_column].astype(float) - region[:, edge_column + 1].astype(float))
            edge_strength = np.mean(color_diff)
        else:
            edge_strength = 0
        
        # 判断是否为行号区域
        has_line_numbers = (
            np.mean(color_std) < 30 and  # 背景色相对统一
            edge_strength > 20 and       # 有明显分界线
            avg_color[0] < 100          # 背景相对较暗
        )
        
        return {
            'detected': has_line_numbers,
            'bbox': (0, 0, left_strip_width, height) if has_line_numbers else None,
            'background_color': avg_color.tolist() if has_line_numbers else None,
            'confidence': 0.8 if has_line_numbers else 0.2
        }
    
    def _detect_syntax_highlighting(self, region: np.ndarray) -> Dict:
        """检测语法高亮"""
        height, width = region.shape[:2]
        
        # 统计图像中的主要颜色
        pixels = region.reshape(-1, 3)
        unique_colors, color_counts = np.unique(pixels, axis=0, return_counts=True)
        
        # 排除背景色（通常是最多的颜色）
        background_idx = np.argmax(color_counts)
        background_color = unique_colors[background_idx]
        
        # 计算颜色多样性
        non_background_pixels = pixels[~np.all(pixels == background_color, axis=1)]
        unique_non_bg_colors = np.unique(non_background_pixels, axis=0)
        
        # 语法高亮通常有多种特定颜色
        color_diversity = len(unique_non_bg_colors)
        
        # 检查是否有典型的语法高亮颜色
        syntax_colors_detected = []
        for color_name, color_ranges in self.ui_features['syntax_highlighting'].items():
            for color_range in color_ranges:
                color_array = np.array(color_range)
                distances = np.linalg.norm(unique_non_bg_colors - color_array, axis=1)
                if np.any(distances < 30):  # 颜色距离阈值
                    syntax_colors_detected.append(color_name)
                    break
        
        has_syntax_highlighting = color_diversity > 5 and len(syntax_colors_detected) > 0
        
        return {
            'detected': has_syntax_highlighting,
            'color_diversity': color_diversity,
            'detected_syntax_colors': syntax_colors_detected,
            'background_color': background_color.tolist(),
            'confidence': min(0.9, (color_diversity / 10) + (len(syntax_colors_detected) * 0.2))
        }
    
    def _detect_cursor(self, region: np.ndarray) -> Dict:
        """检测光标位置"""
        height, width = region.shape[:2]
        
        # 光标通常是一个垂直的亮色线条
        gray = cv2.cvtColor(region, cv2.COLOR_RGB2GRAY)
        
        # 查找垂直线条
        kernel = np.array([[-1], [2], [-1]], dtype=np.float32)
        vertical_edges = cv2.filter2D(gray, -1, kernel)
        
        # 查找亮色垂直线
        bright_vertical = (vertical_edges > 100) & (gray > 200)
        
        cursor_candidates = []
        contours, _ = cv2.findContours(bright_vertical.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            # 光标特征：宽度很小，高度相对较大
            if w <= 3 and h > 10:
                cursor_candidates.append({
                    'position': (x, y),
                    'size': (w, h),
                    'confidence': min(0.9, h / 20.0)
                })
        
        # 选择最可能的光标
        best_cursor = None
        if cursor_candidates:
            best_cursor = max(cursor_candidates, key=lambda c: c['confidence'])
        
        return {
            'detected': best_cursor is not None,
            'cursor': best_cursor,
            'all_candidates': cursor_candidates
        }
    
    def _analyze_text_structure(self, region: np.ndarray) -> Dict:
        """分析文本结构"""
        height, width = region.shape[:2]
        
        # 转换为灰度图进行文本分析
        gray = cv2.cvtColor(region, cv2.COLOR_RGB2GRAY)
        
        # 检测水平线条（可能的文本行）
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 1))
        horizontal_lines = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, horizontal_kernel)
        
        # 查找文本行
        contours, _ = cv2.findContours(horizontal_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        text_lines = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w > width * 0.1 and 5 < h < 50:  # 合理的文本行尺寸
                text_lines.append({
                    'bbox': (x, y, w, h),
                    'line_height': h
                })
        
        # 计算平均行高
        avg_line_height = np.mean([line['line_height'] for line in text_lines]) if text_lines else 0
        
        # 检测缩进模式
        indentation_levels = self._detect_indentation_levels(text_lines, region)
        
        return {
            'text_lines': text_lines,
            'line_count': len(text_lines),
            'average_line_height': avg_line_height,
            'indentation_levels': indentation_levels,
            'has_structured_text': len(text_lines) > 3 and avg_line_height > 0
        }
    
    def _detect_indentation_levels(self, text_lines: List[Dict], region: np.ndarray) -> List[int]:
        """检测代码缩进级别"""
        indentation_levels = []
        
        for line in text_lines:
            x, y, w, h = line['bbox']
            line_region = region[y:y+h, :]
            
            # 从左侧开始检测非背景像素的位置
            gray_line = cv2.cvtColor(line_region, cv2.COLOR_RGB2GRAY)
            
            # 查找每行第一个非背景像素的位置
            for col in range(gray_line.shape[1]):
                if np.any(gray_line[:, col] > 50):  # 假设背景较暗
                    indentation_levels.append(col)
                    break
            else:
                indentation_levels.append(0)
        
        return indentation_levels
    
    def _detect_scroll_indicators(self, region: np.ndarray) -> Dict:
        """检测滚动条指示器"""
        height, width = region.shape[:2]
        
        # 检查右侧区域是否有滚动条
        right_strip_width = 20
        right_strip = region[:, -right_strip_width:]
        
        # 滚动条特征：垂直的条状结构
        gray_strip = cv2.cvtColor(right_strip, cv2.COLOR_RGB2GRAY)
        
        # 查找垂直结构
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 10))
        vertical_structure = cv2.morphologyEx(gray_strip, cv2.MORPH_CLOSE, vertical_kernel)
        
        contours, _ = cv2.findContours(vertical_structure, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        scrollbar_detected = False
        scrollbar_position = None
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            # 滚动条特征：相对较窄但高度较大
            if w < 15 and h > height * 0.3:
                scrollbar_detected = True
                scrollbar_position = (width - right_strip_width + x, y, w, h)
                break
        
        return {
            'detected': scrollbar_detected,
            'position': scrollbar_position,
            'confidence': 0.7 if scrollbar_detected else 0.1
        }
    
    def detect_code_changes(self, prev_region: np.ndarray, curr_region: np.ndarray) -> Dict:
        """
        检测两个代码区域之间的变化
        
        Args:
            prev_region: 前一帧的代码区域
            curr_region: 当前帧的代码区域
            
        Returns:
            变化检测结果
        """
        if prev_region.shape != curr_region.shape:
            # 尺寸不同时需要调整
            min_height = min(prev_region.shape[0], curr_region.shape[0])
            min_width = min(prev_region.shape[1], curr_region.shape[1])
            prev_region = prev_region[:min_height, :min_width]
            curr_region = curr_region[:min_height, :min_width]
        
        # 计算差异图
        diff = cv2.absdiff(prev_region, curr_region)
        diff_gray = cv2.cvtColor(diff, cv2.COLOR_RGB2GRAY)
        
        # 阈值化差异
        _, threshold = cv2.threshold(diff_gray, 30, 255, cv2.THRESH_BINARY)
        
        # 查找变化区域
        contours, _ = cv2.findContours(threshold, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        change_regions = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 100:  # 过滤小的噪声变化
                x, y, w, h = cv2.boundingRect(contour)
                change_regions.append({
                    'bbox': (x, y, w, h),
                    'area': area,
                    'change_type': self._classify_change_type(prev_region[y:y+h, x:x+w], 
                                                           curr_region[y:y+h, x:x+w])
                })
        
        # 计算总体变化程度
        total_changed_pixels = np.sum(threshold > 0)
        total_pixels = threshold.shape[0] * threshold.shape[1]
        change_percentage = total_changed_pixels / total_pixels
        
        return {
            'change_regions': change_regions,
            'total_change_percentage': change_percentage,
            'significant_change': change_percentage > 0.05,  # 5%以上认为是显著变化
            'change_count': len(change_regions)
        }
    
    def _classify_change_type(self, prev_patch: np.ndarray, curr_patch: np.ndarray) -> str:
        """分类变化类型"""
        prev_brightness = np.mean(cv2.cvtColor(prev_patch, cv2.COLOR_RGB2GRAY))
        curr_brightness = np.mean(cv2.cvtColor(curr_patch, cv2.COLOR_RGB2GRAY))
        
        brightness_diff = curr_brightness - prev_brightness
        
        if abs(brightness_diff) < 10:
            return "color_change"  # 颜色变化（可能是语法高亮）
        elif brightness_diff > 10:
            return "text_addition"  # 文本增加
        else:
            return "text_deletion"  # 文本删除
    
    def estimate_font_size(self, region: np.ndarray) -> Dict:
        """估算字体大小"""
        # 分析文本结构来估算字体大小
        text_structure = self._analyze_text_structure(region)
        
        if text_structure['line_count'] > 0:
            avg_line_height = text_structure['average_line_height']
            # 字体大小通常比行高小一些
            estimated_font_size = max(8, int(avg_line_height * 0.8))
        else:
            estimated_font_size = 12  # 默认值
        
        return {
            'estimated_size': estimated_font_size,
            'confidence': 0.7 if text_structure['line_count'] > 3 else 0.3,
            'line_height': text_structure.get('average_line_height', 0)
        }