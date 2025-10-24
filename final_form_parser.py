"""
最终版PDF表单解析器
正确处理层级表单域结构，结合 Document AI 提取标签
"""

import json
import sys
from typing import Dict, List, Any, Optional
from pypdf import PdfReader


class FinalFormParser:
    """最终版表单解析器"""

    def __init__(self, pdf_path: str):
        """初始化"""
        self.pdf_path = pdf_path
        self.reader = PdfReader(pdf_path)

    def extract_all_fields(self) -> List[Dict[str, Any]]:
        """提取所有表单域"""
        fields_list = []

        # 检查 AcroForm
        if "/AcroForm" not in self.reader.trailer["/Root"]:
            return fields_list

        acroform = self.reader.trailer["/Root"]["/AcroForm"]
        if "/Fields" not in acroform:
            return fields_list

        # 遍历所有字段
        for field_ref in acroform["/Fields"]:
            field_obj = field_ref.get_object()
            extracted = self._extract_field(field_obj)
            fields_list.extend(extracted)

        return fields_list

    def _extract_field(self, field_obj, parent_name: str = "") -> List[Dict[str, Any]]:
        """
        递归提取字段（处理层级结构）

        Args:
            field_obj: 字段对象
            parent_name: 父字段名称

        Returns:
            字段列表
        """
        results = []

        # 获取字段名称
        field_name = str(field_obj["/T"]) if "/T" in field_obj else ""
        full_name = f"{parent_name}.{field_name}" if parent_name else field_name

        # 检查是否有子字段
        if "/Kids" in field_obj:
            # 这是一个有子字段的父字段
            kids = field_obj["/Kids"]

            for kid_ref in kids:
                kid_obj = kid_ref.get_object()

                # 检查子字段是否也有 /T（表示它是另一个字段）
                if "/T" in kid_obj and "/Kids" in kid_obj:
                    # 子字段也是一个父字段，递归处理
                    results.extend(self._extract_field(kid_obj, full_name))
                else:
                    # 这是一个最终的 widget（包含实际位置信息）
                    widget_info = self._extract_widget(kid_obj, full_name)
                    if widget_info:
                        results.append(widget_info)
        else:
            # 这是一个没有子字段的字段
            widget_info = self._extract_widget(field_obj, full_name)
            if widget_info:
                results.append(widget_info)

        return results

    def _extract_widget(self, widget_obj, field_name: str) -> Optional[Dict[str, Any]]:
        """提取 widget 信息"""
        widget_info = {
            "fieldName": field_name
        }

        # 获取字段类型
        field_type = None
        if "/FT" in widget_obj:
            field_type = str(widget_obj["/FT"])
        elif "/Parent" in widget_obj:
            parent = widget_obj["/Parent"].get_object() if hasattr(widget_obj["/Parent"], 'get_object') else widget_obj["/Parent"]
            if "/FT" in parent:
                field_type = str(parent["/FT"])

        type_mapping = {
            "/Tx": "text",
            "/Btn": "button",
            "/Ch": "choice",
            "/Sig": "signature"
        }
        widget_info["fieldType"] = type_mapping.get(field_type, field_type or "unknown")

        # 获取值
        value = ""
        if "/V" in widget_obj:
            value = str(widget_obj["/V"])
        elif "/Parent" in widget_obj:
            parent = widget_obj["/Parent"].get_object() if hasattr(widget_obj["/Parent"], 'get_object') else widget_obj["/Parent"]
            if "/V" in parent:
                value = str(parent["/V"])

        widget_info["value"] = value

        # 获取位置
        if "/Rect" in widget_obj:
            rect = widget_obj["/Rect"]

            # 获取页面信息
            page_num = None
            if "/P" in widget_obj:
                page_ref = widget_obj["/P"]
                page_num = self._find_page_number(page_ref)

            if page_num:
                widget_info["pageNumber"] = page_num

                # 获取页面尺寸
                page = self.reader.pages[page_num - 1]
                page_width = float(page.mediabox.width) if page.mediabox else 612
                page_height = float(page.mediabox.height) if page.mediabox else 792

                widget_info["rect"] = {
                    "x1": float(rect[0]),
                    "y1": float(rect[1]),
                    "x2": float(rect[2]),
                    "y2": float(rect[3])
                }

                # 归一化坐标（用于与 Document AI 匹配）
                widget_info["normalizedRect"] = {
                    "x1": float(rect[0]) / page_width,
                    "y1": 1 - (float(rect[3]) / page_height),  # 翻转Y轴
                    "x2": float(rect[2]) / page_width,
                    "y2": 1 - (float(rect[1]) / page_height)   # 翻转Y轴
                }

        return widget_info

    def _find_page_number(self, page_ref) -> Optional[int]:
        """查找页面编号"""
        try:
            page_obj = page_ref.get_object() if hasattr(page_ref, 'get_object') else page_ref
            for i, page in enumerate(self.reader.pages):
                if page == page_obj or (hasattr(page, 'indirect_reference') and page.indirect_reference == page_ref):
                    return i + 1  # 1-based
        except:
            pass
        return None

    def get_summary(self) -> Dict[str, Any]:
        """获取摘要"""
        fields = self.extract_all_fields()

        # 按字段名分组（去掉子项编号）
        unique_fields = {}
        for field in fields:
            base_name = field["fieldName"]
            if base_name not in unique_fields:
                unique_fields[base_name] = {
                    "fieldName": base_name,
                    "fieldType": field["fieldType"],
                    "instances": []
                }

            unique_fields[base_name]["instances"].append({
                "pageNumber": field.get("pageNumber"),
                "value": field.get("value", ""),
                "rect": field.get("rect"),
                "normalizedRect": field.get("normalizedRect")
            })

        # 按页面统计
        fields_by_page = {}
        for field in fields:
            page_num = field.get("pageNumber", 0)
            if page_num not in fields_by_page:
                fields_by_page[page_num] = []
            fields_by_page[page_num].append(field)

        return {
            "totalPages": len(self.reader.pages),
            "totalWidgets": len(fields),
            "uniqueFields": len(unique_fields),
            "fieldsByPage": {str(k): len(v) for k, v in sorted(fields_by_page.items())},
            "fields": list(unique_fields.values()),
            "allWidgets": fields
        }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python final_form_parser.py <pdf文件路径>")
        sys.exit(1)

    pdf_path = sys.argv[1]

    try:
        parser = FinalFormParser(pdf_path)
        result = parser.get_summary()

        print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
