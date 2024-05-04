# Spotify Playlist ordering tool

This tool allows you to order (or shuffle) your Spotify playlists according to serval parameters.

It also allows you to easily create a systemd timer to frequently update your playlists (pretty useful to shuffle your playlist every so often to fix spotify broken random mode).

## Installation

First, you need to install the required packages:

```bash
pip3 install -r requirements.txt
```

Then, you need to create a Spotify application and get the client id and client secret. You can do that by following the instructions [here](https://developer.spotify.com/documentation/general/guides/app-settings/).

Finally, you need to create a file named `config.json` in the root directory of the project with the following content (`Redirect URI` is optional):

```json
{
    "Client ID": "YOUR_CLIENT_ID",
    "Client secret": "YOUR_CLIENT_SECRET",
    "Redirect URI": "http://localhost:8888/callback"
}
```

## Usage

> **Note**: I recommend to save the playlists you apply this tool to with tools such as [`ryanwarrick/spotify-playlist-utility`](https://github.com/ryanwarrick/spotify-playlist-utility), as far as I know only duplicate might get removed, but you never know.

That's actually pretty simple to use, you just need to run the main.py file and follow the instructions:

```bash
python3 main.py
```

You could technically also use it as a library, but I don't think that's necessary, using [spotipy](https://spotipy.readthedocs.io/) directly is probably a better idea.
