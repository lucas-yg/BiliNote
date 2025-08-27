"""
IDE检测器

基于计算机视觉技术检测和识别各种代码编辑器和IDE界面。
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
import json
import os
from pathlib import Path

from app.utils.logger import get_logger

logger = get_logger(__name__)

class IDEDetector:
    def __init__(self):
        """初始化IDE检测器"""
        self.ide_signatures = self._load_ide_signatures()
        self.color_ranges = self._define_color_ranges()
        self.ui_patterns = self._define_ui_patterns()
        
    def _load_ide_signatures(self) -> Dict:
        """加载IDE特征签名"""
        return {
            'vscode': {
                'name': 'Visual Studio Code',
                'window_title_patterns': ['Visual Studio Code', 'Code', 'vscode'],
                'signature_colors': {
                    'activity_bar': [(42, 42, 42), (52, 52, 52)],
                    'side_bar': [(30, 30, 30), (40, 40, 40)],
                    'editor_background': [(30, 30, 30), (45, 45, 45)],
                    'status_bar': [(0, 122, 204), (23, 99, 171)]
                },
                'ui_layout': {
                    'activity_bar_width': (40, 60),
                    'side_bar_width': (200, 350),
                    'status_bar_height': (20, 30)
                },
                'distinctive_features': ['activity_bar', 'integrated_terminal', 'breadcrumb']
            },
            
            'pycharm': {
                'name': 'PyCharm',
                'window_title_patterns': ['PyCharm', 'JetBrains'],
                'signature_colors': {
                    'menu_bar': [(85, 85, 85), (95, 95, 95)],
                    'toolbar': [(75, 75, 75), (85, 85, 85)],
                    'project_tree': [(60, 63, 65), (70, 73, 75)],
                    'editor_background': [(43, 43, 43), (53, 53, 53)]
                },
                'ui_layout': {
                    'menu_bar_height': (25, 35),
                    'toolbar_height': (35, 45),
                    'project_tree_width': (200, 400)
                },
                'distinctive_features': ['project_tree', 'run_configurations', 'debugger_panel']
            },
            
            'sublime': {
                'name': 'Sublime Text',
                'window_title_patterns': ['Sublime Text', 'Sublime'],
                'signature_colors': {
                    'editor_background': [(39, 40, 34), (49, 50, 44)],
                    'sidebar': [(38, 39, 41), (48, 49, 51)],
                    'minimap': [(25, 26, 28), (35, 36, 38)]
                },
                'ui_layout': {
                    'sidebar_width': (150, 250),
                    'minimap_width': (80, 120)
                },
                'distinctive_features': ['minimap', 'goto_anything', 'multiple_cursors']
            },
            
            'atom': {
                'name': 'Atom',
                'window_title_patterns': ['Atom'],
                'signature_colors': {
                    'title_bar': [(40, 44, 52), (50, 54, 62)],
                    'tree_view': [(33, 37, 43), (43, 47, 53)],
                    'editor_background': [(40, 44, 52), (50, 54, 62)]
                },
                'ui_layout': {
                    'tree_view_width': (200, 300)
                },
                'distinctive_features': ['tree_view', 'package_manager']
            },
            
            'intellij': {
                'name': 'IntelliJ IDEA',
                'window_title_patterns': ['IntelliJ IDEA', 'IntelliJ'],
                'signature_colors': {
                    'menu_bar': [(85, 85, 85), (95, 95, 95)],
                    'project_view': [(60, 63, 65), (70, 73, 75)],
                    'editor_background': [(43, 43, 43), (53, 53, 53)]
                },
                'ui_layout': {
                    'project_view_width': (200, 350)
                },
                'distinctive_features': ['project_view', 'navigation_bar', 'tool_windows']
            },
            
            'vim': {
                'name': 'Vim',
                'window_title_patterns': ['vim', 'Vim', 'VIM'],
                'signature_colors': {
                    'background': [(0, 0, 0), (20, 20, 20)],
                    'text': [(200, 200, 200), (255, 255, 255)]
                },
                'ui_layout': {
                    'minimal_ui': True
                },
                'distinctive_features': ['command_line', 'status_line', 'minimal_ui']
            }
        }
    
    def _define_color_ranges(self) -> Dict:
        """定义颜色范围"""
        return {
            'dark_themes': {
                'background_range': [(0, 0, 0), (80, 80, 80)],
                'text_range': [(180, 180, 180), (255, 255, 255)]
            },
            'light_themes': {
                'background_range': [(200, 200, 200), (255, 255, 255)],
                'text_range': [(0, 0, 0), (100, 100, 100)]
            }
        }
    
    def _define_ui_patterns(self) -> Dict:
        """定义UI模式"""
        return {
            'sidebar_pattern': {
                'position': 'left',
                'width_ratio': (0.15, 0.35),
                'color_distinct_from_editor': True
            },
            'tabs_pattern': {
                'position': 'top',
                'height': (25, 40),
                'horizontal_divisions': True
            },
            'status_bar_pattern': {
                'position': 'bottom',
                'height': (18, 35),
                'distinct_color': True
            },
            'minimap_pattern': {
                'position': 'right',
                'width': (80, 150),
                'vertical_content': True
            }
        }
    
    def detect_ide(self, image: np.ndarray) -> Dict:
        """
        检测图像中的IDE
        
        Args:
            image: RGB格式的图像
            
        Returns:
            检测结果字典
        """
        try:
            height, width = image.shape[:2]
            
            # 分析图像的整体特征
            overall_features = self._analyze_overall_features(image)
            
            # 检测UI元素
            ui_elements = self._detect_ui_elements(image)
            
            # 分析颜色特征
            color_analysis = self._analyze_color_scheme(image)
            
            # 匹配IDE签名
            ide_matches = []
            for ide_name, signature in self.ide_signatures.items():
                match_score = self._calculate_ide_match_score(
                    overall_features, ui_elements, color_analysis, signature
                )
                
                if match_score > 0.3:  # 最低置信度阈值
                    ide_matches.append({
                        'ide_name': ide_name,
                        'display_name': signature['name'],
                        'confidence': match_score,
                        'matched_features': self._get_matched_features(signature, ui_elements, color_analysis)
                    })
            
            # 按置信度排序
            ide_matches.sort(key=lambda x: x['confidence'], reverse=True)
            
            # 准备结果
            best_match = ide_matches[0] if ide_matches else None
            
            return {
                'success': True,
                'detected_ide': best_match,
                'all_matches': ide_matches,
                'ui_elements': ui_elements,
                'color_analysis': color_analysis,
                'overall_features': overall_features
            }
            
        except Exception as e:
            logger.error(f"IDE检测失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _analyze_overall_features(self, image: np.ndarray) -> Dict:
        """分析图像的整体特征"""
        height, width = image.shape[:2]
        
        # 转换为灰度图分析结构
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        
        # 检测边缘
        edges = cv2.Canny(gray, 50, 150)
        
        # 查找主要的垂直和水平线条
        vertical_lines = self._detect_lines(edges, 'vertical')
        horizontal_lines = self._detect_lines(edges, 'horizontal')
        
        # 计算区域分割
        regions = self._identify_main_regions(image, vertical_lines, horizontal_lines)
        
        return {
            'image_size': (width, height),
            'vertical_divisions': len(vertical_lines),
            'horizontal_divisions': len(horizontal_lines),
            'main_regions': regions,
            'has_complex_layout': len(vertical_lines) > 2 or len(horizontal_lines) > 2
        }
    
    def _detect_lines(self, edges: np.ndarray, direction: str) -> List[int]:
        """检测主要的线条"""
        height, width = edges.shape
        
        if direction == 'vertical':
            # 检测垂直线
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=height//3, 
                                  minLineLength=height//2, maxLineGap=20)
            
            if lines is not None:
                vertical_positions = []
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    if abs(x1 - x2) < 10:  # 近似垂直线
                        vertical_positions.append((x1 + x2) // 2)
                
                # 聚类相近的位置
                return self._cluster_positions(vertical_positions, width // 20)
            
        else:  # horizontal
            # 检测水平线
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=width//3,
                                  minLineLength=width//2, maxLineGap=20)
            
            if lines is not None:
                horizontal_positions = []
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    if abs(y1 - y2) < 10:  # 近似水平线
                        horizontal_positions.append((y1 + y2) // 2)
                
                return self._cluster_positions(horizontal_positions, height // 20)
        
        return []
    
    def _cluster_positions(self, positions: List[int], threshold: int) -> List[int]:
        """聚类相近的位置"""
        if not positions:
            return []
        
        positions.sort()
        clusters = []
        current_cluster = [positions[0]]
        
        for pos in positions[1:]:
            if pos - current_cluster[-1] <= threshold:
                current_cluster.append(pos)
            else:
                clusters.append(int(np.mean(current_cluster)))
                current_cluster = [pos]
        
        clusters.append(int(np.mean(current_cluster)))
        return clusters
    
    def _identify_main_regions(self, image: np.ndarray, vertical_lines: List[int], horizontal_lines: List[int]) -> List[Dict]:
        """识别主要区域"""
        height, width = image.shape[:2]
        regions = []
        
        # 添加边界线
        v_lines = [0] + sorted(vertical_lines) + [width]
        h_lines = [0] + sorted(horizontal_lines) + [height]
        
        # 分析每个区域
        for i in range(len(v_lines) - 1):
            for j in range(len(h_lines) - 1):
                x1, x2 = v_lines[i], v_lines[i + 1]
                y1, y2 = h_lines[j], h_lines[j + 1]
                
                # 提取区域
                region = image[y1:y2, x1:x2]
                
                if region.size > 0:
                    region_features = self._analyze_region(region)
                    regions.append({
                        'bbox': (x1, y1, x2 - x1, y2 - y1),
                        'position': self._classify_region_position(x1, y1, x2, y2, width, height),
                        'features': region_features
                    })
        
        return regions
    
    def _analyze_region(self, region: np.ndarray) -> Dict:
        """分析单个区域的特征"""
        # 计算平均颜色
        avg_color = np.mean(region.reshape(-1, 3), axis=0)
        
        # 计算颜色方差（用于判断复杂度）
        color_variance = np.var(region.reshape(-1, 3), axis=0)
        
        # 检测是否包含文本（基于边缘密度）
        gray_region = cv2.cvtColor(region, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray_region, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        
        return {
            'avg_color': avg_color.tolist(),
            'color_variance': color_variance.tolist(),
            'edge_density': edge_density,
            'likely_contains_text': edge_density > 0.05,
            'is_uniform': np.mean(color_variance) < 100
        }
    
    def _classify_region_position(self, x1: int, y1: int, x2: int, y2: int, width: int, height: int) -> str:
        """分类区域位置"""
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        
        # 位置分类
        if x1 < width * 0.2:
            horizontal_pos = 'left'
        elif x2 > width * 0.8:
            horizontal_pos = 'right'
        else:
            horizontal_pos = 'center'
        
        if y1 < height * 0.1:
            vertical_pos = 'top'
        elif y2 > height * 0.9:
            vertical_pos = 'bottom'
        else:
            vertical_pos = 'middle'
        
        if horizontal_pos == 'center' and vertical_pos == 'middle':
            return 'main_editor'
        else:
            return f"{vertical_pos}_{horizontal_pos}"
    
    def _detect_ui_elements(self, image: np.ndarray) -> Dict:
        """检测UI元素"""
        height, width = image.shape[:2]
        elements = {}
        
        # 检测侧边栏
        elements['sidebar'] = self._detect_sidebar(image)
        
        # 检测状态栏
        elements['status_bar'] = self._detect_status_bar(image)
        
        # 检测标签页
        elements['tabs'] = self._detect_tabs(image)
        
        # 检测小地图
        elements['minimap'] = self._detect_minimap(image)
        
        # 检测菜单栏
        elements['menu_bar'] = self._detect_menu_bar(image)
        
        return elements
    
    def _detect_sidebar(self, image: np.ndarray) -> Dict:
        """检测侧边栏"""
        height, width = image.shape[:2]
        
        # 检查左侧区域
        left_strip_width = min(width // 4, 300)  # 最多检查1/4宽度
        left_strip = image[:, :left_strip_width]
        
        # 分析左侧区域的特征
        avg_color = np.mean(left_strip.reshape(-1, 3), axis=0)
        color_std = np.std(left_strip.reshape(-1, 3), axis=0)
        
        # 检测与主编辑器区域的颜色差异
        main_area = image[:, left_strip_width:width-left_strip_width//2]
        if main_area.size > 0:
            main_avg_color = np.mean(main_area.reshape(-1, 3), axis=0)
            color_diff = np.linalg.norm(avg_color - main_avg_color)
        else:
            color_diff = 0
        
        # 检测垂直分界线
        edge_column = left_strip_width - 1
        if edge_column < width - 1:
            left_edge = image[:, edge_column]
            right_edge = image[:, edge_column + 1]
            edge_strength = np.mean(np.abs(left_edge.astype(float) - right_edge.astype(float)))
        else:
            edge_strength = 0
        
        has_sidebar = (
            color_diff > 30 and  # 颜色有明显差异
            edge_strength > 20 and  # 有明显边界
            left_strip_width > 50  # 宽度合理
        )
        
        return {
            'detected': has_sidebar,
            'position': 'left',
            'width': left_strip_width if has_sidebar else 0,
            'color_diff': color_diff,
            'confidence': min(1.0, (color_diff + edge_strength) / 100)
        }
    
    def _detect_status_bar(self, image: np.ndarray) -> Dict:
        """检测状态栏"""
        height, width = image.shape[:2]
        
        # 检查底部区域
        bottom_strip_height = min(height // 10, 50)
        bottom_strip = image[height-bottom_strip_height:, :]
        
        if bottom_strip.size == 0:
            return {'detected': False}
        
        # 分析底部区域特征
        avg_color = np.mean(bottom_strip.reshape(-1, 3), axis=0)
        color_variance = np.var(bottom_strip.reshape(-1, 3))
        
        # 检测与上方区域的差异
        above_area = image[height-bottom_strip_height*3:height-bottom_strip_height, :]
        if above_area.size > 0:
            above_avg_color = np.mean(above_area.reshape(-1, 3), axis=0)
            color_diff = np.linalg.norm(avg_color - above_avg_color)
        else:
            color_diff = 0
        
        has_status_bar = (
            color_diff > 20 and  # 有颜色差异
            color_variance < 500 and  # 颜色相对均匀
            bottom_strip_height < height * 0.15  # 高度合理
        )
        
        return {
            'detected': has_status_bar,
            'position': 'bottom',
            'height': bottom_strip_height if has_status_bar else 0,
            'color_diff': color_diff,
            'confidence': min(1.0, color_diff / 50)
        }
    
    def _detect_tabs(self, image: np.ndarray) -> Dict:
        """检测标签页"""
        height, width = image.shape[:2]
        
        # 检查顶部区域
        top_strip_height = min(height // 8, 60)
        top_strip = image[:top_strip_height, :]
        
        if top_strip.size == 0:
            return {'detected': False}
        
        # 检测水平分割（标签页的特征）
        gray_strip = cv2.cvtColor(top_strip, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray_strip, 50, 150)
        
        # 查找垂直线（标签分隔符）
        vertical_lines = []
        for x in range(width):
            if np.sum(edges[:, x]) > top_strip_height * 0.3:
                vertical_lines.append(x)
        
        # 聚类相近的线条
        tab_separators = self._cluster_positions(vertical_lines, 20)
        
        has_tabs = len(tab_separators) >= 2  # 至少有两个分隔符才认为有标签页
        
        return {
            'detected': has_tabs,
            'position': 'top',
            'height': top_strip_height if has_tabs else 0,
            'tab_count': len(tab_separators) + 1 if has_tabs else 0,
            'confidence': min(1.0, len(tab_separators) / 5)
        }
    
    def _detect_minimap(self, image: np.ndarray) -> Dict:
        """检测小地图"""
        height, width = image.shape[:2]
        
        # 检查右侧区域
        right_strip_width = min(width // 8, 120)
        right_strip = image[:, width-right_strip_width:]
        
        if right_strip.size == 0:
            return {'detected': False}
        
        # 小地图的特征：高密度的小元素
        gray_strip = cv2.cvtColor(right_strip, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray_strip, 30, 100)
        edge_density = np.sum(edges > 0) / edges.size
        
        # 检测颜色多样性（代码的语法高亮）
        colors = right_strip.reshape(-1, 3)
        unique_colors = len(np.unique(colors.view(np.dtype((np.void, colors.dtype.itemsize*colors.shape[1])))))
        color_diversity = unique_colors / (right_strip_width * height)
        
        has_minimap = (
            edge_density > 0.1 and  # 高边缘密度
            color_diversity > 0.01 and  # 颜色多样性
            right_strip_width < width * 0.2  # 宽度合理
        )
        
        return {
            'detected': has_minimap,
            'position': 'right',
            'width': right_strip_width if has_minimap else 0,
            'edge_density': edge_density,
            'color_diversity': color_diversity,
            'confidence': min(1.0, (edge_density * 5 + color_diversity * 50))
        }
    
    def _detect_menu_bar(self, image: np.ndarray) -> Dict:
        """检测菜单栏"""
        height, width = image.shape[:2]
        
        # 检查顶部很小的区域
        menu_height = min(height // 15, 30)
        menu_strip = image[:menu_height, :]
        
        if menu_strip.size == 0:
            return {'detected': False}
        
        # 菜单栏通常颜色比较均匀
        color_variance = np.var(menu_strip.reshape(-1, 3))
        avg_brightness = np.mean(cv2.cvtColor(menu_strip, cv2.COLOR_RGB2GRAY))
        
        # 检测文本模式（菜单项）
        gray_strip = cv2.cvtColor(menu_strip, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray_strip, 50, 150)
        text_like_features = np.sum(edges > 0) / edges.size
        
        has_menu_bar = (
            color_variance < 200 and  # 颜色相对均匀
            text_like_features > 0.02 and  # 有文本特征
            menu_height < height * 0.1  # 高度合理
        )
        
        return {
            'detected': has_menu_bar,
            'position': 'top',
            'height': menu_height if has_menu_bar else 0,
            'confidence': min(1.0, text_like_features * 20)
        }
    
    def _analyze_color_scheme(self, image: np.ndarray) -> Dict:
        """分析配色方案"""
        # 计算整体亮度
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        avg_brightness = np.mean(gray)
        
        # 确定主题类型
        theme_type = 'dark' if avg_brightness < 127 else 'light'
        
        # 分析主要颜色
        pixels = image.reshape(-1, 3)
        
        # 使用K-means聚类找出主要颜色
        from sklearn.cluster import KMeans
        
        try:
            kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
            kmeans.fit(pixels[::100])  # 采样以提高性能
            dominant_colors = kmeans.cluster_centers_.astype(int)
        except:
            # 如果scikit-learn不可用，使用简化方法
            dominant_colors = self._simple_color_analysis(pixels)
        
        return {
            'theme_type': theme_type,
            'avg_brightness': avg_brightness,
            'dominant_colors': dominant_colors.tolist(),
            'color_distribution': self._analyze_color_distribution(pixels)
        }
    
    def _simple_color_analysis(self, pixels: np.ndarray) -> np.ndarray:
        """简化的颜色分析"""
        # 将颜色空间分割为网格
        bins = 8
        hist, _ = np.histogramdd(pixels, bins=[bins, bins, bins], range=[[0, 256], [0, 256], [0, 256]])
        
        # 找出最频繁的颜色
        top_indices = np.unravel_index(np.argsort(hist.ravel())[-5:], hist.shape)
        
        dominant_colors = []
        for i in range(5):
            r = top_indices[0][i] * 256 // bins + 128 // bins
            g = top_indices[1][i] * 256 // bins + 128 // bins  
            b = top_indices[2][i] * 256 // bins + 128 // bins
            dominant_colors.append([r, g, b])
        
        return np.array(dominant_colors)
    
    def _analyze_color_distribution(self, pixels: np.ndarray) -> Dict:
        """分析颜色分布"""
        # 分析RGB通道的分布
        r_mean, g_mean, b_mean = np.mean(pixels, axis=0)
        r_std, g_std, b_std = np.std(pixels, axis=0)
        
        return {
            'rgb_means': [float(r_mean), float(g_mean), float(b_mean)],
            'rgb_stds': [float(r_std), float(g_std), float(b_std)],
            'color_variance': float(np.var(pixels))
        }
    
    def _calculate_ide_match_score(self, overall_features: Dict, ui_elements: Dict, 
                                  color_analysis: Dict, ide_signature: Dict) -> float:
        """计算IDE匹配分数"""
        score = 0.0
        total_weight = 0.0
        
        # 1. 颜色匹配 (权重: 0.4)
        color_score = self._match_color_signature(color_analysis, ide_signature.get('signature_colors', {}))
        score += color_score * 0.4
        total_weight += 0.4
        
        # 2. UI元素匹配 (权重: 0.4)
        ui_score = self._match_ui_signature(ui_elements, ide_signature.get('distinctive_features', []))
        score += ui_score * 0.4
        total_weight += 0.4
        
        # 3. 布局匹配 (权重: 0.2)
        layout_score = self._match_layout_signature(overall_features, ide_signature.get('ui_layout', {}))
        score += layout_score * 0.2
        total_weight += 0.2
        
        return score / total_weight if total_weight > 0 else 0.0
    
    def _match_color_signature(self, color_analysis: Dict, color_signature: Dict) -> float:
        """匹配颜色签名"""
        if not color_signature:
            return 0.0
        
        dominant_colors = np.array(color_analysis.get('dominant_colors', []))
        if dominant_colors.size == 0:
            return 0.0
        
        match_count = 0
        total_signatures = len(color_signature)
        
        for component, color_range in color_signature.items():
            if len(color_range) >= 2:
                min_color = np.array(color_range[0])
                max_color = np.array(color_range[1])
                
                # 检查是否有任何主导色在这个范围内
                for color in dominant_colors:
                    if np.all(color >= min_color) and np.all(color <= max_color):
                        match_count += 1
                        break
        
        return match_count / max(total_signatures, 1)
    
    def _match_ui_signature(self, ui_elements: Dict, distinctive_features: List[str]) -> float:
        """匹配UI特征签名"""
        if not distinctive_features:
            return 0.5  # 如果没有特殊要求，返回中性分数
        
        match_count = 0
        
        for feature in distinctive_features:
            if feature == 'activity_bar' and ui_elements.get('sidebar', {}).get('detected', False):
                match_count += 1
            elif feature == 'minimap' and ui_elements.get('minimap', {}).get('detected', False):
                match_count += 1
            elif feature == 'status_bar' and ui_elements.get('status_bar', {}).get('detected', False):
                match_count += 1
            elif feature in ['project_tree', 'tree_view'] and ui_elements.get('sidebar', {}).get('detected', False):
                match_count += 1
            elif feature == 'menu_bar' and ui_elements.get('menu_bar', {}).get('detected', False):
                match_count += 1
        
        return match_count / len(distinctive_features)
    
    def _match_layout_signature(self, overall_features: Dict, layout_signature: Dict) -> float:
        """匹配布局签名"""
        if not layout_signature:
            return 0.5
        
        score = 0.0
        checks = 0
        
        # 检查是否有复杂布局要求
        if 'minimal_ui' in layout_signature:
            has_minimal = overall_features.get('vertical_divisions', 0) <= 1
            score += 1.0 if (layout_signature['minimal_ui'] == has_minimal) else 0.0
            checks += 1
        
        # 检查分割数量
        if overall_features.get('has_complex_layout', False):
            score += 0.7  # 复杂IDE通常有复杂布局
        else:
            score += 0.3  # 简单IDE可能有简单布局
        checks += 1
        
        return score / max(checks, 1)
    
    def _get_matched_features(self, ide_signature: Dict, ui_elements: Dict, color_analysis: Dict) -> List[str]:
        """获取匹配的特征列表"""
        matched_features = []
        
        # 检查UI特征匹配
        for feature in ide_signature.get('distinctive_features', []):
            if feature == 'minimap' and ui_elements.get('minimap', {}).get('detected', False):
                matched_features.append('minimap_detected')
            elif feature == 'status_bar' and ui_elements.get('status_bar', {}).get('detected', False):
                matched_features.append('status_bar_detected')
            # 可以添加更多特征检查
        
        # 检查主题匹配
        if color_analysis.get('theme_type') == 'dark':
            matched_features.append('dark_theme')
        else:
            matched_features.append('light_theme')
        
        return matched_features
    
    def is_available(self) -> bool:
        """检查IDE检测器是否可用"""
        return True  # 基础功能总是可用