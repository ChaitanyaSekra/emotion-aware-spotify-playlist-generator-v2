document.addEventListener("DOMContentLoaded", () => {

  const submitBtn         = document.getElementById("submitBtn");
  const createPlaylistBtn = document.getElementById("createPlaylistBtn");
  const userInput         = document.getElementById("userInput");
  const loader            = document.getElementById("loader");
  const results           = document.getElementById("results");
  const songList          = document.getElementById("songList");
  const trackCount        = document.getElementById("trackCount");
  const emotionInfo       = document.getElementById("emotionInfo");
  const emotionPrimary    = document.getElementById("emotionPrimary");
  const emotionSecondary  = document.getElementById("emotionSecondary");
  const playlistLink      = document.getElementById("playlistLink");
  const spotifyLink       = document.getElementById("spotifyLink");
  const explicitToggle    = document.getElementById("explicitToggle");
  const filterStatus      = document.getElementById("filterStatus");
  const reelLeft          = document.getElementById("reelLeft");
  const reelRight         = document.getElementById("reelRight");

  let currentSongs             = [];
  let currentEmotion           = "";
  let currentSecondaryEmotions = [];
  let currentPromptText        = "";   // stores raw user input for playlist description
  let reelTimer                = null;

  // ── BACKGROUND CANVAS ─────────────────────────────────────
  const canvas = document.getElementById("bgCanvas");
  const ctx    = canvas.getContext("2d");
  let W, H, pts = [], t = 0;

  function initCanvas() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
    pts = Array.from({ length: 100 }, (_, i) => ({
      x: (i / 99) * W,
      offset: Math.random() * Math.PI * 2,
      speed: 0.003 + Math.random() * 0.004,
      amp: 18 + Math.random() * 55,
    }));
  }

  function drawBg() {
    ctx.clearRect(0, 0, W, H);
    t += 0.5;
    [0.32, 0.5, 0.68].forEach((yRatio, li) => {
      ctx.beginPath();
      pts.forEach((p, i) => {
        const y = H * yRatio + Math.sin(t * p.speed + p.offset + li * 1.3) * p.amp;
        i === 0 ? ctx.moveTo(p.x, y) : ctx.lineTo(p.x, y);
      });
      ctx.strokeStyle = `rgba(30,215,96,${0.055 - li * 0.012})`;
      ctx.lineWidth   = 1.4 - li * 0.3;
      ctx.stroke();
    });
    requestAnimationFrame(drawBg);
  }

  initCanvas(); drawBg();
  window.addEventListener("resize", initCanvas);

  // ── REELS ─────────────────────────────────────────────────
  function startReels() {
    reelLeft.classList.add("spinning");
    reelRight.classList.add("spinning");
  }
  function stopReels() {
    reelLeft.classList.remove("spinning");
    reelRight.classList.remove("spinning");
  }

  userInput.addEventListener("input", () => {
    startReels();
    clearTimeout(reelTimer);
    reelTimer = setTimeout(stopReels, 700);
  });

  // ── TOGGLE ────────────────────────────────────────────────
  explicitToggle.addEventListener("change", () => {
    filterStatus.textContent = explicitToggle.checked ? "ON" : "OFF";
    filterStatus.classList.toggle("off", !explicitToggle.checked);
  });

  // ── RECOMMENDATIONS ───────────────────────────────────────
  submitBtn.addEventListener("click", async () => {
    const text = userInput.value.trim();
    if (!text) { userInput.focus(); return; }
    currentPromptText = text;   // save for playlist description

    loader.classList.remove("hidden");
    results.classList.add("hidden");
    emotionInfo.classList.add("hidden");
    playlistLink.classList.add("hidden");
    createPlaylistBtn.classList.add("hidden");
    songList.innerHTML = "";
    submitBtn.disabled = true;
    startReels();

    try {
      const res  = await fetch("/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, allow_explicit: explicitToggle.checked })
      });
      const data = await res.json();

      loader.classList.add("hidden");
      submitBtn.disabled = false;
      stopReels();

      currentEmotion = data.emotion.primary;
      const confidence = data.emotion.confidence || "";
      emotionPrimary.textContent = currentEmotion.toUpperCase();
      // Confidence badge in the header
      const confEl = document.getElementById("emotionConfidence");
      if (confEl) confEl.textContent = confidence ? `${confidence}%` : "";
      const secs = Array.isArray(data.emotion.secondary) ? data.emotion.secondary.join("  ·  ") : "";
      emotionSecondary.textContent = secs ? `[ ${secs} ]` : "";
      // Store secondary emotions for playlist description
      currentSecondaryEmotions = data.emotion.secondary || [];
      emotionInfo.classList.remove("hidden");

      currentSongs = data.songs;
      trackCount.textContent = `${data.songs.length} TRACKS`;

      data.songs.forEach((song, i) => {
        const li = document.createElement("li");
        li.className = "song";
        li.dataset.songId = song.song_id;
        li.innerHTML = `
          <div class="song-index-block">
            <span class="song-index">${String(i + 1).padStart(2, "0")}</span>
          </div>
          <div class="song-info">
            <div class="song-name-row">
              <span class="song-name">${song.song_name}</span>
              ${song.is_explicit ? '<span class="explicit-badge">E</span>' : ""}
            </div>
            <span class="song-artist">${song.artist_name}</span>
          </div>
          <div class="song-feedback">
            <button class="fb-btn fb-like" data-song-id="${song.song_id}" title="Like">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14z"/>
                <path d="M7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/>
              </svg>
            </button>
            <button class="fb-btn fb-dislike" data-song-id="${song.song_id}" title="Dislike">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3H10z"/>
                <path d="M17 2h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"/>
              </svg>
            </button>
          </div>
        `;
        songList.appendChild(li);
      });

      attachFeedbackListeners();
      results.classList.remove("hidden");
      if (currentSongs.length > 0) createPlaylistBtn.classList.remove("hidden");

    } catch (err) {
      loader.classList.add("hidden");
      submitBtn.disabled = false;
      stopReels();
      console.error(err);
      showError("COULDN'T GET RECOMMENDATIONS. TRY AGAIN.");
    }
  });

  // ── FEEDBACK ──────────────────────────────────────────────
  function attachFeedbackListeners() {
    songList.querySelectorAll(".fb-like").forEach(btn =>
      btn.addEventListener("click", () => sendFeedback(btn, 1))
    );
    songList.querySelectorAll(".fb-dislike").forEach(btn =>
      btn.addEventListener("click", () => sendFeedback(btn, -1))
    );
  }

  async function sendFeedback(btn, rating) {
    const songId = parseInt(btn.dataset.songId, 10);
    const row    = btn.closest(".song");
    try {
      await fetch("/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ song_id: songId, emotion: currentEmotion, rating })
      });
      const like    = row.querySelector(".fb-like");
      const dislike = row.querySelector(".fb-dislike");
      like.classList.toggle("active",    rating === 1);
      dislike.classList.toggle("active", rating === -1);
    } catch (err) {
      console.error("Feedback error:", err);
      showError("FEEDBACK FAILED.");
    }
  }

  // ── PUSH TO SPOTIFY ───────────────────────────────────────
  createPlaylistBtn.addEventListener("click", async () => {
    const uris = currentSongs.map(s => s.spotify_uri).filter(Boolean);
    if (uris.length === 0) { showError("NO SPOTIFY TRACKS AVAILABLE"); return; }

    loader.classList.remove("hidden");
    createPlaylistBtn.disabled = true;
    playlistLink.classList.add("hidden");
    startReels();

    try {
      // Playlist name: dominant word from the prompt + "by Reverie"
      // Pick the longest meaningful word from the user's input as the title word
      const stopwords = new Set(["i","me","my","the","a","an","is","was","been","have",
        "had","be","are","and","or","but","in","on","at","to","for","of","with","it",
        "that","this","its","just","so","like","feel","feeling","been","very","really"]);
      const words = currentPromptText
        .toLowerCase()
        .replace(/[^a-z\s]/g, "")
        .split(/\s+/)
        .filter(w => w.length > 2 && !stopwords.has(w));
      const titleWord = words.length > 0
        ? capitalize(words.sort((a, b) => b.length - a.length)[0])
        : capitalize(currentEmotion || "mood");
      const name = `${titleWord} by Reverie`;

      const res  = await fetch("/create-playlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          spotify_uris: uris,
          primary_emotion: currentEmotion,
          secondary_emotions: currentSecondaryEmotions,
          prompt: currentPromptText
        })
      });
      const data = await res.json();
      loader.classList.add("hidden");
      createPlaylistBtn.disabled = false;
      stopReels();
      spotifyLink.href = data.playlist_url;
      playlistLink.classList.remove("hidden");
    } catch (err) {
      loader.classList.add("hidden");
      createPlaylistBtn.disabled = false;
      stopReels();
      showError("PLAYLIST CREATION FAILED. TRY AGAIN.");
    }
  });

  // ── HELPERS ───────────────────────────────────────────────
  function capitalize(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1).toLowerCase() : s; }

  function showError(msg) {
    const old = document.querySelector(".error-toast");
    if (old) old.remove();
    const toast = document.createElement("div");
    toast.className = "error-toast";
    toast.textContent = msg;
    toast.style.cssText = `
      position:fixed; bottom:24px; left:50%; transform:translateX(-50%);
      background:rgba(255,59,59,0.1); border:1px solid rgba(255,59,59,0.3);
      color:#ff6b6b; padding:10px 22px; border-radius:3px;
      font-family:'Space Mono',monospace; font-size:0.62rem;
      letter-spacing:0.15em; z-index:1000;
      animation:fadeUp 0.3s ease both;
    `;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
  }

  userInput.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") submitBtn.click();
  });
});