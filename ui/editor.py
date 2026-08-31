from __future__ import annotations

from typing import Any, Dict

import streamlit as st

import s3_storage


_OUTPUT_PRESETS = {
    "Landscape (16:9) — 1280 × 720": (1280, 720),
    "Portrait (9:16) — 720 × 1280": (720, 1280),
    "Square (1:1) — 1080 × 1080": (1080, 1080),
    "Landscape HD (16:9) — 1920 × 1080": (1920, 1080),
}
_POSITION_OPTIONS = {
    "Top": ("50%", "10%"),
    "Center": ("50%", "50%"),
    "Bottom": ("50%", "90%"),
}


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
        output_preset = st.selectbox("Output resolution and aspect ratio", list(_OUTPUT_PRESETS))
        video_fit = st.selectbox(
            "Video framing",
            ["Crop to fill frame", "Show whole video", "Stretch to fill frame"],
            help="Cropping fills the selected aspect ratio; showing the whole video may add bars.",
        )
        speed = st.select_slider("Playback speed", options=[0.5, 0.75, 1.0, 1.25, 1.5, 2.0], value=1.0)
        mute_video = st.checkbox("Mute original video audio")
        transition = st.selectbox("Video transition", ["None", "Fade"])
        transition_duration = st.number_input(
            "Transition duration (seconds)", min_value=0.1, max_value=3.0, value=0.5, step=0.1,
            disabled=transition == "None",
        )

        st.subheader("Text and Captions")
        text_overlay = st.text_input("Text overlay")
        text_position = st.selectbox("Text position", list(_POSITION_OPTIONS), index=2)
        text_duration = st.number_input(
            "Text duration (seconds)", min_value=0.1, value=5.0, step=0.1
        )
        text_size = st.number_input("Text size (pixels)", min_value=12, max_value=200, value=48, step=1)
        text_color = st.color_picker("Text color", "#FFFFFF")
        text_weight = st.selectbox("Text weight", ["Normal", "Bold"])
        caption_text = st.text_input("Caption text (optional)")
        caption_start = st.number_input("Caption start (seconds)", min_value=0.0, value=0.0, step=0.1)
        caption_duration = st.number_input(
            "Caption duration (seconds)", min_value=0.1, value=5.0, step=0.1
        )

        st.subheader("Audio and Logo")
        music_url = st.text_input("Optional music URL", placeholder="https://...")
        music_volume = st.slider("Music volume (%)", min_value=0, max_value=100, value=40)
        music_fade_in = st.number_input("Music fade in (seconds)", min_value=0.0, value=1.0, step=0.1)
        music_fade_out = st.number_input("Music fade out (seconds)", min_value=0.0, value=1.0, step=0.1)
        logo_url = st.text_input("Optional logo/image URL", placeholder="https://...")
        logo_position = st.selectbox("Logo position", list(_POSITION_OPTIONS), index=0)
        logo_size = st.slider("Logo width (% of frame)", min_value=5, max_value=50, value=15)
        logo_opacity = st.slider("Logo opacity (%)", min_value=0, max_value=100, value=100)

        submitted = st.form_submit_button("Render Video", use_container_width=True)

    width, height = _OUTPUT_PRESETS[output_preset]
    return {
        "submitted": submitted,
        "api_key": api_key,
        "video_url": video_url,
        "trim_start": float(trim_start),
        "trim_end": float(trim_end),
        "text_overlay": text_overlay.strip(),
        "music_url": music_url.strip() or None,
        "width": width,
        "height": height,
        "video_fit": {
            "Crop to fill frame": "cover",
            "Show whole video": "contain",
            "Stretch to fill frame": "fill",
        }[video_fit],
        "speed": float(speed),
        "mute_video": mute_video,
        "transition": transition.lower() if transition != "None" else None,
        "transition_duration": float(transition_duration),
        "text_position": _POSITION_OPTIONS[text_position],
        "text_duration": float(text_duration),
        "text_size": int(text_size),
        "text_color": text_color,
        "text_weight": text_weight.lower(),
        "caption_text": caption_text.strip(),
        "caption_start": float(caption_start),
        "caption_duration": float(caption_duration),
        "music_volume": int(music_volume),
        "music_fade_in": float(music_fade_in),
        "music_fade_out": float(music_fade_out),
        "logo_url": logo_url.strip() or None,
        "logo_position": _POSITION_OPTIONS[logo_position],
        "logo_size": int(logo_size),
        "logo_opacity": int(logo_opacity),
    }


def render_result(result: Dict[str, Any]) -> None:
    if result.get("status") != "done":
        st.error(result.get("error", "Render failed"))
        return

    url = result.get("url")
    st.success("Render complete")
    st.video(url)
    st.markdown(f"[Download rendered video]({url})")
