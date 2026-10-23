import streamlit as st

st.set_page_config(
    page_title="交易规则 · 校园小咸鱼",
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

    .rules-hero {
        padding: 34px 38px;
        border: 1px solid #dce6dc;
        border-radius: 22px;
        background: linear-gradient(120deg, #e6eee7, #f3eee2);
        margin-bottom: 24px;
    }

    .rules-hero small {
        color: #5c7966;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 2px;
    }

    .rules-hero h1 {
        color: #263d32;
        font-size: 36px;
        margin: 10px 0 6px 0;
    }

    .rules-hero p {
        color: #5d6f62;
        font-size: 16px;
        margin: 0;
    }

    .rule-card {
        padding: 22px;
        border: 1px solid #e3e9e1;
        border-radius: 18px;
        background: #fffefa;
        min-height: 150px;
    }

    .rule-card h3 {
        color: #30483a;
        margin-top: 0;
    }

    .safety-note {
        padding: 20px 24px;
        border-left: 5px solid #8a9e79;
        border-radius: 10px;
        background: #f3f6ef;
        color: #435448;
        line-height: 1.7;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="rules-hero">
        <small>SAFE & FRIENDLY CAMPUS EXCHANGE</small>
        <h1>校园交易小指南 📋</h1>
        <p>发布信息清楚一点，沟通充分一点，交易体验会更好。</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.subheader("发布商品")

rule1, rule2 = st.columns(2, gap="large")

with rule1:
    st.markdown(
        """
        <div class="rule-card">
            <h3>📝 信息真实清楚</h3>
            <p>请准确填写商品名称、分类、价格和描述，并说明明显的使用痕迹或功能问题。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with rule2:
    st.markdown(
        """
        <div class="rule-card">
            <h3>📦 商品适合转让</h3>
            <p>请勿发布违法、危险或来源不明的物品。发布前确认商品可以正常交接。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.write("")
st.subheader("沟通与交接")

rule3, rule4 = st.columns(2, gap="large")

with rule3:
    st.markdown(
        """
        <div class="rule-card">
            <h3>💬 提前确认细节</h3>
            <p>交易前与对方确认商品状态、最终价格、时间和交接地点。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with rule4:
    st.markdown(
        """
        <div class="rule-card">
            <h3>📍 选择合适地点</h3>
            <p>建议选择明亮、公开且双方都方便到达的校园地点完成交接。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.write("")
st.markdown(
    """
    <div class="safety-note">
        <b>安全提示</b><br>
        交易时请保管好个人物品和账号信息。若商品情况与描述不符，
        可以暂停交易并与对方沟通。
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()
st.caption("感谢你一起维护友善、诚信的校园交易氛围。")
