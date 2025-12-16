import os
import json
import pygame
import threading
import tkinter as tk
import tkinter.font as tkfont
from tkinter import messagebox, simpledialog, Listbox, END, ttk
import platform

from library import MusicLibrary
from player import Player
from playlist import Playlist
from song import Song

DATA_PATH = os.path.join("data", "songs")
PLAYLISTS_FILE = os.path.join("data", "playlists.json")
LOGO_PATH = os.path.join("data", "assets", "logo2.png")
CONTROL_BG = "#1DB954"
CONTROL_FG = "#1E1E1E"
ACCENT_GREEN = "#1DB954"
CONTROL_HOVER = "#1ED760"
CONTROL_PRESS = "#17a74a"

# ===== Rounded Spotify-green Button =====
class RoundedButton(tk.Canvas):
    """
    A rounded button with Spotify-like colors and hover/press effects.

    Args:
        tk (_type_): Parent tkinter widget.
        text (str): Button text.
        command (callable, optional): Function to call on click. Defaults to None.
        bg (str, optional): Background color. Defaults to "#1DB954".
        hover_bg (str, optional): Hover background color. Defaults to "#1ED760".
        press_bg (str, optional): Pressed background color. Defaults to "#17a74a".
        fg (str, optional): Text color. Defaults to "white".
        font (tuple, optional): Font settings. Defaults to ("Arial", 12, "bold").
        radius (int, optional): Corner radius. Defaults to 12.
        padx (int, optional): Horizontal padding. Defaults to 16.
        pady (int, optional): Vertical padding. Defaults to 8.
        draw_button (bool, optional): Whether to draw the button immediately. Defaults to True.
    """
    def __init__(self, master, text, command=None,
                 bg="#1DB954", hover_bg="#1ED760", press_bg="#17a74a",
                 fg="#1E1E1E", font=("Arial", 12, "bold"),
                 radius=12, padx=16, pady=8, draw_button=True, **kwargs):
        super().__init__(master, highlightthickness=0, borderwidth=0,
                         bg=master.cget("bg"), **kwargs)
        self._text = text
        self._command = command
        self._bg = bg
        self._hover_bg = hover_bg
        self._press_bg = press_bg
        self._fg = fg
        self._font = font
        self._radius = radius
        self._padx = padx
        self._pady = pady
        self._disabled = False
        self._draw_button()

    def _draw_button(self):
        """
        Draw the button on the canvas.
        """
        font_id = tkfont.Font(font=self._font)
        tw, th = font_id.measure(self._text), font_id.metrics("linespace")
        w, h = tw + self._padx * 2, th + self._pady * 2
        self.configure(width=w, height=h, cursor="hand2")

        r = self._radius
        # draw main rounded rect
        self._shape_tag = "button_shape"
        self._draw_round_rect(0, 0, w, h, r, fill=self._bg, tag=self._shape_tag)
        self._label_tag = self.create_text(w / 2, h / 2, text=self._text,
                                           fill=self._fg, font=self._font, tags="button_text")
        for tag in (self._shape_tag, "button_text"):
            self.tag_bind(tag, "<Enter>", self._on_enter)
            self.tag_bind(tag, "<Leave>", self._on_leave)
            self.tag_bind(tag, "<ButtonPress-1>", self._on_press)
            self.tag_bind(tag, "<ButtonRelease-1>", self._on_release)

    def _draw_round_rect(self, x1, y1, x2, y2, r, **kwargs):
        """
        Draw a rounded rectangle on the canvas.

        Args:
            x1 (int): The x-coordinate of the top-left corner.
            y1 (int): The y-coordinate of the top-left corner.
            x2 (int): The x-coordinate of the bottom-right corner.
            y2 (int): The y-coordinate of the bottom-right corner.
            r (int): The corner radius.

        Returns:
            items (list): A list of canvas items representing the rounded rectangle.
        """
        r = min(r, (x2 - x1) / 2, (y2 - y1) / 2)
        items = []
        items.append(self.create_rectangle(x1 + r, y1, x2 - r, y2, outline="", **kwargs))
        items.append(self.create_rectangle(x1, y1 + r, x2, y2 - r, outline="", **kwargs))
        items.append(self.create_arc(x1, y1, x1 + 2 * r, y1 + 2 * r, start=90, extent=90, style="pieslice", outline="", **kwargs))
        items.append(self.create_arc(x2 - 2 * r, y1, x2, y1 + 2 * r, start=0, extent=90, style="pieslice", outline="", **kwargs))
        items.append(self.create_arc(x2 - 2 * r, y2 - 2 * r, x2, y2, start=270, extent=90, style="pieslice", outline="", **kwargs))
        items.append(self.create_arc(x1, y2 - 2 * r, x1 + 2 * r, y2, start=180, extent=90, style="pieslice", outline="", **kwargs))
        return items

    def _paint(self, color):
        """
        Paint the button with the given color.

        Args:
            color (str): The color to paint the button.
        """
        for item in self.find_withtag(self._shape_tag):
            self.itemconfig(item, fill=color)

    def _on_enter(self, _=None):
        """
        Handle mouse enter event.

        Args:
            _ (type, optional): Description. Defaults to None.
        """
        if not self._disabled:
            self._paint(self._hover_bg)

    def _on_leave(self, _=None):
        """
        Handle mouse leave event.

        Args:
            _ (type, optional): Description. Defaults to None.
        """
        if not self._disabled:
            self._paint(self._bg)

    def _on_press(self, _=None):
        """
        Handle mouse press event.

        Args:
            _ (type, optional): Description. Defaults to None.
        """
        if not self._disabled:
            self._paint(self._press_bg)

    def _on_release(self, _=None):
        """
        Handle mouse release event.

        Args:
            _ (type, optional): Description. Defaults to None.
        """
        if not self._disabled:
            self._paint(self._hover_bg)
            if callable(self._command):
                self.after(1, self._command)

    def configure_state(self, state: str):
        """
        Configure the button state (normal/disabled).

        Args:
            state (str): The state to configure the button.
        """
        if state == "disabled":
            self._disabled = True
            self._paint("#4a4a4a")
            self.itemconfig(self._label_tag, fill="gray")
            self.configure(cursor="")
        else:
            self._disabled = False
            self._paint(self._bg)
            self.itemconfig(self._label_tag, fill=self._fg)
            self.configure(cursor="hand2")


class IconButton(tk.Canvas):
    """
    Simple flat icon button drawn on a canvas so colours show correctly on macOS.
    
    Args:
        master: Parent tkinter widget.
        text (str): Button text (icon).
        command (callable): Function to call on click.
        bg (str, optional): Background color. Defaults to CONTROL_BG.
        fg (str, optional): Text color. Defaults to CONTROL_FG.
        hover_bg (str, optional): Hover background color. Defaults to CONTROL_HOVER.
        press_bg (str, optional): Pressed background color. Defaults to CONTROL_PRESS.
        width (int, optional): Button width. Defaults to 62.
        height (int, optional): Button height. Defaults to 44.
        radius (int, optional): Corner radius. Defaults to 18.
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

        self._shape_items = self._draw_round_rect(2, 2, width - 2, height - 2, radius, fill=bg)
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
        Draw a rounded rectangle on the canvas.

        Args:
            x1 (int): The x-coordinate of the top-left corner.
            y1 (int): The y-coordinate of the top-left corner.
            x2 (int): The x-coordinate of the bottom-right corner.
            y2 (int): The y-coordinate of the bottom-right corner.
            radius (int): The radius of the corners.

        Returns:
            list[int]: The IDs of the created canvas items.
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

    def _on_enter(self, _=None):
        """
        Handle mouse enter event.

        Args:
            _ (optional): Defaults to None.
        """
        self._paint(self._hover_bg)

    def _on_leave(self, _=None):
        """
        Handle mouse leave event.

        Args:
            _ (optional): Defaults to None.
        """
        self._paint(self._bg)

    def _on_press(self, _=None):
        """
        Handle mouse press event.

        Args:
            _ (optional): Defaults to None.
        """
        self._paint(self._press_bg)

    def _on_release(self, _=None):
        """
        Handle mouse release event.

        Args:
            _ (optional): Defaults to None.
        """
        self._paint(self._hover_bg)
        if callable(self._command):
            self.after(1, self._command)


# ===== Threaded Playlist Playback =====
def play_playlist_threaded(player: Player, playlist_songs: list[Song], update_label: callable) -> None:
    """
    Play a playlist in a separate thread to keep the UI responsive.

    Args:
        player (Player): The music player instance.
        playlist_songs (list[Song]): The list of songs in the playlist.
        update_label (callable): A function to update the UI label with the current song.
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


# ===== Main Application =====
class SpotifyLiteApp:
    """
    Main application class for Spotify Lite.
    
    Args:
        root: The root tkinter window.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Spotify Lite")
        self.root.geometry("960x640")
        self.root.config(bg="#1e1e1e")
        self.current_mode = "library"

        self.library = MusicLibrary()
        self.player = Player()
        self.playlists = {}
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_song_list)

        self._last_position = 0
        try:
            raw_image = tk.PhotoImage(file=LOGO_PATH)
            self.logo_image = raw_image.subsample(12, 12)
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

        main_frame = tk.Frame(self.root, bg="#1e1e1e")
        main_frame.pack(fill="both", expand=True)

        # Left frame (Songs)
        left_frame = tk.Frame(main_frame, bg="#1e1e1e")
        left_frame.pack(side="left", fill="both", expand=True, padx=(20, 10))

        search_frame = tk.Frame(left_frame, bg="#1e1e1e")
        search_frame.pack(pady=5, fill="x")

        tk.Label(search_frame, text="Search:", fg="white", bg="#1e1e1e",
                 font=("Arial", 12)).pack(side=tk.LEFT, padx=(5, 5))
        tk.Entry(search_frame, textvariable=self.search_var, width=50,
                 bg="#3b3b3b", fg="white", insertbackground="white",
                 font=("Arial", 12)).pack(side=tk.LEFT, fill="x", expand=True)

        song_frame = tk.Frame(left_frame, bg="#1e1e1e")
        song_frame.pack(fill="both", expand=True, pady=5)
        self.song_list = Listbox(song_frame, bg="#2b2b2b", fg="white",
                                 selectmode=tk.SINGLE, font=("Arial", 14))
        self.song_list.pack(side=tk.LEFT, fill="both", expand=True)

        # Right frame (Playlists)
        right_frame = tk.Frame(main_frame, bg="#222222", width=300)
        right_frame.pack(side="right", fill="y")

        tk.Label(right_frame, text="Playlists", fg="white", bg="#222222",
                 font=("Arial", 18, "bold")).pack(pady=10)

        self.playlist_box = Listbox(right_frame, bg="#2b2b2b", fg="white",
                                    selectmode=tk.SINGLE, font=("Arial", 14))
        self.playlist_box.pack(fill="y", padx=10, pady=5)
        self.playlist_box.bind("<<ListboxSelect>>", self.on_playlist_select)

        # Buttons
        RoundedButton(right_frame, text="Add/Edit", command=self.open_playlist_editor).pack(pady=3)
        RoundedButton(right_frame, text="Play Playlist", command=self.play_selected_playlist).pack(pady=3)
        RoundedButton(right_frame, text="Reload", command=self.load_playlists_from_file).pack(pady=3)
        RoundedButton(right_frame, text="Show All Songs", command=self.show_all_songs).pack(pady=3)
        RoundedButton(right_frame, text="Delete Playlist", command=self.delete_selected_playlist).pack(pady=3)

        # Bottom controls
        bottom_frame = tk.Frame(self.root, bg="#1e1e1e")
        bottom_frame.pack(fill="x", pady=10)

        RoundedButton(bottom_frame, text="Scan Library", command=self.load_library_data).pack(side="left", padx=10)

        control_frame = tk.Frame(bottom_frame, bg="#1e1e1e")
        control_frame.pack(side="left", padx=10)
        self._create_control_button(control_frame, "▶", self.play_selected)
        self._create_control_button(control_frame, "⏯", self.player.pause)
        self._create_control_button(control_frame, "⏹", self.player.stop)

        # Progress bar and time label
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(bottom_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=10)
        self.time_label = tk.Label(bottom_frame, text="00:00 / 00:00",
                                   fg="white", bg="#1e1e1e", font=("Arial", 12))
        self.time_label.pack(side="left", padx=5)
        self.status_label = tk.Label(self.root, text="Ready.", fg="white",
                                     bg="#1e1e1e", font=("Arial", 18, "bold"))
        self.status_label.pack(pady=5)

        self.update_progress_bar()

    # ==== Logic ====
    def load_library_data(self):
        """
        Load music library data from the specified folder.
        """
        self.library.load_from_folder(DATA_PATH)
        self.current_mode = "library"
        self.playlist_box.selection_clear(0, END)
        self.filter_song_list()
        self.status_label.config(text=f"Loaded {len(self.library.songs)} songs.")

    def filter_song_list(self, *args):
        """
        Filter the song list based on the search query.
        """
        query = self.search_var.get().lower()
        self.song_list.delete(0, END)
        for song in self.library.songs:
            if query in song.title.lower() or query in song.artist.lower():
                self.song_list.insert(END, str(song))

    def play_selected(self):
        """
        Play the selected song from the song list.
        """
        selection = self.song_list.curselection()
        if not selection:
            return
        song_str = self.song_list.get(selection[0])
        all_songs = (self.playlists[self.playlist_box.get(self.playlist_box.curselection()[0])].songs
                     if self.current_mode == "playlist" and self.playlist_box.curselection()
                     else self.library.songs)
        song_to_play = next((s for s in all_songs if str(s) == song_str), None)
        if song_to_play:
            self.player.play(song_to_play)
            self.status_label.config(text=f"Playing: {song_to_play.title}")

    def update_progress_bar(self):
        """
        Update the progress bar and time label based on the current playback position.
        """
        if pygame.mixer.music.get_busy() and hasattr(self.player, 'current_song') and self.player.current_song:
            pos = pygame.mixer.music.get_pos() / 1000.0
            self._last_position = pos
            total = getattr(self.player.current_song, "length", 0)
            if total > 0:
                self.progress_var.set(min((pos / total) * 100, 100))
                cur_m, cur_s = divmod(int(pos), 60)
                tot_m, tot_s = divmod(int(total), 60)
                self.time_label.config(text=f"{cur_m:02d}:{cur_s:02d} / {tot_m:02d}:{tot_s:02d}")
        elif hasattr(self.player, 'paused') and self.player.paused:
            # If paused, keep showing last position
            total = getattr(self.player.current_song, "length", 0) if hasattr(self.player, 'current_song') else 0
            pos = self._last_position
            if total > 0:
                self.progress_var.set(min((pos / total) * 100, 100))
                cur_m, cur_s = divmod(int(pos), 60)
                tot_m, tot_s = divmod(int(total), 60)
                self.time_label.config(text=f"{cur_m:02d}:{cur_s:02d} / {tot_m:02d}:{tot_s:02d}")
        else:
            self._last_position = 0
            self.progress_var.set(0)
            self.time_label.config(text="00:00 / 00:00")
        self.root.after(100, self.update_progress_bar)

    # ==== Playlist Logic ====
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
                    song = next((s for s in self.library.songs if s.file_path == path), None)
                    if song:
                        pl.add_song(song)
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
        data = {n: [s.file_path for s in pl.songs] for n, pl in self.playlists.items()}
        os.makedirs(os.path.dirname(PLAYLISTS_FILE), exist_ok=True)
        with open(PLAYLISTS_FILE, "w") as f:
            json.dump(data, f, indent=4)

    def open_playlist_editor(self):
        """
        Open the playlist editor window.
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
            Save the edited playlist.
            """
            pl.songs = [self.library.songs[i] for i in listbox.curselection()]
            self.save_all_playlists_to_file()
            self.load_playlists_from_file()
            pl_window.destroy()

        RoundedButton(pl_window, text="Save", command=save).pack(pady=10)

    def on_playlist_select(self, *_):
        """
        Handle playlist selection from the listbox.
        """
        sel = self.playlist_box.curselection()
        if not sel:
            return
        name = self.playlist_box.get(sel[0])
        pl = self.playlists[name]
        self.status_label.config(text=f"Viewing playlist: {name} ({len(pl.songs)} songs)")
        self.song_list.delete(0, END)
        for s in pl.songs:
            self.song_list.insert(END, str(s))
        self.current_mode = "playlist"

    def play_selected_playlist(self):
        """
        Play the selected playlist.
        """
        sel = self.playlist_box.curselection()
        if not sel:
            messagebox.showinfo("Info", "Select a playlist first.")
            return
        name = self.playlist_box.get(sel[0])
        pl = self.playlists.get(name)
        if not pl or not pl.songs:
            messagebox.showinfo("Info", "This playlist is empty.")
            return
        play_playlist_threaded(self.player, pl.songs, self.update_status)

    def delete_selected_playlist(self):
        """
        Delete the selected playlist.
        """
        sel = self.playlist_box.curselection()
        if not sel:
            messagebox.showinfo("Info", "Select a playlist to delete.")
            return
        name = self.playlist_box.get(sel[0])
        if messagebox.askyesno("Confirm Delete", f"Delete playlist '{name}'?"):
            if name in self.playlists:
                del self.playlists[name]
                self.save_all_playlists_to_file()
                self.load_playlists_from_file()
                self.status_label.config(text=f"Deleted playlist: {name}")

    def show_all_songs(self):
        """
        Show all songs in the library.
        """
        self.filter_song_list()
        self.current_mode = "library"
        self.status_label.config(text="Viewing full library.")

    def update_status(self, text):
        """
        Update the status label with the current playback status.

        Args:
            text (str): The status text to display.
        """
        self.status_label.config(text=text)

    def on_closing(self):
        """
        Handle the window closing event.
        """
        self.player.stop()
        self.root.destroy()

    def _create_control_button(self, parent, text: str, command: callable) -> tk.Button:
        """
        Create a Spotify-style flat control button.
        """
        btn = IconButton(parent, text=text, command=command,
                         bg=CONTROL_BG, fg=CONTROL_FG,
                         hover_bg=CONTROL_HOVER, press_bg=CONTROL_PRESS)
        btn.pack(side="left", padx=6)
        return btn


# ==== Entry Point ====
if __name__ == "__main__":
    root = tk.Tk()
    if platform.system() == "Darwin":
        root.tk.call('tk', 'scaling', 1.5)
    app = SpotifyLiteApp(root)
    root.mainloop()
