#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
方案1百炼版：使用完整答案内容+百炼API分析引用关系
"""

import pandas as pd
import json
import requests
import aiohttp
import asyncio
import os
import re
from typing import Dict, List, Any
import time
from ..utils.api_client import create_api_client


class Method1BailianAnalyzer:
    def __init__(self, concurrent_limit: int = 50, api_key: str = None, provider: str = "alibaba",
                 base_url: str = None, model: str = None):
        """
        初始化引文分析器，支持多个API提供商
        
        Args:
            concurrent_limit: 并发限制
            api_key: API密钥
            provider: API提供商 ('alibaba', 'openai', 'deepseek', 'nuwaapi')
            base_url: API基础URL（可选，默认使用提供商的默认URL）
            model: 模型名称（可选，默认使用提供商的推荐模型）
        """
        self.provider = provider.lower()
        self.concurrent_limit = concurrent_limit
        
        # 配置API提供商
        self._configure_provider(api_key, base_url, model)
        
        print(f"正在使用提供商: {self.provider}")
        print(f"正在使用模型: {self.model}")
        print(f"并发限制: {self.concurrent_limit}条")

        if not self.api_key:
            print(f"警告：未找到API密钥，无法调用{self.provider} API")
    
    def _configure_provider(self, api_key: str, base_url: str, model: str):
        """配置不同的API提供商"""
        # 修正NUWA_KEY环境变量名
        if self.provider == "nuwaapi":
            api_key = api_key or os.getenv('NUWA_KEY')
        
        # 使用通用API客户端
        self.api_client = create_api_client(self.provider, api_key, base_url, model)
        
        # 保持兼容性
        self.api_key = self.api_client.api_key
        self.api_ep = self.api_client.base_url
        self.model = self.api_client.model

    def count_chars(self, text: str) -> int:
        """简单的字符计数估算token"""
        # 中文大约1.5字符=1token，英文约4字符=1token
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        other_chars = len(text) - chinese_chars
        estimated_tokens = int(chinese_chars / 1.5 + other_chars / 4)
        return estimated_tokens

    def load_data(self, excel_path: str) -> pd.DataFrame:
        """加载Excel数据"""
        try:
            df = pd.read_excel(excel_path)
            print(f"成功加载Excel数据：{len(df)}行")
            return df
        except Exception as e:
            print(f"加载Excel文件失败：{e}")
            return None

    def extract_citations(self, text: str) -> List[int]:
        """从文本中提取引用标记"""
        citations = []
        pattern = r'\[citation:(\d+)\]'
        matches = re.findall(pattern, text)
        for match in matches:
            citations.append(int(match))
        return sorted(list(set(citations)))

    def extract_clean_answer(self, raw_answer: str) -> str:
        """
        提取纯净的答案内容，移除思考过程
        
        Args:
            raw_answer: 原始答案（可能包含思考过程）
            
        Returns:
            清洁的答案内容
        """
        import re
        
        # 常见的思考过程标记模式
        thinking_patterns = [
            r'<思考>.*?</思考>',
            r'<thinking>.*?</thinking>', 
            r'【思考过程】.*?【回答】',
            r'思考过程：.*?\n\n',
            r'让我思考一下.*?\n\n',
            r'分析：.*?\n\n回答：',
        ]
        
        clean_answer = raw_answer
        
        # 移除思考过程标记
        for pattern in thinking_patterns:
            clean_answer = re.sub(pattern, '', clean_answer, flags=re.DOTALL)
        
        # 移除多余的空白字符
        clean_answer = re.sub(r'\n{3,}', '\n\n', clean_answer)
        clean_answer = clean_answer.strip()
        
        # 如果经过清理后内容太短，可能过度清理了，返回原文
        if len(clean_answer) < len(raw_answer) * 0.3:
            return raw_answer.strip()
            
        return clean_answer

    def prepare_analysis_prompt(self, question: str, answer: str, citations_dict: Dict[int, str]) -> str:
        """准备内部一致性分析prompt（不依赖引文）"""
        # 清理答案，移除思考过程
        clean_answer = self.extract_clean_answer(answer)

        prompt_start = f"""你是一个专业的逻辑一致性检测专家。

【核心任务】
检测AI回答是否存在内部逻辑矛盾、事实冲突或基础错误。
**重要：完全不考虑外部引文或参考资料，只检查答案自身的内部一致性。**

【检测类型】
1. 无问题：答案逻辑清晰，前后一致，无明显错误
2. 前后矛盾：答案内部提到的同一事实或观点前后不一致
3. 逻辑错误：推理链条有漏洞，结论与前提不符，逻辑跳跃
4. 基础错误：简单的数学计算错误、常识性错误、明显的事实性错误
5. 自相矛盾：答案内部观点或立场相互冲突

【重点关注】
- 数字比较错误（如"11.9大于13"）
- 时间逻辑错误（如"2020年比2023年晚"）
- 因果关系混乱
- 同一概念的不同定义或描述
- 计算过程与结果不符
- 违反基本常识的表述

【问题】
{question}

【AI回答（已清理思考过程）】
{clean_answer}

请严格按照以下格式检测这个回答的内部一致性："""

        citations_text = ""

        analysis_requirements = '''【输出格式要求】
状态：[无问题/前后矛盾/逻辑错误/基础错误/自相矛盾]
问题描述：[具体指出存在的问题，如果无问题则说明检查要点]
具体位置：[指出问题出现的具体位置或句子]

**检测示例**：

状态：基础错误
问题描述：数字比较错误，"11.9大于13"违反基本数学常识
具体位置：第二段中"经过计算发现11.9大于13"

状态：前后矛盾  
问题描述：同一概念的描述前后不一致，先说"A是B的主要原因"，后说"A对B没有影响"
具体位置：第一段vs第三段

状态：无问题
问题描述：答案逻辑清晰，数据准确，前后一致，无明显错误
具体位置：全文检查未发现问题

**重要提醒**：
- 只检查答案内部的逻辑一致性
- 不考虑任何外部引文或参考资料
- 重点关注低级错误（数学、常识、逻辑）
- 严格按照格式输出'''

        return prompt_start + citations_text + analysis_requirements

    async def _call_alibaba_api(self, session: aiohttp.ClientSession, prompt: str, max_retries: int = 3) -> Dict[str, Any]:
        """异步调用阿里云百炼API"""
        if not self.api_key:
            return {
                'success': False,
                'error': '缺少API密钥',
                'content': None
            }

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

        data = {
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
                'temperature': 0.2,
                'max_tokens': 15000
            }
        }

        # 重试循环
        last_error = None
        for attempt in range(max_retries):
            try:
                timeout = aiohttp.ClientTimeout(total=180)
                async with session.post(self.api_ep, headers=headers, json=data, timeout=timeout) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get('output') and result['output'].get('text'):
                            return {
                                'success': True,
                                'error': None,
                                'content': result['output']['text']
                            }
                        else:
                            last_error = f'API返回格式异常: {result}'
                            break

                    elif response.status == 429:
                        last_error = 'API调用频率超限'
                        if attempt < max_retries - 1:
                            await asyncio.sleep(30)
                            continue

                    elif response.status >= 500:
                        response_text = await response.text()
                        last_error = f'服务器错误: {response.status} - {response_text[:200]}'
                        if attempt < max_retries - 1:
                            await asyncio.sleep(10)
                            continue

                    elif response.status in [401, 403]:
                        response_text = await response.text()
                        return {
                            'success': False,
                            'error': f'认证错误: {response.status} - {response_text[:200]}',
                            'content': None
                        }

                    else:
                        response_text = await response.text()
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

    async def _call_openai_api(self, session: aiohttp.ClientSession, prompt: str, max_retries: int = 3) -> Dict[str, Any]:
        """异步调用OpenAI兼容的API（包括OpenAI、DeepSeek、NuwaAPI）"""
        if not self.api_key:
            return {
                'success': False,
                'error': '缺少API密钥',
                'content': None
            }

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

        data = {
            'model': self.model,
            'messages': [
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'temperature': 0.2,
            'max_tokens': 15000
        }

        # 重试循环
        last_error = None
        for attempt in range(max_retries):
            try:
                timeout = aiohttp.ClientTimeout(total=180)
                async with session.post(self.api_ep, headers=headers, json=data, timeout=timeout) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get('choices') and len(result['choices']) > 0:
                            return {
                                'success': True,
                                'error': None,
                                'content': result['choices'][0]['message']['content']
                            }
                        else:
                            last_error = f'API返回格式异常: {result}'
                            break

                    elif response.status == 429:
                        last_error = 'API调用频率超限'
                        if attempt < max_retries - 1:
                            await asyncio.sleep(30)
                            continue

                    elif response.status >= 500:
                        response_text = await response.text()
                        last_error = f'服务器错误: {response.status} - {response_text[:200]}'
                        if attempt < max_retries - 1:
                            await asyncio.sleep(10)
                            continue

                    elif response.status in [401, 403]:
                        response_text = await response.text()
                        return {
                            'success': False,
                            'error': f'认证错误: {response.status} - {response_text[:200]}',
                            'content': None
                        }

                    else:
                        response_text = await response.text()
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

    async def call_api_async(self, session: aiohttp.ClientSession, prompt: str, max_retries: int = 3) -> Dict[str, Any]:
        """异步调用API（支持多提供商）"""
        return await self.api_client.call_async(session, prompt, max_retries=max_retries)

    def _call_alibaba_api_sync(self, prompt: str, max_retries: int = 3) -> Dict[str, Any]:
        """同步调用阿里云百炼API"""
        if not self.api_key:
            return {
                'success': False,
                'error': '缺少API密钥',
                'content': None
            }

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

        data = {
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
                'temperature': 0.2,
                'max_tokens': 15000
            }
        }

        prompt_tokens = self.count_chars(prompt)
        print(f"    调用阿里云API... (估算请求Token: {prompt_tokens})")

        # 重试循环
        last_error = None
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    print(f"    第{attempt + 1}次重试...")

                response = requests.post(self.api_ep, headers=headers, json=data, timeout=180)

                if response.status_code == 200:
                    result = response.json()
                    print(f"    API调用成功 (第{attempt + 1}次尝试)")

                    if result.get('output') and result['output'].get('text'):
                        content = result['output']['text']
                        response_tokens = self.count_chars(content)
                        print(f"    估算响应Token: {response_tokens}")
                        return {
                            'success': True,
                            'error': None,
                            'content': content
                        }
                    else:
                        print(f"    API返回格式异常: {result}")
                        last_error = f'API返回格式异常: {result}'
                        break

                elif response.status_code == 429:
                    print(f"    API调用频率超限 (第{attempt + 1}次尝试)，等待30秒后重试")
                    last_error = 'API调用频率超限'
                    if attempt < max_retries - 1:
                        time.sleep(30)
                        continue

                elif response.status_code >= 500:
                    print(f"    服务器错误 {response.status_code} (第{attempt + 1}次尝试)，等待10秒后重试")
                    last_error = f'服务器错误: {response.status_code} - {response.text[:200]}'
                    if attempt < max_retries - 1:
                        time.sleep(10)
                        continue

                elif response.status_code in [401, 403]:
                    print(f"    认证错误 {response.status_code}，请检查API密钥")
                    return {
                        'success': False,
                        'error': f'认证错误: {response.status_code} - {response.text[:200]}',
                        'content': None
                    }

                else:
                    print(f"    客户端错误 {response.status_code}")
                    last_error = f'客户端错误: {response.status_code} - {response.text[:200]}'
                    break

            except requests.exceptions.Timeout:
                print(f"    网络超时 (第{attempt + 1}次尝试，180秒)")
                last_error = '网络超时(180秒)'
                if attempt < max_retries - 1:
                    print(f"    等待15秒后进行第{attempt + 2}次尝试")
                    time.sleep(15)
                    continue

            except requests.exceptions.ConnectionError:
                print(f"    网络连接失败 (第{attempt + 1}次尝试)")
                last_error = '网络连接失败'
                if attempt < max_retries - 1:
                    print(f"    等待10秒后进行第{attempt + 2}次尝试")
                    time.sleep(10)
                    continue

            except Exception as e:
                print(f"    未知错误 (第{attempt + 1}次尝试): {str(e)}")
                last_error = f'未知错误: {str(e)}'
                if attempt < max_retries - 1:
                    print(f"    等待5秒后进行第{attempt + 2}次尝试")
                    time.sleep(5)
                    continue

        print(f"    API调用最终失败，已重试{max_retries}次")
        return {
            'success': False,
            'error': last_error or 'API调用失败',
            'content': None
        }

    def _call_openai_api_sync(self, prompt: str, max_retries: int = 3) -> Dict[str, Any]:
        """同步调用OpenAI兼容的API（包括OpenAI、DeepSeek、NuwaAPI）"""
        if not self.api_key:
            return {
                'success': False,
                'error': '缺少API密钥',
                'content': None
            }

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

        data = {
            'model': self.model,
            'messages': [
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'temperature': 0.2,
            'max_tokens': 15000
        }

        prompt_tokens = self.count_chars(prompt)
        print(f"    调用{self.provider}API... (估算请求Token: {prompt_tokens})")

        # 重试循环
        last_error = None
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    print(f"    第{attempt + 1}次重试...")

                response = requests.post(self.api_ep, headers=headers, json=data, timeout=180)

                if response.status_code == 200:
                    result = response.json()
                    print(f"    API调用成功 (第{attempt + 1}次尝试)")

                    if result.get('choices') and len(result['choices']) > 0:
                        content = result['choices'][0]['message']['content']
                        response_tokens = self.count_chars(content)
                        print(f"    估算响应Token: {response_tokens}")
                        return {
                            'success': True,
                            'error': None,
                            'content': content
                        }
                    else:
                        print(f"    API返回格式异常: {result}")
                        last_error = f'API返回格式异常: {result}'
                        break

                elif response.status_code == 429:
                    print(f"    API调用频率超限 (第{attempt + 1}次尝试)，等待30秒后重试")
                    last_error = 'API调用频率超限'
                    if attempt < max_retries - 1:
                        time.sleep(30)
                        continue

                elif response.status_code >= 500:
                    print(f"    服务器错误 {response.status_code} (第{attempt + 1}次尝试)，等待10秒后重试")
                    last_error = f'服务器错误: {response.status_code} - {response.text[:200]}'
                    if attempt < max_retries - 1:
                        time.sleep(10)
                        continue

                elif response.status_code in [401, 403]:
                    print(f"    认证错误 {response.status_code}，请检查API密钥")
                    return {
                        'success': False,
                        'error': f'认证错误: {response.status_code} - {response.text[:200]}',
                        'content': None
                    }

                else:
                    print(f"    客户端错误 {response.status_code}")
                    last_error = f'客户端错误: {response.status_code} - {response.text[:200]}'
                    break

            except requests.exceptions.Timeout:
                print(f"    网络超时 (第{attempt + 1}次尝试，180秒)")
                last_error = '网络超时(180秒)'
                if attempt < max_retries - 1:
                    print(f"    等待15秒后进行第{attempt + 2}次尝试")
                    time.sleep(15)
                    continue

            except requests.exceptions.ConnectionError:
                print(f"    网络连接失败 (第{attempt + 1}次尝试)")
                last_error = '网络连接失败'
                if attempt < max_retries - 1:
                    print(f"    等待10秒后进行第{attempt + 2}次尝试")
                    time.sleep(10)
                    continue

            except Exception as e:
                print(f"    未知错误 (第{attempt + 1}次尝试): {str(e)}")
                last_error = f'未知错误: {str(e)}'
                if attempt < max_retries - 1:
                    print(f"    等待5秒后进行第{attempt + 2}次尝试")
                    time.sleep(5)
                    continue

        print(f"    API调用最终失败，已重试{max_retries}次")
        return {
            'success': False,
            'error': last_error or 'API调用失败',
            'content': None
        }

    def call_api(self, prompt: str, max_retries: int = 3) -> Dict[str, Any]:
        """同步调用API（支持多提供商）"""
        return self.api_client.call_sync(prompt, max_retries=max_retries)

    def analyze_citation_quality(self, row: pd.Series) -> Dict[str, Any]:
        """分析单行数据的内部一致性（修改后不依赖引文）"""
        question = str(row['模型prompt'])
        answer = str(row['答案'])

        # 清理答案，移除思考过程
        clean_answer = self.extract_clean_answer(answer)

        print(f"    问题长度: {len(question)}字符")
        print(f"    原始答案长度: {len(answer)}字符")
        print(f"    清理后答案长度: {len(clean_answer)}字符")

        # 检查必要数据（不再要求引文）
        if not question.strip() or not clean_answer.strip():
            print("    跳过分析：缺少必要的问题或答案数据")
            return {
                'question': question,
                'answer_preview': clean_answer,
                'original_answer_length': len(answer),
                'clean_answer_length': len(clean_answer),
                'api_success': False,
                'api_error': '缺少必要的问题或答案数据',
                'analysis': None,
                'skipped': True
            }

        # 生成内部一致性检测prompt（不传递引文字典）
        analysis_prompt = self.prepare_analysis_prompt(question, answer, {})

        # 调用API分析
        api_result = self.call_api(analysis_prompt)

        # 解析响应结果
        status = "无问题"
        description = "答案逻辑一致，无明显问题"
        location = ""
        
        if api_result['success']:
            try:
                content = api_result['content'].strip()
                # 解析内部一致性检测结果
                status, description, location = self._parse_consistency_result(content)
            except Exception as e:
                print(f"    响应解析失败: {e}")
                description = f"解析异常: {str(e)}"

        result = {
            'question': question,
            'answer_preview': clean_answer,
            'original_answer_length': len(answer),
            'clean_answer_length': len(clean_answer),
            'api_success': api_result['success'],
            'api_error': api_result['error'],
            'status': status,
            'description': description,
            'location': location,
            'raw_response': api_result['content'] if api_result['success'] else None,
            'skipped': False
        }

        return result
    
    def _parse_consistency_result(self, response_text: str) -> tuple[str, str, str]:
        """
        解析内部一致性检测结果
        
        Args:
            response_text: API返回的分析文本
            
        Returns:
            (status, description, location): 状态、问题描述、具体位置的元组
        """
        response_text = response_text.strip()
        
        # 初始化返回值
        status = "无问题"
        description = "答案逻辑一致，无明显问题"
        location = ""
        
        # 提取状态
        if "状态：" in response_text:
            status_match = re.search(r'状态：\s*([^\n]+)', response_text)
            if status_match:
                status = status_match.group(1).strip()
        
        # 根据关键词识别状态
        if "前后矛盾" in response_text:
            status = "前后矛盾"
        elif "逻辑错误" in response_text:
            status = "逻辑错误"
        elif "基础错误" in response_text:
            status = "基础错误"
        elif "自相矛盾" in response_text:
            status = "自相矛盾"
        elif "无问题" in response_text:
            status = "无问题"
        
        # 提取问题描述
        if "问题描述：" in response_text:
            desc_match = re.search(r'问题描述：\s*([^\n]+(?:\n[^\n]*)*?)(?=具体位置：|$)', response_text, re.MULTILINE)
            if desc_match:
                description = desc_match.group(1).strip()
        
        # 提取具体位置
        if "具体位置：" in response_text:
            loc_match = re.search(r'具体位置：\s*([^\n]+(?:\n[^\n]*)*?)(?=$)', response_text, re.MULTILINE)
            if loc_match:
                location = loc_match.group(1).strip()
        
        return status, description, location

    async def analyze_citation_quality_async(self, session: aiohttp.ClientSession, row: pd.Series, rank: int) -> Dict[
        str, Any]:
        """异步分析单行数据的内部一致性（修改后不依赖引文）"""
        question = str(row['模型prompt'])
        answer = str(row['答案'])

        # 清理答案，移除思考过程
        clean_answer = self.extract_clean_answer(answer)

        # 检查必要数据（不再要求引文）
        if not question.strip() or not clean_answer.strip():
            return {
                'rank': rank,
                'question': question,
                'answer_preview': clean_answer,
                'original_answer_length': len(answer),
                'clean_answer_length': len(clean_answer),
                'api_success': False,
                'api_error': '缺少必要的问题或答案数据',
                'status': 'unknown',
                'description': '',
                'location': '',
                'skipped': True
            }

        # 生成内部一致性检测prompt（不传递引文字典）
        analysis_prompt = self.prepare_analysis_prompt(question, answer, {})

        # 调用异步API分析
        api_result = await self.call_api_async(session, analysis_prompt)

        # 解析响应结果
        status = "无问题"
        description = "答案逻辑一致，无明显问题"
        location = ""
        
        if api_result['success']:
            try:
                content = api_result['content'].strip()
                # 解析内部一致性检测结果
                status, description, location = self._parse_consistency_result(content)
            except Exception as e:
                description = f"解析异常: {str(e)}"

        result = {
            'rank': rank,
            'question': question,
            'answer_preview': clean_answer,
            'original_answer_length': len(answer),
            'clean_answer_length': len(clean_answer),
            'api_success': api_result['success'],
            'api_error': api_result['error'],
            'status': status,
            'description': description,
            'location': location,
            'raw_response': api_result['content'] if api_result['success'] else None,
            'skipped': False
        }

        return result

    async def batch_analyze_concurrent(self, excel_path: str, num_samples: int = None, specific_rank: int = None,
                                       start_from: int = None) -> List[Dict[str, Any]]:
        """异步并发批量分析"""
        df = self.load_data(excel_path)
        if df is None:
            return []

        # 确定要处理的数据
        if specific_rank is not None:
            # 处理特定rank的单条数据
            if specific_rank <= 0 or specific_rank > len(df):
                print(f"错误：指定的rank {specific_rank} 超出数据范围 (1-{len(df)})")
                return []
            sample_df = df.iloc[[specific_rank - 1]]  # rank是1-based，转为0-based索引
            total_count = 1
            print(f"开始分析第{specific_rank}条数据...")
        elif start_from is not None:
            # 从指定位置开始处理指定数量的数据
            if start_from <= 0 or start_from > len(df):
                print(f"错误：起始位置 {start_from} 超出数据范围 (1-{len(df)})")
                return []
            start_idx = start_from - 1  # start_from是1-based，转为0-based索引
            if num_samples is None:
                # 从起始位置到结尾
                sample_df = df.iloc[start_idx:]
                total_count = len(df) - start_idx
                print(f"开始分析从第{start_from}条开始的所有数据（共{total_count}条）...")
            else:
                # 从起始位置开始指定数量
                end_idx = min(start_idx + num_samples, len(df))
                sample_df = df.iloc[start_idx:end_idx]
                total_count = len(sample_df)
                print(f"开始分析从第{start_from}条开始的{total_count}条数据...")
        elif num_samples is None:
            # 处理所有数据
            sample_df = df
            total_count = len(df)
            print(f"开始并发分析所有{total_count}条完整问答数据...")
        else:
            # 处理前num_samples条数据
            sample_df = df.head(num_samples)
            total_count = num_samples
            print(f"开始并发分析前{num_samples}条完整问答数据...")

        print(f"使用百炼API，并发限制: {self.concurrent_limit}条")

        # 创建信号量来控制并发数量
        semaphore = asyncio.Semaphore(self.concurrent_limit)

        async def process_with_semaphore(session, row, rank):
            async with semaphore:
                result = await self.analyze_citation_quality_async(session, row, rank + 1)
                return result

        # 创建HTTP会话
        connector = aiohttp.TCPConnector(limit=100)  # 连接池大小
        async with aiohttp.ClientSession(connector=connector) as session:
            # 创建任务列表
            tasks = []
            for idx, row in sample_df.iterrows():
                task = process_with_semaphore(session, row, idx)
                tasks.append(task)

            # 执行所有任务并显示进度
            print(f"开始处理{len(tasks)}个任务...")
            start_time = time.time()

            completed_tasks = []
            for task in asyncio.as_completed(tasks):
                result = await task
                completed_tasks.append(result)

                # 显示进度
                progress = len(completed_tasks)
                elapsed = time.time() - start_time
                avg_time = elapsed / progress if progress > 0 else 0
                eta = avg_time * (total_count - progress)

                status = "✓" if result['api_success'] else "✗"
                print(f"[{progress}/{total_count}] {status} 第{result['rank']}条 "
                      f"(用时: {elapsed:.1f}s, ETA: {eta:.1f}s)")

        # 按rank排序结果
        completed_tasks.sort(key=lambda x: x['rank'])

        # 统计结果
        success_count = sum(1 for r in completed_tasks if r['api_success'])
        failed_count = len(completed_tasks) - success_count

        total_time = time.time() - start_time
        print(f"\n=== 并发分析完成 ===")
        print(f"总用时: {total_time:.1f}秒")
        print(f"平均每条: {total_time / len(completed_tasks):.2f}秒")
        print(f"成功: {success_count}条, 失败: {failed_count}条")

        return completed_tasks

    def batch_analyze(self, excel_path: str, num_samples: int = 10, specific_rank: int = None, start_from: int = None) -> \
    List[Dict[str, Any]]:
        """批量分析数据，num_samples=None时处理所有数据"""
        df = self.load_data(excel_path)
        if df is None:
            return []

        # 确定要处理的数据
        if specific_rank is not None:
            # 处理特定rank的单条数据
            if specific_rank <= 0 or specific_rank > len(df):
                print(f"错误：指定的rank {specific_rank} 超出数据范围 (1-{len(df)})")
                return []
            sample_df = df.iloc[[specific_rank - 1]]  # rank是1-based，转为0-based索引
            total_count = 1
            print(f"开始分析第{specific_rank}条数据...")
        elif start_from is not None:
            # 从指定位置开始处理指定数量的数据
            if start_from <= 0 or start_from > len(df):
                print(f"错误：起始位置 {start_from} 超出数据范围 (1-{len(df)})")
                return []
            start_idx = start_from - 1  # start_from是1-based，转为0-based索引
            if num_samples is None:
                # 从起始位置到结尾
                sample_df = df.iloc[start_idx:]
                total_count = len(df) - start_idx
                print(f"开始分析从第{start_from}条开始的所有数据（共{total_count}条）...")
            else:
                # 从起始位置开始指定数量
                end_idx = min(start_idx + num_samples, len(df))
                sample_df = df.iloc[start_idx:end_idx]
                total_count = len(sample_df)
                print(f"开始分析从第{start_from}条开始的{total_count}条数据...")
        elif num_samples is None:
            # 处理所有数据
            sample_df = df
            total_count = len(df)
            print(f"开始分析所有{total_count}条完整问答数据...")
        else:
            # 处理前num_samples条数据
            sample_df = df.head(num_samples)
            total_count = num_samples
            print(f"开始分析前{num_samples}条完整问答数据...")

        results = []
        success_count = 0
        failed_count = 0

        print("使用百炼API，支持重试机制和超时延长")

        for idx, row in sample_df.iterrows():
            # 使用原始索引+1作为rank
            actual_rank = idx + 1
            print(f"\n=== 正在分析第{actual_rank}条数据 (DataFrame索引: {idx}) ===")

            result = self.analyze_citation_quality(row)

            if result['api_success']:
                print("    ✓ 分析成功")
                success_count += 1
            else:
                print(f"    ✗ 分析失败: {result['api_error']}")
                failed_count += 1

            results.append({
                'rank': actual_rank,
                **result
            })

            # 简化调用间隔，重试机制已经处理了大部分错误情况
            if result['api_success']:
                time.sleep(3)  # 成功后等3秒（原5秒）
            else:
                time.sleep(1)  # 失败后等1秒（原2秒），因为重试机制已经等待过了

        print(f"\n=== 方案1百炼版分析完成 ===")
        print(f"成功: {success_count}条, 失败: {failed_count}条")

        return results

    def save_results(self, results: List[Dict[str, Any]], output_path: str):
        """保存分析结果，增强错误处理"""
        try:
            # 创建目录（如果不存在）
            import os
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
                print(f"创建输出目录：{output_dir}")

            # 导入排序功能并对结果排序
            from .json_rank_sorter import sort_by_rank
            sorted_results = sort_by_rank(results)
            
            # 保存结果
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(sorted_results, f, ensure_ascii=False, indent=2)
            print(f"✓ 结果已成功保存到：{output_path}（已按rank排序）")
            print(f"    文件大小：{os.path.getsize(output_path)} 字节")

        except PermissionError:
            print(f"✗ 保存失败：没有写入权限 - {output_path}")
        except FileNotFoundError:
            print(f"✗ 保存失败：路径不存在 - {output_path}")
        except Exception as e:
            print(f"✗ 保存失败：{e}")


def get_user_choice() -> dict:
    """获取用户选择的运行模式"""
    print("\n=== 引文分析脚本 ===")
    print("请选择运行模式：")
    print("1. 分析特定rank的单条数据（同步模式）")
    print("2. 从指定位置开始分析指定数量的数据（同步模式）")
    print("3. 分析所有数据（并发模式）")
    print("4. 分析前N条数据（并发模式）")
    print("5. 从指定位置开始分析指定数量的数据（并发模式）")
    print("6. 退出")

    while True:
        try:
            choice = input("\n请输入选择 (1-6): ").strip()

            if choice == '1':
                rank = int(input("请输入要分析的rank (从1开始): "))
                return {"mode": "specific_rank", "specific_rank": rank}

            elif choice == '2':
                start_from = int(input("请输入起始位置 (从1开始): "))
                count_input = input("请输入要分析的数量 (留空表示分析到结尾): ").strip()
                num_samples = int(count_input) if count_input else None
                return {"mode": "start_from", "start_from": start_from, "num_samples": num_samples}

            elif choice == '3':
                return {"mode": "all", "num_samples": None}

            elif choice == '4':
                num_samples = int(input("请输入要分析的数据量: "))
                return {"mode": "head", "num_samples": num_samples}

            elif choice == '5':
                start_from = int(input("请输入起始位置 (从1开始): "))
                count_input = input("请输入要分析的数量 (留空表示分析到结尾): ").strip()
                num_samples = int(count_input) if count_input else None
                return {"mode": "start_from_async", "start_from": start_from, "num_samples": num_samples}

            elif choice == '6':
                print("退出程序")
                return {"mode": "exit"}

            else:
                print("无效选择，请重新输入")

        except ValueError:
            print("输入格式错误，请输入数字")
        except KeyboardInterrupt:
            print("\n用户取消操作")
            return {"mode": "exit"}


def main_unified():
    """统一主函数，根据用户选择决定同步或异步"""
    # 获取用户选择
    user_choice = get_user_choice()
    if user_choice["mode"] == "exit":
        return

    # 根据模式决定使用同步还是异步
    if user_choice["mode"] in ["specific_rank", "start_from"]:
        # 同步模式
        main_sync(user_choice)
    else:
        # 异步模式
        asyncio.run(main_async_impl(user_choice))


def main_sync(user_choice):
    """同步版本主函数"""
    analyzer = Method1BailianAnalyzer()

    # 获取项目根目录路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    
    # 数据路径
    excel_path = os.path.join(project_root, "data", "input", "正文引文内容（纯净版）.xlsx")
    output_dir = os.path.join(project_root, "data", "output", "results")
    os.makedirs(output_dir, exist_ok=True)

    # 根据用户选择设置输出文件名
    if user_choice["mode"] == "specific_rank":
        output_path = os.path.join(output_dir, f"citation_analysis_rank_{user_choice['specific_rank']}_sync_results.json")
    elif user_choice["mode"] == "start_from":
        if user_choice.get("num_samples"):
            output_path = os.path.join(output_dir, f"citation_analysis_from_{user_choice['start_from']}_count_{user_choice['num_samples']}_sync_results.json")
        else:
            output_path = os.path.join(output_dir, f"citation_analysis_from_{user_choice['start_from']}_to_end_sync_results.json")
    else:
        output_path = os.path.join(output_dir, "citation_analysis_sync_results.json")

    print(f"开始同步分析...")
    print(f"输出文件：{output_path}")

    # 根据用户选择调用不同的分析方法
    if user_choice["mode"] == "specific_rank":
        results = analyzer.batch_analyze(excel_path, specific_rank=user_choice["specific_rank"])
    elif user_choice["mode"] == "start_from":
        results = analyzer.batch_analyze(excel_path,
                                         num_samples=user_choice.get("num_samples"),
                                         start_from=user_choice["start_from"])
    else:
        results = analyzer.batch_analyze(excel_path)

    if results:
        analyzer.save_results(results, output_path)
        print(f"\n方案1百炼版分析完成！")

        # 显示成功的结果预览
        success_results = [r for r in results if r['api_success']]
        if success_results:
            print(f"\n成功分析示例：")
            for i, result in enumerate(success_results[:1]):
                print(f"\n{i + 1}. 第{result['rank']}条数据:")
                print(f"   使用引用: {result['citations_used']}")
                print(f"   可用引文: {len(result['citations_available'])}个")
                if result['analysis']:
                    print(f"   分析片段: {result['analysis'][:150]}...")
    else:
        print("分析失败，请检查数据文件和AL_KEY配置")


async def main_async_impl(user_choice):
    """异步并发版本的主函数实现"""
    analyzer = Method1BailianAnalyzer(concurrent_limit=50)  # 50并发

    # 获取项目根目录路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    
    # 数据路径
    excel_path = os.path.join(project_root, "data", "input", "正文引文内容（纯净版）.xlsx")
    output_dir = os.path.join(project_root, "data", "output", "results")
    os.makedirs(output_dir, exist_ok=True)

    # 根据用户选择设置输出文件名
    if user_choice["mode"] == "specific_rank_async":
        output_path = os.path.join(output_dir, f"citation_analysis_rank_{user_choice['specific_rank']}_async_results.json")
    elif user_choice["mode"] == "head":
        output_path = os.path.join(output_dir, f"citation_analysis_head_{user_choice['num_samples']}_results.json")
    elif user_choice["mode"] == "start_from_async":
        if user_choice.get("num_samples"):
            output_path = os.path.join(output_dir, f"citation_analysis_from_{user_choice['start_from']}_count_{user_choice['num_samples']}_async_results.json")
        else:
            output_path = os.path.join(output_dir, f"citation_analysis_from_{user_choice['start_from']}_to_end_async_results.json")
    else:
        output_path = os.path.join(output_dir, "citation_analysis_method1_bailian_concurrent_results.json")

    print(f"🚀 启动高速并发分析模式！")
    print(f"输出文件：{output_path}")

    # 根据用户选择调用不同的分析方法
    if user_choice["mode"] == "specific_rank_async":
        results = await analyzer.batch_analyze_concurrent(excel_path, specific_rank=user_choice["specific_rank"])
    elif user_choice["mode"] == "head":
        results = await analyzer.batch_analyze_concurrent(excel_path, num_samples=user_choice["num_samples"])
    elif user_choice["mode"] == "start_from_async":
        results = await analyzer.batch_analyze_concurrent(excel_path, 
                                                         num_samples=user_choice.get("num_samples"),
                                                         start_from=user_choice["start_from"])
    else:  # "all"
        results = await analyzer.batch_analyze_concurrent(excel_path, num_samples=None)

    if results:
        analyzer.save_results(results, output_path)
        print(f"\n🎉 并发分析完成！")

        # 显示成功的结果预览
        success_results = [r for r in results if r['api_success']]
        if success_results:
            print(f"\n成功分析示例：")
            for i, result in enumerate(success_results[:1]):
                print(f"\n{i + 1}. 第{result['rank']}条数据:")
                print(f"   使用引用: {result['citations_used']}")
                print(f"   可用引文: {len(result['citations_available'])}个")
                if result['analysis']:
                    print(f"   分析片段: {result['analysis'][:150]}...")
    else:
        print("分析失败，请检查数据文件和AL_KEY配置")


# 保留原来的函数名作为别名
async def main_async():
    """异步并发版本的主函数（兼容性保留）"""
    user_choice = {"mode": "all"}
    await main_async_impl(user_choice)


def main():
    """交互式主函数"""
    # 获取用户选择
    user_choice = get_user_choice()
    if user_choice["mode"] == "exit":
        return

    analyzer = Method1BailianAnalyzer()

    # 获取项目根目录路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    
    # 数据路径
    excel_path = os.path.join(project_root, "data", "input", "正文引文内容（纯净版）.xlsx")
    output_dir = os.path.join(project_root, "data", "output", "results")
    os.makedirs(output_dir, exist_ok=True)

    # 根据用户选择设置输出文件名
    if user_choice["mode"] == "specific_rank":
        output_path = os.path.join(output_dir, f"citation_analysis_rank_{user_choice['specific_rank']}_sync_results.json")
    elif user_choice["mode"] == "start_from":
        if user_choice.get("num_samples"):
            output_path = os.path.join(output_dir, f"citation_analysis_from_{user_choice['start_from']}_count_{user_choice['num_samples']}_sync_results.json")
        else:
            output_path = os.path.join(output_dir, f"citation_analysis_from_{user_choice['start_from']}_to_end_sync_results.json")
    elif user_choice["mode"] == "head":
        output_path = os.path.join(output_dir, f"citation_analysis_head_{user_choice['num_samples']}_sync_results.json")
    else:
        output_path = os.path.join(output_dir, "citation_analysis_method1_bailian_sync_results.json")

    print(f"开始同步分析...")
    print(f"输出文件：{output_path}")

    # 根据用户选择调用不同的分析方法
    if user_choice["mode"] == "specific_rank":
        results = analyzer.batch_analyze(excel_path, specific_rank=user_choice["specific_rank"])
    elif user_choice["mode"] == "start_from":
        results = analyzer.batch_analyze(excel_path,
                                         num_samples=user_choice.get("num_samples"),
                                         start_from=user_choice["start_from"])
    else:  # "all" or "head"
        results = analyzer.batch_analyze(excel_path, num_samples=user_choice.get("num_samples"))

    if results:
        analyzer.save_results(results, output_path)
        print(f"\n方案1百炼版分析完成！")

        # 显示成功的结果预览
        success_results = [r for r in results if r['api_success']]
        if success_results:
            print(f"\n成功分析示例：")
            for i, result in enumerate(success_results[:1]):
                print(f"\n{i + 1}. 第{result['rank']}条数据:")
                print(f"   使用引用: {result['citations_used']}")
                print(f"   可用引文: {len(result['citations_available'])}个")
                if result['analysis']:
                    print(f"   分析片段: {result['analysis'][:150]}...")
    else:
        print("分析失败，请检查数据文件和AL_KEY配置")


if __name__ == "__main__":
    # 运行统一主函数，根据用户选择自动决定同步或异步
    main_unified()