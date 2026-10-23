import html
import streamlit as st
from database import list_items

st.set_page_config(
    page_title="商品分类 · 厦了么鱼",
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

    .market-hero {
        padding: 34px 38px;
        border: 1px solid #dce6dc;
        border-radius: 22px;
        background:
            radial-gradient(circle at 88% 20%, #ffffffb8 0, #ffffff00 25%),
            linear-gradient(120deg, #e6eee7 0%, #f3eee2 100%);
        margin-bottom: 24px;
    }

    .market-eyebrow {
        color: #5c7966;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 2px;
    }

    .market-hero h1 {
        color: #263d32;
        font-size: 38px;
        margin: 10px 0 6px 0;
    }

    .market-hero p {
        color: #5d6f62;
        font-size: 16px;
        margin: 0;
    }

    .section-kicker {
        color: #69816f;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-bottom: 4px;
    }

    .product-card {
        min-height: 190px;
        padding: 20px;
        border: 1px solid #e3e9e1;
        border-radius: 18px;
        background: #fffefa;
        margin-bottom: 16px;
        box-shadow: 0 4px 14px #263d320c;
    }

    .product-icon {
        font-size: 28px;
        margin-bottom: 10px;
    }

    .product-name {
        color: #293d32;
        font-size: 19px;
        font-weight: 700;
        line-height: 1.4;
        margin-bottom: 8px;
        overflow-wrap: anywhere;
    }

    .product-category {
        display: inline-block;
        color: #55715f;
        background: #edf3ec;
        border-radius: 20px;
        padding: 4px 10px;
        font-size: 12px;
        margin-bottom: 12px;
    }

    .product-price {
        color: #a45f32;
        font-size: 24px;
        font-weight: 800;
        margin-bottom: 8px;
    }

    .product-meta {
        color: #69756c;
        font-size: 13px;
        margin-bottom: 8px;
    }

    .product-description {
        color: #59665d;
        font-size: 14px;
        line-height: 1.6;
        overflow-wrap: anywhere;
    }

    .empty-state {
        padding: 32px;
        border: 1px dashed #cbd8cc;
        border-radius: 18px;
        background: #fbfcf8;
        color: #58695d;
        text-align: center;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="market-hero">
        <div class="market-eyebrow">XMUM CAMPUS MARKET</div>
        <h1>发现校园好物 🐟</h1>
        <p>从教材到宿舍用品，让闲置好物遇见需要它的人。</p>
    </div>
    """,
    unsafe_allow_html=True,
)

items = list_items()

filter_col, search_col, sort_col = st.columns([1.2, 2.2, 1.2])

with filter_col:
    selected_category = st.selectbox(
        "商品分类",
        ["全部分类", "教材资料", "数码产品", "生活用品", "运动户外"],
    )

with search_col:
    search_text = st.text_input(
        "搜索商品",
        placeholder="试试搜索：高数教材、台灯、鼠标……",
    )

with sort_col:
    sort_option = st.selectbox(
        "排序方式",
        ["最新发布", "价格从低到高"],
    )

shown_items = []

for item in items:
    if selected_category != "全部分类" and item["category"] != selected_category:
        continue

    if search_text and search_text.lower() not in item["name"].lower():
        continue

    shown_items.append(item)

if sort_option == "价格从低到高":
    shown_items.sort(key=lambda item: item["price"])

st.divider()

metric_col, heading_col = st.columns([1, 4])

with metric_col:
    st.metric("在售好物", len(items))

with heading_col:
    st.markdown('<div class="section-kicker">CAMPUS FINDS</div>', unsafe_allow_html=True)
    st.subheader("校园热门推荐")
    st.caption(f"找到 {len(shown_items)} 件符合条件的商品")

if not shown_items:
    st.markdown(
        """
        <div class="empty-state">
            <div style="font-size: 34px;">🧺</div>
            <h3>暂时没有找到商品</h3>
            <p>换个分类或关键词再试试看。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    category_icons = {
        "教材资料": "📚",
        "数码产品": "💻",
        "生活用品": "🏠",
        "运动户外": "⚽",
        "服饰箱包": "🎒",
    }

    product_columns = st.columns(3)

    for index, item in enumerate(shown_items):
        name = html.escape(str(item["name"]))
        category = html.escape(str(item["category"]))
        seller = html.escape(str(item["seller"]))
        description = html.escape(str(item.get("description", "")))
        icon = category_icons.get(item["category"], "🐟")
        price = f"{float(item['price']):g}"

        with product_columns[index % 3]:
            st.markdown(
                f"""
                <div class="product-card">
                    <div class="product-icon">{icon}</div>
                    <div class="product-name">{name}</div>
                    <div class="product-category">{category}</div>
                    <div class="product-price">RM {price}</div>
                    <div class="product-meta">发布者：{seller}</div>
                    <div class="product-description">{description}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
