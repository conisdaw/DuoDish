import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from app.auth import get_current_user
from app.config import UPLOAD_DIR
from app.schemas import ApiResponse

router = APIRouter(prefix="/api", tags=["文件上传"])

ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg",
    ".md", ".markdown",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def _validate_file(file: UploadFile) -> str:
    if not file.filename:
        raise HTTPException(400, "文件名不能为空")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            f"不支持的文件类型 '{ext}'，允许: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    return ext


@router.post("/upload", summary="上传文件（图片/Markdown）", response_model=ApiResponse)
async def upload_file(
    file: UploadFile = File(...),
    _: int = Depends(get_current_user),
):
    ext = _validate_file(file)

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, f"文件大小超过限制（最大 {MAX_FILE_SIZE // 1024 // 1024}MB）")

    date_dir = datetime.now().strftime("%Y%m")
    save_dir = os.path.join(UPLOAD_DIR, date_dir)
    os.makedirs(save_dir, exist_ok=True)

    unique_name = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(save_dir, unique_name)
    with open(filepath, "wb") as f:
        f.write(content)

    url = f"/uploads/{date_dir}/{unique_name}"
    return ApiResponse(data={
        "url": url,
        "filename": file.filename,
        "size": len(content),
        "content_type": file.content_type,
    })


@router.post("/upload/batch", summary="批量上传文件", response_model=ApiResponse)
async def upload_files(
    files: list[UploadFile] = File(...),
    _: int = Depends(get_current_user),
):
    if len(files) > 9:
        raise HTTPException(400, "单次最多上传 9 个文件")

    results = []
    for file in files:
        ext = _validate_file(file)

        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(400, f"文件 '{file.filename}' 大小超过限制（最大 {MAX_FILE_SIZE // 1024 // 1024}MB）")

        date_dir = datetime.now().strftime("%Y%m")
        save_dir = os.path.join(UPLOAD_DIR, date_dir)
        os.makedirs(save_dir, exist_ok=True)

        unique_name = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(save_dir, unique_name)
        with open(filepath, "wb") as f:
            f.write(content)

        results.append({
            "url": f"/uploads/{date_dir}/{unique_name}",
            "filename": file.filename,
            "size": len(content),
            "content_type": file.content_type,
        })

    return ApiResponse(data=results)
