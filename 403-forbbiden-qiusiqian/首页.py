import hashlib
import html
import hmac
import logging
import os
import re
import secrets
import smtplib
import ssl
import time
from pathlib import Path
from email.message import EmailMessage
from database import (
    check_and_log_verification,
    create_item,
    ensure_schema,
    list_items,
    normalize_contact,
)
from brand_assets import add_navigation_mascot_markers, image_data_uri
from product_ui import render_contact_and_sale_actions

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

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
add_navigation_mascot_markers()

hero_source = image_data_uri("campus_building.jpg")
mascot_avatar_source = image_data_uri("mascot_avatar.png")
mascot_moods = {
    "happy": image_data_uri("mascot_happy.png"),
    "wink": image_data_uri("mascot_wink.png"),
    "cheer": image_data_uri("mascot_cheer.png"),
    "confused": image_data_uri("mascot_confused.png"),
    "serious": image_data_uri("mascot_serious.png"),
    "sleep": image_data_uri("mascot_sleep.png"),
}

ensure_schema()


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
    try:
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
    except Exception as exc:
        # SMTP exceptions can embed the recipient address; log only the type
        # here and let the caller log a sanitized traceback.
        logger.warning("SMTP delivery failed (%s)", type(exc).__name__)
        raise RuntimeError("验证码邮件发送失败") from None


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


def render_top_navigation():
    """Use Streamlit's own navigation so moving between pages keeps the session.

    A full-page anchor would reload the browser and reset the in-session
    student-verification state.
    """
    with st.container(key="top_brand_bar"):
        brand_col, nav_col = st.columns([1.15, 3.2], gap="small", vertical_alignment="center")
        with brand_col:
            st.markdown(
                f'<div class="market-brand"><img class="brand-avatar" src="{mascot_avatar_source}" alt="厦了么鱼头像"/>'
                '<span><b>厦了么鱼</b><small>让闲置流转 · 让校园更有温度</small></span></div>',
                unsafe_allow_html=True,
            )
        with nav_col:
            with st.container(
                horizontal=True,
                horizontal_alignment="right",
                vertical_alignment="center",
                gap="small",
                key="top_nav_links",
            ):
                with st.container(key="top_nav_home", width="content"):
                    st.page_link("首页.py", label="⌂ 首页")
                st.page_link("pages/2_商品分类.py", label="商品分类")
                st.page_link("pages/3_发布商品.py", label="发布商品")
                st.page_link("pages/4_关于我们.py", label="关于我们")
                with st.container(key="top_nav_cert", width="content"):
                    if st.button("◉ 学生认证", key="nav_cert", type="tertiary", width="content"):
                        st.session_state["scroll_to_verification"] = True


render_top_navigation()

st.markdown(f"""
<div class="hero-banner" style="position:relative;isolation:isolate;overflow:hidden;min-height:290px;border-radius:18px;background:#d9e5df;">
  <img class="hero-background" src="{hero_source}" alt="嘉庚风格校园建筑" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:center 48%;z-index:0;" />
  <div class="hero-moods" aria-label="厦了么鱼吉祥物表情">
    <img src="{mascot_moods['happy']}" alt="开心的小鱼"/>
    <img src="{mascot_moods['wink']}" alt="比心的小鱼"/>
    <img src="{mascot_moods['cheer']}" alt="加油的小鱼"/>
  </div>
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
    st.markdown(f"""<div class="side-login"><img class="side-login-avatar" src="{mascot_moods['wink']}" alt="比心的小鱼"/><b>欢迎来到厦了么鱼</b><small>完成学生认证后即可发布闲置</small></div>""", unsafe_allow_html=True)
with side_col:
        st.markdown("""<div class="side-promo"><small>XMUM CAMPUS MARKET</small><b>校园二手交易<br>让好物继续发光</b></div>""", unsafe_allow_html=True)
        st.markdown(f'<img class="side-promo-image" src="{hero_source}" alt="校园建筑" />', unsafe_allow_html=True)

with main_col:
    with st.expander("➕ 发布闲置好物", expanded=False):
        if not st.session_state.get("email_verified"):
            st.info("请先在页面底部完成学生认证，再发布商品。")
        else:
            with st.form("create_product_form"):
                product_name = st.text_input("商品名称", max_chars=50)
                product_category = st.selectbox("分类", ["教材资料", "数码产品", "生活用品", "运动户外"])
                product_price = st.number_input("价格（RM）", min_value=0.0, max_value=99999.0, value=10.0, step=1.0)
                seller_name = st.text_input("你的昵称", max_chars=20)
                product_description = st.text_area("商品描述", max_chars=300, placeholder="介绍新旧程度、交易地点等")
                product_contact = st.text_input(
                    "联系方式（选填，公开展示）",
                    max_chars=40,
                    placeholder="WhatsApp / Telegram 链接或微信号",
                    help="可填 WhatsApp / Telegram 链接或微信号，请勿填写学校邮箱",
                )
                publish = st.form_submit_button("发布商品")

            if publish:
                if not product_name.strip() or not seller_name.strip():
                    st.error("请填写商品名称和昵称。")
                else:
                    try:
                        contact = normalize_contact(product_contact)
                    except ValueError as exc:
                        st.error(str(exc))
                    else:
                        try:
                            create_item(
                                product_name.strip(),
                                product_category,
                                product_price,
                                seller_name.strip(),
                                st.session_state.verified_email,
                                product_description.strip(),
                                contact,
                            )
                        except Exception:
                            logger.exception("Failed to create a product from the home page")
                            st.error("商品发布失败，请稍后重试。")
                        else:
                            st.success("商品已发布。")

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

    viewer_email = (
        st.session_state.get("verified_email")
        if st.session_state.get("email_verified")
        else None
    )
    try:
        items = list_items(viewer_email=viewer_email)
    except Exception:
        logger.exception("Failed to load products for the home page")
        st.error("商品加载失败，请稍后重试。")
        items = []

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
                    art_name = category_art.get(item["category"], "product_lifestyle.jpg")
                    art_source = image_data_uri(art_name)
                    avatar_mood = list(mascot_moods.values())[index % len(mascot_moods)]
                    st.markdown(f'<div class="product-icon"><img src="{art_source}" alt="{item["category"]}分类图"></div>', unsafe_allow_html=True)
                    st.markdown(f"### {item['name']}")
                    st.markdown(f'<span class="category-pill">{item["category"]}</span>', unsafe_allow_html=True)
                    st.markdown(f'<div class="product-price">RM {item["price"]:g}</div>', unsafe_allow_html=True)
                    seller_text = html.escape(str(item["seller"]))
                    st.markdown(f'<div class="seller-row"><img src="{avatar_mood}" alt="厦了么鱼表情头像"/><span>发布者：<b>{seller_text}</b></span></div>', unsafe_allow_html=True)
                    if item["description"]:
                        st.caption(item["description"])
                    render_contact_and_sale_actions(
                        item,
                        key_prefix="home",
                        viewer_email=viewer_email,
                    )


st.markdown(
    '<div id="student-email-verification" class="student-auth-anchor"></div>'
    '<div class="student-auth-heading"><span>🎓</span><div><b>学生认证 · 校园身份验证</b>'
    '<small>完成校园身份验证后，即可发布闲置商品</small></div></div>',
    unsafe_allow_html=True,
)
domain, verify_mode, smtp_ready = verification_settings()
with st.expander(
    "🎓 学生邮箱验证 · 校园身份认证",
    expanded=True,
):
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
            elif not check_and_log_verification(email):
                st.error("请求过于频繁，请稍后再试。")
            else:
                try:
                    issue_code(email, verify_mode)
                    st.rerun()
                except Exception:
                    logger.exception("Failed to issue a verification code")
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
                    if not check_and_log_verification(pending):
                        st.error("请求过于频繁，请稍后再试。")
                    else:
                        try:
                            issue_code(pending, verify_mode)
                            st.rerun()
                        except Exception:
                            logger.exception("Failed to resend a verification code")
                            st.error("验证码发送失败，请检查 SMTP 配置后重试。")
                elif elapsed < 60:
                    st.caption(f"{max(1, 60 - int(elapsed))} 秒后可重新发送。")

st.markdown(f"""
<div class="campus-footer-banner"><div><b>在厦马 · 遇见更好的校园生活</b><span>Better Campus · Better Life</span></div><div class="footer-line-art">⌂　⌂　⌂</div></div>
<div class="site-footer"><b><img class="footer-mascot-avatar" src="{mascot_avatar_source}" alt=""/> 厦了么鱼</b><span>自强不息 · 止于至善</span><small>XMUM Campus Marketplace · 让闲置流动起来</small></div>
""", unsafe_allow_html=True)

# The 学生认证 button only sets a session flag, so navigation stays in-app.
# This small same-origin bridge scrolls the Streamlit document after the
# verification section has been rendered. It no longer depends on nav markup.
scroll_requested = st.session_state.pop("scroll_to_verification", False)
st.iframe(
    """<!doctype html><html><body><script>
    (() => {
      try {
        const host = window.parent;
        const requested = %s;
        const hasFragment = host.location.hash === '#student-email-verification';
        if (!requested && !hasFragment) return;
        const scrollToVerification = () => {
          const target = host.document.getElementById('student-email-verification');
          if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        };
        window.setTimeout(scrollToVerification, 150);
        window.setTimeout(scrollToVerification, 500);
      } catch (_) {
        // Scrolling is an enhancement; the section is still present without it.
      }
    })();
    </script></body></html>""" % ("true" if scroll_requested else "false"),
    width="stretch",
    height=1,
    tab_index=-1,
)

