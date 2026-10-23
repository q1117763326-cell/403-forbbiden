import hashlib
import base64
import hmac
import os
import re
import secrets
import smtplib
import ssl
import time
from pathlib import Path
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
    page_title="厦了么鱼 · XMUM 校园市集",
    page_icon="🐟",
    layout="wide",
)

# Load the Jiageng-inspired theme. All business logic below remains unchanged.
css_file = Path(__file__).parent / "styles.css"
if css_file.exists():
    css = css_file.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

hero_file = Path(__file__).parent / "assets" / "campus_building.jpg"
if hero_file.is_file():
    hero_data = base64.b64encode(hero_file.read_bytes()).decode("ascii")
    hero_source = f"data:image/jpeg;base64,{hero_data}"
else:
    hero_source = ""
    st.warning(f"校园横幅图片缺失：{hero_file}。请确认 assets 文件夹已一并复制。")

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
    message["Subject"] = "厦了么鱼邮箱验证码"
    message["From"] = os.environ["SMTP_FROM"]
    message["To"] = email
    message.set_content(f"你的厦了么鱼验证码是：{code}\n验证码 10 分钟内有效，请勿转发给他人。")

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


st.markdown(f"""
<div class="top-brand">
  <div class="brand-seal">厦</div>
  <div class="brand-copy">
    <div class="brand-cn">厦门大学马来西亚分校</div>
    <div class="brand-en">XIAMEN UNIVERSITY MALAYSIA</div>
  </div>
  <div class="brand-divider"></div>
  <div class="market-brand"><span class="fish-mark">🐟</span><span><b>厦了么鱼</b><small>让闲置流转 · 让校园更有温度</small></span></div>
  <div class="top-nav"><span class="nav-active">⌂　首页</span><span>商品分类</span><span>发布商品</span><span>关于我们</span><span class="nav-cert">◉　学生认证</span></div>
</div>
<div class="hero-banner" style="position:relative;isolation:isolate;overflow:hidden;min-height:290px;border-radius:18px;background:#d9e5df;">
  <img class="hero-background" src="{hero_source}" alt="嘉庚风格校园建筑" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:center 48%;z-index:0;" />
  <div class="hero-copy">
    <div class="hero-eyebrow">XMUM CAMPUS MARKETPLACE</div>
    <div class="hero-title">厦了么鱼</div>
    <div class="hero-subtitle">让闲置流转 · 让校园更有温度</div>
    <div class="hero-note">在厦马，遇见更好的校园生活</div>
  </div>
  <div class="hero-stamp">嘉庚精神<br/>薪火相传</div>
</div>
""", unsafe_allow_html=True)

main_col, side_col = st.columns([3.25, 1], gap="large")

with main_col:
    st.markdown("""<div class="intro-strip"><span>📚 教材书籍</span><span>💻 电子产品</span><span>⌂ 宿舍生活</span><span>♧ 服饰箱包</span><span>⚽ 运动户外</span><span>✣ 其他分类</span></div>""", unsafe_allow_html=True)

with side_col:
    st.markdown("""<div class="side-login"><div class="side-login-icon">⌂</div><b>欢迎来到厦了么鱼</b><small>登录后体验更多功能</small></div>""", unsafe_allow_html=True)
with side_col:
    domain, verify_mode, smtp_ready = verification_settings()
    with st.expander("🎓 学生邮箱验证 · 校园身份认证", expanded=False):
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

with side_col:
        st.markdown("""<div class="side-promo"><small>XMUM CAMPUS MARKET</small><b>校园二手交易<br>让好物继续发光</b></div>""", unsafe_allow_html=True)
        st.image(str(Path(__file__).parent / "assets" / "campus_building.jpg"), use_container_width=True)

with main_col:
    with st.expander("➕ 发布闲置好物", expanded=False):
        if not st.session_state.get("email_verified"):
            st.info("请先在右侧完成学生邮箱验证，再发布商品。")
        else:
            with st.form("create_product_form"):
                product_name = st.text_input("商品名称", max_chars=50)
                product_category = st.selectbox("分类", ["教材资料", "数码产品", "生活用品", "运动户外"])
                product_price = st.number_input("价格（RM）", min_value=0.0, max_value=99999.0, value=10.0, step=1.0)
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

    st.subheader("按分类发现好物")
    categories = ["全部", "教材资料", "数码产品", "生活用品", "运动户外"]
    selected_category = st.radio(
        "选择分类",
        categories,
        horizontal=True,
        label_visibility="collapsed",
    )

    st.divider()
    st.subheader("校园热门推荐")

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
        # Category artwork is bundled locally, so cards never depend on remote image URLs.
        category_art = {
            "教材资料": "product_books.jpg",
            "数码产品": "product_tech.jpg",
            "生活用品": "product_lifestyle.jpg",
            "服饰箱包": "product_bag.jpg",
            "运动户外": "product_sports.svg",
        }
        columns = st.columns(3)

        for index, item in enumerate(shown_items):
            with columns[index % 3]:
                with st.container(border=True):
                    art_path = Path(__file__).parent / "assets" / category_art.get(item["category"], "product_lifestyle.jpg")
                    if art_path.suffix.lower() == ".svg" and art_path.exists():
                        art_data = base64.b64encode(art_path.read_bytes()).decode("ascii")
                        st.markdown(f'<div class="product-icon"><img src="data:image/svg+xml;base64,{art_data}" alt="{item["category"]}分类图"></div>', unsafe_allow_html=True)
                    elif art_path.exists():
                        st.image(str(art_path), use_container_width=True)
                    st.markdown(f"### {item['name']}")
                    st.markdown(f'<span class="category-pill">{item["category"]}</span>', unsafe_allow_html=True)
                    st.markdown(f'<div class="product-price">RM {item["price"]:g}</div>', unsafe_allow_html=True)
                    st.caption(f"发布者：{item['seller']}")
                    if item["description"]:
                        st.caption(item["description"])

    st.markdown("""
    <div class="campus-footer-banner"><div><b>在厦马 · 遇见更好的校园生活</b><span>Better Campus · Better Life</span></div><div class="footer-line-art">⌂　⌂　⌂</div></div>
    <div class="site-footer"><b>🐟 厦了么鱼</b><span>自强不息 · 止于至善</span><small>XMUM Campus Market · 让闲置流动起来</small></div>
    """, unsafe_allow_html=True)
