import streamlit as st
from ui.sidebar import render_sidebar
from core.client_flow import playlist_client_flow
from core.oauth_flow import playlist_oauth_flow
from core.music_cluster import render_music_clusters_graph
from ui.tabs import display_playlist_info, display_tracks_list, display_track_analyzer
from ui.chatbot import music_chatbot_ui

# st.set_page_config(page_title="Music Assistant", layout="wide")

render_sidebar()

def main():
    main_col, right_sidebar = st.columns([7, 3])
    with main_col:
        title_placeholder = st.empty()
        title_placeholder.title("🎵Music Assistant")

        with st.container(key="header_container"):
            home_col, search_col = st.columns([1, 10])
            with home_col:
                # Home Button
                if st.button(" ", key="home_button"):
                    title_placeholder.title("🎵Music Assistant")
                    st.session_state['active_tab'] = 0
                    st.session_state['analysis_ready'] = False
                    st.session_state['playlist_data'] = None
                    st.session_state['tracks_with_lyrics'] = None
                    st.session_state['agents'] = None

            with search_col:
                with st.container():
                    song_search = st.text_input(" ", placeholder="Search Song...", key="song_search_input")

        if 'analysis_ready' not in st.session_state:
            st.session_state['analysis_ready'] = False
        if 'active_tab' not in st.session_state:
            st.session_state['active_tab'] = 0

        if st.session_state.get('analysis_ready'):
            title_placeholder.empty()
            st.header("Playlist Analyzer")
            tab1, tab2, tab3, tab4 = st.tabs(["Playlist Info", "Tracks List", "Track Analyzer", "Music Web"])
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
                render_music_clusters_graph(
                    st.session_state['tracks_with_lyrics']
                )
        # else:
            
            # if auth_method == "Login with your Spotify account":
            #     playlist_oauth_flow()
            # else:
        
    with right_sidebar:
        if 'tracks_with_lyrics' in st.session_state and 'agents' in st.session_state:
            music_chatbot_ui(st.session_state['agents'], st.session_state['tracks_with_lyrics'])
        else:
            music_chatbot_ui(None, None)
        

if __name__ == "__main__":
    main()

st.markdown("""
        <style>
        .st-key-home_button [data-testid="stBaseButton-secondary"] {
            display: inline-block;
            width: 50px;
            height: 50px;
            margin-right: 8px;
            vertical-align: middle;
            background-color: #262730;
            --svg: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='%23ffffff' d='M6 19h3v-5q0-.425.288-.712T10 13h4q.425 0 .713.288T15 14v5h3v-9l-6-4.5L6 10zm-2 0v-9q0-.475.213-.9t.587-.7l6-4.5q.525-.4 1.2-.4t1.2.4l6 4.5q.375.275.588.7T20 10v9q0 .825-.588 1.413T18 21h-4q-.425 0-.712-.288T13 20v-5h-2v5q0 .425-.288.713T10 21H6q-.825 0-1.412-.587T4 19m8-6.75'/%3E%3C/svg%3E");
            -webkit-mask-image: var(--svg);
            mask-image: var(--svg);
            -webkit-mask-repeat: no-repeat;
            mask-repeat: no-repeat;
            -webkit-mask-size: 100% 100%;
            mask-size: 100% 100%;
        }

        .st-key-home_button [data-testid="stBaseButton-secondary"]:hover {
            background-color: white;
        }
        .st-key-song_search_input [data-testid="stWidgetLabel"] {
            display: none; /* Hide the label */
        }
        .st-key-header_container [data-testid="stHorizontalBlock"] {
            align-items: center;
        }
        [data-testid="stMain"]{
            align-items: start;
            justify-content: space-between;
        }
        [data-testid="stMainBlockContainer"]{
            padding: 4rem 3rem 5rem;
            width: 100%;
            max-width: none;
        }
        </style>
    """, unsafe_allow_html=True)