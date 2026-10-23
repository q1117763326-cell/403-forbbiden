import streamlit as st
from database import list_items

st.set_page_config(
    page_title="关于我们 · 厦了么鱼",
    page_icon="🐟",
    layout="wide",
)

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
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="about-hero">
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

items = list_items()
categories = {item["category"] for item in items}

metric_a, metric_b, metric_c = st.columns(3)
metric_a.metric("平台商品", len(items))
metric_b.metric("商品分类", len(categories))
metric_c.metric("服务对象", "校园社区")

st.divider()

st.markdown('<div class="about-kicker">OUR PURPOSE</div>', unsafe_allow_html=True)
st.header("我们想做的事")

left_col, right_col = st.columns(2, gap="large")

with left_col:
    st.markdown(
        """
        <div class="about-card">
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
        """
        <div class="about-card">
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
    with st.container(border=True):
        st.markdown("### 01 · 浏览")
        st.write("按分类或关键词查找感兴趣的商品。")

with step2:
    with st.container(border=True):
        st.markdown("### 02 · 了解")
        st.write("查看商品价格、描述和发布者信息。")

with step3:
    with st.container(border=True):
        st.markdown("### 03 · 交接")
        st.write("与发布者沟通商品情况和合适的交接安排。")

st.divider()
st.caption("厦了么鱼 · XMUM Campus Marketplace")
