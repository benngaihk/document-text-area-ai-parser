# PDF 表单智能填写系统

基于阿里云视觉识别技术的 PDF 表单自动识别和填写系统。

## 功能特点

- 🤖 **智能识别**：使用阿里云视觉识别自动识别 PDF 表单字段标签
- 📝 **在线填写**：直观的 Web 界面，轻松填写表单
- 📥 **一键导出**：填写完成后直接下载 PDF 文件
- 🎨 **美观界面**：基于 Bootstrap 5 的现代化设计
- 🔄 **实时处理**：快速上传、解析、填写、下载

## 技术栈

### 后端
- **FastAPI**: 现代化的 Python Web 框架
- **阿里云视觉识别**: 智能识别 PDF 表单字段
- **PyMuPDF**: PDF 文件处理
- **PyPDF2**: PDF 表单填写

### 前端
- **Bootstrap 5**: 响应式 UI 框架
- **Vanilla JavaScript**: 原生 JavaScript 实现
- **Bootstrap Icons**: 图标库

## 快速开始

### 1. 安装依赖

```bash
pip3 install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件并添加阿里云 API 密钥：

```bash
DASHSCOPE_API_KEY=your_api_key_here
```

### 3. 启动服务

```bash
python3 main.py
```

服务将在 `http://127.0.0.1:8000` 启动。

### 4. 访问应用

- **Web 界面**: http://127.0.0.1:8000
- **API 文档**: http://127.0.0.1:8000/docs

## 使用流程

### 步骤 1: 上传 PDF
- 点击或拖拽上传 PDF 文件
- 系统自动上传文件到服务器

### 步骤 2: 自动识别
- 系统使用阿里云视觉识别分析 PDF
- 自动提取表单字段和对应的标签
- 在前端展示所有可填写的字段

### 步骤 3: 填写表单
- 在 Web 界面中填写各个字段
- 每个字段会显示识别到的中文标签
- 支持必填字段验证

### 步骤 4: 下载结果
- 点击"生成 PDF"按钮
- 系统自动填写 PDF 表单
- 下载填写完成的 PDF 文件

## 项目结构

```
google-doc-ai/
├── main.py                          # FastAPI 主应用
├── pdf_field_extractor.py           # PDF 字段提取和识别
├── requirements.txt                 # Python 依赖
├── .env                            # 环境变量配置
├── static/                         # 静态文件
│   ├── index.html                  # Web 界面
│   ├── css/
│   │   └── style.css              # 样式文件
│   └── js/
│       └── app.js                 # 前端逻辑
├── uploads/                        # 上传文件临时目录
├── temp/                          # 临时文件目录
└── output/                        # 输出文件目录
```

## API 端点

### 上传 PDF
```
POST /upload-pdf
```
上传 PDF 文件，返回文件 ID

### 解析 PDF
```
POST /parse-pdf-by-id
```
根据文件 ID 解析 PDF 字段（使用阿里云视觉识别）

### 填写 PDF
```
POST /fill-pdf-by-id
```
根据文件 ID 和表单数据填写 PDF

### 下载 PDF
```
GET /download/{file_id}
```
下载填写完成的 PDF 文件

### 清理文件
```
DELETE /cleanup/{file_id}
```
清理临时文件

## 配置说明

### 页码设置
默认处理 PDF 的第 2 页（page_num=1）。如需修改，请编辑 `main.py` 中的：

```python
results = extractor.process(page_num=1, use_vision=True)
```

### 文件过期时间
临时文件默认 2 小时后过期。修改 `main.py` 中的：

```python
temp_manager = TempFileManager(expiry_hours=2)
```

## 注意事项

1. **API 密钥**: 确保已正确配置阿里云 API 密钥
2. **PDF 格式**: 仅支持包含可编辑表单字段的 PDF
3. **文件大小**: 建议单个文件不超过 10MB
4. **浏览器兼容**: 建议使用 Chrome、Firefox、Safari 等现代浏览器

## 故障排除

### 问题：无法识别字段标签
- 检查 `.env` 文件中的 API 密钥是否正确
- 确认阿里云账户有足够的调用额度
- 查看服务器日志获取详细错误信息

### 问题：上传失败
- 确认文件是 PDF 格式
- 检查文件大小是否过大
- 确认 `uploads/` 目录有写入权限

### 问题：下载的 PDF 没有填写内容
- 确认 PDF 包含可编辑的表单字段
- 查看浏览器控制台是否有错误
- 检查服务器日志

## 开发调试

### 查看服务日志
服务运行时会在终端输出日志信息

### API 文档
访问 http://127.0.0.1:8000/docs 查看交互式 API 文档

### 强制关闭加载层
在浏览器控制台执行：
```javascript
forceCloseLoading()
```

## 更新日志

### v2.0.0 (当前版本)
- ✨ 集成阿里云视觉识别
- ✨ 全新的 Web 界面
- ✨ 自动识别字段标签
- ✨ 实时文件处理
- ✨ 完整的 RESTful API

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交 Issue。
