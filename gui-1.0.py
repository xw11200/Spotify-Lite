import os
import json
import pygame
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, Listbox, END, ttk

from library import MusicLibrary
from player import Player
from playlist import Playlist
from song import Song

DATA_PATH = os.path.join("data", "songs")
PLAYLISTS_FILE = os.path.join("data", "playlists.json")
LOGO_PATH = os.path.join("data", "assets", "logo2.png")
CONTROL_BG = "#1DB954"
CONTROL_FG = "#ffffff"
ACCENT_GREEN = "#1DB954"
CONTROL_HOVER = "#1ED760"
CONTROL_PRESS = "#17a74a"

# ---- macOS UI compatibility fix ----
import platform
if platform.system() == "Darwin":
    # Force Tk scaling for Retina displays
    from ctypes import cdll
    # Force buttons to use a custom ttk theme with visible colors
    from tkinter import ttk
    style = ttk.Style()
    style.theme_use('clam')  # avoids macOS Aqua theme overriding colors
    try:
        cdll.LoadLibrary('/System/Library/Frameworks/Tk.framework/Tk')
    except OSError:
        pass
    root = tk.Tk()
    root.tk.call('tk', 'scaling', 1.5)  # Adjust 1.5 → 2.0 if UI looks too small
    root.destroy()

def play_playlist_threaded(player: Player, playlist_songs: list[Song], update_label: callable) -> None:
    """
    Play a playlist in a separate thread.

    Args:
        player (Player): The music player instance.
        playlist_songs (list of Song): List of songs to play.
        update_label (function): Function to update the status label.
    """
    def run():
        """
        Play the songs in the playlist.
        """
        for song in playlist_songs:
            update_label(f"Playing: {song.title}")
            player.play(song)
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
        update_label("Playlist finished.")
    threading.Thread(target=run, daemon=True).start()

class IconButton(tk.Canvas):
    """
    Simple flat button drawn on a canvas so custom colours render reliably across platforms.
    
    Args:
        master: The parent tkinter widget.
        text (str): The button text.
        command (callable): The function to call when the button is clicked.
        bg (str): Background color.
        fg (str): Foreground (text) color.
        hover_bg (str): Background color on hover.
        press_bg (str): Background color on press.
        width (int): Button width.
        height (int): Button height.
        radius (int): Corner radius for rounded corners.
    """
    def __init__(self, master, text: str, command: callable,
                 bg: str = CONTROL_BG, fg: str = CONTROL_FG,
                 hover_bg: str = CONTROL_HOVER, press_bg: str = CONTROL_PRESS,
                 width: int = 62, height: int = 44, radius: int = 18):
        super().__init__(master, highlightthickness=0, bd=0, bg=master.cget("bg"))
        self._command = command
        self._bg = bg
        self._fg = fg
        self._hover_bg = hover_bg
        self._press_bg = press_bg
        self._radius = radius

        self.configure(width=width, height=height, cursor="hand2")
        self._shape_items = self._draw_round_rect(2, 2, width-2, height-2, radius, fill=bg)
        self._label = self.create_text(width / 2, height / 2, text=text,
                                       fill=fg, font=("Arial", 18, "bold"))

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _paint(self, colour: str) -> None:
        """
        Paint the button with the given color.

        Args:
            colour (str): The color to paint the button.
        """
        for item in self._shape_items:
            self.itemconfig(item, fill=colour)

    def _draw_round_rect(self, x1: int, y1: int, x2: int, y2: int, radius: int, **kwargs) -> list[int]:
        """
        Draw a rounded rectangle and return the created item IDs.
        
        Args:
            x1 (int): Top-left x coordinate.
            y1 (int): Top-left y coordinate.
            x2 (int): Bottom-right x coordinate.
            y2 (int): Bottom-right y coordinate.
            radius (int): Corner radius.
            **kwargs: Additional options for the shapes.
        """
        radius = min(radius, (x2 - x1) / 2, (y2 - y1) / 2)
        items = []
        items.append(self.create_rectangle(x1 + radius, y1, x2 - radius, y2, outline="", **kwargs))
        items.append(self.create_rectangle(x1, y1 + radius, x2, y2 - radius, outline="", **kwargs))
        items.append(self.create_arc(x1, y1, x1 + 2 * radius, y1 + 2 * radius,
                                     start=90, extent=90, style="pieslice", outline="", **kwargs))
        items.append(self.create_arc(x2 - 2 * radius, y1, x2, y1 + 2 * radius,
                                     start=0, extent=90, style="pieslice", outline="", **kwargs))
        items.append(self.create_arc(x2 - 2 * radius, y2 - 2 * radius, x2, y2,
                                     start=270, extent=90, style="pieslice", outline="", **kwargs))
        items.append(self.create_arc(x1, y2 - 2 * radius, x1 + 2 * radius, y2,
                                     start=180, extent=90, style="pieslice", outline="", **kwargs))
        return items

    def _on_enter(self, _event=None):
        """
        Handle mouse enter event.

        Args:
            _event (optional): Defaults to None.
        """
        self._paint(self._hover_bg)

    def _on_leave(self, _event=None):
        """
        Handle mouse leave event.

        Args:
            _event (optional): Defaults to None.
        """
        self._paint(self._bg)

    def _on_press(self, _event=None):
        """
        Handle mouse press event.

        Args:
            _event (optional): Defaults to None.
        """
        self._paint(self._press_bg)

    def _on_release(self, _event=None):
        """
        Handle mouse release event.

        Args:
            _event (optional): Defaults to None.
        """
        self._paint(self._hover_bg)
        if callable(self._command):
            self.after(1, self._command)


class SpotifyLiteApp:
    """
    A simplified Spotify-like music player application using Tkinter.
    
    Attributes:
        root: The root tkinter window.
        library: The music library.
        player: The music player.
        playlists: The dictionary of playlists.
        search_var: The search query variable.
        logo_image: The logo image for the application.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Spotify Lite")
        self.root.geometry("960x640")
        self.root.config(bg="#1e1e1e")
        self.current_mode = "library"  # "library" or "playlist"

        self.library = MusicLibrary()
        self.player = Player()
        self.playlists = {}
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_song_list)
        try:
            raw_image = tk.PhotoImage(master=self.root, file=LOGO_PATH)
            # Subsample to reduce the logo size (integer downscale)
            self.logo_image = raw_image.subsample(4, 4)
        except Exception:
            self.logo_image = None

        self.build_ui()
        self.load_library_data()
        self.load_playlists_from_file()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def build_ui(self):
        """
        Build the user interface.
        """
        if self.logo_image:
            tk.Label(self.root, image=self.logo_image, bg="#1e1e1e").pack(pady=10)
        else:
            tk.Label(self.root, text="Spotify Lite", fg="white", bg="#1e1e1e",
                     font=("Arial", 30, "bold")).pack(pady=10)

        # Main frame
        main_frame = tk.Frame(self.root, bg="#1e1e1e")
        main_frame.pack(fill="both", expand=True)

        # Left frame - Song List
        left_frame = tk.Frame(main_frame, bg="#1e1e1e")
        left_frame.pack(side="left", fill="both", expand=True, padx=(20, 10))

        # Search bar
        search_frame = tk.Frame(left_frame, bg="#1e1e1e")
        search_frame.pack(pady=5, fill="x")

        tk.Label(search_frame, text="Search:", fg="white", bg="#1e1e1e", font=("Arial", 12)).pack(side=tk.LEFT, padx=(5, 5))
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, width=50,
                                bg="#3b3b3b", fg="white", insertbackground="white", font=("Arial", 12))
        search_entry.pack(side=tk.LEFT, fill="x", expand=True)

        song_frame = tk.Frame(left_frame, bg="#1e1e1e")
        song_frame.pack(fill="both", expand=True, pady=5)

        self.song_list = Listbox(song_frame, bg="#2b2b2b", fg="white",
                                 selectmode=tk.SINGLE, font=("Arial", 14))  # Changed from 11 to 14
        self.song_list.pack(side=tk.LEFT, fill="both", expand=True)

        # Right frame - Playlists
        right_frame = tk.Frame(main_frame, bg="#222222", width=300)  # Increased width from 250 to 300
        right_frame.pack(side="right", fill="y")

        tk.Label(right_frame, text="Playlists", fg="white", bg="#222222",
                 font=("Arial", 18, "bold")).pack(pady=10)  # Changed from 14 to 18

        self.playlist_box = Listbox(right_frame, bg="#2b2b2b", fg="white",
                                    selectmode=tk.SINGLE, font=("Arial", 14))  # Changed from 11 to 14  
        self.playlist_box.pack(fill="y", padx=10, pady=5)
        self.playlist_box.bind("<<ListboxSelect>>", self.on_playlist_select)

        tk.Button(right_frame, text="Add/Edit", command=self.open_playlist_editor,
                  bg="#1DB954", fg="white").pack(pady=3)
        tk.Button(right_frame, text="Play Playlist", command=self.play_selected_playlist,
                  bg="#1DB954", fg="white").pack(pady=3)
        tk.Button(right_frame, text="Reload", command=self.load_playlists_from_file,
                  bg="#1DB954", fg="white").pack(pady=3)
        tk.Button(right_frame, text="Show All Songs", command=self.show_all_songs,
          bg="#1DB954", fg="white").pack(pady=3)
        tk.Button(right_frame, text="Delete Playlist", command=self.delete_selected_playlist,
            bg="#1DB954", fg="white").pack(pady=3)

        # Bottom frame - Controls
        bottom_frame = tk.Frame(self.root, bg="#1e1e1e")
        bottom_frame.pack(fill="x", pady=10)

        tk.Button(bottom_frame, text="Scan Library", command=self.load_library_data,
                  width=12, bg=ACCENT_GREEN, fg="white").pack(side="left", padx=10)

        control_frame = tk.Frame(bottom_frame, bg="#1e1e1e")
        control_frame.pack(side="left", padx=10)

        self._create_control_button(control_frame, "▶", self.play_selected)
        self._create_control_button(control_frame, "⏯", self.player.pause)
        self._create_control_button(control_frame, "⏹", self.player.stop)

        # Add progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(bottom_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=10)

        # Add time label
        self.time_label = tk.Label(bottom_frame, text="00:00 / 00:00", 
                                  fg="white", bg="#1e1e1e", font=("Arial", 12))
        self.time_label.pack(side="left", padx=5)

        self.status_label = tk.Label(self.root, text="Ready.", fg="white", bg="#1e1e1e",
                                        font=("Arial", 18, "bold"))
        self.status_label.pack(pady=5)

        self.update_progress_bar()

    # Backend Logic
    def load_library_data(self):
        """
        Load the music library from the specified folder.
        """
        self.library.load_from_folder(DATA_PATH)
        self.current_mode = "library"
        self.playlist_box.selection_clear(0, END)
        self.filter_song_list()
        self.status_label.config(text=f"Loaded {len(self.library.songs)} songs.")

    def filter_song_list(self, *args):
        """
        Filter the song list based on the search query.

        Args:
            *args: Additional arguments (not used).    
        """
        query = self.search_var.get().lower()
        self.song_list.delete(0, END)
        for song in self.library.songs:
            if query in song.title.lower() or query in song.artist.lower():
                self.song_list.insert(END, str(song))

    def play_selected(self):
        """
        Play the selected song from the list.
        """
        selection = self.song_list.curselection()
        if not selection:
            return
        song_str = self.song_list.get(selection[0])

        # Choose correct list source depending on mode
        if self.current_mode == "playlist":
            all_songs = []
            pl_selection = self.playlist_box.curselection()
            if pl_selection:
                pl_name = self.playlist_box.get(pl_selection[0])
                all_songs = self.playlists[pl_name].songs
        else:
            all_songs = self.library.songs

        song_to_play = next((s for s in all_songs if str(s) == song_str), None)
        if song_to_play:
            self.player.play(song_to_play)
            self.status_label.config(text=f"Playing: {song_to_play.title}")


    def update_progress_bar(self):
        """
        Update the progress bar and time label based on the current playback position.
        """
        if pygame.mixer.music.get_busy():
            try:
                if hasattr(self.player, 'current_song') and self.player.current_song:
                    pos = pygame.mixer.music.get_pos() / 1000.0  # Convert milliseconds to seconds
                    total = getattr(self.player.current_song, "length", 0)
                    
                    # Ensure pos and total are valid
                    if pos > 0 and total > 0:
                        progress = min((pos / total) * 100, 100)
                        self.progress_var.set(progress)
                        
                        # Format time as MM:SS
                        cur_m, cur_s = divmod(int(pos), 60)
                        tot_m, tot_s = divmod(int(total), 60)
                        time_text = f"{cur_m:02d}:{cur_s:02d} / {tot_m:02d}:{tot_s:02d}"
                        self.time_label.config(text=time_text)
                        
            except Exception as e:
                print(f"Progress bar error: {e}")  # Debug print
                self.progress_var.set(0)
                self.time_label.config(text="00:00 / 00:00")
        else:
            # Reset progress when not playing
            self.progress_var.set(0)
            self.time_label.config(text="00:00 / 00:00")

        # Update every 100ms for smoother display
        self.root.after(100, self.update_progress_bar)

    # --- Playlist Logic ---
    def load_playlists_from_file(self):
        """
        Load playlists from a JSON file.
        """
        self.playlists.clear()
        self.playlist_box.delete(0, END)
        try:
            with open(PLAYLISTS_FILE, "r") as f:
                data = json.load(f)
            for name, paths in data.items():
                pl = Playlist(name)
                for path in paths:
                    s = next((song for song in self.library.songs if song.file_path == path), None)
                    if s:
                        pl.add_song(s)
                self.playlists[name] = pl
                self.playlist_box.insert(END, name)
            self.status_label.config(text=f"Loaded {len(self.playlists)} playlists.")
        except FileNotFoundError:
            self.status_label.config(text="No playlists found.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load playlists: {e}")

    def save_all_playlists_to_file(self):
        """
        Save all playlists to a JSON file.
        """
        data = {name: [song.file_path for song in pl.songs] for name, pl in self.playlists.items()}
        os.makedirs(os.path.dirname(PLAYLISTS_FILE), exist_ok=True)
        with open(PLAYLISTS_FILE, "w") as f:
            json.dump(data, f, indent=4)

    def open_playlist_editor(self):
        """
        Open the playlist editor for creating or editing a playlist.
        """
        name = simpledialog.askstring("Playlist", "Enter playlist name:")
        if not name:
            return
        if name not in self.playlists:
            self.playlists[name] = Playlist(name)

        pl = self.playlists[name]
        pl_window = tk.Toplevel(self.root)
        pl_window.title(f"Editing Playlist: {name}")
        pl_window.geometry("500x400")
        pl_window.config(bg="#1e1e1e")

        listbox = Listbox(pl_window, bg="#2b2b2b", fg="white", selectmode=tk.EXTENDED)
        listbox.pack(fill="both", expand=True, padx=10, pady=10)
        for s in self.library.songs:
            listbox.insert(END, str(s))
            if s in pl.songs:
                listbox.select_set(END)

        def save():
            """
            Save the current playlist.
            """
            selected = [self.library.songs[i] for i in listbox.curselection()]
            pl.songs = selected
            self.save_all_playlists_to_file()
            self.load_playlists_from_file()
            pl_window.destroy()

        tk.Button(pl_window, text="Save", command=save, bg="#1DB954", fg="white").pack(pady=10)

    def on_playlist_select(self):
        """
        Handle playlist selection from the listbox.
        """
        selection = self.playlist_box.curselection()
        if not selection:
            return

        name = self.playlist_box.get(selection[0])
        pl = self.playlists[name]
        self.status_label.config(text=f"Viewing playlist: {name} ({len(pl.songs)} songs)")

        # Clear song list and show playlist contents
        self.song_list.delete(0, END)
        for s in pl.songs:
            self.song_list.insert(END, str(s))
        self.current_mode = "playlist"

    def play_selected_playlist(self):
        """
        Play the selected playlist.
        """
        selection = self.playlist_box.curselection()
        if not selection:
            messagebox.showinfo("Info", "Select a playlist first.")
            return
        name = self.playlist_box.get(selection[0])
        playlist = self.playlists.get(name)
        if not playlist or not playlist.songs:
            messagebox.showinfo("Info", "This playlist is empty.")
            return
        play_playlist_threaded(self.player, playlist.songs, self.update_status)

    def delete_selected_playlist(self):
        """
        Delete the selected playlist.
        """
        selection = self.playlist_box.curselection()
        if not selection:
            messagebox.showinfo("Info", "Select a playlist to delete.")
            return

        name = self.playlist_box.get(selection[0])
        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete playlist '{name}'?")
        if not confirm:
            return

        # Remove from dictionary
        if name in self.playlists:
            del self.playlists[name]

            # Save updates to file
            self.save_all_playlists_to_file()

            # Refresh playlist box
            self.load_playlists_from_file()
            self.status_label.config(text=f"Deleted playlist: {name}")
            messagebox.showinfo("Deleted", f"Playlist '{name}' was deleted.")
        else:
            messagebox.showwarning("Warning", f"Playlist '{name}' not found.")


    def show_all_songs(self):
        """
        Show all songs in the library.
        """
        self.filter_song_list()
        self.current_mode = "library"
        self.status_label.config(text="Viewing full library.")


    def update_status(self, text: str):
        """
        Update the status label with the given text.

        Args:
            text (str): The text to display.
        """
        self.status_label.config(text=text)

    def on_closing(self):
        """
        Handle application closing: stop playback and close the window.
        """
        self.player.stop()
        self.root.destroy()

    def _create_control_button(self, parent, text: str, command: callable) -> tk.Button:
        """
        Create a Spotify-style control button for playback controls.
        """
        btn = IconButton(parent, text=text, command=command,
                         bg=CONTROL_BG, fg=CONTROL_FG,
                         hover_bg=CONTROL_HOVER, press_bg=CONTROL_PRESS)
        btn.pack(side="left", padx=6)
        return btn

if __name__ == "__main__":
    root = tk.Tk()
    app = SpotifyLiteApp(root)
    root.mainloop()
