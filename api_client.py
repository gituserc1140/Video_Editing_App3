from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests

from config import settings


RENDER_ENDPOINT = "/renders"

TERMINAL_SUCCESS_STATUS = "succeeded"
TERMINAL_FAILURE_STATUSES = {"failed"}


def _extract(data: Any, *paths: str) -> Optional[Any]:
    for path in paths:
        current = data
        ok = True
        for key in path.split("."):
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                ok = False
                break
        if ok and current is not None:
            return current
    return None


def _error_detail(body: Dict[str, Any]) -> Optional[str]:
    hint = body.get("hint")
    message = body.get("message")
    if hint and message and hint != message:
        return f"{message}: {hint}"
    return hint or message


def _is_valid_url(url: Any) -> bool:
    if not isinstance(url, str) or not url:
        return False
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _request(
    method: str,
    path: str,
    api_key: str,
    *,
    json_payload: Optional[Dict[str, Any]] = None,
    timeout: Optional[int] = None,
) -> Any:
    base_url = settings.CREATOMATE_BASE_URL
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    headers = {
        "Authorization": "Bearer " + api_key.strip(),
        "Accept": "application/json",
    }
    if json_payload is not None:
        headers["Content-Type"] = "application/json"

    try:
        response = requests.request(
            method=method.upper(),
            url=url,
            headers=headers,
            json=json_payload,
            timeout=timeout or settings.DEFAULT_TIMEOUT,
            allow_redirects=False,
        )
    except requests.exceptions.ConnectionError as exc:
        raise requests.exceptions.ConnectionError(
            f"Could not reach {base_url} ({method.upper()} {path}); check your network connection "
            "and that this environment allows outbound requests to the Creatomate API host",
            response=getattr(exc, "response", None),
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise requests.exceptions.Timeout(
            f"Timed out connecting to {base_url} ({method.upper()} {path}); the Creatomate API host "
            "may be unreachable from this environment",
            response=getattr(exc, "response", None),
        ) from exc
    if response.status_code in {301, 302, 303, 307, 308}:
        location = response.headers.get("Location", "an unknown location")
        raise requests.HTTPError(
            f"Creatomate redirected {method.upper()} {path} to {location}; "
            "check that the configured API base URL is correct",
            response=response,
        )
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        detail = None
        try:
            body = response.json()
        except ValueError:
            body = None
        if isinstance(body, dict):
            detail = _error_detail(body)
        if response.status_code == 401:
            mismatch_hint = "Check that your Creatomate API key is valid and correctly configured"
            detail = f"{detail}; {mismatch_hint}" if detail else mismatch_hint
        if detail:
            raise requests.HTTPError(f"{exc} - {detail}", response=response) from exc
        raise
    if not response.text:
        return {}

    try:
        return response.json()
    except ValueError:
        return response.text


_TRANSITION_TYPES = {"fade", "slide", "wipe", "reveal"}
_SHAPE_KINDS = {"rectangle", "ellipse"}


def _build_video_filter(
    brightness: int,
    contrast: int,
    saturation: int,
    grayscale: bool,
    sepia: bool,
    blur: int = 0,
) -> Optional[str]:
    parts = []
    if brightness != 100:
        parts.append(f"brightness({brightness}%)")
    if contrast != 100:
        parts.append(f"contrast({contrast}%)")
    if saturation != 100:
        parts.append(f"saturate({saturation}%)")
    if grayscale:
        parts.append("grayscale(100%)")
    if sepia:
        parts.append("sepia(100%)")
    if blur > 0:
        parts.append(f"blur({blur}px)")
    return " ".join(parts) if parts else None


def _build_clip_segments(
    video_url: str,
    trim_start: float,
    trim_end: float,
    speed: float,
    extra_clips: Optional[List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    segments = [
        {"source": video_url, "trim_start": trim_start, "trim_end": trim_end, "speed": speed}
    ]
    for index, clip in enumerate(extra_clips or []):
        clip_url = clip.get("url")
        clip_start = float(clip.get("trim_start", 0) or 0)
        clip_end = float(clip.get("trim_end", 0) or 0)
        if not clip_url:
            continue
        if not _is_valid_url(clip_url):
            raise ValueError(f"Additional clip #{index + 1} needs a valid public video URL")
        if clip_end <= clip_start:
            raise ValueError(f"Additional clip #{index + 1} trim end must be greater than trim start")
        segments.append(
            {"source": clip_url, "trim_start": clip_start, "trim_end": clip_end, "speed": speed}
        )
    return segments


def _build_clip_elements(
    segments: List[Dict[str, Any]],
    *,
    fit: str,
    mute: bool,
    video_filter: Optional[str],
    video_x: int,
    video_y: int,
    video_zoom: int,
    border_radius: int,
    border_width: int,
    border_color: str,
    shadow: bool,
    transition: Optional[str],
    transition_duration: float,
    transition_direction: str,
    track: int,
) -> tuple[List[Dict[str, Any]], float]:
    elements: List[Dict[str, Any]] = []
    offset = 0.0
    for segment in segments:
        duration = round((segment["trim_end"] - segment["trim_start"]) / segment["speed"], 3)
        element: Dict[str, Any] = {
            "type": "video",
            "track": track,
            "time": round(offset, 3),
            "duration": duration,
            "trim_start": round(segment["trim_start"], 3),
            "trim_duration": round(segment["trim_end"] - segment["trim_start"], 3),
            "playback_rate": f"{round(segment['speed'] * 100)}%",
            "fit": fit,
            "volume": "0%" if mute else "100%",
            "source": segment["source"],
            "x": f"{video_x}%",
            "y": f"{video_y}%",
            "x_scale": f"{video_zoom}%",
            "y_scale": f"{video_zoom}%",
        }
        if video_filter:
            element["filter"] = video_filter
        if border_radius > 0:
            element["border_radius"] = border_radius
        if border_width > 0:
            element["border_width"] = border_width
            element["border_color"] = border_color
        if shadow:
            element["shadow_color"] = "rgba(0,0,0,0.5)"
            element["shadow_blur"] = 20

        animations: List[Dict[str, Any]] = []
        if transition:
            fade_duration = min(transition_duration, duration / 2)

            def _transition_anim(anim_time: float) -> Dict[str, Any]:
                anim: Dict[str, Any] = {
                    "time": anim_time,
                    "duration": fade_duration,
                    "transition": True,
                    "type": transition,
                }
                if transition != "fade":
                    anim["direction"] = transition_direction
                return anim

            animations.append(_transition_anim(0))
            animations.append(_transition_anim(max(0, duration - fade_duration)))
        if animations:
            element["animations"] = animations

        elements.append(element)
        offset += duration

    return elements, round(offset, 3)


def _build_source_payload(
    video_url: str,
    trim_start: float,
    trim_end: float,
    text_overlay: str,
    music_url: Optional[str],
    *,
    width: int = 1280,
    height: int = 720,
    video_fit: str = "cover",
    speed: float = 1.0,
    mute_video: bool = False,
    transition: Optional[str] = None,
    transition_duration: float = 0.5,
    transition_direction: str = "left",
    text_position: tuple[str, str] = ("50%", "90%"),
    text_duration: float = 5,
    text_size: int = 48,
    text_color: str = "#FFFFFF",
    text_weight: str = "normal",
    text_font_family: str = "Open Sans",
    text_background_color: Optional[str] = None,
    text_stroke_color: Optional[str] = None,
    text_stroke_width: float = 0,
    caption_text: str = "",
    caption_start: float = 0,
    caption_duration: float = 5,
    captions: Optional[List[Dict[str, Any]]] = None,
    music_volume: int = 40,
    music_fade_in: float = 1,
    music_fade_out: float = 1,
    voiceover_url: Optional[str] = None,
    voiceover_volume: int = 100,
    logo_url: Optional[str] = None,
    logo_position: tuple[str, str] = ("50%", "10%"),
    logo_size: int = 15,
    logo_opacity: int = 100,
    brightness: int = 100,
    contrast: int = 100,
    saturation: int = 100,
    grayscale: bool = False,
    sepia: bool = False,
    video_x: int = 50,
    video_y: int = 50,
    video_zoom: int = 100,
    extra_clips: Optional[List[Dict[str, Any]]] = None,
    video_border_radius: int = 0,
    video_border_width: int = 0,
    video_border_color: str = "#000000",
    video_shadow: bool = False,
    letterbox_blur: bool = False,
    text_fade_in: bool = False,
    logo_fade_in: bool = False,
    pip_url: Optional[str] = None,
    pip_position: tuple[str, str] = ("85%", "85%"),
    pip_size: int = 25,
    pip_opacity: int = 100,
    pip_mute: bool = True,
    shape_enabled: bool = False,
    shape_kind: str = "rectangle",
    shape_color: str = "#000000",
    shape_opacity: int = 50,
    shape_x: int = 50,
    shape_y: int = 90,
    shape_width: int = 60,
    shape_height: int = 15,
    shape_border_radius: int = 0,
    intro_image_url: Optional[str] = None,
    intro_duration: float = 1.5,
    outro_image_url: Optional[str] = None,
    outro_duration: float = 1.5,
) -> Dict[str, Any]:
    if trim_end <= trim_start:
        raise ValueError("Trim end must be greater than trim start")
    if video_fit not in {"cover", "contain", "fill"}:
        raise ValueError("Video framing must be cover, contain, or fill")
    if speed <= 0:
        raise ValueError("Playback speed must be greater than zero")
    if width <= 0 or height <= 0:
        raise ValueError("Output dimensions must be greater than zero")
    if transition is not None and transition not in _TRANSITION_TYPES:
        raise ValueError(f"Video transition must be one of {sorted(_TRANSITION_TYPES)}")
    if video_zoom <= 0:
        raise ValueError("Video zoom must be greater than zero")
    if shape_enabled and shape_kind not in _SHAPE_KINDS:
        raise ValueError(f"Shape kind must be one of {sorted(_SHAPE_KINDS)}")
    if intro_image_url and intro_duration <= 0:
        raise ValueError("Intro duration must be greater than zero")
    if outro_image_url and outro_duration <= 0:
        raise ValueError("Outro duration must be greater than zero")
    for url, description in (
        (music_url, "music"),
        (logo_url, "logo/image"),
        (voiceover_url, "voiceover"),
        (pip_url, "picture-in-picture"),
        (intro_image_url, "intro image"),
        (outro_image_url, "outro image"),
    ):
        if url and not _is_valid_url(url):
            raise ValueError(f"A valid public {description} URL is required")

    video_filter = _build_video_filter(brightness, contrast, saturation, grayscale, sepia)

    segments = _build_clip_segments(video_url, trim_start, trim_end, speed, extra_clips)
    clip_elements, clip_length = _build_clip_elements(
        segments,
        fit=video_fit,
        mute=mute_video,
        video_filter=video_filter,
        video_x=video_x,
        video_y=video_y,
        video_zoom=video_zoom,
        border_radius=video_border_radius,
        border_width=video_border_width,
        border_color=video_border_color,
        shadow=video_shadow,
        transition=transition,
        transition_duration=transition_duration,
        transition_direction=transition_direction,
        track=1,
    )

    elements: List[Dict[str, Any]] = []

    if letterbox_blur and video_fit == "contain":
        background_elements, _ = _build_clip_elements(
            segments,
            fit="cover",
            mute=True,
            video_filter=_build_video_filter(100, 100, 100, False, False, blur=20),
            video_x=50,
            video_y=50,
            video_zoom=100,
            border_radius=0,
            border_width=0,
            border_color="#000000",
            shadow=False,
            transition=None,
            transition_duration=0,
            transition_direction="left",
            track=0,
        )
        elements.extend(background_elements)

    elements.extend(clip_elements)

    if pip_url:
        elements.append(
            {
                "type": "video",
                "track": 7,
                "time": 0,
                "duration": clip_length,
                "source": pip_url,
                "fit": "cover",
                "volume": "0%" if pip_mute else "100%",
                "width": f"{pip_size}%",
                "height": f"{pip_size}%",
                "x_alignment": pip_position[0],
                "y_alignment": pip_position[1],
                "opacity": f"{pip_opacity}%",
            }
        )

    if shape_enabled:
        shape_element: Dict[str, Any] = {
            "type": "shape",
            "shape": shape_kind,
            "track": 8,
            "time": 0,
            "duration": clip_length,
            "width": f"{shape_width}%",
            "height": f"{shape_height}%",
            "x_alignment": f"{shape_x}%",
            "y_alignment": f"{shape_y}%",
            "fill_color": shape_color,
            "opacity": f"{shape_opacity}%",
        }
        if shape_kind == "rectangle" and shape_border_radius > 0:
            shape_element["border_radius"] = shape_border_radius
        elements.append(shape_element)

    if text_overlay:
        text_element: Dict[str, Any] = {
            "type": "text",
            "track": 2,
            "time": 0,
            "duration": min(clip_length, text_duration),
            "text": text_overlay,
            "x_alignment": text_position[0],
            "y_alignment": text_position[1],
            "font_family": text_font_family,
            "font_size": f"{text_size}px",
            "font_weight": "700" if text_weight == "bold" else "400",
            "fill_color": text_color,
        }
        if text_background_color:
            text_element["background_color"] = text_background_color
        if text_stroke_color and text_stroke_width > 0:
            text_element["stroke_color"] = text_stroke_color
            text_element["stroke_width"] = f"{text_stroke_width}px"
        if text_fade_in:
            fade_duration = min(0.5, text_element["duration"] / 2)
            text_element["animations"] = [{"time": 0, "duration": fade_duration, "type": "fade"}]
        elements.append(text_element)

    caption_rows: List[Dict[str, Any]] = list(captions or [])
    if caption_text and caption_start < clip_length:
        caption_rows.append(
            {
                "text": caption_text,
                "start": caption_start,
                "duration": caption_duration,
            }
        )

    for index, caption in enumerate(caption_rows):
        start = float(caption.get("start", 0))
        text = str(caption.get("text", "")).strip()
        if not text or start >= clip_length:
            continue
        duration = float(caption.get("duration", 5))
        elements.append(
            {
                "type": "text",
                "track": 3,
                "time": start,
                "duration": min(duration, clip_length - start),
                "text": text,
                "x_alignment": "50%",
                "y_alignment": "90%",
                "font_size": "32px",
                "fill_color": "#FFFFFF",
            }
        )

    if music_url:
        elements.append(
            {
                "type": "audio",
                "track": 4,
                "time": 0,
                "duration": clip_length,
                "source": music_url,
                "volume": f"{music_volume}%",
                "audio_fade_in": min(music_fade_in, clip_length),
                "audio_fade_out": min(music_fade_out, clip_length),
            }
        )

    if voiceover_url:
        elements.append(
            {
                "type": "audio",
                "track": 6,
                "time": 0,
                "duration": clip_length,
                "source": voiceover_url,
                "volume": f"{voiceover_volume}%",
            }
        )

    if logo_url:
        logo_element: Dict[str, Any] = {
            "type": "image",
            "track": 5,
            "time": 0,
            "duration": clip_length,
            "source": logo_url,
            "fit": "contain",
            "width": f"{logo_size}%",
            "height": f"{logo_size}%",
            "x_alignment": logo_position[0],
            "y_alignment": logo_position[1],
            "opacity": f"{logo_opacity}%",
        }
        if logo_fade_in:
            fade_duration = min(0.5, clip_length / 2)
            logo_element["animations"] = [{"time": 0, "duration": fade_duration, "type": "fade"}]
        elements.append(logo_element)

    content_offset = round(intro_duration, 3) if intro_image_url else 0.0
    if content_offset:
        for element in elements:
            element["time"] = round(element.get("time", 0) + content_offset, 3)

    if intro_image_url:
        elements.insert(
            0,
            {
                "type": "image",
                "track": 1,
                "time": 0,
                "duration": round(intro_duration, 3),
                "source": intro_image_url,
                "fit": "cover",
            },
        )

    total_duration = round(content_offset + clip_length, 3)
    if outro_image_url:
        elements.append(
            {
                "type": "image",
                "track": 1,
                "time": total_duration,
                "duration": round(outro_duration, 3),
                "source": outro_image_url,
                "fit": "cover",
            }
        )
        total_duration = round(total_duration + outro_duration, 3)

    return {
        "output_format": "mp4",
        "width": width,
        "height": height,
        "duration": total_duration,
        "elements": elements,
    }


def fetch_data(
    api_key: str,
    video_url: str,
    trim_start: float,
    trim_end: float,
    text_overlay: str = "",
    music_url: Optional[str] = None,
    **editing_options: Any,
) -> Dict[str, Any]:
    """Render a Creatomate video and return final video URL details."""
    if not api_key or not api_key.strip():
        raise ValueError("A Creatomate API key is required")
    if not _is_valid_url(video_url):
        raise ValueError("A valid, publicly accessible video source URL is required")

    source_payload = _build_source_payload(
        video_url=video_url,
        trim_start=trim_start,
        trim_end=trim_end,
        text_overlay=text_overlay,
        music_url=music_url,
        **editing_options,
    )

    render_response = _request(
        "POST",
        RENDER_ENDPOINT,
        api_key,
        json_payload={"source": source_payload},
        timeout=settings.DEFAULT_TIMEOUT * 2,
    )

    renders = render_response if isinstance(render_response, list) else [render_response]
    if not renders or not isinstance(renders[0], dict):
        raise RuntimeError("Creatomate render response was empty or malformed")

    render_id = renders[0].get("id")
    if not render_id:
        raise RuntimeError("Creatomate render ID was not returned")

    deadline = time.time() + settings.RENDER_WAIT_TIMEOUT
    while time.time() < deadline:
        status_response = _request(
            "GET",
            f"{RENDER_ENDPOINT}/{render_id}",
            api_key,
            timeout=settings.DEFAULT_TIMEOUT,
        )
        status = str(_extract(status_response, "status") or "").lower()

        if status == TERMINAL_SUCCESS_STATUS:
            final_url = _extract(status_response, "url")
            if not _is_valid_url(final_url):
                raise RuntimeError("Render finished but no downloadable video URL was returned")
            return {"status": "done", "url": str(final_url), "render_id": str(render_id)}

        if status in TERMINAL_FAILURE_STATUSES:
            message = _extract(status_response, "error_message") or "Creatomate render failed"
            return {"status": "failed", "error": str(message), "render_id": str(render_id)}

        time.sleep(settings.POLL_INTERVAL_SECONDS)

    raise TimeoutError(f"Timed out waiting for Creatomate render {render_id}")
