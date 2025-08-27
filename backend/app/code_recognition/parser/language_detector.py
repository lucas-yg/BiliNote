"""
编程语言检测器

基于代码特征和语法模式识别编程语言。
"""

import re
from typing import Dict, List, Optional, Tuple
import keyword
from collections import Counter

from app.utils.logger import get_logger

logger = get_logger(__name__)

class LanguageDetector:
    def __init__(self):
        """初始化语言检测器"""
        self.language_signatures = self._load_language_signatures()
        self.extension_mapping = self._load_extension_mapping()
        
    def _load_language_signatures(self) -> Dict:
        """加载各编程语言的特征签名"""
        return {
            'python': {
                'keywords': [
                    'def', 'class', 'import', 'from', 'if', 'else', 'elif', 'for', 'while',
                    'try', 'except', 'finally', 'with', 'as', 'return', 'yield', 'lambda',
                    'and', 'or', 'not', 'in', 'is', 'None', 'True', 'False', 'self',
                    'pass', 'break', 'continue', 'global', 'nonlocal'
                ],
                'built_ins': [
                    'print', 'len', 'range', 'str', 'int', 'float', 'list', 'dict', 'set',
                    'tuple', 'bool', 'type', 'isinstance', 'hasattr', 'getattr', 'setattr',
                    'input', 'open', 'max', 'min', 'sum', 'all', 'any', 'enumerate', 'zip'
                ],
                'patterns': [
                    r'def\\s+\\w+\\s*\\([^)]*\\)\\s*:',  # 函数定义
                    r'class\\s+\\w+\\s*(?:\\([^)]*\\))?\\s*:',  # 类定义
                    r'if\\s+__name__\\s*==\\s*["\']__main__["\']\\s*:',  # main检查
                    r'\\bself\\b',  # self关键字
                    r'@\\w+',  # 装饰器
                    r'\\bprint\\s*\\(',  # print函数
                    r'#.*',  # Python注释
                ],
                'string_patterns': [
                    r'"""[^"]*"""',  # 三引号字符串
                    r"'''[^']*'''",  # 三引号字符串
                    r'f"[^"]*"',  # f字符串
                    r"f'[^']*'",  # f字符串
                ],
                'indentation': 'spaces',
                'file_extensions': ['.py', '.pyw', '.pyi'],
                'weight_multipliers': {
                    'keywords': 2.0,
                    'patterns': 3.0,
                    'indentation': 1.5
                }
            },
            
            'javascript': {
                'keywords': [
                    'function', 'var', 'let', 'const', 'if', 'else', 'for', 'while', 'do',
                    'switch', 'case', 'default', 'break', 'continue', 'return', 'try',
                    'catch', 'finally', 'throw', 'new', 'this', 'typeof', 'instanceof',
                    'delete', 'void', 'null', 'undefined', 'true', 'false'
                ],
                'built_ins': [
                    'console', 'log', 'alert', 'confirm', 'prompt', 'document', 'window',
                    'Array', 'Object', 'String', 'Number', 'Boolean', 'Date', 'Math',
                    'JSON', 'parseInt', 'parseFloat', 'isNaN', 'setTimeout', 'setInterval'
                ],
                'patterns': [
                    r'function\\s+\\w+\\s*\\([^)]*\\)\\s*\\{',  # 函数定义
                    r'\\w+\\s*=>\\s*',  # 箭头函数
                    r'\\bvar\\s+\\w+',  # var声明
                    r'\\b(?:let|const)\\s+\\w+',  # let/const声明
                    r'console\\.log\\s*\\(',  # console.log
                    r'//.*',  # 单行注释
                    r'/\\*[^*]*\\*/',  # 多行注释
                    r'\\$\\{[^}]*\\}',  # 模板字符串
                ],
                'string_patterns': [
                    r'`[^`]*`',  # 模板字符串
                    r'"[^"]*"',  # 双引号字符串
                    r"'[^']*'",  # 单引号字符串
                ],
                'brackets': ['{}'],
                'file_extensions': ['.js', '.mjs', '.jsx', '.ts', '.tsx'],
                'weight_multipliers': {
                    'keywords': 2.0,
                    'patterns': 2.5,
                    'brackets': 1.0
                }
            },
            
            'java': {
                'keywords': [
                    'public', 'private', 'protected', 'static', 'final', 'abstract',
                    'class', 'interface', 'extends', 'implements', 'import', 'package',
                    'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'default',
                    'try', 'catch', 'finally', 'throw', 'throws', 'return', 'new',
                    'this', 'super', 'null', 'true', 'false', 'void'
                ],
                'built_ins': [
                    'String', 'int', 'Integer', 'double', 'Double', 'float', 'Float',
                    'boolean', 'Boolean', 'char', 'Character', 'byte', 'Byte',
                    'short', 'Short', 'long', 'Long', 'Object', 'System', 'out', 'println'
                ],
                'patterns': [
                    r'public\\s+class\\s+\\w+',  # public class
                    r'public\\s+static\\s+void\\s+main',  # main方法
                    r'System\\.out\\.println\\s*\\(',  # System.out.println
                    r'@\\w+',  # 注解
                    r'//.*',  # 单行注释
                    r'/\\*[^*]*\\*/',  # 多行注释
                    r'\\bimport\\s+[\\w.]+;',  # import语句
                ],
                'string_patterns': [
                    r'"[^"]*"',  # 双引号字符串
                    r"'.'",  # 字符常量
                ],
                'brackets': ['{}'],
                'semicolon_required': True,
                'file_extensions': ['.java'],
                'weight_multipliers': {
                    'keywords': 2.0,
                    'patterns': 3.0,
                    'semicolon': 1.5
                }
            },
            
            'cpp': {
                'keywords': [
                    'int', 'float', 'double', 'char', 'bool', 'void', 'auto', 'const',
                    'static', 'extern', 'class', 'struct', 'public', 'private', 'protected',
                    'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'default',
                    'return', 'break', 'continue', 'try', 'catch', 'throw', 'new', 'delete',
                    'true', 'false', 'nullptr', 'using', 'namespace', 'template'
                ],
                'built_ins': [
                    'std', 'cout', 'cin', 'endl', 'string', 'vector', 'map', 'set',
                    'iostream', 'fstream', 'sstream', 'algorithm', 'iterator'
                ],
                'patterns': [
                    r'#include\\s*<[^>]+>',  # include标准库
                    r'#include\\s*"[^"]+"',  # include自定义头文件
                    r'std::\\w+',  # std命名空间
                    r'cout\\s*<<',  # cout输出
                    r'cin\\s*>>',  # cin输入
                    r'//.*',  # 单行注释
                    r'/\\*[^*]*\\*/',  # 多行注释
                    r'\\busing\\s+namespace\\s+std\\s*;',  # using namespace
                ],
                'string_patterns': [
                    r'"[^"]*"',  # 双引号字符串
                    r"'.'",  # 字符常量
                ],
                'brackets': ['{}'],
                'semicolon_required': True,
                'file_extensions': ['.cpp', '.cc', '.cxx', '.c++', '.c', '.h', '.hpp'],
                'weight_multipliers': {
                    'keywords': 2.0,
                    'patterns': 3.0,
                    'includes': 2.5
                }
            },
            
            'csharp': {
                'keywords': [
                    'using', 'namespace', 'class', 'interface', 'struct', 'enum',
                    'public', 'private', 'protected', 'internal', 'static', 'readonly',
                    'const', 'virtual', 'override', 'abstract', 'sealed', 'partial',
                    'if', 'else', 'for', 'foreach', 'while', 'do', 'switch', 'case',
                    'default', 'try', 'catch', 'finally', 'throw', 'return', 'new',
                    'this', 'base', 'null', 'true', 'false', 'void'
                ],
                'built_ins': [
                    'Console', 'WriteLine', 'ReadLine', 'string', 'int', 'double',
                    'bool', 'char', 'DateTime', 'List', 'Dictionary', 'Array'
                ],
                'patterns': [
                    r'using\\s+[\\w.]+;',  # using语句
                    r'namespace\\s+\\w+',  # namespace声明
                    r'Console\\.WriteLine\\s*\\(',  # Console.WriteLine
                    r'//.*',  # 单行注释
                    r'/\\*[^*]*\\*/',  # 多行注释
                    r'\\[\\w+\\]',  # 属性
                ],
                'string_patterns': [
                    r'@"[^"]*"',  # 逐字字符串
                    r'"[^"]*"',  # 普通字符串
                    r"'.'",  # 字符常量
                ],
                'brackets': ['{}'],
                'semicolon_required': True,
                'file_extensions': ['.cs'],
                'weight_multipliers': {
                    'keywords': 2.0,
                    'patterns': 2.5,
                    'using': 2.0
                }
            },
            
            'html': {
                'keywords': [],
                'built_ins': [
                    'div', 'span', 'p', 'a', 'img', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                    'ul', 'ol', 'li', 'table', 'tr', 'td', 'th', 'form', 'input',
                    'button', 'select', 'option', 'textarea', 'script', 'style', 'head',
                    'body', 'html', 'meta', 'title', 'link'
                ],
                'patterns': [
                    r'<!DOCTYPE\\s+html>',  # DOCTYPE声明
                    r'<\\w+[^>]*>',  # 开始标签
                    r'</\\w+>',  # 结束标签
                    r'<\\w+[^>]*/>',  # 自闭合标签
                    r'<!--[^-]*-->',  # HTML注释
                ],
                'string_patterns': [
                    r'"[^"]*"',  # 属性值
                    r"'[^']*'",  # 属性值
                ],
                'brackets': ['<>'],
                'file_extensions': ['.html', '.htm', '.xhtml'],
                'weight_multipliers': {
                    'patterns': 3.0,
                    'tags': 2.0
                }
            },
            
            'css': {
                'keywords': [],
                'built_ins': [
                    'color', 'background', 'font', 'margin', 'padding', 'border',
                    'width', 'height', 'display', 'position', 'top', 'left', 'right',
                    'bottom', 'float', 'clear', 'text-align', 'font-size', 'font-weight'
                ],
                'patterns': [
                    r'\\w+\\s*\\{[^}]*\\}',  # CSS规则
                    r'#\\w+',  # ID选择器
                    r'\\.\\w+',  # 类选择器
                    r'/\\*[^*]*\\*/',  # CSS注释
                    r'\\w+:\\s*[^;]+;',  # 属性声明
                ],
                'string_patterns': [
                    r'"[^"]*"',  # 双引号字符串
                    r"'[^']*'",  # 单引号字符串
                    r'url\\([^)]+\\)',  # URL函数
                ],
                'brackets': ['{}'],
                'file_extensions': ['.css', '.scss', '.sass', '.less'],
                'weight_multipliers': {
                    'patterns': 3.0,
                    'selectors': 2.0
                }
            },
            
            'sql': {
                'keywords': [
                    'SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE', 'CREATE',
                    'DROP', 'ALTER', 'TABLE', 'DATABASE', 'INDEX', 'JOIN', 'INNER',
                    'LEFT', 'RIGHT', 'OUTER', 'ON', 'GROUP', 'BY', 'ORDER', 'HAVING',
                    'COUNT', 'SUM', 'AVG', 'MAX', 'MIN', 'DISTINCT', 'AS', 'AND', 'OR', 'NOT'
                ],
                'built_ins': [
                    'VARCHAR', 'INT', 'INTEGER', 'CHAR', 'TEXT', 'DATE', 'DATETIME',
                    'TIMESTAMP', 'BOOLEAN', 'DECIMAL', 'FLOAT', 'DOUBLE'
                ],
                'patterns': [
                    r'SELECT\\s+.*\\s+FROM\\s+\\w+',  # SELECT语句
                    r'INSERT\\s+INTO\\s+\\w+',  # INSERT语句
                    r'UPDATE\\s+\\w+\\s+SET',  # UPDATE语句
                    r'DELETE\\s+FROM\\s+\\w+',  # DELETE语句
                    r'CREATE\\s+TABLE\\s+\\w+',  # CREATE TABLE
                    r'--.*',  # SQL注释
                ],
                'string_patterns': [
                    r"'[^']*'",  # 单引号字符串
                    r'"[^"]*"',  # 双引号字符串
                ],
                'semicolon_required': True,
                'file_extensions': ['.sql'],
                'weight_multipliers': {
                    'keywords': 3.0,
                    'patterns': 2.5
                }
            }
        }
    
    def _load_extension_mapping(self) -> Dict:
        """加载文件扩展名映射"""
        extension_map = {}
        for lang, info in self.language_signatures.items():
            for ext in info.get('file_extensions', []):
                extension_map[ext] = lang
        return extension_map
    
    def detect_language(self, code_text: str, filename: Optional[str] = None) -> Dict:
        """
        检测代码的编程语言
        
        Args:
            code_text: 代码文本
            filename: 文件名（可选，用于辅助检测）
            
        Returns:
            检测结果字典
        """
        try:
            if not code_text.strip():
                return {
                    'success': False,
                    'error': '代码文本为空',
                    'detected_language': None
                }
            
            # 1. 基于文件扩展名的初步判断
            extension_hint = None
            if filename:
                extension_hint = self._detect_by_extension(filename)
            
            # 2. 基于代码内容的检测
            language_scores = {}
            
            for lang, signature in self.language_signatures.items():
                score = self._calculate_language_score(code_text, signature)
                if score > 0:
                    language_scores[lang] = score
            
            # 3. 如果有扩展名提示，给对应语言加分
            if extension_hint and extension_hint in language_scores:
                language_scores[extension_hint] *= 1.5
            
            # 4. 排序并选择最佳匹配
            if language_scores:
                sorted_languages = sorted(language_scores.items(), key=lambda x: x[1], reverse=True)
                best_language = sorted_languages[0][0]
                best_score = sorted_languages[0][1]
                
                # 计算置信度
                confidence = min(1.0, best_score / 10.0)  # 归一化到0-1
                
                return {
                    'success': True,
                    'detected_language': best_language,
                    'confidence': confidence,
                    'all_scores': dict(language_scores),
                    'extension_hint': extension_hint,
                    'details': self._get_detection_details(code_text, best_language)
                }
            else:
                return {
                    'success': True,
                    'detected_language': 'unknown',
                    'confidence': 0.0,
                    'all_scores': {},
                    'extension_hint': extension_hint,
                    'details': {}
                }
                
        except Exception as e:
            logger.error(f"语言检测失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'detected_language': None
            }
    
    def _detect_by_extension(self, filename: str) -> Optional[str]:
        """基于文件扩展名检测语言"""
        if not filename:
            return None
        
        # 提取扩展名
        parts = filename.lower().split('.')
        if len(parts) < 2:
            return None
        
        extension = '.' + parts[-1]
        return self.extension_mapping.get(extension)
    
    def _calculate_language_score(self, code_text: str, signature: Dict) -> float:
        """计算语言匹配分数"""
        score = 0.0
        code_lower = code_text.lower()
        
        # 1. 关键字匹配
        keywords = signature.get('keywords', [])
        if keywords:
            keyword_matches = sum(1 for keyword in keywords if re.search(r'\\b' + re.escape(keyword.lower()) + r'\\b', code_lower))
            keyword_score = keyword_matches * signature.get('weight_multipliers', {}).get('keywords', 1.0)
            score += keyword_score
        
        # 2. 内置函数/类型匹配
        built_ins = signature.get('built_ins', [])
        if built_ins:
            builtin_matches = sum(1 for builtin in built_ins if re.search(r'\\b' + re.escape(builtin.lower()) + r'\\b', code_lower))
            builtin_score = builtin_matches * signature.get('weight_multipliers', {}).get('built_ins', 1.0)
            score += builtin_score
        
        # 3. 语法模式匹配
        patterns = signature.get('patterns', [])
        if patterns:
            pattern_matches = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, code_text, re.IGNORECASE))
                pattern_matches += matches
            pattern_score = pattern_matches * signature.get('weight_multipliers', {}).get('patterns', 1.0)
            score += pattern_score
        
        # 4. 字符串模式匹配
        string_patterns = signature.get('string_patterns', [])
        if string_patterns:
            string_matches = 0
            for pattern in string_patterns:
                matches = len(re.findall(pattern, code_text))
                string_matches += matches
            string_score = string_matches * signature.get('weight_multipliers', {}).get('strings', 0.5)
            score += string_score
        
        # 5. 特定语言特征
        # 缩进检查（Python特有）
        if signature.get('indentation') == 'spaces':
            indented_lines = len(re.findall(r'^\\s{2,}\\S', code_text, re.MULTILINE))
            if indented_lines > 0:
                indentation_score = indented_lines * signature.get('weight_multipliers', {}).get('indentation', 1.0)
                score += indentation_score
        
        # 分号检查（C系语言）
        if signature.get('semicolon_required'):
            semicolon_lines = len(re.findall(r';\\s*$', code_text, re.MULTILINE))
            if semicolon_lines > 0:
                semicolon_score = semicolon_lines * signature.get('weight_multipliers', {}).get('semicolon', 1.0)
                score += semicolon_score
        
        # 括号类型检查
        brackets = signature.get('brackets', [])
        for bracket_type in brackets:
            if bracket_type == '{}':
                brace_count = code_text.count('{') + code_text.count('}')
                score += brace_count * 0.5
            elif bracket_type == '<>':
                angle_count = code_text.count('<') + code_text.count('>')
                score += angle_count * 0.3
        
        return score
    
    def _get_detection_details(self, code_text: str, language: str) -> Dict:
        """获取检测详情"""
        if language not in self.language_signatures:
            return {}
        
        signature = self.language_signatures[language]
        details = {}
        
        # 统计关键字出现次数
        keywords = signature.get('keywords', [])
        if keywords:
            keyword_counts = {}
            for keyword in keywords:
                count = len(re.findall(r'\\b' + re.escape(keyword) + r'\\b', code_text, re.IGNORECASE))
                if count > 0:
                    keyword_counts[keyword] = count
            details['keyword_matches'] = keyword_counts
        
        # 统计内置函数出现次数
        built_ins = signature.get('built_ins', [])
        if built_ins:
            builtin_counts = {}
            for builtin in built_ins:
                count = len(re.findall(r'\\b' + re.escape(builtin) + r'\\b', code_text, re.IGNORECASE))
                if count > 0:
                    builtin_counts[builtin] = count
            details['builtin_matches'] = builtin_counts
        
        # 统计模式匹配
        patterns = signature.get('patterns', [])
        if patterns:
            pattern_matches = []
            for pattern in patterns:
                matches = re.findall(pattern, code_text, re.IGNORECASE)
                if matches:
                    pattern_matches.append({
                        'pattern': pattern,
                        'matches': matches[:5]  # 只保留前5个匹配
                    })
            details['pattern_matches'] = pattern_matches
        
        return details
    
    def detect_language_from_multiple_sources(self, 
                                            code_snippets: List[str], 
                                            filenames: List[Optional[str]] = None) -> Dict:
        """
        从多个代码片段检测语言
        
        Args:
            code_snippets: 代码片段列表
            filenames: 对应的文件名列表（可选）
            
        Returns:
            综合检测结果
        """
        try:
            if not code_snippets:
                return {
                    'success': False,
                    'error': '没有代码片段',
                    'detected_language': None
                }
            
            # 确保filenames长度与code_snippets一致
            if filenames is None:
                filenames = [None] * len(code_snippets)
            elif len(filenames) != len(code_snippets):
                filenames.extend([None] * (len(code_snippets) - len(filenames)))
            
            # 检测每个片段
            all_results = []
            language_scores = Counter()
            
            for code, filename in zip(code_snippets, filenames):
                if code and code.strip():
                    result = self.detect_language(code, filename)
                    if result['success'] and result['detected_language'] != 'unknown':
                        all_results.append(result)
                        
                        # 累计分数
                        detected_lang = result['detected_language']
                        confidence = result['confidence']
                        language_scores[detected_lang] += confidence
            
            if not all_results:
                return {
                    'success': True,
                    'detected_language': 'unknown',
                    'confidence': 0.0,
                    'individual_results': [],
                    'language_distribution': {}
                }
            
            # 计算最终结果
            total_confidence = sum(language_scores.values())
            language_distribution = {lang: score/total_confidence for lang, score in language_scores.items()}
            
            # 选择最佳语言
            best_language = language_scores.most_common(1)[0][0]
            best_confidence = language_distribution[best_language]
            
            return {
                'success': True,
                'detected_language': best_language,
                'confidence': best_confidence,
                'language_distribution': language_distribution,
                'individual_results': all_results,
                'consensus_strength': len([r for r in all_results if r['detected_language'] == best_language]) / len(all_results)
            }
            
        except Exception as e:
            logger.error(f"多源语言检测失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'detected_language': None
            }
    
    def get_language_info(self, language: str) -> Optional[Dict]:
        """获取特定语言的信息"""
        return self.language_signatures.get(language)
    
    def get_supported_languages(self) -> List[str]:
        """获取支持的语言列表"""
        return list(self.language_signatures.keys())
    
    def is_code_like(self, text: str) -> Dict:
        """
        判断文本是否像代码
        
        Args:
            text: 输入文本
            
        Returns:
            判断结果
        """
        try:
            if not text.strip():
                return {'is_code_like': False, 'confidence': 0.0, 'reasons': ['empty_text']}
            
            code_indicators = []
            confidence_factors = []
            
            # 1. 检查是否包含编程关键字
            all_keywords = set()
            for lang_info in self.language_signatures.values():
                all_keywords.update(lang_info.get('keywords', []))
            
            keyword_matches = sum(1 for keyword in all_keywords if re.search(r'\\b' + re.escape(keyword) + r'\\b', text, re.IGNORECASE))
            if keyword_matches > 0:
                code_indicators.append('contains_keywords')
                confidence_factors.append(min(1.0, keyword_matches / 5.0))
            
            # 2. 检查语法字符
            syntax_chars = ['(', ')', '{', '}', '[', ']', ';', '=', '+', '-', '*', '/', '<', '>']
            syntax_char_count = sum(text.count(char) for char in syntax_chars)
            syntax_density = syntax_char_count / len(text)
            
            if syntax_density > 0.05:
                code_indicators.append('high_syntax_density')
                confidence_factors.append(min(1.0, syntax_density * 10))
            
            # 3. 检查缩进模式
            lines = text.split('\\n')
            indented_lines = sum(1 for line in lines if line.startswith(('    ', '\\t')))
            if len(lines) > 1 and indented_lines / len(lines) > 0.3:
                code_indicators.append('has_indentation')
                confidence_factors.append(0.7)
            
            # 4. 检查注释模式
            comment_patterns = [r'//.*', r'#.*', r'/\\*[^*]*\\*/', r'<!--[^-]*-->']
            comment_matches = sum(len(re.findall(pattern, text)) for pattern in comment_patterns)
            if comment_matches > 0:
                code_indicators.append('contains_comments')
                confidence_factors.append(0.6)
            
            # 5. 检查字符串模式
            string_patterns = [r'"[^"]*"', r"'[^']*'", r'`[^`]*`']
            string_matches = sum(len(re.findall(pattern, text)) for pattern in string_patterns)
            if string_matches > 0:
                code_indicators.append('contains_strings')
                confidence_factors.append(0.5)
            
            # 计算总体置信度
            if confidence_factors:
                overall_confidence = np.mean(confidence_factors)
                is_code_like = overall_confidence > 0.3
            else:
                overall_confidence = 0.0
                is_code_like = False
            
            return {
                'is_code_like': is_code_like,
                'confidence': overall_confidence,
                'indicators': code_indicators,
                'syntax_density': syntax_density,
                'indentation_ratio': indented_lines / max(len(lines), 1)
            }
            
        except Exception as e:
            logger.error(f"代码检测失败: {str(e)}")
            return {
                'is_code_like': False,
                'confidence': 0.0,
                'error': str(e)
            }