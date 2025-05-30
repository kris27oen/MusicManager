import spotipy
import os
import streamlit as st
from spotipy.oauth2 import SpotifyOAuth
from core.lyrics import process_tracks
from core.autogen import setup_autogen_agents

def logout_spotify():
    try:
        if os.path.exists(".spotify_cache"):
            os.remove(".spotify_cache")
        for key in ['token_info', 'playlist_data', 'tracks_with_lyrics', 'agents', 'analysis_ready']:
            if key in st.session_state:
                del st.session_state[key]
    except Exception as e:
        st.error(f"Error during logout: {e}")

def get_spotify_auth():
    try:
        # Explicitly access secrets and verify they exist
        client_id = st.secrets["SPOTIFY_CLIENT_ID"]
        client_secret = st.secrets["SPOTIFY_CLIENT_SECRET"]
        redirect_uri = st.secrets["SPOTIFY_REDIRECT_URI"]
        print(client_id, client_secret, redirect_uri)  # Debugging line
        
        if not all([client_id, client_secret, redirect_uri]):
            st.error("Missing Spotify credentials in secrets.toml")
            return None
            
        return SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope="playlist-read-private playlist-read-collaborative",
            cache_path="./.spotify_cache",  # Explicitly set cache path
            username=None,  # Set to None to use the authenticated user's ID
            show_dialog=True
        )
    except Exception as e:
        st.error(f"Error accessing Spotify credentials: {str(e)}")
        return None

def get_spotify_client():
    sp_oauth = get_spotify_auth()
    if not sp_oauth:
        return None

    try:
        token_info = sp_oauth.get_cached_token()

        if not token_info:
            auth_url = sp_oauth.get_authorize_url()
            st.write("Please log in to Spotify:")
            st.markdown(f"[Click here to authorize]({auth_url})", unsafe_allow_html=True)

            query_params = st.query_params
            if "code" in query_params:
                code = query_params["code"]
                token_info = sp_oauth.get_access_token(code)
                print("Token info after authorization:", token_info)  # Debugging line

        if token_info:
            sp = spotipy.Spotify(auth_manager=sp_oauth)
            print("Spotify client created successfully")  # Debugging line
            try:
                user = sp.current_user()
                print("User info retrieved:", user)  # Debugging line
                # If user info is empty or invalid, force logout
                if not user or not user.get("id"):
                    st.warning("Spotify account not registered or invalid. Logging out...")
                    logout_spotify()
                    return None
            except Exception:
                st.warning("Failed to get Spotify user info. Logging out...")
                logout_spotify()
                return None

            return sp

        return None

    except Exception as e:
        st.error(f"Authentication error: {str(e)}")
        return None

def playlist_oauth_flow():
    try:
        sp = get_spotify_client()
        if sp:
            st.session_state['token_info'] = True
            user_col, button_col = st.columns([3, 1])
            user = sp.current_user()
            with user_col:
                st.success(f"Logged in as: {user['display_name']}")
            with button_col:
                if st.button("Logout", key="oauth_logout_button"):
                    logout_spotify()
                    st.rerun()

            playlists = sp.current_user_playlists()
            playlist_names = [pl["name"] for pl in playlists["items"]]
            playlist_ids = [pl["id"] for pl in playlists["items"]]

            if not playlist_names:
                st.warning("No playlists found in your account.")
                return

            selected = st.selectbox("Select a playlist to analyze", playlist_names)
            selected_id = playlist_ids[playlist_names.index(selected)]

            # Button to trigger analysis
            analyze_clicked = st.button("Analyze Playlist", key="oauth_analyze_button")

            if analyze_clicked:
                st.session_state['active_tab'] = 0
                with st.spinner("Fetching playlist data..."):
                    try:
                        playlist_data = sp.playlist(selected_id)
                        tracks = sp.playlist_tracks(selected_id)
                    except Exception:
                        st.error("Failed to connect to Spotify. Please check your authentication.")
                        return

                    with st.spinner(f"Processing {playlist_data.get('tracks', {}).get('total', 0)} tracks..."):
                        progress_bar = st.progress(0)
                        tracks_with_lyrics = process_tracks(tracks['items'], progress_bar)
                    with st.spinner("Setting up AutoGen agents..."):
                        agents = setup_autogen_agents(st.session_state.get('gemini_api_key'))

                    st.session_state['playlist_data'] = playlist_data
                    st.session_state['tracks_with_lyrics'] = tracks_with_lyrics
                    st.session_state['agents'] = agents
                    st.session_state['analysis_ready'] = True
                    st.rerun()

    except Exception as e:
        st.error(f"Error in OAuth flow: {str(e)}")