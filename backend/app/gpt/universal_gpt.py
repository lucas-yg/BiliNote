from app.gpt.base import GPT
from app.gpt.prompt_builder import generate_base_prompt
from app.models.gpt_model import GPTSource
from app.gpt.prompt import BASE_PROMPT, AI_SUM, SCREENSHOT, LINK
from app.gpt.utils import fix_markdown
from app.models.transcriber_model import TranscriptSegment
from datetime import timedelta
from typing import List
import json
import logging
import math

logger = logging.getLogger(__name__)
# 设置分段处理的参数
MAX_SEGMENTS_PER_CHUNK = 250  # 每块最多包含的段落数
MAX_CONTENT_LENGTH = 30000    # 字符数

class UniversalGPT(GPT):
    def __init__(self, client, model: str, temperature: float = 0.7):
        self.client = client
        self.model = model
        self.temperature = temperature
        self.screenshot = False
        self.link = False

    def _format_time(self, seconds: float) -> str:
        return str(timedelta(seconds=int(seconds)))[2:]

    def _build_segment_text(self, segments: List[TranscriptSegment]) -> str:
        return "\n".join(
            f"{self._format_time(seg.start)} - {seg.text.strip()}"
            for seg in segments
        )

    def ensure_segments_type(self, segments) -> List[TranscriptSegment]:
        return [TranscriptSegment(**seg) if isinstance(seg, dict) else seg for seg in segments]

    def create_messages(self, segments: List[TranscriptSegment], **kwargs):
        content_text = generate_base_prompt(
            title=kwargs.get('title'),
            segment_text=self._build_segment_text(segments),
            tags=kwargs.get('tags'),
            _format=kwargs.get('_format'),
            style=kwargs.get('style'),
            extras=kwargs.get('extras'),
        )
        
        # 检查文本长度
        if len(content_text) > MAX_CONTENT_LENGTH:
            # 保留前部分和后部分内容
            first_part = int(MAX_CONTENT_LENGTH * 0.3)
            second_part = MAX_CONTENT_LENGTH - first_part - 100  # 预留100字符给提示文本
            
            truncated_text = (
                content_text[:first_part] + 
                "\n\n[内容过长，中间部分已省略]\n\n" + 
                content_text[-second_part:]
            )
            content_text = truncated_text
            print(f"内容已截断，原长度: {len(content_text)}，截断后: {len(truncated_text)}")
        
        # 组装 content 数组，支持 text + image_url 混合
        content = [{"type": "text", "text": content_text}]
        video_img_urls = kwargs.get('video_img_urls', [])

        # 限制图片数量
        if len(video_img_urls) > 5:
            video_img_urls = video_img_urls[:5]
            print("图片数量过多，已限制为5张")

        for url in video_img_urls:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": url,
                    "detail": "auto"
                }
            })

        # 正确格式：整体包在一个 message 里，role + content array
        messages = [{
            "role": "user",
            "content": content
        }]

        return messages

    def list_models(self):
        return self.client.models.list()

    def summarize(self, source: GPTSource) -> str:
        self.screenshot = source.screenshot
        self.link = source.link
        source.segment = self.ensure_segments_type(source.segment)

        # 如果段落数量超过阈值，使用分段处理方法
        if len(source.segment) > MAX_SEGMENTS_PER_CHUNK:
            print(f"段落过多({len(source.segment)}个)，将使用分段处理方法")
            return self._process_long_content_by_chunks(source)
        
        # 正常处理较短的内容
        try:
            messages = self.create_messages(
                source.segment,
                title=source.title,
                tags=source.tags,
                video_img_urls=source.video_img_urls,
                _format=source._format,
                style=source.style,
                extras=source.extras
            )
            
            # 检查消息大小
            messages_json = json.dumps(messages)
            if len(messages_json) > 100000:  # API限制
                print(f"消息体积过大: {len(messages_json)} 字节，将使用分段处理方法")
                return self._process_long_content_by_chunks(source)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            error_msg = f"总结失败: {str(e)}"
            print(error_msg)
            # 记录详细错误信息到日志
            import logging
            logging.error(f"GPT单块处理失败 - {error_msg}")
            # 如果处理失败，尝试使用分段处理方法
            print("尝试使用分段处理方法")
            try:
                return self._process_long_content_by_chunks(source)
            except Exception as fallback_error:
                # 如果分段处理也失败，抛出异常
                logging.error(f"GPT分段处理也失败 - {str(fallback_error)}")
                raise Exception(f"视频处理完全失败：主处理失败({str(e)})，分段处理也失败({str(fallback_error)})")

    def _process_long_content_by_chunks(self, source: GPTSource) -> str:
        """
        将长内容分成多个块，分别处理后再整合
        """
        segments = source.segment
        total_segments = len(segments)
        
        # 计算需要多少块
        num_chunks = math.ceil(total_segments / MAX_SEGMENTS_PER_CHUNK)
        chunk_size = math.ceil(total_segments / num_chunks)
        
        print(f"将内容分为{num_chunks}块进行处理，每块约{chunk_size}个段落")
        
        chunk_summaries = []
        
        # 处理每个块
        for i in range(num_chunks):
            start_idx = i * chunk_size
            end_idx = min(start_idx + chunk_size, total_segments)
            
            print(f"处理第{i+1}/{num_chunks}块 (段落 {start_idx} 到 {end_idx-1})")
            
            # 创建此块的子源
            chunk_source = GPTSource(
                title=f"{source.title} - 第{i+1}/{num_chunks}部分",
                segment=segments[start_idx:end_idx],
                tags=source.tags,
                screenshot=False,  # 中间块不需要截图
                video_img_urls=[],  # 中间块不需要图片
                link=False,         # 中间块不需要链接
                _format=[],
                style=source.style,
                extras=f"这是内容的第{i+1}部分，共{num_chunks}部分。请仅总结这部分内容的要点，无需引言和结论。"
            )
            
            try:
                # 处理这个块
                chunk_messages = self.create_messages(
                    chunk_source.segment,
                    title=chunk_source.title,
                    tags=chunk_source.tags,
                    video_img_urls=chunk_source.video_img_urls,
                    _format=chunk_source._format,
                    style=chunk_source.style,
                    extras=chunk_source.extras
                )
                
                chunk_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=chunk_messages,
                    temperature=0.7
                )
                
                chunk_summary = chunk_response.choices[0].message.content.strip()
                chunk_summaries.append(f"### 第{i+1}部分内容总结\n\n{chunk_summary}")
                
                print(f"第{i+1}块处理完成")
                
            except Exception as e:
                error_msg = f"处理第{i+1}块时出错: {str(e)}"
                print(error_msg)
                # 记录详细错误信息到日志
                import logging
                logging.error(f"GPT处理失败 - {error_msg}")
                # 如果某块处理失败，抛出异常停止整个处理流程
                raise Exception(f"视频处理失败：第{i+1}块GPT调用失败 - {str(e)}")
        
        # 合并所有块的总结
        all_summaries = "\n\n".join(chunk_summaries)
        
        # 创建最终总结请求
        final_segment = TranscriptSegment(start=0, end=0, text=all_summaries)
        final_source = GPTSource(
            title=source.title,
            segment=[final_segment],
            tags=source.tags,
            screenshot=source.screenshot,
            video_img_urls=source.video_img_urls,
            link=source.link,
            _format=source._format,
            style=source.style,
            extras="以下是视频各部分的总结，请将它们整合为一篇完整、连贯的笔记。"
        )
        
        try:
            # 最终合并处理
            final_messages = self.create_messages(
                final_source.segment,
                title=final_source.title,
                tags=final_source.tags,
                video_img_urls=final_source.video_img_urls,
                _format=final_source._format,
                style=final_source.style,
                extras=final_source.extras
            )
            
            final_response = self.client.chat.completions.create(
                model=self.model,
                messages=final_messages,
                temperature=0.7
            )
            
            return final_response.choices[0].message.content.strip()
            
        except Exception as e:
            error_msg = f"最终合并处理时出错: {str(e)}"
            print(error_msg)
            # 记录详细错误信息到日志
            import logging
            logging.error(f"GPT最终合并失败 - {error_msg}")
            # 如果最终合并失败，抛出异常
            raise Exception(f"视频处理失败：GPT最终合并失败 - {str(e)}")
