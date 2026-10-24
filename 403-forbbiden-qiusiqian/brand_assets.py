from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

import streamlit as st


ASSET_DIR = Path(__file__).resolve().parent / "assets"

CATEGORY_ARTWORK = {
    "教材资料": "product_books.jpg",
    "数码产品": "product_tech.jpg",
    "生活用品": "product_lifestyle.jpg",
    "运动户外": "product_sports.svg",
    "服饰箱包": "product_bag.jpg",
}
CATEGORY_ICONS = {
    "教材资料": "📚",
    "数码产品": "💻",
    "生活用品": "🏠",
    "运动户外": "⚽",
    "服饰箱包": "🎒",
}


@st.cache_data
def image_data_uri(filename: str) -> str:
    """Return a local image as a self-contained data URI for reliable Streamlit HTML rendering."""
    path = ASSET_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Required visual asset is missing: {path}")
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def add_navigation_mascot_markers() -> None:
    """Decorate page-navigation links with the mascot pointing back toward them."""
    pointer = image_data_uri("mascot_pointer.svg")
    st.markdown(
        f"""
        <style>
        .st-key-top_brand_bar {{ --nav-pointer:url("{pointer}"); }}
        [data-testid="stSidebar"] a[href]::after {{
            content:"";
            position:absolute;
            left:50%;
            bottom:0;
            width:34px;
            height:22px;
            transform:translateX(-50%);
            background:url("{pointer}") center/contain no-repeat;
            pointer-events:none;
        }}
        [data-testid="stSidebar"] a[href] {{
            position:relative;
            padding-bottom:22px !important;
            overflow:visible !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
