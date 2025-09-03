#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
精确的Token计数工具
支持多种模型的tokenizer，包括通义千问、GPT等
"""

import re
from typing import Optional

try:
    import tiktoken
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False


class TokenCounter:
    """精确的Token计数器"""
    
    def __init__(self, model_name: str = "qwen-plus"):
        """
        初始化Token计数器
        
        Args:
            model_name: 模型名称，用于选择合适的tokenizer
        """
        self.model_name = model_name.lower()
        self.tokenizer = self._get_tokenizer()
        
    def _get_tokenizer(self):
        """获取适合的tokenizer"""
        if not HAS_TIKTOKEN:
            return None
            
        # 为不同模型选择合适的tokenizer
        if "gpt-4" in self.model_name or "gpt-3.5" in self.model_name:
            return tiktoken.encoding_for_model("gpt-4")
        elif "gpt-4o" in self.model_name:
            return tiktoken.encoding_for_model("gpt-4o")
        elif "qwen" in self.model_name or "alibaba" in self.model_name:
            # 通义千问使用类似GPT-4的tokenizer
            return tiktoken.get_encoding("cl100k_base")
        elif "deepseek" in self.model_name:
            # DeepSeek使用类似GPT-4的tokenizer
            return tiktoken.get_encoding("cl100k_base")
        else:
            # 默认使用GPT-4的tokenizer
            return tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        """
        精确计算token数量
        
        Args:
            text: 要计算的文本
            
        Returns:
            token数量
        """
        if not text:
            return 0
            
        if self.tokenizer is not None:
            # 使用tiktoken进行精确计算
            try:
                return len(self.tokenizer.encode(text))
            except Exception as e:
                print(f"Tiktoken计算失败，使用字符估算: {e}")
                return self._estimate_by_chars(text)
        else:
            # 回退到字符估算
            return self._estimate_by_chars(text)
    
    def _estimate_by_chars(self, text: str) -> int:
        """
        基于字符数估算token（备用方法）
        
        Args:
            text: 要计算的文本
            
        Returns:
            估算的token数量
        """
        # 中文大约1.5字符=1token，英文约4字符=1token
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        other_chars = len(text) - chinese_chars
        estimated_tokens = int(chinese_chars / 1.5 + other_chars / 4)
        return estimated_tokens
    
    def estimate_cost(self, input_tokens: int, output_tokens: int, provider: str = "alibaba") -> dict:
        """
        估算API调用成本
        
        Args:
            input_tokens: 输入token数量
            output_tokens: 输出token数量  
            provider: API提供商
            
        Returns:
            成本估算信息
        """
        # 不同提供商的计费标准（单位：元/1K tokens）
        pricing = {
            "alibaba": {
                "qwen-plus": {"input": 0.004, "output": 0.012},
                "qwen-max": {"input": 0.02, "output": 0.06},
                "qwen-turbo": {"input": 0.002, "output": 0.006}
            },
            "openai": {
                "gpt-4o": {"input": 0.005, "output": 0.015},
                "gpt-4": {"input": 0.03, "output": 0.06},
                "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002}
            },
            "deepseek": {
                "deepseek-chat": {"input": 0.001, "output": 0.002},
                "deepseek-coder": {"input": 0.001, "output": 0.002}
            }
        }
        
        # 获取定价
        provider = provider.lower()
        model_pricing = pricing.get(provider, {}).get(self.model_name)
        
        if not model_pricing:
            # 默认使用阿里云qwen-plus的定价
            model_pricing = pricing["alibaba"]["qwen-plus"]
        
        # 计算成本
        input_cost = input_tokens * model_pricing["input"] / 1000
        output_cost = output_tokens * model_pricing["output"] / 1000
        total_cost = input_cost + output_cost
        
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost,
            "currency": "CNY",
            "model": self.model_name,
            "provider": provider
        }
    
    def analyze_batch_cost(self, texts: list, estimated_output_per_text: int = 500, provider: str = "alibaba") -> dict:
        """
        分析批量文本的token和成本
        
        Args:
            texts: 文本列表
            estimated_output_per_text: 每个文本的预计输出token数
            provider: API提供商
            
        Returns:
            批量分析结果
        """
        total_input_tokens = sum(self.count_tokens(text) for text in texts)
        total_output_tokens = len(texts) * estimated_output_per_text
        
        cost_info = self.estimate_cost(total_input_tokens, total_output_tokens, provider)
        
        return {
            **cost_info,
            "text_count": len(texts),
            "avg_input_tokens_per_text": total_input_tokens / len(texts) if texts else 0,
            "avg_output_tokens_per_text": estimated_output_per_text,
            "avg_cost_per_text": cost_info["total_cost"] / len(texts) if texts else 0
        }


def create_token_counter(model_name: str = "qwen-plus") -> TokenCounter:
    """
    创建Token计数器的工厂函数
    
    Args:
        model_name: 模型名称
        
    Returns:
        TokenCounter实例
    """
    return TokenCounter(model_name)


# 便捷函数
def count_tokens(text: str, model_name: str = "qwen-plus") -> int:
    """
    快速计算token数量
    
    Args:
        text: 文本
        model_name: 模型名称
        
    Returns:
        token数量
    """
    counter = TokenCounter(model_name)
    return counter.count_tokens(text)


def estimate_api_cost(input_tokens: int, output_tokens: int, 
                     provider: str = "alibaba", model_name: str = "qwen-plus") -> dict:
    """
    快速估算API成本
    
    Args:
        input_tokens: 输入token数
        output_tokens: 输出token数
        provider: API提供商
        model_name: 模型名称
        
    Returns:
        成本信息
    """
    counter = TokenCounter(model_name)
    return counter.estimate_cost(input_tokens, output_tokens, provider)


if __name__ == "__main__":
    # 测试token计数器
    counter = TokenCounter("qwen-plus")
    
    test_text = "这是一个测试文本，包含中文和English mixed content."
    tokens = counter.count_tokens(test_text)
    
    print(f"测试文本: {test_text}")
    print(f"Token数量: {tokens}")
    
    # 测试成本估算
    cost_info = counter.estimate_cost(1000, 500, "alibaba")
    print(f"成本估算: {cost_info}")