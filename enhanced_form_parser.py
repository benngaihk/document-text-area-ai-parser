"""
增强版PDF表单解析器
结合本地PDF解析和Google Document AI，通过坐标匹配找到表单字段的真实标签
"""

import json
import sys
import os
from typing import Dict, List, Any, Optional, Tuple
from pypdf import PdfReader
from dotenv import load_dotenv
from google.cloud import documentai_v1 as documentai
from google.api_core.client_options import ClientOptions
from final_form_parser import FinalFormParser


class EnhancedFormParser:
    """增强版表单解析器 - 结合本地解析和Document AI"""
    
    def __init__(self, pdf_path: str):
        """初始化"""
        self.pdf_path = pdf_path
        
        # 初始化本地解析器
        self.local_parser = FinalFormParser(pdf_path)
        
        # 初始化Document AI（如果配置了环境变量）
        self.document_ai_client = None
        self._init_document_ai()
    
    def _init_document_ai(self):
        """初始化Document AI客户端"""
        try:
            load_dotenv()
            
            project_id = os.getenv("PROJECT_ID")
            location = os.getenv("LOCATION")
            processor_id = os.getenv("PROCESSOR_ID")
            
            if not all([project_id, location, processor_id]):
                print("⚠️  Document AI 未配置，将只使用本地解析")
                return
            
            # 初始化客户端
            opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
            self.document_ai_client = documentai.DocumentProcessorServiceClient(client_options=opts)
            self.processor_name = self.document_ai_client.processor_path(
                project_id, location, processor_id
            )
            
            print("✅ Document AI 客户端初始化成功")
            
        except Exception as e:
            print(f"⚠️  Document AI 初始化失败: {e}")
            self.document_ai_client = None
    
    def process_with_document_ai(self) -> Optional[documentai.Document]:
        """使用Document AI处理文档"""
        if not self.document_ai_client:
            return None
        
        try:
            with open(self.pdf_path, "rb") as f:
                file_content = f.read()
            
            # 创建处理请求
            raw_document = documentai.RawDocument(
                content=file_content,
                mime_type="application/pdf"
            )
            
            # 配置处理选项 - 只处理第一页
            process_options = documentai.ProcessOptions(
                individual_page_selector=documentai.ProcessOptions.IndividualPageSelector(
                    pages=[1]  # API 使用 1-based 索引，只处理第一页
                )
            )
            
            request = documentai.ProcessRequest(
                name=self.processor_name,
                raw_document=raw_document,
                process_options=process_options,
                skip_human_review=True
            )
            
            # 处理文档
            result = self.document_ai_client.process_document(request=request)
            return result.document
            
        except Exception as e:
            print(f"❌ Document AI 处理失败: {e}")
            return None
    
    def extract_text_elements(self, document: documentai.Document) -> List[Dict[str, Any]]:
        """从Document AI结果中提取文本元素"""
        text_elements = []
        
        for page_idx, page in enumerate(document.pages):
            page_num = page_idx + 1
            
            # 获取页面尺寸
            page_width = float(page.dimension.width) if page.dimension else 612
            page_height = float(page.dimension.height) if page.dimension else 792
            
            # 提取 tokens（最细粒度的文本块，对于标签匹配最准确）
            for token in page.tokens:
                text = self._get_text_from_layout(token.layout, document.text)
                if text.strip():
                    text_elements.append({
                        "type": "token",
                        "text": text.strip(),
                        "pageNumber": page_num,
                        "boundingBox": self._convert_bounding_box(token.layout.bounding_poly, page_width, page_height),
                        "confidence": token.layout.confidence if hasattr(token.layout, 'confidence') else 1.0
                    })

            # 提取表单字段名称（这些通常是标签）
            for form_field in page.form_fields:
                field_name = self._get_text_from_layout(form_field.field_name, document.text) if form_field.field_name else ""

                if field_name.strip():
                    text_elements.append({
                        "type": "form_field_label",
                        "text": field_name.strip(),
                        "pageNumber": page_num,
                        "boundingBox": self._convert_bounding_box(form_field.field_name.bounding_poly, page_width, page_height),
                        "confidence": form_field.field_name.confidence if hasattr(form_field.field_name, 'confidence') else 1.0
                    })
        
        return text_elements
    
    def _get_text_from_layout(self, layout, document_text: str) -> str:
        """从布局中提取文本"""
        if not layout.text_anchor:
            return ""
        
        start_idx = layout.text_anchor.text_segments[0].start_index
        end_idx = layout.text_anchor.text_segments[0].end_index
        
        return document_text[start_idx:end_idx]
    
    def _convert_bounding_box(self, bounding_poly, page_width: float = 612, page_height: float = 792) -> Dict[str, float]:
        """转换边界框坐标为归一化坐标"""
        if not bounding_poly or not bounding_poly.vertices:
            return {"x1": 0, "y1": 0, "x2": 0, "y2": 0}
        
        vertices = bounding_poly.vertices
        x_coords = [v.x for v in vertices]
        y_coords = [v.y for v in vertices]
        
        # 转换为归一化坐标
        return {
            "x1": min(x_coords) / page_width,
            "y1": 1 - (max(y_coords) / page_height),  # 翻转Y轴
            "x2": max(x_coords) / page_width,
            "y2": 1 - (min(y_coords) / page_height)   # 翻转Y轴
        }
    
    def find_nearby_labels(self, field_rect: Dict[str, float], text_elements: List[Dict[str, Any]], 
                          page_num: int, search_radius: float = 0.2) -> List[Dict[str, Any]]:
        """查找字段附近的标签文本"""
        nearby_labels = []
        
        for element in text_elements:
            if element["pageNumber"] != page_num:
                continue
            
            element_rect = element["boundingBox"]
            
            # 计算距离
            distance = self._calculate_distance(field_rect, element_rect)
            
            if distance <= search_radius:
                nearby_labels.append({
                    "text": element["text"],
                    "type": element["type"],
                    "distance": distance,
                    "confidence": element.get("confidence", 1.0),
                    "boundingBox": element_rect
                })
        
        # 按距离排序
        nearby_labels.sort(key=lambda x: x["distance"])
        return nearby_labels
    
    def _calculate_distance(self, field_rect: Dict[str, float], label_rect: Dict[str, float]) -> float:
        """
        计算字段和标签之间的距离
        优先考虑位于字段左侧且在同一水平线上的标签
        """
        # 计算中心点
        field_center_x = (field_rect["x1"] + field_rect["x2"]) / 2
        field_center_y = (field_rect["y1"] + field_rect["y2"]) / 2
        label_center_x = (label_rect["x1"] + label_rect["x2"]) / 2
        label_center_y = (label_rect["y1"] + label_rect["y2"]) / 2

        # 计算水平和垂直距离
        dx = field_center_x - label_center_x
        dy = abs(field_center_y - label_center_y)

        # 基础欧几里得距离
        base_distance = (dx ** 2 + dy ** 2) ** 0.5

        # 如果标签在字段左侧（dx > 0）且在同一水平线上（dy 较小），给予奖励（减小距离）
        if dx > 0 and dy < 0.05:  # 标签在左侧且基本水平对齐
            return base_distance * 0.5  # 距离减半，优先级提高

        # 如果标签在字段上方（dy 较大且 label_center_y < field_center_y）
        elif label_center_y < field_center_y and abs(dx) < 0.1:  # 标签在上方且基本垂直对齐
            return base_distance * 0.7  # 稍微降低优先级

        # 如果标签在字段右侧或下方，增加惩罚
        elif dx < 0:  # 标签在右侧
            return base_distance * 2.0  # 距离加倍，优先级降低

        return base_distance
    
    def enhance_fields_with_labels(self) -> Dict[str, Any]:
        """增强字段信息，添加附近标签"""
        # 获取本地解析的字段
        local_result = self.local_parser.get_summary()
        
        # 获取Document AI结果
        document_ai_doc = self.process_with_document_ai()
        
        if not document_ai_doc:
            print("⚠️  无法获取Document AI结果，返回本地解析结果")
            # 为本地结果添加空的nearbyLabels字段
            for field in local_result["fields"]:
                field["nearbyLabels"] = []
                for instance in field["instances"]:
                    instance["nearbyLabels"] = []
            local_result["documentAIEnabled"] = False
            return local_result
        
        # 提取文本元素
        text_elements = self.extract_text_elements(document_ai_doc)
        print(f"📄 提取到 {len(text_elements)} 个文本元素")
        
        # 增强字段信息
        enhanced_fields = []
        
        for field in local_result["fields"]:
            enhanced_field = field.copy()
            enhanced_field["nearbyLabels"] = []
            
            for instance in field["instances"]:
                if "normalizedRect" in instance and instance.get("pageNumber"):
                    page_num = instance["pageNumber"]
                    field_rect = instance["normalizedRect"]
                    
                    # 查找附近标签
                    nearby_labels = self.find_nearby_labels(
                        field_rect, text_elements, page_num
                    )
                    
                    # 添加到实例中
                    instance["nearbyLabels"] = nearby_labels
                    
                    # 合并到字段级别
                    enhanced_field["nearbyLabels"].extend(nearby_labels)
            
            # 去重并按距离排序
            unique_labels = {}
            for label in enhanced_field["nearbyLabels"]:
                key = label["text"]
                if key not in unique_labels or label["distance"] < unique_labels[key]["distance"]:
                    unique_labels[key] = label
            
            enhanced_field["nearbyLabels"] = sorted(
                unique_labels.values(), 
                key=lambda x: x["distance"]
            )[:5]  # 只保留最近的5个标签
            
            enhanced_fields.append(enhanced_field)
        
        # 更新结果
        enhanced_result = local_result.copy()
        enhanced_result["fields"] = enhanced_fields
        enhanced_result["textElements"] = text_elements
        enhanced_result["documentAIEnabled"] = True
        
        return enhanced_result
    
    def generate_label_mapping(self) -> Dict[str, Any]:
        """生成字段到标签的映射建议"""
        enhanced_result = self.enhance_fields_with_labels()

        mapping = {
            "fieldMappings": [],
            "unmappedFields": [],
            "suggestions": []
        }

        for field in enhanced_result["fields"]:
            field_name = field["fieldName"]
            nearby_labels = field["nearbyLabels"]

            if nearby_labels:
                # 选择最近的标签作为建议
                best_label = nearby_labels[0]

                mapping["fieldMappings"].append({
                    "fieldName": field_name,
                    "fieldType": field["fieldType"],
                    "suggestedLabel": best_label["text"],
                    "confidence": best_label["confidence"],
                    "distance": best_label["distance"],
                    "allNearbyLabels": [label["text"] for label in nearby_labels[:3]]
                })
            else:
                mapping["unmappedFields"].append({
                    "fieldName": field_name,
                    "fieldType": field["fieldType"],
                    "reason": "未找到附近标签"
                })

        # 生成建议
        mapping["suggestions"] = [
            "建议手动检查距离较远的标签匹配",
            "考虑字段的实际用途来验证标签建议",
            "对于未映射的字段，可能需要手动添加标签"
        ]

        return mapping

    def generate_simple_output(self) -> List[Dict[str, str]]:
        """生成简化的输出格式，只包含fieldName, fieldType和text（最近的标签）"""
        # 获取本地解析的字段
        local_result = self.local_parser.get_summary()

        # 获取Document AI结果
        document_ai_doc = self.process_with_document_ai()

        if not document_ai_doc:
            # 如果没有 Document AI，返回空标签
            return [{
                "fieldName": field["fieldName"],
                "fieldType": field["fieldType"],
                "text": ""
            } for field in local_result["fields"]
               if any(inst.get("pageNumber") == 1 for inst in field["instances"])]

        # 提取所有文本元素
        text_elements = self.extract_text_elements(document_ai_doc)

        output = []
        for field in local_result["fields"]:
            # 只处理第一页的字段
            first_page_instance = None
            for instance in field["instances"]:
                if instance.get("pageNumber") == 1:
                    first_page_instance = instance
                    break

            if not first_page_instance or "normalizedRect" not in first_page_instance:
                continue

            # 获取字段位置
            field_rect = first_page_instance["normalizedRect"]
            field_center_y = (field_rect["y1"] + field_rect["y2"]) / 2

            # 找到距离字段最近的文本元素（只看第一页的）
            page_1_elements = [e for e in text_elements if e["pageNumber"] == 1]

            if not page_1_elements:
                output.append({
                    "fieldName": field["fieldName"],
                    "fieldType": field["fieldType"],
                    "text": ""
                })
                continue

            # 计算每个元素到字段的距离
            elements_with_distance = []
            for element in page_1_elements:
                element_rect = element["boundingBox"]
                distance = self._calculate_distance(field_rect, element_rect)
                elements_with_distance.append({
                    **element,
                    "distance": distance
                })

            # 按距离排序
            elements_with_distance.sort(key=lambda x: x["distance"])

            # 找到最近元素的 Y 坐标
            closest_element = elements_with_distance[0]
            closest_y = (closest_element["boundingBox"]["y1"] + closest_element["boundingBox"]["y2"]) / 2

            # 收集与最近元素在同一行的所有 tokens
            same_line_tokens = []
            for element in page_1_elements:
                element_bbox = element["boundingBox"]
                element_y = (element_bbox["y1"] + element_bbox["y2"]) / 2
                element_x = (element_bbox["x1"] + element_bbox["x2"]) / 2

                # 如果 Y 坐标与最近元素相近（在同一行）
                if abs(element_y - closest_y) < 0.01:  # 允许 1% 的误差
                    same_line_tokens.append({
                        "text": element["text"],
                        "x": element_x
                    })

            # 按 X 坐标从左到右排序
            same_line_tokens.sort(key=lambda t: t["x"])

            # 合并文本
            text = " ".join([t["text"] for t in same_line_tokens])

            output.append({
                "fieldName": field["fieldName"],
                "fieldType": field["fieldType"],
                "text": text
            })

        return output


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法: python enhanced_form_parser.py <pdf文件路径> [output_format]")
        print("输出格式: enhanced, mapping, simple, json")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_format = sys.argv[2] if len(sys.argv) > 2 else "json"

    try:
        parser = EnhancedFormParser(pdf_path)

        if output_format == "mapping":
            result = parser.generate_label_mapping()
            print("=" * 80)
            print("字段标签映射建议")
            print("=" * 80)

            print("\n📋 已映射字段:")
            for mapping in result["fieldMappings"]:
                print(f"  {mapping['fieldName']} → {mapping['suggestedLabel']} (置信度: {mapping['confidence']:.2f})")

            print("\n❓ 未映射字段:")
            for field in result["unmappedFields"]:
                print(f"  {field['fieldName']} ({field['fieldType']}) - {field['reason']}")

            print("\n💡 建议:")
            for suggestion in result["suggestions"]:
                print(f"  • {suggestion}")

        elif output_format == "simple":
            result = parser.enhance_fields_with_labels()
            print("=" * 80)
            print(f"增强版表单解析结果: {pdf_path}")
            print("=" * 80)

            print(f"\n总页数: {result['totalPages']}")
            print(f"唯一字段数: {result['uniqueFields']}")
            print(f"总Widget数: {result['totalWidgets']}")
            print(f"Document AI: {'✅ 已启用' if result.get('documentAIEnabled') else '❌ 未启用'}")

            print(f"\n{'序号':<4} {'字段名':<25} {'类型':<10} {'建议标签':<20} {'置信度'}")
            print("-" * 80)

            for i, field in enumerate(result["fields"], 1):
                field_name = field["fieldName"]
                field_type = field["fieldType"]

                # 安全地获取nearbyLabels
                nearby_labels = field.get("nearbyLabels", [])
                if nearby_labels:
                    suggested_label = nearby_labels[0]["text"]
                    confidence = nearby_labels[0]["confidence"]
                    confidence_str = f"{confidence:.2f}"
                else:
                    suggested_label = "未找到"
                    confidence_str = "N/A"

                print(f"{i:<4} {field_name:<25} {field_type:<10} {suggested_label:<20} {confidence_str}")

        elif output_format == "json":
            # 生成简化的JSON输出并保存到 ./result
            result = parser.generate_simple_output()

            # 创建 result 目录（在当前目录下）
            result_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "result")
            os.makedirs(result_dir, exist_ok=True)

            # 生成输出文件名
            base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            output_file = os.path.join(result_dir, f"{base_name}_fields.json")

            # 保存到文件
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            print(f"✅ 结果已保存到: {output_file}")
            print(f"📊 第一页共找到 {len(result)} 个字段")

            # 同时输出到控制台
            print("\n" + "=" * 80)
            print("字段列表 (第一页):")
            print("=" * 80)
            print(json.dumps(result, ensure_ascii=False, indent=2))

        else:  # enhanced format
            result = parser.enhance_fields_with_labels()
            print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
