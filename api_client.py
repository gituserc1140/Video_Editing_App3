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
    text_position: tuple[str, str] = ("50%", "90%"),
    text_duration: float = 5,
    text_size: int = 48,
    text_color: str = "#FFFFFF",
    text_weight: str = "normal",
    caption_text: str = "",
    caption_start: float = 0,
    caption_duration: float = 5,
    music_volume: int = 40,
    music_fade_in: float = 1,
    music_fade_out: float = 1,
    logo_url: Optional[str] = None,
    logo_position: tuple[str, str] = ("50%", "10%"),
    logo_size: int = 15,
    logo_opacity: int = 100,
) -> Dict[str, Any]:
    if trim_end <= trim_start:
        raise ValueError("Trim end must be greater than trim start")
    if video_fit not in {"cover", "contain", "fill"}:
        raise ValueError("Video framing must be cover, contain, or fill")
    if speed <= 0:
        raise ValueError("Playback speed must be greater than zero")
    if width <= 0 or height <= 0:
        raise ValueError("Output dimensions must be greater than zero")
    for url, description in ((music_url, "music"), (logo_url, "logo/image")):
        if url and not _is_valid_url(url):
            raise ValueError(f"A valid public {description} URL is required")

    clip_length = round((trim_end - trim_start) / speed, 3)

    video_element: Dict[str, Any] = {
        "type": "video",
        "track": 1,
        "time": 0,
        "duration": clip_length,
        "trim_start": round(trim_start, 3),
        "trim_duration": round(trim_end - trim_start, 3),
        "playback_rate": f"{round(speed * 100)}%",
        "fit": video_fit,
        "volume": "0%" if mute_video else "100%",
        "source": video_url,
    }
    if transition == "fade":
        fade_duration = min(transition_duration, clip_length / 2)
        video_element["animations"] = [
            {"time": 0, "duration": fade_duration, "transition": True, "type": "fade"},
            {
                "time": max(0, clip_length - fade_duration),
                "duration": fade_duration,
                "transition": True,
                "type": "fade",
            },
        ]
    elements: List[Dict[str, Any]] = [video_element]

    if text_overlay:
        elements.append(
            {
                "type": "text",
                "track": 2,
                "time": 0,
                "duration": min(clip_length, text_duration),
                "text": text_overlay,
                "x_alignment": text_position[0],
                "y_alignment": text_position[1],
                "font_size": f"{text_size}px",
                "font_weight": "700" if text_weight == "bold" else "400",
                "fill_color": text_color,
            }
        )

    if caption_text and caption_start < clip_length:
        elements.append(
            {
                "type": "text",
                "track": 3,
                "time": caption_start,
                "duration": min(caption_duration, clip_length - caption_start),
                "text": caption_text,
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

    if logo_url:
        elements.append(
            {
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
        )

    return {
        "output_format": "mp4",
        "width": width,
        "height": height,
        "duration": clip_length,
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
