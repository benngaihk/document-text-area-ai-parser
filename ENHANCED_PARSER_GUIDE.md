# 增强版PDF表单解析器使用指南

## 🎯 功能概述

`enhanced_form_parser.py` 是一个增强版的PDF表单解析器，它结合了：

1. **本地PDF解析** (`final_form_parser.py`) - 快速提取表单字段坐标
2. **Google Document AI** - 识别PDF中的文本内容和标签
3. **智能坐标匹配** - 通过坐标距离找到字段附近的真实标签

## 🚀 核心优势

- **自动标签识别** - 无需手动填写字段含义
- **高精度匹配** - 基于坐标距离的智能匹配算法
- **多种输出格式** - 支持详细JSON、简单表格、映射建议等
- **容错处理** - 即使Document AI不可用也能正常工作

## 📋 使用方法

### 1. 基本用法

```bash
# 增强版解析（JSON格式）
python enhanced_form_parser.py NNC1_fillable.pdf

# 简单表格格式
python enhanced_form_parser.py NNC1_fillable.pdf simple

# 字段标签映射建议
python enhanced_form_parser.py NNC1_fillable.pdf mapping
```

### 2. 输出格式说明

#### Enhanced格式（默认）
完整的JSON输出，包含所有详细信息：
```json
{
  "totalPages": 5,
  "uniqueFields": 12,
  "fields": [
    {
      "fieldName": "applicant_name",
      "fieldType": "text",
      "nearbyLabels": [
        {
          "text": "申请人姓名",
          "type": "paragraph",
          "distance": 0.05,
          "confidence": 0.95
        }
      ],
      "instances": [...]
    }
  ],
  "textElements": [...],
  "documentAIEnabled": true
}
```

#### Simple格式
简洁的表格输出：
```
序号  字段名                   类型        建议标签              置信度
1     applicant_name         text        申请人姓名            0.95
2     application_date       text        申请日期              0.88
```

#### Mapping格式
字段到标签的映射建议：
```
📋 已映射字段:
  applicant_name → 申请人姓名 (置信度: 0.95)
  application_date → 申请日期 (置信度: 0.88)

❓ 未映射字段:
  field_123 (text) - 未找到附近标签

💡 建议:
  • 建议手动检查距离较远的标签匹配
  • 考虑字段的实际用途来验证标签建议
```

## 🔧 工作原理

### 1. 本地PDF解析
- 使用 `pypdf` 提取表单字段的坐标信息
- 获取字段名称、类型、位置等基本信息

### 2. Document AI文本识别
- 调用Google Document AI API识别PDF中的所有文本
- 提取段落、表格、表单字段等文本元素
- 获取每个文本元素的边界框坐标

### 3. 智能坐标匹配
- 计算表单字段与附近文本的距离
- 选择距离最近的文本作为字段标签
- 支持多种文本类型（段落、表格单元格、表单字段等）

### 4. 结果增强
- 为每个字段添加建议的标签
- 提供置信度评分
- 生成映射建议

## ⚙️ 配置要求

### 必需配置（用于Document AI）
在 `.env` 文件中配置：
```env
PROJECT_ID=your-project-id
LOCATION=us
PROCESSOR_ID=your-processor-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

### 可选配置
- 搜索半径：默认0.1（归一化坐标）
- 最大标签数：默认5个
- 置信度阈值：默认0.5

## 📊 输出示例

### 字段信息增强
```json
{
  "fieldName": "applicant_name",
  "fieldType": "text",
  "nearbyLabels": [
    {
      "text": "申请人姓名",
      "type": "paragraph",
      "distance": 0.05,
      "confidence": 0.95,
      "boundingBox": {"x1": 0.1, "y1": 0.2, "x2": 0.3, "y2": 0.25}
    },
    {
      "text": "Name of Applicant",
      "type": "paragraph", 
      "distance": 0.08,
      "confidence": 0.90,
      "boundingBox": {"x1": 0.1, "y1": 0.15, "x2": 0.4, "y2": 0.18}
    }
  ],
  "instances": [
    {
      "pageNumber": 1,
      "value": "",
      "rect": {"x1": 100, "y1": 200, "x2": 300, "y2": 220},
      "normalizedRect": {"x1": 0.16, "y1": 0.75, "x2": 0.49, "y2": 0.72},
      "nearbyLabels": [...]
    }
  ]
}
```

## 🎯 应用场景

1. **自动化表单处理** - 自动识别表单字段含义
2. **多语言文档** - 支持中英文混合文档
3. **批量文档处理** - 处理大量相似格式的PDF
4. **数据提取** - 从表单中提取结构化数据
5. **文档分析** - 分析表单结构和字段关系

## 🔍 技术细节

### 坐标系统
- 使用归一化坐标（0-1范围）
- Y轴翻转处理（PDF坐标与屏幕坐标的差异）
- 支持多页面文档

### 距离计算
- 基于矩形中心点的欧几里得距离
- 可配置搜索半径
- 支持不同页面间的匹配

### 文本提取
- 支持段落、表格、表单字段等多种文本类型
- 保留文本的置信度信息
- 处理多语言文本

## 🚨 注意事项

1. **Document AI配额** - 注意API调用次数限制
2. **坐标精度** - 复杂布局可能需要调整搜索半径
3. **文本质量** - 扫描质量差的PDF可能影响识别效果
4. **多语言支持** - 确保Document AI支持目标语言

## 🔧 故障排除

### 常见问题

1. **Document AI未启用**
   - 检查 `.env` 文件配置
   - 验证服务账号权限
   - 确认API已启用

2. **标签匹配不准确**
   - 调整搜索半径参数
   - 检查PDF布局复杂度
   - 手动验证匹配结果

3. **性能问题**
   - 大文件可能需要较长处理时间
   - 考虑分批处理
   - 优化Document AI配置

## 📈 扩展功能

可以进一步扩展的功能：
- 支持更多文档格式（Word、Excel等）
- 添加机器学习模型提高匹配精度
- 支持自定义标签规则
- 集成OCR功能处理扫描文档
- 添加批量处理功能
