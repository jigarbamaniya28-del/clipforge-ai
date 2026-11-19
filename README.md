# ClipForge AI — Personal Video Clipping Studio

A local-first MVP for turning long videos into candidate YouTube Shorts.

## Requirements
- Windows 10/11, macOS, or Linux
- Python 3.10–3.12 recommended
- FFmpeg + FFprobe installed and available on PATH
- Internet access only for installing packages / downloading Whisper model / importing permitted URLs

## Windows setup
1. Install Python from https://www.python.org/downloads/ (check "Add Python to PATH").
2. Install FFmpeg:
   - Download a Windows build from https://www.gyan.dev/ffmpeg/builds/
   - Extract it, add its `bin` folder to your Windows PATH.
   - Open a NEW Command Prompt and verify:
     `ffmpeg -version`
     `ffprobe -version`
3. Extract this ZIP.
4. Open Command Prompt in the `clipforge_ai` folder.
5. Create a virtual environment:
   `py -m venv .venv`
   `.venv\Scripts\activate`
6. Install dependencies:
   `python -m pip install --upgrade pip`
   `pip install -r requirements.txt`
7. Start the website:
   `streamlit run app.py`
8. Open the local address Streamlit prints (usually http://localhost:8501).

## macOS / Linux
Install Python 3.10–3.12 and FFmpeg with your package manager, then:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## How to use
1. Upload a video file, or paste a URL supported by yt-dlp for content you are authorized to download.
2. Select the Whisper model. `tiny` is fastest; `base` is a reasonable starting point.
3. Choose clip length and number of suggestions.
4. Click **Analyse video and find clips**.
5. Adjust start/end times.
6. Export individual clips or all suggestions.
7. Download MP4 files.

## Notes and limitations
- This is a starter MVP, not a production-grade viral clip predictor.
- Candidate selection currently uses local speech transcription plus simple text heuristics. It does not understand every visual event or guarantee engagement.
- Vertical export currently uses a centered crop. Smart face/speaker tracking and animated captions are planned improvements.
- URL importing depends on the source platform, yt-dlp support, login/access restrictions, and the platform's terms. It will not bypass DRM, paywalls, private access, or other technical restrictions.
- Respect copyright, platform terms, and creator permissions. Only process and republish content you own or are allowed to use.
- First transcription run may take time because Faster-Whisper downloads its model. Processing speed depends on your CPU/RAM.
- FFmpeg must be installed separately; it is not bundled in this project.
