from typing import Optional, Union
from urllib.parse import urlparse
import time
import json
import warnings
import threading

from openai import OpenAI
import httpx

from app.services.cookie_manager import CookieConfigManager
from app.utils.logger import get_logger

# 抑制SSL警告
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    pass

# Cloudscraper 已移除，不再支持
CLOUDSCRAPER_AVAILABLE = False

logging = get_logger(__name__)

try:
    import h2  # noqa: F401
    HTTP2_AVAILABLE = True
except ImportError:
    HTTP2_AVAILABLE = False

HTTP2_WARNING_EMITTED = False
COOKIE_MANAGER = CookieConfigManager()

# Cloudscraper 相关功能已移除


def _warn_http2_disabled_once() -> None:
    global HTTP2_WARNING_EMITTED
    if HTTP2_AVAILABLE or HTTP2_WARNING_EMITTED:
        return
    logging.warning("未安装h2模块，将使用HTTP/1.1访问兼容API；可执行 pip install 'httpx[http2]' 以启用HTTP/2")
    HTTP2_WARNING_EMITTED = True


def _normalize_cookie(cookie: Optional[str]) -> Optional[str]:
    if not cookie:
        return None
    # 允许用户粘贴 `key:value` 或换行分隔的形式，统一转为标准Cookie头
    raw = cookie.replace('\n', ';').strip()
    if not raw:
        return None

    normalized_parts = []
    for segment in raw.split(';'):
        piece = segment.strip()
        if not piece:
            continue
        if ':' in piece and '=' not in piece:
            key, value = piece.split(':', 1)
            piece = f"{key.strip()}={value.strip()}"
        normalized_parts.append(piece)

    if not normalized_parts:
        return None
    return '; '.join(normalized_parts)


def _resolve_cookie_for_base_url(base_url: str, override_cookie: Optional[str] = None) -> Optional[str]:
    if override_cookie:
        normalized = _normalize_cookie(override_cookie)
        if normalized:
            return normalized

    parsed = urlparse(base_url)
    host = parsed.netloc or base_url
    stored_cookie = COOKIE_MANAGER.get(host)
    normalized = _normalize_cookie(stored_cookie)
    if normalized:
        logging.debug(f"读取到 {host} 的Cookie配置")
    return normalized


def _build_cookie_jar(base_url: str, override_cookie: Optional[str] = None) -> Optional[httpx.Cookies]:
    cookie_string = _resolve_cookie_for_base_url(base_url, override_cookie)
    if not cookie_string:
        return None

    jar = httpx.Cookies()
    try:
        jar.update_from_header(cookie_string)
    except Exception as exc:
        logging.warning(f"Cookie格式解析失败，将忽略本次Cookie。内容: {cookie_string}，错误: {exc}")
        return None
    return jar

class OpenAICompatibleProvider:
    def __init__(self, api_key: str, base_url: str, model: Union[str, None]=None, cookie: Optional[str] = None):
        # 标准化base_url，确保以/v1结尾（OpenAI兼容API标准）
        base_url = base_url.rstrip('/')
        if not base_url.endswith('/v1'):
            # 如果base_url不以/v1结尾，自动添加
            base_url = f"{base_url}/v1"
            logging.info(f"自动添加/v1到base_url: {base_url}")

        self.browser_headers = self._build_browser_like_headers(base_url)
        _warn_http2_disabled_once()

        cookie_jar = _build_cookie_jar(base_url, cookie)

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=httpx.Client(
                verify=False,
                http2=HTTP2_AVAILABLE,
                headers=self.browser_headers,
                timeout=30.0,
                cookies=cookie_jar,
                follow_redirects=True,
            )  # 禁用SSL验证并伪装浏览器流量
        )
        self.model = model

        # Cloudscraper 备用客户端已移除
        self.cloudscraper_client = None

    @staticmethod
    def _build_browser_like_headers(base_url: str) -> dict:
        """构造类浏览器请求头，降低被Cloudflare误判的概率"""
        parsed = urlparse(base_url)
        origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else base_url
        # 仿造Chromium系浏览器的常见头部，与Cherry Studio抓包结果保持一致
        return {
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Sec-CH-UA": '\"Not)A;Brand\";v="8", \"Chromium\";v="122", \"Google Chrome\";v="122"',
            "Sec-CH-UA-Platform": '\"macOS\"',
            "Sec-CH-UA-Mobile": "?0",
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Referer": origin,
        }

    @property
    def get_client(self):
        return self.client

    def list_models(self):
        """获取模型列表（支持 Cloudscraper 备用）"""
        return self.list_models_with_fallback()

    # Cloudscraper 相关方法已移除

    def list_models_with_fallback(self):
        """模型列表获取（移除Cloudscraper备用机制）"""
        try:
            # 首先尝试原始方法
            result = self.client.models.list()
            return result
        except Exception as primary_error:
            error_msg = str(primary_error).lower()
            error_str = str(primary_error)

            # 检查是否是压缩数据解析错误 (乱码/二进制数据)
            is_decompression_error = (
                'blocked' in error_msg or
                '403' in error_msg or
                "object has no attribute '_set_private_attributes'" in error_msg or
                not error_str.isprintable()  # 检测乱码/二进制数据
            )

            if is_decompression_error:
                # 尝试使用 requests 直接请求，它有更好的压缩处理
                logging.warning("检测到响应解析问题，尝试使用 requests 备用方案")
                try:
                    import requests

                    base_url = str(self.client.base_url).rstrip('/')
                    models_url = f"{base_url}/models"

                    headers = self.browser_headers.copy()
                    headers['Authorization'] = f"Bearer {self.client.api_key}"

                    response = requests.get(
                        models_url,
                        headers=headers,
                        verify=False,
                        timeout=30.0
                    )

                    if response.status_code == 200:
                        response_data = response.json()

                        # 构造兼容的返回对象
                        class ModelObject:
                            """模拟OpenAI SDK的Model对象"""
                            def __init__(self, model_dict):
                                self.id = model_dict.get('id', '')
                                self.object = model_dict.get('object', 'model')
                                self.created = model_dict.get('created', 0)
                                self.owned_by = model_dict.get('owned_by', 'unknown')
                                self._raw_dict = model_dict

                            def dict(self):
                                """返回字典格式，兼容OpenAI SDK"""
                                return self._raw_dict

                        class RequestsModelList:
                            def __init__(self, data):
                                # 将dict列表转换为ModelObject列表
                                if isinstance(data, list):
                                    self.data = [ModelObject(m) if isinstance(m, dict) else m for m in data]
                                else:
                                    self.data = []

                        models = response_data.get('data', []) if isinstance(response_data, dict) else response_data
                        logging.info(f"使用 requests 成功获取 {len(models)} 个模型")
                        return RequestsModelList(models)
                    else:
                        logging.error(f"requests 备用方案失败: HTTP {response.status_code}")

                except Exception as requests_error:
                    logging.error(f"requests 备用方案失败: {requests_error}")

            # 如果所有备用方案都失败，返回空列表
            logging.error(f"获取模型列表失败: {primary_error}")
            class EmptyModelList:
                def __init__(self):
                    self.data = []
            return EmptyModelList()

    @staticmethod
    def test_connection(api_key: str, base_url: str, cookie: Optional[str] = None) -> bool:
        try:
            # 调试：打印API Key的实际长度和内容
            logging.info(f"正在测试连接 - API Key长度: {len(api_key)}, 前8位: {api_key[:8]}, 后4位: {api_key[-4:] if len(api_key) > 4 else 'TOO_SHORT'}")
            logging.info(f"Base URL: {base_url}")
            _warn_http2_disabled_once()
            cookie_string = _resolve_cookie_for_base_url(base_url, cookie)
            if cookie_string:
                logging.info("已加载Cookie，尝试以持久会话访问目标API")
            
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
                    **OpenAICompatibleProvider._build_browser_like_headers(base_url),
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                if cookie_string:
                    headers["Cookie"] = cookie_string
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
                # 添加 SSL 验证控制
                import httpx
                client = OpenAI(
                    api_key=api_key,
                    base_url=sdk_base_url,
                    http_client=httpx.Client(
                        verify=False,
                        http2=HTTP2_AVAILABLE,
                        headers=OpenAICompatibleProvider._build_browser_like_headers(sdk_base_url),
                        timeout=30.0,
                        cookies=_build_cookie_jar(sdk_base_url, cookie_string)
                    )
                )
                logging.info(f"尝试OpenAI SDK方式，使用base_url: {sdk_base_url}（已禁用SSL验证）")
            else:
                # 为其他OpenAI兼容服务（如new-api）设置合适的超时和SSL控制
                import httpx
                client = OpenAI(
                    api_key=api_key,
                    base_url=base_url,
                    timeout=30.0,  # 增加超时时间
                    http_client=httpx.Client(
                        verify=False,
                        http2=HTTP2_AVAILABLE,
                        headers=OpenAICompatibleProvider._build_browser_like_headers(base_url),
                        cookies=_build_cookie_jar(base_url, cookie_string),
                    )  # 禁用SSL验证并启用HTTP/2
                )
                logging.info(f"创建OpenAI客户端，base_url: {base_url}（已禁用SSL验证）")
            
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
                        time.sleep(1.5)
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
                        # 尝试一些常见的模型名（包括New API支持的模型）
                        test_models = [
                            "gpt-3.5-turbo",
                            "gpt-4",
                            "Qwen/Qwen2.5-7B-Instruct",
                        ]
                        
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
                                time.sleep(1.5)  # 避免触发频率限制
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

            # Cloudscraper 备用方案已移除

            # 检查是否为Cloudflare阻塞，返回统一的错误信息
            if "cloudflare" in error_msg.lower() or "attention required" in error_msg.lower() or "blocked" in error_msg.lower():
                raise Exception("检测到Cloudflare保护，请尝试配置Cookie绕过或联系API提供商获取访问权限")

            # 重新抛出原始异常
            raise

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


# Cloudscraper 连接测试函数已移除
