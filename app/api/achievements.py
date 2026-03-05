from fastapi import APIRouter, Depends

from app.database import get_db
from app.auth import get_current_user
from app.schemas import ApiResponse
from app.services import achievement as ach_svc

router = APIRouter(prefix="/api", tags=["成就"])


@router.get("/achievements", summary="获取所有成就定义", response_model=ApiResponse)
async def list_achievements(db=Depends(get_db), _: int = Depends(get_current_user)):
    items = await ach_svc.list_achievements(db)
    return ApiResponse(data=items)


@router.get("/users/me/achievements", summary="获取当前用户成就进度", response_model=ApiResponse)
async def get_user_achievements(db=Depends(get_db), user_id: int = Depends(get_current_user)):
    items = await ach_svc.get_user_achievements(db, user_id)
    return ApiResponse(data=items)
