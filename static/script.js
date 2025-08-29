// 全局变量
let selectedFile = null;
let apiKey = '';

// DOM元素
const apiKeyInput = document.getElementById('api-key');
const fileInput = document.getElementById('file-input');
const fileInfo = document.getElementById('file-info');
const analyzeXlsxBtn = document.getElementById('analyze-xlsx-btn');
const progressInfo = document.getElementById('progress-info');
const resultsOutput = document.getElementById('results-output');
const analyzeBtn = document.getElementById('analyze-btn');
const textInput = document.getElementById('text-input');

// 初始化事件监听器
document.addEventListener('DOMContentLoaded', function() {
    // API Key输入监听
    apiKeyInput.addEventListener('input', function() {
        apiKey = this.value.trim();
        updateAnalyzeButton();
    });

    // 文件选择监听
    fileInput.addEventListener('change', function() {
        const file = this.files[0];
        if (file) {
            selectedFile = file;
            showFileInfo(file);
        } else {
            selectedFile = null;
            hideFileInfo();
        }
        updateAnalyzeButton();
    });

    // 分析类型切换监听
    document.querySelectorAll('input[name="analysis-type"]').forEach(radio => {
        radio.addEventListener('change', function() {
            toggleFulltextOptions(this.value === 'fulltext');
        });
    });

    // Fulltext详细选项监听
    document.querySelectorAll('input[name="fulltext-mode"]').forEach(radio => {
        radio.addEventListener('change', function() {
            showRelevantInputs(this.value);
        });
    });

    // Excel分析按钮点击
    analyzeXlsxBtn.addEventListener('click', analyzeXlsxFile);

    // 原有的文本分析按钮
    analyzeBtn.addEventListener('click', analyzeText);

    // 初始化界面状态
    toggleFulltextOptions(true);
    showRelevantInputs('all');
});

// 更新分析按钮状态
function updateAnalyzeButton() {
    const hasApiKey = apiKey.length > 0;
    const hasFile = selectedFile !== null;
    
    analyzeXlsxBtn.disabled = !(hasApiKey && hasFile);
}

// 显示文件信息
function showFileInfo(file) {
    const sizeInMB = (file.size / (1024 * 1024)).toFixed(2);
    fileInfo.innerHTML = `
        <strong>已选择文件:</strong> ${file.name}<br>
        <strong>文件大小:</strong> ${sizeInMB} MB<br>
        <strong>文件类型:</strong> ${file.type || 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}
    `;
    fileInfo.style.display = 'block';
}

// 隐藏文件信息
function hideFileInfo() {
    fileInfo.style.display = 'none';
}

// 显示进度信息
function showProgress(message) {
    progressInfo.textContent = message;
    progressInfo.style.display = 'block';
}

// 隐藏进度信息
function hideProgress() {
    progressInfo.style.display = 'none';
}

// 切换Fulltext选项显示
function toggleFulltextOptions(show) {
    const fulltextOptions = document.getElementById('fulltext-options');
    fulltextOptions.style.display = show ? 'block' : 'none';
}

// 显示相关输入框
function showRelevantInputs(mode) {
    // 隐藏所有输入框
    document.getElementById('head-input').style.display = 'none';
    document.getElementById('specific-input').style.display = 'none';
    document.getElementById('range-input').style.display = 'none';
    
    // 显示相关输入框
    switch (mode) {
        case 'head':
            document.getElementById('head-input').style.display = 'flex';
            break;
        case 'specific':
            document.getElementById('specific-input').style.display = 'flex';
            break;
        case 'range':
            document.getElementById('range-input').style.display = 'flex';
            break;
    }
}

// 获取分析选项
function getAnalysisOptions() {
    const analysisType = document.querySelector('input[name="analysis-type"]:checked').value;
    const options = {
        'X-Analysis-Type': analysisType
    };

    if (analysisType === 'fulltext') {
        const fulltextMode = document.querySelector('input[name="fulltext-mode"]:checked').value;
        options['X-Analysis-Mode'] = fulltextMode;

        switch (fulltextMode) {
            case 'head':
                const numSamples = document.getElementById('num-samples').value;
                if (numSamples) {
                    options['X-Num-Samples'] = numSamples;
                }
                break;
            case 'specific':
                const specificRank = document.getElementById('specific-rank').value;
                if (specificRank) {
                    options['X-Specific-Rank'] = specificRank;
                }
                break;
            case 'range':
                const startFrom = document.getElementById('start-from').value;
                const rangeCount = document.getElementById('range-count').value;
                if (startFrom) {
                    options['X-Start-From'] = startFrom;
                    if (rangeCount) {
                        options['X-Num-Samples'] = rangeCount;
                    }
                }
                break;
        }
    }

    return options;
}

// 分析Excel文件
async function analyzeXlsxFile() {
    if (!selectedFile || !apiKey) {
        return;
    }

    const analysisOptions = getAnalysisOptions();
    const analysisType = analysisOptions['X-Analysis-Type'];
    
    // 准备FormData
    const formData = new FormData();
    formData.append('file', selectedFile);
    
    // 禁用按钮并显示进度
    analyzeXlsxBtn.disabled = true;
    analyzeXlsxBtn.textContent = '正在分析...';
    
    let progressMsg = `正在使用${analysisType}模式分析文件: ${selectedFile.name}`;
    if (analysisType === 'fulltext') {
        const mode = analysisOptions['X-Analysis-Mode'];
        if (mode === 'head' && analysisOptions['X-Num-Samples']) {
            progressMsg += ` (前${analysisOptions['X-Num-Samples']}条)`;
        } else if (mode === 'specific' && analysisOptions['X-Specific-Rank']) {
            progressMsg += ` (第${analysisOptions['X-Specific-Rank']}条)`;
        } else if (mode === 'range' && analysisOptions['X-Start-From']) {
            const startFrom = analysisOptions['X-Start-From'];
            const count = analysisOptions['X-Num-Samples'] || '到结尾';
            progressMsg += ` (从第${startFrom}条开始，${count}条)`;
        }
    }
    
    showProgress(progressMsg);
    resultsOutput.textContent = '正在处理文件，请稍候...';

    try {
        // 设置请求头
        const headers = {
            'X-API-Key': apiKey,
            ...analysisOptions
        };

        const response = await fetch('/api/analyze-xlsx', {
            method: 'POST',
            headers: headers,
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }

        const results = await response.json();
        showResults(results);
        showProgress(`分析完成！处理了 ${results.total_rows} 行数据，成功 ${results.success_count} 个，失败 ${results.failed_count} 个`);

    } catch (error) {
        console.error('Error during Excel analysis:', error);
        resultsOutput.textContent = `分析出错: ${error.message}`;
        hideProgress();
    } finally {
        // 恢复按钮状态
        analyzeXlsxBtn.disabled = false;
        analyzeXlsxBtn.textContent = '开始分析';
    }
}

// 显示分析结果
function showResults(results) {
    // 创建格式化的结果展示
    let formattedOutput = '';
    
    // 添加文件基本信息
    formattedOutput += `=== 文件分析报告 ===\n`;
    formattedOutput += `文件名: ${results.filename}\n`;
    formattedOutput += `分析类型: ${results.analysis_type || 'fulltext'}\n`;
    formattedOutput += `分析模式: ${results.analysis_mode || 'all'}\n`;
    formattedOutput += `总行数: ${results.total_rows}\n`;
    formattedOutput += `成功分析: ${results.success_count}条\n`;
    formattedOutput += `分析失败: ${results.failed_count}条\n`;
    formattedOutput += `成功率: ${((results.success_count / results.total_rows) * 100).toFixed(1)}%\n`;
    
    // 显示文件保存信息
    if (results.output_file_saved) {
        formattedOutput += `\n📁 完整结果文件已保存到: ${results.output_file_saved}\n`;
        formattedOutput += `   (即使前端显示异常，完整结果已保存在此文件中)\n`;
    }
    
    formattedOutput += `\n`;
    
    // 添加结果预览
    if (results.results && results.results.length > 0) {
        formattedOutput += `=== 分析结果预览 ===\n`;
        results.results.forEach((result, index) => {
            formattedOutput += `\n--- 第${result.rank || index + 1}条数据 ---\n`;
            
            if (result.api_success) {
                formattedOutput += `状态: ✓ 成功\n`;
                if (result.question) {
                    formattedOutput += `问题: ${result.question.substring(0, 100)}${result.question.length > 100 ? '...' : ''}\n`;
                }
                if (result.answer_preview) {
                    formattedOutput += `答案预览: ${result.answer_preview}\n`;
                }
                if (result.citations_used) {
                    formattedOutput += `使用的引用: [${result.citations_used.join(', ')}]\n`;
                }
                if (result.analysis) {
                    if (typeof result.analysis === 'string') {
                        formattedOutput += `分析结果: ${result.analysis.substring(0, 200)}${result.analysis.length > 200 ? '...' : ''}\n`;
                    } else if (Array.isArray(result.analysis) && result.analysis.length > 0) {
                        formattedOutput += `分析结果: 发现${result.analysis.length}个引用分析项\n`;
                        result.analysis.forEach((item, i) => {
                            if (i < 2) { // 只显示前2项
                                formattedOutput += `  ${i + 1}. ${item.topic || item.content || JSON.stringify(item).substring(0, 50)}...\n`;
                            }
                        });
                        if (result.analysis.length > 2) {
                            formattedOutput += `  ... 还有${result.analysis.length - 2}项\n`;
                        }
                    }
                }
            } else {
                formattedOutput += `状态: ✗ 失败\n`;
                if (result.api_error || result.error) {
                    formattedOutput += `错误: ${result.api_error || result.error}\n`;
                }
                if (result.row_data) {
                    const keys = Object.keys(result.row_data).slice(0, 3);
                    formattedOutput += `数据字段: ${keys.join(', ')}${Object.keys(result.row_data).length > 3 ? '...' : ''}\n`;
                }
            }
        });
        
        if (results.full_results_available) {
            formattedOutput += `\n注意: 结果过多，仅显示前${results.results.length}个。完整结果已保存在服务器。\n`;
        }
    } else {
        formattedOutput += `=== 无有效结果 ===\n`;
        formattedOutput += `没有获得有效的分析结果，请检查文件格式和API配置。\n`;
    }
    
    // 添加JSON格式的详细数据（可选展开）
    formattedOutput += `\n=== 详细数据（JSON格式） ===\n`;
    formattedOutput += JSON.stringify(results, null, 2);
    
    resultsOutput.textContent = formattedOutput;
}

// 原有的文本分析功能
async function analyzeText() {
    const textValue = textInput.value;
    
    if (!textValue.trim()) {
        resultsOutput.textContent = '请输入要分析的文本';
        return;
    }

    resultsOutput.textContent = '正在分析文本...';
    analyzeBtn.disabled = true;
    analyzeBtn.textContent = '分析中...';

    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text: textValue }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const results = await response.json();
        resultsOutput.textContent = JSON.stringify(results, null, 2);

    } catch (error) {
        console.error('Error during text analysis:', error);
        resultsOutput.textContent = `分析出错: ${error.message}`;
    } finally {
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = '分析文本';
    }
}
