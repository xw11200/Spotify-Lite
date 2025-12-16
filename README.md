# 🎧 Spotify Lite  
*A Python-based mini Spotify clone with GUI, playlists, lyrics.*

---

## 🌟 Overview
**Spotify Lite** is a lightweight desktop music player built with **Python** and **CustomTkinter**, featuring:
- Local MP3 playback via `pygame`
- Dynamic playlists and library management
- Automatic lyrics fetching (via Genius API / Lyrics.ovh)
- Cached lyrics for offline use
- Smart AI-based recommendation system
- Modern Spotify-style GUI theme

This project demonstrates object-oriented design, modular architecture, API integration, JSON persistence, and machine-learning concepts — making it a **High Distinction-level** FIT1045 capstone.

---

## 🧩 Project Structure

📁 Spotify-Lite/\
│
├── main.py                # CLI version (menu-based interface)\
├── gui-pro.py             # Full Spotify-style GUI\
├── gui-2.0.py             # Latest enhanced GUI layout\
│\
├── song.py                # Song class (title, artist, duration)\
├── player.py              # Player controls (play, pause, resume, stop)\
├── playlist.py            # Playlist management (add/remove/load)\
├── library.py             # Music library handling & metadata loading\
├── lyrics-fetcher.py      # Genius/Lyrics.ovh lyrics integration with cache\
│\
├── playlists.json         # Saved playlists\
├── lyrics_cache.json      # Cached lyrics data\
│\
└── requirements.txt       # Python dependencies\

---

## ⚙️ Features

### 🎵 Core Music Functions
- Play, pause, resume, skip, and stop tracks.
- Auto-detect title and artist from filename (`Song – Artist.mp3`).
- Track duration extracted using **Mutagen**.

### 💽 Playlists & Library
- Create, rename, and delete playlists.
- Songs loaded from `data/songs/` directory.
- Persistent storage using **JSON** (`playlists.json`).

### 🪶 Lyrics Fetcher (API Integration)
- Fetches lyrics from **Genius API** or **Lyrics.ovh**.
- Automatically caches results in `lyrics_cache.json`.
- Handles network errors gracefully with fallback text.

### 🖥️ Graphical User Interface
- Built using **CustomTkinter** (modern dark theme).
- Spotify-like layout with:
  - Playback buttons aligned near progress bar
  - Up-Next queue panel
  - Lyrics pop-up window
- Uses **Pillow** for image/album rendering.

### 💾 JSON Persistence
- User data saved automatically (playlists, play counts, lyrics cache).
- All features run **offline** once songs and cache exist.

---

## 🧠 Architecture Design

| Module | Responsibility |
|---------|----------------|
| `Song` | Represents individual track (metadata, duration). |
| `Player` | Handles playback using `pygame.mixer`. |
| `Playlist` | Stores a collection of songs and controls queue logic. |
| `MusicLibrary` | Scans local folders and manages songs. |
| `LyricsFetcher` | Handles API requests and caching. |
| `gui-pro.py` | Integrates everything into a modern GUI. |

Each component is modular and reusable, following **object-oriented principles** and **functional decomposition**.

---

## 🧰 Installation

### 1️⃣ Clone the repository
```bash
git clone https://github.com/<your-username>/Spotify-Lite.git
cd Spotify-Lite
```

### 2️⃣ Install dependencies
```
pip install -r requirements.txt
```

### 3️⃣ Run the program

**GUI mode:**

- python gui-1.0.py
- python gui-2.0.py
- python gui-pro.py

**CLI mode (lightweight):**

- python cli.py


---

### 🔑 Environment Setup

If using Genius API (recommended):

export GENIUS_API_TOKEN="your_api_key_here"

If unset, the program defaults to offline lyrics cache.

---

### 🧠 Example Use

$ python gui.py\
Welcome to Spotify Lite!
1. View Library
2. Create Playlist
3. Play Song
4. Fetch Lyrics
5. Exit

Or launch GUI for full experience:

---

### 🧑‍💻 Future Improvements
	•	🧠 Deep learning recommendations (TensorFlow Lite)\
	•	🌐 Cloud sync for playlists\
	•	🕶️ Responsive redesign with album art carousel

---

### 🏆 Achievement Highlights
	•	✅ Modular object-oriented structure (7+ files)\
	•	✅ External API integration (Genius API)\
	•	✅ JSON-based data persistence\
	•	✅ Modern, Spotify-inspired GUI\
	•	✅ Offline cache + error handling\
	•	✅ HD-level coding practices and documentation

---

### 🧾 Generative AI Acknowledgement

I used ChatGPT (GPT-5) to help generate docstrings, optimize Python syntax, design the GUI layout, and document this README.
All creative and logical decisions were reviewed, debugged, and implemented by me.

---

### 👤 Author

Lew Xu Wei\
Bachelor of Computer Science (Data Science)\
Monash University Malaysia\
📧 xlew0002@student.monash.edu\
📦 GitHub: xw675 / xw11200
