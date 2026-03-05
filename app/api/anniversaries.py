from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.auth import get_current_user
from app.schemas import AnniversaryCreate, AnniversaryUpdate, ApiResponse
from app.services import anniversary as ann_svc

router = APIRouter(prefix="/api/anniversaries", tags=["纪念日"])


@router.get("", summary="获取所有纪念日", response_model=ApiResponse)
async def list_anniversaries(db=Depends(get_db), _: int = Depends(get_current_user)):
    items = await ann_svc.list_anniversaries(db)
    return ApiResponse(data=items)


@router.post("", summary="新增纪念日", response_model=ApiResponse)
async def create_anniversary(body: AnniversaryCreate, db=Depends(get_db),
                             _: int = Depends(get_current_user)):
    ann_id = await ann_svc.create_anniversary(
        db, body.name, body.date, body.description, body.is_recurring, body.remind_days
    )
    ann = await ann_svc.get_anniversary(db, ann_id)
    return ApiResponse(data=ann)


@router.get("/upcoming", summary="获取即将到来的纪念日", response_model=ApiResponse)
async def upcoming_anniversaries(days: int = 7, db=Depends(get_db),
                                 _: int = Depends(get_current_user)):
    items = await ann_svc.list_anniversaries(db, upcoming_only=True, days=days)
    return ApiResponse(data=items)


@router.put("/{ann_id}", summary="修改纪念日", response_model=ApiResponse)
async def update_anniversary(ann_id: int, body: AnniversaryUpdate, db=Depends(get_db),
                             _: int = Depends(get_current_user)):
    existing = await ann_svc.get_anniversary(db, ann_id)
    if not existing:
        raise HTTPException(404, "纪念日不存在")
    updates = body.model_dump(exclude_none=True)
    await ann_svc.update_anniversary(db, ann_id, **updates)
    ann = await ann_svc.get_anniversary(db, ann_id)
    return ApiResponse(data=ann)


@router.delete("/{ann_id}", summary="删除纪念日", response_model=ApiResponse)
async def delete_anniversary(ann_id: int, db=Depends(get_db),
                             _: int = Depends(get_current_user)):
    await ann_svc.delete_anniversary(db, ann_id)
    return ApiResponse(message="删除成功")
