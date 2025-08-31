#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
幻觉检测器 - 简化版，适配现有项目架构
检测AI生成内容中的幻觉问题，进行五分类分析
"""

import pandas as pd
import json
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional
import logging
from ..utils.api_client import create_api_client

logger = logging.getLogger(__name__)

class HallucinationDetector:
    def __init__(self, provider: str = "deepseek", api_key: str = None, 
                 base_url: str = None, model: str = None, concurrent_limit: int = 10):
        """
        初始化幻觉检测器
        
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
        
        print(f"正在使用提供商: {self.provider}")
        print(f"正在使用模型: {self.model}")
        print(f"并发限制: {self.concurrent_limit}")

    def create_hallucination_prompt(self, question: str, answer: str, combined_citations: str) -> str:
        """创建幻觉检测的提示词，使用与原版相同的格式"""
        system_prompt = (
            "你是一个大模型输出检测专家。"
            "任务：给定一个大模型的回答（答案）和它使用的引用文章（引文），"
            "判断答案是否基于引文，是否存在幻觉，并给出具体的幻觉类型分类。"
            "\n\n幻觉类型分类标准："
            "\n1. 无幻觉：答案与引文内容完全一致或高度一致，无矛盾、无虚构。"
            "\n2. 事实冲突：答案和引文在同一事实问题上信息相互矛盾。"
            "\n3. 无中生有：答案包含引文中完全没有出现的虚构信息。"
            "\n4. 指令误解：答案整体主题或方向偏离，引文与答案不在一个语境下。"
            "\n5. 逻辑错误：答案的推理链条或逻辑关系有漏洞，导致结论错误。"
            "\n\n输出格式："
            "\n请严格按照以下格式输出："
            "\n状态：[无幻觉/事实冲突/无中生有/指令误解/逻辑错误]"
            "\n详细说明：[具体的问题描述]"
        )
        
        user_prompt = (
            f"答案: {answer}\n"
            f"引文: {combined_citations}\n"
            "请按照要求格式给出分析结果。"
        )
        
        return f"{system_prompt}\n\n{user_prompt}"

    def _parse_analysis_result(self, response_text: str, entry_id: int) -> tuple[str, str]:
        """
        解析AI分析结果，提取状态和详细说明（参考原版 analyze_entry.py）
        
        Args:
            response_text: AI返回的分析文本
            entry_id: 数据ID
            
        Returns:
            (status, detail): 状态和详细说明的元组
        """
        # 清理响应文本
        response_text = response_text.strip()
        
        # 尝试从响应中提取状态和详细说明
        if "无幻觉" in response_text:
            status = "无幻觉"
            # 提取详细说明
            if "：" in response_text:
                detail = response_text.split("：", 1)[1].strip()
            else:
                detail = "答案与引文内容一致"
        elif "事实冲突" in response_text:
            status = "事实冲突"
            detail = self._extract_detail(response_text, "事实冲突")
        elif "无中生有" in response_text:
            status = "无中生有"
            detail = self._extract_detail(response_text, "无中生有")
        elif "指令误解" in response_text:
            status = "指令误解"
            detail = self._extract_detail(response_text, "指令误解")
        elif "逻辑错误" in response_text:
            status = "逻辑错误"
            detail = self._extract_detail(response_text, "逻辑错误")
        else:
            # 兜底处理：根据是否包含"有幻觉问题"来判断
            if "有幻觉问题" in response_text:
                # 默认为"无中生有"类型
                status = "无中生有"
                detail = self._extract_detail(response_text, "有幻觉问题")
            else:
                status = "无幻觉"
                detail = "答案与引文内容一致"
        
        return status, detail

    def _extract_detail(self, response_text: str, keyword: str) -> str:
        """提取详细说明（参考原版 analyze_entry.py）"""
        try:
            if keyword in response_text:
                # 找到关键词后的内容
                start_idx = response_text.find(keyword) + len(keyword)
                if "：" in response_text[start_idx:]:
                    detail = response_text[start_idx:].split("：", 1)[1].strip()
                else:
                    detail = response_text[start_idx:].strip()
                
                # 清理多余的标点符号
                if detail.startswith("，"):
                    detail = detail[1:]
                if detail.startswith("："):
                    detail = detail[1:]
                
                return detail if detail else f"检测到{keyword}问题"
            else:
                return f"检测到{keyword}问题"
        except:
            return f"检测到{keyword}问题"

    async def analyze_single_item(self, session: aiohttp.ClientSession, item: Dict[str, Any]) -> Dict[str, Any]:
        """分析单个数据项"""
        try:
            # 提取数据 - 适配现有项目的列名格式
            question = ""
            answer = ""
            
            # 使用与现有citation_analyzer相同的数据提取逻辑
            # 参考 citation_analyzer_sliced.py:1022-1023
            
            # 提取问题和答案
            question = str(item.get('模型prompt', '')) if pd.notna(item.get('模型prompt', '')) else ""
            answer = str(item.get('答案', '')) if pd.notna(item.get('答案', '')) else ""
            
            # 提取引文 - 按原版逻辑合并所有引文列（参考 preprocess_csv_tool.py:75-82）
            citations_list = []
            for key, value in item.items():
                if pd.notna(value) and key.startswith('引文') and str(value).strip():
                    citations_list.append(str(value).strip())
            
            # 合并引文，用 || 分隔（与原版保持一致）
            combined_citations = " || ".join(citations_list) if citations_list else ""
            
            # 调试信息：查看数据提取情况
            rank = item.get('rank', 0)
            print(f"🔍 第{rank}条数据提取结果:")
            print(f"  问题长度: {len(question)}")
            print(f"  答案长度: {len(answer)}")
            print(f"  引文段数: {len(citations_list)}")
            print(f"  合并引文长度: {len(combined_citations)}")
            if not answer:
                print(f"  ❌ 答案为空")
            if not combined_citations:
                citation_cols = [k for k in item.keys() if k.startswith('引文')]
                print(f"  ❌ 无引文数据，发现引文列: {len(citation_cols)}个")
            
            # 按原版逻辑：答案和引文都必须非空（参考 preprocess_csv_tool.py:85）
            if not answer.strip() or not combined_citations.strip():
                return {
                    'rank': item.get('rank', 0),
                    'api_success': False,
                    'error': '缺少必要的答案或引文数据',
                    'hallucination_category': 'unknown',
                    'has_hallucination': None
                }
            
            # 创建提示词（使用合并后的引文）
            prompt = self.create_hallucination_prompt(question, answer, combined_citations)
            
            # 调用API
            result = await self.api_client.call_async(session, prompt, temperature=0.1, max_tokens=4000)
            
            if result['success']:
                try:
                    # 使用原版的文本解析方式，不是JSON解析
                    content = result['content'].strip()
                    
                    # 解析响应，提取状态和详细说明（参考 analyze_entry.py）
                    status, detail = self._parse_analysis_result(content, item.get('rank', 0))
                    
                    return {
                        'rank': item.get('rank', 0),
                        'api_success': True,
                        'id': item.get('rank', 0),
                        'status': status,
                        'detail': detail
                    }
                    
                except Exception as e:
                    return {
                        'rank': item.get('rank', 0),
                        'api_success': False,
                        'error': f'响应解析失败: {e}',
                        'raw_response': content[:500] if 'content' in locals() else '',
                        'status': 'unknown',
                        'detail': f'解析异常: {str(e)}'
                    }
            else:
                return {
                    'rank': item.get('rank', 0),
                    'api_success': False,
                    'error': result['error'],
                    'hallucination_category': 'unknown',
                    'has_hallucination': None
                }
                
        except Exception as e:
            return {
                'rank': item.get('rank', 0),
                'api_success': False,
                'error': f'分析异常: {str(e)}',
                'hallucination_category': 'unknown',
                'has_hallucination': None
            }

    async def batch_analyze_excel(self, file_content: bytes, num_samples: int = None, 
                                 specific_rank: int = None, start_from: int = None) -> List[Dict[str, Any]]:
        """批量分析Excel文件中的幻觉问题"""
        try:
            # 读取Excel文件
            import io
            df = pd.read_excel(io.BytesIO(file_content))
            print(f"📊 Excel文件读取成功，共{len(df)}行数据")
            print(f"📋 检测到的列名: {df.columns.tolist()}")
            
            # 打印前几行数据用于调试
            if len(df) > 0:
                print(f"📝 第一行数据示例: {dict(df.iloc[0])}")
                print(f"📝 非空列统计: {df.count().to_dict()}")
            
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
            
            print(f"🔄 开始并发幻觉检测分析，并发限制: {self.concurrent_limit}")
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
                        'hallucination_category': 'unknown',
                        'has_hallucination': None
                    })
                else:
                    final_results.append(result)
            
            print(f"✅ 幻觉检测分析完成，共{len(final_results)}条结果")
            return final_results
            
        except Exception as e:
            print(f"❌ 批量分析失败: {str(e)}")
            raise

    def save_results(self, results: List[Dict[str, Any]], output_path: str):
        """保存分析结果"""
        try:
            import os
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 幻觉检测结果已保存到: {output_path}")
            
        except Exception as e:
            print(f"❌ 保存结果失败: {str(e)}")

    def generate_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成分析摘要，使用原版的status字段"""
        total_count = len(results)
        success_count = sum(1 for r in results if r.get('api_success', False))
        failed_count = total_count - success_count
        
        # 统计幻觉类别（使用status字段）
        category_stats = {}
        no_hallucination_count = 0
        
        for result in results:
            if result.get('api_success'):
                status = result.get('status', 'unknown')
                category_stats[status] = category_stats.get(status, 0) + 1
                
                if status == '无幻觉':
                    no_hallucination_count += 1
        
        hallucination_count = success_count - no_hallucination_count
        
        return {
            'total_count': total_count,
            'success_count': success_count,
            'failed_count': failed_count,
            'hallucination_count': hallucination_count,
            'no_hallucination_count': no_hallucination_count,
            'hallucination_rate': hallucination_count / success_count if success_count > 0 else 0,
            'category_distribution': category_stats
        }