import re
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

import database
from brand_assets import CATEGORY_ARTWORK, CATEGORY_ICONS
from search_utils import search_items, sort_items, suggest_similar_items
from text_utils import format_relative_time, mask_email

HOME = APP_DIR / "首页.py"
PUBLISH_PAGE = "pages/3_发布商品.py"


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    """Point the app at a throwaway SQLite file for every test."""
    production_db = APP_DIR / "campus_market.db"
    production_db_existed = production_db.exists()

    monkeypatch.chdir(APP_DIR)
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("EMAIL_VERIFY_MODE", "dev")
    monkeypatch.setenv("SCHOOL_EMAIL_DOMAIN", "xmu.edu.my")
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test_campus_market.db")
    monkeypatch.setattr(database, "_schema_ready", False)

    yield

    assert production_db.exists() == production_db_existed, (
        "tests must not create or remove the production campus_market.db"
    )


def start_home(verified_email=None):
    app = AppTest.from_file(str(HOME), default_timeout=30)
    if verified_email:
        app.session_state["email_verified"] = True
        app.session_state["verified_email"] = verified_email
    app.run()
    assert not app.exception, app.exception
    return app


def widget(elements, label):
    return next(element for element in elements if element.label == label)


def click(app, label):
    widget(app.button, label).click()
    app.run()
    assert not app.exception, app.exception


def combined_text(app):
    values = []
    for collection in (app.markdown, app.caption, app.info, app.success, app.warning, app.error):
        values.extend(element.value or "" for element in collection)
    return "\n".join(values)


def request_dev_code(app, email):
    widget(app.text_input, "学校邮箱").set_value(email)
    click(app, "生成演示验证码")
    info_text = "\n".join(info.value for info in app.info)
    match = re.search(r"(\d{6})", info_text)
    assert match, info_text
    return match.group(1)


def test_mask_email():
    assert mask_email("alice@xmu.edu.my") == "a***@xmu.edu.my"
    assert mask_email("A@xmu.edu.my") == "A***@xmu.edu.my"
    assert mask_email(" alice@xmu.edu.my ") == "a***@xmu.edu.my"
    for invalid in ("", "alice", "@xmu.edu.my", "alice@", "alice@@xmu.edu.my", None, 123):
        assert mask_email(invalid) == ""


def test_format_relative_time():
    now = datetime.now(timezone.utc)
    three_days_ago = now - timedelta(days=3)
    assert format_relative_time(three_days_ago.isoformat()) == "3 天前"
    assert format_relative_time(three_days_ago.strftime("%Y-%m-%d %H:%M:%S")) == "3 天前"
    assert format_relative_time((now - timedelta(hours=2)).isoformat()) == "2 小时前"
    assert format_relative_time("not-a-date") == "not-a-date"
    assert format_relative_time(None) == ""


def test_invalid_school_email_domain_is_rejected():
    app = start_home()
    widget(app.text_input, "学校邮箱").set_value("alice@gmail.com")
    click(app, "生成演示验证码")

    assert any("请输入有效的学校邮箱" in error.value for error in app.error)
    assert not app.session_state.get("email_pending")


def test_wrong_and_expired_verification_code():
    app = start_home()
    widget(app.text_input, "学校邮箱").set_value("student@xmu.edu.my")
    click(app, "生成演示验证码")

    info_text = "\n".join(info.value for info in app.info)
    code_match = re.search(r"(\d{6})", info_text)
    assert code_match, info_text
    code = code_match.group(1)
    wrong_code = "000000" if code != "000000" else "111111"

    widget(app.text_input, "6 位验证码").set_value(wrong_code)
    click(app, "验证邮箱")
    assert any("验证码不正确" in error.value for error in app.error)
    assert not app.session_state.get("email_verified")

    app.session_state["email_code_expires"] = 0
    app.run()
    assert any("验证码已过期" in warning.value for warning in app.warning)
    assert not app.session_state.get("email_pending")


def test_unauthenticated_publish_page_is_blocked():
    app = start_home()
    app.switch_page(PUBLISH_PAGE).run()
    assert not app.exception, app.exception

    warnings = "\n".join(warning.value for warning in app.warning)
    assert "发布商品前，请先完成学生邮箱验证" in warnings
    assert not any(field.label == "商品名称 *" for field in app.text_input)


def test_publish_persists_item_and_masks_email():
    seller_email = "seller@xmu.edu.my"
    app = start_home(seller_email)

    widget(app.text_input, "商品名称").set_value("测试教材")
    widget(app.text_input, "你的昵称").set_value("卖家A")
    widget(app.text_input, "联系方式（选填，公开展示）").set_value("wxid_test")
    click(app, "发布商品")

    items = database.list_items(viewer_email=seller_email)
    item = next(item for item in items if item["name"] == "测试教材")
    assert item["contact"] == "wxid_test"
    assert item["status"] == "available"
    assert item["is_mine"] is True

    connection = sqlite3.connect(database.DB_PATH)
    row = connection.execute(
        "SELECT seller_email FROM products WHERE name = ?", ("测试教材",)
    ).fetchone()
    connection.close()
    assert row[0] == seller_email

    visible_text = combined_text(app)
    assert "s***@xmu.edu.my" in visible_text
    assert seller_email not in visible_text


def test_publish_page_masks_verified_email():
    seller_email = "page3@xmu.edu.my"
    app = start_home(seller_email)
    app.switch_page(PUBLISH_PAGE).run()
    assert not app.exception, app.exception

    visible_text = combined_text(app)
    assert "p***@xmu.edu.my" in visible_text
    assert seller_email not in visible_text


def test_javascript_contact_is_rejected():
    seller_email = "seller@xmu.edu.my"
    app = start_home(seller_email)

    widget(app.text_input, "商品名称").set_value("非法联系方式商品")
    widget(app.text_input, "你的昵称").set_value("卖家A")
    widget(app.text_input, "联系方式（选填，公开展示）").set_value("javascript:alert(1)")
    click(app, "发布商品")

    assert any("联系方式格式无效" in error.value for error in app.error)
    assert all(
        item["name"] != "非法联系方式商品"
        for item in database.list_items(viewer_email=seller_email)
    )


def test_sold_item_is_filtered_and_owner_only():
    seller_email = "seller@xmu.edu.my"
    database.create_item(
        "待售商品",
        "教材资料",
        10.0,
        "卖家A",
        seller_email,
        "测试",
        "",
    )

    app = start_home(seller_email)
    assert any(button.label == "标记已售出" for button in app.button)
    other_view = database.list_items(viewer_email="other@xmu.edu.my")
    other_item = next(item for item in other_view if item["name"] == "待售商品")
    assert other_item["is_mine"] is False

    click(app, "标记已售出")
    assert "待售商品" not in combined_text(app)

    available = database.list_items(viewer_email=seller_email)
    assert all(item["name"] != "待售商品" for item in available)
    all_items = database.list_items(include_sold=True, limit=None)
    sold = next(item for item in all_items if item["name"] == "待售商品")
    assert sold["status"] == "sold"
    stats = database.get_item_stats()
    assert stats["sold"] >= 1
    assert stats["total"] == stats["available"] + stats["sold"]


def test_about_shows_sold_and_available_stats():
    database.create_item(
        "已售统计商品",
        "服饰箱包",
        20.0,
        "卖家A",
        "stats@xmu.edu.my",
        "测试",
        "",
    )
    sold_item = next(
        item for item in database.list_items(limit=None) if item["name"] == "已售统计商品"
    )
    assert database.mark_item_sold(sold_item["id"], "stats@xmu.edu.my") is True

    app = start_home()
    app.switch_page("pages/4_关于我们.py").run()
    assert not app.exception, app.exception
    text = combined_text(app)
    assert "已让 1 件闲置继续使用" in text
    assert "在售 24 件" in text
    assert "共 25 件" in text


def test_list_items_default_limit():
    database.ensure_schema()
    seeded_count = len(database.list_items(limit=None))
    with database.connect() as connection:
        connection.executemany(
            database._query(
                "INSERT INTO products (name, category, price, seller, description) "
                "VALUES (?, ?, ?, ?, ?)"
            ),
            [(f"批量商品 {index}", "生活用品", 1.0, "同学", "") for index in range(205)],
        )

    assert len(database.list_items()) == 200
    assert len(database.list_items(limit=None)) == seeded_count + 205
    assert len(database.list_items(limit=3)) == 3


def test_seed_uses_all_categories():
    assert len(database.SAMPLE_ITEMS) == 24
    assert {item[1] for item in database.SAMPLE_ITEMS} == set(database.CATEGORIES)
    assert set(CATEGORY_ARTWORK) == set(database.CATEGORIES)
    assert set(CATEGORY_ICONS) == set(database.CATEGORIES)
    assert CATEGORY_ARTWORK["服饰箱包"] == "product_bag.jpg"


def test_search_multi_word_and_synonyms():
    items = [
        {"id": 1, "name": "笔记本电脑", "category": "数码产品", "description": "九成新", "seller": "小林"},
        {"id": 2, "name": "高数教材", "category": "教材资料", "description": "书", "seller": "小陈"},
        {"id": 3, "name": "宿舍台灯", "category": "生活用品", "description": "照明正常", "seller": "阿明"},
        {"id": 4, "name": "山地自行车", "category": "运动户外", "description": "骑行", "seller": "小宇"},
        {"id": 5, "name": "二手手机", "category": "数码产品", "description": "备用机", "seller": "阿欣"},
    ]

    assert [item["name"] for item in search_items(items, "电脑")] == ["笔记本电脑"]
    assert [item["name"] for item in search_items(items, "书")] == ["高数教材"]
    assert [item["name"] for item in search_items(items, "灯")] == ["宿舍台灯"]
    assert [item["name"] for item in search_items(items, "单车")] == ["山地自行车"]
    assert [item["name"] for item in search_items(items, "手机")] == ["二手手机"]
    assert [item["name"] for item in search_items(items, "电脑 九成新")] == ["笔记本电脑"]
    assert search_items(items, "电脑 台灯") == []
    assert [item["name"] for item in search_items(items, "阿明")] == ["宿舍台灯"]


def test_search_relevance_and_suggestions():
    items = [
        {"id": 1, "name": "台灯", "category": "生活用品", "description": "", "seller": ""},
        {"id": 2, "name": "宿舍用品", "category": "台灯", "description": "", "seller": ""},
        {"id": 3, "name": "普通商品", "category": "生活用品", "description": "台灯", "seller": ""},
        {"id": 4, "name": "台灯", "category": "生活用品", "description": "", "seller": ""},
    ]
    ranked = search_items(items, "台灯")
    assert [item["id"] for item in ranked] == [4, 1, 2, 3]

    names = [{"name": "高数教材"}, {"name": "宿舍台灯"}]
    assert suggest_similar_items(names, "高数教才") == ["高数教材"]


def test_price_sorting_high_and_low():
    items = [
        {"id": 1, "price": 5.0},
        {"id": 2, "price": 10.0},
        {"id": 3, "price": 10.0},
    ]
    assert [item["id"] for item in sort_items(items, "价格从低到高")] == [1, 3, 2]
    assert [item["id"] for item in sort_items(items, "价格从高到低")] == [3, 2, 1]


def test_home_search_and_suggestions():
    app = start_home()

    widget(app.text_input, "🔍 搜一搜").set_value("电脑")
    app.run()
    text = combined_text(app)
    assert "笔记本电脑（轻薄款）" in text
    assert "宿舍台灯" not in text

    widget(app.text_input, "🔍 搜一搜").set_value("单车")
    app.run()
    assert "山地自行车" in combined_text(app)

    widget(app.text_input, "🔍 搜一搜").set_value("高数教才")
    app.run()
    text = combined_text(app)
    assert "你是不是想找" in text
    assert "高数教材" in text


def test_category_price_sort_high_to_low():
    app = start_home()
    app.switch_page("pages/2_商品分类.py").run()
    assert not app.exception, app.exception

    widget(app.selectbox, "排序方式").set_value("价格从高到低")
    app.run()
    assert not app.exception, app.exception

    cards = [
        markdown.value
        for markdown in app.markdown
        if '<div class="product-card">' in (markdown.value or "")
    ]
    assert len(cards) >= 2
    assert "笔记本电脑（轻薄款）" in cards[0]
    assert "RM 450.00" in cards[0]
    assert "发布于" in cards[0]
    assert "二手手机" in "\n".join(cards)


def test_create_item_server_validation():
    baseline = {
        "name": "校验商品",
        "category": "教材资料",
        "price": 10.0,
        "seller": "卖家",
        "seller_email": "validation@xmu.edu.my",
        "description": "",
        "contact": "",
    }
    invalid_updates = [
        {"name": ""},
        {"name": "x" * 51},
        {"seller": ""},
        {"seller": "x" * 21},
        {"description": "x" * 301},
        {"contact": "x" * 41},
        {"contact": "javascript:alert(1)"},
        {"category": "其他分类"},
        {"price": -1},
        {"price": 100000},
        {"price": float("nan")},
    ]
    for updates in invalid_updates:
        with pytest.raises(ValueError):
            database.create_item(**{**baseline, **updates})


def test_duplicate_item_is_rejected():
    kwargs = {
        "name": "重复提交测试",
        "category": "教材资料",
        "price": 12.5,
        "seller": "卖家",
        "seller_email": "duplicate@xmu.edu.my",
        "description": "第一次",
        "contact": "",
    }
    database.create_item(**kwargs)
    with pytest.raises(ValueError, match="请勿重复提交"):
        database.create_item(**kwargs)

    with database.connect() as connection:
        connection.execute(
            "UPDATE products SET created_at = datetime('now', '-2 minutes') "
            "WHERE name = ? AND seller_email = ?",
            (kwargs["name"], kwargs["seller_email"]),
        )
    database.create_item(**kwargs)


def test_verification_failure_lockout_and_clear():
    email = "locked@xmu.edu.my"
    for _ in range(9):
        database.record_verification_failure(email)
    assert database.verification_lockout_remaining(email) == 0

    database.record_verification_failure(email)
    assert database.verification_lockout_remaining(email) > 0

    with database.connect() as connection:
        rows = connection.execute("SELECT email_hash FROM verification_failures").fetchall()
    assert rows and all(email not in row["email_hash"] for row in rows)

    database.clear_verification_failures(email)
    assert database.verification_lockout_remaining(email) == 0


def test_change_email_clears_pending_state():
    app = start_home()
    request_dev_code(app, "change@xmu.edu.my")
    assert app.session_state.get("email_pending")

    click(app, "换一个邮箱")
    for key in (
        "email_pending",
        "email_code_hash",
        "email_code_salt",
        "email_code_expires",
        "email_code_attempts",
        "email_code_sent_at",
        "email_dev_code",
    ):
        assert not app.session_state.get(key)


def test_exit_verification_clears_verified_state():
    app = start_home()
    email = "exit@xmu.edu.my"
    code = request_dev_code(app, email)

    database.record_verification_failure(email)
    widget(app.text_input, "6 位验证码").set_value(code)
    click(app, "验证邮箱")
    assert app.session_state.get("email_verified") is True

    with database.connect() as connection:
        remaining_failures = connection.execute(
            "SELECT COUNT(*) AS failure_count FROM verification_failures"
        ).fetchone()["failure_count"]
    assert remaining_failures == 0

    click(app, "退出验证")
    assert not app.session_state.get("email_verified")
    assert not app.session_state.get("verified_email")
