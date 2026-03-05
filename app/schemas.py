from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any, Literal, Optional

MOOD_VALUES = Literal["冷", "暖", "躁", "甜"]


# ───────────── 通用响应 ─────────────

class ApiResponse(BaseModel):
    code: int = 200
    data: Any = None
    message: str = "ok"


class PaginatedData(BaseModel):
    items: list = []
    total: int = 0
    page: int = 1
    size: int = 20


# ───────────── 用户 ─────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    nickname: Optional[str] = None


class TokenResponse(BaseModel):
    token: str
    user_id: int


class UserInfo(BaseModel):
    id: int
    username: str
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    created_at: Optional[str] = None


class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    avatar: Optional[str] = None


# ───────────── 偏好 ─────────────

class PreferenceInfo(BaseModel):
    user_id: int
    dislikes: list[str] = []
    likes: list[str] = []


class PreferenceUpdate(BaseModel):
    dislikes: list[str] = []
    likes: list[str] = []


# ───────────── 纪念日 ─────────────

class AnniversaryCreate(BaseModel):
    name: str
    date: str
    description: Optional[str] = None
    is_recurring: int = 0
    remind_days: int = 3


class AnniversaryUpdate(BaseModel):
    name: Optional[str] = None
    date: Optional[str] = None
    description: Optional[str] = None
    is_recurring: Optional[int] = None
    remind_days: Optional[int] = None


class AnniversaryInfo(BaseModel):
    id: int
    name: str
    date: str
    description: Optional[str] = None
    is_recurring: int = 0
    remind_days: int = 3
    days_until: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ───────────── 菜品 ─────────────

class DishCreate(BaseModel):
    name: str
    price: Optional[float] = None
    ordered_by: Optional[int] = None
    notes: Optional[str] = None


class DishInfo(BaseModel):
    id: int
    order_id: int
    dish_name: str
    price: Optional[float] = None
    ordered_by: Optional[int] = None
    notes: Optional[str] = None


# ───────────── 订单 ─────────────

class MoodInput(BaseModel):
    user1: Optional[MOOD_VALUES] = None
    user2: Optional[MOOD_VALUES] = None


class OrderCreate(BaseModel):
    restaurant: str
    address: Optional[str] = None
    date: str
    dishes: list[DishCreate] = []
    moods: Optional[MoodInput] = None
    notes: Optional[str] = None


class OrderUpdate(BaseModel):
    restaurant: Optional[str] = None
    address: Optional[str] = None
    date: Optional[str] = None
    dishes: Optional[list[DishCreate]] = None
    moods: Optional[MoodInput] = None
    notes: Optional[str] = None


class OrderInfo(BaseModel):
    id: int
    restaurant: str
    address: Optional[str] = None
    order_date: Optional[str] = None
    mood_user1: Optional[str] = None
    mood_user2: Optional[str] = None
    notes: Optional[str] = None
    dishes: list = []
    created_at: Optional[str] = None


# ───────────── 忌口校验 ─────────────

class ValidateDish(BaseModel):
    name: str
    ordered_for: Optional[int] = None


class ValidateRequest(BaseModel):
    dishes: list[ValidateDish]


class ConflictItem(BaseModel):
    dish_name: str
    user_id: int
    nickname: str
    conflicts: list[str]


# ───────────── 成就 ─────────────

class AchievementInfo(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    criteria: Optional[str] = None
    badge_icon: Optional[str] = None


class UserAchievementInfo(BaseModel):
    achievement: AchievementInfo
    progress: int = 0
    unlocked_at: Optional[str] = None


# ───────────── 爱情币 ─────────────

class LoveCoinBalance(BaseModel):
    user_id: int
    balance: int


class TransactionInfo(BaseModel):
    id: int
    amount: int
    type: str
    reference_id: Optional[int] = None
    description: Optional[str] = None
    created_at: Optional[str] = None


class RedeemItemInfo(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    cost: int
    icon: Optional[str] = None
    star_level: int = 0
    is_active: bool = True


class RedeemRequest(BaseModel):
    itemId: int


class SynthesizeRequest(BaseModel):
    itemIds: list[int]


class InventoryItem(BaseModel):
    redemption_id: int
    item_name: str
    description: Optional[str] = None
    star_level: int = 0
    icon: Optional[str] = None
    status: str
    redeemed_at: Optional[str] = None


# ───────────── 盲猜价格 ─────────────

class PriceGuessInit(BaseModel):
    hidden_dish_id: Optional[int] = None


class PriceGuessSubmit(BaseModel):
    guess: float


class PriceGuessStatus(BaseModel):
    order_id: int
    hidden_dish: Optional[dict] = None
    user1_guessed: bool = False
    user2_guessed: bool = False
    completed: bool = False


class PriceGuessResult(BaseModel):
    actual_price: float
    guess_user1: Optional[float] = None
    guess_user2: Optional[float] = None
    result: str
    reward: Optional[str] = None


# ───────────── 味觉日记 ─────────────

class DiaryCreate(BaseModel):
    content: Optional[str] = None
    images: list[str] = []
    rating: Optional[int] = None


class DiaryUpdate(BaseModel):
    content: Optional[str] = None
    images: Optional[list[str]] = None
    rating: Optional[int] = None


class DiaryInfo(BaseModel):
    id: int
    order_id: int
    content: Optional[str] = None
    images: list[str] = []
    rating: Optional[int] = None
    restaurant: Optional[str] = None
    order_date: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TasteMapPoint(BaseModel):
    restaurant: str
    address: Optional[str] = None
    visit_count: int
    avg_rating: Optional[float] = None
    last_visit: Optional[str] = None
    dishes: list[str] = []


# ───────────── 情绪统计 ─────────────

class MoodStat(BaseModel):
    mood: str
    count: int


class MoodStatistics(BaseModel):
    user1: list[MoodStat] = []
    user2: list[MoodStat] = []


# ───────────── 仪表盘 ─────────────

class DashboardData(BaseModel):
    upcoming_anniversaries: list = []
    love_coin_balances: list = []
    recent_orders: list = []
    latest_achievements: list = []
    total_orders: int = 0
    total_restaurants: int = 0


# ───────────── 惊喜模式 ─────────────

class SurpriseStatus(BaseModel):
    active: bool = False
    anniversary: Optional[dict] = None
    message: Optional[str] = None


# ───────────── 私家厨房 ─────────────

class IngredientInput(BaseModel):
    name: str
    amount: Optional[str] = None
    unit: Optional[str] = ""


class PrivateKitchenDishCreate(BaseModel):
    name: str
    recipe: Optional[str] = Field(None, description="Markdown 格式菜谱，可使用 ![](/uploads/xxx.png) 引用图片")
    recipe_url: Optional[str] = Field(None, description="可选，上传的 .md 菜谱文档 URL，请求 /api/upload 后填入")
    images: list[str] = Field(default_factory=list, description="图片 URL 列表，先通过 /api/upload 上传后填入")
    ingredients: list[IngredientInput] = []


class PrivateKitchenDishUpdate(BaseModel):
    name: Optional[str] = None
    recipe: Optional[str] = Field(None, description="Markdown 格式菜谱")
    recipe_url: Optional[str] = Field(None, description="上传的 .md 菜谱文档 URL")
    images: Optional[list[str]] = Field(None, description="图片 URL 列表")
    ingredients: Optional[list[IngredientInput]] = None


class DishIngredientInfo(BaseModel):
    id: int
    name: str
    amount: Optional[str] = None
    unit: Optional[str] = None


class PrivateKitchenDishInfo(BaseModel):
    id: int
    name: str
    recipe: Optional[str] = None
    recipe_url: Optional[str] = None
    images: list[str] = []
    ingredients: list[DishIngredientInfo] = []
    created_by: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class KitchenSelectionCreate(BaseModel):
    dish_id: int


class KitchenSelectionInfo(BaseModel):
    id: int
    dish_id: int
    dish: Optional[dict] = None
    selected_by: int
    created_at: Optional[str] = None


class AggregatedIngredient(BaseModel):
    name: str
    amount: Optional[str] = None
    unit: Optional[str] = None
    total_numeric: Optional[float] = None
    sources: list[dict] = []
