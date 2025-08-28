#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
引文分析器：基于完整正文的引文关联性分析模块
支持xlsx文件输入和Web API调用
"""

import pandas as pd
import json
import aiohttp
import asyncio
import os
import re
import io
from typing import Dict, List, Any

class CitationAnalyzer:
    def __init__(self, concurrent_limit: int = 50):
        self.api_key = os.getenv('AL_KEY')
        self.api_ep = 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation'
        self.model = 'qwen-flash'
        self.concurrent_limit = concurrent_limit
        
        if not self.api_key:
            print("警告：未找到AL_KEY环境变量，无法调用百炼API")

    def extract_citations(self, text: str) -> List[int]:
        """从文本中提取引用标记"""
        citations = []
        pattern = r'\[citation:(\d+)\]'
        matches = re.findall(pattern, text)
        for match in matches:
            citations.append(int(match))
        return sorted(list(set(citations)))

    def prepare_analysis_prompt(self, question: str, answer: str, citations_dict: Dict[int, str]) -> str:
        """准备分析prompt"""
        used_citations = self.extract_citations(answer)
        
        prompt_start = f"""请分析以下问答内容中引用与引文的匹配关系：

【完整答案内容】
{answer}

【答案中使用的引用标记】
{used_citations}

【可用引文内容】
"""
        
        citations_text = ""
        for citation_num in used_citations:
            if citation_num in citations_dict:
                cite_text = citations_dict[citation_num]
                citations_text += f"引文{citation_num}：{cite_text}\n\n"
            else:
                citations_text += f"引文{citation_num}：（未找到对应内容）\n\n"
        
        analysis_requirements = """【分析要求】
你是一个严谨的文本分析专家。
你的任务是分析【完整答案内容】中所有包含引用标记[citation:x]的句子，并判断其与【可用引文内容】的一致性。

请遵循以下规则：
1.  **逐句分析**：对于每一个包含引用标记 `[citation:x]` 的句子进行分析。
2.  **精确判断**：
    - **一致 (Consistent)**：当句子中的核心信息能在引文中找到明确、直接的支持时。
    - **不一致 (Inconsistent)**：当句子中包含任何引文未提及的信息，或与引文内容相悖时。
3.  **输出格式**：你的输出必须是一个JSON格式的列表 `[]`。列表中的每个对象代表对一个句子的分析，格式如下：
    ```json
    {
      "topic": "被分析的句子或观点",
      "citation_numbers": [引用的编号列表],
      "consistency": "一致" 或 "不一致",
      "reason": "详细的判断理由。"
    }
    ```
4.  **重要**：只分析包含 `[citation:x]` 标记的句子。没有引用标记的句子必须被忽略，不能出现在输出的JSON中。
"""
        
        return prompt_start + citations_text + analysis_requirements

    async def call_api_async(self, session: aiohttp.ClientSession, prompt: str, max_retries: int = 3) -> Dict[str, Any]:
        """异步调用百炼API"""
        if not self.api_key:
            return {'success': False, 'error': '缺少AL_KEY环境变量', 'content': None}
        
        headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {self.api_key}'}
        data = {
            'model': self.model,
            'input': {'messages': [{'role': 'user', 'content': prompt}]},
            'parameters': {'temperature': 0.2, 'max_tokens': 15000}
        }
        
        for attempt in range(max_retries):
            try:
                timeout = aiohttp.ClientTimeout(total=180)
                async with session.post(self.api_ep, headers=headers, json=data, timeout=timeout) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get('output') and result['output'].get('text'):
                            return {'success': True, 'error': None, 'content': result['output']['text']}
                        else:
                            return {'success': False, 'error': f'API返回格式异常: {result}', 'content': None}
                    else:
                        await asyncio.sleep(5)
                        continue
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(5)
                    continue
        return {'success': False, 'error': 'API调用失败，已重试最大次数', 'content': None}

    async def analyze(self, question: str, answer: str, citations_dict: Dict[int, str]) -> Dict[str, Any]:
        """分析单条数据的引用质量"""
        citations_used = self.extract_citations(answer)
        if not citations_used:
            return {'analysis': '跳过分析：答案中没有引用标记', 'skipped': True}
        
        analysis_prompt = self.prepare_analysis_prompt(question, answer, citations_dict)
        
        async with aiohttp.ClientSession() as session:
            api_result = await self.call_api_async(session, analysis_prompt)

        analysis_content = None
        if api_result['success']:
            try:
                analysis_content = json.loads(api_result['content'])
            except json.JSONDecodeError:
                analysis_content = api_result['content']

        return {
            'api_success': api_result['success'],
            'api_error': api_result['error'],
            'analysis': analysis_content,
            'skipped': False
        }

    def load_xlsx_data(self, xlsx_path: str) -> pd.DataFrame:
        """加载xlsx数据"""
        try:
            df = pd.read_excel(xlsx_path, engine='openpyxl')
            return df
        except Exception as e:
            raise ValueError(f"加载xlsx文件失败：{e}")
    
    def load_data_from_bytes(self, file_content: bytes, filename: str) -> pd.DataFrame:
        """从字节流加载xlsx数据"""
        try:
            df = pd.read_excel(io.BytesIO(file_content), engine='openpyxl')
            return df
        except Exception as e:
            raise ValueError(f"解析xlsx文件失败：{e}")

    async def analyze_xlsx_file(self, xlsx_path: str = None, file_content: bytes = None, filename: str = None) -> List[Dict[str, Any]]:
        """分析xlsx文件中的所有数据"""
        if xlsx_path:
            df = self.load_xlsx_data(xlsx_path)
        elif file_content and filename:
            df = self.load_data_from_bytes(file_content, filename)
        else:
            raise ValueError("必须提供xlsx_path或者file_content和filename")

        total_count = len(df)
        semaphore = asyncio.Semaphore(self.concurrent_limit)

        async def process_with_semaphore(session, row, rank):
            async with semaphore:
                result = await self.analyze_single_row_async(session, row, rank + 1)
                return result

        connector = aiohttp.TCPConnector(limit=100)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []
            for idx, row in df.iterrows():
                task = process_with_semaphore(session, row, idx)
                tasks.append(task)

            completed_tasks = []
            for task in asyncio.as_completed(tasks):
                result = await task
                completed_tasks.append(result)

        completed_tasks.sort(key=lambda x: x['rank'])
        return completed_tasks

    async def analyze_single_row_async(self, session: aiohttp.ClientSession, row: pd.Series, rank: int) -> Dict[str, Any]:
        """异步分析单行数据的引用质量"""
        question = str(row['模型prompt'])
        answer = str(row['答案'])

        citations_dict = {}
        for i in range(1, 21):
            col_name = f'引文{i}'
            if col_name in row and pd.notna(row[col_name]):
                citations_dict[i] = str(row[col_name])

        citations_used = self.extract_citations(answer)

        if not citations_used:
            return {
                'rank': rank,
                'question': question,
                'answer_preview': answer[:200] + '...' if len(answer) > 200 else answer,
                'citations_used': citations_used,
                'citations_available': list(citations_dict.keys()),
                'api_success': True,
                'api_error': None,
                'analysis': '跳过分析：答案中没有引用标记',
                'skipped': True
            }

        analysis_prompt = self.prepare_analysis_prompt(question, answer, citations_dict)
        api_result = await self.call_api_async(session, analysis_prompt)

        analysis_content = None
        if api_result['success']:
            try:
                analysis_content = json.loads(api_result['content'])
            except json.JSONDecodeError:
                analysis_content = api_result['content']

        return {
            'rank': rank,
            'question': question,
            'answer_preview': answer[:200] + '...' if len(answer) > 200 else answer,
            'citations_used': citations_used,
            'citations_available': list(citations_dict.keys()),
            'api_success': api_result['success'],
            'api_error': api_result['error'],
            'analysis': analysis_content,
            'skipped': False
        }