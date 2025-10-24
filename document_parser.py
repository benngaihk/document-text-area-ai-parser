"""
Google Document AI PDF Parser
解析 PDF 文件并提取结构化数据
"""

import os
from typing import Dict, List, Any, Optional
from google.cloud import documentai_v1 as documentai
from google.api_core.client_options import ClientOptions
from dotenv import load_dotenv


class DocumentAIParser:
    """Google Document AI 解析器"""

    def __init__(self, project_id: str, location: str, processor_id: str):
        """
        初始化 Document AI 解析器

        Args:
            project_id: GCP 项目 ID
            location: 处理器位置 (如 'us', 'eu')
            processor_id: Document AI 处理器 ID
        """
        self.project_id = project_id
        self.location = location
        self.processor_id = processor_id

        # 初始化客户端
        opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
        self.client = documentai.DocumentProcessorServiceClient(client_options=opts)

        # 构建处理器资源名称
        self.processor_name = self.client.processor_path(
            project_id, location, processor_id
        )

    def process_document(self, file_path: str, mime_type: str = "application/pdf", imageless_mode: bool = True, max_pages: int = None) -> documentai.Document:
        """
        处理文档文件

        Args:
            file_path: PDF 文件路径
            mime_type: 文件 MIME 类型
            imageless_mode: 是否使用 imageless 模式（支持最多 30 页，默认 True）
            max_pages: 最多处理的页面数（None 表示全部，默认 15 页限制）

        Returns:
            处理后的 Document 对象
        """
        # 读取文件
        with open(file_path, "rb") as file:
            file_content = file.read()

        # 创建请求
        raw_document = documentai.RawDocument(content=file_content, mime_type=mime_type)

        # 配置处理选项
        process_options = None
        if max_pages is not None:
            # 只处理指定数量的页面
            process_options = documentai.ProcessOptions(
                individual_page_selector=documentai.ProcessOptions.IndividualPageSelector(
                    pages=list(range(1, min(max_pages + 1, 16)))  # API 使用 1-based 索引
                )
            )

        request = documentai.ProcessRequest(
            name=self.processor_name,
            raw_document=raw_document,
            process_options=process_options,
            skip_human_review=True
        )

        # 处理文档
        result = self.client.process_document(request=request)
        return result.document

    def extract_entities(self, document: documentai.Document) -> List[Dict[str, Any]]:
        """
        提取文档中的实体

        Args:
            document: Document AI 返回的文档对象

        Returns:
            实体列表
        """
        entities = []

        for entity in document.entities:
            entity_data = {
                "type": entity.type_,
                "mentionText": entity.mention_text,
                "confidence": entity.confidence,
            }

            # 添加页面锚点信息
            if entity.page_anchor:
                page_refs = []
                for page_ref in entity.page_anchor.page_refs:
                    page_refs.append({
                        "page": page_ref.page,
                        "boundingPoly": self._extract_bounding_poly(page_ref.bounding_poly) if page_ref.bounding_poly else None
                    })
                entity_data["pageAnchor"] = {"pageRefs": page_refs}

            # 添加文本锚点信息
            if entity.text_anchor:
                text_segments = []
                for segment in entity.text_anchor.text_segments:
                    text_segments.append({
                        "startIndex": segment.start_index,
                        "endIndex": segment.end_index
                    })
                entity_data["textAnchor"] = {"textSegments": text_segments}

            # 处理归一化值（如果有）
            if entity.normalized_value:
                entity_data["normalizedValue"] = {
                    "text": entity.normalized_value.text
                }

            entities.append(entity_data)

        return entities

    def extract_form_fields(self, page: documentai.Document.Page, document_text: str) -> List[Dict[str, Any]]:
        """
        提取页面中的表单域

        Args:
            page: 文档页面对象
            document_text: 完整文档文本

        Returns:
            表单域列表
        """
        form_fields = []

        for field in page.form_fields:
            field_data = {}

            # 提取字段名称
            if field.field_name:
                field_data["fieldName"] = {
                    "text": self._get_text(field.field_name.text_anchor, document_text),
                    "confidence": field.field_name.confidence,
                }
                if field.field_name.text_anchor:
                    field_data["fieldName"]["textAnchor"] = self._extract_text_anchor(
                        field.field_name.text_anchor
                    )
                if field.field_name.bounding_poly:
                    field_data["fieldName"]["boundingPoly"] = self._extract_bounding_poly(
                        field.field_name.bounding_poly
                    )

            # 提取字段值
            if field.field_value:
                field_data["fieldValue"] = {
                    "text": self._get_text(field.field_value.text_anchor, document_text),
                    "confidence": field.field_value.confidence,
                }
                if field.field_value.text_anchor:
                    field_data["fieldValue"]["textAnchor"] = self._extract_text_anchor(
                        field.field_value.text_anchor
                    )
                if field.field_value.bounding_poly:
                    field_data["fieldValue"]["boundingPoly"] = self._extract_bounding_poly(
                        field.field_value.bounding_poly
                    )

            form_fields.append(field_data)

        return form_fields

    def _get_text(self, text_anchor: Optional[documentai.Document.TextAnchor],
                  document_text: str) -> str:
        """
        从文本锚点获取文本内容

        Args:
            text_anchor: 文本锚点
            document_text: 完整文档文本

        Returns:
            文本内容
        """
        if not text_anchor or not text_anchor.text_segments:
            return ""

        # 从完整文档文本中提取
        response = ""
        for segment in text_anchor.text_segments:
            start_index = int(segment.start_index) if segment.start_index else 0
            end_index = int(segment.end_index) if segment.end_index else 0
            response += document_text[start_index:end_index]

        return response

    def _extract_text_anchor(self, text_anchor: documentai.Document.TextAnchor) -> Dict[str, Any]:
        """提取文本锚点信息"""
        segments = []
        for segment in text_anchor.text_segments:
            segments.append({
                "startIndex": int(segment.start_index) if segment.start_index else 0,
                "endIndex": int(segment.end_index) if segment.end_index else 0
            })
        return {"textSegments": segments}

    def _extract_bounding_poly(self, bounding_poly: documentai.BoundingPoly) -> Dict[str, Any]:
        """提取边界框信息"""
        vertices = []
        for vertex in bounding_poly.normalized_vertices:
            vertices.append({
                "x": vertex.x,
                "y": vertex.y
            })
        return {"normalizedVertices": vertices}

    def format_result(self, document: documentai.Document) -> Dict[str, Any]:
        """
        格式化解析结果为结构化数据

        Args:
            document: Document AI 返回的文档对象

        Returns:
            结构化的文档数据
        """
        result = {
            "document": {
                "text": document.text,
                "entities": self.extract_entities(document),
                "pages": []
            }
        }

        # 处理每一页
        for page_num, page in enumerate(document.pages):
            page_data = {
                "pageNumber": page_num + 1,
                "dimension": {
                    "width": page.dimension.width,
                    "height": page.dimension.height,
                    "unit": page.dimension.unit
                } if page.dimension else None,
                "formFields": self.extract_form_fields(page, document.text),
                "tables": [],
                "paragraphs": [],
                "lines": [],
                "tokens": []
            }

            # 提取表格信息
            for table in page.tables:
                table_data = {
                    "headerRows": [],
                    "bodyRows": []
                }
                # 简化表格提取（可以根据需要扩展）
                page_data["tables"].append(table_data)

            # 提取段落信息
            for paragraph in page.paragraphs:
                para_data = {
                    "textAnchor": self._extract_text_anchor(paragraph.layout.text_anchor) if paragraph.layout.text_anchor else None,
                    "confidence": paragraph.layout.confidence if paragraph.layout else None
                }
                page_data["paragraphs"].append(para_data)

            # 提取行信息
            for line in page.lines:
                line_data = {
                    "textAnchor": self._extract_text_anchor(line.layout.text_anchor) if line.layout.text_anchor else None,
                    "confidence": line.layout.confidence if line.layout else None
                }
                page_data["lines"].append(line_data)

            result["document"]["pages"].append(page_data)

        return result


def parse_pdf(file_path: str, project_id: str = None, location: str = None,
              processor_id: str = None, max_pages: int = 15) -> Dict[str, Any]:
    """
    解析 PDF 文件的便捷函数

    Args:
        file_path: PDF 文件路径
        project_id: GCP 项目 ID（如果不提供，从环境变量读取）
        location: 处理器位置（如果不提供，从环境变量读取）
        processor_id: 处理器 ID（如果不提供，从环境变量读取）
        max_pages: 最多处理的页数（默认15页，避免超出API限制）

    Returns:
        结构化的文档数据
    """
    # 加载环境变量
    load_dotenv()

    # 获取配置
    project_id = project_id or os.getenv("PROJECT_ID")
    location = location or os.getenv("LOCATION", "us")
    processor_id = processor_id or os.getenv("PROCESSOR_ID")

    if not all([project_id, processor_id]):
        raise ValueError("必须提供 project_id 和 processor_id，或在 .env 文件中配置")

    # 创建解析器并处理文档
    parser = DocumentAIParser(project_id, location, processor_id)
    document = parser.process_document(file_path, max_pages=max_pages)
    result = parser.format_result(document)

    # 添加处理信息
    result["processing_info"] = {
        "max_pages_requested": max_pages,
        "pages_processed": len(result["document"]["pages"])
    }

    return result


if __name__ == "__main__":
    import json
    import sys

    # 示例用法
    if len(sys.argv) < 2:
        print("使用方法: python document_parser.py <pdf文件路径>")
        sys.exit(1)

    pdf_path = sys.argv[1]

    try:
        # 解析 PDF
        result = parse_pdf(pdf_path)

        # 输出结果
        print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as e:
        print(f"错误: {str(e)}", file=sys.stderr)
        sys.exit(1)
