import streamlit as st
from database import create_item

st.set_page_config(page_title="发布商品 · 校园小咸鱼", page_icon="🐟", layout="wide")

st.title("➕ 发布闲置好物")

if not st.session_state.get("email_verified"):
    st.info("请先回到首页，在侧边栏完成学生邮箱验证。")
else:
    with st.form("publish_item_form"):
        name = st.text_input("商品名称", max_chars=50)
        category = st.selectbox(
            "分类",
            ["教材资料", "数码产品", "生活用品", "运动户外"],
        )
        price = st.number_input(
            "价格（RM）",
            min_value=0.0,
            max_value=99999.0,
            value=10.0,
            step=1.0,
        )
        seller = st.text_input("你的昵称", max_chars=20)
        description = st.text_area("商品描述", max_chars=300)
        submitted = st.form_submit_button("发布商品")

    if submitted:
        if not name.strip() or not seller.strip():
            st.error("请填写商品名称和昵称。")
        else:
            create_item(
                name.strip(),
                category,
                price,
                seller.strip(),
                st.session_state.verified_email,
                description.strip(),
            )
            st.success("商品已发布！")
