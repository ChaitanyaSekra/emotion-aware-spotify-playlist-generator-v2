# 🎵 Reverie — Emotion-Aware Spotify Playlist Generation System

> Type how you feel. Reverie reads the emotion. Spotify gets the playlist.

Reverie detects the emotional tone of your free-form text using the Mistral AI API, maps it to a curated PostgreSQL database of annotated tracks using a multi-tier scoring engine, and automatically creates a Spotify playlist in your account — all in one flow. It also learns from your feedback over time.

---

## ✨ How It Works

```
User types: "I just got played and I'm done with people"
        ↓
  Emotion Classification (Mistral AI REST API)
  → primary: betrayal, secondary: [rage, self_respect]
  → confidence: 87%
        ↓
  Track Recommendation (Multi-Tier Scoring Engine)
  → Primary exact match: +100 pts
  → Secondary exact match: +30 pts each
  → Cluster-adjacent match: +15 pts
  → Audio tiebreaker (tempo + energy): +3 pts
  → Feedback multipliers: ×1.3 liked / ×0.5 disliked
        ↓
  Spotify Integration
  → Creates playlist with emotion-based description
  → Adds tracks to your account via /playlists/{id}/items
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Backend | Python, FastAPI, Uvicorn | REST API, pipeline orchestration |
| Emotion Detection | Mistral AI REST API (`mistral-small-latest`) | 29-category emotion classification |
| Database | PostgreSQL + SQLModel | Normalised track storage (Song, Emotion, Artist, Genre, Feedback) |
| Music API | Spotify Web API, Spotipy | Playlist creation, track insertion, OAuth |
| Frontend | HTML5, CSS3, Vanilla JS | Single-page interface |
| Config | python-dotenv | Environment variable management |

---

## 📁 Project Structure

```
app_v2/
├── main.py                        # FastAPI app, endpoints, session feedback store
├── backend/
│   ├── recommend.py               # Mistral API call, scoring engine, feedback logic
│   ├── spotify_playlist.py        # Spotify OAuth + playlist creation
│   ├── models.py                  # SQLModel table definitions
│   └── db.py                      # Database session management
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── .env                           # Credentials (never commit)
└── .spotify_token_cache           # OAuth token cache (never commit)
```

---

## 🗄️ Database Schema

Five normalised tables:

| Table | Key Columns |
|---|---|
| **Song** | song_id, song_name, artist_id (FK), p_emotion_id (FK), s_emotion_1/2/3_id (FK), genre_id (FK), tempo, energy_level, lang, is_explicit, spotify_uri |
| **Emotion** | emotion_id, emotion_name (29 categories) |
| **Artist** | artist_id, name |
| **Genre** | genre_id, genre_name |
| **Feedback** | id, song_id (FK), emotion, rating (+1 / −1) |

---

## 🧠 Emotion Taxonomy

29 categories:

`win` `confidence` `flex` `hype` `determination` `motivation` `confidence_boost` `self_respect` `rebellion` `happiness` `celebration` `love` `hope` `calm` `manifesting` `healing` `nostalgia` `remembering` `introspection` `loneliness` `melancholy` `sadness` `hurt` `heartbreak` `betrayal` `rage` `stress` `exhaustion` `failure`

---

## ⚙️ Setup

### 1. Clone the repo

```bash
git clone https://github.com/yourname/reverie.git
cd reverie/app_v2
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the `app_v2/` directory:

```env
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
MISTRAL_API_KEY=your_mistral_api_key_here
DATABASE_URL=postgresql://user:password@localhost:5432/reverie
```

- Spotify credentials: [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
- Mistral API key: [console.mistral.ai](https://console.mistral.ai)

### 5. Set up the database

Run these in your PostgreSQL client to create the Feedback table (all other tables are created by SQLModel on startup):

```sql
CREATE TABLE feedback (
    id          SERIAL PRIMARY KEY,
    song_id     INTEGER NOT NULL REFERENCES song(song_id) ON DELETE CASCADE,
    emotion     VARCHAR(50) NOT NULL,
    rating      SMALLINT NOT NULL CHECK (rating IN (1, -1))
);

CREATE INDEX idx_feedback_song_emotion ON feedback(song_id, emotion);
```

### 6. Configure your Spotify app

In the Spotify Developer Dashboard:
- **Redirect URI:** `http://127.0.0.1:8000/callback`
- **User Management:** Add your Spotify account email (required in Development Mode)

> ⚠️ Your Spotify account must have an **active Premium subscription** for write endpoints to work in Development Mode.

---

## 🚀 Running the App

```bash
uvicorn main:app --reload
```

On first run, Spotify will open a browser window for OAuth authorisation. After authorising, the token is cached in `.spotify_token_cache` for future runs.

Open your browser at: [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 🔌 API Endpoints

### `POST /recommend`

Classifies emotion from text and returns ranked matching tracks.

**Request:**
```json
{
  "text": "I just got played and I'm done with people",
  "allow_explicit": true
}
```

**Response:**
```json
{
  "emotion": {
    "primary": "betrayal",
    "secondary": ["rage", "self_respect"],
    "confidence": 87
  },
  "songs": [
    {
      "song_id": 12,
      "song_name": "Baatein",
      "artist_name": "Raabta",
      "spotify_uri": "spotify:track:4Ttg2ZRg24knfykSp52aiM",
      "is_explicit": false,
      "score": 130
    }
  ]
}
```

---

### `POST /create-playlist`

Creates a Spotify playlist and adds the recommended tracks.

**Request:**
```json
{
  "name": "Played by Reverie",
  "spotify_uris": ["spotify:track:4Ttg2ZRg24knfykSp52aiM"],
  "primary_emotion": "betrayal",
  "secondary_emotions": ["rage", "self_respect"],
  "prompt": "I just got played and I'm done with people"
}
```

**Response:**
```json
{
  "playlist_id": "26Lj5ld57gCfF9fg1Qd6pm",
  "playlist_url": "https://open.spotify.com/playlist/26Lj5ld57gCfF9fg1Qd6pm",
  "track_count": 10
}
```

The playlist description is automatically set to: `"I just got played and I'm done with people" — Reverie detected: betrayal · rage · self_respect`

---

### `POST /feedback`

Records a user rating for a track in the context of a specific emotion.

**Request:**
```json
{
  "song_id": 12,
  "emotion": "betrayal",
  "rating": -1
}
```

**Response:**
```json
{ "status": "ok", "song_id": 12, "rating": -1 }
```

Ratings affect the score of that track on the **next** `/recommend` call for the same emotion:
- `+1` (like) → score ×1.3
- `-1` (dislike) → score ×0.5

---

## 🔐 OAuth Flow

Reverie uses Spotify's **Authorization Code Flow**:

1. On startup, the app checks for a cached token in `.spotify_token_cache`
2. If none exists, it opens a browser for Spotify login
3. After authorisation, Spotify redirects to `http://127.0.0.1:8000/callback`
4. The token is cached locally for future sessions

**Required scopes:**
```
playlist-modify-private
playlist-modify-public
playlist-read-private
```

> **Note (Feb 2026):** Spotipy's `user_playlist_create()` and `playlist_add_items()` wrappers return HTTP 403 in Development Mode. Reverie bypasses both — playlist creation uses `sp._post("me/playlists")` directly, and track insertion uses raw `requests.post` to `/playlists/{id}/items`.

---

## 🚫 .gitignore

Make sure these are excluded from version control:

```
.env
.spotify_token_cache
.venv/
__pycache__/
*.pyc
```

---

## 📌 Known Limitations

- **Development Mode only** — up to 5 Spotify users. Apply for Extended Access on the Spotify Developer Dashboard for more.
- **Manually curated database** — tracks are hand-annotated; the dataset is currently limited in size.
- **Single user session** — designed for one authenticated Spotify account at a time.
- **Session feedback resets on restart** — in-memory feedback is lost when the server stops; persisted DB feedback carries over.

---

## 🗺️ Roadmap

- [ ] Scale DB using a fine-tuned LLM on song lyrics for existing catalogue
- [ ] Artist emotion-tagging integration at upload via DistroKid / RouteNote
- [ ] Language-based track filtering (detect input language, surface matching tracks)
- [ ] Artist diversity cap (max 2 tracks per artist per playlist)
- [ ] Cluster fallback when primary emotion has fewer than N results

---

## 📄 License

MIT License — feel free to use, modify, and distribute.