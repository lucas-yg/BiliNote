"""
硅基流动快速配置工具
基于市面上成熟的接入方案
"""

from app.gpt.provider.SiliconFlow_provider import SiliconFlowProvider

class SiliconFlowSetupHelper:
    """硅基流动配置助手"""
    
    @classmethod
    def get_quick_setup_guide(cls) -> dict:
        """获取快速配置指南"""
        return {
            "title": "硅基流动(SiliconFlow)快速配置指南",
            "steps": [
                {
                    "step": 1,
                    "title": "获取API密钥",
                    "description": "访问 https://cloud.siliconflow.cn/account/ak 获取API密钥",
                    "note": "需要先注册账号并登录"
                },
                {
                    "step": 2, 
                    "title": "选择API端点",
                    "description": "根据地理位置选择合适的端点",
                    "options": {
                        "国内用户": "https://api.siliconflow.cn/v1",
                        "海外用户": "https://api-st.siliconflow.cn/v1"
                    }
                },
                {
                    "step": 3,
                    "title": "填写配置信息",
                    "fields": {
                        "名称": "硅基流动",
                        "API Key": "从步骤1获取的密钥",
                        "API地址": "从步骤2选择的端点",
                        "类型": "custom"
                    }
                },
                {
                    "step": 4,
                    "title": "测试连接",
                    "description": "点击测试连通性按钮验证配置"
                }
            ],
            "recommended_models": SiliconFlowProvider.SUPPORTED_MODELS[:5],
            "troubleshooting": {
                "连接失败": [
                    "检查API密钥是否正确",
                    "确认API地址格式正确",
                    "尝试切换到另一个端点",
                    "检查网络连接"
                ],
                "模型列表为空": [
                    "确认API密钥有效",
                    "检查账户余额",
                    "联系硅基流动客服"
                ]
            }
        }
    
    @classmethod
    def validate_config(cls, api_key: str, base_url: str) -> dict:
        """验证配置"""
        try:
            result = SiliconFlowProvider.test_connection(api_key, base_url)
            return {
                "success": True,
                "message": "硅基流动配置验证成功",
                "recommended_next_steps": [
                    "添加推荐的模型到列表",
                    "开始使用AI功能"
                ]
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"配置验证失败: {str(e)}",
                "suggestions": cls._get_error_suggestions(str(e))
            }
    
    @classmethod 
    def _get_error_suggestions(cls, error_msg: str) -> list:
        """根据错误信息提供建议"""
        suggestions = []
        
        if "API Key" in error_msg:
            suggestions.extend([
                "检查API密钥是否从 https://cloud.siliconflow.cn/account/ak 正确复制",
                "确认API密钥没有过期",
                "检查账户状态是否正常"
            ])
        
        if "404" in error_msg or "地址" in error_msg:
            suggestions.extend([
                "确认使用正确的API地址: https://api.siliconflow.cn/v1",
                "海外用户尝试: https://api-st.siliconflow.cn/v1",
                "检查URL末尾是否包含 /v1"
            ])
        
        if "timeout" in error_msg or "连接" in error_msg:
            suggestions.extend([
                "检查网络连接",
                "尝试切换网络环境",
                "联系网络管理员检查防火墙设置"
            ])
        
        if not suggestions:
            suggestions.append("请参考官方文档或联系技术支持")
            
        return suggestions
    
    @classmethod
    def get_example_usage(cls) -> dict:
        """获取使用示例"""
        return {
            "python_code": '''
# 硅基流动使用示例
from openai import OpenAI

client = OpenAI(
    api_key="你的API密钥",
    base_url="https://api.siliconflow.cn/v1"
)

response = client.chat.completions.create(
    model="Qwen/Qwen2.5-7B-Instruct",
    messages=[
        {"role": "user", "content": "你好，介绍一下自己"}
    ]
)

print(response.choices[0].message.content)
            ''',
            "curl_example": '''
curl -X POST "https://api.siliconflow.cn/v1/chat/completions" \\
  -H "Authorization: Bearer 你的API密钥" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "messages": [
      {"role": "user", "content": "你好"}
    ]
  }'
            '''
        }

if __name__ == "__main__":
    # 打印配置指南
    guide = SiliconFlowSetupHelper.get_quick_setup_guide()
    print("=" * 50)
    print(guide["title"])
    print("=" * 50)
    
    for step in guide["steps"]:
        print(f"\n步骤 {step['step']}: {step['title']}")
        print(f"描述: {step['description']}")
        if "options" in step:
            for option, value in step["options"].items():
                print(f"  {option}: {value}")
        if "fields" in step:
            for field, value in step["fields"].items():
                print(f"  {field}: {value}")
    
    print(f"\n推荐模型:")
    for i, model in enumerate(guide["recommended_models"], 1):
        print(f"  {i}. {model}")