from __future__ import annotations

from pathlib import Path

import streamlit as st

import api_client
from ui import render_editor_form, render_result

st.set_page_config(page_title="Creatomate Video Editor", page_icon="🎬", layout="centered")

css_path = Path(__file__).parent / "static" / "styles.css"
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

state = render_editor_form()

if state["submitted"]:
    if not state["api_key"]:
        st.error("Please enter your Creatomate API key.")
    elif not state["video_url"]:
        st.error("Please provide a video source URL.")
    elif state["trim_end"] <= state["trim_start"]:
        st.error("Trim end must be greater than trim start.")
    else:
        with st.spinner("Rendering video..."):
            try:
                result = api_client.fetch_data(
                    api_key=state["api_key"],
                    video_url=state["video_url"],
                    trim_start=state["trim_start"],
                    trim_end=state["trim_end"],
                    text_overlay=state["text_overlay"],
                    music_url=state["music_url"],
                )
            except Exception as exc:
                st.error(f"Render request failed: {exc}")
            else:
                render_result(result)
else:
    st.info("Enter your API key, provide a video source URL, configure edits, then click Render Video.")
