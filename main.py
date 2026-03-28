from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from typing import List, Dict

from backend.recommend import get_recommendations, save_feedback
from backend.spotify_playlist import create_playlist

app = FastAPI(title="Emotion Music API")

# -------------------------
# SESSION FEEDBACK STORE
# In-memory {song_id: rating} — lives for the server process lifetime.
# Merged with DB feedback on every /recommend call so ratings affect
# the very next query in the same session.
# -------------------------
_session_feedback: Dict[int, int] = {}

# -------------------------
# FRONTEND SERVING
# -------------------------
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
def serve_frontend():
    return FileResponse("frontend/index.html")

@app.get("/callback", response_class=HTMLResponse)
def spotify_callback():
    return """
    <html>
        <head>
            <title>Spotify Authorized</title>
            <style>
                body {
                    background: #121212; color: #1db954;
                    font-family: system-ui, sans-serif;
                    display: flex; justify-content: center;
                    align-items: center; height: 100vh;
                }
            </style>
        </head>
        <body>
            <h2>Spotify authorization successful. You can close this tab.</h2>
        </body>
    </html>
    """

# -------------------------
# MIDDLEWARE
# -------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# REQUEST MODELS
# -------------------------
class EmotionRequest(BaseModel):
    text: str
    allow_explicit: bool = True
    track_count: int = 10   # number of tracks to return (5-25, clamped in backend)

class PlaylistRequest(BaseModel):
    name: str
    spotify_uris: List[str]
    primary_emotion: str = ""
    secondary_emotions: List[str] = []
    prompt: str = ""   # original user input text

class FeedbackRequest(BaseModel):
    song_id: int
    emotion: str   # primary emotion active when the user rated this song
    rating: int    # +1 like, -1 dislike

# -------------------------
# ENDPOINTS
# -------------------------

@app.post("/recommend")
def recommend(req: EmotionRequest):
    return get_recommendations(
        text=req.text,
        allow_explicit=req.allow_explicit,
        session_feedback=_session_feedback,
        track_count=req.track_count,
    )

@app.post("/feedback")
def feedback(req: FeedbackRequest):
    if req.rating not in (1, -1):
        return {"error": "rating must be 1 or -1"}

    # Persist to DB
    save_feedback(song_id=req.song_id, emotion=req.emotion, rating=req.rating)

    # Update session store so next /recommend sees it immediately
    _session_feedback[req.song_id] = req.rating

    return {"status": "ok", "song_id": req.song_id, "rating": req.rating}

@app.post("/create-playlist")
def create_playlist_endpoint(req: PlaylistRequest):
    # Build a meaningful description using the user's actual prompt
    if req.primary_emotion and req.prompt:
        emotions_str = " · ".join([req.primary_emotion] + req.secondary_emotions)
        # Truncate prompt to 80 chars so description stays clean on Spotify
        short_prompt = req.prompt[:80] + ("..." if len(req.prompt) > 80 else "")
        description = f'"{short_prompt}" — Reverie detected: {emotions_str}'
    elif req.primary_emotion:
        parts = [req.primary_emotion] + req.secondary_emotions
        description = "Reverie detected: " + " · ".join(parts)
    else:
        description = "Emotion-driven playlist by Reverie"

    return create_playlist(
        playlist_name=req.name,
        spotify_uris=req.spotify_uris,
        description=description,
        public=False
    )