"""
OCR结果优化器

对OCR识别结果进行后处理和优化，提高代码文本的准确性。
"""

import re
import difflib
from typing import List, Dict, Tuple, Optional, Set
import numpy as np

from app.utils.logger import get_logger

logger = get_logger(__name__)

class OCROptimizer:
    def __init__(self):
        """初始化OCR优化器"""
        self.programming_keywords = self._load_programming_keywords()
        self.common_symbols = self._load_common_symbols()
        self.correction_rules = self._load_correction_rules()
        
    def _load_programming_keywords(self) -> Dict[str, Set[str]]:
        """加载编程语言关键字"""
        return {
            'python': {
                'def', 'class', 'import', 'from', 'if', 'else', 'elif', 'for', 'while', 
                'try', 'except', 'finally', 'with', 'as', 'return', 'yield', 'lambda',
                'and', 'or', 'not', 'in', 'is', 'None', 'True', 'False', 'self',
                'print', 'len', 'range', 'str', 'int', 'float', 'list', 'dict', 'set'
            },
            'javascript': {
                'function', 'var', 'let', 'const', 'if', 'else', 'for', 'while', 
                'do', 'switch', 'case', 'default', 'break', 'continue', 'return',
                'try', 'catch', 'finally', 'throw', 'new', 'this', 'typeof',
                'null', 'undefined', 'true', 'false', 'console', 'log'
            },
            'java': {
                'public', 'private', 'protected', 'static', 'final', 'abstract',
                'class', 'interface', 'extends', 'implements', 'import', 'package',
                'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'default',
                'try', 'catch', 'finally', 'throw', 'throws', 'return', 'new',
                'this', 'super', 'null', 'true', 'false', 'void', 'int', 'String'
            },
            'cpp': {
                'int', 'float', 'double', 'char', 'bool', 'void', 'auto', 'const',
                'static', 'extern', 'class', 'struct', 'public', 'private', 'protected',
                'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'default',
                'return', 'break', 'continue', 'try', 'catch', 'throw', 'new', 'delete',
                'true', 'false', 'nullptr', 'std', 'cout', 'cin', 'endl'
            }
        }
    
    def _load_common_symbols(self) -> Dict[str, str]:
        """加载常见符号映射"""
        return {
            # 括号类
            '（': '(', '）': ')',
            '［': '[', '］': ']',
            '｛': '{', '｝': '}',
            # 标点符号
            '；': ';', '：': ':',
            '，': ',', '。': '.',
            '"': '"', '"': '"',
            ''': "'", ''': "'",
            # 数字
            '０': '0', '１': '1', '２': '2', '３': '3', '４': '4',
            '５': '5', '６': '6', '７': '7', '８': '8', '９': '9',
            # 运算符
            '＋': '+', '－': '-', '＊': '*', '／': '/',
            '＝': '=', '＜': '<', '＞': '>',
            '！': '!', '＆': '&', '｜': '|',
            # 其他常见误识别
            'l': '1', 'O': '0', 'S': '5'
        }
    
    def _load_correction_rules(self) -> List[Tuple[str, str]]:
        """加载常见的OCR错误修正规则"""
        return [
            # 常见的OCR错误模式
            (r'\\bl\\b', '1'),  # 单独的小写l通常是数字1
            (r'\\bO\\b', '0'),  # 单独的大写O通常是数字0
            (r'if\\s*\\(', 'if ('),  # if语句格式
            (r'for\\s*\\(', 'for ('),  # for语句格式
            (r'while\\s*\\(', 'while ('),  # while语句格式
            (r'def\\s+', 'def '),  # Python函数定义
            (r'class\\s+', 'class '),  # 类定义
            (r'import\\s+', 'import '),  # 导入语句
            (r'return\\s+', 'return '),  # 返回语句
            (r'print\\s*\\(', 'print('),  # print语句
            # 修复常见的空格问题
            (r'\\s*=\\s*', ' = '),  # 赋值运算符前后加空格
            (r'\\s*\\+\\s*', ' + '),  # 加号前后加空格
            (r'\\s*-\\s*', ' - '),  # 减号前后加空格（需要小心负数）
            (r'\\s*\\*\\s*', ' * '),  # 乘号前后加空格
            (r'\\s*/\\s*', ' / '),  # 除号前后加空格
        ]
    
    def optimize_ocr_results(self, ocr_results: List[Dict], language_hint: Optional[str] = None) -> Dict:
        """
        优化OCR识别结果
        
        Args:
            ocr_results: OCR识别结果列表
            language_hint: 编程语言提示
            
        Returns:
            优化后的结果
        """
        try:
            if not ocr_results:
                return {
                    'success': False,
                    'error': '无OCR结果需要优化',
                    'optimized_results': []
                }
            
            # 1. 基础字符修正
            corrected_results = self._correct_characters(ocr_results)
            
            # 2. 关键字修正
            keyword_corrected = self._correct_keywords(corrected_results, language_hint)
            
            # 3. 语法结构优化
            structure_optimized = self._optimize_structure(keyword_corrected)
            
            # 4. 行内容整理
            line_optimized = self._optimize_lines(structure_optimized)
            
            # 5. 计算优化统计信息
            optimization_stats = self._calculate_optimization_stats(ocr_results, line_optimized)
            
            return {
                'success': True,
                'optimized_results': line_optimized,
                'optimization_stats': optimization_stats,
                'detected_language': self._detect_programming_language(line_optimized)
            }
            
        except Exception as e:
            logger.error(f"OCR结果优化失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'optimized_results': ocr_results
            }
    
    def _correct_characters(self, results: List[Dict]) -> List[Dict]:
        """基础字符修正"""
        corrected_results = []
        
        for result in results:
            corrected_result = result.copy()
            text = result.get('text', '')
            
            # 应用字符映射
            corrected_text = text
            for wrong_char, correct_char in self.common_symbols.items():
                corrected_text = corrected_text.replace(wrong_char, correct_char)
            
            corrected_result['text'] = corrected_text
            corrected_result['original_text'] = text
            
            corrected_results.append(corrected_result)
        
        return corrected_results
    
    def _correct_keywords(self, results: List[Dict], language_hint: Optional[str] = None) -> List[Dict]:
        """关键字修正"""
        corrected_results = []
        
        # 获取所有可能的关键字
        all_keywords = set()
        if language_hint and language_hint in self.programming_keywords:
            all_keywords.update(self.programming_keywords[language_hint])
        else:
            # 如果没有语言提示，使用所有语言的关键字
            for keywords in self.programming_keywords.values():
                all_keywords.update(keywords)
        
        for result in results:
            corrected_result = result.copy()
            text = result.get('text', '')
            
            # 分词并检查每个词
            words = re.findall(r'\\b\\w+\\b', text)
            corrected_text = text
            
            for word in words:
                if len(word) > 1:  # 跳过单字符
                    # 查找最匹配的关键字
                    best_match = self._find_best_keyword_match(word, all_keywords)
                    if best_match and best_match != word:
                        corrected_text = re.sub(r'\\b' + re.escape(word) + r'\\b', best_match, corrected_text)
            
            corrected_result['text'] = corrected_text
            corrected_results.append(corrected_result)
        
        return corrected_results
    
    def _find_best_keyword_match(self, word: str, keywords: Set[str]) -> Optional[str]:
        """查找最佳关键字匹配"""
        word_lower = word.lower()
        
        # 精确匹配
        if word_lower in keywords:
            return word_lower
        
        # 相似度匹配
        best_match = None
        best_ratio = 0.0
        
        for keyword in keywords:
            ratio = difflib.SequenceMatcher(None, word_lower, keyword).ratio()
            
            # 只考虑相似度较高的匹配
            if ratio > 0.8 and ratio > best_ratio:
                best_ratio = ratio
                best_match = keyword
        
        # 如果原词长度差异太大，不进行替换
        if best_match and abs(len(word) - len(best_match)) <= 2:
            return best_match
        
        return None
    
    def _optimize_structure(self, results: List[Dict]) -> List[Dict]:
        """语法结构优化"""
        optimized_results = []
        
        for result in results:
            optimized_result = result.copy()
            text = result.get('text', '')
            
            # 应用修正规则
            corrected_text = text
            for pattern, replacement in self.correction_rules:
                corrected_text = re.sub(pattern, replacement, corrected_text)
            
            # 修正常见的格式问题
            corrected_text = self._fix_formatting_issues(corrected_text)
            
            optimized_result['text'] = corrected_text
            optimized_results.append(optimized_result)
        
        return optimized_results
    
    def _fix_formatting_issues(self, text: str) -> str:
        """修正格式问题"""
        # 修正括号前后的空格
        text = re.sub(r'\\s*\\(\\s*', '(', text)
        text = re.sub(r'\\s*\\)\\s*', ')', text)
        text = re.sub(r'\\s*\\[\\s*', '[', text)
        text = re.sub(r'\\s*\\]\\s*', ']', text)
        text = re.sub(r'\\s*\\{\\s*', '{', text)
        text = re.sub(r'\\s*\\}\\s*', '}', text)
        
        # 修正逗号后的空格
        text = re.sub(r',\\s*', ', ', text)
        text = re.sub(r';\\s*', '; ', text)
        
        # 修正冒号后的空格
        text = re.sub(r':\\s*', ': ', text)
        
        # 移除多余的空格
        text = re.sub(r'\\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def _optimize_lines(self, results: List[Dict]) -> List[Dict]:
        """优化行内容"""
        # 按行分组
        lines_dict = {}
        for result in results:
            line_num = result.get('line_num', 0)
            if line_num not in lines_dict:
                lines_dict[line_num] = []
            lines_dict[line_num].append(result)
        
        optimized_results = []
        
        for line_num in sorted(lines_dict.keys()):
            line_results = lines_dict[line_num]
            
            # 按x坐标排序
            line_results.sort(key=lambda x: x.get('bbox', [0, 0, 0, 0])[0])
            
            # 重构行文本
            line_text_parts = []
            for result in line_results:
                text = result.get('text', '').strip()
                if text:
                    line_text_parts.append(text)
            
            if line_text_parts:
                # 智能组合文本片段
                combined_text = self._smart_combine_text_parts(line_text_parts)
                
                # 创建优化后的结果
                first_result = line_results[0]
                optimized_result = first_result.copy()
                optimized_result['text'] = combined_text
                optimized_result['is_line_combined'] = len(line_results) > 1
                
                optimized_results.append(optimized_result)
        
        return optimized_results
    
    def _smart_combine_text_parts(self, text_parts: List[str]) -> str:
        """智能组合文本片段"""
        if not text_parts:
            return ""
        
        if len(text_parts) == 1:
            return text_parts[0]
        
        combined = ""
        for i, part in enumerate(text_parts):
            if i == 0:
                combined = part
            else:
                # 判断是否需要添加空格
                prev_part = text_parts[i-1]
                
                # 如果前一部分以符号结尾，或当前部分以符号开头，不加空格
                if (prev_part[-1] in '([{' or part[0] in ')]}.,;:') or \
                   (prev_part[-1] in ')]}.,;:' and part[0] in '([{'):
                    combined += part
                else:
                    combined += " " + part
        
        return combined
    
    def _calculate_optimization_stats(self, original_results: List[Dict], optimized_results: List[Dict]) -> Dict:
        """计算优化统计信息"""
        original_text = " ".join([r.get('text', '') for r in original_results])
        optimized_text = " ".join([r.get('text', '') for r in optimized_results])
        
        # 计算字符级别的变化
        char_changes = sum(1 for a, b in zip(original_text, optimized_text) if a != b)
        
        # 计算修正的单词数
        original_words = set(re.findall(r'\\b\\w+\\b', original_text.lower()))
        optimized_words = set(re.findall(r'\\b\\w+\\b', optimized_text.lower()))
        
        corrected_words = len(original_words - optimized_words)
        
        return {
            'original_text_length': len(original_text),
            'optimized_text_length': len(optimized_text),
            'character_changes': char_changes,
            'corrected_words': corrected_words,
            'optimization_ratio': char_changes / max(len(original_text), 1),
            'word_correction_ratio': corrected_words / max(len(original_words), 1)
        }
    
    def _detect_programming_language(self, results: List[Dict]) -> Optional[str]:
        """检测编程语言"""
        all_text = " ".join([r.get('text', '') for r in results]).lower()
        
        language_scores = {}
        
        for lang, keywords in self.programming_keywords.items():
            score = 0
            for keyword in keywords:
                # 计算关键字在文本中出现的次数
                count = len(re.findall(r'\\b' + re.escape(keyword) + r'\\b', all_text))
                score += count
            
            language_scores[lang] = score
        
        # 返回得分最高的语言
        if language_scores:
            best_language = max(language_scores, key=language_scores.get)
            if language_scores[best_language] > 0:
                return best_language
        
        return None
    
    def merge_multiple_ocr_results(self, *ocr_results_list: List[Dict]) -> Dict:
        """
        合并多个OCR引擎的结果
        
        Args:
            *ocr_results_list: 多个OCR结果列表
            
        Returns:
            合并后的最佳结果
        """
        try:
            if not ocr_results_list:
                return {
                    'success': False,
                    'error': '无OCR结果需要合并',
                    'merged_results': []
                }
            
            # 收集所有候选文本
            all_candidates = []
            
            for ocr_results in ocr_results_list:
                if ocr_results and isinstance(ocr_results, list):
                    for result in ocr_results:
                        if result.get('text', '').strip():
                            all_candidates.append(result)
            
            if not all_candidates:
                return {
                    'success': False,
                    'error': '所有OCR结果都为空',
                    'merged_results': []
                }
            
            # 按位置分组候选文本
            position_groups = self._group_candidates_by_position(all_candidates)
            
            # 为每个位置选择最佳候选
            merged_results = []
            for group in position_groups:
                best_candidate = self._select_best_candidate(group)
                if best_candidate:
                    merged_results.append(best_candidate)
            
            # 优化合并后的结果
            optimization_result = self.optimize_ocr_results(merged_results)
            
            return {
                'success': True,
                'merged_results': optimization_result.get('optimized_results', merged_results),
                'merge_stats': {
                    'total_candidates': len(all_candidates),
                    'position_groups': len(position_groups),
                    'final_results': len(merged_results)
                },
                'optimization_stats': optimization_result.get('optimization_stats', {})
            }
            
        except Exception as e:
            logger.error(f"合并OCR结果失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'merged_results': []
            }
    
    def _group_candidates_by_position(self, candidates: List[Dict]) -> List[List[Dict]]:
        """按位置分组候选文本"""
        groups = []
        tolerance = 30  # 位置容差（像素）
        
        for candidate in candidates:
            bbox = candidate.get('bbox', [0, 0, 0, 0])
            x, y = bbox[0], bbox[1]
            
            # 查找匹配的组
            matched_group = None
            for group in groups:
                group_bbox = group[0]['bbox']
                group_x, group_y = group_bbox[0], group_bbox[1]
                
                if abs(x - group_x) <= tolerance and abs(y - group_y) <= tolerance:
                    matched_group = group
                    break
            
            if matched_group:
                matched_group.append(candidate)
            else:
                groups.append([candidate])
        
        return groups
    
    def _select_best_candidate(self, candidates: List[Dict]) -> Optional[Dict]:
        """从候选列表中选择最佳候选"""
        if not candidates:
            return None
        
        if len(candidates) == 1:
            return candidates[0]
        
        # 多重评分策略
        scored_candidates = []
        
        for candidate in candidates:
            score = 0.0
            
            # 1. 置信度权重
            confidence = candidate.get('confidence', 0.0)
            score += confidence * 0.4
            
            # 2. 文本长度权重（通常更长的文本更准确）
            text_length = len(candidate.get('text', ''))
            score += min(text_length / 20.0, 1.0) * 0.2
            
            # 3. 关键字匹配权重
            text = candidate.get('text', '').lower()
            keyword_matches = 0
            for keywords in self.programming_keywords.values():
                for keyword in keywords:
                    if keyword in text:
                        keyword_matches += 1
            score += min(keyword_matches / 5.0, 1.0) * 0.3
            
            # 4. 字符质量权重（减少明显错误的字符）
            char_quality = self._assess_character_quality(text)
            score += char_quality * 0.1
            
            scored_candidates.append((score, candidate))
        
        # 返回得分最高的候选
        best_score, best_candidate = max(scored_candidates, key=lambda x: x[0])
        return best_candidate
    
    def _assess_character_quality(self, text: str) -> float:
        """评估文本字符质量"""
        if not text:
            return 0.0
        
        # 计算合理字符的比例
        reasonable_chars = sum(1 for c in text if c.isalnum() or c in ' .,;:()[]{}+-*/<>=!"\'')
        quality_ratio = reasonable_chars / len(text)
        
        return quality_ratio