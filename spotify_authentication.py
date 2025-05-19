import spotipy
from spotipy.oauth2 import SpotifyOAuth
import streamlit as st

def get_spotify_auth():
    try:
        # Explicitly access secrets and verify they exist
        client_id = st.secrets["SPOTIFY_CLIENT_ID"]
        client_secret = st.secrets["SPOTIFY_CLIENT_SECRET"]
        redirect_uri = st.secrets["SPOTIFY_REDIRECT_URI"]
        
        if not all([client_id, client_secret, redirect_uri]):
            st.error("Missing Spotify credentials in secrets.toml")
            return None
            
        return SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope="playlist-read-private playlist-read-collaborative",
            cache_path="./.spotify_cache",  # Explicitly set cache path
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
            
            # Get auth code from URL
            query_params = st.query_params
            if "code" in query_params:
                code = query_params["code"]
                token_info = sp_oauth.get_access_token(code)
                
        if token_info:
            # Use the token_info directly with Spotify client
            return spotipy.Spotify(auth_manager=sp_oauth)
            
        return None
        
    except Exception as e:
        st.error(f"Authentication error: {str(e)}")
        return None