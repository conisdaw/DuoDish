# DuoDish — 情侣点餐互动后端 API

DuoDish 是一个专为情侣设计的美食记录与互动平台后端服务，基于 **FastAPI + SQLite** 构建。支持共同点餐记录、味觉日记、盲猜价格游戏、爱情银行、纪念日管理、私家厨房等功能。

## 快速开始

### 环境要求

- Python 3.11+
- pip

### 安装与运行

```bash
# 1. 创建虚拟环境
python -m venv .venv

# 2. 激活虚拟环境
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动服务
python main.py
```

服务默认运行在 `http://127.0.0.1:8000`，访问 `/docs` 查看 Swagger UI 交互式文档。

### 填充测试数据

```bash
# 拉取 HowToCook 菜谱（私家厨房需要）
python scripts/setup_howtocook.py

# 填充测试数据（用户、订单、纪念日等）
python test/seed.py

# 迁移 HowToCook 全部菜谱到私家厨房（356+ 道）
python scripts/migrate_howtocook.py
```

会创建两个测试账号（密码均为 `123456`）：

| 用户名 | 昵称 | 爱情币 |
|--------|------|--------|
| alice  | 小爱 | 2000   |
| bob    | 阿宝 | 1500   |

同时填充 6 个纪念日、7 条点餐记录（28 道菜）、5 篇味觉日记、1 局待猜价游戏、成就进度、兑换记录等完整测试数据。

---

## 项目结构

```
DuoDish/
├── app/
│   ├── main.py            # FastAPI 应用入口、路由注册、异常处理
│   ├── config.py          # 配置项（密钥、数据库路径等）
│   ├── auth.py            # JWT 鉴权与密码哈希
│   ├── database.py        # 数据库连接与初始化
│   ├── schemas.py         # Pydantic 请求/响应模型
│   ├── api/               # 路由层
│   │   ├── auth.py        # 注册、登录
│   │   ├── users.py       # 用户信息、偏好
│   │   ├── upload.py      # 文件上传
│   │   ├── anniversaries.py # 纪念日管理
│   │   ├── orders.py      # 点餐记录、忌口校验
│   │   ├── games.py       # 盲猜价格游戏
│   │   ├── diary.py       # 味觉日记
│   │   ├── achievements.py # 成就系统
│   │   ├── love_bank.py   # 爱情银行
│   │   ├── private_kitchen.py # 私家厨房
│   │   └── extras.py      # 推荐、惊喜模式、情绪统计、仪表盘
│   └── services/          # 业务逻辑层
│       ├── user.py
│       ├── anniversary.py
│       ├── order.py
│       ├── game.py
│       ├── diary.py
│       ├── achievement.py
│       ├── love_bank.py
│       ├── private_kitchen.py
│       └── extras.py
├── migrations/
│   └── init.sql           # 数据库初始化脚本（建表、种子数据）
├── uploads/               # 上传文件存储目录
├── test/                  # 测试目录
│   ├── conftest.py        # pytest 配置与 fixtures
│   ├── test_api.py        # Python 自动化测试脚本
│   ├── test_main.http     # JetBrains HTTP Client 测试文件
│   ├── test_image/        # 测试用图片
│   └── seed.py            # 测试数据填充脚本
├── main.py                # 启动入口（调用 uvicorn）
└── requirements.txt       # 依赖清单
```

---

## 配置项

通过环境变量覆盖，默认值见 `app/config.py`：

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `SECRET_KEY` | `duodish-secret-change-in-production` | JWT 签名密钥 |
| `DB_PATH` | `duodish.db` | SQLite 数据库文件路径 |

| 内部常量 | 值 | 说明 |
|----------|-----|------|
| `ALGORITHM` | `HS256` | JWT 算法 |
| `TOKEN_EXPIRE_DAYS` | `7` | Token 有效期（天） |
| `UPLOAD_DIR` | `uploads` | 上传文件存储目录 |
| `LOVE_COIN_PER_ORDER` | `10` | 每次点餐获得的爱情币 |
| `LOVE_COIN_FOR_PARTNER_DISH` | `5` | 为对方点菜额外获得的爱情币 |

---

## 认证机制

采用 **JWT Bearer Token** 认证：

1. 通过 `/api/auth/login` 或 `/api/auth/register` 获取 Token
2. 后续请求在 Header 中携带：`Authorization: Bearer <token>`
3. Token 中包含 `user_id`，所有 `/me` 接口自动识别当前用户身份

密码采用 **SHA256 + 随机盐值** 哈希存储，格式为 `{salt}${hash}`。

---

## 统一响应格式

所有接口返回统一的 JSON 结构：

```json
{
  "code": 200,
  "data": { ... },
  "message": "ok"
}
```

| 状态码 | 说明 |
|--------|------|
| `200` | 成功 |
| `400` | 业务错误（如游戏已结束、余额不足） |
| `401` | 未认证或 Token 无效 |
| `403` | 权限不足（如超过两人注册限制） |
| `404` | 资源不存在 |
| `422` | 参数校验失败 |
| `500` | 服务器内部错误 |

---

## API 接口文档

### 1. 用户认证

无需 Token。系统限制最多注册 **2 名用户**（情侣双人制）。

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/auth/register` | 用户注册 |
| `POST` | `/api/auth/login` | 用户登录 |

**注册 / 登录请求体：**

```json
{
  "username": "alice",
  "password": "123456",
  "nickname": "小爱"       // 注册时可选
}
```

**响应 `data`：**

```json
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "user_id": 1
}
```

---

### 2. 用户信息与偏好

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/users/me` | 获取当前用户信息 |
| `PUT` | `/api/users/me` | 更新昵称和头像 |
| `GET` | `/api/users/me/preferences` | 获取双方偏好（含对方忌口） |
| `PUT` | `/api/users/me/preferences` | 更新忌口与喜好 |

**更新用户信息：**

```json
{
  "nickname": "小爱",
  "avatar": "/uploads/202603/abc123.png"
}
```

**更新偏好：**

```json
{
  "dislikes": ["香菜", "葱", "芥末"],
  "likes": ["辣", "麻", "川菜"]
}
```

**获取偏好响应 `data`（同时返回对方忌口）：**

```json
{
  "mine": { "user_id": 1, "dislikes": ["香菜", "葱"], "likes": ["辣", "麻"] },
  "partner": { "user_id": 2, "dislikes": ["辣", "花椒"], "likes": ["甜品", "日料"] }
}
```

---

### 3. 文件上传

支持图片和 Markdown 文件上传。先上传获取 URL，再在其他接口中引用。

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/upload` | 单文件上传 |
| `POST` | `/api/upload/batch` | 批量上传（最多 9 个） |

**限制：**

| 项目 | 限制 |
|------|------|
| 允许类型 | `.jpg` `.jpeg` `.png` `.gif` `.webp` `.bmp` `.svg` `.md` `.markdown` |
| 单文件大小 | 10 MB |
| 批量数量 | 单次最多 9 个文件 |

**请求格式：** `multipart/form-data`，字段名为 `file`（单文件）或 `files`（批量）。

**单文件响应 `data`：**

```json
{
  "url": "/uploads/202603/a1b2c3d4e5f6.png",
  "filename": "food_photo.png",
  "size": 204800,
  "content_type": "image/png"
}
```

**批量响应 `data`：** 数组，每项结构同上。

**存储结构：** `uploads/{YYYYMM}/{uuid}.{ext}`，通过 `/uploads/...` 路径直接访问。

---

### 4. 纪念日管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/anniversaries` | 获取所有纪念日 |
| `POST` | `/api/anniversaries` | 新增纪念日 |
| `GET` | `/api/anniversaries/upcoming` | 获取即将到来的纪念日 |
| `PUT` | `/api/anniversaries/{id}` | 修改纪念日 |
| `DELETE` | `/api/anniversaries/{id}` | 删除纪念日 |

**查询参数：** `upcoming` 接口支持 `days`（默认 7，查询未来 N 天内的纪念日）。

**创建纪念日：**

```json
{
  "name": "在一起纪念日",
  "date": "2025-03-04",
  "description": "我们在一起的第一天",
  "is_recurring": 1,
  "remind_days": 7
}
```

**`is_recurring` 枚举：**

| 值 | 含义 |
|----|------|
| `0` | 不重复（一次性） |
| `1` | 每年重复 |
| `2` | 每周重复 |

---

### 5. 点餐记录

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/orders` | 获取点餐列表（分页+筛选） |
| `POST` | `/api/orders` | 创建点餐记录 |
| `GET` | `/api/orders/{id}` | 获取单次点餐详情 |
| `PUT` | `/api/orders/{id}` | 更新点餐记录 |
| `DELETE` | `/api/orders/{id}` | 删除点餐记录 |
| `POST` | `/api/orders/validate` | 忌口冲突校验 |

**列表查询参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `page` | int | 页码，默认 1 |
| `size` | int | 每页数量，默认 20 |
| `restaurant` | string | 按餐厅名模糊筛选 |
| `startDate` | string | 起始日期 |
| `endDate` | string | 结束日期 |

**创建点餐：**

```json
{
  "restaurant": "海底捞",
  "address": "北京市朝阳区望京SOHO",
  "date": "2026-03-05T12:00:00",
  "dishes": [
    { "name": "麻辣牛肉", "price": 68.0, "ordered_by": 1 },
    { "name": "虾滑", "price": 38.0, "ordered_by": 2 },
    { "name": "酸梅汤", "price": 12.0, "notes": "少糖" }
  ],
  "moods": { "user1": "暖", "user2": "甜" },
  "notes": "今天很开心"
}
```

**心情值 `moods`：** `冷` / `暖` / `躁` / `甜`（可选，Swagger UI 下拉选择）。

**忌口校验请求：**

```json
{
  "dishes": [
    { "name": "香菜牛肉丸", "ordered_for": 1 },
    { "name": "水煮鱼", "ordered_for": 2 }
  ]
}
```

如果存在冲突返回冲突详情列表，否则返回空数组。

---

### 6. 盲猜价格游戏

两人各自猜一道隐藏菜品的价格，猜得更接近者获胜并赢得爱情币。

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/orders/{id}/price-guess/init` | 初始化游戏（可指定隐藏菜品或随机选取） |
| `GET` | `/api/orders/{id}/price-guess` | 查看游戏状态（价格隐藏） |
| `POST` | `/api/orders/{id}/price-guess` | 提交猜测 |
| `GET` | `/api/orders/{id}/price-guess/result` | 揭晓结果 |
| `DELETE` | `/api/orders/{id}/price-guess` | 重置游戏 |

**游戏流程：**

```
初始化(init) → 双方各自提交猜测 → 两人都猜完后揭晓结果(result)
                                    ↓ 如需重玩
                              重置(DELETE) → 重新初始化
```

**提交猜测：** `{ "guess": 45.0 }`

**结果 `data`：**

```json
{
  "actual_price": 68.0,
  "guess_user1": 45.0,
  "guess_user2": 60.0,
  "result": "user2_win",
  "reward": "user2 获得 5 爱情币"
}
```

`result` 值：`user1_win` / `user2_win` / `both_wrong`

---

### 7. 味觉日记

每条点餐记录可关联一篇味觉日记，支持文字内容、评分和图片。图片先通过上传接口获取 URL，再以 JSON 数组传入。

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/taste-diary` | 获取日记列表（分页） |
| `GET` | `/api/taste-diary/{id}` | 获取单篇日记详情 |
| `POST` | `/api/orders/{id}/diary` | 为点餐添加日记 |
| `PUT` | `/api/taste-diary/{id}` | 更新日记 |

**创建日记：**

```json
{
  "content": "三文鱼刺身入口即化，鳗鱼饭也很赞！",
  "rating": 5,
  "images": [
    "/uploads/202603/abc123.png",
    "/uploads/202603/def456.png"
  ]
}
```

---

### 7.5 私家厨房

菜品上传（Markdown 菜谱、图片、食材）、点菜、制作、备菜。菜谱支持 Markdown，可使用 `![](url)` 引用图片；`recipe_url` 可指向通过 `/api/upload` 上传的 `.md` 文档。

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/private-kitchen/dishes` | 获取菜品列表（分页、关键词筛选） |
| `GET` | `/api/private-kitchen/dishes/{id}` | 获取菜品详情 |
| `POST` | `/api/private-kitchen/dishes` | 上传菜品 |
| `PUT` | `/api/private-kitchen/dishes/{id}` | 更新菜品 |
| `DELETE` | `/api/private-kitchen/dishes/{id}` | 删除菜品 |
| `POST` | `/api/private-kitchen/selections` | 点菜（加入制作计划） |
| `GET` | `/api/private-kitchen/selections` | 制作接口：查看计划中的菜品（含食材、菜谱、图片） |
| `DELETE` | `/api/private-kitchen/selections/{id}` | 从计划中移除 |
| `GET` | `/api/private-kitchen/ingredients` | 备菜接口：当前计划所需食材汇总 |

**创建菜品（支持 HowToCook md 链接）：**

```json
{
  "name": "西红柿炒鸡蛋",
  "recipe": "完整菜谱：[西红柿炒鸡蛋](/temp/HowToCook/dishes/vegetable_dish/西红柿炒鸡蛋.md)",
  "recipe_url": "/temp/HowToCook/dishes/vegetable_dish/西红柿炒鸡蛋.md",
  "images": ["/uploads/202603/xxx.png"],
  "ingredients": [
    { "name": "番茄", "amount": "2", "unit": "个" },
    { "name": "鸡蛋", "amount": "3", "unit": "个" }
  ]
}
```

菜谱可引用 [HowToCook](https://github.com/Anduin2017/HowToCook) 项目，运行 `python scripts/setup_howtocook.py` 拉取到 `temp/HowToCook`。

**备菜接口响应示例：**

```json
[
  { "name": "番茄", "amount": "2个", "unit": "个", "sources": [{"dish_name": "番茄炒蛋", "amount": "2"}] },
  { "name": "鸡蛋", "amount": "5个", "unit": "个", "sources": [...] }
]
```

---

### 8. 味觉地图

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/taste-map/points` | 获取所有餐厅标记点 |

**查询参数：** `restaurant`（可选，按名称模糊筛选）

**响应 `data` 示例：**

```json
[
  {
    "restaurant": "海底捞",
    "address": "北京市朝阳区望京SOHO",
    "visit_count": 2,
    "avg_rating": 4.5,
    "last_visit": "2026-03-05",
    "dishes": ["麻辣牛肉", "虾滑", "毛肚", "肥牛卷"]
  }
]
```

---

### 9. 成就系统

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/achievements` | 获取所有成就定义 |
| `GET` | `/api/users/me/achievements` | 获取当前用户成就进度 |

**内置成就：**

| 成就 | 类别 | 目标 |
|------|------|------|
| 初次约饭 | 点餐成就 | 完成 1 次点餐 |
| 十次约会 | 点餐成就 | 累计 10 次点餐 |
| 百次携手 | 点餐成就 | 累计 100 次点餐 |
| 冒险家 | 探索成就 | 连续 3 次点新菜 |
| 回头客 | 忠诚成就 | 同一餐厅 5 次以上 |
| 美食评论家 | 记录成就 | 写满 10 篇日记 |
| 默契满分 | 游戏成就 | 盲猜获胜 3 次 |
| 甜蜜储蓄家 | 爱情银行 | 累计存入 1000 爱情币 |

---

### 10. 爱情银行

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/users/me/love-coins` | 查询爱情币余额 |
| `GET` | `/api/users/me/love-coin-transactions` | 获取积分流水（分页） |
| `GET` | `/api/redeem-items` | 获取可兑换特权列表 |
| `POST` | `/api/redeem` | 兑换特权物品 |
| `POST` | `/api/redeem/synthesize` | 合成不生气券 |
| `GET` | `/api/users/me/inventory` | 查看物品背包 |

**爱情币获取方式：** 每次创建点餐记录自动存入 10 爱情币。

**可兑换物品：**

| 物品 | 花费 | 星级 | 说明 |
|------|------|------|------|
| 免洗碗特权 | 200 | — | 免洗碗/免做家务 |
| 点餐独裁权 | 300 | — | 下次完全由你决定 |
| 一星不生气券 | 500 | ★ | 可抵消一次小摩擦 |
| 二星不生气券 | — | ★★ | 3 张一星合成 |
| 三星不生气券 | — | ★★★ | 3 张二星合成 |
| 四星不生气券 | — | ★★★★ | 3 张三星合成 |

**兑换：** `{ "itemId": 3 }`

**合成（传入 3 个背包中同星级券的 `redemption_id`，必须同类型。seed 下 1/2/3 为一星券）：**

```json
{ "itemIds": [1, 2, 3] }
```

---

### 11. 情绪温度计

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/moods/statistics` | 获取情绪统计 |

**查询参数：** `startDate`、`endDate`（可选，按时间范围筛选）

**响应 `data`：**

```json
{
  "user1": [
    { "mood": "暖", "count": 3 },
    { "mood": "甜", "count": 2 }
  ],
  "user2": [
    { "mood": "甜", "count": 3 },
    { "mood": "冷", "count": 1 }
  ]
}
```

---

### 12. 选择困难症拯救器

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/recommendations` | 随机推荐菜品 |

**查询参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `count` | int | 推荐数量，默认 3 |
| `restaurant` | string | 指定餐厅范围 |
| `mood` | string | 按心情推荐 |

自动结合当前用户偏好排除忌口菜品。

---

### 13. 惊喜模式

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/surprise-mode/status` | 查看惊喜模式状态 |

临近纪念日时自动激活，返回即将到来的纪念日信息和提示消息。

---

### 14. 仪表盘

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/dashboard` | 获取首页聚合数据 |

**响应 `data`：**

```json
{
  "upcoming_anniversaries": [],
  "love_coin_balances": [{ "user_id": 1, "balance": 2000 }],
  "recent_orders": [],
  "latest_achievements": [],
  "total_orders": 7,
  "total_restaurants": 5
}
```

---

## 数据库结构

使用 SQLite，数据库文件默认为项目根目录下的 `duodish.db`。启动时自动执行 `migrations/init.sql` 建表。

**核心表：**

| 表名 | 说明 |
|------|------|
| `users` | 用户（限 2 人） |
| `user_preferences` | 忌口与喜好（JSON 数组） |
| `anniversaries` | 纪念日 |
| `orders` | 点餐记录 |
| `order_dishes` | 订单菜品 |
| `dish_tags` | 菜品标签 |
| `taste_diary` | 味觉日记（每单一篇） |
| `price_guess_games` | 盲猜价格游戏 |
| `achievements` | 成就定义 |
| `user_achievements` | 用户成就进度 |
| `love_coins` | 爱情币余额 |
| `love_coin_transactions` | 爱情币流水 |
| `redeem_items` | 可兑换物品定义 |
| `redemptions` | 兑换/合成记录 |
| `private_kitchen_dishes` | 私家厨房菜品（菜谱） |
| `dish_ingredients` | 菜品食材 |
| `kitchen_selections` | 点菜/制作计划 |

数据库开启了 `WAL` 模式和外键约束，`updated_at` 字段通过 SQLite 触发器自动更新。

---

## 测试

### Python 自动化测试（推荐）

使用 pytest 运行，无需手动启动服务器，自动创建临时测试数据库：

```bash
# 安装测试依赖
pip install pytest httpx

# 运行全部测试
pytest test/test_api.py -v

# 精简输出
pytest test/test_api.py -v --tb=short

# 只运行某个模块
pytest test/test_api.py -v -k "Test06Orders"
```

测试覆盖 17 个模块、90+ 个用例，包括正常流程和异常情况（非法参数、权限校验、余额不足等）。

### JetBrains HTTP Client

项目还提供 `test/test_main.http`，可在 PyCharm / IntelliJ IDEA 中直接运行（需先启动服务器）。

测试流程按编号顺序执行：

1. **用户认证** — 登录获取 Token
2. **用户信息** — 上传头像 → 更新资料 → 验证
3. **忌口偏好** — 设置并查询双方偏好
4. **纪念日** — 增删改查 + 即将到来
5. **点餐记录** — 创建、筛选、忌口校验
6. **盲猜游戏** — 初始化 → 双方猜测 → 揭晓
7. **文件上传** — 单文件 + 批量上传（使用 `test/test_image/` 中的图片）
8. **味觉日记** — 创建（纯文字/带图）→ 更新 → 查询
8.5 **私家厨房** — 上传菜品（Markdown 菜谱、图片、食材）→ 点菜 → 制作接口 → 备菜接口
9. **味觉地图** — 餐厅标记点
10. **成就系统** — 查看定义和进度
11. **爱情银行** — 余额、流水、兑换、合成、背包
12. **情绪温度计** — 统计查询
13. **菜品推荐** — 随机/指定餐厅/按心情
14. **惊喜模式** — 状态查询
15. **仪表盘** — 首页聚合数据
