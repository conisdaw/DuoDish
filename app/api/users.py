from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.auth import get_current_user
from app.schemas import UserUpdate, PreferenceUpdate, ApiResponse
from app.services import user as user_svc

router = APIRouter(prefix="/api/users", tags=["用户"])


@router.get("/me", summary="获取当前用户信息", response_model=ApiResponse)
async def get_user(db=Depends(get_db), user_id: int = Depends(get_current_user)):
    user = await user_svc.get_user(db, user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    data = dict(user)
    data.pop("password_hash", None)
    data.pop("dingtalk", None)  # 加签密钥，敏感信息不返回
    return ApiResponse(data=data)


@router.put("/me", summary="更新当前用户信息", response_model=ApiResponse)
async def update_user(body: UserUpdate, db=Depends(get_db),
                      user_id: int = Depends(get_current_user)):
    await user_svc.update_user(db, user_id,
                               nickname=body.nickname, avatar=body.avatar,
                               dingtalk=body.dingtalk, webhookUrl=body.webhookUrl)
    user = await user_svc.get_user(db, user_id)
    data = dict(user)
    data.pop("password_hash", None)
    data.pop("dingtalk", None)  # 加签密钥，敏感信息不返回
    return ApiResponse(data=data)


@router.get("/me/preferences", summary="获取双方偏好（含对方忌口）", response_model=ApiResponse)
async def get_preferences(db=Depends(get_db), user_id: int = Depends(get_current_user)):
    mine = await user_svc.get_preferences(db, user_id)
    partner_id = await user_svc.get_partner_id(db, user_id)
    partner = await user_svc.get_preferences(db, partner_id) if partner_id else None
    return ApiResponse(data={"mine": mine, "partner": partner})


@router.put("/me/preferences", summary="更新当前用户偏好（忌口与喜好）", response_model=ApiResponse)
async def update_preferences(body: PreferenceUpdate, db=Depends(get_db),
                             user_id: int = Depends(get_current_user)):
    await user_svc.update_preferences(db, user_id, body.dislikes, body.likes)
    prefs = await user_svc.get_preferences(db, user_id)
    return ApiResponse(data=prefs)
