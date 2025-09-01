import json
import os
from typing import List, Dict, Any


def read_json_file(file_path: str) -> List[Dict[str, Any]]:
    """
    读取JSON文件并返回数据
    
    Args:
        file_path: JSON文件路径
        
    Returns:
        解析后的JSON数据列表
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, list) else [data]
    except Exception as e:
        print(f"读取文件 {file_path} 时出错: {e}")
        return []


def sort_by_rank(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    按rank字段升序排序
    
    Args:
        data: 包含rank字段的字典列表
        
    Returns:
        排序后的数据列表
    """
    try:
        # 按rank字段升序排序，如果没有rank字段则放在最后
        sorted_data = sorted(data, key=lambda x: x.get('rank', float('inf')))
        return sorted_data
    except Exception as e:
        print(f"排序时出错: {e}")
        return data


def save_json_file(data: List[Dict[str, Any]], file_path: str) -> bool:
    """
    保存数据到JSON文件
    
    Args:
        data: 要保存的数据
        file_path: 输出文件路径
        
    Returns:
        保存是否成功
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存文件 {file_path} 时出错: {e}")
        return False


def process_single_file(input_path: str, output_path: str = None) -> bool:
    """
    处理单个JSON文件
    
    Args:
        input_path: 输入文件路径
        output_path: 输出文件路径，如果为None则覆盖原文件
        
    Returns:
        处理是否成功
    """
    if not os.path.exists(input_path):
        print(f"文件不存在: {input_path}")
        return False
    
    # 读取数据
    data = read_json_file(input_path)
    if not data:
        print(f"文件 {input_path} 为空或读取失败")
        return False
    
    # 排序
    sorted_data = sort_by_rank(data)
    
    # 确定输出路径
    if output_path is None:
        output_path = input_path
    
    # 保存
    success = save_json_file(sorted_data, output_path)
    if success:
        print(f"成功处理文件: {input_path} -> {output_path}")
        print(f"排序前后数据量: {len(data)} -> {len(sorted_data)}")
    
    return success


def process_directory(directory_path: str, output_directory: str = None) -> int:
    """
    处理目录下的所有JSON文件
    
    Args:
        directory_path: 输入目录路径
        output_directory: 输出目录路径，如果为None则覆盖原文件
        
    Returns:
        成功处理的文件数量
    """
    if not os.path.exists(directory_path):
        print(f"目录不存在: {directory_path}")
        return 0
    
    success_count = 0
    
    # 遍历目录下的所有JSON文件
    for filename in os.listdir(directory_path):
        if filename.endswith('.json'):
            input_path = os.path.join(directory_path, filename)
            
            if output_directory:
                # 确保输出目录存在
                os.makedirs(output_directory, exist_ok=True)
                output_path = os.path.join(output_directory, filename)
            else:
                output_path = None
            
            if process_single_file(input_path, output_path):
                success_count += 1
    
    print(f"\n处理完成，成功处理 {success_count} 个文件")
    return success_count


def main():
    """
    主函数 - 处理默认结果目录
    """
    results_dir = "d:\\VScode\\Python\\AItools\\AIQualityKit\\data\\output\\results"
    
    print("JSON文件rank字段排序工具")
    print(f"处理目录: {results_dir}")
    print("-" * 50)
    
    # 处理目录下的所有JSON文件
    process_directory(results_dir)


if __name__ == "__main__":
    main()