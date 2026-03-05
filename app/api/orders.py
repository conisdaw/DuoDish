from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.auth import get_current_user
from app.config import LOVE_COIN_PER_ORDER
from app.schemas import OrderCreate, OrderUpdate, ValidateRequest, ApiResponse
from app.services import order as order_svc
from app.services import achievement as ach_svc
from app.services import love_bank as lb_svc

router = APIRouter(prefix="/api/orders", tags=["点餐"])


@router.get("", summary="获取点餐记录列表", response_model=ApiResponse)
async def list_orders(
    page: int = 1,
    size: int = 20,
    startDate: Optional[str] = None,
    endDate: Optional[str] = None,
    restaurant: Optional[str] = None,
    db=Depends(get_db),
    _: int = Depends(get_current_user),
):
    result = await order_svc.list_orders(db, page, size, startDate, endDate, restaurant)
    return ApiResponse(data=result)


@router.post("", summary="创建新点餐记录", response_model=ApiResponse)
async def create_order(body: OrderCreate, db=Depends(get_db),
                       current_user: int = Depends(get_current_user)):
    mood_u1 = body.moods.user1 if body.moods else None
    mood_u2 = body.moods.user2 if body.moods else None
    dishes = [d.model_dump() for d in body.dishes]

    order_id = await order_svc.create_order(
        db, body.restaurant, body.date, body.address,
        mood_u1, mood_u2, body.notes, dishes,
    )

    await lb_svc.deposit(
        db, current_user, LOVE_COIN_PER_ORDER,
        "order_deposit", order_id, f"点餐存入: {body.restaurant}",
    )
    await ach_svc.check_achievements(db, current_user)

    order = await order_svc.get_order(db, order_id)
    return ApiResponse(data=order)


@router.get("/{order_id}", summary="获取单次点餐详情", response_model=ApiResponse)
async def get_order(order_id: int, db=Depends(get_db),
                    _: int = Depends(get_current_user)):
    order = await order_svc.get_order(db, order_id)
    if not order:
        raise HTTPException(404, "订单不存在")
    return ApiResponse(data=order)


@router.put("/{order_id}", summary="更新点餐记录", response_model=ApiResponse)
async def update_order(order_id: int, body: OrderUpdate, db=Depends(get_db),
                       _: int = Depends(get_current_user)):
    existing = await order_svc.get_order(db, order_id)
    if not existing:
        raise HTTPException(404, "订单不存在")

    updates = {}
    if body.restaurant is not None:
        updates["restaurant"] = body.restaurant
    if body.address is not None:
        updates["address"] = body.address
    if body.date is not None:
        updates["date"] = body.date
    if body.notes is not None:
        updates["notes"] = body.notes
    if body.moods is not None:
        updates["moods"] = body.moods.model_dump()
    if body.dishes is not None:
        updates["dishes"] = [d.model_dump() for d in body.dishes]

    await order_svc.update_order(db, order_id, **updates)
    order = await order_svc.get_order(db, order_id)
    return ApiResponse(data=order)


@router.delete("/{order_id}", summary="删除点餐记录", response_model=ApiResponse)
async def delete_order(order_id: int, db=Depends(get_db),
                       _: int = Depends(get_current_user)):
    await order_svc.delete_order(db, order_id)
    return ApiResponse(message="删除成功")


@router.post("/validate", summary="忌口冲突校验", response_model=ApiResponse)
async def validate_dishes(body: ValidateRequest, db=Depends(get_db),
                          _: int = Depends(get_current_user)):
    dishes = [d.model_dump() for d in body.dishes]
    conflicts = await order_svc.validate_dishes(db, dishes)
    if conflicts:
        return ApiResponse(code=200, data=conflicts, message="发现忌口冲突")
    return ApiResponse(data=[], message="没有忌口冲突")
