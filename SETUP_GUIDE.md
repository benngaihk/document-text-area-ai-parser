# Google Document AI 设置指南

本指南将帮助你获取所需的配置参数：PROJECT_ID、LOCATION 和 PROCESSOR_ID。

## 前置条件

- Google Cloud Platform (GCP) 账号
- 已开通计费（Document AI 需要启用计费，但有免费额度）

## 步骤 1: 创建或选择 GCP 项目

### 1.1 访问 Google Cloud Console
打开浏览器访问：https://console.cloud.google.com/

### 1.2 创建新项目（或选择现有项目）
1. 点击顶部导航栏的项目下拉菜单
2. 点击 "新建项目"
3. 输入项目名称（如 "document-ai-parser"）
4. 点击 "创建"
5. **记录 PROJECT_ID**（在项目信息中显示，如 `my-project-123456`）

## 步骤 2: 启用 Document AI API

### 2.1 启用 API
1. 在 Google Cloud Console 中，确保选择了正确的项目
2. 在左侧菜单中选择 "API 和服务" → "库"
3. 搜索 "Document AI API"
4. 点击 "Cloud Document AI API"
5. 点击 "启用" 按钮

### 2.2 启用计费
1. 在左侧菜单中选择 "结算"
2. 如果没有设置计费账号，点击 "关联结算账号"
3. 按照提示完成设置（需要信用卡，但有免费额度）

**免费额度：** 每月前 1,000 页免费

## 步骤 3: 创建 Document AI 处理器（获取 PROCESSOR_ID）

### 3.1 访问 Document AI 控制台
1. 在 Google Cloud Console 左侧菜单中搜索 "Document AI"
2. 或直接访问：https://console.cloud.google.com/ai/document-ai/processors
3. 首次使用可能需要同意服务条款

### 3.2 创建处理器
1. 点击 "创建处理器" 或 "CREATE PROCESSOR" 按钮
2. 选择处理器类型：

   **常用处理器类型：**
   - **Form Parser** - 通用表单解析（推荐初学者使用）
   - **Invoice Parser** - 发票专用解析器
   - **Receipt Parser** - 收据解析器
   - **Contract Document AI** - 合同解析
   - **Procurement Document AI** - 采购文档解析
   - **Lending Document AI** - 贷款文档解析

3. 输入处理器名称（如 "my-form-parser"）
4. 选择区域（LOCATION）：
   - **us** - 美国（推荐，功能最全）
   - **eu** - 欧洲
   - **asia-northeast1** - 日本东京

5. 点击 "创建"

### 3.3 获取 PROCESSOR_ID

创建成功后，你会看到处理器列表页面：

1. 点击你刚创建的处理器名称
2. 在处理器详情页面，你会看到类似这样的信息：

   ```
   处理器名称: my-form-parser
   处理器 ID: 1234567890abcdef  ← 这就是 PROCESSOR_ID
   类型: FORM_PARSER_PROCESSOR
   位置: us
   ```

3. **复制 PROCESSOR_ID**（纯数字或字母数字组合）

**或者从 URL 中获取：**
处理器详情页的 URL 格式为：
```
https://console.cloud.google.com/ai/document-ai/processors/locations/us/processors/1234567890abcdef
```
其中 `1234567890abcdef` 就是你的 PROCESSOR_ID

## 步骤 4: 创建服务账号密钥

### 4.1 创建服务账号
1. 在 Google Cloud Console 左侧菜单，选择 "IAM 和管理" → "服务账号"
2. 点击 "创建服务账号"
3. 输入名称（如 "document-ai-service"）
4. 点击 "创建并继续"

### 4.2 授予权限
1. 在 "授予此服务账号对项目的访问权限" 部分
2. 选择角色：**Document AI API User**
3. 点击 "继续"
4. 点击 "完成"

### 4.3 创建密钥
1. 在服务账号列表中，找到刚创建的服务账号
2. 点击服务账号的邮箱地址
3. 切换到 "密钥" 标签
4. 点击 "添加密钥" → "创建新密钥"
5. 选择 "JSON" 格式
6. 点击 "创建"
7. JSON 密钥文件会自动下载到你的电脑

**重要：** 妥善保管这个 JSON 文件，不要提交到 Git 仓库！

### 4.4 保存密钥文件
1. 将下载的 JSON 文件移动到安全位置，如：
   ```
   /Users/admin/.gcp/document-ai-key.json
   ```
2. 记录文件的完整路径

## 步骤 5: 配置 .env 文件

现在你已经获取了所有需要的信息，编辑项目中的 `.env` 文件：

```bash
# 复制模板
cp .env.example .env

# 编辑 .env
nano .env
```

填入你获取的信息：

```env
# 步骤 1 获取
PROJECT_ID=my-project-123456

# 步骤 3.2 选择的区域
LOCATION=us

# 步骤 3.3 获取
PROCESSOR_ID=1234567890abcdef

# 步骤 4.4 保存的文件路径
GOOGLE_APPLICATION_CREDENTIALS=/Users/admin/.gcp/document-ai-key.json
```

## 步骤 6: 验证配置

### 6.1 测试连接

创建一个简单的测试脚本 `test_connection.py`：

```python
import os
from dotenv import load_dotenv
from google.cloud import documentai_v1 as documentai
from google.api_core.client_options import ClientOptions

# 加载环境变量
load_dotenv()

project_id = os.getenv("PROJECT_ID")
location = os.getenv("LOCATION")
processor_id = os.getenv("PROCESSOR_ID")

print(f"项目 ID: {project_id}")
print(f"位置: {location}")
print(f"处理器 ID: {processor_id}")

# 测试连接
try:
    opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
    client = documentai.DocumentProcessorServiceClient(client_options=opts)

    processor_name = client.processor_path(project_id, location, processor_id)
    print(f"\n✓ 连接成功！")
    print(f"处理器完整路径: {processor_name}")
except Exception as e:
    print(f"\n✗ 连接失败: {e}")
```

运行测试：
```bash
python test_connection.py
```

如果看到 "✓ 连接成功！"，说明配置正确！

## 常见问题

### Q1: 找不到 Document AI 菜单？
**A:** 确保你已经启用了 Document AI API（步骤 2）。刷新页面或重新登录。

### Q2: 创建处理器时提示需要启用计费？
**A:** Document AI 需要启用计费账号，即使你使用免费额度也需要绑定信用卡。

### Q3: PROCESSOR_ID 看起来很长？
**A:** PROCESSOR_ID 通常是 16 位的字母数字组合，如 `a1b2c3d4e5f6g7h8`。如果你复制了完整的资源路径，只需要最后一段。

**错误示例：**
```
projects/123/locations/us/processors/a1b2c3d4e5f6g7h8  ← 这是完整路径
```

**正确的 PROCESSOR_ID：**
```
a1b2c3d4e5f6g7h8  ← 只需要这部分
```

### Q4: 认证错误 "Could not automatically determine credentials"？
**A:** 检查：
1. `GOOGLE_APPLICATION_CREDENTIALS` 路径是否正确
2. JSON 密钥文件是否存在
3. 服务账号是否有正确的权限

### Q5: 选择哪个处理器类型？
**A:**
- 不确定用途 → **Form Parser**（通用表单解析）
- 处理发票 → **Invoice Parser**
- 处理收据 → **Receipt Parser**
- 自定义文档 → 可以训练 **Custom Extractor**

### Q6: 区域 (LOCATION) 选择哪个？
**A:**
- 推荐使用 **us**（美国），功能最全，处理器类型最多
- 如果有数据合规要求，选择 **eu**（欧洲）
- 中国大陆用户可能访问速度较慢，建议使用 VPN 或选择 **asia-northeast1**

## 成本估算

Document AI 定价（截至 2024 年）：

| 处理器类型 | 免费额度 | 超出后价格 |
|-----------|---------|-----------|
| Form Parser | 1,000 页/月 | $1.50/1000页 |
| Invoice Parser | 1,000 页/月 | $1.50/1000页 |
| Specialized Parsers | 1,000 页/月 | $10-65/1000页 |

**示例：**
- 处理 500 页文档/月 → **免费**
- 处理 5,000 页文档/月 → (5000-1000) × $1.50/1000 = **$6**

详细定价：https://cloud.google.com/document-ai/pricing

## 下一步

配置完成后，你可以：

1. 运行示例程序：
   ```bash
   python document_parser.py your_test.pdf
   ```

2. 查看示例代码：
   ```bash
   python example.py
   ```

3. 阅读 API 文档：
   - [Document AI 官方文档](https://cloud.google.com/document-ai/docs)
   - [Python 客户端库参考](https://cloud.google.com/python/docs/reference/documentai/latest)

## 获取帮助

- [Document AI 讨论区](https://groups.google.com/g/cloud-document-ai-discuss)
- [Stack Overflow](https://stackoverflow.com/questions/tagged/google-cloud-document-ai)
- [Google Cloud 支持](https://cloud.google.com/support)
