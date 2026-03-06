"""DuoDish API 自动化测试

运行方式:
    pytest test/test_api.py -v
    pytest test/test_api.py -v --tb=short   # 精简错误输出

PyCharm: 右键 test_api.py -> Run 'pytest in test_api.py'
或: Settings -> Tools -> Python Integrated Tools -> Default test runner -> pytest
"""

import base64
import json
import os

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

# ═══════════════════════════════════════════
#  辅助函数
# ═══════════════════════════════════════════


def _encrypt_for_auth(public_key_pem: str, payload: dict) -> str:
    """使用 RSA 公钥加密认证数据，模拟前端加密（含 _t _n 防重放）"""
    import time
    data = {**payload, "_t": int(time.time()), "_n": os.urandom(8).hex()}
    return _encrypt_raw(public_key_pem, data)


def _encrypt_raw(public_key_pem: str, data: dict) -> str:
    """加密任意 dict（不自动添加 _t _n），用于测试"""
    pub = serialization.load_pem_public_key(public_key_pem.encode())
    plain = json.dumps(data, ensure_ascii=False).encode("utf-8")
    cipher = pub.encrypt(
        plain,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return base64.b64encode(cipher).decode("ascii")


def auth(state, user=1):
    return {"Authorization": f"Bearer {state[f'token{user}']}"}


def ok(resp, code=200):
    assert resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["code"] == code, f"code={body['code']}, msg={body['message']}"
    return body["data"]


# ═══════════════════════════════════════════
#  1. 用户认证
# ═══════════════════════════════════════════

class Test01Auth:

    def test_public_key(self, api):
        r = api.get("/api/auth/public-key")
        assert r.status_code == 200
        data = r.json()
        assert "publicKey" in data
        assert "-----BEGIN PUBLIC KEY-----" in data["publicKey"]

    def test_register_alice(self, api, state):
        pem = api.get("/api/auth/public-key").json()["publicKey"]
        enc = _encrypt_for_auth(pem, {"username": "alice", "password": "123456", "nickname": "小爱"})
        data = ok(api.post("/api/auth/register", json={"encryptedData": enc}))
        assert data["user_id"] == 1
        assert data["token"]
        state["token1"] = data["token"]

    def test_register_bob(self, api, state):
        pem = api.get("/api/auth/public-key").json()["publicKey"]
        enc = _encrypt_for_auth(pem, {"username": "bob", "password": "123456", "nickname": "阿宝"})
        data = ok(api.post("/api/auth/register", json={"encryptedData": enc}))
        assert data["user_id"] == 2
        state["token2"] = data["token"]

    def test_register_third_rejected(self, api):
        pem = api.get("/api/auth/public-key").json()["publicKey"]
        enc = _encrypt_for_auth(pem, {"username": "charlie", "password": "123456"})
        r = api.post("/api/auth/register", json={"encryptedData": enc})
        assert r.json()["code"] == 403

    def test_login_alice(self, api, state):
        pem = api.get("/api/auth/public-key").json()["publicKey"]
        enc = _encrypt_for_auth(pem, {"username": "alice", "password": "123456"})
        data = ok(api.post("/api/auth/login", json={"encryptedData": enc}))
        state["token1"] = data["token"]

    def test_login_bob(self, api, state):
        pem = api.get("/api/auth/public-key").json()["publicKey"]
        enc = _encrypt_for_auth(pem, {"username": "bob", "password": "123456"})
        data = ok(api.post("/api/auth/login", json={"encryptedData": enc}))
        state["token2"] = data["token"]

    def test_login_wrong_password(self, api):
        pem = api.get("/api/auth/public-key").json()["publicKey"]
        enc = _encrypt_for_auth(pem, {"username": "alice", "password": "wrong"})
        r = api.post("/api/auth/login", json={"encryptedData": enc})
        assert r.json()["code"] == 401

    def test_login_missing_timestamp_rejected(self, api):
        """缺少时间戳 _t 的密文应被拒绝（需使用最新版前端）"""
        pem = api.get("/api/auth/public-key").json()["publicKey"]
        enc = _encrypt_raw(pem, {"username": "alice", "password": "123456"})
        r = api.post("/api/auth/login", json={"encryptedData": enc})
        assert r.json()["code"] == 400
        assert "时间戳" in r.json()["message"]

    def test_login_expired_rejected(self, api):
        """超时密文应被拒绝（防重放）"""
        import time
        pem = api.get("/api/auth/public-key").json()["publicKey"]
        data = {"username": "alice", "password": "123456", "_t": int(time.time()) - 600, "_n": "deadbeef"}
        enc = _encrypt_raw(pem, data)
        r = api.post("/api/auth/login", json={"encryptedData": enc})
        assert r.json()["code"] == 400
        assert "过期" in r.json()["message"]


# ═══════════════════════════════════════════
#  2. 文件上传
# ═══════════════════════════════════════════

class Test02Upload:

    def test_single_upload(self, api, state, image_dir):
        img_path = os.path.join(image_dir, "72027189_p0.png")
        with open(img_path, "rb") as f:
            data = ok(api.post(
                "/api/upload",
                files={"file": ("hotpot.png", f, "image/png")},
                headers=auth(state),
            ))
        assert data["url"].startswith("/uploads/")
        assert data["size"] > 0
        state["upload_url1"] = data["url"]

    def test_single_upload_2(self, api, state, image_dir):
        img_path = os.path.join(image_dir, "72100589_p0.png")
        with open(img_path, "rb") as f:
            data = ok(api.post(
                "/api/upload",
                files={"file": ("sushi.png", f, "image/png")},
                headers=auth(state),
            ))
        state["upload_url2"] = data["url"]

    def test_single_upload_3(self, api, state, image_dir):
        img_path = os.path.join(image_dir, "72204201_p0.png")
        with open(img_path, "rb") as f:
            data = ok(api.post(
                "/api/upload",
                files={"file": ("dessert.png", f, "image/png")},
                headers=auth(state, 2),
            ))
        state["upload_url3"] = data["url"]

    def test_batch_upload(self, api, state, image_dir):
        files = []
        for name in ("69988918_p0.png", "70004896_p0.png", "71607942_p1.png"):
            path = os.path.join(image_dir, name)
            files.append(("files", (name, open(path, "rb"), "image/png")))
        data = ok(api.post("/api/upload/batch", files=files, headers=auth(state)))
        assert len(data) == 3
        for item in data:
            assert item["url"].startswith("/uploads/")
        for _, (_, fobj, _) in files:
            fobj.close()

    def test_upload_invalid_type(self, api, state):
        r = api.post(
            "/api/upload",
            files={"file": ("bad.exe", b"binary", "application/octet-stream")},
            headers=auth(state),
        )
        assert r.json()["code"] == 400

    def test_upload_no_auth(self, api):
        r = api.post("/api/upload", files={"file": ("a.png", b"x", "image/png")})
        assert r.status_code in (401, 403)


# ═══════════════════════════════════════════
#  3. 用户信息
# ═══════════════════════════════════════════

class Test03Users:

    def test_get_alice(self, api, state):
        data = ok(api.get("/api/users/me", headers=auth(state)))
        assert data["username"] == "alice"
        assert data["nickname"] == "小爱"

    def test_update_alice_avatar(self, api, state):
        data = ok(api.put("/api/users/me", headers=auth(state), json={
            "nickname": "小爱同学",
            "avatar": state["upload_url1"],
            "dingtalk": "alice_dingtalk",
            "webhookUrl": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
        }))
        assert data["nickname"] == "小爱同学"
        assert data["avatar"] == state["upload_url1"]
        assert data["dingtalk"] == "alice_dingtalk"
        assert data["webhookUrl"] == "https://oapi.dingtalk.com/robot/send?access_token=xxx"

    def test_update_bob(self, api, state):
        data = ok(api.put("/api/users/me", headers=auth(state, 2), json={
            "avatar": state["upload_url3"],
            "webhookUrl": "https://oapi.dingtalk.com/robot/send?access_token=yyy",
        }))
        assert data["avatar"] == state["upload_url3"]
        assert data["webhookUrl"] == "https://oapi.dingtalk.com/robot/send?access_token=yyy"

    def test_get_bob(self, api, state):
        data = ok(api.get("/api/users/me", headers=auth(state, 2)))
        assert data["username"] == "bob"
        assert data["webhookUrl"] == "https://oapi.dingtalk.com/robot/send?access_token=yyy"


# ═══════════════════════════════════════════
#  4. 忌口与偏好
# ═══════════════════════════════════════════

class Test04Preferences:

    def test_set_alice_prefs(self, api, state):
        data = ok(api.put("/api/users/me/preferences", headers=auth(state), json={
            "dislikes": ["香菜", "葱", "芥末"],
            "likes": ["辣", "麻", "川菜"],
        }))
        assert "香菜" in data["dislikes"]

    def test_set_bob_prefs(self, api, state):
        data = ok(api.put("/api/users/me/preferences", headers=auth(state, 2), json={
            "dislikes": ["辣", "花椒", "内脏"],
            "likes": ["甜品", "日料", "清淡"],
        }))
        assert "辣" in data["dislikes"]

    def test_get_alice_prefs_with_partner(self, api, state):
        data = ok(api.get("/api/users/me/preferences", headers=auth(state)))
        assert data["mine"]["dislikes"] == ["香菜", "葱", "芥末"]
        assert data["partner"] is not None
        assert "辣" in data["partner"]["dislikes"]

    def test_get_bob_prefs_with_partner(self, api, state):
        data = ok(api.get("/api/users/me/preferences", headers=auth(state, 2)))
        assert data["mine"]["dislikes"] == ["辣", "花椒", "内脏"]
        assert "香菜" in data["partner"]["dislikes"]


# ═══════════════════════════════════════════
#  5. 纪念日管理
# ═══════════════════════════════════════════

class Test05Anniversaries:

    def test_create_yearly(self, api, state):
        data = ok(api.post("/api/anniversaries", headers=auth(state), json={
            "name": "在一起纪念日",
            "date": "2025-03-04",
            "description": "我们在一起的第一天",
            "is_recurring": 1,
            "remind_days": 7,
        }))
        assert data["id"]
        state["ann_id1"] = data["id"]

    def test_create_birthday(self, api, state):
        data = ok(api.post("/api/anniversaries", headers=auth(state), json={
            "name": "Bob生日",
            "date": "2026-06-15",
            "is_recurring": 1,
            "remind_days": 5,
        }))
        state["ann_id2"] = data["id"]

    def test_create_weekly(self, api, state):
        data = ok(api.post("/api/anniversaries", headers=auth(state), json={
            "name": "每周约会日",
            "date": "2026-03-07",
            "description": "每周六的固定约会",
            "is_recurring": 2,
            "remind_days": 1,
        }))
        state["ann_id3"] = data["id"]

    def test_list_all(self, api, state):
        data = ok(api.get("/api/anniversaries", headers=auth(state)))
        assert len(data) == 3

    def test_upcoming_7days(self, api, state):
        data = ok(api.get("/api/anniversaries/upcoming?days=7", headers=auth(state)))
        assert isinstance(data, list)

    def test_upcoming_30days(self, api, state):
        data = ok(api.get("/api/anniversaries/upcoming?days=30", headers=auth(state)))
        assert isinstance(data, list)

    def test_update(self, api, state):
        data = ok(api.put(
            f"/api/anniversaries/{state['ann_id1']}",
            headers=auth(state),
            json={"description": "最特别的日子", "remind_days": 10},
        ))
        assert data["description"] == "最特别的日子"
        assert data["remind_days"] == 10

    def test_delete(self, api, state):
        ok(api.delete(f"/api/anniversaries/{state['ann_id3']}", headers=auth(state)))
        data = ok(api.get("/api/anniversaries", headers=auth(state)))
        assert len(data) == 2


# ═══════════════════════════════════════════
#  6. 点餐记录
# ═══════════════════════════════════════════

class Test06Orders:

    def test_create_order1(self, api, state):
        data = ok(api.post("/api/orders", headers=auth(state), json={
            "restaurant": "海底捞",
            "address": "北京市朝阳区望京SOHO",
            "date": "2026-03-05T12:00:00",
            "dishes": [
                {"name": "麻辣牛肉", "price": 68.0, "ordered_by": 1},
                {"name": "虾滑", "price": 38.0, "ordered_by": 2},
                {"name": "酸梅汤", "price": 12.0, "notes": "少糖"},
            ],
            "moods": {"user1": "暖", "user2": "甜"},
            "notes": "今天很开心，第一次一起吃火锅",
        }))
        assert data["id"]
        assert data["restaurant"] == "海底捞"
        state["order_id1"] = data["id"]

    def test_create_order2(self, api, state):
        data = ok(api.post("/api/orders", headers=auth(state), json={
            "restaurant": "一幸寿司",
            "address": "北京市海淀区中关村",
            "date": "2026-03-04T18:30:00",
            "dishes": [
                {"name": "三文鱼刺身", "price": 88.0, "ordered_by": 2},
                {"name": "鳗鱼饭", "price": 58.0, "ordered_by": 1},
                {"name": "味增汤", "price": 15.0},
            ],
            "moods": {"user1": "甜", "user2": "暖"},
        }))
        state["order_id2"] = data["id"]

    def test_create_order3(self, api, state):
        data = ok(api.post("/api/orders", headers=auth(state), json={
            "restaurant": "海底捞",
            "address": "北京市朝阳区望京SOHO",
            "date": "2026-03-03T19:00:00",
            "dishes": [
                {"name": "毛肚", "price": 42.0, "ordered_by": 1},
                {"name": "肥牛卷", "price": 52.0, "ordered_by": 2},
                {"name": "冰粉", "price": 8.0},
            ],
            "moods": {"user1": "躁", "user2": "冷"},
            "notes": "今天都有点累，火锅治愈一切",
        }))
        state["order_id3"] = data["id"]

    def test_list_paginated(self, api, state):
        data = ok(api.get("/api/orders?page=1&size=10", headers=auth(state)))
        assert data["total"] == 3
        assert len(data["items"]) == 3

    def test_filter_by_restaurant(self, api, state):
        data = ok(api.get("/api/orders?restaurant=海底捞", headers=auth(state)))
        assert data["total"] == 2
        for item in data["items"]:
            assert "海底捞" in item["restaurant"]

    def test_filter_by_date(self, api, state):
        data = ok(api.get(
            "/api/orders?startDate=2026-03-04&endDate=2026-03-05",
            headers=auth(state),
        ))
        assert data["total"] >= 1

    def test_get_detail(self, api, state):
        data = ok(api.get(f"/api/orders/{state['order_id1']}", headers=auth(state)))
        assert data["restaurant"] == "海底捞"
        assert len(data["dishes"]) == 3

    def test_update(self, api, state):
        data = ok(api.put(
            f"/api/orders/{state['order_id1']}",
            headers=auth(state),
            json={"notes": "下次要试试番茄锅底"},
        ))
        assert "番茄" in data["notes"]

    def test_validate_conflict(self, api, state):
        data = ok(api.post("/api/orders/validate", headers=auth(state), json={
            "dishes": [
                {"name": "香菜牛肉丸", "ordered_for": 1},
                {"name": "水煮鱼", "ordered_for": 2},
            ],
        }))
        assert len(data) > 0

    def test_validate_no_conflict(self, api, state):
        data = ok(api.post("/api/orders/validate", headers=auth(state), json={
            "dishes": [
                {"name": "清蒸鲈鱼", "ordered_for": 1},
                {"name": "蛋炒饭", "ordered_for": 2},
            ],
        }))
        assert len(data) == 0

    def test_invalid_mood(self, api, state):
        r = api.post("/api/orders", headers=auth(state), json={
            "restaurant": "test",
            "date": "2026-03-05",
            "moods": {"user1": "invalid"},
        })
        assert r.json()["code"] == 422


# ═══════════════════════════════════════════
#  7. 盲猜价格游戏
# ═══════════════════════════════════════════

class Test07PriceGuess:

    def test_init(self, api, state):
        ok(api.post(
            f"/api/orders/{state['order_id1']}/price-guess/init",
            headers=auth(state),
            json={},
        ))

    def test_status_before_guess(self, api, state):
        data = ok(api.get(
            f"/api/orders/{state['order_id1']}/price-guess",
            headers=auth(state),
        ))
        assert data["order_id"] == state["order_id1"]
        assert data["user1_guessed"] is False
        assert data["user2_guessed"] is False
        assert data["completed"] is False

    def test_alice_guess(self, api, state):
        ok(api.post(
            f"/api/orders/{state['order_id1']}/price-guess",
            headers=auth(state),
            json={"guess": 45.0},
        ))

    def test_bob_guess(self, api, state):
        ok(api.post(
            f"/api/orders/{state['order_id1']}/price-guess",
            headers=auth(state, 2),
            json={"guess": 60.0},
        ))

    def test_status_after_both(self, api, state):
        data = ok(api.get(
            f"/api/orders/{state['order_id1']}/price-guess",
            headers=auth(state),
        ))
        assert data["user1_guessed"] is True
        assert data["user2_guessed"] is True

    def test_result(self, api, state):
        data = ok(api.get(
            f"/api/orders/{state['order_id1']}/price-guess/result",
            headers=auth(state),
        ))
        assert data["actual_price"] > 0
        assert data["guess_user1"] == 45.0
        assert data["guess_user2"] == 60.0
        assert data["result"] in ("user1_win", "user2_win", "both_wrong")

    def test_game_ended_error(self, api, state):
        r = api.post(
            f"/api/orders/{state['order_id1']}/price-guess",
            headers=auth(state),
            json={"guess": 50.0},
        )
        assert r.json()["code"] == 400

    def test_reset_and_replay(self, api, state):
        ok(api.delete(
            f"/api/orders/{state['order_id1']}/price-guess",
            headers=auth(state),
        ))
        ok(api.post(
            f"/api/orders/{state['order_id1']}/price-guess/init",
            headers=auth(state),
            json={},
        ))
        data = ok(api.get(
            f"/api/orders/{state['order_id1']}/price-guess",
            headers=auth(state),
        ))
        assert data["completed"] is False


# ═══════════════════════════════════════════
#  8. 味觉日记
# ═══════════════════════════════════════════

class Test08Diary:

    def test_create_text_only(self, api, state):
        data = ok(api.post(
            f"/api/orders/{state['order_id1']}/diary",
            headers=auth(state),
            json={
                "content": "第一次一起吃海底捞，麻辣牛肉超好吃！",
                "rating": 5,
            },
        ))
        assert data["content"]
        assert data["rating"] == 5
        assert data["images"] == []
        state["diary_id1"] = data["id"]

    def test_create_with_images(self, api, state):
        data = ok(api.post(
            f"/api/orders/{state['order_id2']}/diary",
            headers=auth(state),
            json={
                "content": "三文鱼刺身入口即化，鳗鱼饭也很赞！",
                "rating": 5,
                "images": [state["upload_url2"], state["upload_url3"]],
            },
        ))
        assert len(data["images"]) == 2
        state["diary_id2"] = data["id"]

    def test_update_diary(self, api, state):
        data = ok(api.put(
            f"/api/taste-diary/{state['diary_id1']}",
            headers=auth(state),
            json={
                "content": "海底捞太赞了，冰粉也不错！",
                "images": [state["upload_url1"]],
                "rating": 4,
            },
        ))
        assert data["rating"] == 4
        assert len(data["images"]) == 1

    def test_list(self, api, state):
        data = ok(api.get("/api/taste-diary?page=1&size=10", headers=auth(state)))
        assert data["total"] == 2

    def test_get_detail(self, api, state):
        data = ok(api.get(
            f"/api/taste-diary/{state['diary_id2']}",
            headers=auth(state),
        ))
        assert len(data["images"]) == 2
        assert data["restaurant"] == "一幸寿司"

    def test_duplicate_diary_fails(self, api, state):
        r = api.post(
            f"/api/orders/{state['order_id1']}/diary",
            headers=auth(state),
            json={"content": "duplicate", "rating": 3},
        )
        assert r.json()["code"] in (400, 500)


# ═══════════════════════════════════════════
#  9. 味觉地图
# ═══════════════════════════════════════════

class Test09TasteMap:

    def test_all_points(self, api, state):
        data = ok(api.get("/api/taste-map/points", headers=auth(state)))
        assert len(data) >= 2
        restaurants = [p["restaurant"] for p in data]
        assert "海底捞" in restaurants

    def test_filter_by_restaurant(self, api, state):
        data = ok(api.get(
            "/api/taste-map/points?restaurant=海底捞",
            headers=auth(state),
        ))
        assert len(data) == 1
        assert data[0]["visit_count"] >= 1


# ═══════════════════════════════════════════
#  9.5 私家厨房
# ═══════════════════════════════════════════

class Test09aPrivateKitchen:

    def test_create_dish(self, api, state, image_dir):
        if "token1" not in state:
            pem = api.get("/api/auth/public-key").json()["publicKey"]
            ok(api.post("/api/auth/register", json={"encryptedData": _encrypt_for_auth(pem, {"username": "alice", "password": "123456", "nickname": "小爱"})}))
            ok(api.post("/api/auth/register", json={"encryptedData": _encrypt_for_auth(pem, {"username": "bob", "password": "123456", "nickname": "阿宝"})}))
            for u, p, t in [("alice", "123456", "token1"), ("bob", "123456", "token2")]:
                data = ok(api.post("/api/auth/login", json={"encryptedData": _encrypt_for_auth(pem, {"username": u, "password": p})}))
                state[t] = data["token"]
            for i, name in enumerate(["72027189_p0.png", "72100589_p0.png"], 1):
                path = os.path.join(image_dir, name)
                with open(path, "rb") as f:
                    data = ok(api.post("/api/upload", files={"file": (name, f, "image/png")}, headers=auth(state)))
                state[f"upload_url{i}"] = data["url"]
        recipe_url = "/temp/HowToCook/dishes/vegetable_dish/西红柿炒鸡蛋.md"
        data = ok(api.post("/api/private-kitchen/dishes", headers=auth(state), json={
            "name": "番茄炒蛋",
            "recipe": f"完整菜谱：[西红柿炒鸡蛋]({recipe_url})",
            "recipe_url": recipe_url,
            "images": [state["upload_url1"]],
            "ingredients": [
                {"name": "番茄", "amount": "2", "unit": "个"},
                {"name": "鸡蛋", "amount": "3", "unit": "个"},
                {"name": "盐", "amount": "适量", "unit": ""},
            ],
        }))
        assert data["name"] == "番茄炒蛋"
        assert data["recipe"]
        assert len(data["images"]) == 1
        assert len(data["ingredients"]) == 3
        state["pk_dish_id1"] = data["id"]

    def test_create_dish_with_recipe_url(self, api, state):
        recipe_url = "/temp/HowToCook/dishes/vegetable_dish/蒜蓉西兰花.md"
        data = ok(api.post("/api/private-kitchen/dishes", headers=auth(state), json={
            "name": "蒜蓉西兰花",
            "recipe": f"完整菜谱：[蒜蓉西兰花]({recipe_url})",
            "recipe_url": recipe_url,
            "images": [state["upload_url2"]],
            "ingredients": [{"name": "西兰花", "amount": "1", "unit": "棵"}, {"name": "蒜", "amount": "3", "unit": "瓣"}],
        }))
        assert data["recipe_url"] == recipe_url
        state["pk_dish_id2"] = data["id"]

    def test_list_dishes(self, api, state):
        data = ok(api.get("/api/private-kitchen/dishes?page=1&size=10", headers=auth(state)))
        assert data["total"] == 2

    def test_list_dishes_keyword(self, api, state):
        data = ok(api.get("/api/private-kitchen/dishes?keyword=番茄", headers=auth(state)))
        assert data["total"] == 1
        assert data["items"][0]["name"] == "番茄炒蛋"

    def test_get_dish(self, api, state):
        data = ok(api.get(f"/api/private-kitchen/dishes/{state['pk_dish_id1']}", headers=auth(state)))
        assert data["name"] == "番茄炒蛋"
        assert len(data["ingredients"]) == 3

    def test_add_selection(self, api, state):
        data = ok(api.post("/api/private-kitchen/selections", headers=auth(state), json={
            "dish_id": state["pk_dish_id1"],
        }))
        assert data["name"] == "番茄炒蛋"
        state["pk_selection_id1"] = data["id"]

    def test_add_selection_by_bob(self, api, state):
        data = ok(api.post("/api/private-kitchen/selections", headers=auth(state, 2), json={
            "dish_id": state["pk_dish_id2"],
        }))
        assert data["name"] == "蒜蓉西兰花"
        state["pk_selection_id2"] = data["id"]

    def test_add_selection_duplicate_fails(self, api, state):
        r = api.post("/api/private-kitchen/selections", headers=auth(state), json={
            "dish_id": state["pk_dish_id1"],
        })
        assert r.json()["code"] == 400

    def test_list_selections(self, api, state):
        data = ok(api.get("/api/private-kitchen/selections", headers=auth(state)))
        assert len(data) == 2
        names = [d["name"] for d in data]
        assert "番茄炒蛋" in names
        assert "蒜蓉西兰花" in names

    def test_list_selections_bob(self, api, state):
        data = ok(api.get("/api/private-kitchen/selections", headers=auth(state, 2)))
        assert len(data) == 2

    def test_get_aggregated_ingredients(self, api, state):
        data = ok(api.get("/api/private-kitchen/ingredients", headers=auth(state)))
        assert len(data) >= 4
        names = [i["name"] for i in data]
        assert "番茄" in names
        assert "鸡蛋" in names
        assert "西兰花" in names

    def test_remove_selection(self, api, state):
        ok(api.delete(f"/api/private-kitchen/selections/{state['pk_selection_id2']}", headers=auth(state)))
        data = ok(api.get("/api/private-kitchen/selections", headers=auth(state)))
        assert len(data) == 1

    def test_update_dish(self, api, state):
        data = ok(api.put(f"/api/private-kitchen/dishes/{state['pk_dish_id1']}", headers=auth(state), json={
            "recipe": "## 更新版步骤\n1. 先炒蛋\n2. 再炒番茄",
        }))
        assert "更新版" in data["recipe"]

    def test_delete_dish(self, api, state):
        ok(api.delete(f"/api/private-kitchen/dishes/{state['pk_dish_id2']}", headers=auth(state)))
        r = api.get(f"/api/private-kitchen/dishes/{state['pk_dish_id2']}", headers=auth(state))
        assert r.json()["code"] == 404


# ═══════════════════════════════════════════
#  10. 成就系统
# ═══════════════════════════════════════════

class Test10Achievements:

    def test_list_definitions(self, api, state):
        data = ok(api.get("/api/achievements", headers=auth(state)))
        assert len(data) >= 8
        names = [a["name"] for a in data]
        assert "初次约饭" in names

    def test_alice_progress(self, api, state):
        data = ok(api.get("/api/users/me/achievements", headers=auth(state)))
        assert isinstance(data, list)

    def test_bob_progress(self, api, state):
        data = ok(api.get("/api/users/me/achievements", headers=auth(state, 2)))
        assert isinstance(data, list)


# ═══════════════════════════════════════════
#  11. 爱情银行
# ═══════════════════════════════════════════

class Test11LoveBank:

    def test_accumulate_coins(self, api, state):
        """批量创建点餐记录以积累爱情币（每次 +10）"""
        before = ok(api.get("/api/users/me/love-coins", headers=auth(state)))
        needed = 1800 - before["balance"]
        n = max(0, (needed + 9) // 10)
        for i in range(n):
            api.post("/api/orders", headers=auth(state), json={
                "restaurant": f"积分测试餐厅{i}",
                "date": "2026-01-01",
                "dishes": [{"name": "测试菜", "price": 10}],
            })
        data = ok(api.get("/api/users/me/love-coins", headers=auth(state)))
        assert data["balance"] >= 1800
        state["alice_balance"] = data["balance"]

    def test_bob_balance(self, api, state):
        data = ok(api.get("/api/users/me/love-coins", headers=auth(state, 2)))
        assert data["balance"] >= 0

    def test_transactions(self, api, state):
        data = ok(api.get(
            "/api/users/me/love-coin-transactions?page=1&size=20",
            headers=auth(state),
        ))
        assert data["total"] >= 3

    def test_redeem_items(self, api, state):
        data = ok(api.get("/api/redeem-items", headers=auth(state)))
        assert len(data) >= 6
        names = [i["name"] for i in data]
        assert "免洗碗特权" in names
        assert "一星不生气券" in names

    def test_redeem_wash_free(self, api, state):
        data = ok(api.post("/api/redeem", headers=auth(state), json={"itemId": 1}))
        assert data["redemption_id"]

    def test_redeem_star1_x3(self, api, state):
        ids = []
        for _ in range(3):
            data = ok(api.post("/api/redeem", headers=auth(state), json={"itemId": 3}))
            ids.append(data["redemption_id"])
        state["star1_ids"] = ids

    def test_inventory(self, api, state):
        data = ok(api.get("/api/users/me/inventory", headers=auth(state)))
        assert len(data) >= 4
        star1_count = sum(1 for i in data if i["star_level"] == 1)
        assert star1_count >= 3

    def test_synthesize(self, api, state):
        data = ok(api.post("/api/redeem/synthesize", headers=auth(state), json={
            "itemIds": state["star1_ids"],
        }))
        assert data["redemption_id"]

    def test_inventory_after_synth(self, api, state):
        data = ok(api.get("/api/users/me/inventory", headers=auth(state)))
        star2 = [i for i in data if i["star_level"] == 2 and i["status"] == "redeemed"]
        assert len(star2) >= 1

    def test_balance_decreased(self, api, state):
        data = ok(api.get("/api/users/me/love-coins", headers=auth(state)))
        assert data["balance"] < state["alice_balance"]

    def test_insufficient_balance(self, api, state):
        for _ in range(50):
            r = api.post("/api/redeem", headers=auth(state), json={"itemId": 3})
            if r.json()["code"] != 200:
                assert r.json()["code"] == 400
                return
        assert False, "应在某次兑换时余额不足"


# ═══════════════════════════════════════════
#  12. 情绪温度计
# ═══════════════════════════════════════════

class Test12Moods:

    def test_all_stats(self, api, state):
        data = ok(api.get("/api/moods/statistics", headers=auth(state)))
        assert "user1" in data
        assert "user2" in data
        moods_u1 = {m["mood"] for m in data["user1"]}
        assert "暖" in moods_u1 or "甜" in moods_u1

    def test_date_range(self, api, state):
        data = ok(api.get(
            "/api/moods/statistics?startDate=2026-03-01&endDate=2026-03-31",
            headers=auth(state),
        ))
        assert "user1" in data


# ═══════════════════════════════════════════
#  13. 选择困难症拯救器
# ═══════════════════════════════════════════

class Test13Recommendations:

    def test_random(self, api, state):
        data = ok(api.get("/api/recommendations?count=3", headers=auth(state)))
        assert isinstance(data, list)

    def test_by_restaurant(self, api, state):
        data = ok(api.get(
            "/api/recommendations?restaurant=海底捞&count=2",
            headers=auth(state),
        ))
        assert isinstance(data, list)

    def test_by_mood(self, api, state):
        data = ok(api.get(
            "/api/recommendations?mood=甜&count=3",
            headers=auth(state),
        ))
        assert isinstance(data, list)


# ═══════════════════════════════════════════
#  14. 惊喜模式
# ═══════════════════════════════════════════

class Test14Surprise:

    def test_status(self, api, state):
        data = ok(api.get("/api/surprise-mode/status", headers=auth(state)))
        assert "active" in data


# ═══════════════════════════════════════════
#  15. 仪表盘
# ═══════════════════════════════════════════

class Test15Dashboard:

    def test_dashboard(self, api, state):
        data = ok(api.get("/api/dashboard", headers=auth(state)))
        assert "total_orders" in data
        assert data["total_orders"] >= 2
        assert data["total_restaurants"] >= 2
        assert "upcoming_anniversaries" in data
        assert "love_coin_balances" in data
        assert "recent_orders" in data


# ═══════════════════════════════════════════
#  16. 清理 / 删除操作
# ═══════════════════════════════════════════

class Test16Cleanup:

    def test_delete_order(self, api, state):
        before = ok(api.get("/api/orders?page=1&size=1", headers=auth(state)))
        total_before = before["total"]
        ok(api.delete(f"/api/orders/{state['order_id3']}", headers=auth(state)))
        after = ok(api.get("/api/orders?page=1&size=1", headers=auth(state)))
        assert after["total"] == total_before - 1

    def test_deleted_order_not_found(self, api, state):
        r = api.get(f"/api/orders/{state['order_id3']}", headers=auth(state))
        assert r.json()["code"] == 404
