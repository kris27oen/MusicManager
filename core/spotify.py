### File: core/spotify.py
import requests
import streamlit as st

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
