"""私家厨房 API：菜品上传、点菜、制作、备菜"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.auth import get_current_user
from app.schemas import (
    ApiResponse,
    PrivateKitchenDishCreate,
    PrivateKitchenDishUpdate,
    KitchenSelectionCreate,
)
from app.services import private_kitchen as pk_svc

router = APIRouter(prefix="/api/private-kitchen", tags=["私家厨房"])


# ─── 菜品管理 ───

@router.get("/dishes", summary="获取私家厨房菜品列表", response_model=ApiResponse)
async def list_dishes(
    page: int = 1,
    size: int = 20,
    keyword: Optional[str] = None,
    db=Depends(get_db),
    _: int = Depends(get_current_user),
):
    result = await pk_svc.list_dishes(db, page, size, keyword)
    return ApiResponse(data=result)


@router.get("/dishes/{dish_id}", summary="获取菜品详情", response_model=ApiResponse)
async def get_dish(dish_id: int, db=Depends(get_db), _: int = Depends(get_current_user)):
    dish = await pk_svc.get_dish(db, dish_id)
    if not dish:
        raise HTTPException(404, "菜品不存在")
    return ApiResponse(data=dish)


@router.post("/dishes", summary="上传菜品（Markdown 菜谱、图片、食材）", response_model=ApiResponse)
async def create_dish(
    body: PrivateKitchenDishCreate,
    db=Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    ingredients = [i.model_dump() for i in body.ingredients]
    dish_id = await pk_svc.create_dish(
        db, user_id, body.name, body.recipe, body.recipe_url, body.images, ingredients
    )
    dish = await pk_svc.get_dish(db, dish_id)
    return ApiResponse(data=dish)


@router.put("/dishes/{dish_id}", summary="更新菜品", response_model=ApiResponse)
async def update_dish(
    dish_id: int,
    body: PrivateKitchenDishUpdate,
    db=Depends(get_db),
    _: int = Depends(get_current_user),
):
    existing = await pk_svc.get_dish(db, dish_id)
    if not existing:
        raise HTTPException(404, "菜品不存在")
    ingredients = [i.model_dump() for i in body.ingredients] if body.ingredients is not None else None
    await pk_svc.update_dish(
        db, dish_id,
        name=body.name,
        recipe=body.recipe,
        recipe_url=body.recipe_url,
        images=body.images,
        ingredients=ingredients,
    )
    dish = await pk_svc.get_dish(db, dish_id)
    return ApiResponse(data=dish)


@router.delete("/dishes/{dish_id}", summary="删除菜品", response_model=ApiResponse)
async def delete_dish(dish_id: int, db=Depends(get_db), _: int = Depends(get_current_user)):
    existing = await pk_svc.get_dish(db, dish_id)
    if not existing:
        raise HTTPException(404, "菜品不存在")
    await pk_svc.delete_dish(db, dish_id)
    return ApiResponse(message="删除成功")


# ─── 点菜（加入制作计划） ───

@router.post("/selections", summary="点菜（将菜品加入制作计划）", response_model=ApiResponse)
async def add_selection(
    body: KitchenSelectionCreate,
    db=Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    sel_id, err = await pk_svc.add_selection(db, user_id, body.dish_id)
    if err:
        raise HTTPException(400, err)
    selections = await pk_svc.list_selections(db)
    sel = next((s for s in selections if s.get("id") == sel_id), None)
    return ApiResponse(data=sel, message="已加入制作计划")


@router.delete("/selections/{selection_id}", summary="从制作计划中移除菜品", response_model=ApiResponse)
async def remove_selection(
    selection_id: int,
    db=Depends(get_db),
    _: int = Depends(get_current_user),
):
    ok = await pk_svc.remove_selection(db, selection_id)
    if not ok:
        raise HTTPException(404, "该菜品不在制作计划中")
    return ApiResponse(message="已移除")


# ─── 制作接口（查看当前计划中的菜品详情） ───

@router.get("/selections", summary="制作接口：查看当前计划中的菜品（含食材、菜谱、图片）", response_model=ApiResponse)
async def list_selections(db=Depends(get_db), _: int = Depends(get_current_user)):
    items = await pk_svc.list_selections(db)
    return ApiResponse(data=items)


# ─── 备菜接口 ───

@router.get("/ingredients", summary="备菜接口：当前计划所需食材汇总", response_model=ApiResponse)
async def get_aggregated_ingredients(db=Depends(get_db), _: int = Depends(get_current_user)):
    items = await pk_svc.get_aggregated_ingredients(db)
    return ApiResponse(data=items)
