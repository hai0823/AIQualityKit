from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import asyncio

# Import the logic classes
from .logic.citation_analyzer_fulltext import Method1BailianAnalyzer as CitationAnalyzer
from .logic.citation_analyzer_sync import ConsistencyEvaluator as SyncAnalyzer
from .logic.citation_analyzer_async import ConsistencyEvaluator as AsyncAnalyzer
from .logic.internal_consistency_detector import InternalConsistencyDetector

app = FastAPI()

# --- App Setup ---
# Mount the static directory to serve frontend files
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Analyzers will be initialized at runtime with API keys

# --- Pydantic Models ---
class AnalysisRequest(BaseModel):
    text: str
    question: str = "" # Optional question context
    # A dictionary where key is citation number (int) and value is the text (str)
    citations: dict[int, str] = {}

# --- API Endpoints ---
@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main index.html file."""
    try:
        index_path = os.path.join(static_dir, "index.html")
        print(f"🔍 尝试读取文件: {index_path}")
        
        if not os.path.exists(index_path):
            print(f"❌ 文件不存在: {index_path}")
            return HTMLResponse(content="<h1>错误：index.html文件不存在</h1>", status_code=404)
        
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()
            print(f"✅ 成功读取index.html，大小: {len(content)} 字符")
            return HTMLResponse(content=content)
            
    except Exception as e:
        print(f"❌ 读取index.html出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return HTMLResponse(content=f"<h1>错误：无法读取index.html</h1><p>{str(e)}</p>", status_code=500)

@app.post("/api/analyze")
async def analyze_text(request: AnalysisRequest, http_request: Request):
    """
    This endpoint receives text and performs multiple analyses.
    It runs citation and consistency analysis concurrently.
    """
    # 获取API配置
    api_key = http_request.headers.get('X-API-Key')
    api_provider = http_request.headers.get('X-API-Provider', 'alibaba')
    api_model = http_request.headers.get('X-API-Model', '')
    api_base_url = http_request.headers.get('X-API-Base-URL', '')
    
    if not api_key:
        return JSONResponse(
            status_code=400,
            content={"error": "缺少API Key，请在请求头中提供X-API-Key"}
        )
    
    try:
        # 使用运行时API Key初始化引文分析器
        citation_analyzer = CitationAnalyzer(
            api_key=api_key,
            provider=api_provider,
            model=api_model if api_model else None,
            base_url=api_base_url if api_base_url else None
        )
        
        # 运行引文分析
        citation_results = await citation_analyzer.analyze(
            question=request.question,
            answer=request.text,
            citations_dict=request.citations
        )

        # Combine results into a single response
        return JSONResponse(content={
            "original_text_preview": request.text[:200] + "...",
            "citation_analysis": citation_results,
            "consistency_evaluation": "已移除旧版sliced分析器，请使用新版evaluator",
            # Placeholder for hallucination detection
            "hallucination_detection": "Not implemented yet."
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"分析失败：{str(e)}"}
        )

@app.post("/api/analyze-xlsx")
async def analyze_xlsx_file(
    request: Request,
    file: UploadFile = File(...)
):
    """
    上传xlsx文件进行批量引文分析
    """
    print("🚨🚨🚨 API函数 analyze_xlsx_file 被调用了！🚨🚨🚨")
    
    # 获取API配置和分析类型
    api_key = request.headers.get('X-API-Key')
    api_provider = request.headers.get('X-API-Provider', 'alibaba')
    api_model = request.headers.get('X-API-Model', '')
    api_base_url = request.headers.get('X-API-Base-URL', '')
    analysis_type = request.headers.get('X-Analysis-Type', 'fulltext')
    
    print(f"🔑 API配置: 密钥={'已设置' if api_key else '未设置'}, 提供商={api_provider}, 模型={api_model or '默认'}, 分析类型={analysis_type}")
    
    if not api_key:
        return JSONResponse(
            status_code=400,
            content={"error": "缺少API Key"}
        )
    
    # 检查文件类型
    if not file.filename.endswith('.xlsx'):
        return JSONResponse(
            status_code=400,
            content={"error": "只支持xlsx格式文件"}
        )
    
    try:
        print("🌟 API端点被调用")
        
        # 读取文件内容
        file_content = await file.read()
        print(f"📁 文件读取完成，大小：{len(file_content)} bytes")
        
        # 获取分析选项
        analysis_mode = request.headers.get('X-Analysis-Mode', 'all')  # all, head, specific, range
        num_samples = request.headers.get('X-Num-Samples')
        specific_rank = request.headers.get('X-Specific-Rank')  
        start_from = request.headers.get('X-Start-From')
        
        print(f"⚙️ 分析选项：type={analysis_type}, mode={analysis_mode}, samples={num_samples}, rank={specific_rank}, start={start_from}")
        
        # 转换数值参数
        try:
            if num_samples:
                num_samples = int(num_samples)
            if specific_rank:
                specific_rank = int(specific_rank)
            if start_from:
                start_from = int(start_from)
        except ValueError:
            print("❌ 参数格式错误")
            return JSONResponse(
                status_code=400,
                content={"error": "分析参数格式错误"}
            )
        
        # 根据分析类型选择分析器
        if analysis_type == 'sliced':
            # 获取执行模式（同步或异步）
            execution_mode = request.headers.get('X-Execution-Mode', 'sync')
            print(f"🔄 使用Sliced分析，执行模式: {execution_mode}")
            
            if execution_mode == 'sync':
                # 使用同步版analyzer
                print("🔄 使用同步版Sliced Analyzer进行分析...")
                analyzer = SyncAnalyzer(
                    provider=api_provider,
                    model=api_model if api_model else None,
                    api_key=api_key,
                    base_url=api_base_url if api_base_url else None
                )
            else:
                # 使用异步版analyzer
                print("🔄 使用异步版Sliced Analyzer进行分析...")
                analyzer = AsyncAnalyzer(
                    provider=api_provider,
                    model=api_model if api_model else None,
                    api_key=api_key,
                    base_url=api_base_url if api_base_url else None
                )
            
            # 创建临时文件进行分析
            import tempfile
            import json
            
            # 创建临时Excel文件
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_excel:
                temp_excel.write(file_content)
                temp_excel_path = temp_excel.name
            
            try:
                print(f"🔄 开始使用{execution_mode}模式Sliced Analyzer进行真实分析...")
                
                # 读取Excel文件数据
                import pandas as pd
                import io
                
                try:
                    # 将文件内容转换为DataFrame
                    df = pd.read_excel(io.BytesIO(file_content))
                    print(f"📊 Excel文件读取成功，共{len(df)}行数据")
                    
                    # 根据分析模式筛选数据
                    if analysis_mode == 'head' and num_samples:
                        df_to_analyze = df.head(num_samples)
                        print(f"🔍 分析前{num_samples}条数据")
                    elif analysis_mode == 'specific' and specific_rank:
                        if specific_rank <= len(df):
                            df_to_analyze = df.iloc[[specific_rank - 1]]  # -1 因为索引从0开始
                            print(f"🔍 分析第{specific_rank}条数据")
                        else:
                            raise ValueError(f"指定的rank {specific_rank} 超出数据范围（共{len(df)}行）")
                    elif analysis_mode == 'range' and start_from:
                        start_idx = start_from - 1  # -1 因为索引从0开始
                        if num_samples:
                            end_idx = start_idx + num_samples
                            df_to_analyze = df.iloc[start_idx:end_idx]
                            print(f"🔍 分析从第{start_from}条开始的{num_samples}条数据")
                        else:
                            df_to_analyze = df.iloc[start_idx:]
                            print(f"🔍 分析从第{start_from}条到结尾的数据")
                    else:
                        df_to_analyze = df
                        print(f"🔍 分析所有{len(df)}条数据")
                    
                    print(f"📈 实际分析数据行数：{len(df_to_analyze)}")
                    
                    # 真正调用analyzer进行分析
                    import datetime
                    analysis_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # 使用citation_processor处理Excel文件，提取引文标注
                    from .logic.citation_processor import process_excel_file
                    
                    # 保存临时Excel文件内容到磁盘供citation_processor使用
                    temp_excel_for_processing_fd, temp_excel_for_processing = tempfile.mkstemp(suffix='.xlsx', prefix='excel_for_processing_')
                    with os.fdopen(temp_excel_for_processing_fd, 'wb') as f:
                        f.write(file_content)
                    
                    print("🔄 使用citation_processor提取引文标注...")
                    try:
                        # 使用citation_processor提取引文标注的句子
                        citation_results = process_excel_file(temp_excel_for_processing)
                        print(f"📊 提取到{len(citation_results)}个包含引文标注的句子")
                        
                        # 根据分析模式筛选citation_results
                        if analysis_mode == 'head' and num_samples:
                            # 获取前N个rank的数据
                            citation_results = [r for r in citation_results if r['rank'] <= num_samples]
                        elif analysis_mode == 'specific' and specific_rank:
                            # 获取特定rank的数据
                            citation_results = [r for r in citation_results if r['rank'] == specific_rank]
                        elif analysis_mode == 'range' and start_from:
                            # 获取范围内的数据
                            if num_samples:
                                end_rank = start_from + num_samples - 1
                                citation_results = [r for r in citation_results if start_from <= r['rank'] <= end_rank]
                            else:
                                citation_results = [r for r in citation_results if r['rank'] >= start_from]
                        
                        print(f"📈 筛选后待分析数据：{len(citation_results)}条")
                        
                    except Exception as e:
                        print(f"❌ citation_processor处理失败：{e}")
                        citation_results = []
                    finally:
                        # 清理临时文件
                        try:
                            os.unlink(temp_excel_for_processing)
                        except:
                            pass
                    
                    # 创建临时文件
                    import tempfile
                    import json
                    
                    # 创建临时citation_results.json文件
                    temp_citation_fd, temp_citation_path = tempfile.mkstemp(suffix='.json', prefix='citation_results_')
                    with os.fdopen(temp_citation_fd, 'w', encoding='utf-8') as f:
                        json.dump(citation_results, f, ensure_ascii=False, indent=2)
                    
                    try:
                        # 确定分析范围
                        if analysis_mode == 'head' and num_samples:
                            rank_start, rank_end = 1, num_samples
                        elif analysis_mode == 'specific' and specific_rank:
                            rank_start, rank_end = specific_rank, specific_rank
                        elif analysis_mode == 'range' and start_from:
                            if num_samples:
                                rank_start, rank_end = start_from, start_from + num_samples - 1
                            else:
                                rank_start, rank_end = start_from, len(df_to_analyze)
                        else:
                            rank_start, rank_end = 1, len(df_to_analyze)
                        
                        print(f"🔍 调用analyzer分析 rank {rank_start} 到 {rank_end}")
                        
                        # 调用analyzer
                        if execution_mode == 'sync':
                            # 同步模式
                            print("🔄 开始同步分析...")
                            analyzer_results = analyzer.evaluate_consistency(
                                citation_file=temp_citation_path,
                                excel_file=temp_excel_path,
                                rank_start=rank_start,
                                rank_end=rank_end
                            )
                        else:
                            # 异步模式
                            print("🔄 开始异步分析...")
                            analyzer_results = await analyzer.evaluate_consistency_async(
                                citation_file=temp_citation_path,
                                excel_file=temp_excel_path,
                                rank_start=rank_start,
                                rank_end=rank_end
                            )
                        
                        # 处理analyzer结果
                        results = []
                        if analyzer_results and isinstance(analyzer_results, list):
                            for result in analyzer_results:
                                # 构建分析结果文本
                                analysis_text = f"一致性评估：{result.get('consistency', '未知')}\n"
                                analysis_text += f"引用内容：{result.get('citation_topic', '无')}\n"
                                analysis_text += f"分析原因：{result.get('reason', '无')}"
                                
                                # 计算一致性分数（一致=1.0，不一致=0.0）
                                consistency = result.get('consistency', '')
                                consistency_score = 1.0 if consistency == '一致' else 0.0
                                
                                processed_result = {
                                    "rank": result.get("rank", 0),
                                    "api_success": True,  # 如果返回了结果说明API调用成功
                                    "analysis_type": "sliced",
                                    "execution_mode": execution_mode,
                                    "analysis_mode": analysis_mode,
                                    "provider": api_provider,
                                    "model": api_model or "default",
                                    "analysis_time": analysis_time,
                                    "message": f"Sliced分析完成 - {execution_mode}模式，第{result.get('rank', 0)}行",
                                    "status": "success",
                                    "question": result.get("topic", "")[:200],
                                    "analysis": analysis_text,
                                    "citations_found": result.get("citation_numbers", []),
                                    "consistency_score": consistency_score,
                                    "processing_time": "1.0s"  # 简化处理时间显示
                                }
                                results.append(processed_result)
                        else:
                            # 如果analyzer没有返回结果，创建错误信息
                            results = [{
                                "rank": 1,
                                "api_success": False,
                                "analysis_type": "sliced",
                                "execution_mode": execution_mode,
                                "status": "failed",
                                "message": "Analyzer调用失败",
                                "error": "Analyzer未返回有效结果",
                                "analysis": f"Sliced analyzer调用失败，可能的原因：\n1. 数据格式不匹配\n2. API调用失败\n3. 文件处理错误"
                            }]
                        
                        print(f"✅ Sliced analyzer分析完成，获得{len(results)}条结果")
                        
                    finally:
                        # 清理临时citation文件
                        try:
                            os.unlink(temp_citation_path)
                        except:
                            pass
                    
                except Exception as e:
                    print(f"❌ Excel文件处理失败：{str(e)}")
                    # 如果Excel处理失败，返回错误信息
                    results = [{
                        "rank": 1,
                        "api_success": False,
                        "analysis_type": "sliced",
                        "execution_mode": execution_mode,
                        "status": "failed",
                        "message": "Excel文件处理失败",
                        "error": str(e),
                        "analysis": f"无法处理Excel文件：{str(e)}\n\n请确保文件格式正确，包含必要的列：模型prompt、答案、引文1-引文20"
                    }]
                
            finally:
                # 清理临时文件
                try:
                    os.unlink(temp_excel_path)
                except:
                    pass
        else:
            # 使用fulltext版本分析器（默认）
            citation_analyzer = CitationAnalyzer(
                api_key=api_key,
                provider=api_provider,
                model=api_model if api_model else None,
                base_url=api_base_url if api_base_url else None
            )
            
            # 直接调用脚本方法并从保存的文件读取结果
            import tempfile
            import json
            import uuid
            
            # 创建临时Excel文件
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_excel:
                temp_excel.write(file_content)
                temp_excel_path = temp_excel.name
            
            # 创建临时JSON输出文件
            import tempfile
            temp_json_fd, temp_json_path = tempfile.mkstemp(suffix='.json', prefix='web_analysis_')
            os.close(temp_json_fd)  # 关闭文件描述符，让脚本可以写入文件
            
            try:
                print("🔄 开始调用fulltext分析脚本...")
                
                # 根据分析模式调用脚本方法
                if analysis_mode == 'head' and num_samples:
                    print(f"📊 分析模式：前{num_samples}条")
                    script_results = await citation_analyzer.batch_analyze_concurrent(
                        temp_excel_path, num_samples=num_samples
                    )
                elif analysis_mode == 'specific' and specific_rank:
                    print(f"📊 分析模式：第{specific_rank}条")
                    script_results = await citation_analyzer.batch_analyze_concurrent(
                        temp_excel_path, specific_rank=specific_rank
                    )
                elif analysis_mode == 'range' and start_from:
                    print(f"📊 分析模式：从第{start_from}条开始，{num_samples or '全部'}条")
                    script_results = await citation_analyzer.batch_analyze_concurrent(
                        temp_excel_path, start_from=start_from, num_samples=num_samples
                    )
                else:
                    # 默认分析所有数据
                    print("📊 分析模式：全部数据")
                    script_results = await citation_analyzer.batch_analyze_concurrent(temp_excel_path)
                
                print(f"✅ 脚本分析完成，获得{len(script_results)}条结果")
                
                # 使用脚本的保存方法保存到临时文件
                print("💾 保存临时结果文件...")
                citation_analyzer.save_results(script_results, temp_json_path)
                
                # 同时保存到项目的data/output/results目录
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                permanent_output_path = os.path.join(
                    os.path.dirname(__file__), "..", "data", "output", "results",
                    f"web_analysis_{analysis_type}_{analysis_mode}_{timestamp}.json"
                )
                
                # 确保输出目录存在
                print(f"📁 准备保存到：{permanent_output_path}")
                os.makedirs(os.path.dirname(permanent_output_path), exist_ok=True)
                
                # 保存永久副本
                citation_analyzer.save_results(script_results, permanent_output_path)
                print(f"✅ Web分析结果已保存到：{permanent_output_path}")
                
                # 从保存的文件读取干净的数据
                print("📖 从文件读取结果...")
                with open(temp_json_path, 'r', encoding='utf-8') as f:
                    results = json.load(f)
                
                print(f"✅ 成功读取{len(results)}条结果")
                
                # 清理临时文件
                try:
                    os.unlink(temp_json_path)
                    print("🧹 临时文件已清理")
                except:
                    pass
                    
            except Exception as e:
                print(f"❌ Fulltext分析过程出错：{str(e)}")
                import traceback
                traceback.print_exc()
                raise ValueError(f"Fulltext分析执行失败：{str(e)}")
            finally:
                # 清理临时Excel文件
                try:
                    os.unlink(temp_excel_path)
                except:
                    pass
        
        # 添加分析选项信息到结果中
        analysis_info = {
            'analysis_type': analysis_type,
            'analysis_mode': analysis_mode
        }
        if num_samples:
            analysis_info['num_samples'] = num_samples
        if specific_rank:
            analysis_info['specific_rank'] = specific_rank
        if start_from:
            analysis_info['start_from'] = start_from
        
        # 统计结果
        total_count = len(results)
        success_count = sum(1 for r in results if r.get('api_success', False))
        failed_count = total_count - success_count
        
        # 清理返回结果中的无效浮点数
        def clean_for_json(obj):
            """递归清理对象中的无效浮点数"""
            import math
            import pandas as pd
            import numpy as np
            
            if isinstance(obj, dict):
                return {key: clean_for_json(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [clean_for_json(item) for item in obj]
            elif isinstance(obj, (float, np.floating)):
                if math.isnan(obj) or math.isinf(obj):
                    return None
                return float(obj)
            elif isinstance(obj, (np.integer, np.int64)):
                return int(obj)
            elif hasattr(obj, 'item'):  # numpy标量
                return clean_for_json(obj.item())
            else:
                # 使用pandas检查NaN/NA
                try:
                    if pd.isna(obj):
                        return None
                except (TypeError, ValueError):
                    pass
                return obj
        
        # 清理响应数据
        response_data = {
            "filename": file.filename,
            "analysis_type": analysis_type,
            "analysis_mode": analysis_mode,
            "total_rows": total_count,
            "success_count": success_count,
            "failed_count": failed_count,
            "results": results[:10] if len(results) > 10 else results,
            "full_results_available": len(results) > 10,
            "output_file_saved": permanent_output_path if 'permanent_output_path' in locals() else None
        }
        
        cleaned_response = clean_for_json(response_data)
        return JSONResponse(content=cleaned_response)
        
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"处理文件时发生错误：{str(e)}"}
        )

@app.post("/api/analyze-internal-consistency")
async def analyze_internal_consistency(
    request: Request,
    file: UploadFile = File(...)
):
    """
    上传xlsx文件进行内部一致性检测（新版幻觉检测）
    不依赖引文，检测答案自身的逻辑一致性
    """
    print("🔍 内部一致性检测API被调用！")
    
    # 获取API配置
    api_key = request.headers.get('X-API-Key')
    api_provider = request.headers.get('X-API-Provider', 'deepseek')
    api_model = request.headers.get('X-API-Model', '')
    api_base_url = request.headers.get('X-API-Base-URL', '')
    
    print(f"🔑 API配置: 密钥={'已设置' if api_key else '未设置'}, 提供商={api_provider}, 模型={api_model or '默认'}")
    
    if not api_key:
        return JSONResponse(
            status_code=400,
            content={"error": "缺少API Key"}
        )
    
    # 检查文件类型
    if not file.filename.endswith('.xlsx'):
        return JSONResponse(
            status_code=400,
            content={"error": "只支持xlsx格式文件"}
        )
    
    try:
        print("🔍 开始内部一致性检测...")
        
        # 读取文件内容
        file_content = await file.read()
        print(f"📁 文件读取完成，大小：{len(file_content)} bytes")
        
        # 获取分析选项
        analysis_mode = request.headers.get('X-Analysis-Mode', 'all')
        num_samples = request.headers.get('X-Num-Samples')
        specific_rank = request.headers.get('X-Specific-Rank')
        start_from = request.headers.get('X-Start-From')
        concurrent_limit = request.headers.get('X-Concurrent-Limit', '10')
        
        print(f"⚙️ 分析选项：mode={analysis_mode}, samples={num_samples}, rank={specific_rank}, start={start_from}, concurrent={concurrent_limit}")
        
        # 转换数值参数
        try:
            if num_samples:
                num_samples = int(num_samples)
            if specific_rank:
                specific_rank = int(specific_rank)
            if start_from:
                start_from = int(start_from)
            concurrent_limit = int(concurrent_limit)
        except ValueError:
            print("❌ 参数格式错误")
            return JSONResponse(
                status_code=400,
                content={"error": "分析参数格式错误"}
            )
        
        # 创建内部一致性检测器
        print(f"🔄 初始化内部一致性检测器...")
        detector = InternalConsistencyDetector(
            provider=api_provider,
            api_key=api_key,
            base_url=api_base_url if api_base_url else None,
            model=api_model if api_model else None,
            concurrent_limit=concurrent_limit
        )
        
        # 执行分析
        print(f"🔄 开始内部一致性检测...")
        import datetime
        analysis_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        results = await detector.batch_analyze_excel(
            file_content=file_content,
            num_samples=num_samples,
            specific_rank=specific_rank,
            start_from=start_from
        )
        
        print(f"✅ 内部一致性检测完成，获得{len(results)}条结果")
        
        # 生成摘要
        summary = detector.generate_summary(results)
        print(f"📊 分析摘要：成功{summary['success_count']}条，问题{summary['problem_count']}条")
        
        # 保存结果到项目目录
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "output", "results",
            f"internal_consistency_{analysis_mode}_{timestamp}.json"
        )
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        detector.save_results(results, output_path)
        print(f"✅ 结果已保存到：{output_path}")
        
        # 构建响应数据
        response_data = {
            "filename": file.filename,
            "analysis_type": "internal_consistency",
            "analysis_mode": analysis_mode,
            "provider": api_provider,
            "model": api_model or "default",
            "analysis_time": analysis_time,
            "total_count": summary['total_count'],
            "success_count": summary['success_count'],
            "failed_count": summary['failed_count'],
            "problem_count": summary['problem_count'],
            "no_problem_count": summary['no_problem_count'],
            "problem_rate": round(summary['problem_rate'], 3),
            "status_distribution": summary['status_distribution'],
            "analysis_summary": summary['analysis_summary'],
            "results": results[:10] if len(results) > 10 else results,  # 只返回前10条详细结果
            "full_results_available": len(results) > 10,
            "output_file_saved": output_path,
            "message": f"内部一致性检测完成，发现{summary['problem_count']}个问题"
        }
        
        return JSONResponse(content=response_data)
        
    except ValueError as e:
        print(f"❌ 参数错误：{str(e)}")
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        print(f"❌ 内部一致性检测失败：{str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": f"内部一致性检测失败：{str(e)}"}
        )
