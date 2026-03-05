-- ==================== 用户表 ====================
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    nickname TEXT,
    avatar TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ==================== 纪念日表 ====================
CREATE TABLE IF NOT EXISTS anniversaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    date DATE NOT NULL,
    description TEXT,
    is_recurring INTEGER DEFAULT 0,  -- 0-不重复, 1-每年, 2-每周, 3-每月
    remind_days INTEGER DEFAULT 3,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME
);

-- ==================== 点餐记录主表 ====================
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant TEXT NOT NULL,
    address TEXT,
    order_date DATETIME NOT NULL,
    mood_user1 TEXT CHECK (mood_user1 IN ('冷','暖','躁','甜')),
    mood_user2 TEXT CHECK (mood_user2 IN ('冷','暖','躁','甜')),
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ==================== 菜品明细表 ====================
CREATE TABLE IF NOT EXISTS order_dishes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    dish_name TEXT NOT NULL,
    price REAL,
    ordered_by INTEGER,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (ordered_by) REFERENCES users(id) ON DELETE SET NULL
);

-- ==================== 盲猜价格游戏表 ====================
CREATE TABLE IF NOT EXISTS price_guess_games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER UNIQUE NOT NULL,
    hidden_dish_id INTEGER NOT NULL,
    guess_user1 REAL,
    guess_user2 REAL,
    result TEXT,
    reward TEXT,
    completed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (hidden_dish_id) REFERENCES order_dishes(id) ON DELETE CASCADE
);

-- ==================== 成就定义表 ====================
CREATE TABLE IF NOT EXISTS achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT,
    criteria TEXT,
    badge_icon TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ==================== 用户成就进度表 ====================
CREATE TABLE IF NOT EXISTS user_achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    achievement_id INTEGER NOT NULL,
    progress INTEGER DEFAULT 0,
    unlocked_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, achievement_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (achievement_id) REFERENCES achievements(id) ON DELETE CASCADE
);

-- ==================== 爱情币余额表 ====================
CREATE TABLE IF NOT EXISTS love_coins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    balance INTEGER DEFAULT 0,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ==================== 爱情币流水表 ====================
CREATE TABLE IF NOT EXISTS love_coin_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    type TEXT NOT NULL,
    reference_id INTEGER,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ==================== 可兑换特权物品表（含不生气券星级） ====================
CREATE TABLE IF NOT EXISTS redeem_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    cost INTEGER NOT NULL,
    icon TEXT,
    star_level INTEGER DEFAULT 0,       -- 0=普通特权, 1-4=不生气券星级
    synthesize_from INTEGER,             -- 合成所需的低一级 item_id
    synthesize_count INTEGER DEFAULT 3,  -- 合成所需数量
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (synthesize_from) REFERENCES redeem_items(id)
);

-- ==================== 兑换记录表 ====================
CREATE TABLE IF NOT EXISTS redemptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    cost INTEGER NOT NULL,
    status TEXT DEFAULT 'redeemed',  -- redeemed, used, consumed_for_synthesis
    synthesized_into INTEGER,        -- 合成产物的 redemption_id
    redeemed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES redeem_items(id) ON DELETE CASCADE,
    FOREIGN KEY (synthesized_into) REFERENCES redemptions(id)
);

-- ==================== 味觉日记表（多图JSON） ====================
CREATE TABLE IF NOT EXISTS taste_diary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER UNIQUE NOT NULL,
    content TEXT,
    images TEXT,  -- JSON数组存储多图路径
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);

-- ==================== 用户偏好表 ====================
CREATE TABLE IF NOT EXISTS user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    dislikes TEXT,  -- JSON数组
    likes TEXT,     -- JSON数组
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ==================== 菜品标签表 ====================
CREATE TABLE IF NOT EXISTS dish_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dish_name TEXT NOT NULL,
    tag TEXT NOT NULL,
    UNIQUE(dish_name, tag)
);

-- ==================== 索引 ====================
CREATE INDEX IF NOT EXISTS idx_orders_order_date ON orders(order_date);
CREATE INDEX IF NOT EXISTS idx_order_dishes_order_id ON order_dishes(order_id);
CREATE INDEX IF NOT EXISTS idx_user_achievements_user_id ON user_achievements(user_id);
CREATE INDEX IF NOT EXISTS idx_user_achievements_achievement_id ON user_achievements(achievement_id);
CREATE INDEX IF NOT EXISTS idx_love_coin_transactions_user_id ON love_coin_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_taste_diary_order_id ON taste_diary(order_id);
CREATE INDEX IF NOT EXISTS idx_price_guess_games_order_id ON price_guess_games(order_id);
CREATE INDEX IF NOT EXISTS idx_dish_tags_name ON dish_tags(dish_name);
CREATE INDEX IF NOT EXISTS idx_redemptions_user_status ON redemptions(user_id, status);

-- ==================== 自动更新 updated_at 触发器 ====================
CREATE TRIGGER IF NOT EXISTS trg_anniversaries_updated
AFTER UPDATE ON anniversaries
BEGIN
    UPDATE anniversaries SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_taste_diary_updated
AFTER UPDATE ON taste_diary
BEGIN
    UPDATE taste_diary SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_user_preferences_updated
AFTER UPDATE ON user_preferences
BEGIN
    UPDATE user_preferences SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_love_coins_updated
AFTER UPDATE ON love_coins
BEGIN
    UPDATE love_coins SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- ==================== 预置成就 ====================
INSERT OR IGNORE INTO achievements (id, name, description, category, criteria, badge_icon) VALUES
(1, '初次约饭', '完成第一次点餐记录', '点餐成就', '{"type":"order_count","target":1}', '🍽️'),
(2, '十次约会', '累计点餐10次', '点餐成就', '{"type":"order_count","target":10}', '🔟'),
(3, '百次携手', '累计点餐100次', '点餐成就', '{"type":"order_count","target":100}', '💯'),
(4, '冒险家', '连续3次点从未吃过的菜', '探索成就', '{"type":"new_dish_streak","target":3}', '🗺️'),
(5, '回头客', '在同一家餐厅吃饭超过5次', '忠诚成就', '{"type":"same_restaurant","target":5}', '🏠'),
(6, '美食评论家', '写满10篇味觉日记', '记录成就', '{"type":"diary_count","target":10}', '📝'),
(7, '默契满分', '盲猜价格游戏中获胜3次', '游戏成就', '{"type":"guess_win","target":3}', '🎯'),
(8, '甜蜜储蓄家', '爱情币累计存入1000', '爱情银行成就', '{"type":"total_deposit","target":1000}', '🏦');

-- ==================== 预置兑换物品（含不生气券星级体系） ====================
INSERT OR IGNORE INTO redeem_items (id, name, description, cost, star_level, synthesize_from, synthesize_count, is_active) VALUES
(1, '免洗碗特权', '一次免洗碗/免做家务的特权', 200, 0, NULL, 3, 1),
(2, '点餐独裁权', '下次完全由你说了算', 300, 0, NULL, 3, 1),
(3, '一星不生气券', '基础版不生气券，500爱情币兑换，可抵消一次小摩擦', 500, 1, NULL, 3, 1),
(4, '二星不生气券', '进阶版不生气券，三张一星合成获得', 0, 2, 3, 3, 1),
(5, '三星不生气券', '高级版不生气券，三张二星合成获得', 0, 3, 4, 3, 1),
(6, '四星不生气券', '终极版不生气券，三张三星合成获得', 0, 4, 5, 3, 1);

-- ==================== 私家厨房 ====================
-- 私家厨房菜品表（菜谱）
CREATE TABLE IF NOT EXISTS private_kitchen_dishes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    recipe TEXT,
    recipe_url TEXT,
    images TEXT,
    created_by INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
);

-- 菜品食材表
CREATE TABLE IF NOT EXISTS dish_ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dish_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    amount TEXT,
    unit TEXT DEFAULT '',
    sort_order INTEGER DEFAULT 0,
    FOREIGN KEY (dish_id) REFERENCES private_kitchen_dishes(id) ON DELETE CASCADE
);

-- 点菜/选菜表（将菜品加入制作计划）
CREATE TABLE IF NOT EXISTS kitchen_selections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dish_id INTEGER NOT NULL,
    selected_by INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(dish_id),
    FOREIGN KEY (dish_id) REFERENCES private_kitchen_dishes(id) ON DELETE CASCADE,
    FOREIGN KEY (selected_by) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_dish_ingredients_dish_id ON dish_ingredients(dish_id);
CREATE INDEX IF NOT EXISTS idx_kitchen_selections_dish_id ON kitchen_selections(dish_id);

CREATE TRIGGER IF NOT EXISTS trg_private_kitchen_dishes_updated
AFTER UPDATE ON private_kitchen_dishes
BEGIN
    UPDATE private_kitchen_dishes SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
