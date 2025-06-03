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
            