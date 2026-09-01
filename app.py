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
                    width=state["width"],
                    height=state["height"],
                    video_fit=state["video_fit"],
                    speed=state["speed"],
                    mute_video=state["mute_video"],
                    transition=state["transition"],
                    transition_duration=state["transition_duration"],
                    transition_direction=state["transition_direction"],
                    text_position=state["text_position"],
                    text_duration=state["text_duration"],
                    text_size=state["text_size"],
                    text_color=state["text_color"],
                    text_weight=state["text_weight"],
                    text_font_family=state["text_font_family"],
                    text_background_color=state["text_background_color"],
                    text_stroke_color=state["text_stroke_color"],
                    text_stroke_width=state["text_stroke_width"],
                    caption_text=state["caption_text"],
                    caption_start=state["caption_start"],
                    caption_duration=state["caption_duration"],
                    captions=state["captions"],
                    music_volume=state["music_volume"],
                    music_fade_in=state["music_fade_in"],
                    music_fade_out=state["music_fade_out"],
                    voiceover_url=state["voiceover_url"],
                    voiceover_volume=state["voiceover_volume"],
                    logo_url=state["logo_url"],
                    logo_position=state["logo_position"],
                    logo_size=state["logo_size"],
                    logo_opacity=state["logo_opacity"],
                    brightness=state["brightness"],
                    contrast=state["contrast"],
                    saturation=state["saturation"],
                    grayscale=state["grayscale"],
                    sepia=state["sepia"],
                    video_x=state["video_x"],
                    video_y=state["video_y"],
                    video_zoom=state["video_zoom"],
                )
            except Exception as exc:
                st.error(f"Render request failed: {exc}")
            else:
                render_result(result)
else:
    st.info("Enter your API key, provide a video source URL, configure edits, then click Render Video.")
