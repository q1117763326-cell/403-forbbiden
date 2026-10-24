import logging

import streamlit as st
from database import get_item_stats
from brand_assets import add_navigation_mascot_markers, image_data_uri

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="关于我们 · 厦了么鱼",
    page_icon="🐟",
    layout="wide",
)
add_navigation_mascot_markers()

st.markdown(
    """
    <style>
    .block-container {
        max-width: 1180px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    .about-hero {
        padding: 38px;
        border: 1px solid #dce6dc;
        border-radius: 22px;
        background:
            radial-gradient(circle at 90% 18%, #ffffffb8 0, #ffffff00 25%),
            linear-gradient(120deg, #e6eee7, #f3eee2);
        margin-bottom: 24px;
    }

    .about-hero small {
        color: #5c7966;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 2px;
    }

    .about-hero h1 {
        color: #263d32;
        font-size: 38px;
        margin: 10px 0;
    }

    .about-hero p {
        color: #5d6f62;
        font-size: 17px;
        line-height: 1.7;
        max-width: 720px;
        margin: 0;
    }

    .about-card {
        height: 100%;
        padding: 24px;
        border: 1px solid #e3e9e1;
        border-radius: 18px;
        background: #fffefa;
        line-height: 1.7;
    }

    .about-card h3 {
        color: #30483a;
        margin-top: 0;
    }

    .about-kicker {
        color: #69816f;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 1.5px;
        margin-bottom: 4px;
    }

    .about-mood { width:60px; height:54px; object-fit:contain; float:right; margin:-4px 0 4px 10px; border-radius:15px; mix-blend-mode:multiply; }
    .about-hero-mood { width:72px; height:68px; object-fit:contain; float:right; margin:0 8px 0 16px; border-radius:16px; mix-blend-mode:multiply; }
    .step-card { min-height:145px; padding:18px; border:1px solid #d9e6f1; border-radius:18px; background:linear-gradient(145deg,#fff,#f1f8ff); }
    .step-card img { width:58px; height:54px; object-fit:contain; float:right; margin-left:8px; border-radius:15px; mix-blend-mode:multiply; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="about-hero">
        <img class="about-hero-mood" src="{image_data_uri('mascot_confused.png')}" alt="疑惑的小鱼"/>
        <small>BETTER CAMPUS · BETTER LIFE</small>
        <h1>让闲置流转，让校园更有温度 🐟</h1>
        <p>
            厦了么鱼是为校园社区打造的闲置物品交流平台。
            我们希望让好物找到新主人，也让同学们更方便地发现需要的东西。
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    stats = get_item_stats()
except Exception:
    logger.exception("Failed to load product statistics for the about page")
    st.error("商品数据加载失败，请稍后重试。")
    stats = {"total": 0, "available": 0, "sold": 0, "categories": 0}

mascot_happy = image_data_uri("mascot_happy.png")
mascot_wink = image_data_uri("mascot_wink.png")
mascot_cheer = image_data_uri("mascot_cheer.png")
mascot_serious = image_data_uri("mascot_serious.png")
mascot_sleep = image_data_uri("mascot_sleep.png")

metric_a, metric_b, metric_c = st.columns(3)
metric_a.metric("已让闲置继续使用", stats["sold"])
metric_b.metric("在售好物", stats["available"])
metric_c.metric("平台商品", stats["total"])
st.caption(
    f"已让 {stats['sold']} 件闲置继续使用 / 在售 {stats['available']} 件 / 共 {stats['total']} 件"
)

st.divider()

st.markdown('<div class="about-kicker">OUR PURPOSE</div>', unsafe_allow_html=True)
st.header("我们想做的事")

left_col, right_col = st.columns(2, gap="large")

with left_col:
    st.markdown(
        f"""
        <div class="about-card">
            <img class="about-mood" src="{mascot_happy}" alt="开心的小鱼"/>
            <h3>♻️ 让好物继续使用</h3>
            <p>
                教材、数码产品和生活用品可能只是暂时闲置。
                通过校园内的信息交流，让它们有机会继续发挥价值。
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with right_col:
    st.markdown(
        f"""
        <div class="about-card">
            <img class="about-mood" src="{mascot_wink}" alt="比心的小鱼"/>
            <h3>🤝 让交易更方便</h3>
            <p>
                集中展示校园里的闲置商品，方便同学浏览、搜索和了解商品信息，
                减少寻找和沟通的时间。
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.write("")

st.markdown('<div class="about-kicker">HOW IT WORKS</div>', unsafe_allow_html=True)
st.header("简单三步，发现校园好物")

step1, step2, step3 = st.columns(3)

with step1:
    st.markdown(f'<div class="step-card"><img src="{mascot_cheer}" alt="加油的小鱼"/><h3>01 · 浏览</h3><p>按分类或关键词查找感兴趣的商品。</p></div>', unsafe_allow_html=True)

with step2:
    st.markdown(f'<div class="step-card"><img src="{mascot_serious}" alt="认真的小鱼"/><h3>02 · 了解</h3><p>查看商品价格、描述和发布者信息。</p></div>', unsafe_allow_html=True)

with step3:
    st.markdown(f'<div class="step-card"><img src="{mascot_sleep}" alt="睡觉的小鱼"/><h3>03 · 交接</h3><p>与发布者沟通商品情况和合适的交接安排。</p></div>', unsafe_allow_html=True)

st.divider()
st.caption("厦了么鱼 · XMUM Campus Marketplace")
