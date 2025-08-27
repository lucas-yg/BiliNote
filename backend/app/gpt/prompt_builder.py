from app.gpt.prompt import BASE_PROMPT
from app.gpt.tutorial_prompts import TUTORIAL_STYLES
from app.gpt.minimal_prompts import MINIMAL_STYLES
from app.gpt.detailed_prompts import DETAILED_STYLES

note_formats = [
    {'label': '目录', 'value': 'toc'},
    {'label': '原片跳转', 'value': 'link'},
    {'label': '原片截图', 'value': 'screenshot'},
    {'label': 'AI总结', 'value': 'summary'}
]

note_styles = [
    {'label': '精简', 'value': 'minimal'},
    {'label': '详细', 'value': 'detailed'},
    {'label': '学术', 'value': 'academic'},
    {"label": '编程教程',"value": 'tutorial', },
    {'label': '小红书', 'value': 'xiaohongshu'},
    {'label': '生活向', 'value': 'life_journal'},
    {'label': '任务导向', 'value': 'task_oriented'},
    {'label': '商业风格', 'value': 'business'},
    {'label': '会议纪要', 'value': 'meeting_minutes'}
]


# 生成 BASE_PROMPT 函数
def generate_base_prompt(title, segment_text, tags, _format=None, style=None, extras=None):
    # 生成 Base Prompt 开头部分
    prompt = BASE_PROMPT.format(
        video_title=title,
        segment_text=segment_text,
        tags=tags
    )

    # 特殊处理教程风格 - 直接使用代码提取模板，忽略其他格式
    if style == 'tutorial':
        tutorial_prompt = TUTORIAL_STYLES.get('code_extraction', '')
        prompt += f"\n\n**教程代码提取任务（最高优先级）：**\n{tutorial_prompt}\n"
        prompt += "\n请严格按照上述教程提取要求执行，专注于代码提取和整理。\n"
        
        # 如果有用户自定义备注，作为补充
        if extras and extras.strip():
            prompt += f"\n**用户补充要求：**\n{extras}\n"
        
        return prompt
    
    # 特殊处理精简风格 - 直接使用精简提取模板，忽略其他格式
    if style == 'minimal':
        minimal_prompt = MINIMAL_STYLES.get('content_extraction', '')
        prompt += f"\n\n**精简内容提取任务（最高优先级）：**\n{minimal_prompt}\n"
        prompt += "\n请严格按照上述精简提取要求执行，专注于核心信息提炼和整理。\n"
        
        # 如果有用户自定义备注，作为补充
        if extras and extras.strip():
            prompt += f"\n**用户补充要求：**\n{extras}\n"
        
        return prompt
    
    # 特殊处理详细风格 - 直接使用详细分析模板，忽略其他格式
    if style == 'detailed':
        detailed_prompt = DETAILED_STYLES.get('content_extraction', '')
        prompt += f"\n\n**详细内容分析任务（最高优先级）：**\n{detailed_prompt}\n"
        prompt += "\n请严格按照上述详细分析要求执行，专注于全面深入的信息整理。\n"
        
        # 如果有用户自定义备注，作为补充
        if extras and extras.strip():
            prompt += f"\n**用户补充要求：**\n{extras}\n"
        
        return prompt
    
    # 原有的备注优先级逻辑（非特殊风格时使用）
    if extras and extras.strip():
        # 将用户备注提升为最重要的任务指令
        prompt += f"\n\n**用户特定要求（最高优先级）：**\n{extras}\n"
        prompt += "\n请严格按照上述用户要求执行，如与默认格式冲突，以用户要求为准。\n"

    # 添加用户选择的格式（如果没有备注内容，或者备注内容较短）
    if _format:
        format_instructions = "\n" + "\n".join([get_format_function(f) for f in _format])
        if not extras or len(extras.strip()) < 100:  # 如果备注内容较短，仍然添加格式指令
            prompt += format_instructions
        else:
            # 备注内容较长时，将格式指令作为补充说明
            prompt += f"\n\n**补充格式要求：**{format_instructions}"

    # 根据用户选择的笔记风格添加描述
    if style:
        style_instruction = get_style_format(style)
        if not extras or len(extras.strip()) < 100:
            prompt += "\n" + style_instruction
        else:
            prompt += f"\n\n**风格参考：**\n{style_instruction}"
    
    return prompt


# 获取格式函数
def get_format_function(format_type):
    format_map = {
        'toc': get_toc_format,
        'link': get_link_format,
        'screenshot': get_screenshot_format,
        'summary': get_summary_format
    }
    return format_map.get(format_type, lambda: '')()


# 风格描述的处理
def get_style_format(style):
    style_map = {
        'academic': '3. **学术风格**: 适合学术报告，正式且结构化。',
        'xiaohongshu': '''4. **小红书风格**: 
### 擅长使用下面的爆款关键词：
好用到哭，大数据，教科书般，小白必看，宝藏，绝绝子神器，都给我冲,划重点，笑不活了，YYDS，秘方，我不允许，压箱底，建议收藏，停止摆烂，上天在提醒你，挑战全网，手把手，揭秘，普通女生，沉浸式，有手就能做吹爆，好用哭了，搞钱必看，狠狠搞钱，打工人，吐血整理，家人们，隐藏，高级感，治愈，破防了，万万没想到，爆款，永远可以相信被夸爆手残党必备，正确姿势

### 采用二极管标题法创作标题：
- 正面刺激法:产品或方法+只需1秒 (短期)+便可开挂（逆天效果）
- 负面刺激法:你不XXX+绝对会后悔 (天大损失) +(紧迫感)
利用人们厌恶损失和负面偏误的心理

### 写作技巧
1. 使用惊叹号、省略号等标点符号增强表达力，营造紧迫感和惊喜感。
2. **使用emoji表情符号，来增加文字的活力**
3. 采用具有挑战性和悬念的表述，引发读、“无敌者好奇心，例如“暴涨词汇量”了”、“拒绝焦虑”等
4. 利用正面刺激和负面激，诱发读者的本能需求和动物基本驱动力，如“离离原上谱”、“你不知道的项目其实很赚”等
5. 融入热点话题和实用工具，提高文章的实用性和时效性，如“2023年必知”、“chatGPT狂飙进行时”等
6. 描述具体的成果和效果，强调标题中的关键词，使其更具吸引力，例如“英语底子再差，搞清这些语法你也能拿130+”
7. 使用吸引人的标题：''',

        'life_journal': '5. **生活向**: 记录个人生活感悟，情感化表达。',
        'task_oriented': '6. **任务导向**: 强调任务、目标，适合工作和待办事项。',
        'business': '7. **商业风格**: 适合商业报告、会议纪要，正式且精准。',
        'meeting_minutes': '8. **会议纪要**: 适合商业报告、会议纪要，正式且精准。',
        "tutorial": TUTORIAL_STYLES.get('code_extraction', '9.**教程笔记**:尽可能详细的记录教程,特别是关键点和一些重要的结论步骤')
    }
    return style_map.get(style, '')


# 格式化输出内容
def get_toc_format():
    return '''
    9. **目录**: 自动生成一个基于 `##` 级标题的目录。不需要插入原片跳转
    '''


def get_link_format():
    return '''
    10. **原片跳转**: 为每个主要章节添加时间戳，使用格式 `*Content-[mm:ss]`。 
    重要：**始终**在章节标题前加上 `*Content` 前缀，例如：`AI 的发展史 *Content-[01:23]`。一定是标题在前 插入标记在后
    '''


def get_screenshot_format():
    return '''
11. **原片截图**:你收到的截图一般是一个网格，网格的每张图片就是一个时间点，左上角会包含时间mm:ss的格式，请你结合我发你的图片插入截图提示，请你帮助用户更好的理解视频内容，请你认真的分析每个图片和对应的转写文案，插入最合适的内容来备注用户理解，请一定按照这个格式 返回否则系统无法解析：
- 格式：`*Screenshot-[mm:ss]`

    '''


def get_summary_format():
    return '''
    12. **AI总结**: 在笔记末尾加入简短的AI生成总结,并且二级标题 就是 AI 总结 例如 ## AI 总结。
    '''
