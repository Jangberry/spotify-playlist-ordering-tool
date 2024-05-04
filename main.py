#!/usr/bin/python3

import spotipy
from spotipy.cache_handler import CacheFileHandler
from spotipy.oauth2 import SpotifyOAuth
import json

SCOPES = ['playlist-read-private', 'playlist-modify-public', 'playlist-modify-private', 'playlist-read-collaborative', 'ugc-image-upload']
ACTIONS = ['nop','shuffle', 'sort-popularity', 'sort-alphabetical'] + [f"sort-audio-feature-{x}" for x in ['acousticness', 'danceability', 'duration_ms', 'energy', 'instrumentalness', 'key', 'liveness', 'loudness', 'mode', 'speechiness', 'tempo', 'time_signature', 'valence']]

class SpotifyPlaylistMod():
    def __init__(self, confPath = "config.json", no_browser = False) -> None:
        self.spotify = self.getSpotify(confPath, no_browser)    
    
    def getSpotify(self, path = "config.json", no_browser = False) -> spotipy.Spotify:
        with open(path) as f:
            conf = json.load(f)

        authMNG = SpotifyOAuth(
                client_id=conf["Client ID"],
                client_secret=conf["Client secret"],
                redirect_uri=conf["Redirect URI"] if "Redirect URI" in conf.keys() else "http://localhost:8888",
                scope=SCOPES,
                open_browser=not no_browser
            )

        return spotipy.Spotify(
            auth_manager=authMNG
        )
        
    def askForPlaylist(self):
        results = self.spotify.current_user_playlists()
        if results is None:
            print("It looks like you don't have any playlists")
            exit(1)
        
        print("Fetching your playlists", end='')
        playlists = results['items']
        while results['next']: # type: ignore
            results = self.spotify.current_user_playlists(offset=results['offset'] + results['limit'], limit=results['limit']) # type: ignore
            playlists += results['items'] # type: ignore

        ownID = self.spotify.me()['id'] # type: ignore
        playlists = [x for x in playlists if x['owner']['id'] == ownID or x['collaborative']]

        print("\033[2K\rYour playlists:")
        for i in range(len(playlists)):
            if playlists[i]['collaborative']:
                print(i+1, f"\033[31mCollaborative: {playlists[i]['name']}\033[0m", sep='\t')
            else:
                print(i+1, playlists[i]['name'], sep='\t')
        print("0\tCancel")

        while True:
            try:
                i = int(input(f"Choose a playlist [0 - {len(playlists)}] : "))
                if i == 0:
                    exit()
                elif i > len(playlists):
                    print('You don\'t have that much playlists')
                    continue
                self.playlist=playlists[i - 1]
            except ValueError or IndexError:
                continue
            return self.playlist['id']
        
    def getPlaylist(self, id):
        self.playlist = self.spotify.playlist(id)
        if self.playlist is None:
            raise Exception()
        
        print("Fetching the playlist tracks...", end='')
        results = self.spotify.playlist_tracks(self.playlist['id'], fields='next, offset, limit, items.track(href, uri, type, popularity, name)')
        self.playlist['tracks'] = results['items'] # type: ignore
        while results['next']: # type: ignore
            results = self.spotify.playlist_tracks(self.playlist['id'], fields='next, offset, limit, items.track(href, uri, type, popularity, name)', offset=results['offset'] + results['limit']) # type: ignore
            self.playlist['tracks'] += results['items'] # type: ignore

        self.playlist['tracks'] = [x['track'] for x in self.playlist['tracks']]
        print("\033[2K\rPlaylist fetched")
    
    def apply(self, mod, asc = True):
        if mod not in ACTIONS:
            raise Exception()
        if mod == "nop":
            # Get the list of tracks with the shape it would have if we were to commit it
            self.playlist['tracks'] = [x['uri'] for x in self.playlist['tracks']]
            return
        if mod == "shuffle":
            return self.__shuffle()
        if mod == "sort-popularity":
            return self.__popularity(asc)
        if mod == "sort-alphabetical":
            return self.__alphabetical(asc)
        if mod.startswith("sort-audio-feature-"):
            self.__getAudioFeatures()
            mod = mod[len("sort-audio-feature-"):]
            return self.__audioFeatures(mod, asc)
        
    def __audioFeatures(self, mod, asc = True):
        if self.playlist is None:
            raise Exception()
        
        self.playlist['tracks'] = sorted(self.playlist['tracks'],
                                         key=lambda x: x['audio_features'][mod] if x['audio_features'] is not None else 0, 
                                         reverse=not asc)
        print(f"Playlist sorted by {mod} locally. Applying to Spotify...")
        
        self.__commit()
            
    def __shuffle(self):
        if self.playlist is None:
            raise Exception()
        
        from random import shuffle
        shuffle(self.playlist['tracks'])
        print("Playlist shuffled locally. Applying to Spotify...")
        
        self.__commit()
        
    def __popularity(self, asc = True):
        if self.playlist is None:
            raise Exception()
        
        self.playlist['tracks'] = sorted(self.playlist['tracks'], key=lambda x: x['popularity'], reverse=not asc)
        print("Playlist sorted by popularity locally. Applying to Spotify...")
        
        self.__commit()
    
    def __alphabetical(self, asc = True):
        if self.playlist is None:
            raise Exception()
        
        self.playlist['tracks'] = sorted(self.playlist['tracks'], key=lambda x: x['name'], reverse=not asc)
        print("Playlist sorted alphabetically locally. Applying to Spotify...")
        
        self.__commit()
    
    def __getAudioFeatures(self):
        if self.playlist is None:
            raise Exception()
        
        print("Getting audio features from Spotify...", end='')
        for i in range(0, len(self.playlist['tracks']), 100):
            result = self.spotify.audio_features([x['uri'] for x in self.playlist['tracks'][i:i+100]])
            for j in range(len(result)): # type: ignore
                self.playlist['tracks'][i+j]['audio_features'] = result[j] # type: ignore
        print("\033[2K\rAudio features fetched")
    
    def __commit(self):
        if self.playlist is None:
            raise Exception()
        
        # Get the list of tracks with the awaited shape
        self.playlist['tracks'] = [x['uri'] for x in self.playlist['tracks']]
        
        for i in range(0, len(self.playlist['tracks']), 100):
            print(f"\033[2K\rUpdating the playlist {i+1}/{len(self.playlist['tracks'])}", end='')
            # Remove the original
            res = self.spotify.playlist_remove_all_occurrences_of_items(self.playlist['id'], self.playlist['tracks'][i:i+100], self.playlist['snapshot_id'])
            
            # Append shuffled to the playlist
            res = self.spotify.playlist_add_items(self.playlist['id'], self.playlist['tracks'][i:i+100])
        print("\033[2K\rOnline playlist updated")
    
def createTimer(playlist, mod, order, confPath, img = False):
    from subprocess import call, check_output
    from os import path
    from shlex import quote
    
    job = input("Would you like to set up a systemd timer to apply this to the playlist periodically ? [y/N]")
    if job.lower() != 'y':
        return
    
    print('Please provide the interval using systemd.timer syntax (https://www.freedesktop.org/software/systemd/man/latest/systemd.time.html#Calendar%20Events)')
    while True:
        interval = input("How often do you want to apply it ?")
        if call(["systemd-analyze", "calendar", interval]) == 0:
            break
        print("Invalid interval")
    
    description = f"{mod.capitalize()} the Spotify playlist {playlist['name']}"
    cmd = f"/usr/bin/python3 {quote(path.realpath(__file__))} --playlist {quote(playlist['id'])} --playlist-modification {quote(mod)} --playlist-sort-order {quote(order)} --conf {quote(confPath)} {'--image' if img else ''}"
    
    print(f"""
Creating the user service spotify-playlist-mod-{playlist['id']}.service to apply {mod} on {playlist['name']} {"and generate a new cover image " if img else ""}every {interval}.
To see the logs, use 'journalctl --user -u spotify-playlist-mod-{playlist['id']}.service'.
To disable it, use 'systemctl --user disable spotify-playlist-mod-{playlist['id']}.timer'

> cmdline will be: {cmd}""")
 
    if input("Is that correct ? [Y/n]").lower() not in ['y', 'yes', '']:
        print("Aborting")
        return
    
    print("Finding the user systemd directory...", end='')
    dirs = check_output(["systemd-analyze", "--user", "unit-paths"]).decode().split('\n')
    if len(dirs) == 0:
        print("\033[2K\rCouldn't find the user systemd directory, output will be in the current directory and not activated")
        dirs = path.realpath(".")
    elif len(dirs) == 1:
        print("\033[2K\rUser systemd directory is", dirs[0])
    else:
        if path.expanduser("~/.config/systemd/user") in dirs:
            print("\033[2K\rUser systemd directory is", path.expanduser("~/.config/systemd/user"))
            dirs = path.expanduser("~/.config/systemd/user")
        else:
            dirs = dirs[0]
            print("\033[2K\rMultiple directories found, using the first one:", dirs)

    print("Creating the timer and service...", end='')
    timer = f"""[Unit]
Description={description}

[Timer]
OnCalendar={interval}
Persistent=true
"""

    service = f"""[Unit]
Description={description}
After=network-online.target
Wants=network-online.target

[Service]
WorkingDirectory={path.dirname(path.realpath(__file__))}
ExecStart={cmd}
"""
    
    with open(path.join(dirs, f"spotify-playlist-mod-{playlist['id']}.timer"), 'w') as f:
        f.write(timer)
    with open(path.join(dirs, f"spotify-playlist-mod-{playlist['id']}.service"), 'w') as f:
        f.write(service)
    
    if call(["systemd-analyze", "verify", path.join(dirs, f"spotify-playlist-mod-{playlist['id']}.timer")]) != 0 or call(["systemd-analyze", "verify", path.join(dirs, f"spotify-playlist-mod-{playlist['id']}.service")]) != 0:
        print("\033[2K\rCouldn't validate the files. They are in", dirs, "but aren't activated, and are probably not functional.")
        return
    
    if path.realpath(dirs) == path.realpath("."):
        print("\033[2K\rDone ! The files are in the current directory and not activated, but validated.")
        return
    
    print("\033[2K\rEnabling the timer...", end='')
    
    call(["systemctl", "--user", "start", f"spotify-playlist-mod-{playlist['id']}.timer"])
    
    print("\033[2K\rDone !")

def generateImage(playlist):
    import randimage as ri
    import random
    import numpy as np
    import matplotlib.image as MPimg
    from io import BytesIO
    import base64
    
    seed = ''.join(playlist['tracks'])
    random.seed(seed)
    np.random.seed(sum([ord(x) for x in seed]))
    
    img_size = (256, 256)
    
    mask = ri.SaltPepperMask(img_size).get_mask()
    path = ri.ProbabilisticPath(mask).get_path()
    img = ri.ColoredPath(path, mask.shape).get_colored_path('Spectral')
    
    bio = BytesIO()
    MPimg.imsave(bio, img)
    bio.seek(0)
    
    return base64.b64encode(bio.read())

if __name__ == "__main__":
    import argparse
    args = argparse.ArgumentParser()
    args.description = 'Spotify playlist modifier. Default behavior is to ask for a playlist to modify and set a cron job to shuffle it periodically.'
    args.add_argument('--conf', help='Path to the configuration file', default='config.json')
    args.add_argument('--playlist', help='Playlist to modify', type=str, default=None)
    args.add_argument('--playlist-modification', help='Modification to apply to the playlist', default=None, choices=ACTIONS)
    args.add_argument('--playlist-sort-order', help='Order of the playlist after modification', default='asc', choices=['asc', 'desc'])
    args.add_argument('--interactive', help='Start the interactive mode', action='store_true')
    args.add_argument('--image', help='Generate an image for the playlist', action='store_true')
    args.add_argument('--no-browser', help='Don\'t open the browser for the authentication', action='store_true')
    args = args.parse_args()
    
    if args.playlist is None and args.playlist_modification is None:
        print("No arguments provided. Starting the interactive mode")
        print("Be aware that this script works weird with duplicates in the playlist (most of the time it will remove them)")
        args.interactive = True
    
    print("Arguments:", args)
    
    util = SpotifyPlaylistMod(args.conf, args.no_browser)
    
    util.getPlaylist(args.playlist if args.playlist is not None else util.askForPlaylist())
    if util.playlist is None:
        print("Couldn't find the playlist", args.playlist)
        exit(1)
    print('Using', util.playlist['name'], "with", len(util.playlist['tracks']), "tracks")

    if args.playlist_modification is None:
        print("Available actions")
        for i in range(len(ACTIONS)):
            print(i+1, ACTIONS[i], sep="\t")
        print("0\tCancel")
        while True:
            try:
                i = int(input("What do you want to do with it ?"))
                if i == 0:
                    exit()
                elif i > len(ACTIONS):
                    print('Invalid action')
                    continue
                args.playlist_modification = ACTIONS[i - 1]
            except ValueError or IndexError:
                continue
            break
        if input(f"Applying {args.playlist_modification} on {util.playlist['name']}. Is that correct ? [Y/n]").lower() not in ['y', 'yes', '']:
            print("Aborting")
            exit(0)

    print(f"Applying {args.playlist_modification} on {util.playlist['name']}")
    util.apply(args.playlist_modification, args.playlist_sort_order == 'asc')
    print(f"All done !")
    
    if args.interactive and not args.image:
        args.image = input("Would you like to generate an image fo the playlist ? [y/N]").lower() == 'y'

    if args.image:
        img = generateImage(util.playlist)
        # util.spotify.playlist_upload_cover_image(util.playlist['id'], img)
    
    if args.interactive:
        createTimer(util.playlist, args.playlist_modification, args.playlist_sort_order, args.conf, args.image)