# PDF表单字段提取和识别综合工具使用指南

## 🎯 功能概述

`pdf_field_extractor.py` 是一个综合性的PDF表单字段提取和识别工具，它结合了：

1. **PDF字段坐标提取** - 从PDF中提取表单字段的精确坐标
2. **图片转换和标注** - 将PDF转换为图片并标注字段位置
3. **阿里云视觉识别** - 使用通义千问3-VL-Plus模型识别字段标签

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

需要的依赖：
- PyMuPDF (fitz)
- Pillow (PIL)
- dashscope
- python-dotenv

### 2. 配置环境

在 `.env` 文件中添加阿里云API密钥：

```env
DASHSCOPE_API_KEY=your_api_key_here
```

### 3. 基本使用

```bash
# 完整处理（包括视觉识别）
python pdf_field_extractor.py document.pdf

# 指定输出目录
python pdf_field_extractor.py document.pdf --output result

# 处理指定页码
python pdf_field_extractor.py document.pdf --page 2

# 不使用视觉识别（仅提取坐标和标注图片）
python pdf_field_extractor.py document.pdf --no-vision
```

## 📋 输出文件说明

脚本会生成以下文件：

### 1. 坐标信息文件 (`*_coordinates.json`)

包含所有字段的坐标信息：

```json
{
  "fill_1_P.1": {
    "rect": [85.93, 184.92, 570.98, 235.70],
    "type": "Text",
    "page": 0
  }
}
```

### 2. 原始图片 (`*_page1.png`)

PDF页面转换后的高清图片（200 DPI）

### 3. 标注图片 (`*_page1_annotated.png`)

在原始图片上标注了字段名称和边界框的图片

### 4. 完整数据文件 (`*_complete.json`)

包含坐标和识别标签的完整信息：

```json
{
  "fill_1_P.1": {
    "fieldName": "fill_1_P.1",
    "fieldType": "Text",
    "coordinates": {
      "rect": [85.93, 184.92, 570.98, 235.70],
      "page": 0
    },
    "label": "建议采用的公司名称 Proposed Company Name",
    "recognizedType": "text"
  }
}
```

### 5. 简化格式文件 (`*_fields.json`)

符合用户要求的简化格式，适合直接使用：

```json
[
  {
    "fieldName": "fill_1_P.1",
    "fieldType": "text",
    "text": "建议采用的公司名称 Proposed Company Name"
  },
  {
    "fieldName": "fill_2_P.2",
    "fieldType": "text",
    "text": "建议采用的公司英文名称 Proposed English Company Name"
  }
]
```

## 🔧 工作流程

1. **提取字段坐标** - 从PDF中读取表单字段及其位置信息
2. **PDF转图片** - 将PDF页面转换为高清图片
3. **创建标注图片** - 在图片上标注字段名称和边界框
4. **视觉识别** - 使用阿里云API识别字段标签文字
5. **合并结果** - 将坐标信息和识别结果合并输出

## 📊 命令行参数

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `pdf_path` | - | PDF文件路径（必需） | - |
| `--output` | `-o` | 输出目录 | `result` |
| `--page` | `-p` | 要处理的页码 | `1` |
| `--no-vision` | - | 不使用视觉识别 | False |

## 🎯 使用场景

### 场景1：完整的字段识别

```bash
python pdf_field_extractor.py NNC1_fillable.pdf
```

输出：
- 所有字段的坐标
- 标注图片
- 字段标签识别结果
- 完整的字段映射

### 场景2：仅提取坐标（不需要识别标签）

```bash
python pdf_field_extractor.py document.pdf --no-vision
```

适用于：
- 仅需要字段坐标信息
- 没有配置阿里云API密钥
- 需要快速处理不需要标签识别

### 场景3：处理多页文档

```bash
# 处理第1页
python pdf_field_extractor.py document.pdf --page 1

# 处理第2页
python pdf_field_extractor.py document.pdf --page 2
```

### 场景4：批量处理

```bash
# 批量处理多个PDF
for pdf in *.pdf; do
    python pdf_field_extractor.py "$pdf" --output "output/$(basename $pdf .pdf)"
done
```

## 🔍 与其他工具的关系

### 1. annotate_fields.py

`pdf_field_extractor.py` 包含了 `annotate_fields.py` 的所有功能：
- 提取字段坐标
- 创建标注图片

但提供了更好的封装和命令行接口。

### 2. aliyun_vision_parser.py

`pdf_field_extractor.py` 集成了 `aliyun_vision_parser.py` 的视觉识别功能：
- 自动调用阿里云API
- 自动解析识别结果

但增加了完整的工作流集成。

## ⚙️ 高级用法

### Python API 调用

```python
from pdf_field_extractor import PDFFieldExtractor

# 创建提取器
extractor = PDFFieldExtractor("document.pdf", "output")

# 处理PDF
results = extractor.process(page_num=0, use_vision=True)

# 访问结果
print(f"找到 {results['fields_count']} 个字段")
print(f"完整数据: {results['complete_file']}")
print(f"简化格式: {results['simplified_file']}")
```

### 自定义提示词

修改 `recognize_field_labels` 方法中的 `custom_prompt` 参数来自定义识别提示词。

## ⚠️ 注意事项

1. **API配额** - 注意阿里云API的调用限制和费用
2. **图片质量** - 默认使用200 DPI，可根据需要调整
3. **字段类型** - 支持文本框、复选框等常见表单字段
4. **多页处理** - 每次只处理一页，需要多次调用处理多页
5. **坐标系统** - 使用PDF坐标系统（左上角为原点）

## 🔧 故障排除

### 问题1: ImportError: No module named 'fitz'

**解决**:
```bash
pip install PyMuPDF
```

### 问题2: 未找到字段

**可能原因**:
- PDF不包含交互式表单字段
- 页码选择错误
- PDF是扫描件（纯图片）

**解决**: 检查PDF是否为可填写的表单类型

### 问题3: 视觉识别失败

**可能原因**:
- 未配置API密钥
- 网络连接问题
- API配额不足

**解决**:
- 检查 `.env` 配置
- 验证网络连接
- 检查阿里云账号额度

### 问题4: 标签识别不准确

**解决**:
- 检查标注图片质量
- 调整DPI设置
- 自定义提示词优化识别效果

## 📈 性能优化

- **批量处理**: 使用脚本批量处理多个文件
- **并行处理**: 多个PDF可以并行处理
- **缓存结果**: 避免重复处理相同的PDF
- **关闭视觉识别**: 不需要时使用 `--no-vision` 加快速度

## 🔗 相关资源

- [PyMuPDF 文档](https://pymupdf.readthedocs.io/)
- [阿里云百炼文档](https://help.aliyun.com/zh/dashscope/)
- [通义千问API文档](https://help.aliyun.com/zh/dashscope/developer-reference/api-details)

## 📝 最佳实践

1. **先测试小文件** - 确保配置正确后再处理大批量文件
2. **保存中间结果** - 所有中间文件都会保存，便于调试
3. **检查标注图片** - 通过标注图片验证字段提取是否准确
4. **验证识别结果** - 人工检查识别的标签是否正确
5. **版本控制输出** - 将输出文件纳入版本控制以追踪变化

## 🎉 总结

`pdf_field_extractor.py` 提供了一站式的PDF表单字段提取和识别解决方案，集成了：

- ✅ 精确的坐标提取
- ✅ 直观的图片标注
- ✅ 强大的视觉识别
- ✅ 多种输出格式
- ✅ 灵活的命令行接口

是处理PDF表单的理想工具！
