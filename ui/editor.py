from __future__ import annotations

from typing import Any, Dict

import streamlit as st


def render_editor_form() -> Dict[str, Any]:
    st.title("Creatomate Video Editor")
    st.caption("Provide a video source URL, set simple edits, and render using your Creatomate API key.")

    with st.form("video-editor-form"):
        api_key = st.text_input("Creatomate API key", type="password")
        video_url = st.text_input(
            "Video source URL",
            placeholder="https://...",
            help="Must be a publicly accessible URL to a video file that Creatomate can fetch.",
        )

        st.subheader("Editing Controls")
        trim_start = st.number_input("Trim start (seconds)", min_value=0.0, value=0.0, step=0.1)
        trim_end = st.number_input("Trim end (seconds)", min_value=0.1, value=5.0, step=0.1)
        text_overlay = st.text_input("Text overlay")
        music_url = st.text_input("Optional music URL", placeholder="https://...")

        submitted = st.form_submit_button("Render Video", use_container_width=True)

    return {
        "submitted": submitted,
        "api_key": api_key,
        "video_url": video_url.strip(),
        "trim_start": float(trim_start),
        "trim_end": float(trim_end),
        "text_overlay": text_overlay.strip(),
        "music_url": music_url.strip() or None,
    }


def render_result(result: Dict[str, Any]) -> None:
    if result.get("status") != "done":
        st.error(result.get("error", "Render failed"))
        return

    url = result.get("url")
    st.success("Render complete")
    st.video(url)
    st.markdown(f"[Download rendered video]({url})")
