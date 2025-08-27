from app.gpt.base import GPT
from app.gpt.prompt_builder import generate_base_prompt
from app.models.gpt_model import GPTSource
from app.models.transcriber_model import TranscriptSegment
from datetime import timedelta
from typing import List
import json
import logging
import math
import time
import random
from openai import APIError, APIConnectionError, APITimeoutError, RateLimitError

logger = logging.getLogger(__name__)
# 设置分段处理的参数
MAX_SEGMENTS_PER_CHUNK = 250  # 每块最多包含的段落数
MAX_CONTENT_LENGTH = 30000    # 字符数
# 重试配置
MAX_RETRIES = 5  # 增加重试次数
BASE_DELAY = 2  # 基础延迟时间（秒）
MAX_DELAY = 60  # 最大延迟时间（秒）
# 分块处理容错配置
MAX_FAILED_CHUNKS_RATIO = 0.3  # 允许最多30%的块失败

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

    def _call_gpt_with_retry(self, messages: list, chunk_info: str = "") -> str:
        """
        带重试机制的GPT调用
        """
        last_exception = None
        
        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"GPT调用尝试 {attempt + 1}/{MAX_RETRIES} {chunk_info}")
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature
                )
                
                content = response.choices[0].message.content
                if not content or content.strip() == "":
                    raise Exception("GPT返回空内容")
                
                return content.strip()
                
            except (APIConnectionError, APITimeoutError) as e:
                last_exception = e
                error_msg = f"网络连接错误 {chunk_info}: {str(e)}"
                logger.warning(f"第{attempt + 1}次尝试失败 - {error_msg}")
                
                if attempt < MAX_RETRIES - 1:
                    # 指数退避延迟
                    delay = min(BASE_DELAY * (2 ** attempt) + random.uniform(0, 1), MAX_DELAY)
                    logger.info(f"等待 {delay:.2f} 秒后重试...")
                    time.sleep(delay)
                else:
                    logger.error(f"网络连接失败，已达最大重试次数 {chunk_info}")
                    
            except RateLimitError as e:
                last_exception = e
                error_msg = f"API速率限制 {chunk_info}: {str(e)}"
                logger.warning(f"第{attempt + 1}次尝试失败 - {error_msg}")
                
                if attempt < MAX_RETRIES - 1:
                    # 速率限制时使用更长的延迟
                    delay = min(BASE_DELAY * (3 ** attempt) + random.uniform(1, 3), MAX_DELAY)
                    logger.info(f"遇到速率限制，等待 {delay:.2f} 秒后重试...")
                    time.sleep(delay)
                else:
                    logger.error(f"API速率限制，已达最大重试次数 {chunk_info}")
                    
            except APIError as e:
                last_exception = e
                error_code = getattr(e, 'status_code', 'unknown')
                error_msg = f"API服务错误 {chunk_info} (状态码: {error_code}): {str(e)}"
                logger.warning(f"第{attempt + 1}次尝试失败 - {error_msg}")
                
                # 对于某些错误码，不需要重试
                if hasattr(e, 'status_code') and e.status_code in [400, 401, 403, 404]:
                    logger.error(f"API错误不可重试 {chunk_info}: {error_code}")
                    break
                # 对于500/503等服务器错误，使用更长的延迟
                elif hasattr(e, 'status_code') and e.status_code in [500, 502, 503, 504]:
                    if attempt < MAX_RETRIES - 1:
                        delay = min(BASE_DELAY * (3 ** attempt) + random.uniform(1, 5), MAX_DELAY)
                        logger.info(f"服务器内部错误，等待 {delay:.2f} 秒后重试...")
                        time.sleep(delay)
                    else:
                        logger.error(f"API服务器错误，已达最大重试次数 {chunk_info}")
                else:
                    if attempt < MAX_RETRIES - 1:
                        delay = min(BASE_DELAY * (2 ** attempt) + random.uniform(0, 1), MAX_DELAY)
                        logger.info(f"API服务错误，等待 {delay:.2f} 秒后重试...")
                        time.sleep(delay)
                    else:
                        logger.error(f"API服务错误，已达最大重试次数 {chunk_info}")
                    
            except Exception as e:
                last_exception = e
                error_msg = f"未知错误 {chunk_info}: {str(e)}"
                logger.warning(f"第{attempt + 1}次尝试失败 - {error_msg}")
                
                if attempt < MAX_RETRIES - 1:
                    delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                    logger.info(f"遇到未知错误，等待 {delay:.2f} 秒后重试...")
                    time.sleep(delay)
                else:
                    logger.error(f"未知错误，已达最大重试次数 {chunk_info}")
        
        # 所有重试都失败了
        error_type = type(last_exception).__name__ if last_exception else "UnknownError"
        raise Exception(f"GPT调用失败 {chunk_info}，已重试{MAX_RETRIES}次。最后错误类型: {error_type}，错误信息: {str(last_exception)}")

    def _format_user_friendly_error(self, error: Exception, stage: str = "") -> str:
        """
        将技术错误信息转换为用户友好的描述
        """
        error_str = str(error)
        error_type = type(error).__name__
        
        if "Connection error" in error_str or "APIConnectionError" in error_type:
            return f"{stage}阶段网络连接失败，请检查网络连接或稍后重试"
        elif "timeout" in error_str.lower() or "APITimeoutError" in error_type:
            return f"{stage}阶段请求超时，服务器响应缓慢，请稍后重试"
        elif "rate limit" in error_str.lower() or "RateLimitError" in error_type:
            return f"{stage}阶段API调用频率过高，请稍后重试"
        elif "500" in error_str and "Internal Server Error" in error_str:
            return f"{stage}阶段AI服务暂时不可用，请稍后重试"
        elif "401" in error_str or "authentication" in error_str.lower():
            return f"{stage}阶段API认证失败，请检查API密钥配置"
        elif "400" in error_str or "Bad Request" in error_str:
            return f"{stage}阶段请求格式错误，可能是视频内容过长或格式不支持"
        elif "GPT返回空内容" in error_str:
            return f"{stage}阶段AI未返回有效内容，可能是输入内容不适合处理"
        elif "已重试" in error_str and "次" in error_str:
            return f"{stage}阶段多次重试后仍然失败，服务可能暂时不稳定"
        else:
            return f"{stage}阶段处理失败: {error_str}"

    def _generate_comprehensive_error_message(self, main_error: str, fallback_error: str) -> str:
        """
        生成综合的错误信息，提供用户可操作的建议
        """
        error_suggestions = []
        
        # 分析错误类型并提供建议
        if "网络连接" in main_error or "网络连接" in fallback_error:
            error_suggestions.append("检查网络连接是否正常")
            error_suggestions.append("确认是否能正常访问AI服务")
            
        if "timeout" in main_error.lower() or "timeout" in fallback_error.lower():
            error_suggestions.append("视频内容可能过长，建议使用较短的视频")
            error_suggestions.append("稍后重试，服务器可能暂时繁忙")
            
        if "rate limit" in main_error.lower() or "rate limit" in fallback_error.lower():
            error_suggestions.append("等待几分钟后再次尝试")
            error_suggestions.append("检查API配额是否充足")
            
        if "500" in main_error or "500" in fallback_error:
            error_suggestions.append("AI服务暂时不稳定，请稍后重试")
            error_suggestions.append("如果问题持续，请联系管理员")
            
        if "authentication" in main_error.lower() or "authentication" in fallback_error.lower():
            error_suggestions.append("检查API密钥是否正确配置")
            error_suggestions.append("确认API密钥是否有效且未过期")
        
        # 默认建议
        if not error_suggestions:
            error_suggestions = [
                "稍后重试此操作",
                "检查视频内容是否过长或格式是否支持",
                "如果问题持续，请联系技术支持"
            ]
        
        suggestions_text = "建议尝试以下解决方案:\n" + "\n".join(f"• {suggestion}" for suggestion in error_suggestions)
        
        return f"视频笔记生成失败。{suggestions_text}"

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
            
            return self._call_gpt_with_retry(messages, "(主处理)")
        except Exception as e:
            error_msg = self._format_user_friendly_error(e, "主处理")
            logger.error(f"GPT主处理失败 - {error_msg}")
            print(f"主处理失败: {error_msg}")
            
            # 如果处理失败，尝试使用分段处理方法
            print("尝试使用分段处理方法作为备用方案...")
            try:
                return self._process_long_content_by_chunks(source)
            except Exception as fallback_error:
                fallback_msg = self._format_user_friendly_error(fallback_error, "分段处理")
                logger.error(f"GPT分段处理也失败 - {fallback_msg}")
                
                # 生成综合的用户友好错误信息
                final_error_msg = self._generate_comprehensive_error_message(str(e), str(fallback_error))
                raise Exception(final_error_msg)

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
        failed_chunks = []
        
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
                
                chunk_summary = self._call_gpt_with_retry(chunk_messages, f"(第{i+1}/{num_chunks}块)")
                chunk_summaries.append(f"### 第{i+1}部分内容总结\n\n{chunk_summary}")
                
                print(f"第{i+1}块处理完成")
                
            except Exception as e:
                error_msg = self._format_user_friendly_error(e, f"第{i+1}块处理")
                print(f"第{i+1}块处理失败: {error_msg}")
                logger.error(f"GPT第{i+1}块处理失败 - {error_msg}")
                
                failed_chunks.append(i+1)
                # 添加失败块的占位符，保持结构完整性
                chunk_summaries.append(f"### 第{i+1}部分内容总结\n\n*[此部分处理失败: {error_msg}]*")
                
                # 检查失败率是否超过阈值
                failed_ratio = len(failed_chunks) / num_chunks
                if failed_ratio > MAX_FAILED_CHUNKS_RATIO:
                    raise Exception(f"视频分段处理失败率过高({failed_ratio:.1%})，已停止处理。失败的块: {failed_chunks}。建议稍后重试或使用较短的视频内容。")
                
                print(f"继续处理剩余块... (当前失败率: {failed_ratio:.1%})")
        
        # 检查整体结果
        total_chunks = len(chunk_summaries)
        successful_chunks = total_chunks - len(failed_chunks)
        
        if len(failed_chunks) == total_chunks:
            # 所有块都失败的情况
            raise Exception(f"所有视频分段都处理失败。失败的块: {failed_chunks}。建议检查网络连接或稍后重试。")
        elif len(failed_chunks) > 0:
            # 部分块失败的情况，记录警告但继续处理
            failed_ratio = len(failed_chunks) / total_chunks
            logger.warning(f"部分分段处理失败 ({failed_ratio:.1%})，失败的块: {failed_chunks}")
            print(f"警告: {len(failed_chunks)}/{total_chunks}个分段处理失败，将继续使用成功的{successful_chunks}个分段生成笔记")
        
        # 检查最终结果质量
        if successful_chunks < total_chunks * 0.5:
            # 如果成功块少于50%，警告用户
            logger.warning(f"仅{successful_chunks}/{total_chunks}个分段成功处理，笔记质量可能不佳")
            print(f"警告: 仅{successful_chunks}/{total_chunks}个分段成功处理，生成的笔记可能不完整")
        # 合并所有块的总结
        all_summaries = "\n\n".join(chunk_summaries)
        
        # 如果有失败的块，在内容中添加说明
        if failed_chunks:
            all_summaries += f"\n\n---\n\n**注意**: 由于网络或服务问题，第{failed_chunks}部分内容未能成功处理。已使用其余{successful_chunks}个部分生成笔记。"
            all_summaries += f"\n\n---\n\n**注意**: 由于网络或服务问题，第{failed_chunks}部分内容未能成功处理。已使用其余{successful_chunks}个部分生成笔记。"
        
        # 创建最终总结请求
        final_segment = TranscriptSegment(start=0, end=0, text=all_summaries)
        final_source = GPTSource(
            title=source.title,
            segment=[final_segment],
            tags=source.tags,
            screenshot=source.screenshot,
            video_img_urls=[],  # 最终合并阶段不传递图片，避免VLM模型错误
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
            
            final_result = self._call_gpt_with_retry(final_messages, "(最终合并)")
            
            # 如果有失败的块，在最终结果中添加说明
            if failed_chunks:
                final_result += f"\n\n---\n\n**处理说明**: 由于服务不稳定，第{failed_chunks}部分内容未能成功处理。本笔记基于其余{successful_chunks}个部分生成。"
            
            return final_result
            
        except Exception as e:
            error_msg = self._format_user_friendly_error(e, "最终合并")
            print(f"最终合并失败: {error_msg}")
            logger.error(f"GPT最终合并失败 - {error_msg}")
            
            # 如果最终合并失败，返回已成功处理的块的直接拼接结果
            if chunk_summaries and successful_chunks > 0:
                logger.info(f"最终合并失败，使用直接拼接作为降级方案")
                print(f"最终合并失败，使用已成功处理的{successful_chunks}个部分直接拼接")
                
                fallback_result = all_summaries
                if failed_chunks:
                    fallback_result += f"\n\n---\n\n**处理说明**: 由于服务不稳定，第{failed_chunks}部分内容未能成功处理，最终整合阶段也出现问题。本笔记为各部分的直接拼接结果。"
                return fallback_result
            else:
                # 如果没有任何成功的块，抛出异常
                raise Exception(f"视频笔记最终整合失败: {error_msg}。所有部分均处理失败。")
