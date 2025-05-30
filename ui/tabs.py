### File: ui/tabs.py
import streamlit as st
import matplotlib.pyplot as plt
from core.autogen import analyze_playlist_with_agents
from core.lyrics import generate_wordcloud, compute_sentiment_scores, plot_mood_radar

def display_playlist_info(playlist_data, tracks_with_lyrics, agents):
    st.session_state['active_tab'] = 0
    if playlist_data.get("images"):
        col1, col2 = st.columns([1, 3])
        with col1:
            st.image(playlist_data["images"][0]["url"], width=200)
        with col2:
            st.header(playlist_data["name"])
            st.write(f"Created by: {playlist_data.get('owner', {}).get('display_name', 'Unknown')}")
            st.write(f"Tracks: {len(tracks_with_lyrics)}")
            if playlist_data.get("description"):
                st.write(f"Description: {playlist_data['description']}")

    with st.spinner("Analyzing playlist with Autogen..."):
        analysis = analyze_playlist_with_agents(agents, playlist_data, tracks_with_lyrics, "general")
        st.subheader("Playlist Analysis (via AutoGen)")
        st.write(analysis)

    all_lyrics = " ".join([
        track['lyrics'] for track in tracks_with_lyrics 
        if track.get('lyrics') and track['lyrics'] != "Lyrics not found"
    ])

    st.subheader("Lyrics Word Cloud")
    if all_lyrics:
        try:
            wordcloud = generate_wordcloud(all_lyrics)
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.imshow(wordcloud, interpolation='bilinear')
            ax.axis("off")
            st.pyplot(fig)
        except Exception as e:
            st.error(f"Error generating word cloud: {e}")
    else:
        st.warning("No lyrics available to generate a word cloud.")

def display_tracks_list(tracks_with_lyrics):
    st.subheader("Tracks in Playlist")
    st.session_state['active_tab'] = 1

    filter_text = st.text_input("Filter by song title or artist", "", placeholder="Type to filter...")
    filtered_tracks = [
        track for track in tracks_with_lyrics
        if filter_text.lower() in track['title'].lower() or filter_text.lower() in track['artist'].lower()
    ] if filter_text else tracks_with_lyrics

    for i, track in enumerate(filtered_tracks):
        with st.expander(f"{i+1}. {track['title']} - {track['artist']}"):
            if track.get('lyrics') and track['lyrics'] != "Lyrics not found":
                st.markdown(f"**Lyrics Preview:**\n```{track['lyrics'][:500]}\n```")
            else:
                st.info("Lyrics not found")

def display_track_analyzer(playlist_data, tracks_with_lyrics, agents):
    st.subheader("🔍 Analyze Individual Song")
    available_tracks = [
        f"{t['title']} - {t['artist']}" for t in tracks_with_lyrics 
        if t.get('lyrics') and t['lyrics'] != "Lyrics not found"
    ]

    if not available_tracks:
        st.warning("No tracks with lyrics available for analysis.")
        return

    selected_song = st.selectbox("Select a track with lyrics", available_tracks)
    if st.button("Analyze Song", key="analyze_song_button"):
        selected_track = next(
            t for t in tracks_with_lyrics
            if f"{t['title']} - {t['artist']}" == selected_song
        )

        st.markdown(f"### ✨ {selected_track['title']} - {selected_track['artist']}")
        col1, col2 = st.columns(2)

        with col1:
            try:
                wc = generate_wordcloud(selected_track["lyrics"])
                fig, ax = plt.subplots(figsize=(4, 4))
                ax.imshow(wc, interpolation='bilinear')
                ax.axis("off")
                st.pyplot(fig)
            except Exception as e:
                st.error(f"Error generating word cloud: {e}")

        with col2:
            try:
                sentiments = compute_sentiment_scores(selected_track["lyrics"])
                fig = plot_mood_radar(sentiments)
                st.pyplot(fig)
            except Exception as e:
                st.error(f"Error generating sentiment analysis: {e}")

        with st.spinner("Analyzing lyrics..."):
            result = analyze_playlist_with_agents(agents, playlist_data, [selected_track], "lyrics")
            st.markdown("**Lyrics Analysis Result:**")
            st.write(result)