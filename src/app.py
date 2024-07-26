# src/app.py

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, request, redirect, jsonify
import jwt
import time
import requests

app = Flask(__name__)

SPOTIPY_CLIENT_ID = 'your_spotify_client_id'
SPOTIPY_CLIENT_SECRET = 'your_spotify_client_secret'
SPOTIPY_REDIRECT_URI = 'http://localhost:5000/callback'

APPLE_TEAM_ID = 'your_apple_team_id'
APPLE_KEY_ID = 'your_apple_key_id'
APPLE_PRIVATE_KEY = 'path_to_your_private_key.p8'

scope = 'playlist-read-private'
sp_oauth = SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                        client_secret=SPOTIPY_CLIENT_SECRET,
                        redirect_uri=SPOTIPY_REDIRECT_URI,
                        scope=scope)

def create_apple_music_token():
    token = jwt.encode(
        {
            "iss": APPLE_TEAM_ID,
            "iat": int(time.time()),
            "exp": int(time.time()) + 86400 * 180,
        },
        open(APPLE_PRIVATE_KEY).read(),
        algorithm='ES256',
        headers={
            "alg": "ES256",
            "kid": APPLE_KEY_ID
        }
    )
    return token

def search_apple_music(token, song_name, artist_name):
    url = f'https://api.music.apple.com/v1/catalog/us/search?term={song_name} {artist_name}&types=songs'
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(url, headers=headers)
    return response.json() if response.status_code == 200 else None

def create_apple_music_playlist(user_token, playlist_name, track_ids):
    url = 'https://api.music.apple.com/v1/me/library/playlists'
    headers = {
        'Authorization': f'Bearer {apple_music_token}',
        'Music-User-Token': user_token,
        'Content-Type': 'application/json'
    }
    payload = {
        "attributes": {
            "name": playlist_name,
            "description": "Playlist imported from Spotify"
        },
        "relationships": {
            "tracks": {
                "data": [{"id": track_id, "type": "songs"} for track_id in track_ids]
            }
        }
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

def map_spotify_to_apple_music(sp, spotify_playlist_id, apple_music_token):
    tracks = sp.playlist_tracks(spotify_playlist_id)['items']
    apple_music_tracks = []
    for track in tracks:
        track_name = track['track']['name']
        artist_name = track['track']['artists'][0]['name']
        search_result = search_apple_music(apple_music_token, track_name, artist_name)
        if search_result and 'results' in search_result and 'songs' in search_result['results']:
            song_data = search_result['results']['songs']['data']
            if song_data:
                apple_music_track_id = song_data[0]['id']
                apple_music_tracks.append(apple_music_track_id)
    return apple_music_tracks

@app.route('/')
def login():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    access_token = token_info['access_token']
    
    sp = spotipy.Spotify(auth=access_token)
    playlists = sp.current_user_playlists()

    # Get the first playlist for simplicity
    spotify_playlist_id = playlists['items'][0]['id']
    apple_music_token = create_apple_music_token()
    apple_music_track_ids = map_spotify_to_apple_music(sp, spotify_playlist_id, apple_music_token)
    
    user_token = 'user_music_token'  # You need to handle getting the Apple Music user token
    apple_music_playlist = create_apple_music_playlist(user_token, 'My Spotify Playlist', apple_music_track_ids)
    
    return jsonify(apple_music_playlist)

if __name__ == '__main__':
    app.run(port=5000)