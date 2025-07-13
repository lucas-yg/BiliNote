from typing import Optional, Union, List
from openai import OpenAI
from app.utils.logger import get_logger

logger = get_logger(__name__)

class SiliconFlowProvider:
    """
    专门为硅基流动(SiliconFlow)优化的提供商类
    基于市面上成熟的接入方案设计
    """
    
    # 硅基流动支持的常用模型列表
    SUPPORTED_MODELS = [
        "deepseek-ai/DeepSeek-V3",
        "deepseek-ai/DeepSeek-R1", 
        "Qwen/Qwen2.5-72B-Instruct",
        "Qwen/Qwen2.5-32B-Instruct",
        "Qwen/Qwen2.5-14B-Instruct",
        "Qwen/Qwen2.5-7B-Instruct",
        "meta-llama/Llama-3.1-70B-Instruct",
        "meta-llama/Llama-3.1-8B-Instruct",
        "THUDM/glm-4-9b-chat",
        "01-ai/Yi-1.5-34B-Chat"
    ]
    
    # 硅基流动API端点
    API_ENDPOINTS = [
        "https://api.siliconflow.cn/v1",  # 国内用户
        "https://api-st.siliconflow.cn/v1"  # 海外用户
    ]
    
    def __init__(self, api_key: str, base_url: str = None, model: Union[str, None] = None):
        """
        初始化硅基流动提供商
        
        Args:
            api_key: API密钥
            base_url: API基础URL，默认使用国内端点
            model: 模型名称
        """
        self.api_key = api_key
        
        # 标准化base_url，确保符合硅基流动API要求
        if base_url:
            base_url_clean = base_url.rstrip('/')
            # 确保使用正确的API端点格式
            if not base_url_clean.endswith('/v1'):
                if base_url_clean.endswith('/chat/completions'):
                    # 用户输入了完整的endpoint，提取base部分并添加/v1
                    base_url_clean = base_url_clean.replace('/chat/completions', '/v1')
                elif 'siliconflow' in base_url_clean.lower():
                    # 硅基流动需要/v1后缀
                    base_url_clean = f"{base_url_clean}/v1"
            self.base_url = base_url_clean
        else:
            self.base_url = self.API_ENDPOINTS[0]
            
        self.model = model
        logger.info(f"硅基流动提供商初始化 - 使用base_url: {self.base_url}")
        self.client = OpenAI(api_key=api_key, base_url=self.base_url)
    
    @property
    def get_client(self):
        return self.client
    
    @classmethod
    def test_connection(cls, api_key: str, base_url: str = None) -> bool:
        """
        测试硅基流动连接
        使用成熟的chat接口测试方法，而非models接口
        
        Args:
            api_key: API密钥
            base_url: API基础URL
            
        Returns:
            bool: 连接是否成功
        """
        base_url = base_url or cls.API_ENDPOINTS[0]
        
        try:
            logger.info(f"测试硅基流动连接 - API Key: {api_key[:8]}...（已截断） Base URL: {base_url}")
            
            client = OpenAI(api_key=api_key, base_url=base_url)
            
            # 使用轻量级模型进行连接测试
            test_models = [
                "Qwen/Qwen2.5-7B-Instruct",  # 免费模型优先
                "deepseek-ai/DeepSeek-V3",
                "THUDM/glm-4-9b-chat"
            ]
            
            for model in test_models:
                try:
                    logger.info(f"尝试测试模型: {model}")
                    
                    # 发送简单的chat请求测试连接
                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "user", "content": "hi"}
                        ],
                        max_tokens=1,
                        timeout=15.0
                    )
                    
                    logger.info(f"硅基流动连接测试成功 - 模型: {model}")
                    return True
                    
                except Exception as model_error:
                    error_msg = str(model_error)
                    logger.warning(f"模型 {model} 测试失败: {error_msg}")
                    
                    # 如果是401错误（API Key问题），不继续尝试其他模型
                    if "401" in error_msg or "Unauthorized" in error_msg or "Api key is invalid" in error_msg:
                        raise Exception("API Key 无效或已过期，请检查API Key是否正确")
                    
                    continue
            
            # 如果所有模型都失败，尝试models接口作为最后手段
            logger.info("所有模型测试失败，尝试models接口")
            try:
                models = client.models.list()
                logger.info("硅基流动连接测试成功（通过models接口）")
                return True
            except Exception as models_error:
                logger.error(f"models接口也失败: {models_error}")
                raise models_error
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"硅基流动连接测试失败：{error_msg}")
            
            # 根据错误类型提供具体的错误信息
            if "401" in error_msg or "Unauthorized" in error_msg or "Api key is invalid" in error_msg:
                raise Exception("API Key 无效或已过期，请检查API Key是否正确")
            elif "404" in error_msg or "Not Found" in error_msg:
                raise Exception(f"API地址不正确，请检查URL格式。推荐使用: {cls.API_ENDPOINTS[0]} 或 {cls.API_ENDPOINTS[1]}")
            elif "timeout" in error_msg.lower():
                raise Exception("连接超时，请检查网络连接或尝试海外端点")
            elif "connection" in error_msg.lower():
                raise Exception(f"无法连接到硅基流动服务器，请尝试: {cls.API_ENDPOINTS[1]}")
            else:
                raise Exception(f"连接失败: {error_msg}")
    
    def list_models(self):
        """
        获取可用模型列表
        优先返回预定义的模型列表，如果API支持则获取实时列表
        """
        try:
            # 尝试获取实时模型列表
            models = self.client.models.list()
            logger.info("成功获取硅基流动实时模型列表")
            return models
        except Exception as e:
            logger.warning(f"无法获取实时模型列表，返回预定义列表: {e}")
            # 返回预定义的模型列表
            from types import SimpleNamespace
            
            model_objects = []
            for model_name in self.SUPPORTED_MODELS:
                model_obj = SimpleNamespace()
                model_obj.id = model_name
                model_obj.object = "model"
                model_obj.created = 1640995200  # 固定时间戳
                model_obj.owned_by = "siliconflow"
                
                # 添加dict方法
                def dict_method():
                    return {
                        "id": model_name,
                        "object": "model", 
                        "created": 1640995200,
                        "owned_by": "siliconflow"
                    }
                model_obj.dict = dict_method
                model_objects.append(model_obj)
            
            # 构造兼容的返回对象
            result = SimpleNamespace()
            result.data = model_objects
            return result
    
    def create_chat_completion(self, model: str, messages: list, **kwargs):
        """
        创建聊天完成请求
        """
        return self.client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs
        )
    
    @classmethod
    def get_recommended_config(cls) -> dict:
        """
        获取推荐的硅基流动配置
        """
        return {
            "name": "硅基流动",
            "type": "custom", 
            "base_url": cls.API_ENDPOINTS[0],
            "logo": "SiliconFlow",
            "supported_models": cls.SUPPORTED_MODELS,
            "description": "硅基流动 - 免费高性能AI模型服务",
            "features": [
                "完全兼容OpenAI API",
                "支持多种开源大模型", 
                "部分模型永久免费",
                "国内外双端点支持"
            ]
        }