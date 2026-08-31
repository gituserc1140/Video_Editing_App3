# Creatomate Video Editing Micro-App

A Streamlit micro-app for simple Creatomate-powered video editing using the Template_App_Private-style structure.

## Repository structure

- `app.py` — Streamlit entrypoint
- `api_client.py` — Creatomate API client (`fetch_data()` renders and polls)
- `ui/` — Streamlit UI form and result rendering
- `static/` — app styling assets
- `config/` — environment-configurable settings
- `README.md` — usage instructions

## Requirements

- Python 3.10+
- A [Creatomate](https://creatomate.com/) API key

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the app:

```bash
streamlit run app.py
```

## How to use

1. **Enter API key**
   - Paste your Creatomate API key into the `Creatomate API key` field. You can find it in your Creatomate project settings.

2. **Provide a video source URL**
   - Enter a publicly accessible URL to an MP4 (or other supported) video file. Creatomate fetches the source directly from this URL, so it must be reachable from the internet (e.g. a link to a file you've already uploaded to cloud storage).

3. **Configure edits**
   - Set `Trim start (seconds)` and `Trim end (seconds)`.
   - Add `Text overlay` (optional).
   - Add an `Optional music URL` (optional, must be a publicly accessible audio URL).

4. **Render video**
   - Click `Render Video`.
   - The app submits a Creatomate render request (`POST https://api.creatomate.com/v1/renders`), polls render status (`GET /v1/renders/{render_id}`), then displays the final video.

5. **Download output**
   - Use the `Download rendered video` link shown after render completion.

## Notes

- Trim end must be greater than trim start.
- The app keeps API key entry in the UI (not hard-coded).
- Polling and timeout behavior can be adjusted via environment variables in `config/settings.py`.
