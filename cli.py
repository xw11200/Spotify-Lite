import os
import json
import time
import pygame
from library import MusicLibrary
from player import Player
from playlist import Playlist
import threading
from song import Song

DATA_PATH = os.path.join("data", "songs")
PLAYLISTS_FILE = os.path.join("data", "playlists.json")

# ========== Helper Functions ==========
def save_all_playlists(playlists: dict[str, Playlist]) -> None:
    """
    Saves the entire playlists dictionary to playlists.json
    Args:
        playlists (dict[str, Playlist]): Dictionary of playlist name to Playlist object.
    """
    data = {name: [s.file_path for s in pl.songs] for name, pl in playlists.items()}
    os.makedirs(os.path.dirname(PLAYLISTS_FILE), exist_ok=True)
    with open(PLAYLISTS_FILE, "w") as f:
        json.dump(data, f, indent=4)
    print(f"Saved {len(playlists)} playlists.")

def load_all_playlists(library: MusicLibrary) -> dict[str, Playlist]:
    """
    Loads all playlists from playlists.json

    Args:
        library (MusicLibrary): The music library to reference for Song objects.

    Returns:
        dict[str, Playlist]: Dictionary of playlist name to Playlist object.
    """
    playlists = {}
    try:
        with open(PLAYLISTS_FILE, "r") as f:
            data = json.load(f)
        for name, paths in data.items():
            pl = Playlist(name)
            for p in paths:
                s = next((song for song in library.songs if song.file_path == p), None)
                if s:
                    pl.add_song(s)
            playlists[name] = pl
        print(f"Loaded {len(playlists)} playlists.")
    except FileNotFoundError:
        print("No saved playlists found.")
    return playlists

def select_song(library: MusicLibrary) -> Song | None:
    """
    Prompts the user to select a song from the library.

    Args:
        library (MusicLibrary): The music library to select from.

    Returns:
        Song | None: The selected Song object or None if selection was invalid.
    """
    library.display_songs()
    try:
        idx = int(input("Enter song number: ")) - 1
        return library.songs[idx]
    except:
        print("Invalid selection.")
        return None

def select_playlist(playlists: dict[str, Playlist]) -> Playlist | None:
    """
    Prompts the user to select a playlist.

    Args:
        playlists (dict[str, Playlist]): Dictionary of playlist name to Playlist object.
    
    Returns:
        Playlist | None: The selected Playlist object or None if selection was invalid.
    """
    if not playlists:
        print("No playlists available.")
        return None
    names = list(playlists.keys())
    for i, n in enumerate(names, 1):
        print(f"{i}. {n} ({len(playlists[n].songs)} songs)")
    try:
        idx = int(input("Select playlist number: ")) - 1
        return playlists[names[idx]]
    except:
        print("Invalid selection.")
        return None

def edit_playlist(playlists: dict[str, Playlist], library: MusicLibrary) -> None:
    """
    Allows the user to create or edit a playlist.

    Args:
        playlists (dict[str, Playlist]): Dictionary of playlist name to Playlist object.
        library (MusicLibrary): The music library to select songs from.
    """
    name = input("Enter playlist name: ").strip()
    if not name:
        return
    if name not in playlists:
        playlists[name] = Playlist(name)
    pl = playlists[name]

    selected = {s.file_path for s in pl.songs}

    while True:
        print(f"\nEditing playlist: {name}")
        for i, song in enumerate(library.songs, 1):
            mark = "[X]" if song.file_path in selected else "[ ]"
            print(f"{mark} {i}. {song}")
        print("s = save, q = cancel")

        choice = input("> ").lower()
        if choice == 's':
            pl.songs = [s for s in library.songs if s.file_path in selected]
            playlists[name] = pl
            save_all_playlists(playlists)
            print(f"Playlist '{name}' saved.")
            return
        elif choice == 'q':
            return
        else:
            try:
                idx = int(choice) - 1
                song = library.songs[idx]
                if song.file_path in selected:
                    selected.remove(song.file_path)
                else:
                    selected.add(song.file_path)
            except:
                print("Invalid input.")

# --- Helper ---
def play_playlist_threaded(player: Player, playlist: Playlist) -> None:
    """
    Plays the given playlist in a separate thread.

    Args:
        player (Player): The music player instance.
        playlist (Playlist): The playlist to play.
    """
    def run():
        """
        Plays songs in the playlist sequentially.
        """
        for song in playlist.songs:
            player.play(song)
            print(f"Now playing: {song.title}")
            while pygame.mixer.music.get_busy():
                time.sleep(0.5)
        print(f"Playlist '{playlist.name}' finished.")
    threading.Thread(target=run, daemon=True).start()


# ========== Main Program ==========
def main():
    library = MusicLibrary()
    player = Player()

    print("Loading songs...")
    library.load_from_folder(DATA_PATH)
    playlists = load_all_playlists(library)

    while True:
        print("\n===== Spotify Lite (CLI Edition) =====")
        print("1. Search Library")
        print("2. Play Song")
        print("3. Pause / Resume")
        print("4. Stop")
        print("5. Volume Control")
        print("6. View Playlists")
        print("7. Edit / Create Playlist")
        print("8. Play Playlist")
        print("9. Reload Library")
        print("0. Quit")

        choice = input("Select option: ")

        if choice == '1':
            query = input("Search term: ").lower()
            for s in library.songs:
                if query in s.title.lower() or query in s.artist.lower():
                    print(s)
        elif choice == '2':
            song = select_song(library)
            if song:
                player.play(song)
        elif choice == '3':
            player.pause()
        elif choice == '4':
            player.stop()
        elif choice == '5':
            try:
                level = float(input("Enter volume (0.0 - 1.0): "))
                player.set_volume(level)
            except:
                print("Invalid volume.")
        elif choice == '6':
            if not playlists:
                print("No playlists found.")
            else:
                for n, pl in playlists.items():
                    print(f"{n}: {len(pl.songs)} songs")
        elif choice == '7':
            edit_playlist(playlists, library)
        elif choice == '8':
            pl = select_playlist(playlists)
            if pl and pl.songs:
                play_playlist_threaded(player, pl)

        elif choice == '9':
            library.load_from_folder(DATA_PATH)
            playlists = load_all_playlists(library)
        elif choice == '0':
            save_all_playlists(playlists)
            player.stop()
            print("Goodbye!")
            break
        else:
            print("Invalid option.")

if __name__ == "__main__":
    main()
