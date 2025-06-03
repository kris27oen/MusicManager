import streamlit as st
from core.spotify import get_spotify_token, extract_playlist_id, get_playlist_details, get_playlist_tracks
from core.lyrics import process_tracks
from core.autogen import setup_autogen_agents

def playlist_client_flow():
    client_id = st.session_state.get('spotify_client_id')
    client_secret = st.session_state.get('spotify_client_secret')
    gemini_key = st.session_state.get('gemini_api_key')
    
    with st.container(key="playlist_client_container"):
        text_col, input_col = st.columns([5, 1])
        with text_col:
            playlist_url = st.text_input("Analyze Playlist URL", placeholder="Enter Spotify Playlist URL...", key="playlist_url_input")       

        if not client_id or not client_secret or not gemini_key:
            st.error("Please configure your API keys in the settings.")
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

        with input_col:
            if st.button(" ", key="client_analyze_button"):
                st.session_state['active_tab'] = 0

                # Full-screen spinner
                with st.spinner("Analyzing playlist..."):
                    agents = setup_autogen_agents(gemini_key)

                    playlist_data = get_playlist_details(access_token, playlist_id)
                    if not playlist_data:
                        st.error("Failed to fetch playlist details")
                        return

                    tracks = get_playlist_tracks(access_token, playlist_id)
                    if not tracks:
                        st.error("Failed to fetch playlist tracks")
                        return

                    progress_bar = st.progress(0)
                    tracks_with_lyrics = process_tracks(tracks, progress_bar)

                st.session_state['playlist_data'] = playlist_data
                st.session_state['tracks_with_lyrics'] = tracks_with_lyrics
                st.session_state['agents'] = agents
                st.session_state['analysis_ready'] = True
            
    st.markdown("""
        <style>
        .st-key-client_analyze_button [data-testid="stBaseButton-secondary"] {
            display: inline-block;
            width: 50px;
            height: 50px;
            padding-right: 10px;
            margin-bottom: -2px;
            vertical-align: middle;
            background-color: #0E1117;
            border-radius: 10px;
            --svg: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='%23000' d='m19.8 12.925l-15.4 6.5q-.5.2-.95-.088T3 18.5v-13q0-.55.45-.837t.95-.088l15.4 6.5q.625.275.625.925t-.625.925M5 17l11.85-5L5 7v3.5l6 1.5l-6 1.5zm0 0V7z'/%3E%3C/svg%3E");
            -webkit-mask-image: var(--svg);
            mask-image: var(--svg);
            -webkit-mask-repeat: no-repeat;
            mask-repeat: no-repeat;
            -webkit-mask-size: 100% 100%;
            mask-size: 100% 100%;
        }
        .st-key-client_analyze_button [data-testid="stBaseButton-secondary"]:hover {
            background-color: white;
        }
        .st-key-playlist_client_container [data-testid="stHorizontalBlock"] {
            align-items: end;
        }
        
        </style>
    """, unsafe_allow_html=True)