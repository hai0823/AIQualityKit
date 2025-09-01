#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内部一致性检测器 - 检测AI回答自身的逻辑一致性
不依赖外部引文，专门检测答案内部的矛盾、错误和逻辑问题
"""

import pandas as pd
import json
import asyncio
import aiohttp
import re
from typing import Dict, Any, List, Optional
import logging
from ..utils.api_client import create_api_client

logger = logging.getLogger(__name__)

class InternalConsistencyDetector:
    def __init__(self, provider: str = "deepseek", api_key: str = None, 
                 base_url: str = None, model: str = None, concurrent_limit: int = 10):
        """
        初始化内部一致性检测器
        
        Args:
            provider: API提供商 ('alibaba', 'openai', 'deepseek')
            api_key: API密钥
            base_url: API基础URL（可选）
            model: 模型名称（可选）
            concurrent_limit: 并发限制
        """
        self.provider = provider.lower()
        self.concurrent_limit = concurrent_limit
        
        # 使用现有的API客户端
        self.api_client = create_api_client(provider, api_key, base_url, model)
        self.api_key = self.api_client.api_key
        self.base_url = self.api_client.base_url
        self.model = self.api_client.model
        
        if not self.api_key:
            raise ValueError(f"API密钥未设置，请提供{provider} API密钥")
        
        print(f"🔍 内部一致性检测器启动")
        print(f"正在使用提供商: {self.provider}")
        print(f"正在使用模型: {self.model}")
        print(f"并发限制: {self.concurrent_limit}")

    def extract_clean_answer(self, raw_answer: str) -> str:
        """
        提取纯净的答案内容，移除思考过程
        
        Args:
            raw_answer: 原始答案（可能包含思考过程）
            
        Returns:
            清洁的答案内容
        """
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

    def create_consistency_prompt(self, question: str, answer: str) -> str:
        """
        创建内部一致性检测的提示词
        专注于答案自身的逻辑一致性，不依赖外部引文
        """
        system_prompt = """你是一个专业的逻辑一致性检测专家。

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

【输出格式】
状态：[无问题/前后矛盾/逻辑错误/基础错误/自相矛盾]
问题描述：[具体指出存在的问题，如果无问题则说明检查要点]
具体位置：[指出问题出现的具体位置或句子]"""

        user_prompt = f"""【问题】
{question}

【AI回答】
{answer}

请严格按照要求格式检测这个回答的内部一致性："""

        return f"{system_prompt}\n\n{user_prompt}"

    def _parse_consistency_result(self, response_text: str, entry_id: int) -> tuple[str, str, str]:
        """
        解析一致性检测结果
        
        Args:
            response_text: API返回的分析文本
            entry_id: 数据ID
            
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
            status_match = re.search(r'状态：\s*([^\\n]+)', response_text)
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
            desc_match = re.search(r'问题描述：\s*([^\\n]+(?:\\n[^\\n]*)*?)(?=具体位置：|$)', response_text, re.MULTILINE)
            if desc_match:
                description = desc_match.group(1).strip()
        
        # 提取具体位置
        if "具体位置：" in response_text:
            loc_match = re.search(r'具体位置：\s*([^\\n]+(?:\\n[^\\n]*)*?)(?=$)', response_text, re.MULTILINE)
            if loc_match:
                location = loc_match.group(1).strip()
        
        return status, description, location

    async def analyze_single_item(self, session: aiohttp.ClientSession, item: Dict[str, Any]) -> Dict[str, Any]:
        """分析单个数据项的内部一致性"""
        try:
            rank = item.get('rank', 0)
            
            # 提取问题和原始答案
            question = str(item.get('模型prompt', '')) if pd.notna(item.get('模型prompt', '')) else ""
            raw_answer = str(item.get('答案', '')) if pd.notna(item.get('答案', '')) else ""
            
            # 清理答案，移除思考过程
            clean_answer = self.extract_clean_answer(raw_answer)
            
            # 调试信息
            print(f"🔍 第{rank}条数据提取结果:")
            print(f"  问题长度: {len(question)}")
            print(f"  原始答案长度: {len(raw_answer)}")
            print(f"  清理后答案长度: {len(clean_answer)}")
            
            # 检查必要数据
            if not question.strip() or not clean_answer.strip():
                return {
                    'rank': rank,
                    'api_success': False,
                    'error': '缺少必要的问题或答案数据',
                    'status': 'unknown',
                    'description': '',
                    'location': ''
                }
            
            # 创建检测提示词
            prompt = self.create_consistency_prompt(question, clean_answer)
            
            # 调用API
            result = await self.api_client.call_async(session, prompt, temperature=0.1, max_tokens=4000)
            
            if result['success']:
                try:
                    content = result['content'].strip()
                    
                    # 解析响应
                    status, description, location = self._parse_consistency_result(content, rank)
                    
                    return {
                        'rank': rank,
                        'api_success': True,
                        'question': question,
                        'clean_answer': clean_answer,
                        'original_answer_length': len(raw_answer),
                        'clean_answer_length': len(clean_answer),
                        'status': status,
                        'description': description,
                        'location': location,
                        'raw_response': content
                    }
                    
                except Exception as e:
                    return {
                        'rank': rank,
                        'api_success': False,
                        'error': f'响应解析失败: {e}',
                        'raw_response': content if 'content' in locals() else '',
                        'status': 'unknown',
                        'description': f'解析异常: {str(e)}',
                        'location': ''
                    }
            else:
                return {
                    'rank': rank,
                    'api_success': False,
                    'error': result['error'],
                    'status': 'unknown',
                    'description': '',
                    'location': ''
                }
                
        except Exception as e:
            return {
                'rank': item.get('rank', 0),
                'api_success': False,
                'error': f'分析异常: {str(e)}',
                'status': 'unknown',
                'description': '',
                'location': ''
            }

    async def batch_analyze_excel(self, file_content: bytes, num_samples: int = None, 
                                 specific_rank: int = None, start_from: int = None) -> List[Dict[str, Any]]:
        """批量分析Excel文件中的内部一致性问题"""
        try:
            # 读取Excel文件
            import io
            df = pd.read_excel(io.BytesIO(file_content))
            print(f"📊 Excel文件读取成功，共{len(df)}行数据")
            print(f"📋 检测到的列名: {df.columns.tolist()}")
            
            # 根据参数筛选数据
            if specific_rank:
                if specific_rank <= len(df):
                    df = df.iloc[[specific_rank - 1]]
                    print(f"🔍 分析第{specific_rank}条数据")
                else:
                    raise ValueError(f"指定的rank {specific_rank} 超出数据范围（共{len(df)}行）")
            elif start_from:
                start_idx = start_from - 1
                if num_samples:
                    end_idx = start_idx + num_samples
                    df = df.iloc[start_idx:end_idx]
                    print(f"🔍 分析从第{start_from}条开始的{num_samples}条数据")
                else:
                    df = df.iloc[start_idx:]
                    print(f"🔍 分析从第{start_from}条到结尾的数据")
            elif num_samples:
                df = df.head(num_samples)
                print(f"🔍 分析前{num_samples}条数据")
            else:
                print(f"🔍 分析所有{len(df)}条数据")
            
            # 为每行数据添加rank信息
            data_items = []
            for idx, row in df.iterrows():
                item = row.to_dict()
                item['rank'] = idx + 1  # rank从1开始
                data_items.append(item)
            
            # 异步并发分析
            semaphore = asyncio.Semaphore(self.concurrent_limit)
            
            async def analyze_with_semaphore(item):
                async with semaphore:
                    async with aiohttp.ClientSession() as session:
                        return await self.analyze_single_item(session, item)
            
            print(f"🔄 开始并发内部一致性检测，并发限制: {self.concurrent_limit}")
            tasks = [analyze_with_semaphore(item) for item in data_items]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理异常结果
            final_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    final_results.append({
                        'rank': data_items[i].get('rank', i + 1),
                        'api_success': False,
                        'error': f'分析异常: {str(result)}',
                        'status': 'unknown',
                        'description': '',
                        'location': ''
                    })
                else:
                    final_results.append(result)
            
            print(f"✅ 内部一致性检测完成，共{len(final_results)}条结果")
            return final_results
            
        except Exception as e:
            print(f"❌ 批量分析失败: {str(e)}")
            raise

    def save_results(self, results: List[Dict[str, Any]], output_path: str):
        """保存分析结果"""
        try:
            import os
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 导入排序功能并对结果排序
            from .json_rank_sorter import sort_by_rank
            sorted_results = sort_by_rank(results)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(sorted_results, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 内部一致性检测结果已保存到: {output_path}（已按rank排序）")
            
        except Exception as e:
            print(f"❌ 保存结果失败: {str(e)}")

    def generate_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成分析摘要"""
        total_count = len(results)
        success_count = sum(1 for r in results if r.get('api_success', False))
        failed_count = total_count - success_count
        
        # 统计问题类别
        status_stats = {}
        no_problem_count = 0
        
        for result in results:
            if result.get('api_success'):
                status = result.get('status', 'unknown')
                status_stats[status] = status_stats.get(status, 0) + 1
                
                if status == '无问题':
                    no_problem_count += 1
        
        problem_count = success_count - no_problem_count
        
        return {
            'total_count': total_count,
            'success_count': success_count,
            'failed_count': failed_count,
            'problem_count': problem_count,
            'no_problem_count': no_problem_count,
            'problem_rate': problem_count / success_count if success_count > 0 else 0,
            'status_distribution': status_stats,
            'analysis_summary': {
                '前后矛盾': status_stats.get('前后矛盾', 0),
                '逻辑错误': status_stats.get('逻辑错误', 0),
                '基础错误': status_stats.get('基础错误', 0),
                '自相矛盾': status_stats.get('自相矛盾', 0),
                '无问题': status_stats.get('无问题', 0)
            }
        }