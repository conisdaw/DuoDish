from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.auth import get_current_user
from app.schemas import ApiResponse, DiaryCreate, DiaryUpdate
from app.services import diary as diary_svc

router = APIRouter(prefix="/api", tags=["味觉日记"])


@router.get("/taste-diary", summary="获取味觉日记列表", response_model=ApiResponse)
async def list_diaries(page: int = 1, size: int = 20, db=Depends(get_db),
                       _: int = Depends(get_current_user)):
    result = await diary_svc.list_diaries(db, page, size)
    return ApiResponse(data=result)


@router.get("/taste-diary/{diary_id}", summary="获取单篇日记详情", response_model=ApiResponse)
async def get_diary(diary_id: int, db=Depends(get_db),
                    _: int = Depends(get_current_user)):
    d = await diary_svc.get_diary(db, diary_id)
    if not d:
        raise HTTPException(404, "日记不存在")
    return ApiResponse(data=d)


@router.post("/orders/{order_id}/diary", summary="为点餐添加味觉日记", response_model=ApiResponse)
async def create_diary(
    order_id: int,
    body: DiaryCreate,
    db=Depends(get_db),
    _: int = Depends(get_current_user),
):
    diary_id = await diary_svc.create_diary(db, order_id, body.content, body.rating, body.images)
    d = await diary_svc.get_diary(db, diary_id)
    return ApiResponse(data=d)


@router.put("/taste-diary/{diary_id}", summary="更新味觉日记", response_model=ApiResponse)
async def update_diary(
    diary_id: int,
    body: DiaryUpdate,
    db=Depends(get_db),
    _: int = Depends(get_current_user),
):
    existing = await diary_svc.get_diary(db, diary_id)
    if not existing:
        raise HTTPException(404, "日记不存在")
    await diary_svc.update_diary(db, diary_id, body.content, body.rating, body.images)
    d = await diary_svc.get_diary(db, diary_id)
    return ApiResponse(data=d)


@router.get("/taste-map/points", summary="获取味觉地图标记点", response_model=ApiResponse)
async def taste_map(restaurant: Optional[str] = None, db=Depends(get_db),
                    _: int = Depends(get_current_user)):
    points = await diary_svc.get_taste_map(db, restaurant)
    return ApiResponse(data=points)
