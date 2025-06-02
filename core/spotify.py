### File: core/spotify.py
import requests
import streamlit as st
from core.oauth_flow import get_spotify_client, logout_spotify
from ui.tabs import analyze_result
from core.lyrics import process_tracks, get_lyrics_auto
from core.autogen import setup_autogen_agents

def get_spotify_token(client_id, client_secret):
    auth_url = "https://accounts.spotify.com/api/token"
    auth_response = requests.post(
        auth_url,
        data={"grant_type": "client_credentials"},
        auth=(client_id, client_secret)
    )
    if auth_response.status_code != 200:
        st.error(f"Failed to get Spotify token: {auth_response.text}")
        return None
    return auth_response.json().get("access_token")


def extract_playlist_id(playlist_url):
    return playlist_url.split("/")[-1].split("?")[0]


def get_playlist_tracks(access_token, playlist_id):
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    tracks = []
    try:
        while url:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            tracks.extend(data["items"])
            url = data.get("next")
        return tracks
    except Exception as e:
        st.error(f"Error fetching playlist tracks: {e}")
        return []


def get_playlist_details(access_token, playlist_id):
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching playlist details: {e}")
        return {}


def search_spotify_tracks():
    sp = get_spotify_client()
    query = st.session_state.get('search_songs', '')

    if query:
        st.session_state['active_tab'] = 0
        with st.spinner(f"Searching for '{query}'..."):
            try:
                results = sp.search(q=query, type="track", limit=10)
            except Exception as e:
                st.error(f"Spotify search error: {e}")
                return
            
            tracks = results.get('tracks', {}).get('items', [])
            if not tracks:
                st.info("No songs found.")
                return
            
            st.subheader(f"Search Results for '{query}'")

            analyze_result_clicked = False
            
            with st.container(key="search_results_container", height=550):
                for i, track in enumerate(tracks):
                    album = track['album']
                    track_name = track['name']
                    artists = ", ".join([artist['name'] for artist in track['artists']])
                    album_name = album['name']
                    image_url = album['images'][0]['url'] if album.get('images') else "https://via.placeholder.com/50"

                    img_col, info_col = st.columns([1, 9])
                    with img_col:
                        st.image(image_url, width=50)

                    with info_col:
                        analyze_result_clicked = st.button(f"{track_name} — {artists}", key=f"track_btn_{i}")
            
                    if analyze_result_clicked:
                        # Prepare track dict to match analyzer expected keys
                        lyrics = get_lyrics_auto(track["artists"][0]["name"], track["name"])
                        selected_track = {
                            "id": track["id"],
                            "artist": track["artists"][0]["name"],
                            "title": track["name"],
                            "lyrics": lyrics or "Lyrics not found",
                            "preview_url": track.get("preview_url"),
                            "album": track.get("album", {}).get("name", "Unknown Album")
                        }
                        # Ensure playlist_data and agents exist in session_state or pass None if not available
                        playlist_data = st.session_state.get('playlist_data')
                        agents = setup_autogen_agents(st.session_state.get('gemini_api_key'))

                        # Show analyzer UI (clear other UI if needed)
                        st.session_state['active_tab'] = 0
                        analyze_result(selected_track, album, agents)

        
            # Custom CSS for the playlist container
            st.markdown(f"""
                <style>
                .stButton > button[data-testid="stBaseButton-secondary"] {{
                        border-radius: 4px;
                        border: 1px solid rgba(255, 255, 255, 0.2);
                        background-color: rgba(255, 255, 255, 0.05);
                        text-align: left;
                        padding: 10px 10px;
                        width: 100%;
                        color: white;
                        justify-content: stretch;
                    }}
                .st-key-search_results_container{{
                    gap: 7px;
                }}
                </style>
            """, unsafe_allow_html=True)
            

def playback():
    sp = get_spotify_client()
    access_token = sp.auth_manager.get_access_token(as_dict=False)
    track_uri = get_current_playback_uri(access_token)
    
    embed_url = f"https://open.spotify.com/embed/track/{track_uri.split(':')[-1]}?utm_source=generator"

    st.markdown(
        f"""
        <iframe 
            src="{embed_url}" 
            width="100%" 
            height="152" 
            frameborder="0" 
            allowtransparency="true" 
            allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" loading="lazy"
        </iframe>
        """, 
        unsafe_allow_html=True
    )
    
def get_current_playback_uri(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        response = requests.get("https://api.spotify.com/v1/me/player/currently-playing", headers=headers)
        if response.status_code == 200:
            data = response.json()
            item = data.get("item")
            if item:
                return item["uri"]
            else:
                st.warning ("Nothing is currently playing.")
        else:
            st.warning("No playback info available.")
    except Exception as e:
        return f"Playback info error: {e}"
    
def play_track(access_token, track_uri=None, device_id=None):
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    payload = {}

    if track_uri:
        payload["uris"] = [track_uri]

    params = {"device_id": device_id} if device_id else {}

    try:
        response = requests.put(
            "https://api.spotify.com/v1/me/player/play",
            headers=headers,
            json=payload,
            params=params
        )
        if response.status_code in [200, 204]:
            return "Playback started"
        else:
            return f"Failed to play: {response.text}"
    except Exception as e:
        return f"Playback error: {e}"


def pause_playback(access_token, device_id=None):
    headers = {"Authorization": f"Bearer {access_token}"}
    url = "https://api.spotify.com/v1/me/player/pause"
    if device_id:
        url += f"?device_id={device_id}"

    try:
        response = requests.put(url, headers=headers)
        if response.status_code in [200, 204]:
            return "⏸️ Playback paused"
        else:
            return f"Failed to pause: {response.text}"
    except Exception as e:
        return f"Pause error: {e}"


def next_track(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        response = requests.post("https://api.spotify.com/v1/me/player/next", headers=headers)
        if response.status_code in [200, 204]:
            return "⏭️ Skipped to next track"
        else:
            return f"Failed to skip: {response.text}"
    except Exception as e:
        return f"Skip error: {e}"


def get_current_playback(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        response = requests.get("https://api.spotify.com/v1/me/player/currently-playing", headers=headers)
        if response.status_code == 200:
            data = response.json()
            item = data.get("item")
            if item:
                return f"🎵 Now playing: {item['name']} - {item['artists'][0]['name']}"
            else:
                return "Nothing is currently playing."
        else:
            return "No playback info available."
    except Exception as e:
        return f"Playback info error: {e}"

def search_tracks(access_token, query, limit=5, offset=0):
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "q": query,
        "type": "track",
        "limit": limit,
        "offset": offset
    }

    try:
        response = requests.get("https://api.spotify.com/v1/search", headers=headers, params=params)
        response.raise_for_status()
        results = response.json()["tracks"]["items"]
        return results  # list of track dicts
    except Exception as e:
        st.error(f"Search error: {e}")
        return []


def add_track_to_queue(access_token, track_uri, device_id=None):
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"uri": track_uri}
    if device_id:
        params["device_id"] = device_id

    try:
        response = requests.post("https://api.spotify.com/v1/me/player/queue", headers=headers, params=params)
        if response.status_code in [200, 204]:
            return "✅ Added to queue"
        else:
            return f"Failed to queue track: {response.text}"
    except Exception as e:
        return f"Queue error: {e}"

def get_playback_queue(access_token):
    headers = {"Authorization": f"Bearer " + access_token}
    try:
        response = requests.get("https://api.spotify.com/v1/me/player/queue", headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get("queue", [])  # List of track objects
    except Exception as e:
        st.error(f"Error retrieving playback queue: {e}")
        return []

def create_playlist(access_token, user_id, name="My AI Playlist", description="Created by AI Assistant"):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "name": name,
        "description": description,
        "public": False
    }
    try:
        response = requests.post(
            f"https://api.spotify.com/v1/users/{user_id}/playlists",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        return response.json().get("id")
    except Exception as e:
        st.error(f"Playlist creation error: {e}")
        return None

def add_track_to_playlist(access_token, playlist_id, track_uri):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "uris": [track_uri]
    }
    try:
        response = requests.post(
            f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks",
            headers=headers,
            json=payload
        )
        if response.status_code in [200, 201]:
            return "✅ Added to playlist"
        else:
            return f"Failed to add track: {response.text}"
    except Exception as e:
        return f"Error adding track: {e}"
    
def play_playlist(access_token: str, playlist_id: str):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    data = {
        "context_uri": f"spotify:playlist:{playlist_id}"
    }
    response = requests.put(
        "https://api.spotify.com/v1/me/player/play",
        headers=headers,
        json=data
    )
    if response.status_code == 204:
        return "▶️ Playlist is now playing!"
    else:
        return f"⚠️ Failed to start playback: {response.text}"
