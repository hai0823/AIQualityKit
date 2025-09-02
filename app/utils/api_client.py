#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用API客户端模块
支持多个API提供商：阿里云百炼、OpenAI、DeepSeek、演示专用
"""

import os
import json
import asyncio
import aiohttp
import requests
from typing import Dict, Any, Optional
import time
import re


class APIClient:
    """通用API客户端，支持多个提供商"""
    
    def __init__(self, provider: str, api_key: str = None, base_url: str = None, model: str = None):
        """
        初始化API客户端
        
        Args:
            provider: API提供商 ('alibaba', 'openai', 'deepseek', 'demo')
            api_key: API密钥
            base_url: API基础URL（可选）
            model: 模型名称（可选）
        """
        self.provider = provider.lower()
        self._configure_provider(api_key, base_url, model)
        
    def _configure_provider(self, api_key: str, base_url: str, model: str):
        """配置不同的API提供商"""
        if self.provider == "alibaba":
            self.api_key = api_key if api_key and api_key.strip() else None
            self.base_url = base_url or "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
            self.model = model or "qwen-plus"
            self._request_format = "alibaba"
            
        elif self.provider == "openai":
            self.api_key = api_key if api_key and api_key.strip() else None
            self.base_url = base_url or "https://api.openai.com/v1/chat/completions"
            self.model = model or "gpt-4o"
            self._request_format = "openai"
            
        elif self.provider == "deepseek":
            self.api_key = api_key if api_key and api_key.strip() else None
            self.base_url = base_url or "https://api.deepseek.com/v1/chat/completions"
            self.model = model or "deepseek-chat"
            self._request_format = "openai"  # DeepSeek使用OpenAI兼容格式
            
        elif self.provider == "demo":
            # 演示专用配置，使用OpenAI兼容格式
            self.api_key = api_key if api_key and api_key.strip() else None
            self.base_url = base_url or "https://api.nuwaapi.com/v1/chat/completions"
            self.model = model or "gemini-2.5-pro"
            self._request_format = "openai"  # 演示API使用OpenAI兼容格式
            
        else:
            raise ValueError(f"不支持的API提供商: {self.provider}")
    
    def _build_request_data(self, prompt: str, temperature: float = 0.2, max_tokens: int = 15000) -> dict:
        """构建请求数据"""
        if self._request_format == "alibaba":
            return {
                'model': self.model,
                'input': {
                    'messages': [
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ]
                },
                'parameters': {
                    'temperature': temperature,
                    'max_tokens': max_tokens,
                    'enable_thinking': False
                }
            }
        else:  # OpenAI格式
            return {
                'model': self.model,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'temperature': temperature,
                'max_tokens': max_tokens
            }
    
    def _build_headers(self) -> dict:
        """构建请求头"""
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
    
    def _extract_content(self, response_data: dict) -> str:
        """从响应中提取内容"""
        if self._request_format == "alibaba":
            # 优先尝试新格式 (output.choices)
            if (response_data.get('output') and 
                response_data['output'].get('choices') and 
                len(response_data['output']['choices']) > 0):
                return response_data['output']['choices'][0]['message']['content']
            # 回退到旧格式 (output.text)
            elif response_data.get('output') and response_data['output'].get('text'):
                return response_data['output']['text']
            else:
                raise ValueError(f"阿里云API响应格式异常: {response_data}")
        else:  # OpenAI格式
            if response_data.get('choices') and len(response_data['choices']) > 0:
                return response_data['choices'][0]['message']['content']
            else:
                raise ValueError(f"OpenAI格式API响应异常: {response_data}")
    
    def count_chars(self, text: str) -> int:
        """简单的字符计数估算token"""
        # 中文大约1.5字符=1token，英文约4字符=1token
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        other_chars = len(text) - chinese_chars
        estimated_tokens = int(chinese_chars / 1.5 + other_chars / 4)
        return estimated_tokens
    
    def call_sync(self, prompt: str, temperature: float = 0.2, max_tokens: int = 15000, 
                  max_retries: int = 3) -> Dict[str, Any]:
        """同步调用API"""
        if not self.api_key:
            return {
                'success': False,
                'error': f'缺少{self.provider} API密钥',
                'content': None
            }

        headers = self._build_headers()
        data = self._build_request_data(prompt, temperature, max_tokens)
        
        # 简化日志输出
        print(f"API调用: {self.provider} {self.model} (prompt: {len(prompt)}字符)")

        prompt_tokens = self.count_chars(prompt)

        # 重试循环
        last_error = None
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    print(f"第{attempt + 1}次重试...")
                
                response = requests.post(self.base_url, headers=headers, json=data, timeout=180)

                if response.status_code == 200:
                    result = response.json()
                    
                    try:
                        content = self._extract_content(result)
                        response_tokens = self.count_chars(content)
                        return {
                            'success': True,
                            'error': None,
                            'content': content
                        }
                    except ValueError as e:
                        last_error = str(e)
                        break

                elif response.status_code == 429:
                    last_error = 'API调用频率超限'
                    if attempt < max_retries - 1:
                        time.sleep(30)
                        continue

                elif response.status_code >= 500:
                    error_response = response.text
                    last_error = f'服务器错误: {response.status_code}'
                    if attempt < max_retries - 1:
                        time.sleep(10)
                        continue

                elif response.status_code in [401, 403]:
                    return {
                        'success': False,
                        'error': f'认证错误: {response.status_code}',
                        'content': None
                    }

                else:
                    error_response = response.text
                    print(f"400错误详情: {error_response}")
                    last_error = f'客户端错误: {response.status_code} - {error_response[:200]}'
                    break

            except requests.exceptions.Timeout:
                last_error = '网络超时(180秒)'
                if attempt < max_retries - 1:
                    time.sleep(15)
                    continue

            except requests.exceptions.ConnectionError:
                last_error = '网络连接失败'
                if attempt < max_retries - 1:
                    time.sleep(10)
                    continue

            except Exception as e:
                last_error = f'未知错误: {str(e)}'
                if attempt < max_retries - 1:
                    time.sleep(5)
                    continue

        return {
            'success': False,
            'error': last_error or 'API调用失败',
            'content': None
        }

    async def call_async(self, session: aiohttp.ClientSession, prompt: str, 
                        temperature: float = 0.2, max_tokens: int = 15000, 
                        max_retries: int = 3) -> Dict[str, Any]:
        """异步调用API"""
        if not self.api_key:
            return {
                'success': False,
                'error': f'缺少{self.provider} API密钥',
                'content': None
            }

        headers = self._build_headers()
        data = self._build_request_data(prompt, temperature, max_tokens)
        
        # 详细调试日志
        print(f"异步API调用: {self.provider} {self.model} (prompt: {len(prompt)}字符)")
        print(f"请求URL: {self.base_url}")
        print(f"请求数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
        print(f"请求头: {headers}")

        # 重试循环
        last_error = None
        for attempt in range(max_retries):
            try:
                timeout = aiohttp.ClientTimeout(total=180)
                async with session.post(self.base_url, headers=headers, json=data, timeout=timeout) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        try:
                            content = self._extract_content(result)
                            return {
                                'success': True,
                                'error': None,
                                'content': content
                            }
                        except ValueError as e:
                            last_error = str(e)
                            break

                    elif response.status == 429:
                        last_error = 'API调用频率超限'
                        if attempt < max_retries - 1:
                            await asyncio.sleep(30)
                            continue

                    elif response.status >= 500:
                        last_error = f'服务器错误: {response.status}'
                        if attempt < max_retries - 1:
                            await asyncio.sleep(10)
                            continue

                    elif response.status in [401, 403]:
                        response_text = await response.text()
                        return {
                            'success': False,
                            'error': f'认证错误: {response.status}',
                            'content': None
                        }

                    else:
                        response_text = await response.text()
                        print(f"400错误详情: {response_text}")
                        last_error = f'客户端错误: {response.status} - {response_text[:200]}'
                        break

            except asyncio.TimeoutError:
                last_error = '网络超时(180秒)'
                if attempt < max_retries - 1:
                    await asyncio.sleep(15)
                    continue

            except Exception as e:
                last_error = f'未知错误: {str(e)}'
                if attempt < max_retries - 1:
                    await asyncio.sleep(5)
                    continue

        return {
            'success': False,
            'error': last_error or 'API调用失败',
            'content': None
        }

    def __repr__(self):
        return f"APIClient(provider={self.provider}, model={self.model})"


# 工厂函数
def create_api_client(provider: str, api_key: str = None, base_url: str = None, model: str = None) -> APIClient:
    """创建API客户端的工厂函数"""
    return APIClient(provider, api_key, base_url, model)


# 预设配置
DEFAULT_MODELS = {
    'alibaba': 'qwen-plus',
    'openai': 'gpt-4o',
    'deepseek': 'deepseek-chat',
    'demo': 'gemini-2.5-pro'
}

DEFAULT_ENV_KEYS = {
    'alibaba': 'AL_KEY',
    'openai': 'OPENAI_API_KEY',
    'deepseek': 'DEEPSEEK_API_KEY',
    'demo': 'DEMO_API_KEY'  # 演示专用，但实际不会从环境变量读取
}