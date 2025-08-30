#!/usr/bin/env python3
"""
调试API连接测试失败问题的测试脚本
手动复现连通性测试过程
"""

import requests
import json
import sys
import traceback
from openai import OpenAI

def test_direct_http_request():
    """直接HTTP请求测试"""
    print("=== 直接HTTP请求测试 ===")
    
    # 根据日志，使用的是new-api容器
    base_url = "http://new-api:3000/v1"
    # 从日志中看到的API Key
    api_key = "sk-x****"  # 需要替换为实际的API Key
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # 测试models接口
    try:
        print(f"测试models接口: {base_url}/models")
        response = requests.get(f"{base_url}/models", headers=headers, timeout=15)
        print(f"Models接口状态码: {response.status_code}")
        if response.status_code == 200:
            models_data = response.json()
            print(f"可用模型数量: {len(models_data.get('data', []))}")
            if models_data.get('data'):
                print(f"第一个模型: {models_data['data'][0].get('id', 'N/A')}")
        else:
            print(f"Models接口响应: {response.text}")
    except Exception as e:
        print(f"Models接口请求异常: {e}")
        traceback.print_exc()
    
    print()
    
    # 测试chat/completions接口
    try:
        print(f"测试chat/completions接口: {base_url}/chat/completions")
        payload = {
            "model": "gpt-3.5-turbo",  # 尝试一个通用模型
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 1
        }
        
        response = requests.post(f"{base_url}/chat/completions", 
                               headers=headers, 
                               json=payload, 
                               timeout=15)
        print(f"Chat接口状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Chat响应成功: {json.dumps(result, ensure_ascii=False)[:200]}...")
        else:
            print(f"Chat接口响应: {response.text}")
            
    except Exception as e:
        print(f"Chat接口请求异常: {e}")
        traceback.print_exc()

def test_openai_sdk():
    """OpenAI SDK测试"""
    print("\n=== OpenAI SDK测试 ===")
    
    base_url = "http://new-api:3000/v1"
    api_key = "sk-x****"  # 需要替换为实际的API Key
    
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        print(f"创建OpenAI客户端成功，base_url: {base_url}")
        
        # 测试models.list()
        print("测试models.list()...")
        models = client.models.list()
        print(f"SDK models.list()成功，模型数量: {len(models.data) if models.data else 0}")
        
    except Exception as e:
        print(f"OpenAI SDK测试失败: {e}")
        traceback.print_exc()

def test_network_connectivity():
    """网络连通性测试"""
    print("\n=== 网络连通性测试 ===")
    
    # 测试基本连接
    try:
        response = requests.get("http://new-api:3000/", timeout=10)
        print(f"基本连接状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
    except Exception as e:
        print(f"基本连接失败: {e}")
        
    # 测试健康检查端点（如果存在）
    try:
        response = requests.get("http://new-api:3000/health", timeout=10)
        print(f"健康检查状态码: {response.status_code}")
    except Exception as e:
        print(f"健康检查失败: {e}")

if __name__ == "__main__":
    print("开始调试API连接问题...")
    print(f"Python版本: {sys.version}")
    print(f"Requests版本: {requests.__version__}")
    
    # 提示需要替换API Key
    print("\n注意: 请在脚本中替换实际的API Key")
    
    test_network_connectivity()
    test_direct_http_request()
    test_openai_sdk()