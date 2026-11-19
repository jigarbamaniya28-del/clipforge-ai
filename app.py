import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).parent
WORK_DIR = APP_DIR / "work"
OUT_DIR = APP_DIR / "outputs"
WORK_DIR.mkdir(exist_ok=True)
OUT_DIR.mkdir(exist_ok=True)

st.set_page_config(page_title="ClipForge AI", page_icon="✂️", layout="wide")

st.markdown("""
<style>
.stApp { background: #0d0f17; color: #f4f4f5; }
.block-container { padding-top: 2rem; max-width: 1180px; }
.hero { padding: 1.4rem 1.6rem; border: 1px solid #292d3d; border-radius: 18px;
        background: linear-gradient(120deg,#171a2a,#211735); margin-bottom: 1rem; }
.hero h1 { margin: 0; font-size: 2.25rem; }
.hero p { color: #b7b9c9; margin-bottom: 0; }
div[data-testid="stMetric"] { background:#171a25; padding:14px; border-radius:12px; border:1px solid #292d3d; }
.stButton button, .stDownloadButton button { border-radius: 10px; }
.small-note { color:#a1a1aa; font-size:.88rem; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <h1>✂️ ClipForge AI</h1>
  <p>Your personal, local-first video clipping studio. Turn long videos into vertical Shorts.</p>
</div>
""", unsafe_allow_html=True)

def run_cmd(args):
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-2500:] or "Command failed")
    return result.stdout

def check_ffmpeg():
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None

def get_duration(path):
    out = run_cmd([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ])
    return float(out.strip())

def download_url(url, destination):
    # yt-dlp only downloads media the user is permitted to access and download.
    run_cmd([
        "yt-dlp", "--no-playlist", "-f", "bv*+ba/b",
        "--merge-output-format", "mp4", "-o", str(destination), url
    ])
    if not destination.exists():
        # yt-dlp may append/choose an extension; find the produced file.
        matches = list(destination.parent.glob(destination.stem + ".*"))
        if matches:
            return matches[0]
        raise RuntimeError("The downloader did not create an output file.")
    return destination

def transcribe_video(video_path, model_size):
    from faster_whisper import WhisperModel
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(video_path), vad_filter=True, word_timestamps=False)
    rows = []
    for seg in segments:
        text = (seg.text or "").strip()
        if text:
            rows.append({"start": float(seg.start), "end": float(seg.end), "text": text})
    return rows, info

HOOK_WORDS = {
    "wow", "wait", "what", "crazy", "insane", "secret", "never", "amazing",
    "incredible", "impossible", "funny", "fail", "winning", "danger", "happened",
    "unbelievable", "best", "worst", "look", "listen", "finally", " omg "
}

def score_window(rows, start, end):
    text = " ".join(r["text"] for r in rows if r["start"] < end and r["end"] > start)
    words = re.findall(r"[a-zA-Z']+", text.lower())
    if not words:
        return 0.0, text
    hook_hits = sum(1 for w in words if w in HOOK_WORDS)
    # Prefer clips with enough spoken content and a few potential hooks.
    density = min(len(words) / 55.0, 1.0)
    hook_score = min(hook_hits / 3.0, 1.0)
    sentence_bonus = 0.15 if re.search(r"[.!?]", text) else 0.0
    return min(0.7 * density + 0.3 * hook_score + sentence_bonus, 1.0), text

def make_suggestions(rows, duration, clip_len, max_clips):
    if not rows:
        return []
    step = max(8, int(clip_len * 0.55))
    candidates = []
    start = 0
    while start < duration:
        end = min(start + clip_len, duration)
        if end - start >= min(12, clip_len * 0.5):
            score, text = score_window(rows, start, end)
            if text.strip():
                candidates.append({"start": float(start), "end": float(end),
                                   "score": score, "transcript": text})
        start += step
    candidates.sort(key=lambda x: x["score"], reverse=True)
    selected = []
    for item in candidates:
        # Avoid near-duplicate overlapping suggestions.
        if all(item["end"] <= s["start"] or item["start"] >= s["end"] for s in selected):
            selected.append(item)
        if len(selected) >= max_clips:
            break
    selected.sort(key=lambda x: x["start"])
    return selected

def export_clip(video_path, start, end, output_path, vertical=True, burn_subtitles=False, transcript_rows=None):
    duration = max(1, end - start)
    vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    if not vertical:
        vf = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
    cmd = ["ffmpeg", "-y", "-ss", str(start), "-i", str(video_path), "-t", str(duration),
           "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
           "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(output_path)]
    run_cmd(cmd)

if "video_path" not in st.session_state:
    st.session_state.video_path = None
if "suggestions" not in st.session_state:
    st.session_state.suggestions = []
if "transcript" not in st.session_state:
    st.session_state.transcript = []

if not check_ffmpeg():
    st.error("FFmpeg and FFprobe are required but were not found. Install FFmpeg, add its bin folder to PATH, then restart this app.")
    st.markdown("[FFmpeg installation guide](https://ffmpeg.org/download.html)")
    st.stop()

left, right = st.columns([1.2, 0.8], gap="large")
with left:
    st.subheader("1 · Add your video")
    source_mode = st.radio("Choose input", ["Upload a video", "Paste a supported video URL"], horizontal=True)
    video_file = None
    url = ""
    if source_mode == "Upload a video":
        video_file = st.file_uploader("Choose MP4, MOV, MKV or WebM", type=["mp4", "mov", "mkv", "webm"])
        if video_file and st.button("Use uploaded video", type="primary"):
            suffix = Path(video_file.name).suffix or ".mp4"
            path = WORK_DIR / ("source" + suffix)
            path.write_bytes(video_file.getbuffer())
            st.session_state.video_path = path
            st.session_state.suggestions = []
            st.session_state.transcript = []
            st.success(f"Loaded: {video_file.name}")
    else:
        url = st.text_input("Video URL", placeholder="https://...")
        st.caption("Use only links you own or are authorized to download. Some platforms block downloads or restrict reuse.")
        if st.button("Import video", type="primary", disabled=not url.strip()):
            try:
                with st.spinner("Importing video…"):
                    path = download_url(url.strip(), WORK_DIR / "source.mp4")
                st.session_state.video_path = path
                st.session_state.suggestions = []
                st.session_state.transcript = []
                st.success("Video imported.")
            except Exception as e:
                st.error(f"Could not import this URL: {e}")

with right:
    st.subheader("2 · AI settings")
    model_size = st.selectbox("Speech model", ["tiny", "base", "small"], index=1,
                              help="Tiny is fastest; small may be more accurate but needs more RAM and time.")
    clip_len = st.slider("Target clip length (seconds)", 15, 90, 45, 5)
    max_clips = st.slider("Number of clip suggestions", 1, 15, 6)
    vertical = st.toggle("Export vertical 9:16 for Shorts", value=True)
    st.caption("The first transcription run downloads the selected open-source Whisper model. It runs locally.")

video_path = st.session_state.video_path
if video_path and Path(video_path).exists():
    try:
        duration = get_duration(video_path)
        st.divider()
        st.subheader("Loaded video")
        st.write(f"**{Path(video_path).name}** · {int(duration//60)}m {int(duration%60)}s")
        st.video(str(video_path))
        if st.button("✨ Analyse video and find clips", type="primary", use_container_width=True):
            try:
                with st.spinner("Transcribing and finding candidate moments. This can take a while on the first run…"):
                    rows, info = transcribe_video(video_path, model_size)
                    suggestions = make_suggestions(rows, duration, clip_len, max_clips)
                st.session_state.transcript = rows
                st.session_state.suggestions = suggestions
                st.success(f"Analysis complete. Found {len(suggestions)} candidate clips.")
            except ImportError:
                st.error("Faster-Whisper is not installed. Run: pip install faster-whisper")
            except Exception as e:
                st.error(f"Analysis failed: {e}")

        if st.session_state.suggestions:
            st.divider()
            st.subheader("3 · Review and edit your clips")
            st.caption("Adjust timestamps before exporting. Suggestions are ranked using transcript content heuristics; they are not guaranteed viral moments.")
            for i, item in enumerate(st.session_state.suggestions):
                with st.container(border=True):
                    st.markdown(f"**Clip {i+1}** · AI score: {item['score']:.0%}")
                    c1, c2 = st.columns(2)
                    start = c1.number_input("Start (seconds)", min_value=0.0, max_value=float(duration),
                                            value=float(item["start"]), step=1.0, key=f"s_{i}")
                    end = c2.number_input("End (seconds)", min_value=0.0, max_value=float(duration),
                                          value=float(item["end"]), step=1.0, key=f"e_{i}")
                    st.caption(item["transcript"][:500] or "No transcript text.")
                    if end <= start:
                        st.warning("End time must be after start time.")
                    if st.button(f"Export Clip {i+1}", key=f"export_{i}", disabled=end <= start):
                        out = OUT_DIR / f"short_{i+1}.mp4"
                        try:
                            with st.spinner("Rendering MP4…"):
                                export_clip(video_path, start, end, out, vertical=vertical)
                            st.success(f"Exported {out.name}")
                            st.video(str(out))
                            st.download_button("Download MP4", data=out.read_bytes(),
                                               file_name=out.name, mime="video/mp4",
                                               key=f"download_{i}")
                        except Exception as e:
                            st.error(f"Export failed: {e}")
            if st.button("Export all edited clips"):
                progress = st.progress(0)
                for i, item in enumerate(st.session_state.suggestions):
                    start = st.session_state.get(f"s_{i}", item["start"])
                    end = st.session_state.get(f"e_{i}", item["end"])
                    if end > start:
                        out = OUT_DIR / f"short_{i+1}.mp4"
                        export_clip(video_path, start, end, out, vertical=vertical)
                    progress.progress((i+1)/len(st.session_state.suggestions))
                st.success(f"Finished exporting clips to: {OUT_DIR}")
                st.info("Use the Downloads section below to retrieve your exported files.")
            existing = sorted(OUT_DIR.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
            if existing:
                st.subheader("4 · Your exports")
                for p in existing[:20]:
                    st.download_button(f"Download {p.name}", data=p.read_bytes(),
                                       file_name=p.name, mime="video/mp4", key=f"out_{p.name}")
    except Exception as e:
        st.error(f"Could not read this video. Check that it is a valid media file. Details: {e}")
else:
    st.info("Add a video to get started. Your files and processing stay on this computer.")
    st.markdown("""
    **Current MVP capabilities**
    - Local video upload and supported URL import
    - Local speech transcription with Faster-Whisper
    - Suggested clip windows and editable timestamps
    - Vertical MP4 export with FFmpeg

    **Coming next**
    - Word-by-word animated subtitles
    - Face/speaker-aware reframing
    - Audio energy and scene-change scoring
    - Batch export as a ZIP
    """)

st.divider()
st.markdown('<p class="small-note">ClipForge AI · Personal local tool · Only download and reuse media you have rights or permission to use.</p>', unsafe_allow_html=True)
