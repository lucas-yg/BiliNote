"""
视频帧分析器

专门分析编程视频帧，检测代码编辑器界面和代码区域。
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from PIL import Image
import base64
import io

from app.utils.logger import get_logger

logger = get_logger(__name__)

class FrameAnalyzer:
    def __init__(self):
        """初始化帧分析器"""
        self.ide_templates = self._load_ide_templates()
        
    def _load_ide_templates(self) -> Dict:
        """加载IDE模板特征"""
        return {
            'vscode': {
                'colors': {
                    'sidebar': [(42, 42, 42), (30, 30, 30)],  # VSCode 侧边栏颜色范围
                    'editor': [(30, 30, 30), (45, 45, 45)],   # 编辑器背景
                    'statusbar': [(0, 122, 204), (23, 99, 171)],  # 状态栏蓝色
                },
                'patterns': ['menu_bar', 'file_tree', 'editor_tabs', 'status_bar']
            },
            'pycharm': {
                'colors': {
                    'sidebar': [(60, 63, 65), (70, 73, 75)],
                    'editor': [(43, 43, 43), (60, 63, 65)],
                    'menubar': [(80, 80, 80), (90, 90, 90)],
                },
                'patterns': ['menu_bar', 'project_tree', 'editor_area', 'tool_window']
            },
            'sublime': {
                'colors': {
                    'sidebar': [(38, 39, 41), (48, 49, 51)],
                    'editor': [(35, 36, 38), (45, 46, 48)],
                    'minimap': [(25, 26, 28), (35, 36, 38)],
                },
                'patterns': ['file_tabs', 'minimap', 'status_bar']
            }
        }
        
    def analyze_frame(self, frame_path: str) -> Dict:
        """
        分析单个视频帧
        
        Args:
            frame_path: 帧图像文件路径
            
        Returns:
            分析结果字典，包含IDE类型、代码区域等信息
        """
        try:
            # 加载图像
            frame = cv2.imread(frame_path)
            if frame is None:
                logger.warning(f"无法加载帧图像: {frame_path}")
                return {'error': 'Failed to load frame'}
                
            # 转换为RGB格式
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # 分析结果
            analysis_result = {
                'frame_path': frame_path,
                'frame_size': frame_rgb.shape[:2],
                'ide_detected': None,
                'code_regions': [],
                'ui_elements': {},
                'confidence': 0.0
            }
            
            # 检测IDE类型
            ide_result = self._detect_ide_type(frame_rgb)
            analysis_result['ide_detected'] = ide_result['ide_type']
            analysis_result['confidence'] = ide_result['confidence']
            
            # 检测代码区域
            code_regions = self._detect_code_regions(frame_rgb, ide_result['ide_type'])
            analysis_result['code_regions'] = code_regions
            
            # 检测UI元素
            ui_elements = self._detect_ui_elements(frame_rgb, ide_result['ide_type'])
            analysis_result['ui_elements'] = ui_elements
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"帧分析失败 {frame_path}: {str(e)}")
            return {'error': str(e)}
    
    def _detect_ide_type(self, frame: np.ndarray) -> Dict:
        """
        检测IDE类型
        
        Args:
            frame: RGB格式的帧图像
            
        Returns:
            检测结果，包含IDE类型和置信度
        """
        best_match = {'ide_type': None, 'confidence': 0.0}
        
        for ide_name, template in self.ide_templates.items():
            confidence = self._calculate_ide_similarity(frame, template)
            if confidence > best_match['confidence']:
                best_match = {'ide_type': ide_name, 'confidence': confidence}
        
        # 如果置信度低于阈值，标记为未知
        if best_match['confidence'] < 0.3:
            best_match['ide_type'] = 'unknown'
            
        return best_match
    
    def _calculate_ide_similarity(self, frame: np.ndarray, template: Dict) -> float:
        """
        计算帧与IDE模板的相似度
        
        Args:
            frame: RGB格式的帧图像
            template: IDE模板信息
            
        Returns:
            相似度分数 (0-1)
        """
        height, width = frame.shape[:2]
        score = 0.0
        
        # 颜色特征匹配
        color_score = self._match_color_features(frame, template.get('colors', {}))
        score += color_score * 0.6
        
        # 布局特征匹配
        layout_score = self._match_layout_features(frame, template.get('patterns', []))
        score += layout_score * 0.4
        
        return min(score, 1.0)
    
    def _match_color_features(self, frame: np.ndarray, color_template: Dict) -> float:
        """匹配颜色特征"""
        if not color_template:
            return 0.0
            
        height, width = frame.shape[:2]
        total_score = 0.0
        feature_count = 0
        
        # 检查侧边栏区域颜色
        if 'sidebar' in color_template:
            sidebar_region = frame[:, :width//6]  # 假设侧边栏占宽度的1/6
            sidebar_score = self._check_color_range(sidebar_region, color_template['sidebar'])
            total_score += sidebar_score
            feature_count += 1
        
        # 检查编辑器区域颜色
        if 'editor' in color_template:
            editor_region = frame[:, width//6:width*5//6]  # 编辑器主区域
            editor_score = self._check_color_range(editor_region, color_template['editor'])
            total_score += editor_score
            feature_count += 1
        
        # 检查状态栏区域颜色
        if 'statusbar' in color_template:
            status_region = frame[height*9//10:, :]  # 底部状态栏区域
            status_score = self._check_color_range(status_region, color_template['statusbar'])
            total_score += status_score
            feature_count += 1
        
        return total_score / max(feature_count, 1)
    
    def _check_color_range(self, region: np.ndarray, color_range: List[Tuple]) -> float:
        """检查区域颜色是否在指定范围内"""
        if len(color_range) < 2:
            return 0.0
            
        min_color = np.array(color_range[0])
        max_color = np.array(color_range[1])
        
        # 计算区域内像素在颜色范围内的比例
        mask = np.all((region >= min_color) & (region <= max_color), axis=2)
        return np.mean(mask)
    
    def _match_layout_features(self, frame: np.ndarray, patterns: List[str]) -> float:
        """匹配布局特征"""
        # 这里可以实现更复杂的模式匹配
        # 目前返回基础分数
        return 0.5 if patterns else 0.0
    
    def _detect_code_regions(self, frame: np.ndarray, ide_type: Optional[str]) -> List[Dict]:
        """
        检测代码区域
        
        Args:
            frame: RGB格式的帧图像
            ide_type: 检测到的IDE类型
            
        Returns:
            代码区域列表，每个区域包含坐标和类型信息
        """
        regions = []
        height, width = frame.shape[:2]
        
        if ide_type == 'vscode':
            # VSCode布局：侧边栏 + 编辑器区域
            editor_region = {
                'type': 'editor',
                'bbox': (width//6, 40, width*5//6, height-30),  # x, y, width, height
                'confidence': 0.8
            }
            regions.append(editor_region)
            
        elif ide_type == 'pycharm':
            # PyCharm布局
            editor_region = {
                'type': 'editor', 
                'bbox': (width//5, 60, width*4//5, height-50),
                'confidence': 0.8
            }
            regions.append(editor_region)
            
        elif ide_type == 'sublime':
            # Sublime Text布局
            editor_region = {
                'type': 'editor',
                'bbox': (width//8, 30, width*7//8, height-20),
                'confidence': 0.8
            }
            regions.append(editor_region)
            
        else:
            # 未知IDE，使用通用检测方法
            generic_regions = self._detect_generic_code_regions(frame)
            regions.extend(generic_regions)
        
        return regions
    
    def _detect_generic_code_regions(self, frame: np.ndarray) -> List[Dict]:
        """通用代码区域检测方法"""
        regions = []
        height, width = frame.shape[:2]
        
        # 使用启发式方法检测可能的代码区域
        # 1. 检测深色背景区域（通常是代码编辑器）
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        dark_mask = gray < 80  # 深色阈值
        
        # 2. 查找大的连通区域
        contours, _ = cv2.findContours(dark_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > (width * height * 0.1):  # 区域要足够大
                x, y, w, h = cv2.boundingRect(contour)
                regions.append({
                    'type': 'editor',
                    'bbox': (x, y, w, h),
                    'confidence': 0.6
                })
        
        return regions
    
    def _detect_ui_elements(self, frame: np.ndarray, ide_type: Optional[str]) -> Dict:
        """检测UI元素"""
        elements = {}
        height, width = frame.shape[:2]
        
        # 检测文件标签区域
        tab_region = frame[0:50, :]  # 顶部区域
        elements['tabs'] = {
            'bbox': (0, 0, width, 50),
            'detected': self._has_tab_pattern(tab_region)
        }
        
        # 检测侧边栏
        sidebar_region = frame[:, 0:width//6]
        elements['sidebar'] = {
            'bbox': (0, 0, width//6, height),
            'detected': self._has_sidebar_pattern(sidebar_region)
        }
        
        # 检测状态栏
        statusbar_region = frame[height*9//10:, :]
        elements['statusbar'] = {
            'bbox': (0, height*9//10, width, height//10),
            'detected': self._has_statusbar_pattern(statusbar_region)
        }
        
        return elements
    
    def _has_tab_pattern(self, region: np.ndarray) -> bool:
        """检测是否有标签页模式"""
        # 简单的启发式检测：查找水平分割线
        gray = cv2.cvtColor(region, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, minLineLength=30)
        return lines is not None and len(lines) > 0
    
    def _has_sidebar_pattern(self, region: np.ndarray) -> bool:
        """检测是否有侧边栏模式"""
        # 检测垂直结构
        height, width = region.shape[:2]
        if width < 50:  # 太窄不太可能是侧边栏
            return False
            
        # 计算平均亮度，侧边栏通常比较暗
        gray = cv2.cvtColor(region, cv2.COLOR_RGB2GRAY)
        avg_brightness = np.mean(gray)
        return avg_brightness < 100  # 相对较暗
    
    def _has_statusbar_pattern(self, region: np.ndarray) -> bool:
        """检测是否有状态栏模式"""
        height, width = region.shape[:2]
        if height < 10 or height > 50:  # 状态栏高度通常在这个范围
            return False
        
        # 状态栏通常有统一的背景色
        colors = region.reshape(-1, 3)
        unique_colors = len(np.unique(colors.view(np.dtype((np.void, colors.dtype.itemsize*colors.shape[1])))))
        return unique_colors < 20  # 颜色相对单一
    
    def extract_code_content(self, frame_path: str, regions: List[Dict]) -> List[Dict]:
        """
        从指定区域提取代码内容的图像
        
        Args:
            frame_path: 帧图像路径
            regions: 代码区域列表
            
        Returns:
            提取的代码区域图像列表
        """
        extracted_regions = []
        
        try:
            frame = cv2.imread(frame_path)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            for region in regions:
                bbox = region['bbox']
                x, y, w, h = bbox
                
                # 提取区域图像
                region_img = frame_rgb[y:y+h, x:x+w]
                
                # 转换为PIL Image
                pil_img = Image.fromarray(region_img)
                
                # 转换为base64
                buffer = io.BytesIO()
                pil_img.save(buffer, format='PNG')
                img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                
                extracted_regions.append({
                    'region_type': region['type'],
                    'bbox': bbox,
                    'confidence': region['confidence'],
                    'image_base64': f"data:image/png;base64,{img_base64}",
                    'image_size': region_img.shape[:2]
                })
                
        except Exception as e:
            logger.error(f"提取代码区域失败 {frame_path}: {str(e)}")
            
        return extracted_regions

    def batch_analyze_frames(self, frame_paths: List[str]) -> List[Dict]:
        """
        批量分析多个视频帧
        
        Args:
            frame_paths: 帧图像路径列表
            
        Returns:
            分析结果列表
        """
        results = []
        
        for frame_path in frame_paths:
            logger.info(f"分析帧: {frame_path}")
            result = self.analyze_frame(frame_path)
            results.append(result)
            
        return results