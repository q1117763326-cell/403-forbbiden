import logging

import streamlit as st
from database import CATEGORIES, create_item
from brand_assets import add_navigation_mascot_markers, image_data_uri
from text_utils import mask_email

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="发布商品 · 厦了么鱼",
    page_icon="🐟",
    layout="wide",
)
add_navigation_mascot_markers()

mascot_avatar = image_data_uri("mascot_avatar.png")
mascot_happy = image_data_uri("mascot_happy.png")

st.markdown(
    """
    <style>
    .block-container {
        max-width: 1180px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    .publish-hero {
        padding: 32px 36px;
        border: 1px solid #dce6dc;
        border-radius: 22px;
        background: linear-gradient(120deg, #e6eee7, #f3eee2);
        margin-bottom: 24px;
    }

    .publish-hero small {
        color: #5c7966;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 2px;
    }

    .publish-hero h1 {
        color: #263d32;
        font-size: 36px;
        margin: 10px 0 6px 0;
    }

    .publish-hero p {
        color: #5d6f62;
        font-size: 16px;
        margin: 0;
    }

    .side-note {
        padding: 20px;
        border: 1px solid #e3e9e1;
        border-radius: 18px;
        background: #fffefa;
        color: #526459;
        line-height: 1.7;
    }

    .publish-mascot { width:92px; height:92px; object-fit:cover; border-radius:22px; float:right; margin:0 0 8px 12px; }
    .publish-avatar { width:34px; height:34px; object-fit:cover; border-radius:50%; vertical-align:middle; margin-right:8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="publish-hero">
        <small>GIVE YOUR ITEMS A SECOND LIFE</small>
        <h1>发布一件闲置好物 📦</h1>
        <p>填写商品信息，让校园里的好物继续发挥价值。</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if not st.session_state.get("email_verified"):
    st.warning("发布商品前，请先完成学生邮箱验证。")
    st.page_link("首页.py", label="去完成学生邮箱验证")
else:
    form_col, note_col = st.columns([2, 1], gap="large")

    with form_col:
        with st.container(border=True):
            st.subheader("商品信息")
            st.caption("带 * 的内容请填写完整。")

            with st.form("publish_item_form"):
                name = st.text_input("商品名称 *", max_chars=50)

                category = st.selectbox(
                    "商品分类 *",
                    CATEGORIES,
                )

                price = st.number_input(
                    "价格（RM）*",
                    min_value=0.0,
                    max_value=99999.0,
                    value=10.0,
                    step=0.5,
                    format="%.2f",
                )

                seller = st.text_input("你的昵称 *", max_chars=20)

                description = st.text_area(
                    "商品描述",
                    max_chars=300,
                    placeholder="可以介绍新旧程度、配件情况和方便交易的地点。",
                    height=130,
                )

                contact = st.text_input(
                    "联系方式（选填，公开展示）",
                    max_chars=40,
                    placeholder="WhatsApp / Telegram 链接或微信号",
                    help="可填 WhatsApp / Telegram 链接或微信号，请勿填写学校邮箱",
                )

                submitted = st.form_submit_button(
                    "发布商品",
                    use_container_width=True,
                    type="primary",
                )

    with note_col:
        st.markdown(
            f"""
            <div class="side-note">
                <img class="publish-mascot" src="{mascot_happy}" alt="开心的小鱼吉祥物"/>
                <h3><img class="publish-avatar" src="{mascot_avatar}" alt="厦了么鱼头像"/>发布小贴士</h3>
                <p>• 写清商品名称和使用情况</p>
                <p>• 价格填写马币（RM）</p>
                <p>• 约在安全、方便的校园地点交接</p>
                <hr>
                <p>当前验证邮箱：</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(mask_email(st.session_state.get("verified_email", "")))

    if submitted:
        try:
            create_item(
                name,
                category,
                price,
                seller,
                st.session_state.verified_email,
                description,
                contact,
            )
        except ValueError as exc:
            st.error(str(exc))
        except Exception:
            logger.exception("Failed to create a product from the publish page")
            st.error("商品发布失败，请稍后重试。")
        else:
            st.success("商品发布成功！可以去商品分类页面查看。")
