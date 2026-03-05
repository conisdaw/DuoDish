from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.auth import get_current_user
from app.schemas import PriceGuessInit, PriceGuessSubmit, ApiResponse
from app.services import game as game_svc

router = APIRouter(prefix="/api/orders/{order_id}/price-guess", tags=["盲猜价格"])


@router.post("/init", summary="初始化盲猜游戏", response_model=ApiResponse)
async def init_game(order_id: int, body: PriceGuessInit = PriceGuessInit(),
                    db=Depends(get_db), _: int = Depends(get_current_user)):
    try:
        await game_svc.init_game(db, order_id, body.hidden_dish_id)
        return ApiResponse(message="盲猜游戏已创建")
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("", summary="获取盲猜游戏状态", response_model=ApiResponse)
async def get_status(order_id: int, db=Depends(get_db),
                     _: int = Depends(get_current_user)):
    status = await game_svc.get_game_status(db, order_id)
    if not status:
        raise HTTPException(404, "该订单没有盲猜游戏")
    return ApiResponse(data=status)


@router.post("", summary="提交价格猜测", response_model=ApiResponse)
async def submit_guess(order_id: int, body: PriceGuessSubmit, db=Depends(get_db),
                       user_id: int = Depends(get_current_user)):
    try:
        await game_svc.submit_guess(db, order_id, user_id, body.guess)
        return ApiResponse(message="猜测已提交")
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("", summary="重置盲猜游戏", response_model=ApiResponse)
async def reset_game(order_id: int, db=Depends(get_db),
                     _: int = Depends(get_current_user)):
    try:
        await game_svc.reset_game(db, order_id)
        return ApiResponse(message="盲猜游戏已重置，可重新初始化")
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/result", summary="揭晓盲猜结果", response_model=ApiResponse)
async def get_result(order_id: int, db=Depends(get_db),
                     _: int = Depends(get_current_user)):
    try:
        result = await game_svc.get_result(db, order_id)
        return ApiResponse(data=result)
    except ValueError as e:
        raise HTTPException(400, str(e))
