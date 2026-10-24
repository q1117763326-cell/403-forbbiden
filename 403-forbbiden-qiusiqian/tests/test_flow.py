import re
import sqlite3
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

import database
from text_utils import mask_email

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


def test_mask_email():
    assert mask_email("alice@xmu.edu.my") == "a***@xmu.edu.my"
    assert mask_email("A@xmu.edu.my") == "A***@xmu.edu.my"
    assert mask_email(" alice@xmu.edu.my ") == "a***@xmu.edu.my"
    for invalid in ("", "alice", "@xmu.edu.my", "alice@", "alice@@xmu.edu.my", None, 123):
        assert mask_email(invalid) == ""


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
