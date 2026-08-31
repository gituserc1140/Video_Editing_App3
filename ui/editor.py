from __future__ import annotations

from typing import Any, Dict

import streamlit as st

import s3_storage


def _render_video_source_tabs() -> str:
    """Render the "paste URL" / "upload to private S3" tabs and return the resolved video URL."""
    url_tab, upload_tab = st.tabs(["Paste video URL", "Upload video (private S3)"])

    with url_tab:
        pasted_url = st.text_input(
            "Video source URL",
            placeholder="https://...",
            help="Must be a publicly accessible URL to a video file that Creatomate can fetch.",
            key="pasted_video_url",
        )

    with upload_tab:
        st.caption(
            "Uploads your video to a private S3 bucket and generates a temporary, "
            "signed link that only Creatomate can use to fetch it. The link stops "
            "working automatically once it expires, so the video is never left "
            "publicly accessible."
        )
        uploaded_file = st.file_uploader(
            "Upload video", type=["mp4", "mov", "webm", "m4v"], key="s3_video_upload"
        )
        if st.button("Upload to S3", disabled=uploaded_file is None):
            with st.spinner("Uploading to S3..."):
                try:
                    presigned_url = s3_storage.upload_video(
                        uploaded_file.getvalue(),
                        uploaded_file.name,
                        content_type=uploaded_file.type,
                    )
                except Exception as exc:
                    st.error(f"Upload failed: {exc}")
                else:
                    st.session_state["uploaded_video_url"] = presigned_url
                    st.success("Upload complete. The temporary source URL is ready below.")

        if st.session_state.get("uploaded_video_url"):
            st.text_input(
                "Temporary video source URL",
                value=st.session_state["uploaded_video_url"],
                disabled=True,
            )

    return pasted_url.strip() or st.session_state.get("uploaded_video_url", "")


def render_editor_form() -> Dict[str, Any]:
    st.title("Creatomate Video Editor")
    st.caption("Provide a video source URL, set simple edits, and render using your Creatomate API key.")

    video_url = _render_video_source_tabs()

    with st.form("video-editor-form"):
        api_key = st.text_input("Creatomate API key", type="password")

        st.subheader("Editing Controls")
        trim_start = st.number_input("Trim start (seconds)", min_value=0.0, value=0.0, step=0.1)
        trim_end = st.number_input("Trim end (seconds)", min_value=0.1, value=5.0, step=0.1)
        text_overlay = st.text_input("Text overlay")
        music_url = st.text_input("Optional music URL", placeholder="https://...")

        submitted = st.form_submit_button("Render Video", use_container_width=True)

    return {
        "submitted": submitted,
        "api_key": api_key,
        "video_url": video_url,
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
