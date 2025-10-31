from openai import OpenAI

from app.gpt.base import GPT
from app.gpt.provider.OpenAI_compatible_provider import OpenAICompatibleProvider
from app.gpt.provider.SiliconFlow_provider import SiliconFlowProvider
from app.gpt.universal_gpt import UniversalGPT
from app.models.model_config import ModelConfig


class GPTFactory:
    @staticmethod
    def from_config(config: ModelConfig) -> GPT:
        # 检查是否是硅基流动，使用专门的提供商类
        if "siliconflow" in config.base_url.lower():
            provider = SiliconFlowProvider(
                api_key=config.api_key,
                base_url=config.base_url,
                model=config.model_name
            )
            return UniversalGPT(client=provider.get_client, model=config.model_name, provider=provider)
        else:
            # 其他提供商使用通用兼容类
            provider = OpenAICompatibleProvider(
                api_key=config.api_key,
                base_url=config.base_url
            )
            # 传递provider实例，以便使用Cloudscraper备用方案
            return UniversalGPT(client=provider.get_client, model=config.model_name, provider=provider)