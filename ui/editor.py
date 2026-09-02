from __future__ import annotations

import json
import re
from typing import Any, Dict, List

import streamlit as st

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
_FONT_FAMILIES = ["Open Sans", "Roboto", "Montserrat", "Playfair Display", "Oswald", "Lato"]
_TRANSITION_OPTIONS = {
    "None": None,
    "Fade": "fade",
    "Slide": "slide",
    "Wipe": "wipe",
    "Reveal": "reveal",
}
_TRANSITION_DIRECTIONS = ["left", "right", "up", "down"]
_SHAPE_KINDS = ["rectangle", "ellipse"]

_SRT_TIME_RE = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})[.,](\d{1,3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[.,](\d{1,3})"
)


def _timestamp_to_seconds(hours: str, minutes: str, seconds: str, millis: str) -> float:
    return (
        int(hours) * 3600
        + int(minutes) * 60
        + int(seconds)
        + int(millis.ljust(3, "0")) / 1000
    )


def _parse_subtitle_file(content: str) -> List[Dict[str, Any]]:
    """Parse a .srt or .vtt subtitle file into caption rows (start/duration/text)."""
    rows: List[Dict[str, Any]] = []
    blocks = re.split(r"\r?\n\r?\n+", content.strip())
    for block in blocks:
        lines = [line for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        match = None
        text_lines_start = 0
        for i, line in enumerate(lines):
            match = _SRT_TIME_RE.search(line)
            if match:
                text_lines_start = i + 1
                break
        if not match:
            continue
        start = _timestamp_to_seconds(*match.groups()[0:4])
        end = _timestamp_to_seconds(*match.groups()[4:8])
        text = " ".join(lines[text_lines_start:]).strip()
        if text and end > start:
            rows.append({"start": round(start, 3), "duration": round(end - start, 3), "text": text})
    return rows


def _render_video_source_tabs() -> str:
    """Render the video source tabs and return the resolved video URL."""
    url_tab, upload_tab = st.tabs(["Paste video URL", "S3 upload help"])

    with url_tab:
        pasted_url = st.text_input(
            "Video source URL",
            placeholder="https://...",
            help="Must be a publicly accessible URL to a video file that Creatomate can fetch.",
            key="pasted_video_url",
        )

    with upload_tab:
        st.caption(
            "If S3 upload is not currently working in your environment, sign in to AWS "
            "to manage your bucket and credentials."
        )
        st.link_button(
            "Sign in to AWS",
            "https://signin.aws.amazon.com/signin",
            use_container_width=True,
        )
        st.info("After signing in, create or fetch a video URL and paste it in the first tab.")

    return pasted_url.strip()


def render_editor_form() -> Dict[str, Any]:
    st.title("Creatomate Video Editor")
    st.caption("Provide a video source URL, set simple edits, and render using your Creatomate API key.")

    video_url = _render_video_source_tabs()

    preset_data: Dict[str, Any] = {}
    with st.expander("Load preset and import subtitles"):
        st.caption("Load a previously saved preset, or import an SRT/VTT file to auto-fill captions.")
        preset_file = st.file_uploader("Load preset (.json)", type=["json"], key="preset_upload")
        if preset_file is not None:
            try:
                preset_data = json.loads(preset_file.getvalue().decode("utf-8"))
            except Exception as exc:
                st.error(f"Could not read preset file: {exc}")

        subtitle_file = st.file_uploader(
            "Import captions from .srt or .vtt", type=["srt", "vtt"], key="subtitle_upload"
        )
        if subtitle_file is not None:
            try:
                parsed_rows = _parse_subtitle_file(subtitle_file.getvalue().decode("utf-8"))
            except Exception as exc:
                st.error(f"Could not parse subtitle file: {exc}")
                parsed_rows = []
            if parsed_rows:
                st.session_state["extra_captions_editor"] = parsed_rows
                st.success(f"Imported {len(parsed_rows)} caption(s) from {subtitle_file.name}.")

    def _pref(name: str, default: Any) -> Any:
        return preset_data.get(name, default)

    with st.form("video-editor-form"):
        api_key = st.text_input("Creatomate API key", type="password")

        st.subheader("Editing Controls")
        trim_start = st.number_input(
            "Trim start (seconds)", min_value=0.0, value=float(_pref("trim_start", 0.0)), step=0.1
        )
        trim_end = st.number_input(
            "Trim end (seconds)", min_value=0.1, value=float(_pref("trim_end", 5.0)), step=0.1
        )
        preset_names = list(_OUTPUT_PRESETS)
        output_preset = st.selectbox(
            "Output resolution and aspect ratio",
            preset_names,
            index=preset_names.index(_pref("output_preset", preset_names[0]))
            if _pref("output_preset", preset_names[0]) in preset_names
            else 0,
        )
        fit_options = ["Crop to fill frame", "Show whole video", "Stretch to fill frame"]
        video_fit = st.selectbox(
            "Video framing",
            fit_options,
            index=fit_options.index(_pref("video_fit_label", fit_options[0]))
            if _pref("video_fit_label", fit_options[0]) in fit_options
            else 0,
            help="Cropping fills the selected aspect ratio; showing the whole video may add bars.",
        )
        speed = st.select_slider(
            "Playback speed", options=[0.5, 0.75, 1.0, 1.25, 1.5, 2.0], value=float(_pref("speed", 1.0))
        )
        mute_video = st.checkbox("Mute original video audio", value=bool(_pref("mute_video", False)))
        transition_names = list(_TRANSITION_OPTIONS)
        transition = st.selectbox(
            "Video transition",
            transition_names,
            index=transition_names.index(_pref("transition_label", "None"))
            if _pref("transition_label", "None") in transition_names
            else 0,
        )
        transition_duration = st.number_input(
            "Transition duration (seconds)", min_value=0.1, max_value=3.0,
            value=float(_pref("transition_duration", 0.5)), step=0.1,
            disabled=transition == "None",
        )
        transition_direction = st.selectbox(
            "Transition direction",
            _TRANSITION_DIRECTIONS,
            disabled=transition in ("None", "Fade"),
        )

        st.subheader("Multiple Clips")
        st.caption(
            "Add more clips to play back-to-back after the main clip above (each row needs a "
            "public video URL and trim range)."
        )
        extra_clip_rows = st.data_editor(
            [],
            num_rows="dynamic",
            key="extra_clips_editor",
            column_config={
                "url": st.column_config.TextColumn("Video URL"),
                "trim_start": st.column_config.NumberColumn("Trim start (s)", min_value=0.0, step=0.1),
                "trim_end": st.column_config.NumberColumn("Trim end (s)", min_value=0.1, step=0.1),
            },
        )

        st.subheader("Color and Crop")
        brightness = st.slider("Brightness (%)", min_value=50, max_value=150, value=int(_pref("brightness", 100)))
        contrast = st.slider("Contrast (%)", min_value=50, max_value=150, value=int(_pref("contrast", 100)))
        saturation = st.slider("Saturation (%)", min_value=0, max_value=200, value=int(_pref("saturation", 100)))
        col_gray, col_sepia = st.columns(2)
        with col_gray:
            grayscale = st.checkbox("Grayscale", value=bool(_pref("grayscale", False)))
        with col_sepia:
            sepia = st.checkbox("Sepia", value=bool(_pref("sepia", False)))
        video_x = st.slider("Horizontal position (%)", min_value=0, max_value=100, value=int(_pref("video_x", 50)))
        video_y = st.slider("Vertical position (%)", min_value=0, max_value=100, value=int(_pref("video_y", 50)))
        video_zoom = st.slider("Zoom (%)", min_value=50, max_value=200, value=int(_pref("video_zoom", 100)))
        video_border_radius = st.slider("Corner rounding (px)", min_value=0, max_value=100, value=0)
        video_border_width = st.slider("Border width (px)", min_value=0, max_value=20, value=0)
        video_border_color = st.color_picker(
            "Border color", "#FFFFFF", disabled=video_border_width == 0
        )
        video_shadow = st.checkbox("Add drop shadow to video")
        letterbox_blur = st.checkbox(
            "Fill letterbox bars with a blurred copy of the video",
            help="Only applies when video framing is set to 'Show whole video'.",
        )

        st.subheader("Overlays")
        pip_url = st.text_input("Picture-in-picture video URL (optional)", placeholder="https://...")
        pip_position = st.selectbox("Picture-in-picture position", list(_POSITION_OPTIONS), index=2, key="pip_position_select")
        pip_size = st.slider("Picture-in-picture size (% of frame)", min_value=10, max_value=60, value=25)
        pip_opacity = st.slider("Picture-in-picture opacity (%)", min_value=0, max_value=100, value=100)
        pip_mute = st.checkbox("Mute picture-in-picture audio", value=True)

        shape_enabled = st.checkbox("Add a shape/banner overlay")
        shape_kind = st.selectbox("Shape type", _SHAPE_KINDS, disabled=not shape_enabled)
        shape_color = st.color_picker("Shape fill color", "#000000", disabled=not shape_enabled)
        shape_opacity = st.slider("Shape opacity (%)", min_value=0, max_value=100, value=50, disabled=not shape_enabled)
        shape_x = st.slider("Shape horizontal position (%)", min_value=0, max_value=100, value=50, disabled=not shape_enabled)
        shape_y = st.slider("Shape vertical position (%)", min_value=0, max_value=100, value=90, disabled=not shape_enabled)
        shape_width = st.slider("Shape width (% of frame)", min_value=5, max_value=100, value=60, disabled=not shape_enabled)
        shape_height = st.slider("Shape height (% of frame)", min_value=5, max_value=100, value=15, disabled=not shape_enabled)
        shape_border_radius = st.slider(
            "Shape corner rounding (px)", min_value=0, max_value=100, value=0,
            disabled=not shape_enabled or shape_kind != "rectangle",
        )

        st.subheader("Text and Captions")
        text_overlay = st.text_input("Text overlay", value=str(_pref("text_overlay", "")))
        text_position = st.selectbox("Text position", list(_POSITION_OPTIONS), index=2)
        text_duration = st.number_input(
            "Text duration (seconds)", min_value=0.1, value=float(_pref("text_duration", 5.0)), step=0.1
        )
        text_size = st.number_input(
            "Text size (pixels)", min_value=12, max_value=200, value=int(_pref("text_size", 48)), step=1
        )
        text_color = st.color_picker("Text color", str(_pref("text_color", "#FFFFFF")))
        text_weight = st.selectbox("Text weight", ["Normal", "Bold"])
        text_font_family = st.selectbox(
            "Text font family",
            _FONT_FAMILIES,
            index=_FONT_FAMILIES.index(_pref("text_font_family", _FONT_FAMILIES[0]))
            if _pref("text_font_family", _FONT_FAMILIES[0]) in _FONT_FAMILIES
            else 0,
        )
        text_fade_in = st.checkbox("Fade text overlay in")
        text_background_enabled = st.checkbox("Add text background box")
        text_background_color = st.color_picker(
            "Text background color", "#000000", disabled=not text_background_enabled
        )
        text_outline_enabled = st.checkbox("Add text outline")
        text_stroke_color = st.color_picker(
            "Text outline color", "#000000", disabled=not text_outline_enabled
        )
        text_stroke_width = st.number_input(
            "Text outline width (pixels)", min_value=0.0, max_value=20.0, value=2.0, step=0.5,
            disabled=not text_outline_enabled,
        )
        caption_text = st.text_input("Caption text (optional)")
        caption_start = st.number_input("Caption start (seconds)", min_value=0.0, value=0.0, step=0.1)
        caption_duration = st.number_input(
            "Caption duration (seconds)", min_value=0.1, value=5.0, step=0.1
        )
        st.caption("Add extra timed captions below (each row is a subtitle-style entry).")
        extra_captions = st.data_editor(
            [{"start": 0.0, "duration": 5.0, "text": ""}],
            num_rows="dynamic",
            key="extra_captions_editor",
            column_config={
                "start": st.column_config.NumberColumn("Start (s)", min_value=0.0, step=0.1),
                "duration": st.column_config.NumberColumn("Duration (s)", min_value=0.1, step=0.1),
                "text": st.column_config.TextColumn("Text"),
            },
        )

        st.subheader("Audio and Logo")
        music_url = st.text_input("Optional music URL", value=str(_pref("music_url", "") or ""), placeholder="https://...")
        music_volume = st.slider("Music volume (%)", min_value=0, max_value=100, value=int(_pref("music_volume", 40)))
        music_fade_in = st.number_input("Music fade in (seconds)", min_value=0.0, value=1.0, step=0.1)
        music_fade_out = st.number_input("Music fade out (seconds)", min_value=0.0, value=1.0, step=0.1)
        voiceover_url = st.text_input("Optional voiceover URL", placeholder="https://...")
        voiceover_volume = st.slider("Voiceover volume (%)", min_value=0, max_value=100, value=100)
        logo_url = st.text_input("Optional logo/image URL", value=str(_pref("logo_url", "") or ""), placeholder="https://...")
        logo_position = st.selectbox("Logo position", list(_POSITION_OPTIONS), index=0)
        logo_size = st.slider("Logo width (% of frame)", min_value=5, max_value=50, value=int(_pref("logo_size", 15)))
        logo_opacity = st.slider("Logo opacity (%)", min_value=0, max_value=100, value=int(_pref("logo_opacity", 100)))
        logo_fade_in = st.checkbox("Fade logo in")

        st.subheader("Intro and Outro")
        intro_image_url = st.text_input("Intro freeze-frame image URL (optional)", placeholder="https://...")
        intro_duration = st.number_input(
            "Intro duration (seconds)", min_value=0.1, max_value=10.0, value=1.5, step=0.1,
        )
        outro_image_url = st.text_input("Outro freeze-frame image URL (optional)", placeholder="https://...")
        outro_duration = st.number_input(
            "Outro duration (seconds)", min_value=0.1, max_value=10.0, value=1.5, step=0.1,
        )

        submitted = st.form_submit_button("Render Video", use_container_width=True)

    width, height = _OUTPUT_PRESETS[output_preset]
    captions = [
        {
            "start": float(row.get("start", 0) or 0),
            "duration": float(row.get("duration", 5) or 5),
            "text": str(row.get("text", "") or "").strip(),
        }
        for row in (extra_captions or [])
        if str(row.get("text", "") or "").strip()
    ]
    extra_clips = [
        {
            "url": str(row.get("url", "") or "").strip(),
            "trim_start": float(row.get("trim_start", 0) or 0),
            "trim_end": float(row.get("trim_end", 0) or 0),
        }
        for row in (extra_clip_rows or [])
        if str(row.get("url", "") or "").strip()
    ]
    video_fit_value = {
        "Crop to fill frame": "cover",
        "Show whole video": "contain",
        "Stretch to fill frame": "fill",
    }[video_fit]

    state = {
        "submitted": submitted,
        "api_key": api_key,
        "video_url": video_url,
        "trim_start": float(trim_start),
        "trim_end": float(trim_end),
        "text_overlay": text_overlay.strip(),
        "music_url": music_url.strip() or None,
        "width": width,
        "height": height,
        "output_preset": output_preset,
        "video_fit": video_fit_value,
        "video_fit_label": video_fit,
        "speed": float(speed),
        "mute_video": mute_video,
        "transition": _TRANSITION_OPTIONS[transition],
        "transition_label": transition,
        "transition_duration": float(transition_duration),
        "transition_direction": transition_direction,
        "extra_clips": extra_clips,
        "text_position": _POSITION_OPTIONS[text_position],
        "text_duration": float(text_duration),
        "text_size": int(text_size),
        "text_color": text_color,
        "text_weight": text_weight.lower(),
        "text_font_family": text_font_family,
        "text_fade_in": text_fade_in,
        "text_background_color": text_background_color if text_background_enabled else None,
        "text_stroke_color": text_stroke_color if text_outline_enabled else None,
        "text_stroke_width": float(text_stroke_width) if text_outline_enabled else 0.0,
        "caption_text": caption_text.strip(),
        "caption_start": float(caption_start),
        "caption_duration": float(caption_duration),
        "captions": captions,
        "music_volume": int(music_volume),
        "music_fade_in": float(music_fade_in),
        "music_fade_out": float(music_fade_out),
        "voiceover_url": voiceover_url.strip() or None,
        "voiceover_volume": int(voiceover_volume),
        "logo_url": logo_url.strip() or None,
        "logo_position": _POSITION_OPTIONS[logo_position],
        "logo_size": int(logo_size),
        "logo_opacity": int(logo_opacity),
        "logo_fade_in": logo_fade_in,
        "brightness": int(brightness),
        "contrast": int(contrast),
        "saturation": int(saturation),
        "grayscale": grayscale,
        "sepia": sepia,
        "video_x": int(video_x),
        "video_y": int(video_y),
        "video_zoom": int(video_zoom),
        "video_border_radius": int(video_border_radius),
        "video_border_width": int(video_border_width),
        "video_border_color": video_border_color,
        "video_shadow": video_shadow,
        "letterbox_blur": letterbox_blur,
        "pip_url": pip_url.strip() or None,
        "pip_position": _POSITION_OPTIONS[pip_position],
        "pip_size": int(pip_size),
        "pip_opacity": int(pip_opacity),
        "pip_mute": pip_mute,
        "shape_enabled": shape_enabled,
        "shape_kind": shape_kind,
        "shape_color": shape_color,
        "shape_opacity": int(shape_opacity),
        "shape_x": int(shape_x),
        "shape_y": int(shape_y),
        "shape_width": int(shape_width),
        "shape_height": int(shape_height),
        "shape_border_radius": int(shape_border_radius),
        "intro_image_url": intro_image_url.strip() or None,
        "intro_duration": float(intro_duration),
        "outro_image_url": outro_image_url.strip() or None,
        "outro_duration": float(outro_duration),
    }

    with st.expander("Save preset"):
        preset_json = json.dumps({k: v for k, v in state.items() if k not in {"submitted", "api_key"}}, indent=2)
        st.download_button(
            "Download current settings as preset (.json)",
            data=preset_json,
            file_name="video_editor_preset.json",
            mime="application/json",
        )

    return state


def render_result(result: Dict[str, Any]) -> None:
    if result.get("status") != "done":
        st.error(result.get("error", "Render failed"))
        return

    url = result.get("url")
    st.success("Render complete")
    st.video(url)
    st.markdown(f"[Download rendered video]({url})")
