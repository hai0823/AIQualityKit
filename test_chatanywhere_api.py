#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试ChatAnywhere API调用脚本
"""

import requests
import json
import os
import time

def test_chatanywhere_api():
    """测试ChatAnywhere API"""
    
    # API配置
    api_key = 'sk-DE8xhX8sshtGmJennCNAAfvGCKB15QSLjoFilbJwI7PwCRCc'  # 使用你的ChatAnywhere API密钥
    base_url = "https://api.chatanywhere.tech/v1/chat/completions"
    
    print(f"🔑 API密钥: {api_key[:10]}...{api_key[-10:]}")
    print(f"🌐 API地址: {base_url}")
    
    # 请求头
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    # 测试数据
    test_cases = [
        {
            "name": "简单英文测试",
            "data": {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": "Say hello"}],
                "temperature": 0.7
            }
        },
        {
            "name": "中文测试",
            "data": {
                "model": "gpt-3.5-turbo", 
                "messages": [{"role": "user", "content": "你好，请介绍一下自己"}],
                "temperature": 0.7
            }
        },
        {
            "name": "gpt-4o模型测试",
            "data": {
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": "Test with gpt-4o"}],
                "temperature": 0.2,
                "max_tokens": 100
            }
        },
        {
            "name": "长文本测试",
            "data": {
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": "请分析以下内容的逻辑一致性：干细胞是一类具有自我更新和多向分化潜能的特殊细胞。"}],
                "temperature": 0.2,
                "max_tokens": 1000
            }
        }
    ]
    
    # 测试每个案例
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*50}")
        print(f"测试 {i}: {test_case['name']}")
        print(f"{'='*50}")
        
        data = test_case['data']
        
        # 打印请求数据
        print("📤 请求数据:")
        print(f"  模型: {data['model']}")
        print(f"  消息内容: {data['messages'][0]['content'][:50]}{'...' if len(data['messages'][0]['content']) > 50 else ''}")
        print(f"  完整JSON: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        try:
            # 发送请求
            print("\n🚀 发送请求...")
            start_time = time.time()
            
            response = requests.post(base_url, headers=headers, json=data, timeout=30)
            
            elapsed_time = time.time() - start_time
            print(f"⏱️  响应时间: {elapsed_time:.2f}秒")
            print(f"📊 状态码: {response.status_code}")
            
            # 处理响应
            if response.status_code == 200:
                result = response.json()
                print("✅ 请求成功!")
                
                if result.get('choices') and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content']
                    print(f"📝 响应内容 ({len(content)}字符):")
                    print(f"  {content[:200]}{'...' if len(content) > 200 else ''}")
                else:
                    print("⚠️  响应格式异常:")
                    print(f"  {json.dumps(result, ensure_ascii=False, indent=2)}")
                    
            else:
                print(f"❌ 请求失败 ({response.status_code})")
                try:
                    error_data = response.json()
                    print("错误详情:")
                    print(f"  {json.dumps(error_data, ensure_ascii=False, indent=2)}")
                except:
                    print(f"错误文本: {response.text}")
                    
        except requests.exceptions.Timeout:
            print("❌ 请求超时 (30秒)")
        except requests.exceptions.ConnectionError:
            print("❌ 网络连接失败")
        except Exception as e:
            print(f"❌ 未知错误: {str(e)}")
        
        # 测试间隔
        if i < len(test_cases):
            print("\n⏳ 等待3秒后进行下一个测试...")
            time.sleep(3)
    
    print(f"\n{'='*50}")
    print("🎯 测试完成!")
    print(f"{'='*50}")

if __name__ == "__main__":
    test_chatanywhere_api()