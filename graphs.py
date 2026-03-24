import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import os

df = pd.read_csv("songs.csv")

output_dir = "charts"
os.makedirs(output_dir, exist_ok=True)

# ─── 1. BAR CHART: All emotions combined (primary + secondary) ──────────────
emotion_cols = ["p_emotion", "s_emotion_1", "s_emotion_2", "s_emotion_3"]

all_emotions = pd.concat([df[col] for col in emotion_cols], ignore_index=True)
all_emotions = all_emotions.dropna().str.strip()
emotion_counts = all_emotions.value_counts()

fig, ax = plt.subplots(figsize=(16, 7))
colors = plt.cm.tab20.colors
bars = ax.bar(emotion_counts.index, emotion_counts.values,
              color=[colors[i % len(colors)] for i in range(len(emotion_counts))])
ax.set_title("Number of Songs per Emotion (All Columns Combined)", fontsize=16, fontweight="bold", pad=15)
ax.set_xlabel("Emotion", fontsize=12)
ax.set_ylabel("Count", fontsize=12)
ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
plt.xticks(rotation=45, ha="right", fontsize=9)
for bar in bars:
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
            str(int(bar.get_height())), ha="center", va="bottom", fontsize=8)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "emotion_bar.png"), dpi=150)
plt.show()
print("Saved: emotion_bar.png")

# ─── 2. PIE CHART: is_explicit ──────────────────────────────────────────────
explicit_counts = df["is_explicit"].value_counts()

fig, ax = plt.subplots(figsize=(7, 7))
ax.pie(explicit_counts.values, labels=explicit_counts.index, autopct="%1.1f%%",
       startangle=140, colors=["#FF6B6B", "#4ECDC4"],
       wedgeprops={"edgecolor": "white", "linewidth": 2})
ax.set_title("Explicit vs Non-Explicit Songs", fontsize=15, fontweight="bold", pad=15)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "explicit_pie.png"), dpi=150)
plt.show()
print("Saved: explicit_pie.png")

# ─── 3. PIE CHART: Genre ────────────────────────────────────────────────────
genre_counts = df["genre"].value_counts()

fig, ax = plt.subplots(figsize=(8, 8))
ax.pie(genre_counts.values, labels=genre_counts.index, autopct="%1.1f%%",
       startangle=140, colors=plt.cm.Set3.colors[:len(genre_counts)],
       wedgeprops={"edgecolor": "white", "linewidth": 2})
ax.set_title("Song Distribution by Genre", fontsize=15, fontweight="bold", pad=15)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "genre_pie.png"), dpi=150)
plt.show()
print("Saved: genre_pie.png")

# ─── 4. PIE CHART: Energy Level ─────────────────────────────────────────────
energy_counts = df["energy_level"].value_counts()

fig, ax = plt.subplots(figsize=(7, 7))
ax.pie(energy_counts.values, labels=energy_counts.index, autopct="%1.1f%%",
       startangle=140, colors=["#F7DC6F", "#E67E22", "#E74C3C"],
       wedgeprops={"edgecolor": "white", "linewidth": 2})
ax.set_title("Song Distribution by Energy Level", fontsize=15, fontweight="bold", pad=15)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "energy_pie.png"), dpi=150)
plt.show()
print("Saved: energy_pie.png")

# ─── 5. PIE CHART: Tempo ────────────────────────────────────────────────────
tempo_counts = df["tempo_category"].value_counts()

fig, ax = plt.subplots(figsize=(7, 7))
ax.pie(tempo_counts.values, labels=tempo_counts.index, autopct="%1.1f%%",
       startangle=140, colors=["#AED6F1", "#5DADE2", "#1A5276"],
       wedgeprops={"edgecolor": "white", "linewidth": 2})
ax.set_title("Song Distribution by Tempo", fontsize=15, fontweight="bold", pad=15)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "tempo_pie.png"), dpi=150)
plt.show()
print("Saved: tempo_pie.png")

print(f"\nAll charts saved to ./{output_dir}/")