import streamlit as st
from ui.sidebar import render_sidebar
from core.client_flow import playlist_client_flow
from core.oauth_flow import playlist_oauth_flow
from core.music_cluster import render_music_clusters_graph
from ui.tabs import display_playlist_info, display_tracks_list, display_track_analyzer
from ui.chatbot import music_chatbot_ui

st.set_page_config(page_title="Spotify Lyrics Analyzer with Autogen", layout="wide")
st.title("🎵 Lyrics Analyzer with Autogen")
st.markdown("Analyze lyrics from Spotify playlists using Autogen agents!")

render_sidebar()

def main():
    if 'analysis_ready' not in st.session_state:
        st.session_state['analysis_ready'] = False
    if 'active_tab' not in st.session_state:
        st.session_state['active_tab'] = 0

    if st.session_state.get('analysis_ready'):
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["Playlist Info", "Tracks List", "Track Analyzer", "Music Chatbot", "Music Web"])
        with tab1:
            display_playlist_info(
                st.session_state['playlist_data'], 
                st.session_state['tracks_with_lyrics'], 
                st.session_state['agents']
            )
        with tab2:
            display_tracks_list(st.session_state['tracks_with_lyrics'])
        with tab3:
            display_track_analyzer(
                st.session_state['playlist_data'], 
                st.session_state['tracks_with_lyrics'], 
                st.session_state['agents']
            )
        with tab4:
            music_chatbot_ui(
                st.session_state['agents'], 
                st.session_state['tracks_with_lyrics']
            )
        with tab5:
            render_music_clusters_graph(
                st.session_state['tracks_with_lyrics']
            )
        if st.button("Start Over", key="start_over"):
            for key in ['analysis_ready', 'playlist_data', 'tracks_with_lyrics', 'agents', 'active_tab']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    else:
        auth_method = st.radio(
            "Choose how you want to access playlists:",
            ["Login with your Spotify account", "Enter a Spotify playlist URL"],
            horizontal=True
        )
        if auth_method == "Login with your Spotify account":
            playlist_oauth_flow()
        else:
            playlist_client_flow()

if __name__ == "__main__":
    main()
