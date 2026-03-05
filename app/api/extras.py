from typing import Optional

from fastapi import APIRouter, Depends

from app.database import get_db
from app.auth import get_current_user
from app.schemas import ApiResponse
from app.services import extras as extras_svc

router = APIRouter(prefix="/api", tags=["其他功能"])


@router.get("/moods/statistics", summary="获取情绪统计", response_model=ApiResponse)
async def mood_statistics(startDate: Optional[str] = None, endDate: Optional[str] = None,
                          db=Depends(get_db), _: int = Depends(get_current_user)):
    stats = await extras_svc.get_mood_statistics(db, startDate, endDate)
    return ApiResponse(data=stats)


@router.get("/recommendations", summary="随机推荐菜品", response_model=ApiResponse)
async def recommendations(
    restaurant: Optional[str] = None,
    mood: Optional[str] = None,
    count: int = 3,
    db=Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    items = await extras_svc.get_recommendations(
        db, restaurant=restaurant, mood=mood, user_id=user_id, count=count,
    )
    return ApiResponse(data=items)


@router.get("/surprise-mode/status", summary="获取惊喜模式状态", response_model=ApiResponse)
async def surprise_status(db=Depends(get_db), _: int = Depends(get_current_user)):
    status = await extras_svc.get_surprise_status(db)
    return ApiResponse(data=status)


@router.get("/dashboard", summary="获取首页仪表盘数据", response_model=ApiResponse)
async def dashboard(db=Depends(get_db), _: int = Depends(get_current_user)):
    data = await extras_svc.get_dashboard(db)
    return ApiResponse(data=data)
