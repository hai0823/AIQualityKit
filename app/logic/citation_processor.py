import pandas as pd
import re
import json
from typing import List, Dict, Any


def extract_citations_from_text(text: str, line_number: int) -> List[Dict[str, Any]]:
    """
    从文本中提取包含引用标注的句子

    Args:
        text: 输入文本
        line_number: 文本在源文件中的行号

    Returns:
        包含提取结果的字典列表，每个字典包含：
        - topic: 完整句子内容（保留原始文本）
        - rank: 句子在源文件中的行号
        - citation: 对应的引用编号（单个数字或数组）
    """
    if pd.isna(text) or not isinstance(text, str):
        return []

    results = []

    # 更精确的句子分割：按中文句号、问号、感叹号以及换行符分割
    # 同时考虑英文句号，但要避免小数点等情况
    sentences = re.split(r'[。！？\n]|(?<=[^\d])\.(?=\s|$)', text)

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        # 查找[citation:X]格式的引用
        citation_pattern = r'\[citation:(\d+)\]'
        citation_matches = re.findall(citation_pattern, sentence)

        # 查找[^X]格式的引用
        caret_pattern = r'\[\^(\d+)\]'
        caret_matches = re.findall(caret_pattern, sentence)

        # 合并所有引用编号
        all_citations = []
        if citation_matches:
            all_citations.extend([int(x) for x in citation_matches])
        if caret_matches:
            all_citations.extend([int(x) for x in caret_matches])

        # 如果找到引用标注
        if all_citations:
            # 去除重复的引用编号并排序
            unique_citations = sorted(list(set(all_citations)))

            # 移除引用标注，获取纯文本内容
            clean_sentence = re.sub(r'\[citation:\d+\]', '', sentence)
            clean_sentence = re.sub(r'\[\^\d+\]', '', clean_sentence)
            clean_sentence = clean_sentence.strip()

            # 确保句子有实际内容（不只是引用标注）且长度合理
            if clean_sentence and len(clean_sentence) > 3 and len(sentence) < 500:
                result = {
                    "topic": sentence,  # 保留原始文本包含引用标注
                    "rank": line_number,
                    "citation": unique_citations if len(unique_citations) > 1 else unique_citations[0]
                }
                results.append(result)

    return results


def process_excel_file(file_path: str) -> List[Dict[str, Any]]:
    """
    处理Excel文件，提取包含引用标注的句子

    Args:
        file_path: Excel文件路径

    Returns:
        提取结果列表
    """
    try:
        # 读取Excel文件
        print(f"正在读取文件: {file_path}")
        df = pd.read_excel(file_path)

        # 检查是否存在'答案'列
        if '答案' not in df.columns:
            print("错误：Excel文件中未找到'答案'列")
            print(f"可用列名: {list(df.columns)}")
            return []

        print(f"文件读取成功，共 {len(df)} 行数据")
        all_results = []

        # 遍历每一行的答案内容
        for index, row in df.iterrows():
            if (index + 1) % 100 == 0:
                print(f"处理进度: {index + 1}/{len(df)}")

            answer_text = row['答案']
            line_number = index + 1  # 行号从1开始

            # 提取该行的引用标注
            results = extract_citations_from_text(answer_text, line_number)
            all_results.extend(results)

        print(f"处理完成，共提取到 {len(all_results)} 个包含引用标注的句子")
        return all_results

    except FileNotFoundError:
        print(f"错误：文件 {file_path} 不存在")
        return []
    except Exception as e:
        print(f"处理文件时出错: {e}")
        return []


def save_results_to_json(results: List[Dict[str, Any]], output_file: str = 'citation_results.json'):
    """
    将结果保存为JSON文件

    Args:
        results: 提取结果列表
        output_file: 输出文件名
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"结果已保存到: {output_file}")
    except Exception as e:
        print(f"保存文件时出错: {e}")


def print_sample_results(results: List[Dict[str, Any]], sample_count: int = 5):
    """
    打印示例结果

    Args:
        results: 提取结果列表
        sample_count: 显示的示例数量
    """
    if not results:
        print("没有找到包含引用标注的句子")
        return

    print(f"\n=== 提取结果示例（前 {min(sample_count, len(results))} 个）===")

    for i, result in enumerate(results[:sample_count]):
        print(f"\n结果 {i + 1}:")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    if len(results) > sample_count:
        print(f"\n... 还有 {len(results) - sample_count} 个结果未显示")


def main():
    """
    主函数
    """
    print("=== AI回答文本引用标注处理程序 ===")
    print("功能：提取包含[citation:X]和[^X]格式标注的句子\n")

    # 配置文件路径
    input_file = '../../data/正文引文内容.xlsx'
    output_file = '../../results/citation_results.json'

    # 处理Excel文件
    results = process_excel_file(input_file)

    if results:
        # 显示统计信息
        print(f"\n=== 处理统计 ===")
        print(f"总提取句子数: {len(results)}")

        # 统计引用编号分布
        citation_counts = {}
        for item in results:
            citations = item['citation']
            if isinstance(citations, list):
                for c in citations:
                    citation_counts[c] = citation_counts.get(c, 0) + 1
            else:
                citation_counts[citations] = citation_counts.get(citations, 0) + 1

        print(f"不同引用编号数量: {len(citation_counts)}")
        print(f"最常用的引用编号: {max(citation_counts.items(), key=lambda x: x[1])}")

        # 显示示例结果
        print_sample_results(results)

        # 保存结果
        save_results_to_json(results, output_file)

        print(f"\n=== 程序执行完成 ===")
        print(f"输入文件: {input_file}")
        print(f"输出文件: {output_file}")
        print(f"提取结果: {len(results)} 个句子")

    else:
        print("\n未找到包含引用标注的句子，请检查输入文件")


if __name__ == "__main__":
    main()