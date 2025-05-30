import streamlit as st
from core.spotify import get_spotify_token, extract_playlist_id, get_playlist_details, get_playlist_tracks
from core.lyrics import process_tracks
from core.autogen import setup_autogen_agents

def playlist_client_flow():
    playlist_url = st.text_input("Enter Spotify Playlist URL", placeholder="https://open.spotify.com/playlist/...")
    if not playlist_url:
        st.info("Please enter a Spotify playlist URL to get started")
        return

    client_id = st.session_state.get('spotify_client_id')
    client_secret = st.session_state.get('spotify_client_secret')
    gemini_key = st.session_state.get('gemini_api_key')

    if not client_id or not client_secret:
        st.error("Please provide Spotify API credentials in the sidebar")
        return
    if not gemini_key:
        st.error("Please provide a Gemini API key in the sidebar")
        return

    access_token = get_spotify_token(client_id, client_secret)
    if not access_token:
        st.error("Failed to authenticate with Spotify")
        return

    try:
        playlist_id = extract_playlist_id(playlist_url)
    except Exception as e:
        st.error(f"Invalid playlist URL: {e}")
        return

    if st.button("Analyze Playlist", key="client_analyze_button"):
        st.session_state['active_tab'] = 0

        with st.spinner("Setting up AutoGen agents..."):
            agents = setup_autogen_agents(gemini_key)

        with st.spinner("Fetching playlist data..."):
            playlist_data = get_playlist_details(access_token, playlist_id)
            if not playlist_data:
                st.error("Failed to fetch playlist details")
                return
            tracks = get_playlist_tracks(access_token, playlist_id)
            if not tracks:
                st.error("Failed to fetch playlist tracks")
                return

        with st.spinner(f"Processing {len(tracks)} tracks..."):
            progress_bar = st.progress(0)
            tracks_with_lyrics = process_tracks(tracks, progress_bar)

        st.session_state['playlist_data'] = playlist_data
        st.session_state['tracks_with_lyrics'] = tracks_with_lyrics
        st.session_state['agents'] = agents
        st.session_state['analysis_ready'] = True