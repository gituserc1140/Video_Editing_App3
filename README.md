# Creatomate Video Editing Micro-App

A Streamlit micro-app for simple Creatomate-powered video editing using the Template_App_Private-style structure.

## Repository structure

- `app.py` — Streamlit entrypoint
- `api_client.py` — Creatomate API client (`fetch_data()` renders and polls)
- `s3_storage.py` — private S3 upload helper that returns time-limited presigned URLs
- `ui/` — Streamlit UI form and result rendering
- `static/` — app styling assets
- `config/` — environment-configurable settings
- `README.md` — usage instructions

## Requirements

- Python 3.10+
- A [Creatomate](https://creatomate.com/) API key
- (Optional, for the "Upload video" tab) An AWS account with a **private** S3 bucket and an IAM
  user/role scoped to `s3:PutObject` and `s3:GetObject` on that bucket

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the app:

```bash
streamlit run app.py
```

### Configuring private S3 uploads (optional)

If you want to upload videos directly from the app instead of pasting a URL, set the following
as environment variables (or as [Streamlit secrets](https://docs.streamlit.io/develop/concepts/connections/secrets-management)
when deployed — they are automatically forwarded into the process environment at startup):

- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` — credentials for an IAM user/role with
  `s3:PutObject`/`s3:GetObject` permissions scoped to your bucket only
- `AWS_S3_BUCKET` — the name of a **private** S3 bucket (keep "Block all public access" enabled)
- `AWS_S3_REGION` — the bucket's AWS region (defaults to `us-east-1`)
- `S3_UPLOAD_PREFIX` — optional key prefix for uploaded objects (defaults to `uploads`)
- `S3_PRESIGNED_URL_EXPIRY_SECONDS` — how long the generated link stays valid (defaults to `3600`)

The bucket itself is never made public. Each upload generates a presigned URL that only works
for a limited time, after which the video becomes inaccessible again without your AWS credentials —
useful for videos you intend to post/monetize later and don't want exposed indefinitely.

## How to use

1. **Enter API key**
   - Paste your Creatomate API key into the `Creatomate API key` field. You can find it in your Creatomate project settings.

2. **Provide a video source**
   - **Paste video URL** tab: enter a publicly accessible URL to an MP4 (or other supported) video file.
   - **S3 upload help** tab: use the `Sign in to AWS` button to open the AWS sign-in page, then paste a
     usable video URL into the first tab.

3. **Configure edits**
   - Set `Trim start (seconds)` and `Trim end (seconds)`.
   - Choose output resolution/aspect ratio and whether to crop, contain, or stretch the video.
   - Set playback speed, mute source audio, and optionally add fade transitions.
   - Add an optional text overlay with position, size, color, weight, and duration controls.
   - Add an optional timed caption.
   - Add an `Optional music URL` (must be publicly accessible) with volume and fade controls.
   - Add an optional publicly accessible logo/image URL with position, size, and opacity controls.

4. **Render video**
   - Click `Render Video`.
   - The app submits a Creatomate render request (`POST https://api.creatomate.com/v1/renders`), polls render status (`GET /v1/renders/{render_id}`), then displays the final video.

5. **Download output**
   - Use the `Download rendered video` link shown after render completion.

## Notes

- Trim end must be greater than trim start.
- The app keeps API key entry in the UI (not hard-coded).
- AWS credentials are never hard-coded; they are read from the environment/Streamlit secrets by boto3's standard credential chain.
- Polling and timeout behavior can be adjusted via environment variables in `config/settings.py`.
- Rendering consumes your Creatomate plan credits; choose shorter clips and lower resolutions to remain
  within your plan's free-tier limits.
