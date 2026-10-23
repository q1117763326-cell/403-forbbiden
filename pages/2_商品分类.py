import streamlit as st
from database import list_items

st.set_page_config(page_title="商品分类 · 校园小咸鱼", page_icon="🐟", layout="wide")

st.title("🔎 商品分类")
st.caption("按分类浏览校园里的闲置好物")

categories = ["全部", "教材资料", "数码产品", "生活用品", "运动户外"]
selected_category = st.selectbox("选择分类", categories)
search_text = st.text_input("搜索商品名称")

items = list_items()
shown_items = []

for item in items:
    if selected_category != "全部" and item["category"] != selected_category:
        continue

    if search_text and search_text.lower() not in item["name"].lower():
        continue

    shown_items.append(item)

if not shown_items:
    st.info("没有找到商品，换个分类或关键词试试。")
else:
    for item in shown_items:
        with st.container(border=True):
            st.subheader(item["name"])
            st.write(f"分类：{item['category']}")
            st.write(f"价格：RM {item['price']:g}")
            st.write(f"发布者：{item['seller']}")
            if item["description"]:
                st.write(item["description"])
