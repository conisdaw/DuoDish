from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.auth import get_current_user
from app.schemas import RedeemRequest, SynthesizeRequest, ApiResponse
from app.services import love_bank as lb_svc

router = APIRouter(prefix="/api", tags=["爱情银行"])


@router.get("/users/me/love-coins", summary="查询当前用户爱情币余额", response_model=ApiResponse)
async def get_balance(db=Depends(get_db), user_id: int = Depends(get_current_user)):
    balance = await lb_svc.get_balance(db, user_id)
    return ApiResponse(data={"user_id": user_id, "balance": balance})


@router.get("/users/me/love-coin-transactions", summary="获取当前用户爱情币流水", response_model=ApiResponse)
async def get_transactions(page: int = 1, size: int = 20,
                           db=Depends(get_db), user_id: int = Depends(get_current_user)):
    result = await lb_svc.get_transactions(db, user_id, page, size)
    return ApiResponse(data=result)


@router.get("/redeem-items", summary="获取可兑换特权列表", response_model=ApiResponse)
async def list_redeem_items(db=Depends(get_db), _: int = Depends(get_current_user)):
    items = await lb_svc.list_redeem_items(db)
    return ApiResponse(data=items)


@router.post("/redeem", summary="兑换特权物品", response_model=ApiResponse)
async def redeem(body: RedeemRequest, db=Depends(get_db),
                 user_id: int = Depends(get_current_user)):
    try:
        rid = await lb_svc.redeem_item(db, user_id, body.itemId)
        return ApiResponse(data={"redemption_id": rid}, message="兑换成功")
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/redeem/synthesize", summary="合成不生气券", response_model=ApiResponse)
async def synthesize(body: SynthesizeRequest, db=Depends(get_db),
                     user_id: int = Depends(get_current_user)):
    try:
        rid = await lb_svc.synthesize(db, user_id, body.itemIds)
        return ApiResponse(data={"redemption_id": rid}, message="合成成功")
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/users/me/inventory", summary="查看当前用户物品背包", response_model=ApiResponse)
async def get_inventory(db=Depends(get_db), user_id: int = Depends(get_current_user)):
    items = await lb_svc.get_inventory(db, user_id)
    return ApiResponse(data=items)
