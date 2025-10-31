#!/usr/bin/env python3
"""
诊断所有Provider的健康状态
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from app.services.provider import ProviderService
from app.gpt.provider.OpenAI_compatible_provider import OpenAICompatibleProvider
from app.utils.logger import get_logger

logging = get_logger(__name__)

def diagnose_all_providers():
    """诊断所有provider"""
    print("=" * 80)
    print("🔍 开始诊断所有Provider...")
    print("=" * 80)

    # 获取所有启用的provider
    from app.db.provider_dao import get_enabled_providers
    providers = get_enabled_providers()

    if not providers:
        print("⚠️  没有找到启用的provider")
        return

    print(f"\n找到 {len(providers)} 个启用的provider\n")

    results = []

    for i, provider in enumerate(providers, 1):
        print(f"\n{'='*80}")
        print(f"[{i}/{len(providers)}] Provider: {provider['name']}")
        print(f"{'='*80}")
        print(f"ID: {provider['id']}")
        print(f"Base URL: {provider['base_url']}")
        print(f"API Key: {provider['api_key'][:12]}...{provider['api_key'][-8:]}")

        # 测试连接
        try:
            print("\n🔄 测试连接...")
            is_connected = OpenAICompatibleProvider.test_connection(
                api_key=provider['api_key'],
                base_url=provider['base_url']
            )

            if is_connected:
                print("✅ 连接成功")
                results.append({
                    'name': provider['name'],
                    'status': '✅ 可用',
                    'base_url': provider['base_url']
                })
            else:
                print("❌ 连接失败")
                results.append({
                    'name': provider['name'],
                    'status': '❌ 不可用',
                    'base_url': provider['base_url']
                })
        except Exception as e:
            error_msg = str(e)
            print(f"❌ 连接失败: {error_msg[:100]}")

            # 分析错误类型
            if '402' in error_msg or 'Insufficient' in error_msg or 'balance' in error_msg.lower():
                status = '💰 余额不足'
            elif '401' in error_msg or 'Unauthorized' in error_msg or 'invalid' in error_msg.lower():
                status = '🔑 API Key无效'
            elif '403' in error_msg or 'blocked' in error_msg.lower():
                status = '🚫 被拦截'
            elif 'timeout' in error_msg.lower():
                status = '⏱️  超时'
            else:
                status = '❌ 错误'

            results.append({
                'name': provider['name'],
                'status': status,
                'base_url': provider['base_url'],
                'error': error_msg[:100]
            })

    # Cloudscraper缓存统计已移除

    # 总结
    print(f"\n{'='*80}")
    print("📋 Provider状态总结")
    print(f"{'='*80}")
    print(f"{'Provider名称':<20} {'状态':<15} {'Base URL'}")
    print(f"{'-'*80}")

    available_count = 0
    for result in results:
        print(f"{result['name']:<20} {result['status']:<15} {result['base_url']}")
        if '✅' in result['status']:
            available_count += 1

    print(f"\n{'='*80}")
    print(f"✅ 可用: {available_count}/{len(results)}")
    print(f"❌ 不可用: {len(results)-available_count}/{len(results)}")
    print(f"{'='*80}")

    if available_count == 0:
        print("\n⚠️  警告：没有可用的provider！请检查：")
        print("   1. API Key是否有效")
        print("   2. 账户余额是否充足")
        print("   3. 网络连接是否正常")
        return False
    else:
        print(f"\n✅ 有 {available_count} 个provider可用")
        return True

if __name__ == "__main__":
    try:
        success = diagnose_all_providers()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 诊断失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
