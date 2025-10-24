#!/usr/bin/env python3
"""
PDF表单解析和填写服务 - 整合版
结合阿里云视觉识别和PyPDF表单填写功能
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from typing import Dict, List, Optional
import json
import uuid
import time
import shutil
from datetime import datetime, timedelta
import PyPDF2
from pdf_field_extractor import PDFFieldExtractor

# 创建FastAPI应用
app = FastAPI(
    title="PDF表单智能解析和填写服务",
    description="使用阿里云视觉识别解析PDF表单字段，支持在线填写和导出",
    version="2.0.0"
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置
UPLOAD_DIR = Path("uploads")
TEMP_DIR = Path("temp")
STATIC_DIR = Path("static")
OUTPUT_DIR = Path("output")

# 创建必要的目录
for directory in [UPLOAD_DIR, TEMP_DIR, STATIC_DIR, OUTPUT_DIR]:
    directory.mkdir(exist_ok=True)

# 临时文件管理
temp_files = {}


class TempFileManager:
    """临时文件管理器"""

    def __init__(self, expiry_hours: int = 2):
        self.expiry_hours = expiry_hours

    async def save_uploaded_file(self, file: UploadFile) -> str:
        """保存上传的文件"""
        if not file.filename.lower().endswith('.pdf'):
            raise ValueError("只支持PDF文件")

        # 生成唯一ID
        file_id = str(uuid.uuid4())

        # 保存文件
        file_path = UPLOAD_DIR / f"{file_id}.pdf"
        with open(file_path, 'wb') as f:
            shutil.copyfileobj(file.file, f)

        # 记录文件信息
        temp_files[file_id] = {
            'original_name': file.filename,
            'upload_path': str(file_path),
            'upload_time': datetime.now(),
            'output_path': None
        }

        return file_id

    def get_file_path(self, file_id: str) -> Optional[str]:
        """获取文件路径"""
        if file_id not in temp_files:
            return None

        info = temp_files[file_id]
        # 检查是否过期
        if datetime.now() - info['upload_time'] > timedelta(hours=self.expiry_hours):
            self.cleanup_file(file_id)
            return None

        return info['upload_path']

    def register_output_file(self, file_id: str, output_path: str):
        """注册输出文件"""
        if file_id in temp_files:
            temp_files[file_id]['output_path'] = output_path

    def get_output_file(self, file_id: str) -> Optional[str]:
        """获取输出文件路径"""
        if file_id not in temp_files:
            return None
        return temp_files[file_id].get('output_path')

    def get_file_info(self, file_id: str) -> Optional[Dict]:
        """获取文件信息"""
        return temp_files.get(file_id)

    def cleanup_file(self, file_id: str) -> bool:
        """清理文件"""
        if file_id not in temp_files:
            return False

        info = temp_files[file_id]

        # 删除上传的文件
        try:
            upload_path = Path(info['upload_path'])
            if upload_path.exists():
                upload_path.unlink()
        except Exception as e:
            print(f"删除上传文件失败: {e}")

        # 删除输出文件
        if info.get('output_path'):
            try:
                output_path = Path(info['output_path'])
                if output_path.exists():
                    output_path.unlink()
            except Exception as e:
                print(f"删除输出文件失败: {e}")

        # 从记录中删除
        del temp_files[file_id]
        return True

    def cleanup_expired_files(self) -> int:
        """清理过期文件"""
        expired_ids = []
        now = datetime.now()

        for file_id, info in temp_files.items():
            if now - info['upload_time'] > timedelta(hours=self.expiry_hours):
                expired_ids.append(file_id)

        for file_id in expired_ids:
            self.cleanup_file(file_id)

        return len(expired_ids)


# 创建管理器实例
temp_manager = TempFileManager()


def fill_pdf_fields(pdf_path: str, field_data: Dict[str, str]) -> str:
    """填写PDF表单字段"""
    # 读取PDF
    with open(pdf_path, 'rb') as pdf_file:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        pdf_writer = PyPDF2.PdfWriter()

        # 复制所有页面
        for page in pdf_reader.pages:
            pdf_writer.add_page(page)

        # 填写字段
        if pdf_reader.get_fields():
            pdf_writer.update_page_form_field_values(
                pdf_writer.pages[0],
                field_data
            )

        # 生成输出文件名
        output_filename = f"filled_{int(time.time())}.pdf"
        output_path = OUTPUT_DIR / output_filename

        # 保存填写后的PDF
        with open(output_path, 'wb') as output_file:
            pdf_writer.write(output_file)

    return str(output_path)


# API路由

@app.get("/", summary="Web界面")
async def root():
    """返回Web界面"""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "PDF表单智能解析和填写服务", "version": "2.0.0"}


@app.get("/api", summary="API状态")
async def api_status():
    """API状态检查"""
    return {
        "message": "API服务运行中",
        "version": "2.0.0",
        "features": ["阿里云视觉识别", "PDF字段解析", "在线表单填写"]
    }


@app.post("/upload-pdf", summary="上传PDF文件")
async def upload_pdf(file: UploadFile = File(...)):
    """
    上传PDF文件

    Returns:
        {"success": True, "file_id": "...", "message": "..."}
    """
    try:
        file_id = await temp_manager.save_uploaded_file(file)

        return {
            "success": True,
            "file_id": file_id,
            "message": f"文件上传成功: {file.filename}"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@app.post("/get-pdf-info", summary="获取PDF信息")
async def get_pdf_info(request: dict):
    """
    获取PDF基本信息（总页数等）

    Args:
        request: {"file_id": "..."}

    Returns:
        {"total_pages": ..., "file_name": "..."}
    """
    try:
        file_id = request.get("file_id")
        if not file_id:
            raise HTTPException(status_code=400, detail="缺少file_id参数")

        # 获取文件路径
        file_path = temp_manager.get_file_path(file_id)
        if not file_path:
            raise HTTPException(status_code=404, detail="文件不存在或已过期")

        # 获取PDF页数
        import fitz
        doc = fitz.open(file_path)
        total_pages = len(doc)
        doc.close()

        # 获取文件信息
        file_info = temp_manager.get_file_info(file_id)
        file_name = file_info.get('original_name', 'document.pdf') if file_info else 'document.pdf'

        return {
            "success": True,
            "total_pages": total_pages,
            "file_name": file_name
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取信息失败: {str(e)}")


@app.post("/parse-pdf-by-id", summary="根据文件ID解析PDF")
async def parse_pdf_by_id(request: dict):
    """
    根据文件ID解析PDF表单字段，使用阿里云视觉识别

    Args:
        request: {"file_id": "...", "page_num": 1}  # page_num从1开始

    Returns:
        {"fields": [...], "current_page": ..., "total_pages": ...}
    """
    try:
        file_id = request.get("file_id")
        page_num = request.get("page_num", 1)  # 默认第1页

        if not file_id:
            raise HTTPException(status_code=400, detail="缺少file_id参数")

        # 获取文件路径
        file_path = temp_manager.get_file_path(file_id)
        if not file_path:
            raise HTTPException(status_code=404, detail="文件不存在或已过期")

        # 获取总页数
        import fitz
        doc = fitz.open(file_path)
        total_pages = len(doc)
        doc.close()

        # 验证页码
        if page_num < 1 or page_num > total_pages:
            raise HTTPException(status_code=400, detail=f"页码超出范围（1-{total_pages}）")

        # 使用PDF字段提取器
        extractor = PDFFieldExtractor(file_path, output_dir=str(TEMP_DIR / file_id))

        # 处理PDF（page_num从1开始，转换为从0开始的索引）
        results = extractor.process(page_num=page_num - 1, use_vision=True)

        # 读取简化格式的字段数据
        simplified_file = Path(results['simplified_file'])
        if not simplified_file.exists():
            # 如果简化文件不存在，尝试读取完整文件并转换
            complete_file = Path(results['complete_file'])
            if complete_file.exists():
                with open(complete_file, 'r', encoding='utf-8') as f:
                    complete_data = json.load(f)

                # 转换为简化格式
                fields_data = []
                for field_name, field_info in complete_data.items():
                    fields_data.append({
                        "fieldName": field_name,
                        "fieldType": field_info.get("recognizedType") or field_info["fieldType"],
                        "text": field_info.get("label", "")
                    })
            else:
                fields_data = []
        else:
            with open(simplified_file, 'r', encoding='utf-8') as f:
                fields_data = json.load(f)

        # 转换为前端需要的格式
        fields = []
        for field in fields_data:
            fields.append({
                "name": field["fieldName"],
                "type": field["fieldType"].lower(),
                "label": field.get("text", ""),
                "required": False  # 默认非必填
            })

        return {
            "fields": fields,
            "current_page": page_num,
            "total_pages": total_pages
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")


@app.post("/fill-pdf-by-id", summary="根据文件ID填写PDF")
async def fill_pdf_by_id(request: dict):
    """
    根据文件ID填写PDF表单字段

    Args:
        request: {"file_id": "...", "field_data": {...}}

    Returns:
        {"success": True, "file_id": "...", "message": "..."}
    """
    try:
        file_id = request.get("file_id")
        field_data = request.get("field_data", {})

        if not file_id:
            raise HTTPException(status_code=400, detail="缺少file_id参数")

        # 获取文件路径
        file_path = temp_manager.get_file_path(file_id)
        if not file_path:
            raise HTTPException(status_code=404, detail="文件不存在或已过期")

        # 填写PDF字段
        output_path = fill_pdf_fields(file_path, field_data)

        # 注册输出文件
        temp_manager.register_output_file(file_id, output_path)

        return {
            "success": True,
            "file_id": file_id,
            "message": "PDF填写完成"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"填写失败: {str(e)}")


@app.get("/download/{file_id}", summary="下载填写完成的PDF")
async def download_pdf(file_id: str):
    """
    下载填写完成的PDF文件

    Args:
        file_id: 文件ID

    Returns:
        PDF文件
    """
    try:
        # 获取输出文件路径
        output_path = temp_manager.get_output_file(file_id)
        if not output_path or not Path(output_path).exists():
            raise HTTPException(status_code=404, detail="文件不存在或尚未处理完成")

        # 获取文件信息
        file_info = temp_manager.get_file_info(file_id)
        original_name = file_info['original_name'] if file_info else "document.pdf"

        # 生成下载文件名
        name_without_ext = Path(original_name).stem
        download_name = f"{name_without_ext}_filled.pdf"

        return FileResponse(
            path=output_path,
            filename=download_name,
            media_type="application/pdf"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")


@app.delete("/cleanup/{file_id}", summary="清理临时文件")
async def cleanup_files(file_id: str):
    """清理指定文件ID的所有相关临时文件"""
    try:
        success = temp_manager.cleanup_file(file_id)

        if success:
            return {"success": True, "message": "文件清理完成"}
        else:
            return {"success": False, "message": "文件不存在或已被清理"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")


@app.get("/cleanup-expired", summary="清理过期文件")
async def cleanup_expired_files():
    """清理所有过期的临时文件"""
    try:
        cleanup_count = temp_manager.cleanup_expired_files()

        return {
            "success": True,
            "cleanup_count": cleanup_count,
            "message": f"已清理 {cleanup_count} 个过期文件"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")


# 挂载静态文件服务（必须放在最后）
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


if __name__ == "__main__":
    import uvicorn

    print("="*80)
    print("PDF表单智能解析和填写服务")
    print("="*80)
    print(f"服务地址: http://127.0.0.1:8000")
    print(f"API文档: http://127.0.0.1:8000/docs")
    print("="*80)

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
