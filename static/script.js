// 全局变量
let selectedFile = null;
let apiKey = '';
let apiProvider = 'demo';
let apiModel = '';
let apiBaseUrl = '';

// DOM元素
const apiProviderSelect = document.getElementById('api-provider');
const modelNameInput = document.getElementById('model-name');
const modelLabel = document.getElementById('model-label');
const modelHelp = document.getElementById('model-help');
const apiKeyInput = document.getElementById('api-key');
const apiKeyLabel = document.getElementById('api-key-label');
const apiBaseUrlInput = document.getElementById('api-base-url');
const showAdvancedCheckbox = document.getElementById('show-advanced-api');
const fileInput = document.getElementById('file-input');
const fileInfo = document.getElementById('file-info');
const analyzeXlsxBtn = document.getElementById('analyze-xlsx-btn');
const progressInfo = document.getElementById('progress-info');
const resultsOutput = document.getElementById('results-output');

// 初始化事件监听器
document.addEventListener('DOMContentLoaded', function() {
    // API提供商选择监听
    apiProviderSelect.addEventListener('change', function() {
        apiProvider = this.value;
        updateApiKeyLabel();
        updateDefaultModel();
        updateDemoConfiguration();
    });

    // 模型名称输入监听
    modelNameInput.addEventListener('input', function() {
        apiModel = this.value.trim();
        updateAnalyzeButton();
    });

    // 显示高级选项监听
    showAdvancedCheckbox.addEventListener('change', function() {
        toggleAdvancedOptions(this.checked);
    });

    // API高级选项监听
    apiBaseUrlInput.addEventListener('input', function() {
        apiBaseUrl = this.value.trim();
    });

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
            toggleAnalysisOptions(this.value);
        });
    });

    // Fulltext详细选项监听
    document.querySelectorAll('input[name="fulltext-mode"]').forEach(radio => {
        radio.addEventListener('change', function() {
            showFulltextInputs(this.value);
        });
    });

    // Sliced详细选项监听
    document.querySelectorAll('input[name="sliced-mode"]').forEach(radio => {
        radio.addEventListener('change', function() {
            showSlicedInputs(this.value);
        });
    });

    // Hallucination详细选项监听
    document.querySelectorAll('input[name="hallucination-mode"]').forEach(radio => {
        radio.addEventListener('change', function() {
            showHallucinationInputs(this.value);
        });
    });

    // Excel分析按钮点击
    analyzeXlsxBtn.addEventListener('click', analyzeXlsxFile);


    // 初始化界面状态
    updateDefaultModel();
    updateDemoConfiguration();
    toggleAnalysisOptions('fulltext');
    showFulltextInputs('all');
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

// 切换分析选项显示
function toggleAnalysisOptions(analysisType) {
    const fulltextOptions = document.getElementById('fulltext-options');
    const slicedOptions = document.getElementById('sliced-options');
    const hallucinationOptions = document.getElementById('hallucination-options');
    
    if (analysisType === 'fulltext') {
        fulltextOptions.style.display = 'block';
        slicedOptions.style.display = 'none';
        hallucinationOptions.style.display = 'none';
    } else if (analysisType === 'sliced') {
        fulltextOptions.style.display = 'none';
        slicedOptions.style.display = 'block';
        hallucinationOptions.style.display = 'none';
        // 初始化sliced输入框显示
        showSlicedInputs('all');
    } else if (analysisType === 'hallucination') {
        fulltextOptions.style.display = 'none';
        slicedOptions.style.display = 'none';
        hallucinationOptions.style.display = 'block';
        // 初始化hallucination输入框显示
        showHallucinationInputs('all');
    }
}

// 显示Fulltext相关输入框
function showFulltextInputs(mode) {
    // 隐藏所有fulltext输入框
    document.getElementById('fulltext-head-input').style.display = 'none';
    document.getElementById('fulltext-specific-input').style.display = 'none';
    document.getElementById('fulltext-range-input').style.display = 'none';
    
    // 显示相关输入框
    switch (mode) {
        case 'head':
            document.getElementById('fulltext-head-input').style.display = 'flex';
            break;
        case 'specific':
            document.getElementById('fulltext-specific-input').style.display = 'flex';
            break;
        case 'range':
            document.getElementById('fulltext-range-input').style.display = 'flex';
            break;
    }
}

// 显示Sliced相关输入框
function showSlicedInputs(mode) {
    // 隐藏所有sliced输入框
    document.getElementById('sliced-head-input').style.display = 'none';
    document.getElementById('sliced-specific-input').style.display = 'none';
    document.getElementById('sliced-range-input').style.display = 'none';
    
    // 显示相关输入框
    switch (mode) {
        case 'head':
            document.getElementById('sliced-head-input').style.display = 'flex';
            break;
        case 'specific':
            document.getElementById('sliced-specific-input').style.display = 'flex';
            break;
        case 'range':
            document.getElementById('sliced-range-input').style.display = 'flex';
            break;
    }
}

// 显示Hallucination相关输入框
function showHallucinationInputs(mode) {
    // 隐藏所有hallucination输入框
    document.getElementById('hallucination-head-input').style.display = 'none';
    document.getElementById('hallucination-specific-input').style.display = 'none';
    document.getElementById('hallucination-range-input').style.display = 'none';
    
    // 显示相关输入框
    switch (mode) {
        case 'head':
            document.getElementById('hallucination-head-input').style.display = 'flex';
            break;
        case 'specific':
            document.getElementById('hallucination-specific-input').style.display = 'flex';
            break;
        case 'range':
            document.getElementById('hallucination-range-input').style.display = 'flex';
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
                const numSamples = document.getElementById('fulltext-num-samples').value;
                if (numSamples) {
                    options['X-Num-Samples'] = numSamples;
                }
                break;
            case 'specific':
                const specificRank = document.getElementById('fulltext-specific-rank').value;
                if (specificRank) {
                    options['X-Specific-Rank'] = specificRank;
                }
                break;
            case 'range':
                const startFrom = document.getElementById('fulltext-start-from').value;
                const rangeCount = document.getElementById('fulltext-range-count').value;
                if (startFrom) {
                    options['X-Start-From'] = startFrom;
                    if (rangeCount) {
                        options['X-Num-Samples'] = rangeCount;
                    }
                }
                break;
        }
    } else if (analysisType === 'sliced') {
        // 获取执行模式
        const executionMode = document.querySelector('input[name="sliced-execution"]:checked').value;
        options['X-Execution-Mode'] = executionMode;
        
        // 获取分析范围
        const slicedMode = document.querySelector('input[name="sliced-mode"]:checked').value;
        options['X-Analysis-Mode'] = slicedMode;

        switch (slicedMode) {
            case 'head':
                const numSamples = document.getElementById('sliced-num-samples').value;
                if (numSamples) {
                    options['X-Num-Samples'] = numSamples;
                }
                break;
            case 'specific':
                const specificRank = document.getElementById('sliced-specific-rank').value;
                if (specificRank) {
                    options['X-Specific-Rank'] = specificRank;
                }
                break;
            case 'range':
                const startFrom = document.getElementById('sliced-start-from').value;
                const rangeCount = document.getElementById('sliced-range-count').value;
                if (startFrom) {
                    options['X-Start-From'] = startFrom;
                    if (rangeCount) {
                        options['X-Num-Samples'] = rangeCount;
                    }
                }
                break;
        }
    } else if (analysisType === 'hallucination') {
        // 获取分析范围
        const hallucinationMode = document.querySelector('input[name="hallucination-mode"]:checked').value;
        options['X-Analysis-Mode'] = hallucinationMode;

        switch (hallucinationMode) {
            case 'head':
                const numSamples = document.getElementById('hallucination-num-samples').value;
                if (numSamples) {
                    options['X-Num-Samples'] = numSamples;
                }
                break;
            case 'specific':
                const specificRank = document.getElementById('hallucination-specific-rank').value;
                if (specificRank) {
                    options['X-Specific-Rank'] = specificRank;
                }
                break;
            case 'range':
                const startFrom = document.getElementById('hallucination-start-from').value;
                const rangeCount = document.getElementById('hallucination-range-count').value;
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
    } else if (analysisType === 'sliced') {
        const executionMode = analysisOptions['X-Execution-Mode'];
        const mode = analysisOptions['X-Analysis-Mode'];
        
        progressMsg += ` - ${executionMode}模式`;
        
        if (mode === 'head' && analysisOptions['X-Num-Samples']) {
            progressMsg += ` (前${analysisOptions['X-Num-Samples']}条)`;
        } else if (mode === 'specific' && analysisOptions['X-Specific-Rank']) {
            progressMsg += ` (第${analysisOptions['X-Specific-Rank']}条)`;
        } else if (mode === 'range' && analysisOptions['X-Start-From']) {
            const startFrom = analysisOptions['X-Start-From'];
            const count = analysisOptions['X-Num-Samples'] || '到结尾';
            progressMsg += ` (从第${startFrom}条开始，${count}条)`;
        } else {
            progressMsg += ` (所有数据)`;
        }
    } else if (analysisType === 'hallucination') {
        const mode = analysisOptions['X-Analysis-Mode'];
        
        if (mode === 'head' && analysisOptions['X-Num-Samples']) {
            progressMsg += ` (前${analysisOptions['X-Num-Samples']}条)`;
        } else if (mode === 'specific' && analysisOptions['X-Specific-Rank']) {
            progressMsg += ` (第${analysisOptions['X-Specific-Rank']}条)`;
        } else if (mode === 'range' && analysisOptions['X-Start-From']) {
            const startFrom = analysisOptions['X-Start-From'];
            const count = analysisOptions['X-Num-Samples'] || '到结尾';
            progressMsg += ` (从第${startFrom}条开始，${count}条)`;
        } else {
            progressMsg += ` (所有数据)`;
        }
    }
    
    showProgress(progressMsg);
    resultsOutput.textContent = '正在处理文件，请稍候...';

    try {
        // 设置请求头
        const headers = {
            'X-API-Key': apiKey,
            'X-API-Provider': apiProvider,
            ...analysisOptions
        };

        // 添加API高级选项
        if (apiModel) {
            headers['X-API-Model'] = apiModel;
        }
        if (apiBaseUrl) {
            headers['X-API-Base-URL'] = apiBaseUrl;
        }

        // 根据分析类型选择API端点
        let apiEndpoint = '/api/analyze-xlsx';
        if (analysisType === 'hallucination') {
            apiEndpoint = '/api/analyze-internal-consistency';
        }

        const response = await fetch(apiEndpoint, {
            method: 'POST',
            headers: headers,
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }

        const results = await response.json();
        
        // 调试信息：检查响应数据结构
        console.log('API响应数据结构:', results);
        console.log('total_rows:', results.total_rows);
        console.log('total_count:', results.total_count);
        console.log('token_usage:', results.token_usage);
        
        showResults(results);
        
        const totalRows = results.total_rows || results.total_count || 0;
        showProgress(`分析完成！处理了 ${totalRows} 行数据，成功 ${results.success_count} 个，失败 ${results.failed_count} 个`);

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
    
    const totalRows = results.total_rows || results.total_count || 0;
    const successCount = results.success_count || 0;
    const failedCount = results.failed_count || 0;
    
    formattedOutput += `总行数: ${totalRows}\n`;
    formattedOutput += `成功分析: ${successCount}条\n`;
    formattedOutput += `分析失败: ${failedCount}条\n`;
    
    // 计算成功率，确保类型正确
    let successRate = '0';
    if (totalRows > 0 && successCount >= 0) {
        successRate = ((successCount / totalRows) * 100).toFixed(1);
    }
    formattedOutput += `成功率: ${successRate}%\n`;
    
    // 显示token使用信息（如果有的话）
    if (results.token_usage) {
        formattedOutput += `\n=== Token使用统计 ===\n`;
        formattedOutput += `API调用次数: ${results.token_usage.api_call_count}\n`;
        formattedOutput += `输入Token总计: ${results.token_usage.total_input_tokens}\n`;
        formattedOutput += `输出Token总计: ${results.token_usage.total_output_tokens}\n`;
        formattedOutput += `Token总计: ${results.token_usage.total_tokens}\n`;
        if (results.token_usage.avg_total_tokens_per_call > 0) {
            formattedOutput += `平均每次调用Token: ${results.token_usage.avg_total_tokens_per_call.toFixed(1)}\n`;
        }
    }
    
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
                // 显示分析结果 (支持不同分析器格式)
                // 处理引文分析结果
                if (result.citation_analysis && Array.isArray(result.citation_analysis)) {
                    // 使用新的数据结构
                    if (result.analysis_summary) {
                        formattedOutput += `🔍 ${result.analysis_summary}\n`;
                    }
                    
                    if (result.citation_analysis.length > 0) {
                        result.citation_analysis.forEach((item, i) => {
                            const consistency = item.consistency === "一致" ? "✅" : "❌";
                            const citations = item.citation_numbers ? `[${item.citation_numbers.join(',')}]` : "[]";
                            formattedOutput += `  ${i + 1}. ${consistency} ${item.consistency} ${citations}\n`;
                            formattedOutput += `     观点: ${item.topic}\n`;
                            if (item.reason) {
                                formattedOutput += `     分析: ${item.reason}\n`;
                            }
                            formattedOutput += `\n`;
                        });
                    }
                } else if (result.raw_response) {
                    // 兼容旧格式：尝试解析raw_response
                    try {
                        const citationAnalysis = JSON.parse(result.raw_response);
                        if (Array.isArray(citationAnalysis) && citationAnalysis.length > 0) {
                            formattedOutput += `🔍 引文分析结果: 发现${citationAnalysis.length}个带引用标记的句子\n`;
                            citationAnalysis.forEach((item, i) => {
                                const consistency = item.consistency === "一致" ? "✅" : "❌";
                                const citations = item.citation_numbers ? `[${item.citation_numbers.join(',')}]` : "[]";
                                formattedOutput += `  ${i + 1}. ${consistency} ${item.consistency} ${citations}\n`;
                                formattedOutput += `     观点: ${item.topic}\n`;
                                if (item.reason) {
                                    formattedOutput += `     分析: ${item.reason}\n`;
                                }
                                formattedOutput += `\n`;
                            });
                        } else {
                            formattedOutput += `🔍 引文分析: 未发现带引用标记的句子\n`;
                        }
                    } catch (e) {
                        // 如果不是JSON格式，显示原始文本
                        formattedOutput += `🔍 分析结果:\n${result.raw_response}\n`;
                    }
                }
                
                // 备用显示逻辑（兼容旧格式）
                if (result.analysis && !result.raw_response) {
                    if (typeof result.analysis === 'string') {
                        let analysisText = result.analysis;
                        if (analysisText.includes('\\n')) {
                            analysisText = analysisText.replace(/\\n/g, '\n');
                        }
                        formattedOutput += `分析结果:\n${analysisText}\n`;
                    } else if (Array.isArray(result.analysis) && result.analysis.length > 0) {
                        formattedOutput += `分析结果: 发现${result.analysis.length}个引用分析项\n`;
                        result.analysis.forEach((item, i) => {
                            let itemText = item.topic || item.content || JSON.stringify(item);
                            if (itemText.includes('\\n')) {
                                itemText = itemText.replace(/\\n/g, '\n');
                            }
                            formattedOutput += `  ${i + 1}. ${itemText}\n`;
                        });
                    }
                }
                
                // 显示内部一致性检测结果（如果有的话）
                if (result.status) {
                    formattedOutput += `🔍 检测状态: ${result.status}\n`;
                }
                if (result.description) {
                    formattedOutput += `📝 问题描述: ${result.description}\n`;
                }
                if (result.location) {
                    formattedOutput += `📍 具体位置: ${result.location}\n`;
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
    
    // 深度处理JSON中的换行符
    function processJsonForDisplay(obj) {
        if (typeof obj === 'string') {
            return obj.replace(/\\n/g, '\n');
        } else if (Array.isArray(obj)) {
            return obj.map(processJsonForDisplay);
        } else if (obj !== null && typeof obj === 'object') {
            const processed = {};
            for (let key in obj) {
                processed[key] = processJsonForDisplay(obj[key]);
            }
            return processed;
        }
        return obj;
    }
    
    const processedResults = processJsonForDisplay(results);
    let jsonString = JSON.stringify(processedResults, null, 2);
    formattedOutput += jsonString;
    
    resultsOutput.textContent = formattedOutput;
}


// API提供商相关功能

// 更新API Key标签
function updateApiKeyLabel() {
    const labels = {
        'demo': 'API Key (演示专用):',
        'alibaba': '百炼API Key:',
        'openai': 'OpenAI API Key:',
        'deepseek': 'DeepSeek API Key:'
    };
    
    const placeholders = {
        'demo': '演示专用 - 已自动配置',
        'alibaba': '请输入百炼API Key...',
        'openai': '请输入OpenAI API Key...',
        'deepseek': '请输入DeepSeek API Key...'
    };
    
    apiKeyLabel.textContent = labels[apiProvider] || 'API Key:';
    apiKeyInput.placeholder = placeholders[apiProvider] || '请输入API Key...';
}

// 更新默认模型
function updateDefaultModel() {
    // 定义各提供商的默认模型
    const defaultModels = {
        'demo': 'gemini-2.5-pro',
        'alibaba': 'qwen-plus',
        'openai': 'gpt-4o',
        'deepseek': 'deepseek-chat'
    };
    
    // 定义各提供商的模型描述
    const modelDescriptions = {
        'demo': '演示专用模型 - 已自动配置',
        'alibaba': '推荐使用 qwen-plus, qwen-turbo, qwen-max, qwen-long 等',
        'openai': '推荐使用 gpt-4o, gpt-4o-mini, gpt-3.5-turbo 等',
        'deepseek': '推荐使用 deepseek-chat'
    };

    // 获取当前提供商的默认模型
    const defaultModel = defaultModels[apiProvider] || '';
    const description = modelDescriptions[apiProvider] || '请输入模型名称';
    
    // 设置默认模型值
    apiModel = defaultModel;
    modelNameInput.value = defaultModel;
    
    // 更新占位符和帮助文本
    modelNameInput.placeholder = defaultModel || '请输入模型名称...';
    modelHelp.textContent = description;
}

// 更新演示配置
function updateDemoConfiguration() {
    if (apiProvider === 'demo') {
        // 为演示专用配置固定的API Key和URL
        apiKey = 'sk-DE8xhX8sshtGmJennCNAAfvGCKB15QSLjoFilbJwI7PwCRCc';
        apiBaseUrl = 'api.chatanywhere.tech/v1/chat/completions';
        
        // 设置UI状态
        apiKeyInput.value = apiKey;
        apiKeyInput.disabled = true;
        apiBaseUrlInput.value = apiBaseUrl;
        apiBaseUrlInput.disabled = true;
        modelNameInput.disabled = true;
        
        // 更新分析按钮状态
        updateAnalyzeButton();
    } else {
        // 恢复其他提供商的正常状态
        apiKeyInput.disabled = false;
        apiBaseUrlInput.disabled = false;
        modelNameInput.disabled = false;
        
        // 清空演示专用的配置
        if (apiKey === 'sk-DE8xhX8sshtGmJennCNAAfvGCKB15QSLjoFilbJwI7PwCRCc') {
            apiKey = '';
            apiKeyInput.value = '';
        }
        if (apiBaseUrl === 'api.chatanywhere.tech/v1/chat/completions') {
            apiBaseUrl = '';
            apiBaseUrlInput.value = '';
        }
        
        // 更新分析按钮状态
        updateAnalyzeButton();
    }
}

// 切换高级选项显示
function toggleAdvancedOptions(show) {
    const advancedOptions = document.querySelectorAll('.api-advanced-options');
    advancedOptions.forEach(option => {
        if (show) {
            option.style.display = 'flex';
            option.classList.add('visible');
        } else {
            option.style.display = 'none';
            option.classList.remove('visible');
        }
    });
}
