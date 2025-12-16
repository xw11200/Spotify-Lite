import io
import os
import time
import threading
import tkinter as tk
from tkinter import messagebox
from importlib import util as importlib_util

import customtkinter as ctk
from PIL import Image
from mutagen import File as MutagenFile

from library import MusicLibrary
from player import Player
from playlist import Playlist
from song import Song

DATA_PATH = os.path.join("data", "songs")
PLAYLISTS_FILE = os.path.join("data", "playlists.json")
DEFAULT_COVER = os.path.join("data", "default_cover.png")
LOGO_PATH = os.path.join("data", "assets", "logo2.png")

SPOTIFY_FONT_FAMILY = "Helvetica Neue"
FONT_SECTION = (SPOTIFY_FONT_FAMILY, 16, "bold")
FONT_BODY = (SPOTIFY_FONT_FAMILY, 13)
FONT_BODY_BOLD = (SPOTIFY_FONT_FAMILY, 14, "bold")
FONT_LYRICS = (SPOTIFY_FONT_FAMILY, 13)
FONT_TITLE = (SPOTIFY_FONT_FAMILY, 34, "bold")
FONT_ARTIST = (SPOTIFY_FONT_FAMILY, 22)
FONT_TIME = (SPOTIFY_FONT_FAMILY, 14)
FONT_STATUS = (SPOTIFY_FONT_FAMILY, 14)
FONT_BUTTON = (SPOTIFY_FONT_FAMILY, 14, "bold")
FONT_MINI_TITLE = (SPOTIFY_FONT_FAMILY, 14, "bold")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LYRICS_MODULE_PATH = os.path.join(BASE_DIR, "lyrics-fetcher.py")

def _load_lyrics_fetcher() -> callable:
    """
    Dynamically load the lyrics-fetcher module if available.

    Returns:
        Callable[[str, str], str]: Function to fetch lyrics given artist and title.
    """
    try:
        spec = importlib_util.spec_from_file_location("lyrics_fetcher", LYRICS_MODULE_PATH)
        if spec and spec.loader:
            module = importlib_util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module.get_lyrics
    except Exception:
        pass
    return lambda _artist, _title: "Lyrics unavailable (lyrics module not available)."

get_lyrics = _load_lyrics_fetcher()

# ========== Helper ==========
def find_cover_for(file_path: str) -> str:
    """
    Return plausible album-cover image path for a given audio file.

    Args:
        file_path (str): Path to the audio file.

    Returns:
        str: Path to the cover image if found, else default cover or None.
    """
    base, _ = os.path.splitext(file_path)
    for ext in (".jpg", ".png", ".jpeg", ".webp"):
        candidate = base + ext
        if os.path.exists(candidate):
            return candidate
    if os.path.exists(DEFAULT_COVER):
        return DEFAULT_COVER
    return None


# ========== App ==========
class CTkSpotifyLite(ctk.CTk):
    """
    Main application class for the Spotify Lite player.
    
    Attributes:
        library (MusicLibrary): The music library.
        player (Player): The audio player.
        playlists (dict[str, Playlist]): The user's playlists.
        current_song (Song | None): The currently playing song.
        queue (list[Song]): The playback queue.
    """
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        self.title("Spotify Lite")
        self.geometry("1100x700")
        self.minsize(960, 640)

        # Core state
        self.library = MusicLibrary()
        self.player = Player()
        self.playlists: dict[str, Playlist] = {}
        self.current_song: Song | None = None
        self.queue: list[Song] = []
        self._lyrics_request_token = None
        self._progress_job = None
        self._t_play_started = None
        self._t_paused_start = None
        self._paused_cumulative = 0.0
        self._is_paused = False
        self._mini = None

        # Build UI
        self._build_layout()
        self._bind_window_events()
        self._set_lyrics_text("Select a song to view lyrics.")

        # Load data automatically
        self._load_library()
        self._load_playlists()

    # ------------------------------------------------
    def _build_layout(self):
        """
        Build the layout of the main application window.
        """
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, corner_radius=8)
        self.sidebar.grid(row=0, column=0, sticky="nsw", padx=16, pady=16)
        self.sidebar.grid_propagate(False)
        self.sidebar.configure(width=380)

        self.search_var = tk.StringVar()
        self.search_entry = ctk.CTkEntry(
            self.sidebar,
            textvariable=self.search_var,
            placeholder_text="Search songs or artists…",
        )
        self.search_entry.configure(placeholder_text_color="#7a7a7a", font=FONT_BODY)
        self.search_entry.grid(row=0, column=0, padx=12, pady=(12, 8), sticky="ew")
        self.search_entry.bind("<KeyRelease>", lambda e: self._refresh_library_list())

        self.library_list = tk.Listbox(
            self.sidebar,
            height=18,
            bg="#121212",
            fg="#eaeaea",
            selectbackground="#1DB954",
            highlightthickness=0,
            activestyle="none",
            font=FONT_BODY,
        )
        self.library_list.grid(row=1, column=0, padx=12, pady=(0, 8), sticky="nsew")
        self.library_list.bind("<Double-Button-1>", self._play_selected_from_library)
        self.sidebar.grid_rowconfigure(1, weight=1)

        # Playlist controls
        pl_controls = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        pl_controls.grid(row=2, column=0, padx=12, pady=(8, 12), sticky="ew")
        pl_controls.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.btn_new_pl = self._hover_button(pl_controls, "+ New", self._new_playlist, width=100)
        self.btn_new_pl.grid(row=0, column=0, padx=4, pady=4, sticky="ew")

        self.btn_edit_pl = self._hover_button(
            pl_controls, "Edit", self._edit_playlist, width=100
        )
        self.btn_edit_pl.grid(row=0, column=1, padx=4, pady=4, sticky="ew")

        self.btn_delete_pl = self._hover_button(
            pl_controls, "Delete", self._delete_playlist, width=100
        )
        self.btn_delete_pl.grid(row=0, column=2, padx=4, pady=4, sticky="ew")

        ctk.CTkLabel(
            self.sidebar, text="Playlists", font=FONT_SECTION, text_color="#b3b3b3"
        ).grid(row=3, column=0, padx=12, pady=(8, 4), sticky="w")

        self.playlist_list = tk.Listbox(
            self.sidebar,
            height=10,
            bg="#121212",
            fg="#eaeaea",
            selectbackground="#1DB954",
            highlightthickness=0,
            activestyle="none",
            font=FONT_BODY,
        )
        self.playlist_list.grid(row=4, column=0, padx=12, pady=(0, 12), sticky="nsew")
        self.playlist_list.bind("<<ListboxSelect>>", self._on_playlist_selected)
        self.sidebar.grid_rowconfigure(4, weight=0)

        # Main panel
        self.main = ctk.CTkFrame(self, corner_radius=20)
        self.main.grid(row=0, column=1, sticky="nsew", padx=(0, 16), pady=16)
        self.main.grid_rowconfigure(0, weight=1)
        self.main.grid_columnconfigure((0, 1), weight=1)

        # Album art + lyrics column
        self.left_column = ctk.CTkFrame(self.main, fg_color="transparent")
        self.left_column.grid(row=0, column=0, padx=20, pady=20, sticky="nsw")
        self.left_column.grid_columnconfigure(0, weight=1)

        self.cover_label = ctk.CTkLabel(
            self.left_column,
            text="No cover",
            width=360,
            height=360,
            corner_radius=0,
            fg_color="#1a1a1a"
        )
        self.cover_label.grid(row=0, column=0, sticky="n")

        self.lyrics_frame = ctk.CTkFrame(self.left_column, fg_color="transparent")
        self.lyrics_frame.grid(row=1, column=0, sticky="nsew", pady=(16, 0))
        self.left_column.grid_rowconfigure(1, weight=1)

        self.lyrics_title = ctk.CTkLabel(self.lyrics_frame, text="Lyrics", font=FONT_SECTION)
        self.lyrics_title.pack(anchor="w")
        self.lyrics_text = ctk.CTkTextbox(self.lyrics_frame, width=360, height=200, font=FONT_LYRICS)
        self.lyrics_text.pack(fill="both", expand=True, pady=(4, 0))
        self.lyrics_text.configure(state="disabled")

        # Info section
        info = ctk.CTkFrame(self.main, fg_color="transparent")
        info.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        info.grid_rowconfigure(2, weight=1)
        info.grid_columnconfigure(0, weight=1)
        info.grid_columnconfigure(1, weight=0)

        self.logo_image = None
        logo_file = os.path.join(BASE_DIR, LOGO_PATH)
        if os.path.exists(logo_file):
            try:
                logo_pil = Image.open(logo_file)
                self.logo_image = ctk.CTkImage(dark_image=logo_pil, light_image=logo_pil, size=(120, 48))
            except Exception:
                self.logo_image = None

        title_row = ctk.CTkFrame(info, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="ew")
        title_row.grid_columnconfigure(0, weight=1)

        self.lbl_title = ctk.CTkLabel(title_row, text="Nothing playing", font=FONT_TITLE)
        self.lbl_title.grid(row=0, column=0, sticky="w")
        if self.logo_image:
            self.logo_label = ctk.CTkLabel(title_row, text="", image=self.logo_image)
            self.logo_label.grid(row=0, column=1, sticky="e", padx=(12, 0))

        self.lbl_artist = ctk.CTkLabel(info, text="—", font=FONT_ARTIST)
        self.lbl_artist.grid(row=1, column=0, sticky="w", pady=(2, 8))

        # Playback area
        playback_section = ctk.CTkFrame(info, fg_color="transparent")
        playback_section.grid(row=2, column=0, sticky="sew", pady=(16, 0))
        playback_section.grid_columnconfigure(0, weight=1)

        # Playback buttons
        controls_frame = ctk.CTkFrame(playback_section, fg_color="transparent")
        controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        controls_frame.grid_columnconfigure(0, weight=1)

        inner_controls = ctk.CTkFrame(controls_frame, fg_color="transparent")
        inner_controls.pack(fill="x", expand=True, padx=(60, 60))
        inner_controls.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        self.btn_prev = self._hover_button(inner_controls, "⏮", self._prev_track, width=80)
        self.btn_play = self._hover_button(inner_controls, "▶", self._toggle_play, width=80)
        self.btn_pause = self._hover_button(inner_controls, "⏸", self._pause, width=80)
        self.btn_stop = self._hover_button(inner_controls, "⏹", self._stop, width=80)
        self.btn_next = self._hover_button(inner_controls, "⏭", self._next_track, width=80)

        for i, btn in enumerate(
            [self.btn_prev, self.btn_play, self.btn_pause, self.btn_stop, self.btn_next]
        ):
            btn.grid(row=0, column=i, padx=5, pady=(0, 0), sticky="ew")

        # Progress bar row
        prog_row = ctk.CTkFrame(playback_section, fg_color="transparent")
        prog_row.grid(row=1, column=0, sticky="ew", pady=(6, 10))
        prog_row.grid_columnconfigure(1, weight=1)

        self.time_start = ctk.CTkLabel(prog_row, text="00:00", font=FONT_TIME, width=55)
        self.time_start.grid(row=0, column=0, padx=(0, 6))
        self.progress = ctk.CTkProgressBar(prog_row, height=10, progress_color="#1DB954")
        self.progress.grid(row=0, column=1, sticky="ew")
        self.progress.set(0.0)
        self.time_end = ctk.CTkLabel(prog_row, text="00:00", font=FONT_TIME, width=55)
        self.time_end.grid(row=0, column=2, padx=(6, 0))

        # Mini Player button
        self.btn_mini = self._hover_button(
            playback_section, "Mini Player", self._open_miniplayer, width=120
        )
        self.btn_mini.grid(row=2, column=0, sticky="w", pady=(8, 10))

        # Up Next section
        ctk.CTkLabel(
            playback_section, text="Up Next", font=FONT_SECTION, text_color="#b3b3b3"
        ).grid(row=3, column=0, sticky="w", pady=(6, 4))

        self.queue_box = tk.Listbox(
            playback_section,
            height=14,  # ← Taller! (was 8)
            bg="#121212",
            fg="#eaeaea",
            selectbackground="#1DB954",
            highlightthickness=0,
            activestyle="none",
            font=FONT_BODY,
        )
        self.queue_box.grid(row=4, column=0, sticky="nsew", pady=(0, 4))
        self.queue_box.bind("<Double-Button-1>", self._jump_queue)

        # Status
        self.status = ctk.CTkLabel(self, text="Ready", anchor="w", font=FONT_STATUS)
        self.status.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 16))

    # ------------------------------------------------
    def _hover_button(self, master, text, command, width: int = 0) -> ctk.CTkButton:
        """
        Create a button with hover effect.

        Args:
            master: The parent widget.
            text (str): The button text.
            command: The function to call on click.
            width (int): The button width.

        Returns:
            ctk.CTkButton: The created button.
        """
        btn = ctk.CTkButton(master, text=text, command=command, corner_radius=12, width=width, font=FONT_BUTTON)
        normal = "#1DB954"
        hover = "#1ED760"
        btn.configure(fg_color=normal)

        def on_enter(_): btn.configure(fg_color=hover) # Change button color on hover
        def on_leave(_): btn.configure(fg_color=normal) # Change button color back on leave

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        return btn

    # ------------------------------------------------
    def _load_library(self):
        """
        Load the music library from the specified folder.
        """
        os.makedirs(DATA_PATH, exist_ok=True)
        self.library.load_from_folder(DATA_PATH)
        self._refresh_library_list()

    def _load_playlists(self):
        """
        Load playlists from the JSON file.
        """
        import json
        if os.path.exists(PLAYLISTS_FILE):
            with open(PLAYLISTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for name, paths in data.items():
                pl = Playlist(name)
                for p in paths:
                    s = self._song_from_path(p)
                    if s:
                        pl.add_song(s)
                self.playlists[name] = pl
        self._refresh_playlist_list()

    def _save_all_playlists(self):
        """
        Persist playlists to JSON file.
        """
        import json
        data = {name: [song.file_path for song in pl.songs] for name, pl in self.playlists.items()}
        os.makedirs(os.path.dirname(PLAYLISTS_FILE), exist_ok=True)
        with open(PLAYLISTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    # --------------------------- Sidebar interactions ---------------------------
    def _refresh_library_list(self):
        """
        Refresh the library list based on the current search query.
        """
        query = self.search_var.get().strip().lower()
        self.library_list.delete(0, tk.END)
        ordered = sorted(self.library.songs, key=lambda x: (x.artist, x.title))
        filtered = []
        for s in ordered:
            label = f"{s.title} — {s.artist}"
            if not query or query in label.lower():
                self.library_list.insert(tk.END, label)
                self.library_list.itemconfig(tk.END, {'fg': '#eaeaea'})
                filtered.append(s)
        self._lib_index_map = filtered

    def _refresh_playlist_list(self):
        """
        Refresh the playlist list in the sidebar.
        """
        self.playlist_list.delete(0, tk.END)
        for name in sorted(self.playlists.keys()):
            self.playlist_list.insert(tk.END, name)

    def _on_playlist_selected(self, _e=None):
        """
        Handle the event when a playlist is selected.

        Args:
            event: The Tkinter event object.
            _e: Unused parameter, included for event compatibility.
        """
        sel = self.playlist_list.curselection()
        if not sel:
            return
        name = self.playlist_list.get(sel[0])
        pl = self.playlists.get(name)
        self._set_queue(pl.songs if pl else [])

    def _new_playlist(self):
        """
        Create a new playlist.
        """
        name = ctk.CTkInputDialog(text="Playlist name:", title="New Playlist").get_input()
        if not name:
            return
        if name in self.playlists:
            messagebox.showinfo("Playlist", "Name already exists.")
            return
        self.playlists[name] = Playlist(name)
        self._refresh_playlist_list()
        self._save_all_playlists()
        self.status.configure(text=f"Created playlist ‘{name}’. Add songs by double‑clicking in Library.")

    def _rename_playlist(self):
        """
        Rename an existing playlist.
        """
        sel = self.playlist_list.curselection()
        if not sel:
            return
        old = self.playlist_list.get(sel[0])
        new = ctk.CTkInputDialog(text="New name:", title="Rename Playlist").get_input()
        if not new or new == old:
            return
        if new in self.playlists:
            messagebox.showinfo("Playlist", "Name already exists.")
            return
        self.playlists[new] = self.playlists.pop(old)
        self.playlists[new].name = new
        self._refresh_playlist_list()
        self._save_all_playlists()

    def _delete_playlist(self):
        """
        Delete the selected playlist.
        """
        sel = self.playlist_list.curselection()
        if not sel:
            return
        name = self.playlist_list.get(sel[0])
        if messagebox.askyesno("Delete Playlist", f"Delete ‘{name}’?"):
            self.playlists.pop(name, None)
            self._refresh_playlist_list()
            self._save_all_playlists()

    def _edit_playlist(self):
        """
        Open an editor to add or remove songs from the selected playlist.
        """
        sel = self.playlist_list.curselection()
        if not sel:
            messagebox.showinfo("Playlist", "Select a playlist to edit.")
            return

        playlist_name = self.playlist_list.get(sel[0])
        playlist = self.playlists.get(playlist_name)
        if not playlist:
            messagebox.showerror("Playlist", "Playlist not found.")
            return

        editor = ctk.CTkToplevel(self)
        editor.title(f"Edit Playlist: {playlist_name}")
        editor.geometry("520x560")
        editor.grab_set()

        ctk.CTkLabel(editor, text="Select songs to include:", font=FONT_SECTION).pack(anchor="w", padx=16, pady=(16, 8))

        listbox_frame = ctk.CTkFrame(editor, fg_color="transparent")
        listbox_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        song_listbox = tk.Listbox(
            listbox_frame,
            selectmode=tk.MULTIPLE,
            bg="#121212",
            fg="#eaeaea",
            selectbackground="#1DB954",
            activestyle="none",
            highlightthickness=0,
            font=FONT_BODY,
        )
        song_listbox.pack(fill="both", expand=True, side="left")

        scrollbar = tk.Scrollbar(listbox_frame, orient="vertical", command=song_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        song_listbox.config(yscrollcommand=scrollbar.set)

        ordered_songs = sorted(self.library.songs, key=lambda x: (x.artist, x.title))
        selection_map = []
        playlist_set = set(playlist.songs)
        for idx, song in enumerate(ordered_songs):
            song_listbox.insert(tk.END, f"{song.title} — {song.artist}")
            selection_map.append(song)
            if song in playlist_set:
                song_listbox.selection_set(idx)

        def save_changes():
            """
            Save changes made to the playlist.
            """
            indices = song_listbox.curselection()
            playlist.songs = [selection_map[i] for i in indices]
            self._save_all_playlists()
            self._refresh_playlist_list()
            # If currently viewing this playlist, refresh queue display
            current_sel = self.playlist_list.curselection()
            if current_sel and self.playlist_list.get(current_sel[0]) == playlist_name:
                self._set_queue(playlist.songs)
            self.status.configure(text=f"Updated playlist ‘{playlist_name}’.")
            editor.destroy()

        def close_editor():
            """
            Close the playlist editor.
            """
            editor.destroy()

        button_frame = ctk.CTkFrame(editor, fg_color="transparent")
        button_frame.pack(fill="x", padx=16, pady=(0, 16))
        self._hover_button(button_frame, "Save", save_changes, width=120).pack(side="left", padx=(0, 8))
        self._hover_button(button_frame, "Cancel", close_editor, width=120).pack(side="left")

    # --------------------------- Queue & playback ---------------------------
    def _set_queue(self, songs: list[Song]):
        """
        Set the playback queue to the specified list of songs.'

        Args:
            songs (list[Song]): List of songs to set as the queue.
        """
        self.queue = list(songs)
        self.queue_box.delete(0, tk.END)
        for s in self.queue:
            self.queue_box.insert(tk.END, f"{s.title} — {s.artist}")

    def _pop_next_from_queue(self) -> Song | None:
        """
        Pop the next song from the queue and keep UI in sync.
        
        Returns:
            Song | None: The next song or None if the queue is empty.
        """
        if not self.queue:
            return None
        song = self.queue.pop(0)
        if self.queue_box.size() > 0:
            self.queue_box.delete(0)
        return song

    def _song_from_path(self, path: str) -> Song | None:
        """
        Find a song in the library by its file path.

        Args:
            path (str): The file path of the song.

        Returns:
            Song | None: The found song or None if not found.
        """
        return next((s for s in self.library.songs if getattr(s, "file_path", None) == path), None)

    def _enqueue_from_library(self, s: Song):
        """
        Add a song from the library to the playback queue.

        Args:
            s (Song): The song to enqueue.
        """
        self.queue.append(s)
        self.queue_box.insert(tk.END, f"{s.title} — {s.artist}")

    def _play_selected_from_library(self, _e=None):
        """
        Play the selected song from the library.

        Args:
            event: The Tkinter event object.
        """
        sel = self.library_list.curselection()
        if not sel:
            return
        s = self._lib_index_map[sel[0]]
        # double-click: play immediately
        self._play_song(s)

    def _jump_queue(self, _e=None):
        """
        Jump to the selected song in the queue.

        Args:
            event: The Tkinter event object.
        """
        sel = self.queue_box.curselection()
        if not sel:
            return
        s = self.queue[sel[0]]
        # Move selected to the front and play it
        self.queue.pop(sel[0])
        self.queue.insert(0, s)
        song = self._pop_next_from_queue()
        if song:
            self._play_song(song)

    def _next_track(self):
        """
        Advance to the next track in the queue.
        """
        song = self._pop_next_from_queue()
        if song:
            self._play_song(song)
        else:
            self._stop()

    def _prev_track(self):
        """
        Go back to the previous track (replay current).
        """
        # naive: just restart current
        if self.current_song:
            self._play_song(self.current_song)

    def _toggle_play(self):
        """
        Toggle playback state.
        """
        if self.current_song and self._is_paused:
            self._resume()
        elif self.current_song:
            self._pause()
        else:
            # nothing yet; if queue has items, play first
            song = self._pop_next_from_queue()
            if song:
                self._play_song(song)

    # --------------------------- Player state machine ---------------------------
    def _play_song(self, song: Song):
        """
        Play the specified song.

        Args:
            song (Song): The song to play.
        """
        try:
            self.player.play(song)
        except Exception as e:
            messagebox.showerror("Playback", f"Failed to play: {e}")
            return

        self.current_song = song
        self._is_paused = False
        self._paused_cumulative = 0.0
        self._t_paused_start = None
        self._t_play_started = time.monotonic()

        self._update_now_playing(song)
        self._start_lyrics_fetch(song)
        self._start_progress_loop()
        self.status.configure(text=f"Playing: {song.title} — {song.artist}")

    def _pause(self):
        """
        Pause playback.
        """
        if not self._is_paused:
            try:
                self.player.pause()
            except Exception:
                return
            self._is_paused = True
            self._t_paused_start = time.monotonic()
            self.status.configure(text="Paused")

    def _resume(self):
        """
        Resume playback.
        """
        if self._is_paused and self._t_paused_start is not None:
            try:
                self.player.pause()  # toggles resume in Player.pause
            except Exception:
                return
            self._paused_cumulative += time.monotonic() - self._t_paused_start
            self._t_paused_start = None
            self._is_paused = False
            self.status.configure(text="Playing…")

    def _stop(self):
        """
        Stop playback.
        """
        try:
            self.player.stop()
        except Exception:
            pass
        self._is_paused = False
        self._t_play_started = None
        self._paused_cumulative = 0.0
        self.progress.set(0.0)
        self.time_start.configure(text="00:00")
        self.status.configure(text="Stopped")

    # --------------------------- Animated progress ---------------------------
    def _start_progress_loop(self):
        """
        Start the progress loop for the currently playing song.
        """
        if self._progress_job is not None:
            self.after_cancel(self._progress_job)
        self._tick_progress()

    def _tick_progress(self):
        """
        Update the progress bar and time labels.
        """
        # Update every 200ms; keep time during pause (do not reset to 00:00)
        if not self.current_song:
            return
        total = getattr(self.current_song, 'length', 0) or getattr(self.current_song, 'duration', 0) or 0
        if total <= 0:
            total = 1
        elapsed = 0.0
        if self._t_play_started is not None:
            base = time.monotonic() - self._t_play_started
            paused = self._paused_cumulative + ((time.monotonic() - self._t_paused_start) if (self._is_paused and self._t_paused_start) else 0.0)
            elapsed = max(0.0, base - paused)
        # clamp and roll-over
        if elapsed >= total - 0.05:
            self.progress.set(1.0)
            self.time_start.configure(text=self._fmt(total))
            self.time_end.configure(text=self._fmt(total))
            self._progress_job = self.after(300, self._on_track_end)
            return
        self.progress.set(elapsed / total)
        self.time_start.configure(text=self._fmt(elapsed))
        self.time_end.configure(text=self._fmt(total))
        self._progress_job = self.after(200, self._tick_progress)

    def _on_track_end(self):
        """
        Handle the end of the current track.
        """
        # Auto-advance
        self._next_track()

    # Static method to format time
    @staticmethod
    def _fmt(seconds: float) -> str:
        """
        Format the given time in seconds to a string "MM:SS".

        Args:
            seconds (float): Time in seconds.

        Returns:
            str: Formatted time string.
        """
        seconds = int(seconds)
        m, s = divmod(seconds, 60)
        return f"{m:02d}:{s:02d}"

    def _update_now_playing(self, song: Song):
        """
        Update the UI to reflect the currently playing song.

        Args:
            song (Song): The currently playing song.
        """
        # metadata
        self.lbl_title.configure(text=song.title)
        self.lbl_artist.configure(text=song.artist)
        cover_img = self._load_cover_image(song)
        self._apply_cover_image(cover_img)

    def _load_cover_image(self, song: Song) -> Image.Image | None:
        """
        Load the cover image for the given song.

        Args:
            song (Song): The song for which to load the cover image.

        Returns:
            Image.Image | None: The cover image, or None if not found.
        """
        if not song or not getattr(song, "file_path", None):
            return self._load_default_cover()

        path = find_cover_for(song.file_path)
        if path and os.path.exists(path):
            try:
                return Image.open(path).convert("RGBA")
            except Exception:
                pass

        try:
            audio = MutagenFile(song.file_path)
            if not audio:
                raise ValueError("Unsupported format")

            artwork_data = None
            tags = getattr(audio, "tags", None)
            if tags:
                # ID3 (MP3)
                for key in tags.keys():
                    if key.startswith("APIC"):
                        artwork_data = tags[key].data
                        break
                # MP4/M4A
                if not artwork_data:
                    covr = tags.get("covr")
                    if covr:
                        artwork_data = covr[0]
            # FLAC/others
            if not artwork_data and hasattr(audio, "pictures") and audio.pictures:
                artwork_data = audio.pictures[0].data

            if artwork_data:
                return Image.open(io.BytesIO(artwork_data)).convert("RGBA")
        except Exception:
            pass

        return self._load_default_cover()

    def _load_default_cover(self) -> Image.Image | None:
        """
        Load the default cover image.

        Returns:
            Image.Image | None: The default cover image, or None if not found.
        """
        if os.path.exists(DEFAULT_COVER):
            try:
                return Image.open(DEFAULT_COVER).convert("RGBA")
            except Exception:
                return None
        return None

    def _apply_cover_image(self, image: Image.Image | None) -> None:
        """
        Apply the cover image to the GUI.

        Args:
            image (Image.Image | None): The PIL Image to display as cover.
        """
        if image is None:
            self.cover_label.configure(text="No cover", image=None)
            self.cover_label.image = None
            self._cover_image = None
            return

        size = 360
        img = image.copy()
        img_ratio = img.width / img.height if img.height else 1
        if img_ratio >= 1:
            new_width = size
            new_height = int(size / img_ratio)
        else:
            new_height = size
            new_width = int(size * img_ratio)
        img = img.resize((max(1, new_width), max(1, new_height)), Image.Resampling.LANCZOS)

        canvas = Image.new("RGBA", (size, size), (26, 26, 26, 255))
        offset = ((size - img.width) // 2, (size - img.height) // 2)
        canvas.paste(img, offset, img if img.mode == "RGBA" else None)

        self._cover_image = ctk.CTkImage(light_image=canvas, dark_image=canvas, size=(size, size))
        self.cover_label.configure(image=self._cover_image, text="")
        self.cover_label.image = self._cover_image

    def _set_lyrics_text(self, text: str) -> None:
        """
        Set the lyrics text in the GUI.

        Args:
            text (str): The lyrics text to display.
        """
        display = text.strip() if text else "No lyrics available."
        if "lyrics unavailable" in display.lower():
            self.lyrics_title.configure(text="Lyrics (setup required)")
        else:
            self.lyrics_title.configure(text="Lyrics")
        self.lyrics_text.configure(state="normal")
        self.lyrics_text.delete("1.0", tk.END)
        self.lyrics_text.insert(tk.END, display)
        self.lyrics_text.configure(state="disabled")
        self.lyrics_text.yview("1.0")

    def _start_lyrics_fetch(self, song: Song) -> None:
        """
        Start fetching lyrics for the given song in a background thread.
        
        Args:
            song (Song): The song for which to fetch lyrics.
        """
        if not callable(get_lyrics):
            self._set_lyrics_text("Lyrics module not available.")
            return
        token = getattr(song, "file_path", None) or f"{song.artist}-{song.title}"
        self._lyrics_request_token = token
        self._set_lyrics_text("Loading lyrics…")
        threading.Thread(target=self._fetch_lyrics_worker, args=(song, token), daemon=True).start()

    def _fetch_lyrics_worker(self, song: Song, token: str) -> None:
        """
        Worker thread to fetch lyrics.

        Args:
            song (Song): The song for which to fetch lyrics.
            token (str): The request token to validate the result.
        """
        try:
            lyrics = get_lyrics(song.artist, song.title)
        except Exception as exc:
            lyrics = f"Lyrics unavailable ({exc})"
        self.after(0, lambda: self._apply_lyrics_result(token, lyrics))

    def _apply_lyrics_result(self, token: str, lyrics: str) -> None:
        """
        Apply the result of the lyrics fetch.

        Args:
            token (str): The request token to validate the result.
            lyrics (str): The fetched lyrics.
        """
        if token != self._lyrics_request_token:
            return
        self._set_lyrics_text(lyrics)

    # --------------------------- Mini‑player --------------------------- 
    def _open_miniplayer(self):
        """
        Open the mini-player window.
        """
        if self._mini and tk.Toplevel.winfo_exists(self._mini):
            self._mini.deiconify()
            self._mini.lift()
            return
        self._mini = MiniPlayer(self)

    def _bind_window_events(self):
        """
        Bind window events for the main application.
        """
        # When window is minimized, pop the mini-player
        self.bind("<Unmap>", self._maybe_open_mini_on_minimize)

    def _maybe_open_mini_on_minimize(self, event=None):
        """
        Open mini-player when main window is minimized.

        Args:
            event: The Tkinter event object.
        """
        # If iconified (minimized), open mini-player
        if str(self.state()) == 'iconic':
            self._open_miniplayer()

# ------------------------------ Mini Player ------------------------------
class MiniPlayer(tk.Toplevel):
    """
    Mini Player window for controlling playback.

    Args:
        app (CTkSpotifyLite): The main application instance.
    """
    def __init__(self, app: CTkSpotifyLite):
        super().__init__(app)
        self.app = app
        self.overrideredirect(False)
        self.title("Mini Player")
        self.attributes('-topmost', True)
        self.geometry("360x120+80+80")
        self.configure(bg="#0f0f0f")

        frm = ctk.CTkFrame(self, corner_radius=16)
        frm.pack(fill="both", expand=True, padx=8, pady=8)

        top = ctk.CTkFrame(frm, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=(8,4))
        self.lbl = ctk.CTkLabel(top, text="—", font=FONT_MINI_TITLE)
        self.lbl.pack(side="left")

        ctrl = ctk.CTkFrame(frm, fg_color="transparent")
        ctrl.pack(fill="x", padx=8, pady=(4,8))
        self.btn_prev = ctk.CTkButton(ctrl, text="⏮", width=60, command=app._prev_track, font=FONT_BUTTON, fg_color="#1DB954")
        self.btn_play = ctk.CTkButton(ctrl, text="▶", width=60, command=app._toggle_play, font=FONT_BUTTON, fg_color="#1DB954")
        self.btn_pause = ctk.CTkButton(ctrl, text="⏸", width=60, command=app._pause, font=FONT_BUTTON, fg_color="#1DB954")
        self.btn_next = ctk.CTkButton(ctrl, text="⏭", width=60, command=app._next_track, font=FONT_BUTTON, fg_color="#1DB954")
        for b in (self.btn_prev, self.btn_play, self.btn_pause, self.btn_next):
            b.pack(side="left", padx=4)

        self.prog = ctk.CTkProgressBar(frm)
        self.prog.pack(fill="x", padx=12, pady=(4,10))

        # timer
        self._job = None
        self._tick()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _tick(self):
        """
        Update mini-player display.
        """
        s = self.app.current_song
        if s:
            self.lbl.configure(text=f"{s.title} — {s.artist}")
            total = getattr(s, 'length', 0) or getattr(s, 'duration', 0) or 0
            total = total if total > 0 else 1
            # Borrow app's computed elapsed by reformatting labels
            # Safer: recompute quickly
            elapsed = 0.0
            if self.app._t_play_started is not None:
                base = time.monotonic() - self.app._t_play_started
                paused = self.app._paused_cumulative + ((time.monotonic() - self.app._t_paused_start) if (self.app._is_paused and self.app._t_paused_start) else 0.0)
                elapsed = max(0.0, base - paused)
            self.prog.set(min(1.0, elapsed/total))
        else:
            self.lbl.configure(text="—")
            self.prog.set(0.0)
        self._job = self.after(250, self._tick)

    def _on_close(self):
        """
        Update mini-player display.
        """
        if self._job:
            self.after_cancel(self._job)
        self.destroy()

# ========================= Entry =========================
if __name__ == "__main__":
    # Allow running as a drop-in replacement for the existing GUI.
    app = CTkSpotifyLite()
    app.mainloop()
