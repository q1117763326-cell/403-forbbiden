from __future__ import annotations

import html
import logging

import streamlit as st

from database import is_contact_link, mark_item_sold

logger = logging.getLogger(__name__)


def render_contact_and_sale_actions(item, *, key_prefix, viewer_email):
    """Render a product's contact and the owner-only sold action."""
    contact = str(item.get("contact") or "").strip()
    if contact:
        if is_contact_link(contact):
            st.link_button("联系卖家", contact)
        else:
            st.caption(f"联系方式：{html.escape(contact)}")

    if item.get("is_mine") and viewer_email:
        if st.button("标记已售出", key=f"{key_prefix}_sold_{item['id']}"):
            try:
                sold = mark_item_sold(item["id"], viewer_email)
            except Exception:
                logger.exception("Failed to mark a product as sold")
                st.error("操作失败，请稍后重试。")
            else:
                if sold:
                    st.rerun()
                else:
                    st.warning("该商品已售出或你无权操作。")
