"""
查看和分析 PDF 表单域
生成易读的表单域映射表
"""

import json
import sys
from final_form_parser import FinalFormParser


def generate_field_mapping(pdf_path: str, output_format: str = "simple"):
    """
    生成表单域映射表

    Args:
        pdf_path: PDF 文件路径
        output_format: 输出格式 (simple/detailed/csv)
    """
    parser = FinalFormParser(pdf_path)
    result = parser.get_summary()

    if output_format == "csv":
        # CSV 格式
        print("字段名,字段类型,实例数量,首次出现页码,所有页码")
        for field in result["fields"]:
            name = field["fieldName"]
            field_type = field["fieldType"]
            instance_count = len(field["instances"])
            first_page = field["instances"][0].get("pageNumber", "?") if field["instances"] else "?"

            pages = [str(inst.get("pageNumber", "?")) for inst in field["instances"]]
            pages_str = ",".join(pages)

            print(f"{name},{field_type},{instance_count},{first_page},\"{pages_str}\"")

    elif output_format == "detailed":
        # 详细格式（JSON）
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        # 简单格式（表格）
        print("=" * 80)
        print(f"PDF 表单域映射表: {pdf_path}")
        print("=" * 80)
        print(f"\n总页数: {result['totalPages']}")
        print(f"唯一字段数: {result['uniqueFields']}")
        print(f"总 Widget 数: {result['totalWidgets']}")

        print(f"\n{'序号':<4} {'字段名':<30} {'类型':<10} {'实例数':<8} {'页码'}")
        print("-" * 80)

        for i, field in enumerate(result["fields"], 1):
            name = field["fieldName"]
            field_type = field["fieldType"]
            instance_count = len(field["instances"])

            # 获取所有页码
            pages = [str(inst.get("pageNumber", "?")) for inst in field["instances"]]
            pages_str = ", ".join(pages)

            # 截断过长的页码列表
            if len(pages_str) > 30:
                pages_str = pages_str[:27] + "..."

            print(f"{i:<4} {name:<30} {field_type:<10} {instance_count:<8} {pages_str}")

        print("\n" + "=" * 80)


def generate_field_to_label_mapping(pdf_path: str):
    """
    生成字段名到标签的映射（用于手动填写）

    Args:
        pdf_path: PDF 文件路径
    """
    parser = FinalFormParser(pdf_path)
    result = parser.get_summary()

    print("# PDF 表单域标签映射")
    print(f"# PDF 文件: {pdf_path}")
    print("#")
    print("# 请手动填写每个字段对应的中文标签")
    print("#")
    print("# 格式: 字段名 | 标签 | 类型 | 页码")
    print()

    for field in result["fields"]:
        name = field["fieldName"]
        field_type = field["fieldType"]
        first_page = field["instances"][0].get("pageNumber", "?") if field["instances"] else "?"

        print(f"{name} | [待填写标签] | {field_type} | 页{first_page}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python view_form_fields.py <pdf文件> [format]")
        print()
        print("格式选项:")
        print("  simple   - 简单表格格式（默认）")
        print("  detailed - 详细 JSON 格式")
        print("  csv      - CSV 格式")
        print("  mapping  - 生成标签映射模板")
        print()
        print("示例:")
        print("  python view_form_fields.py form.pdf")
        print("  python view_form_fields.py form.pdf csv > fields.csv")
        print("  python view_form_fields.py form.pdf mapping > mapping.txt")
        sys.exit(1)

    pdf_path = sys.argv[1]
    format_type = sys.argv[2] if len(sys.argv) > 2 else "simple"

    try:
        if format_type == "mapping":
            generate_field_to_label_mapping(pdf_path)
        else:
            generate_field_mapping(pdf_path, format_type)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
