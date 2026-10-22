import hashlib
import hmac
import os
import re
import secrets
import smtplib
import ssl
import time
from email.message import EmailMessage
from database import create_item, init_db, list_items

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Read Community Cloud secrets as environment settings, while keeping local .env support.
for secret_name in (
    "SCHOOL_EMAIL_DOMAIN",
    "EMAIL_VERIFY_MODE",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USER",
    "SMTP_PASSWORD",
    "SMTP_FROM",
    "SMTP_USE_SSL",
    "DATABASE_URL",
):
    if secret_name not in os.environ:
        try:
            secret_value = st.secrets.get(secret_name)
        except Exception:
            secret_value = None
        if secret_value is not None:
            os.environ[secret_name] = str(secret_value)

st.set_page_config(
    page_title="校园小咸鱼",
    page_icon="🐟",
    layout="wide",
)

init_db()


def verification_settings():
    domain = os.getenv("SCHOOL_EMAIL_DOMAIN", "xmu.edu.my").strip().lower().lstrip("@")
    configured_mode = os.getenv("EMAIL_VERIFY_MODE", "").strip().lower()
    smtp_ready = all(os.getenv(key) for key in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM"))
    mode = configured_mode or ("smtp" if smtp_ready else "dev")
    return domain, mode, smtp_ready


def valid_school_email(email, domain):
    if len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+", email):
        return False
    local, entered_domain = email.rsplit("@", 1)
    return bool(local) and entered_domain.lower() == domain


def send_code(email, code):
    message = EmailMessage()
    message["Subject"] = "校园小咸鱼邮箱验证码"
    message["From"] = os.environ["SMTP_FROM"]
    message["To"] = email
    message.set_content(f"你的校园小咸鱼验证码是：{code}\n验证码 10 分钟内有效，请勿转发给他人。")

    host = os.environ["SMTP_HOST"]
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASSWORD"]
    if os.getenv("SMTP_USE_SSL", "false").lower() in {"1", "true", "yes"}:
        with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=15) as server:
            server.login(username, password)
            server.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(username, password)
            server.send_message(message)


def issue_code(email, mode):
    code = f"{secrets.randbelow(1_000_000):06d}"
    if mode == "smtp":
        send_code(email, code)
    salt = secrets.token_bytes(16)
    st.session_state.email_code_hash = hashlib.sha256(salt + code.encode("ascii")).digest()
    st.session_state.email_code_salt = salt
    st.session_state.email_code_expires = time.time() + 600
    st.session_state.email_code_attempts = 0
    st.session_state.email_code_sent_at = time.time()
    st.session_state.email_pending = email
    if mode == "dev":
        # This demo code is intentionally shown in the UI and is not email verification.
        st.session_state.email_dev_code = code
    else:
        st.session_state.pop("email_dev_code", None)


st.title("🐟 校园小咸鱼")
st.caption("校园里的闲置好物、生活信息，都在这里发现。")

domain, verify_mode, smtp_ready = verification_settings()
with st.expander("🎓 学生邮箱验证", expanded=False):
    if verify_mode == "dev":
        st.warning("开发演示模式：验证码会显示在页面上，不会发送邮件，也不能证明你拥有该邮箱。")
    elif verify_mode != "smtp" or not smtp_ready:
        st.error("SMTP 配置不完整，邮箱验证暂不可用。请检查 .env 配置。")
    else:
        st.caption("使用学校邮箱接收一次性验证码。")

    if st.session_state.get("email_verified"):
        st.success(f"已在此浏览器会话中验证：{st.session_state.verified_email}")
    else:
        pending = st.session_state.get("email_pending")
        with st.form("school_email_form"):
            school_email = st.text_input(
                "学校邮箱",
                value=pending or "",
                placeholder=f"name@{domain}",
                disabled=bool(pending),
            )
            request_code = st.form_submit_button("发送验证码" if verify_mode == "smtp" else "生成演示验证码", disabled=bool(pending) or verify_mode not in {"smtp", "dev"})

        if request_code:
            email = school_email.strip()
            if not valid_school_email(email, domain):
                st.error(f"请输入有效的学校邮箱（@{domain}）。")
            elif verify_mode == "smtp" and not smtp_ready:
                st.error("SMTP 配置不完整，请先补齐邮件服务配置。")
            else:
                try:
                    issue_code(email, verify_mode)
                    st.rerun()
                except (KeyError, ValueError, OSError, smtplib.SMTPException):
                    st.error("验证码发送失败，请检查 SMTP 配置后重试。")

        pending = st.session_state.get("email_pending")
        if pending:
            if time.time() >= st.session_state.get("email_code_expires", 0):
                st.session_state.pop("email_pending", None)
                st.session_state.pop("email_code_hash", None)
                st.session_state.pop("email_dev_code", None)
                st.warning("验证码已过期，请重新申请。")
            else:
                if verify_mode == "dev":
                    st.info(f"演示验证码：{st.session_state.email_dev_code}（仅供本地演示）")
                st.caption("验证码 10 分钟有效，最多可尝试 5 次。")
                with st.form("verify_code_form"):
                    entered_code = st.text_input("6 位验证码", max_chars=6)
                    verify_code = st.form_submit_button("验证邮箱")

                if verify_code:
                    attempts = st.session_state.get("email_code_attempts", 0)
                    if attempts >= 5:
                        st.error("尝试次数已用完，请重新申请验证码。")
                    elif not re.fullmatch(r"\d{6}", entered_code):
                        st.error("请输入 6 位数字验证码。")
                    else:
                        st.session_state.email_code_attempts = attempts + 1
                        expected = hashlib.sha256(
                            st.session_state.email_code_salt + entered_code.encode("ascii")
                        ).digest()
                        if hmac.compare_digest(expected, st.session_state.email_code_hash):
                            st.session_state.email_verified = True
                            st.session_state.verified_email = pending
                            for key in ("email_pending", "email_code_hash", "email_code_salt", "email_code_expires", "email_dev_code"):
                                st.session_state.pop(key, None)
                            st.success("邮箱验证码通过。")
                            st.rerun()
                        else:
                            remaining = 4 - attempts
                            st.error(f"验证码不正确。还可尝试 {remaining} 次。")

                elapsed = time.time() - st.session_state.get("email_code_sent_at", 0)
                if elapsed >= 60 and st.button("重新发送验证码"):
                    try:
                        issue_code(pending, verify_mode)
                        st.rerun()
                    except (KeyError, ValueError, OSError, smtplib.SMTPException):
                        st.error("验证码发送失败，请检查 SMTP 配置后重试。")
                elif elapsed < 60:
                    st.caption(f"{max(1, 60 - int(elapsed))} 秒后可重新发送。")

st.divider()
st.subheader("发布闲置")
if not st.session_state.get("email_verified"):
    st.info("请先在上方完成学生邮箱验证，再发布商品。")
else:
    with st.expander("➕ 发布一个闲置商品"):
        with st.form("create_product_form"):
            product_name = st.text_input("商品名称", max_chars=50)
            product_category = st.selectbox("分类", ["教材资料", "数码产品", "生活用品", "运动户外"])
            product_price = st.number_input("价格（元）", min_value=0.0, max_value=99999.0, value=10.0, step=1.0)
            seller_name = st.text_input("你的昵称", max_chars=20)
            product_description = st.text_area("商品描述", max_chars=300, placeholder="介绍新旧程度、交易地点等")
            publish = st.form_submit_button("发布商品")

        if publish:
            if not product_name.strip() or not seller_name.strip():
                st.error("请填写商品名称和昵称。")
            else:
                create_item(
                    product_name.strip(),
                    product_category,
                    product_price,
                    seller_name.strip(),
                    st.session_state.verified_email,
                    product_description.strip(),
                )
                st.success("商品已发布。")
                st.rerun()

search_text = st.text_input(
    "🔍 搜一搜",
    placeholder="试试搜索：教材、自行车、台灯……",
)

st.subheader("逛逛分类")
categories = ["全部", "教材资料", "数码产品", "生活用品", "运动户外"]
selected_category = st.radio(
    "选择分类",
    categories,
    horizontal=True,
    label_visibility="collapsed",
)

st.divider()
st.subheader("校园热门")

items = list_items()

shown_items = [
    item for item in items
    if selected_category == "全部" or item["category"] == selected_category
]

if search_text:
    shown_items = [
        item for item in shown_items
        if search_text.lower() in item["name"].lower()
    ]

if not shown_items:
    st.info("没有找到相关商品，换个关键词或分类试试。")
else:
    columns = st.columns(2)

    for index, item in enumerate(shown_items):
        with columns[index % 2]:
            with st.container(border=True):
                st.markdown(f"### {item['name']}")
                st.write(f"分类：{item['category']}　·　发布者：{item['seller']}")
                st.markdown(f"**¥{item['price']:g}**")
                if item["description"]:
                    st.caption(item["description"])

st.divider()
st.caption("校园小咸鱼 · 让闲置流动起来")
