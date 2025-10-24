# 阿里云百炼API配置指南

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置API密钥

在 `.env` 文件中添加你的阿里云API密钥：

```env
# 阿里云百炼API密钥
DASHSCOPE_API_KEY=your_api_key_here
```

### 3. 获取API密钥

1. 访问阿里云百炼平台：https://dashscope.aliyun.com/
2. 登录你的阿里云账号
3. 进入控制台
4. 创建API-KEY并复制

### 4. 运行脚本

基本用法：
```bash
python aliyun_vision_parser.py /path/to/image.png
```

保存结果到文件：
```bash
python aliyun_vision_parser.py /path/to/image.png output.json
```

示例：
```bash
python aliyun_vision_parser.py result/NNC1_page1_annotated.png result/fields_output.json
```

## 📋 输出格式

脚本会输出如下JSON格式：

```json
[
  {
    "fieldName": "fill_1_P.1",
    "fieldType": "text",
    "text": "申请人姓名"
  },
  {
    "fieldName": "fill_2_P.2",
    "fieldType": "text",
    "text": "申请日期"
  }
]
```

其中：
- `fieldName`: 字段标识符
- `fieldType`: 字段类型（text, checkbox, date等）
- `text`: 字段旁边的标签文字（由视觉模型推理得出）

## 🔧 模型信息

- **模型名称**: 通义千问3-VL-Plus (qwen-vl-plus-latest)
- **功能**: 视觉理解和图像分析
- **支持格式**: PNG, JPG, JPEG等常见图片格式

## 📊 使用示例

```python
from aliyun_vision_parser import AliyunVisionParser

# 创建解析器
parser = AliyunVisionParser()

# 解析表单字段
result = parser.parse_form_fields("image.png")

if result["success"]:
    fields = result["fields"]
    for field in fields:
        print(f"{field['fieldName']}: {field['text']}")
else:
    print(f"错误: {result['error']}")
```

## 🎯 提示词自定义

你可以自定义提示词来优化识别效果：

```python
custom_prompt = """
请识别这张表单中的所有字段，并提供：
1. 字段名称
2. 字段类型
3. 字段标签

以JSON格式输出...
"""

result = parser.parse_form_fields("image.png", prompt=custom_prompt)
```

## ⚠️ 注意事项

1. **API配额**: 注意阿里云百炼的API调用次数和流量限制
2. **图片质量**: 确保图片清晰，分辨率适中
3. **文件大小**: 建议图片大小不超过10MB
4. **支持语言**: 支持中文、英文等多语言表单

## 🔍 故障排除

### 问题1: ImportError: No module named 'dashscope'
**解决**: 运行 `pip install dashscope`

### 问题2: 未设置 DASHSCOPE_API_KEY
**解决**: 在 `.env` 文件中添加你的API密钥

### 问题3: API调用失败
**解决**:
- 检查API密钥是否正确
- 检查网络连接
- 确认账号是否有足够的调用额度

## 📈 进阶用法

### 批量处理
```bash
# 处理多个图片
for img in result/*.png; do
    python aliyun_vision_parser.py "$img" "output/$(basename $img .png).json"
done
```

### 与现有工具集成
可以将阿里云百炼API与现有的PDF解析工具结合使用，实现更强大的文档处理能力。

## 🔗 相关资源

- [阿里云百炼官方文档](https://help.aliyun.com/zh/dashscope/)
- [通义千问API文档](https://help.aliyun.com/zh/dashscope/developer-reference/api-details)
- [Python SDK文档](https://help.aliyun.com/zh/dashscope/developer-reference/quick-start)
