
from fastapi import FastAPI

app = FastAPI(
    title="ClipForge AI",
    description="AI-powered video clipping API",
    version="1.0.0"
)

@app.get("/")
def home():
    return {
        "message": "ClipForge AI API is running"
    }

@app.get("/health")
def health():
    return {
        "status": "online",
        "service": "ClipForge AI"
    }
