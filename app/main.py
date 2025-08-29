from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import asyncio

# Import the logic classes
from .logic.citation_analyzer_fulltext import Method1BailianAnalyzer as CitationAnalyzer
from .logic.citation_analyzer_sliced import ConsistencyEvaluator as SlicedAnalyzer

app = FastAPI()

# --- App Setup ---
# Mount the static directory to serve frontend files
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Initialize analyzers
# It's better to initialize them once when the app starts
print("🚀 正在初始化分析器...")
try:
    citation_analyzer = CitationAnalyzer()
    print("✅ Fulltext分析器初始化成功")
except Exception as e:
    print(f"❌ Fulltext分析器初始化失败：{e}")
    import traceback
    traceback.print_exc()

try:
    sliced_analyzer = SlicedAnalyzer()
    print("✅ Sliced分析器初始化成功")
except Exception as e:
    print(f"❌ Sliced分析器初始化失败：{e}")
    import traceback
    traceback.print_exc()

print("🎯 分析器初始化完成")

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
    index_path = os.path.join(static_dir, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/api/analyze")
async def analyze_text(request: AnalysisRequest):
    """
    This endpoint receives text and performs multiple analyses.
    It runs citation and consistency analysis concurrently.
    """
    # Create concurrent tasks for each analysis
    citation_task = citation_analyzer.analyze(
        question=request.question,
        answer=request.text,
        citations_dict=request.citations
    )
    
    consistency_task = asyncio.to_thread(sliced_analyzer.evaluate, request.text)

    # Run tasks concurrently and wait for results
    citation_results, consistency_results = await asyncio.gather(
        citation_task,
        consistency_task
    )

    # Combine results into a single response
    return JSONResponse(content={
        "original_text_preview": request.text[:200] + "...",
        "citation_analysis": citation_results,
        "consistency_evaluation": consistency_results,
        # Placeholder for hallucination detection
        "hallucination_detection": "Not implemented yet."
    })

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
            # 使用sliced版本分析器，支持多API提供商
            analyzer = SlicedAnalyzer(
                api_key=api_key,
                provider=api_provider,
                base_url=api_base_url if api_base_url else None,
                model=api_model if api_model else None
            )
            results = await analyzer.analyze_xlsx_file(
                file_content=file_content,
                filename=file.filename
            )
        else:
            # 使用fulltext版本分析器（默认）
            citation_analyzer.api_key = api_key  # 设置API Key
            
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
