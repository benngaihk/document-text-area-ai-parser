#!/usr/bin/env python3
"""
阿里云百炼API调用脚本
使用通义千问3-VL-Plus模型识别表单字段
"""

import os
import sys
import json
import base64
from typing import Dict, Any
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

try:
    from dashscope import MultiModalConversation
    import dashscope
except ImportError:
    print("错误：需要安装 dashscope 库")
    print("请运行：pip install dashscope")
    sys.exit(1)


class AliyunVisionParser:
    """阿里云通义千问VL-Plus模型解析器"""

    def __init__(self, api_key: str = None):
        """
        初始化解析器

        Args:
            api_key: 阿里云API Key，如果为None则从环境变量DASHSCOPE_API_KEY读取
        """
        self.api_key = api_key or os.getenv('DASHSCOPE_API_KEY')
        if not self.api_key:
            raise ValueError("请设置 DASHSCOPE_API_KEY 环境变量或传入 api_key 参数")

        dashscope.api_key = self.api_key
        self.model = "qwen-vl-plus-latest"  # 通义千问3-VL-Plus模型

    def encode_image(self, image_path: str) -> str:
        """
        将图片编码为base64

        Args:
            image_path: 图片文件路径

        Returns:
            base64编码的图片字符串
        """
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')

    def parse_form_fields(self, image_path: str, prompt: str = None) -> Dict[str, Any]:
        """
        解析表单字段

        Args:
            image_path: 图片文件路径
            prompt: 自定义提示词，如果为None则使用默认提示词

        Returns:
            包含字段信息的字典
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")

        # 默认提示词
        if prompt is None:
            prompt = """请仔细分析这张表单图片。图片中用红色边框标注了表单字段，在每个红色边框的左上角有黄色背景的字段名称标签。

你的任务是：
1. 找到每个红色边框标注的字段
2. 读取该字段左上角黄色背景中的字段名称（例如：fill_1_P.1、fill_2_P.2 等）
3. 识别该字段附近的标签文字（通常在字段左侧或上方，用于说明该字段需要填写什么内容）
4. 判断字段类型（text、checkbox、date 等）

请以JSON数组格式输出，每个字段一个JSON对象。格式如下：
[
{
    "fieldName": "fill_1_P.1",
    "fieldType": "text",
    "text": "字段标签文字"
}
]

重要要求：
- fieldName 必须与图片中红色框左上角黄色背景标注的名称完全一致（包括大小写和点号）
- text 是字段附近的说明文字，不是黄色背景中的字段名
- 按照从上到下、从左到右的顺序识别所有字段
- 如果字段旁边没有明显的标签文字，text 可以为空字符串
- 只输出JSON数组，不要包含任何其他文字说明"""

        # 构建消息
        messages = [
            {
                "role": "user",
                "content": [
                    {"text": prompt},
                    {"image": f"file://{os.path.abspath(image_path)}"}
                ]
            }
        ]

        # 调用API
        try:
            response = MultiModalConversation.call(
                model=self.model,
                messages=messages
            )

            if response.status_code == 200:
                # 提取响应内容
                result_text = response.output.choices[0].message.content[0]["text"]

                # 尝试解析JSON
                try:
                    # 清理响应文本，提取JSON部分
                    result_text = result_text.strip()

                    # 如果响应包含markdown代码块，提取JSON部分
                    if "```json" in result_text:
                        start = result_text.find("```json") + 7
                        end = result_text.find("```", start)
                        result_text = result_text[start:end].strip()
                    elif "```" in result_text:
                        start = result_text.find("```") + 3
                        end = result_text.find("```", start)
                        result_text = result_text[start:end].strip()

                    # 解析JSON
                    fields = json.loads(result_text)

                    return {
                        "success": True,
                        "fields": fields,
                        "raw_response": response.output.choices[0].message.content[0]["text"]
                    }
                except json.JSONDecodeError as e:
                    return {
                        "success": False,
                        "error": f"JSON解析失败: {str(e)}",
                        "raw_response": result_text
                    }
            else:
                return {
                    "success": False,
                    "error": f"API调用失败: {response.message}",
                    "status_code": response.status_code
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"API调用异常: {str(e)}"
            }


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python aliyun_vision_parser.py <图片路径> [输出文件路径]")
        print("\n示例:")
        print("  python aliyun_vision_parser.py image.png")
        print("  python aliyun_vision_parser.py image.png output.json")
        sys.exit(1)

    image_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    # 检查环境变量
    api_key = os.getenv('DASHSCOPE_API_KEY')
    if not api_key:
        print("\n错误：未设置 DASHSCOPE_API_KEY 环境变量")
        print("请在 .env 文件中添加：")
        print("DASHSCOPE_API_KEY=your_api_key_here")
        print("\n或者在命令行中设置：")
        print("export DASHSCOPE_API_KEY=your_api_key_here")
        sys.exit(1)

    # 创建解析器
    try:
        parser = AliyunVisionParser()

        print(f"\n正在处理图片: {image_path}")
        print(f"使用模型: {parser.model}")
        print("正在调用API...\n")

        # 解析表单字段
        result = parser.parse_form_fields(image_path)

        if result["success"]:
            print("✓ 解析成功！\n")
            print("识别到的字段：")
            print("=" * 80)

            # 格式化输出
            fields = result["fields"]
            output_json = json.dumps(fields, ensure_ascii=False, indent=2)
            print(output_json)

            # 保存到文件
            if output_path:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(fields, f, ensure_ascii=False, indent=2)
                print(f"\n✓ 结果已保存到: {output_path}")

            # 统计信息
            print("\n" + "=" * 80)
            print(f"总计识别字段数: {len(fields)}")

            # 统计字段类型
            field_types = {}
            for field in fields:
                field_type = field.get("fieldType", "unknown")
                field_types[field_type] = field_types.get(field_type, 0) + 1

            print("字段类型统计:")
            for field_type, count in field_types.items():
                print(f"  - {field_type}: {count}")

        else:
            print("✗ 解析失败")
            print(f"错误信息: {result.get('error', 'Unknown error')}")
            if "raw_response" in result:
                print("\n原始响应:")
                print(result["raw_response"])
            sys.exit(1)

    except Exception as e:
        print(f"\n✗ 发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
