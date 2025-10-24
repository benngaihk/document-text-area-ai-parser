// 全局变量
let currentFileId = null;
let currentFields = [];
let currentPage = 1;
let totalPages = 1;
let allPagesData = {};  // 存储所有页面的表单数据

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

// 初始化应用
function initializeApp() {
    // 绑定事件监听器
    bindEventListeners();

    // 重置到初始状态
    resetForm();
}

// 绑定事件监听器
function bindEventListeners() {
    const fileInput = document.getElementById('fileInput');
    const uploadArea = document.getElementById('uploadArea');
    const submitForm = document.getElementById('submitForm');
    const downloadBtn = document.getElementById('downloadBtn');
    const prevPageBtn = document.getElementById('prevPageBtn');
    const nextPageBtn = document.getElementById('nextPageBtn');

    // 文件输入变化事件
    fileInput.addEventListener('change', handleFileSelect);

    // 拖拽上传事件
    uploadArea.addEventListener('click', () => fileInput.click());
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleDrop);

    // 表单提交事件
    submitForm.addEventListener('click', handleFormSubmit);

    // 下载按钮事件
    downloadBtn.addEventListener('click', handleDownload);

    // 翻页按钮事件
    prevPageBtn.addEventListener('click', handlePrevPage);
    nextPageBtn.addEventListener('click', handleNextPage);
}

// 处理文件选择
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        uploadFile(file);
    }
}

// 处理拖拽悬停
function handleDragOver(event) {
    event.preventDefault();
    event.currentTarget.classList.add('dragover');
}

// 处理拖拽离开
function handleDragLeave(event) {
    event.currentTarget.classList.remove('dragover');
}

// 处理文件拖拽放置
function handleDrop(event) {
    event.preventDefault();
    event.currentTarget.classList.remove('dragover');

    const files = event.dataTransfer.files;
    if (files.length > 0) {
        uploadFile(files[0]);
    }
}

// 上传文件
async function uploadFile(file) {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
        showError('请选择PDF文件');
        return;
    }

    try {
        // 显示上传进度
        showUploadProgress();

        // 创建FormData
        const formData = new FormData();
        formData.append('file', file);

        // 上传文件
        showLoading('正在上传文件...');
        const uploadResponse = await fetch('/upload-pdf', {
            method: 'POST',
            body: formData
        });

        if (!uploadResponse.ok) {
            const errorData = await uploadResponse.json();
            throw new Error(errorData.detail || '上传失败');
        }

        const uploadResult = await uploadResponse.json();
        currentFileId = uploadResult.file_id;

        // 解析PDF字段（使用阿里云视觉识别）
        showLoading('正在使用阿里云视觉识别解析PDF字段...');
        const parseResponse = await fetch('/parse-pdf-by-id', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ file_id: currentFileId })
        });

        if (!parseResponse.ok) {
            const errorData = await parseResponse.json();
            throw new Error(errorData.detail || '解析失败');
        }

        const parseResult = await parseResponse.json();
        currentFields = parseResult.fields;
        currentPage = parseResult.current_page || 1;
        totalPages = parseResult.total_pages || 1;

        console.log('解析结果:', parseResult);
        console.log('字段数量:', currentFields.length);
        console.log('当前页:', currentPage, '总页数:', totalPages);

        hideLoading();
        hideUploadProgress();

        // 检查是否有表单字段
        if (currentFields.length === 0) {
            console.log('没有字段，显示无字段页面');
            showNoFieldsSection();
            updateStepStatus(2, 'completed');
        } else {
            console.log('有字段，显示表单页面');
            showFormSection();
            updatePageIndicator();
            updatePaginationButtons();
            generateFormFields();
            updateStepStatus(1, 'completed');
            updateStepStatus(2, 'active');
        }

    } catch (error) {
        hideLoading();
        hideUploadProgress();
        showError(error.message);
        console.error('上传错误:', error);
    }
}

// 显示上传进度
function showUploadProgress() {
    const progressDiv = document.getElementById('uploadProgress');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');

    progressDiv.classList.remove('d-none');

    // 模拟进度更新
    let progress = 0;
    const interval = setInterval(() => {
        progress += Math.random() * 30;
        if (progress > 90) {
            progress = 90;
            clearInterval(interval);
        }

        progressBar.style.width = progress + '%';
        progressText.textContent = Math.round(progress) + '%';
    }, 200);
}

// 隐藏上传进度
function hideUploadProgress() {
    const progressDiv = document.getElementById('uploadProgress');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');

    // 完成进度动画
    progressBar.style.width = '100%';
    progressText.textContent = '100%';

    setTimeout(() => {
        progressDiv.classList.add('d-none');
        progressBar.style.width = '0%';
        progressText.textContent = '0%';
    }, 1000);
}

// 生成表单字段
function generateFormFields() {
    const container = document.getElementById('fieldsContainer');
    container.innerHTML = '';

    currentFields.forEach((field, index) => {
        const fieldDiv = document.createElement('div');
        fieldDiv.className = 'field-group fade-in';

        // 字段类型图标
        const typeIcon = getFieldTypeIcon(field.type);
        const requiredIndicator = field.required ? '<span class="field-required">*</span>' : '';

        // 显示字段标签（从阿里云视觉识别中获取）
        const labelText = field.label ? `<span class="field-label-text">(${field.label})</span>` : '';

        fieldDiv.innerHTML = `
            <div class="field-label">
                <i class="${typeIcon}"></i>
                ${field.name}
                ${labelText}
                ${requiredIndicator}
                <span class="field-type">${field.type}</span>
            </div>
            <input type="text"
                   class="form-control"
                   id="field_${index}"
                   name="${field.name}"
                   placeholder="请输入${field.label || field.name}"
                   ${field.required ? 'required' : ''}>
        `;

        container.appendChild(fieldDiv);
    });
}

// 获取字段类型图标
function getFieldTypeIcon(type) {
    const iconMap = {
        'text': 'bi bi-input-cursor-text',
        'button': 'bi bi-square',
        'choice': 'bi bi-list-check',
        'signature': 'bi bi-pen',
        'listbox': 'bi bi-list',
        'combobox': 'bi bi-menu-button-wide'
    };
    return iconMap[type] || 'bi bi-question-circle';
}

// 处理表单提交
async function handleFormSubmit() {
    if (!currentFileId) {
        showError('请先上传PDF文件');
        return;
    }

    try {
        // 保存当前页的数据
        saveCurrentPageData();

        // 合并所有页面的数据
        const formData = {};
        for (let page in allPagesData) {
            Object.assign(formData, allPagesData[page]);
        }

        console.log('提交所有页面的数据:', formData);

        // 提交数据
        showLoading('正在生成PDF...');
        const fillResponse = await fetch('/fill-pdf-by-id', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                file_id: currentFileId,
                field_data: formData
            })
        });

        if (!fillResponse.ok) {
            const errorData = await fillResponse.json();
            throw new Error(errorData.detail || '填写失败');
        }

        const fillResult = await fillResponse.json();

        hideLoading();

        // 显示结果页面
        showResultSection();
        updateStepStatus(2, 'completed');
        updateStepStatus(3, 'active');

    } catch (error) {
        hideLoading();
        showError(error.message);
        console.error('提交错误:', error);
    }
}

// 收集表单数据
function collectFormData() {
    const formData = {};

    currentFields.forEach((field, index) => {
        const input = document.getElementById(`field_${index}`);
        if (input && input.value.trim()) {
            formData[field.name] = input.value.trim();
        }
    });

    return formData;
}

// 验证必填字段
function validateRequiredFields(formData) {
    for (let field of currentFields) {
        if (field.required && (!formData[field.name] || formData[field.name].trim() === '')) {
            return false;
        }
    }
    return true;
}

// 处理下载
async function handleDownload() {
    if (!currentFileId) {
        showError('没有可下载的文件');
        return;
    }

    try {
        showLoading('正在准备下载...');

        const response = await fetch(`/download/${currentFileId}`);

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '下载失败');
        }

        // 获取文件名
        const contentDisposition = response.headers.get('content-disposition');
        let filename = 'filled_document.pdf';
        if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
            if (filenameMatch) {
                filename = filenameMatch[1];
            }
        }

        // 创建下载链接
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

        hideLoading();

        // 清理文件
        setTimeout(() => {
            cleanupFile();
        }, 2000);

    } catch (error) {
        hideLoading();
        showError(error.message);
        console.error('下载错误:', error);
    }
}

// 清理文件
async function cleanupFile() {
    if (!currentFileId) return;

    try {
        await fetch(`/cleanup/${currentFileId}`, {
            method: 'DELETE'
        });
    } catch (error) {
        console.warn('清理文件失败:', error);
    }
}

// 显示/隐藏页面部分
function showFormSection() {
    hideAllSections();
    document.getElementById('formSection').classList.remove('d-none');
    document.getElementById('formSection').classList.add('fade-in');
}

function showResultSection() {
    hideAllSections();
    document.getElementById('resultSection').classList.remove('d-none');
    document.getElementById('resultSection').classList.add('fade-in');
}

function showNoFieldsSection() {
    hideAllSections();
    document.getElementById('noFieldsSection').classList.remove('d-none');
    document.getElementById('noFieldsSection').classList.add('fade-in');
}

function showUploadSection() {
    hideAllSections();
    document.getElementById('uploadSection').classList.remove('d-none');
    document.getElementById('uploadSection').classList.add('fade-in');
}

function hideAllSections() {
    const sections = ['formSection', 'resultSection', 'noFieldsSection'];
    sections.forEach(sectionId => {
        const section = document.getElementById(sectionId);
        section.classList.add('d-none');
        section.classList.remove('fade-in');
    });
    hideError();
}

// 更新步骤状态
function updateStepStatus(stepNumber, status) {
    const step = document.getElementById(`step${stepNumber}`);
    step.className = `step ${status}`;
}

// 重置表单
function resetForm() {
    currentFileId = null;
    currentFields = [];
    currentPage = 1;
    totalPages = 1;
    allPagesData = {};

    // 重置文件输入
    document.getElementById('fileInput').value = '';

    // 重置步骤状态
    updateStepStatus(1, 'active');
    updateStepStatus(2, '');
    updateStepStatus(3, '');

    // 显示上传部分
    showUploadSection();

    // 清理临时文件
    if (currentFileId) {
        cleanupFile();
    }
}

// 显示错误
function showError(message) {
    const errorAlert = document.getElementById('errorAlert');
    const errorMessage = document.getElementById('errorMessage');

    errorMessage.textContent = message;
    errorAlert.classList.remove('d-none');

    // 自动隐藏错误提示
    setTimeout(() => {
        hideError();
    }, 5000);
}

// 隐藏错误
function hideError() {
    const errorAlert = document.getElementById('errorAlert');
    errorAlert.classList.add('d-none');
}

// 显示加载状态
function showLoading(text = '正在处理...') {
    console.log('显示加载状态:', text);
    const loadingText = document.getElementById('loadingText');
    const loadingOverlay = document.getElementById('loadingOverlay');

    if (loadingText) {
        loadingText.textContent = text;
    }

    if (loadingOverlay) {
        loadingOverlay.classList.remove('d-none');
    }
}

// 隐藏加载状态
function hideLoading() {
    console.log('隐藏加载状态');
    const loadingOverlay = document.getElementById('loadingOverlay');

    if (loadingOverlay) {
        loadingOverlay.classList.add('d-none');
    }

    console.log('加载状态已隐藏');
}

// 工具函数：防抖
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 强制关闭加载覆盖层的紧急函数
function forceCloseLoading() {
    console.log('强制关闭加载覆盖层');

    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
        loadingOverlay.classList.add('d-none');
        loadingOverlay.style.display = 'none !important';
    }

    // 清理可能残留的Bootstrap模态框
    const backdrops = document.querySelectorAll('.modal-backdrop');
    backdrops.forEach(backdrop => backdrop.remove());

    document.body.classList.remove('modal-open');
    document.body.style.paddingRight = '';
    document.body.style.overflow = '';

    console.log('加载覆盖层已强制关闭');
}

// 将函数暴露到全局作用域，方便调试
window.forceCloseLoading = forceCloseLoading;

// 翻页相关函数

// 处理上一页
async function handlePrevPage() {
    if (currentPage <= 1) return;

    // 保存当前页的数据
    saveCurrentPageData();

    // 加载上一页
    await loadPage(currentPage - 1);
}

// 处理下一页
async function handleNextPage() {
    if (currentPage >= totalPages) return;

    // 保存当前页的数据
    saveCurrentPageData();

    // 加载下一页
    await loadPage(currentPage + 1);
}

// 保存当前页的表单数据
function saveCurrentPageData() {
    const pageData = {};

    currentFields.forEach((field, index) => {
        const input = document.getElementById(`field_${index}`);
        if (input && input.value.trim()) {
            pageData[field.name] = input.value.trim();
        }
    });

    allPagesData[currentPage] = pageData;
    console.log(`保存第 ${currentPage} 页数据:`, pageData);
}

// 加载指定页面
async function loadPage(pageNum) {
    if (!currentFileId) return;

    try {
        showLoading(`正在加载第 ${pageNum} 页...`);

        const parseResponse = await fetch('/parse-pdf-by-id', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                file_id: currentFileId,
                page_num: pageNum
            })
        });

        if (!parseResponse.ok) {
            const errorData = await parseResponse.json();
            throw new Error(errorData.detail || '解析失败');
        }

        const parseResult = await parseResponse.json();
        currentFields = parseResult.fields;
        currentPage = parseResult.current_page || pageNum;
        totalPages = parseResult.total_pages || totalPages;

        console.log(`加载第 ${currentPage} 页，共 ${totalPages} 页`);
        console.log('字段数量:', currentFields.length);

        hideLoading();

        // 更新UI
        updatePageIndicator();
        updatePaginationButtons();
        generateFormFields();

        // 恢复该页之前填写的数据
        restorePageData(currentPage);

    } catch (error) {
        hideLoading();
        showError(error.message);
        console.error('加载页面错误:', error);
    }
}

// 恢复页面数据
function restorePageData(pageNum) {
    if (!allPagesData[pageNum]) return;

    const pageData = allPagesData[pageNum];
    console.log(`恢复第 ${pageNum} 页数据:`, pageData);

    currentFields.forEach((field, index) => {
        const input = document.getElementById(`field_${index}`);
        if (input && pageData[field.name]) {
            input.value = pageData[field.name];
        }
    });
}

// 更新页面指示器
function updatePageIndicator() {
    const indicator = document.getElementById('pageIndicator');
    if (indicator) {
        indicator.textContent = `第 ${currentPage} 页，共 ${totalPages} 页`;
    }
}

// 更新翻页按钮状态
function updatePaginationButtons() {
    const prevBtn = document.getElementById('prevPageBtn');
    const nextBtn = document.getElementById('nextPageBtn');

    if (prevBtn) {
        prevBtn.disabled = currentPage <= 1;
    }

    if (nextBtn) {
        nextBtn.disabled = currentPage >= totalPages;
    }

    // 如果只有一页，隐藏翻页控件
    const paginationControls = document.getElementById('paginationControls');
    if (paginationControls) {
        if (totalPages <= 1) {
            paginationControls.classList.add('d-none');
        } else {
            paginationControls.classList.remove('d-none');
        }
    }
}
