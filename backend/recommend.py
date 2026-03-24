from typing import List, Dict
from sqlmodel import select
from backend.db import get_session
from backend.models import Song, Emotion, Artist, Feedback
import os
import json
import requests

# ---- EMOTIONS ----
EMOTIONS = {
    "win", "confidence", "motivation", "happiness", "celebration",
    "love", "hope", "calm", "nostalgia", "loneliness",
    "introspection", "healing", "heartbreak", "sadness",
    "rage", "stress", "exhaustion", "failure", "hype",
    "rebellion", "confidence_boost", "melancholy",
    "determination", "remembering", "manifesting",
    "flex", "self_respect", "betrayal", "hurt"
}

PRIMARY_SCORE   = 100
SECONDARY_SCORE = 30
CLUSTER_SCORE   = 15
TIEBREAK_BONUS  = 3   # tiny — only breaks ties, never flips emotion rankings

EMOTION_CLUSTERS = {
    # ───────────────
    # PAIN CORE
    # ───────────────
    "hurt":       ["sadness", "heartbreak", "betrayal", "loneliness"],
    "sadness":    ["melancholy", "loneliness", "hurt"],
    "heartbreak": ["hurt", "sadness", "nostalgia"],
    "betrayal":   ["hurt", "rage"],

    # ───────────────
    # INTROSPECTION / LOW ENERGY
    # ───────────────
    "melancholy":    ["sadness", "nostalgia", "introspection"],
    "nostalgia":     ["remembering", "melancholy"],
    "loneliness":    ["sadness", "introspection", "hurt"],
    "introspection": ["loneliness", "melancholy", "healing"],

    # ───────────────
    # RECOVERY
    # ───────────────
    "healing": ["hope", "calm", "introspection"],
    "hope":    ["healing", "motivation"],
    "calm":    ["healing", "introspection"],

    # ───────────────
    # ENERGY / DRIVE
    # ───────────────
    "confidence":       ["confidence_boost", "self_respect", "flex"],
    "confidence_boost": ["confidence", "motivation"],
    "motivation":       ["determination", "hype"],
    "determination":    ["motivation", "confidence"],
    "hype":             ["motivation", "confidence"],

    # ───────────────
    # AGGRESSION / RELEASE
    # ───────────────
    "rage":      ["betrayal", "rebellion"],
    "rebellion": ["rage", "self_respect"],

    # ───────────────
    # MEMORY / MEANING
    # ───────────────
    "remembering": ["nostalgia", "melancholy"],
}

# ---- AUDIO TIEBREAKER ----
# Preferred (tempo_category, energy_level) per emotion.
# Only adds TIEBREAK_BONUS when BOTH match — never overrides emotion score.
AUDIO_PREFERENCE = {
    "heartbreak":    ("slow", "low"),
    "sadness":       ("slow", "low"),
    "hurt":          ("slow", "low"),
    "melancholy":    ("slow", "low"),
    "loneliness":    ("slow", "low"),
    "introspection": ("slow", "low"),
    "exhaustion":    ("slow", "low"),
    "healing":       ("slow", "low"),
    "failure":       ("slow", "low"),
    "calm":          ("slow", "low"),
    "nostalgia":     ("slow", "medium"),
    "remembering":   ("slow", "medium"),
    "hope":          ("mid",  "low"),
    "manifesting":   ("mid",  "low"),
    "stress":        ("mid",  "medium"),
    "betrayal":      ("mid",  "medium"),
    "love":          ("mid",  "medium"),
    "rage":          ("fast", "high"),
    "hype":          ("fast", "high"),
    "rebellion":     ("fast", "high"),
    "win":           ("fast", "high"),
    "motivation":    ("fast", "high"),
    "determination": ("fast", "high"),
    "happiness":     ("fast", "high"),
    "celebration":   ("fast", "high"),
    "confidence":    ("mid",  "high"),
    "flex":          ("mid",  "high"),
    "confidence_boost": ("mid", "high"),
    "self_respect":  ("mid",  "high"),
}


# ---------------- LLM ----------------

def extract_emotions(text: str) -> Dict:
    prompt = f"""
You are an emotion classification engine. Your only job is to output JSON.

TASK

Given a text input, identify what emotional state the person is experiencing.
Think about the SITUATION and UNDERLYING FEELING — not just the surface words.


ALLOWED_EMOTIONS (use ONLY these, exactly as written)

win, confidence, motivation, happiness, celebration, love, hope, calm,
nostalgia, loneliness, introspection, healing, heartbreak, sadness, rage,
stress, exhaustion, failure, hype, rebellion, confidence_boost, melancholy,
determination, remembering, manifesting, flex, self_respect, betrayal, hurt


EMOTION GUIDE (how to map situations → emotions)

Use this table to resolve ambiguous or overlapping cases:

SITUATION                                         → PRIMARY EMOTION
──────────────────────────────────────────────────────────────────
Got a job / promotion / big achievement           → win
Feeling powerful, untouchable, on top             → confidence
Showing off success, money, status                → flex
Pumped up, fired up before something big         → hype
Need to push through, not giving up               → determination
Just starting to feel better after pain           → healing
Wishing / visualizing the future you want         → manifesting
Missing a specific person or time                 → remembering
Missing the feeling of the past in general        → nostalgia
Processing grief or a bad chapter alone           → introspection
Was wronged, used, deceived by someone            → betrayal
Emotionally wounded but not full heartbreak       → hurt
Relationship ended / lost someone you loved       → heartbreak
General low mood, no specific cause               → melancholy
Deep sadness with a clear reason                  → sadness
Burned out, running on empty                      → exhaustion
Feeling like you failed at something important    → failure
Furious, explosive anger                          → rage
Overwhelmed by pressure / deadlines               → stress
Trusting the future will be better                → hope
At peace, no pressure, quiet mind                 → calm
Romantic love, warmth for another person          → love
Joy, things are good right now                    → happiness
Marking a milestone, party energy                 → celebration
Standing up for yourself, done being disrespected → self_respect
Going against the system / norms                  → rebellion
Getting a compliment or recognition that lands    → confidence_boost
Feeling driven to improve yourself                → motivation


HARD RULES

1. Output ONLY valid JSON. No text before or after.
2. primary: exactly ONE emotion from ALLOWED_EMOTIONS.
3. secondary: ZERO to THREE emotions from ALLOWED_EMOTIONS.
4. BOTH primary and secondary must come from ALLOWED_EMOTIONS only.
5. Never invent emotion names. Never rephrase them.
6. If secondary emotions don't apply, return an empty array [].
7. Output must be parseable by Python's json.loads().


FEW-SHOT EXAMPLES

Input: "I finally got the job I've been working toward for 2 years"
Output: {{"primary": "win", "secondary": ["happiness", "determination"]}}

Input: "I keep thinking about her even though it's been months"
Output: {{"primary": "heartbreak", "secondary": ["loneliness", "remembering"]}}

Input: "I'm so done with people using me"
Output: {{"primary": "betrayal", "secondary": ["rage", "self_respect"]}}

Input: "Just want to lie in bed and do nothing today"
Output: {{"primary": "exhaustion", "secondary": ["melancholy"]}}

Input: "I know it's going to work out. I just feel it."
Output: {{"primary": "manifesting", "secondary": ["hope", "calm"]}}

Input: "New car, new apartment, life is good right now"
Output: {{"primary": "flex", "secondary": ["win", "happiness"]}}

Input: "I don't know why I feel empty lately"
Output: {{"primary": "melancholy", "secondary": ["introspection"]}}

Input: "My team is counting on me, I can't let them down"
Output: {{"primary": "determination", "secondary": ["stress", "motivation"]}}

OUTPUT FORMAT

{{
  "primary": "<one emotion from ALLOWED_EMOTIONS>",
  "secondary": ["<emotion>", "<emotion>"]
}}

TEXT:
{text}
"""

    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError("MISTRAL_API_KEY not set in .env")

    try:
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistral-small-latest",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,   # low temp = more deterministic JSON output
                "max_tokens": 150
            },
            timeout=30
        )
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise RuntimeError("Mistral API request timed out")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Mistral API request failed: {e}")

    raw_output = response.json()["choices"][0]["message"]["content"].strip()

    print("\n===== RAW MISTRAL OUTPUT =====")
    print(raw_output)
    print("===== END RAW OUTPUT =====\n")

    try:
        data = json.loads(raw_output)
    except json.JSONDecodeError:
        raise ValueError("Mistral returned invalid JSON")

    print("Parsed emotion object:", data)

    primary   = data.get("primary")
    secondary = data.get("secondary", [])

    if primary not in EMOTIONS:
        raise ValueError(f"Invalid primary emotion from Mistral: {primary}")

    secondary = [
        e for e in secondary
        if e in EMOTIONS and e != primary
    ][:3]

    return {"primary": primary, "secondary": secondary}


# ---------------- SCORING ----------------

def score_song(song, user, id_to_emotion):
    score = 0

    song_primary     = id_to_emotion[song.p_emotion_id]
    song_secondaries = [
        id_to_emotion[e] for e in
        [song.s_emotion_1_id, song.s_emotion_2_id, song.s_emotion_3_id]
        if e
    ]

    # ── Emotion score ──
    if song_primary == user["primary"]:
        score += PRIMARY_SCORE
    elif song_primary in EMOTION_CLUSTERS.get(user["primary"], []):
        score += CLUSTER_SCORE

    for ue in user["secondary"]:
        if ue in song_secondaries:
            score += SECONDARY_SCORE
        elif any(ue in EMOTION_CLUSTERS.get(se, []) for se in song_secondaries):
            score += CLUSTER_SCORE

    if song_secondaries:
        score = int(score * (1 / len(song_secondaries) + 0.5))

    # ── Audio tiebreaker (only applies when score > 0) ──
    if score > 0:
        pref = AUDIO_PREFERENCE.get(user["primary"])
        if pref:
            pref_tempo, pref_energy = pref
            if (song.tempo_category == pref_tempo and
                    song.energy_level == pref_energy):
                score += TIEBREAK_BONUS

    return score


# ---------------- FEEDBACK ----------------

def save_feedback(song_id: int, emotion: str, rating: int) -> None:
    """
    Upsert: if feedback already exists for this song+emotion, update it.
    Otherwise insert a new row.
    """
    with get_session() as session:
        existing = session.exec(
            select(Feedback).where(
                Feedback.song_id == song_id,
                Feedback.emotion == emotion
            )
        ).first()

        if existing:
            existing.rating = rating
            session.add(existing)
        else:
            session.add(Feedback(song_id=song_id, emotion=emotion, rating=rating))

        session.commit()


def get_feedback_map(song_ids: List[int], emotion: str) -> Dict[int, int]:
    """
    Returns {song_id: rating} for all persisted feedback rows
    matching the given emotion. Called once per recommendation request.
    """
    if not song_ids:
        return {}
    with get_session() as session:
        rows = session.exec(
            select(Feedback).where(
                Feedback.song_id.in_(song_ids),
                Feedback.emotion == emotion
            )
        ).all()
    return {row.song_id: row.rating for row in rows}


# ---------------- MAIN ENTRY ----------------

def get_recommendations(
    text: str,
    allow_explicit: bool = True,
    session_feedback: Dict[int, int] = None,  # {song_id: +1/-1} accumulated this session
    track_count: int = 10                      # number of tracks to return (5-25)
) -> Dict:

    user_emotion = extract_emotions(text)
    print("\n--- MISTRAL EMOTION OUTPUT ---")
    print(f"Primary   : {user_emotion['primary']}")
    print(f"Secondary : {user_emotion['secondary']}")
    print(f"Explicit  : {'allowed' if allow_explicit else 'filtered out'}")
    print(f"Tracks    : {track_count}")
    print("------------------------------\n")

    with get_session() as session:
        emotions   = session.exec(select(Emotion)).all()
        name_to_id = {e.emotion_name: e.emotion_id for e in emotions}
        id_to_name = {v: k for k, v in name_to_id.items()}

        emotion_ids = [name_to_id[user_emotion["primary"]]] + [
            name_to_id[e] for e in user_emotion["secondary"]
            if e in name_to_id
        ]

        query = (
            select(Song, Artist)
            .join(Artist, Song.artist_id == Artist.artist_id)
            .where(
                (Song.p_emotion_id.in_(emotion_ids)) |
                (Song.s_emotion_1_id.in_(emotion_ids)) |
                (Song.s_emotion_2_id.in_(emotion_ids)) |
                (Song.s_emotion_3_id.in_(emotion_ids))
            )
        )

        if not allow_explicit:
            query = query.where(Song.is_explicit == False)

        songs = session.exec(query).all()

    # ── Score every candidate ──
    ranked = []
    for song, artist in songs:
        sc = score_song(song, user_emotion, id_to_name)
        if sc > 0:
            ranked.append({
                "song_id":     song.song_id,
                "song_name":   song.song_name,
                "artist_name": artist.name,
                "spotify_uri": song.spotify_uri,
                "is_explicit": song.is_explicit,
                "score":       sc,
            })

    # ── Fetch persisted DB feedback for these songs ──
    all_song_ids = [r["song_id"] for r in ranked]
    db_feedback  = get_feedback_map(all_song_ids, user_emotion["primary"])

    # ── Merge: session feedback overrides DB for same song ──
    merged = {**db_feedback, **(session_feedback or {})}

    for r in ranked:
        fb = merged.get(r["song_id"])
        if fb == 1:
            r["score"] = int(r["score"] * 1.3)   # liked  → boost 30%
        elif fb == -1:
            r["score"] = int(r["score"] * 0.5)   # disliked → halve

    ranked.sort(key=lambda x: x["score"], reverse=True)

    return {
        "emotion": user_emotion,
        "songs":   ranked[:max(5, min(25, track_count))],
    }