from typing import Optional, Union

from openai import OpenAI

from app.utils.logger import get_logger

logging= get_logger(__name__)

class OpenAICompatibleProvider:
    def __init__(self, api_key: str, base_url: str, model: Union[str, None]=None):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    @property
    def get_client(self):
        return self.client

    @staticmethod
    def test_connection(api_key: str, base_url: str) -> bool:
        try:
            # 调试：打印API Key的实际长度和内容
            logging.info(f"正在测试连接 - API Key长度: {len(api_key)}, 前8位: {api_key[:8]}, 后4位: {api_key[-4:] if len(api_key) > 4 else 'TOO_SHORT'}")
            logging.info(f"Base URL: {base_url}")
            
            # 硅基流动特殊处理：参考Cherry Studio的实现方式
            if "siliconflow" in base_url.lower():
                logging.info("检测到硅基流动，参考Cherry Studio实现方式")
                
                # 标准化URL处理，避免路径重复
                base_url_clean = base_url.rstrip('/')
                
                if base_url_clean.endswith("/v1"):
                    # 如果用户输入了/v1，直接使用
                    api_base = base_url_clean
                    test_url = f"{api_base}/chat/completions"
                elif base_url_clean.endswith("/chat/completions"):
                    # 如果用户直接输入了完整路径，直接使用
                    test_url = base_url_clean
                    api_base = base_url_clean.replace("/chat/completions", "")
                else:
                    # Cherry Studio方式：不加/v1后缀，直接加/chat/completions
                    api_base = base_url_clean
                    test_url = f"{base_url_clean}/chat/completions"
                
                logging.info(f"使用API基地址: {api_base}")
                logging.info(f"测试URL: {test_url}")
                
                # 先用requests验证（Cherry Studio方式）
                import requests
                import json
                
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "Qwen/Qwen2.5-7B-Instruct",
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 1
                }
                
                try:
                    logging.info("Cherry Studio方式：直接HTTP请求测试")
                    response = requests.post(test_url, headers=headers, json=payload, timeout=15)
                    logging.info(f"HTTP响应状态码: {response.status_code}")
                    
                    if response.status_code == 200:
                        logging.info("硅基流动连接测试成功（Cherry Studio方式）")
                        result = response.json()
                        logging.info(f"响应: {json.dumps(result, ensure_ascii=False)[:100]}...")
                        return True
                    else:
                        logging.error(f"HTTP请求失败: {response.status_code} - {response.text}")
                        
                        # 尝试不同的端点
                        if response.status_code == 404 and "/v1" in test_url:
                            # 尝试去掉/v1
                            alt_url = test_url.replace("/v1", "")
                            logging.info(f"尝试备用URL: {alt_url}")
                            alt_response = requests.post(alt_url, headers=headers, json=payload, timeout=15)
                            if alt_response.status_code == 200:
                                logging.info("硅基流动连接测试成功（备用URL）")
                                return True
                                
                except Exception as http_error:
                    logging.error(f"直接HTTP请求异常: {http_error}")
            
            # 标准OpenAI SDK方式作为备选
            # 对于硅基流动，需要使用正确的base_url
            if "siliconflow" in base_url.lower():
                # 确保SDK使用正确的base_url（需要包含/v1）
                sdk_base_url = api_base if api_base.endswith('/v1') else f"{api_base}/v1"
                client = OpenAI(api_key=api_key, base_url=sdk_base_url)
                logging.info(f"尝试OpenAI SDK方式，使用base_url: {sdk_base_url}")
            else:
                # 为其他OpenAI兼容服务（如new-api）设置合适的超时
                client = OpenAI(
                    api_key=api_key, 
                    base_url=base_url,
                    timeout=30.0  # 增加超时时间
                )
                logging.info(f"创建OpenAI客户端，base_url: {base_url}")
            
            if "siliconflow" in base_url.lower():
                # 硅基流动的免费模型列表
                test_models = [
                    "Qwen/Qwen2.5-7B-Instruct",
                    "THUDM/glm-4-9b-chat", 
                    "deepseek-ai/DeepSeek-V3"
                ]
                
                for model in test_models:
                    try:
                        logging.info(f"尝试测试模型: {model}")
                        response = client.chat.completions.create(
                            model=model,
                            messages=[{"role": "user", "content": "hi"}],
                            max_tokens=1,
                            timeout=15.0
                        )
                        logging.info(f"硅基流动连接测试成功，使用模型: {model}")
                        return True
                    except Exception as model_error:
                        error_msg = str(model_error)
                        logging.warning(f"模型 {model} 测试失败: {error_msg}")
                        
                        if "401" in error_msg or "Unauthorized" in error_msg or "Api key is invalid" in error_msg:
                            raise Exception("API Key 无效或已过期，请检查API Key是否正确")
                        continue
                
                # 尝试models接口
                try:
                    models = client.models.list()
                    logging.info("硅基流动连接测试成功（通过models接口）")
                    return True
                except Exception as models_error:
                    logging.error(f"models接口失败: {models_error}")
                    raise models_error
            else:
                # 非硅基流动提供商（如new-api等自建服务）
                try:
                    logging.info("尝试通过models.list()测试连接...")
                    models = client.models.list()
                    logging.info(f"models.list()成功，获取到{len(models.data)}个模型")
                    if models.data:
                        logging.info(f"第一个可用模型: {models.data[0].id}")
                    return True
                except Exception as models_error:
                    models_error_msg = str(models_error)
                    logging.warning(f"models.list()失败: {models_error_msg}")
                    
                    # 如果models接口失败，尝试直接调用chat completion
                    try:
                        logging.info("models接口失败，尝试chat completions接口...")
                        # 尝试一些常见的模型名
                        test_models = ["gpt-3.5-turbo", "gpt-4", "text-davinci-003", "claude-3-haiku"]
                        
                        for model in test_models:
                            try:
                                logging.info(f"测试模型: {model}")
                                response = client.chat.completions.create(
                                    model=model,
                                    messages=[{"role": "user", "content": "test"}],
                                    max_tokens=1,
                                    timeout=15.0
                                )
                                logging.info(f"连通性测试成功，使用模型: {model}")
                                return True
                            except Exception as model_error:
                                error_msg = str(model_error)
                                logging.debug(f"模型 {model} 测试失败: {error_msg}")
                                if "401" in error_msg or "Unauthorized" in error_msg:
                                    raise Exception("API Key 无效或已过期")
                                # 继续尝试下一个模型
                                continue
                        
                        # 如果所有测试模型都失败，抛出原始的models错误
                        raise models_error
                        
                    except Exception as chat_error:
                        if chat_error == models_error:
                            # 重新抛出models错误
                            raise models_error
                        else:
                            # 抛出chat错误
                            raise chat_error
            
        except Exception as e:
            error_msg = str(e)
            logging.error(f"连通性测试失败：{error_msg}")
            
            # 详细记录异常信息用于调试
            import traceback
            logging.error(f"详细错误堆栈：{traceback.format_exc()}")
            
            # 根据错误类型提供更具体的错误信息
            if "401" in error_msg or "Unauthorized" in error_msg or "Api key is invalid" in error_msg:
                raise Exception("API Key 无效或已过期，请检查API Key是否正确")
            elif "404" in error_msg or "Not Found" in error_msg:
                if "siliconflow" in base_url.lower():
                    raise Exception("API 地址可能不正确。建议尝试: https://api.siliconflow.cn/v1 或 https://api.siliconflow.cn（参考Cherry Studio配置）")
                else:
                    raise Exception(f"API 地址不正确，请检查 base_url 格式。当前地址: {base_url}")
            elif "timeout" in error_msg.lower():
                raise Exception(f"连接超时，请检查网络连接或 API 地址是否正确。超时详情: {error_msg}")
            elif "ssl" in error_msg.lower() or "certificate" in error_msg.lower():
                raise Exception("SSL 证书验证失败，请检查 API 地址是否使用 HTTPS")
            elif "connection" in error_msg.lower():
                if "siliconflow" in base_url.lower():
                    raise Exception("无法连接到硅基流动服务器，请尝试: https://api.siliconflow.cn/v1 或 https://api.siliconflow.cn")
                else:
                    raise Exception(f"无法连接到服务器，请检查 API 地址和网络连接。连接详情: {error_msg}")
            elif "_set_private_attributes" in error_msg:
                raise Exception("OpenAI SDK版本兼容性问题，请尝试重新配置或联系管理员")
            elif "ConnectTimeout" in error_msg or "ReadTimeout" in error_msg:
                raise Exception(f"网络请求超时，请检查网络连接。详情: {error_msg}")
            elif "RemoteDisconnected" in error_msg or "ConnectionError" in error_msg:
                raise Exception(f"远程服务器连接断开或拒绝连接。详情: {error_msg}")
            else:
                raise Exception(f"连接失败。完整错误信息: {error_msg}")

            return False