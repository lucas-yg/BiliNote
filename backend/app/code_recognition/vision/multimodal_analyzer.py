"""
多模态视觉分析器

集成GPT-4V、Claude Vision等多模态AI模型，对代码截图进行智能分析。
"""

import base64
import json
from typing import List, Dict, Optional, Union
import numpy as np
from PIL import Image
import io

from app.gpt.universal_gpt import UniversalGPT
from app.utils.logger import get_logger

logger = get_logger(__name__)

class MultimodalAnalyzer:
    def __init__(self):
        """初始化多模态分析器"""
        self.gpt_service = UniversalGPT()
        self.analysis_prompts = self._load_analysis_prompts()
        
    def _load_analysis_prompts(self) -> Dict[str, str]:
        """加载分析提示词"""
        return {
            'code_analysis': """
You are an expert code analyst. Please analyze the provided screenshot of code and provide the following information:

1. **Programming Language**: Identify the programming language shown in the image
2. **Code Structure**: Describe the overall structure (functions, classes, variables, etc.)
3. **Key Components**: List the main code elements visible (imports, function definitions, variable assignments, etc.)
4. **Code Content**: Extract the actual code text as accurately as possible
5. **Syntax Elements**: Identify syntax highlighting, indentation patterns, comments
6. **IDE/Editor**: Identify the code editor or IDE being used
7. **Code Quality**: Comment on code organization and structure

Please format your response as a JSON object with the following structure:
{
    "programming_language": "detected language",
    "ide_editor": "detected IDE/editor",
    "code_structure": {
        "functions": ["list of function names"],
        "classes": ["list of class names"],
        "imports": ["list of import statements"],
        "variables": ["list of variable names"]
    },
    "extracted_code": "actual code content with proper formatting",
    "syntax_elements": {
        "has_syntax_highlighting": true/false,
        "indentation_type": "spaces/tabs",
        "indentation_level": "number of spaces/tabs per level",
        "has_line_numbers": true/false
    },
    "code_quality": {
        "organization_score": "1-10",
        "readability_score": "1-10",
        "comments": "analysis comments"
    }
}
""",
            
            'ide_detection': """
You are an expert in identifying code editors and IDEs. Please analyze the provided screenshot and identify:

1. **IDE/Editor Name**: The specific code editor or IDE shown
2. **UI Elements**: Describe visible UI components (sidebar, tabs, status bar, etc.)
3. **Theme/Appearance**: Describe the color scheme and visual theme
4. **Visible Features**: List any visible features or tools
5. **Layout**: Describe the overall layout and arrangement

Respond in JSON format:
{
    "ide_name": "detected IDE name",
    "confidence": "confidence level (0-100)",
    "ui_elements": {
        "sidebar": true/false,
        "file_tabs": true/false,
        "status_bar": true/false,
        "menu_bar": true/false,
        "minimap": true/false,
        "line_numbers": true/false
    },
    "theme": {
        "name": "theme name if identifiable",
        "type": "dark/light",
        "background_color": "dominant background color"
    },
    "visible_features": ["list of visible features"],
    "layout_description": "description of the layout"
}
""",
            
            'code_changes': """
You are analyzing changes between two code screenshots. Please compare the images and identify:

1. **Change Type**: What type of changes occurred (addition, deletion, modification)
2. **Changed Lines**: Which lines were modified
3. **Change Description**: Describe what specifically changed
4. **Code Diff**: Provide a diff-like comparison if possible

Format your response as JSON:
{
    "has_changes": true/false,
    "change_type": ["addition", "deletion", "modification"],
    "changed_regions": [
        {
            "type": "addition/deletion/modification",
            "description": "description of the change",
            "approximate_line": "line number if identifiable"
        }
    ],
    "overall_description": "general description of all changes",
    "change_magnitude": "small/medium/large"
}
""",
            
            'code_extraction': """
You are a code extraction expert. Please carefully read and transcribe ALL visible code from this screenshot.

Focus on:
1. **Accuracy**: Transcribe code exactly as shown
2. **Formatting**: Preserve indentation and structure
3. **Completeness**: Include all visible text
4. **Syntax**: Maintain proper syntax elements

Important notes:
- Pay attention to proper indentation (spaces vs tabs)
- Include all visible comments
- Preserve exact variable names, function names, and syntax
- Note any code that is partially cut off or unclear

Provide the response in JSON format:
{
    "extracted_code": "complete code transcription with proper formatting",
    "programming_language": "detected language",
    "extraction_confidence": "confidence level (0-100)",
    "notes": "any notes about unclear or partially visible text",
    "code_lines": [
        {
            "line_number": "estimated line number",
            "content": "line content",
            "indent_level": "indentation level",
            "confidence": "confidence for this line"
        }
    ]
}
"""
        }
    
    def analyze_code_screenshot(self, image: Union[str, np.ndarray], analysis_type: str = 'code_analysis') -> Dict:
        """
        分析代码截图
        
        Args:
            image: 图像（base64字符串或numpy数组）
            analysis_type: 分析类型 (code_analysis, ide_detection, code_extraction)
            
        Returns:
            分析结果
        """
        try:
            # 准备图像
            image_base64 = self._prepare_image_for_analysis(image)
            if not image_base64:
                return {
                    'success': False,
                    'error': '图像处理失败'
                }
            
            # 获取对应的提示词
            prompt = self.analysis_prompts.get(analysis_type, self.analysis_prompts['code_analysis'])
            
            # 调用多模态模型
            result = self._call_multimodal_model(image_base64, prompt)
            
            if result['success']:
                # 解析结果
                parsed_result = self._parse_analysis_result(result['response'], analysis_type)
                return {
                    'success': True,
                    'analysis_type': analysis_type,
                    'result': parsed_result,
                    'raw_response': result['response']
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"代码截图分析失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _prepare_image_for_analysis(self, image: Union[str, np.ndarray]) -> Optional[str]:
        """准备用于分析的图像"""
        try:
            if isinstance(image, str):
                # 已经是base64格式
                if image.startswith('data:image'):
                    return image
                else:
                    return f"data:image/png;base64,{image}"
            
            elif isinstance(image, np.ndarray):
                # numpy数组转base64
                if len(image.shape) == 3:
                    # RGB图像
                    pil_image = Image.fromarray(image)
                else:
                    # 灰度图像
                    pil_image = Image.fromarray(image, mode='L')
                
                buffer = io.BytesIO()
                pil_image.save(buffer, format='PNG')
                img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                
                return f"data:image/png;base64,{img_base64}"
            
            else:
                logger.error(f"不支持的图像类型: {type(image)}")
                return None
                
        except Exception as e:
            logger.error(f"图像准备失败: {str(e)}")
            return None
    
    def _call_multimodal_model(self, image_base64: str, prompt: str) -> Dict:
        """调用多模态模型"""
        try:
            # 构建消息
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_base64
                            }
                        }
                    ]
                }
            ]
            
            # 调用GPT服务
            response = self.gpt_service.call_llm(
                messages=messages,
                model_type="gpt-4-vision-preview",  # 使用视觉模型
                temperature=0.1,  # 低温度保证准确性
                max_tokens=2000
            )
            
            if response.get('success', False):
                return {
                    'success': True,
                    'response': response['content']
                }
            else:
                return {
                    'success': False,
                    'error': response.get('error', '模型调用失败')
                }
                
        except Exception as e:
            logger.error(f"多模态模型调用失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _parse_analysis_result(self, response: str, analysis_type: str) -> Dict:
        """解析分析结果"""
        try:
            # 尝试解析JSON响应
            if response.strip().startswith('{') and response.strip().endswith('}'):
                parsed = json.loads(response)
                return parsed
            
            # 如果不是JSON格式，尝试提取JSON部分
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_part = response[json_start:json_end]
                parsed = json.loads(json_part)
                return parsed
            
            # 如果无法解析为JSON，返回原始文本
            logger.warning(f"无法解析为JSON格式的响应: {analysis_type}")
            return {
                'raw_text': response,
                'parsed': False
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}")
            return {
                'raw_text': response,
                'parsed': False,
                'parse_error': str(e)
            }
    
    def compare_code_screenshots(self, image1: Union[str, np.ndarray], image2: Union[str, np.ndarray]) -> Dict:
        """
        比较两个代码截图的差异
        
        Args:
            image1: 第一个图像
            image2: 第二个图像
            
        Returns:
            比较结果
        """
        try:
            # 准备图像
            image1_base64 = self._prepare_image_for_analysis(image1)
            image2_base64 = self._prepare_image_for_analysis(image2)
            
            if not image1_base64 or not image2_base64:
                return {
                    'success': False,
                    'error': '图像处理失败'
                }
            
            # 构建比较提示词
            comparison_prompt = f\"\"\"
Please compare these two code screenshots and identify the differences between them.

Image 1: First screenshot
Image 2: Second screenshot

{self.analysis_prompts['code_changes']}
\"\"\"
            
            # 构建消息（包含两个图像）
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": comparison_prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image1_base64,
                                "detail": "high"
                            }
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image2_base64,
                                "detail": "high"
                            }
                        }
                    ]
                }
            ]
            
            # 调用GPT服务
            response = self.gpt_service.call_llm(
                messages=messages,
                model_type="gpt-4-vision-preview",
                temperature=0.1,
                max_tokens=1500
            )
            
            if response.get('success', False):
                parsed_result = self._parse_analysis_result(response['content'], 'code_changes')
                return {
                    'success': True,
                    'comparison_result': parsed_result,
                    'raw_response': response['content']
                }
            else:
                return {
                    'success': False,
                    'error': response.get('error', '比较分析失败')
                }
                
        except Exception as e:
            logger.error(f"代码截图比较失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def extract_code_with_multimodal(self, image: Union[str, np.ndarray]) -> Dict:
        """
        使用多模态模型提取代码
        
        Args:
            image: 代码截图
            
        Returns:
            代码提取结果
        """
        return self.analyze_code_screenshot(image, 'code_extraction')
    
    def detect_ide_with_multimodal(self, image: Union[str, np.ndarray]) -> Dict:
        """
        使用多模态模型检测IDE
        
        Args:
            image: IDE截图
            
        Returns:
            IDE检测结果
        """
        return self.analyze_code_screenshot(image, 'ide_detection')
    
    def batch_analyze_screenshots(self, images: List[Union[str, np.ndarray]], analysis_type: str = 'code_analysis') -> List[Dict]:
        """
        批量分析多个截图
        
        Args:
            images: 图像列表
            analysis_type: 分析类型
            
        Returns:
            分析结果列表
        """
        results = []
        
        for i, image in enumerate(images):
            logger.info(f"分析截图 {i+1}/{len(images)}")
            
            result = self.analyze_code_screenshot(image, analysis_type)
            result['image_index'] = i
            
            results.append(result)
        
        return results
    
    def analyze_code_evolution(self, image_sequence: List[Union[str, np.ndarray]]) -> Dict:
        """
        分析代码演化过程
        
        Args:
            image_sequence: 按时间顺序排列的代码截图序列
            
        Returns:
            代码演化分析结果
        """
        try:
            if len(image_sequence) < 2:
                return {
                    'success': False,
                    'error': '至少需要两个图像进行演化分析'
                }
            
            evolution_steps = []
            
            # 分析每个变化步骤
            for i in range(1, len(image_sequence)):
                prev_image = image_sequence[i-1]
                curr_image = image_sequence[i]
                
                logger.info(f"分析演化步骤 {i}/{len(image_sequence)-1}")
                
                comparison = self.compare_code_screenshots(prev_image, curr_image)
                
                if comparison['success']:
                    evolution_steps.append({
                        'step': i,
                        'from_image': i-1,
                        'to_image': i,
                        'changes': comparison['comparison_result']
                    })
            
            # 生成演化总结
            evolution_summary = self._summarize_code_evolution(evolution_steps)
            
            return {
                'success': True,
                'evolution_steps': evolution_steps,
                'evolution_summary': evolution_summary,
                'total_steps': len(evolution_steps)
            }
            
        except Exception as e:
            logger.error(f"代码演化分析失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _summarize_code_evolution(self, evolution_steps: List[Dict]) -> Dict:
        """总结代码演化过程"""
        summary = {
            'total_changes': 0,
            'change_types': {'addition': 0, 'deletion': 0, 'modification': 0},
            'major_changes': [],
            'development_pattern': ''
        }
        
        for step in evolution_steps:
            changes = step.get('changes', {})
            
            if changes.get('has_changes', False):
                summary['total_changes'] += 1
                
                # 统计变化类型
                change_types = changes.get('change_type', [])
                for change_type in change_types:
                    if change_type in summary['change_types']:
                        summary['change_types'][change_type] += 1
                
                # 记录重大变化
                if changes.get('change_magnitude') == 'large':
                    summary['major_changes'].append({
                        'step': step['step'],
                        'description': changes.get('overall_description', '')
                    })
        
        # 分析开发模式
        if summary['change_types']['addition'] > summary['change_types']['deletion']:
            summary['development_pattern'] = 'incremental_development'
        elif summary['change_types']['modification'] > summary['change_types']['addition']:
            summary['development_pattern'] = 'iterative_refinement'
        else:
            summary['development_pattern'] = 'mixed_development'
        
        return summary
    
    def is_available(self) -> bool:
        """检查多模态分析器是否可用"""
        return self.gpt_service is not None