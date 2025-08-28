from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import asyncio

# Import the logic classes
from .logic.citation_analyzer_fulltext import CitationAnalyzer
from .logic.citation_analyzer_sliced import ConsistencyEvaluator

app = FastAPI()

# --- App Setup ---
# Mount the static directory to serve frontend files
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Initialize analyzers
# It's better to initialize them once when the app starts
citation_analyzer = CitationAnalyzer()
consistency_evaluator = ConsistencyEvaluator()

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
    
    consistency_task = asyncio.to_thread(consistency_evaluator.evaluate, request.text)

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
async def analyze_xlsx_file(file: UploadFile = File(...)):
    """
    上传xlsx文件进行批量引文分析
    """
    # 检查文件类型
    if not file.filename.endswith('.xlsx'):
        return JSONResponse(
            status_code=400,
            content={"error": "只支持xlsx格式文件"}
        )
    
    try:
        # 读取文件内容
        file_content = await file.read()
        
        # 使用fulltext版本分析器处理xlsx文件
        results = await citation_analyzer.analyze_xlsx_file(
            file_content=file_content,
            filename=file.filename
        )
        
        # 统计结果
        total_count = len(results)
        success_count = sum(1 for r in results if r.get('api_success', False))
        failed_count = total_count - success_count
        
        return JSONResponse(content={
            "filename": file.filename,
            "total_rows": total_count,
            "success_count": success_count,
            "failed_count": failed_count,
            "results": results[:10] if len(results) > 10 else results,  # 只返回前10个结果预览
            "full_results_available": len(results) > 10
        })
        
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
