import streamlit as st
import json
from core.oauth_flow import get_spotify_client, logout_spotify
from core.lyrics import process_tracks
from core.autogen import setup_autogen_agents
from core.client_flow import playlist_client_flow

def account_info():
    sp = get_spotify_client()
    if sp:
        user = sp.current_user()
        
        with st.container(key="sidebar_user_info"):
            profile_col, user_col, button_col = st.columns([1, 3, 2])
            with profile_col:
                if user and user.get("images"):
                    st.image(user["images"][0]["url"], width=50)
                else:
                    st.image("https://via.placeholder.com/50", width=50)
            with user_col:
                if user:
                    st.markdown(f"**{user['display_name']}**")
                else:
                    st.markdown("**Not logged in**")
            with button_col:
                if st.button("Logout", key="sidebar_logout_button"):
                    logout_spotify()
                    st.rerun()
            
        st.markdown(f"""
            <style>
            .st-key-sidebar_user_info [data-testid="stHorizontalBlock"] {{
                align-items: center;
            }}
            </style>
        """, unsafe_allow_html=True)
        
        return sp
    
    else:
        return None

def playlist_list(sp):
    playlists = sp.current_user_playlists()
    playlist_items = playlists['items']

    with st.container(key="playlist_container", height=350):
        for i, album in enumerate(playlist_items):
            profile_col, playlist_name = st.columns([1, 4])
            with profile_col:
                if album.get("images"):
                    st.image(album["images"][0]["url"], width=40)
                else:
                    st.image("https://via.placeholder.com/50", width=40)
            with playlist_name:
                if st.button(f"{album['name']}", key=f"album_btn_{i}"):
                    st.session_state['active_tab'] = 0
                    with st.spinner("Fetching playlist data..."):
                        try:
                            playlist_data = sp.playlist(album['id'])
                            tracks = sp.playlist_tracks(album['id'])
                        except Exception:
                            st.error("Failed to connect to Spotify. Please check your authentication.")
                            st.stop()

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
            
            # Custom CSS for playlist list buttons
            st.markdown(f"""
                <style>
                .st-key-album_btn_{i} [data-testid="stBaseButton-secondary"]{{
                    border-radius: 4px; /* Less rounded corners */
                    border: 1px solid rgba(255, 255, 255, 0.2); /* Subtle border */
                    background-color: rgba(255, 255, 255, 0.05); /* Semi-transparent background */
                    text-align: left; /* Align text to the left */
                    padding: 4px 8px; /* Reduced padding */
                    width: 100%; /* Full width buttons */
                    color: white; /* Text color */
                    justify-content: stretch; /* Stretch button to fill container */
                }}
                </style>
            """, unsafe_allow_html=True)
    
    # Custom CSS for the playlist container
    st.markdown(f"""
        <style>
        .st-key-playlist_container{{
            gap: 7px;
        }}
        .st-key-playlist_info [data-testid="stVerticalBlockBorderWrapper"]{{
            background-color: #0E1117;
        }}
        </style>
    """, unsafe_allow_html=True)

@st.dialog("Settings")
def settings_popup():
    st.selectbox("Language", ["English", "繁體中文"], index=0)

    st.header("API Configuration")
    spotify_client_id = st.text_input("Spotify Client ID", type="password", value="b9e0979d54c449d4a1b7f23a1be1d329")
    spotify_client_secret = st.text_input("Spotify Client Secret", type="password", value="03559d2dc6b643e8af412d5930ee4ec2")
    gemini_api_key = st.text_input("Gemini API Key", type="password", value="AIzaSyBT-j55lWkh5Mz9_RrSwpCaaagDPcCDjpI")

    if st.button("Save API Keys"):
        st.success("API keys saved!")
        if gemini_api_key:
            config = {
                "config_list": [
                    {
                        "model": "gemini-2.0-flash-lite",
                        "api_key": gemini_api_key,
                        "base_url": "https://generativelanguage.googleapis.com/v1beta/"
                    }
                ]
            }
            with open("config.json", "w") as f:
                json.dump(config, f, indent=4)
    
        # Store credentials in session
        st.session_state['spotify_client_id'] = spotify_client_id
        st.session_state['spotify_client_secret'] = spotify_client_secret
        st.session_state['gemini_api_key'] = gemini_api_key
        st.rerun()
    
def render_sidebar():
    with st.sidebar:
        sp = account_info()
        
        spotify_client_id = st.session_state.get('spotify_client_id')
        spotify_client_secret = st.session_state.get('spotify_client_secret')
        gemini_api_key = st.session_state.get('gemini_api_key')
        
        if not spotify_client_id or not spotify_client_secret or not gemini_api_key:
            st.warning("Please configure your API keys in the settings.")
        
        if sp:
            with st.container(key="playlist_info"):
                st.header(f"{sp.current_user()['display_name']}'s Playlist")
                playlist_list(sp)    
            playlist_client_flow()
        
        if st.button("Settings", icon="⚙️", key="settings_button"):
            settings_popup()
        
        st.markdown(f"""
            <style>
                .st-key-settings_button [data-testid="stBaseButton-secondary"] {{
                    text-align: center;
                    width: 100%;
                }}
                [data-testid="stSidebarUserContent"]{{
                    padding: 0px 1.5rem 2rem;
                }}
            </style>       
        """, unsafe_allow_html=True)
        