#!/usr/bin/env python3
"""
PDF表单字段提取和识别综合工具
结合了PDF字段坐标提取、图片标注和阿里云视觉识别功能
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont
import fitz  # PyMuPDF
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

try:
    from dashscope import MultiModalConversation
    import dashscope
except ImportError:
    print("警告：未安装 dashscope 库，阿里云视觉识别功能将不可用")
    print("如需使用该功能，请运行：pip install dashscope")
    dashscope = None


class PDFFieldExtractor:
    """PDF表单字段提取器"""

    def __init__(self, pdf_path: str, output_dir: str = "result"):
        """
        初始化提取器

        Args:
            pdf_path: PDF文件路径
            output_dir: 输出目录
        """
        self.pdf_path = Path(pdf_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")

        # 初始化阿里云API（如果可用）
        self.api_key = os.getenv('DASHSCOPE_API_KEY')
        if self.api_key and dashscope:
            dashscope.api_key = self.api_key
            self.model = "qwen-vl-plus-latest"
            self.vision_available = True
        else:
            self.vision_available = False

    def extract_field_coordinates(self, page_num: int = 0) -> tuple:
        """
        从PDF中提取表单字段坐标

        Args:
            page_num: 页码（从0开始）

        Returns:
            (fields, page_width, page_height) 元组
        """
        doc = fitz.open(self.pdf_path)
        page = doc[page_num]

        fields = {}

        # 提取表单字段
        for widget in page.widgets():
            field_name = widget.field_name
            rect = widget.rect
            field_type = widget.field_type_string

            fields[field_name] = {
                'rect': [rect.x0, rect.y0, rect.x1, rect.y1],
                'type': field_type,
                'page': page_num
            }

        # 获取页面尺寸
        page_rect = page.rect
        page_width = page_rect.width
        page_height = page_rect.height

        doc.close()
        return fields, page_width, page_height

    def pdf_to_image(self, page_num: int = 0, dpi: int = 200) -> Path:
        """
        将PDF页面转换为图片

        Args:
            page_num: 页码（从0开始）
            dpi: 分辨率

        Returns:
            生成的图片路径
        """
        doc = fitz.open(self.pdf_path)
        page = doc[page_num]

        # 转换为图片
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)

        # 保存图片
        image_path = self.output_dir / f"{self.pdf_path.stem}_page{page_num + 1}.png"
        pix.save(image_path)
        doc.close()

        return image_path

    def annotate_image(self, image_path: Path, fields: Dict, page_width: float,
                      page_height: float, output_suffix: str = "_annotated") -> Path:
        """
        在图片上标注字段位置和名称

        Args:
            image_path: 图片路径
            fields: 字段信息字典
            page_width: PDF页面宽度
            page_height: PDF页面高度
            output_suffix: 输出文件后缀

        Returns:
            标注后的图片路径
        """
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)

        # 计算缩放比例
        img_width, img_height = img.size
        scale_x = img_width / page_width
        scale_y = img_height / page_height

        # 加载字体
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 30)
        except:
            font = ImageFont.load_default()

        # 绘制字段标注
        for field_name, field_info in fields.items():
            rect = field_info['rect']
            x1 = rect[0] * scale_x
            y1 = rect[1] * scale_y
            x2 = rect[2] * scale_x
            y2 = rect[3] * scale_y

            # 绘制边界框
            draw.rectangle([x1, y1, x2, y2], outline='red', width=2)

            # 绘制字段名称
            text_position = (x1 + 2, y1 + 2)
            text_bbox = draw.textbbox(text_position, field_name, font=font)
            draw.rectangle(text_bbox, fill='yellow')
            draw.text(text_position, field_name, fill='red', font=font)

        # 保存标注后的图片
        output_path = self.output_dir / f"{image_path.stem}{output_suffix}.png"
        img.save(output_path)

        return output_path

    def recognize_field_labels(self, image_path: Path,
                               field_names: Optional[list] = None,
                               custom_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        使用阿里云视觉模型识别字段标签

        Args:
            image_path: 图片路径
            custom_prompt: 自定义提示词

        Returns:
            识别结果字典
        """
        if not self.vision_available:
            return {
                "success": False,
                "error": "阿里云视觉识别功能不可用（未配置API密钥或未安装dashscope库）"
            }

        # 默认提示词
        if custom_prompt is None:
            if field_names:
                # 如果提供了字段名列表，生成更精确的提示词
                field_list = "\n".join([f"- {name}" for name in field_names])
                custom_prompt = f"""请仔细分析这张表单图片。图片中用红色边框标注了表单字段，在每个红色边框的左上角有黄色背景显示字段名称。

图片中包含以下字段（已标注在红色框的左上角）：
{field_list}

你的任务是：
对于上述每个字段，识别该字段需要填写什么内容。

请以JSON数组格式输出，每个字段一个JSON对象。格式如下：
[
{{
    "fieldName": [字段名],
    "fieldType": [字段类型],
    "text": [推测的字段标签文字]
}},
...
]

重要要求：
- fieldName 必须使用我提供的字段名（完全一致，包括大小写和点号）
- fieldType 根据字段外观判断（text、checkbox、date 等）
- text 是字段附近的标签文字或说明文字，如果没有明显标签则为空字符串
- 必须包含所有我列出的字段，即使某些字段的 text 为空
- 只输出JSON数组，不要包含任何其他文字说明"""
            else:
                # 没有提供字段名列表，使用原来的提示词
                custom_prompt = """请仔细分析这张表单图片。图片中用红色边框标注了表单字段，在每个红色边框的左上角有黄色背景的字段名称标签。

你的任务是：
1. 找到每个红色边框标注的字段
2. 读取该字段左上角黄色背景中的字段名称（例如：fill_1_P.2、fill_2_P.2 等）
3. 识别该字段附近的标签文字（通常在字段左侧或上方，用于说明该字段需要填写什么内容）
4. 判断字段类型（text、checkbox、date 等）

请以JSON数组格式输出，每个字段一个JSON对象。格式如下：
[
{{
    "fieldName": "fill_1_P.2",
    "fieldType": "text",
    "text": "字段标签文字"
}}
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
                    {"text": custom_prompt},
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
                result_text = response.output.choices[0].message.content[0]["text"]

                # 解析JSON
                try:
                    result_text = result_text.strip()

                    # 提取JSON部分
                    if "```json" in result_text:
                        start = result_text.find("```json") + 7
                        end = result_text.find("```", start)
                        result_text = result_text[start:end].strip()
                    elif "```" in result_text:
                        start = result_text.find("```") + 3
                        end = result_text.find("```", start)
                        result_text = result_text[start:end].strip()

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

    def merge_results(self, coordinates: Dict, labels: Dict) -> Dict:
        """
        合并坐标信息和标签识别结果

        Args:
            coordinates: 字段坐标信息
            labels: 标签识别结果

        Returns:
            合并后的完整字段信息
        """
        # 创建标签查找字典
        label_dict = {}
        if labels.get("success") and labels.get("fields"):
            for field in labels["fields"]:
                label_dict[field["fieldName"]] = {
                    "text": field.get("text", ""),
                    "recognizedType": field.get("fieldType", "")
                }

        # 合并信息
        merged = {}
        for field_name, coord_info in coordinates.items():
            merged[field_name] = {
                "fieldName": field_name,
                "fieldType": coord_info["type"],
                "coordinates": {
                    "rect": coord_info["rect"],
                    "page": coord_info["page"]
                }
            }

            # 添加识别的标签信息
            if field_name in label_dict:
                merged[field_name]["label"] = label_dict[field_name]["text"]
                merged[field_name]["recognizedType"] = label_dict[field_name]["recognizedType"]
            else:
                merged[field_name]["label"] = ""
                merged[field_name]["recognizedType"] = ""

        return merged

    def process(self, page_num: int = 0, use_vision: bool = True) -> Dict[str, Any]:
        """
        完整的处理流程

        Args:
            page_num: 要处理的页码（从0开始）
            use_vision: 是否使用视觉识别功能

        Returns:
            包含所有结果的字典
        """
        results = {
            "pdf_path": str(self.pdf_path),
            "page_num": page_num,
            "output_dir": str(self.output_dir)
        }

        print(f"\n{'='*80}")
        print(f"处理PDF: {self.pdf_path.name}")
        print(f"页码: {page_num + 1}")
        print(f"{'='*80}\n")

        # 1. 提取字段坐标
        print("步骤 1/5: 提取表单字段坐标...")
        fields, page_width, page_height = self.extract_field_coordinates(page_num)
        print(f"✓ 找到 {len(fields)} 个表单字段")
        results["fields_count"] = len(fields)

        # 保存坐标信息
        coords_file = self.output_dir / f"{self.pdf_path.stem}_coordinates.json"
        with open(coords_file, 'w', encoding='utf-8') as f:
            json.dump(fields, f, indent=2, ensure_ascii=False)
        print(f"✓ 坐标信息保存到: {coords_file}")
        results["coordinates_file"] = str(coords_file)

        # 2. 转换PDF为图片
        print("\n步骤 2/5: 将PDF页面转换为图片...")
        image_path = self.pdf_to_image(page_num)
        print(f"✓ 图片保存到: {image_path}")
        results["image_path"] = str(image_path)

        # 3. 创建标注图片
        print("\n步骤 3/5: 创建标注图片...")
        annotated_path = self.annotate_image(image_path, fields, page_width, page_height)
        print(f"✓ 标注图片保存到: {annotated_path}")
        results["annotated_image_path"] = str(annotated_path)

        # 4. 使用视觉模型识别标签
        if use_vision and self.vision_available:
            print("\n步骤 4/5: 使用阿里云视觉模型识别字段标签...")
            print("正在调用API...")
            # 传入字段名列表，让模型使用准确的字段名
            field_names_list = list(fields.keys())
            labels_result = self.recognize_field_labels(annotated_path, field_names=field_names_list)

            if labels_result["success"]:
                print(f"✓ 成功识别 {len(labels_result['fields'])} 个字段标签")
                results["labels"] = labels_result["fields"]
            else:
                print(f"✗ 标签识别失败: {labels_result.get('error', 'Unknown error')}")
                results["labels"] = []
        else:
            if not use_vision:
                print("\n步骤 4/5: 跳过视觉识别（use_vision=False）")
            else:
                print("\n步骤 4/5: 跳过视觉识别（未配置API密钥）")
            labels_result = {"success": False, "fields": []}
            results["labels"] = []

        # 5. 合并结果
        print("\n步骤 5/5: 合并结果...")
        merged_data = self.merge_results(fields, labels_result)

        # 保存合并后的完整数据
        merged_file = self.output_dir / f"{self.pdf_path.stem}_complete.json"
        with open(merged_file, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, indent=2, ensure_ascii=False)
        print(f"✓ 完整数据保存到: {merged_file}")
        results["complete_file"] = str(merged_file)

        # 生成简化的字段列表（按要求的格式）
        simplified_fields = []
        for field_name, field_info in merged_data.items():
            simplified_fields.append({
                "fieldName": field_name,
                "fieldType": field_info.get("recognizedType") or field_info["fieldType"],
                "text": field_info.get("label", "")
            })

        # 保存简化格式
        simplified_file = self.output_dir / f"{self.pdf_path.stem}_fields.json"
        with open(simplified_file, 'w', encoding='utf-8') as f:
            json.dump(simplified_fields, f, indent=2, ensure_ascii=False)
        print(f"✓ 简化格式保存到: {simplified_file}")
        results["simplified_file"] = str(simplified_file)

        print(f"\n{'='*80}")
        print("处理完成！")
        print(f"{'='*80}")

        return results


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="PDF表单字段提取和识别综合工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 完整处理（包括视觉识别）
  python pdf_field_extractor.py document.pdf

  # 指定输出目录
  python pdf_field_extractor.py document.pdf --output result

  # 处理指定页码
  python pdf_field_extractor.py document.pdf --page 2

  # 不使用视觉识别
  python pdf_field_extractor.py document.pdf --no-vision
        """
    )

    parser.add_argument('pdf_path', help='PDF文件路径')
    parser.add_argument('--output', '-o', default='result', help='输出目录（默认: result）')
    parser.add_argument('--page', '-p', type=int, default=1, help='要处理的页码（默认: 1）')
    parser.add_argument('--no-vision', action='store_true', help='不使用视觉识别功能')

    args = parser.parse_args()

    try:
        # 创建提取器
        extractor = PDFFieldExtractor(args.pdf_path, args.output)

        # 处理PDF
        results = extractor.process(
            page_num=args.page - 1,  # 转换为从0开始的索引
            use_vision=not args.no_vision
        )

        # 显示摘要
        print("\n生成的文件:")
        print(f"  - 坐标信息: {results['coordinates_file']}")
        print(f"  - 原始图片: {results['image_path']}")
        print(f"  - 标注图片: {results['annotated_image_path']}")
        print(f"  - 完整数据: {results['complete_file']}")
        print(f"  - 简化格式: {results['simplified_file']}")

    except Exception as e:
        print(f"\n✗ 发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
