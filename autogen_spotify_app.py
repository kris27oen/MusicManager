import streamlit as st
import requests
import re
import time
import autogen
import jieba
from typing import Dict, List, Optional, Union, Any
import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from openai import OpenAI
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
from wordcloud import WordCloud
from opencc import OpenCC
from spotify_authentication import get_spotify_auth, get_spotify_client

# Initialize OpenCC converter for Simplified to Traditional Chinese
chinese_converter = OpenCC('s2t')

# Title and page configuration
st.set_page_config(page_title="Spotify Lyrics Analyzer with Autogen", layout="wide")
st.title("🎵 Lyrics Analyzer with Autogen")
st.markdown("Analyze lyrics from Spotify playlists using Autogen agents!")

# Sidebar for settings
with st.sidebar:
    st.header("Settings")
    selected_lang = st.selectbox("Language", ["English", "繁體中文"], index=0)
    
    # API Keys
    with st.expander("API Configuration"):
        spotify_client_id = st.text_input("Spotify Client ID", value="7e506b1a8964420b8ce8b76e3d791acc", type="password")
        spotify_client_secret = st.text_input("Spotify Client Secret", value="2e10e4d49112499c9b8ff11ee361c91d", type="password")
        gemini_api_key = st.text_input("Gemini API Key", value="AIzaSyBT-j55lWkh5Mz9_RrSwpCaaagDPcCDjpI", type="password")
        
        if st.button("Save API Keys"):
            st.success("API keys saved!")
            
            # Save Gemini API key to config file
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

#Add active tab state
if 'active_tab' not in st.session_state:
    st.session_state['active_tab'] = 0

# Function to get Spotify access token
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

# Function to extract playlist ID from URL
def extract_playlist_id(playlist_url):
    return playlist_url.split("/")[-1].split("?")[0]

# Function to get tracks from a playlist
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

# Function to get playlist details
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

# Function to get lyrics
def get_lyrics_en(artist, title):
    formatted_artist = artist.strip().lower().replace(" ", "%20")
    formatted_title = title.strip().lower().replace(" ", "%20")
    
    url = f"https://api.lyrics.ovh/v1/{formatted_artist}/{formatted_title}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json().get("lyrics")
        else:
            return None
    except Exception:
        return None
    
def get_lyrics_zh(artist, title):
    """
    Get Chinese lyrics from NetEase Cloud Music (unofficial API), and convert to Traditional Chinese.

    Args:
        artist (str): Artist name.
        title (str): Song title.

    Returns:
        str or None: Traditional Chinese lyrics if found, else None.
    """
    formatted_artist = artist.strip().lower().replace(" ", "%20")
    formatted_title = title.strip().lower().replace(" ", "%20")

    # Step 1: search song
    search_url = "http://music.163.com/api/search/get"
    params = {
        "s": f"{formatted_title} {formatted_artist}",
        "type": 1,
        "limit": 1
    }

    try:
        res = requests.post(search_url, data=params)
        result = res.json()
        if "result" not in result or "songs" not in result["result"] or not result["result"]["songs"]:
            return None
        song_id = result["result"]["songs"][0]["id"]
    except Exception:
        return None

    # Step 2: fetch lyrics
    lyric_url = f"http://music.163.com/api/song/lyric?os=pc&id={song_id}&lv=-1&kv=-1&tv=-1"
    try:
        lyric_res = requests.get(lyric_url)
        lyrics_json = lyric_res.json()

        if "lrc" not in lyrics_json or "lyric" not in lyrics_json["lrc"]:
            return None

        raw_lyrics = lyrics_json["lrc"]["lyric"]
        if "纯音乐" in raw_lyrics:
            return None

        # Remove timestamps
        lyrics = re.sub(r'\[\s*\d{2}\s*:\s*\d{2}(?:\.\d{1,3})?\s*\]', '', raw_lyrics)

        # Remove common metadata lines
        pattern = r'(作词|词|作曲|曲|编曲|制作人|母帶|混音|Studios|工程 師|监制|Music|OP|演唱|錄音師|制作公司|混音|吉他|和声|錄音室|制作|维伴音|京延|编写)\s*[:：].*'
        lyrics_lines = lyrics.splitlines()
        filtered_lines = [line.strip() for line in lyrics_lines if not re.match(pattern, line.strip()) and line.strip()]

        simplified_lyric = ' '.join(filtered_lines)
        traditional_lyric = chinese_converter.convert(simplified_lyric)
        traditional_lyric = traditional_lyric.replace("咪", "夢")  # Fix for misconverted character
        return traditional_lyric

    except Exception:
        return None
    
def get_lyrics_auto(artist: str, title: str) -> str | None:
    """
    Automatically get lyrics: try English source first, fallback to Chinese if not found.

    Args:
        artist (str): Artist name.
        title (str): Song title.

    Returns:
        str or None: Lyrics text (English or Traditional Chinese) if found, else None.
    """
    lyrics = get_lyrics_en(artist, title)
    if lyrics:
        return lyrics

    lyrics = get_lyrics_zh(artist, title)
    if lyrics:
        return lyrics

    return None


# Function to generate wordcloud 
def generate_wordcloud(text):
    """
    Automatically handle mixed Chinese-English lyrics and generate a word cloud.

    Parameters:
    - text: The lyrics text.
    - font_path: Path to the font file that supports Chinese characters 
                 (recommended to always specify for compatibility with both Chinese and English).
    """
    # Use jieba to segment mixed Chinese-English lyrics (English words and numbers will be preserved)
    words = jieba.cut(text)
    processed_text = " ".join(words)

    wordcloud = WordCloud(width=800, height=400, background_color='white', font_path="TaipeiSansTCBeta-Regular.ttf",).generate(processed_text)
    return wordcloud

def compute_sentiment_scores(lyrics):
    """
    Compute sentiment scores for lyrics without using TextBlob.
    Uses a simple lexicon-based approach with predefined emotion words.
    
    Args:
        lyrics (str): The song lyrics to analyze
        
    Returns:
        dict: Dictionary with emotion scores
    """
    if not lyrics or not isinstance(lyrics, str):
        return {
            "joy": 0.5,
            "sadness": 0.5,
            "anger": 0.5,
            "fear": 0.5,
            "love": 0.5,
            "surprise": 0.5
        }
    
    # Convert to lowercase for case-insensitive matching
    text = lyrics.lower()
    
    # Simple emotion lexicons
    emotion_words = {
        "joy": ["happy", "joy", "delight", "glad", "cheerful", "bliss", "fun", "enjoy", "smile", "laugh", 
                "wonderful", "great", "excellent", "amazing", "pleasure", "thrill", "beautiful", "excited", 
                "paradise", "celebration", "sunshine", "heaven", "dream", "perfect", "love"],
        
        "sadness": ["sad", "sorrow", "grief", "cry", "tear", "depressed", "depression", "unhappy", "miserable", 
                   "heartbreak", "lonely", "alone", "pain", "hurt", "suffer", "hopeless", "empty", "loss", 
                   "lost", "broken", "regret", "goodbye", "gone", "dark", "blue"],
        
        "anger": ["angry", "anger", "rage", "hate", "mad", "fury", "furious", "bitter", "irritated", "annoyed", 
                 "frustrated", "hostile", "fight", "violent", "destroy", "burn", "scream", "yell", "enemy", 
                 "revenge", "battle", "war", "attack", "kill", "hurt"],
        
        "fear": ["fear", "afraid", "scared", "terror", "panic", "horror", "nightmare", "worry", "anxious", 
                "dread", "threat", "danger", "escape", "hide", "run", "terrified", "nervous", "tremble", 
                "shiver", "scream", "dark", "unknown", "monster", "ghost", "death"],
        
        "love": ["love", "adore", "affection", "heart", "passion", "desire", "romance", "romantic", "kiss", 
               "embrace", "cuddle", "honey", "darling", "baby", "beautiful", "sweet", "dear", "forever", 
               "devoted", "intimate", "relationship", "together", "hold", "touch", "feel"],
        
        "surprise": ["surprise", "shock", "sudden", "unexpected", "wonder", "amazed", "astonished", "startled", 
                   "gasp", "discover", "realize", "revelation", "epiphany", "twist", "turn", "transform", 
                   "change", "new", "different", "strange", "unusual", "rare", "unbelievable", "wow", "whoa"]
    }
    
    # Count word matches
    counts = {emotion: 0 for emotion in emotion_words}
    total_matches = 0
    
    # Count occurrences of emotion words
    for emotion, words in emotion_words.items():
        for word in words:
            # Count exact matches with word boundaries
            matches = text.split().count(word)
            # Also check for words containing our emotion word
            for lyric_word in text.split():
                if word in lyric_word and word != lyric_word:
                    matches += 0.5  # Give partial weight to contained words
            
            counts[emotion] += matches
            total_matches += matches
    
    # Normalize scores between 0.1 and 0.9 (avoid extremes)
    if total_matches == 0:
        return {emotion: 0.5 for emotion in counts}
    
    # Calculate the proportion and scale
    max_count = max(counts.values()) if max(counts.values()) > 0 else 1
    scores = {}
    
    for emotion, count in counts.items():
        # Get a base score as the proportion of this emotion to the max emotion
        if max_count > 0:
            base_score = count / max_count
        else:
            base_score = 0.5
            
        # Scale to range between 0.1 and 0.9
        scores[emotion] = 0.1 + (base_score * 0.8)
    
    return scores
    
def plot_mood_radar(mood_dict):
    labels = list(mood_dict.keys())
    values = list(mood_dict.values())

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    values += values[:1]
    angles += angles[:1]  # to close the circle

    fig, ax = plt.subplots(figsize=(4, 4), subplot_kw=dict(polar=True))
    ax.plot(angles, values, linewidth=2)
    ax.fill(angles, values, alpha=0.3)
    ax.set_yticklabels([])
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)

    return fig

def logout_spotify():
    """Clear Spotify authentication cache and session state"""
    try:
        # Remove the Spotify token cache file
        if os.path.exists(".spotify_cache"):
            os.remove(".spotify_cache")
            
        # Clear relevant session state
        keys_to_clear = ['token_info', 'playlist_data', 'tracks_with_lyrics', 'agents', 'analysis_ready']
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
                
    except Exception as e:
        st.error(f"Error during logout: {e}")

def setup_autogen_agents(gemini_api_key):
    gemini_llm = OpenAI(api_key=gemini_api_key, base_url="https://generativelanguage.googleapis.com/v1beta/")

    playlist_agent_config = {
        "name": "playlist_agent",
        "llm_config": {
            "config_list": [
                {
                    "model": "gemini-2.0-flash-lite", 
                    "api_key": gemini_api_key, 
                    "base_url": "https://generativelanguage.googleapis.com/v1beta/"
                }
            ]
        },
        "system_message": """You are a Playlist Agent specialized in extracting and organizing data 
        from Spotify playlists. You analyze track listings, metadata, and provide well-structured 
        information about playlists. Focus on identifying trends, themes, and the overall purpose 
        or mood of the playlist."""
    }

    lyrics_agent_config = {
        "name": "lyrics_agent",
        "llm_config": {
            "config_list": [
                {
                    "model": "gemini-2.0-flash-lite", 
                    "api_key": gemini_api_key, 
                    "base_url": "https://generativelanguage.googleapis.com/v1beta/"
                }
            ]
        },
        "system_message": """You are a Lyrics Analysis Agent specialized in analyzing song lyrics. 
        You identify themes, sentiment, vocabulary complexity, and provide insightful analysis of 
        lyrical content. Look for patterns in language, emotional tones, and storytelling elements."""
    }

    playlist_agent = AssistantAgent(**playlist_agent_config)
    lyrics_agent = AssistantAgent(**lyrics_agent_config)

    user_proxy = UserProxyAgent(
        name="user_proxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=10,
        code_execution_config={"use_docker": False},
        llm_config=False,
        system_message="A user proxy agent that helps coordinate the conversation between specialized agents."
    )

    return {
        "playlist_agent": playlist_agent,
        "lyrics_agent": lyrics_agent,
        "user_proxy": user_proxy,
        "gemini_llm": gemini_llm
    }

# Analyze playlist or track with AutoGen
def analyze_playlist_with_agents(agents, playlist_data, tracks_with_lyrics, analysis_type):
    user_proxy = agents["user_proxy"]
    gemini_llm = agents["gemini_llm"]

    if analysis_type == "lyrics":
        target_agent = agents["lyrics_agent"]
        lyrics_data = ""
        for track in tracks_with_lyrics[:5]:
            if track.get('lyrics') and isinstance(track['lyrics'], str):
                lyrics_sample = track['lyrics'][:500] if len(track['lyrics']) > 500 else track['lyrics']
                lyrics_data += f"Song: {track['title']} by {track['artist']}\n"
                lyrics_data += f"Lyrics sample: {lyrics_sample}...\n\n"
        prompt = f"""
        Analyze the lyrics from this playlist named "{playlist_data.get('name', 'Unknown Playlist')}".
        
        Here are sample lyrics from the playlist:
        
        {lyrics_data}
        
        Please provide insights on:
        1. Common themes or topics across these songs
        2. Emotional tone/sentiment analysis
        3. Language complexity and vocabulary analysis
        4. Any standout lyrical patterns or techniques
        
        Format your analysis in a clear, structured way.
        """

    else:  # General playlist analysis
        target_agent = agents["playlist_agent"]
        artists = {}
        for track in tracks_with_lyrics:
            artists[track['artist']] = artists.get(track['artist'], 0) + 1
        top_artists = sorted(artists.items(), key=lambda x: x[1], reverse=True)[:5]
        prompt = f"""
        Analyze this Spotify playlist named "{playlist_data.get('name', 'Unknown Playlist')}" created by {playlist_data.get('owner', {}).get('display_name', 'Unknown')}.
        
        Playlist details:
        - Total tracks: {len(tracks_with_lyrics)}
        - Top artists: {top_artists}
        - Description: {playlist_data.get('description', 'No description')}
        
        Please provide:
        1. A summary of what this playlist seems to be about
        2. The musical coherence/theme based on the tracks and artists
        3. What might be the purpose or occasion for this playlist
        4. Any interesting patterns in the track selection
        
        Format your analysis in a clear, structured way.
        """

    response = None
    try:
        messages = [{"role": "user", "content": prompt}]
        response_obj = gemini_llm.chat.completions.create(model="gemini-2.0-flash-lite", messages=messages)
        if response_obj and response_obj.choices:
            response = response_obj.choices[0].message.content
        else:
            chat_result = user_proxy.initiate_chat(target_agent, message=prompt)
            for msg in chat_result.chat_history:
                if msg["role"] == "assistant":
                    response = msg["content"]
                    break
    except Exception as e:
        st.error(f"Error analyzing with AutoGen: {str(e)}")
        response = f"Analysis failed due to an error: {str(e)}"

    return response or "No analysis results available."

# Process tracks to get lyrics
def process_tracks(tracks, progress_bar=None):
    tracks_with_lyrics = []
    
    for i, item in enumerate(tracks):
        if not item.get("track"):
            continue
            
        track = item["track"]
        artist = track["artists"][0]["name"]
        title = track["name"]
        
        track_data = {
            "id": track["id"],
            "artist": artist,
            "title": title,
            "lyrics": get_lyrics_auto(artist, title) or "Lyrics not found",
            "preview_url": track.get("preview_url"),
            "album": track.get("album", {}).get("name", "Unknown Album")
        }
        
        tracks_with_lyrics.append(track_data)
        
        # Update progress if progress_bar provided
        if progress_bar:
            progress_bar.progress((i + 1) / len(tracks))
            
    return tracks_with_lyrics

# Display playlist info tab
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
    else:
        st.header(playlist_data["name"])
        st.write(f"Created by: {playlist_data.get('owner', {}).get('display_name', 'Unknown')}")
        st.write(f"Tracks: {playlist_data.get('tracks', {}).get('total', 0)}")
        
    # Run general playlist analysis with Autogen
    with st.spinner("Analyzing playlist with Autogen..."):
        analysis = analyze_playlist_with_agents(agents, playlist_data, tracks_with_lyrics, "general")
        st.subheader("Playlist Analysis (via AutoGen)")
        st.write(analysis)

    # Concatenate all lyrics
    all_lyrics = " ".join([
        track['lyrics'] for track in tracks_with_lyrics 
        if track.get('lyrics') and track['lyrics'] != "Lyrics not found" and isinstance(track['lyrics'], str)
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

# Display tracks list tab
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
            if track.get('lyrics') and track['lyrics'] != "Lyrics not found" and isinstance(track['lyrics'], str):
                try:
                    lyrics_lines = track['lyrics'].split("\n")
                    lyrics_preview = "\n".join(lyrics_lines[:10]) if len(lyrics_lines) > 10 else track['lyrics']
                    st.markdown(f"**Lyrics Preview:**\n```\n{lyrics_preview}\n```")
                except (AttributeError, TypeError) as e:
                    st.info(f"Error processing lyrics: {e}")
            else:
                st.info("Lyrics not found")

# Display track analyzer tab
def display_track_analyzer(playlist_data, tracks_with_lyrics, agents):
    st.subheader("🔍 Analyze Individual Song")

    available_tracks = [
        f"{t['title']} - {t['artist']}" for t in tracks_with_lyrics if t.get('lyrics') and t['lyrics'] != "Lyrics not found" and isinstance(t['lyrics'], str)
    ]

    if not available_tracks:
        st.warning("No tracks with lyrics available for analysis.")
        return

    selected_song = st.selectbox("Select a track with lyrics", available_tracks)
    
    if st.button("Analyze Song", key="analyze_song_button"): 
        # st.session_state['active_tab'] = 2

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

# Main app with OAuth flow
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

            if st.button("Analyze Playlist", key="oauth_analyze_button"):
                st.session_state['active_tab'] = 0
                with st.spinner("Fetching playlist data..."):
                    playlist_data = sp.playlist(selected_id)
                    tracks = sp.playlist_tracks(selected_id)
                    
                    # Process tracks to get lyrics and features
                    with st.spinner(f"Processing {playlist_data.get('tracks', {}).get('total', 0)} tracks..."):
                        progress_bar = st.progress(0)
                        tracks_with_lyrics = process_tracks(tracks['items'], progress_bar)
                    
                    # Set up AutoGen agents
                    with st.spinner("Setting up AutoGen agents..."):
                        agents = setup_autogen_agents(gemini_api_key)

                    # Save to session state for persistence between reruns
                    st.session_state['playlist_data'] = playlist_data
                    st.session_state['tracks_with_lyrics'] = tracks_with_lyrics
                    st.session_state['agents'] = agents
                    st.session_state['analysis_ready'] = True
                    st.rerun()

        else:
            st.error("Failed to connect to Spotify. Please check your authentication.")
    except Exception as e:
        st.error(f"Error in OAuth flow: {str(e)}")
        
# Main app with client credentials flow
def playlist_client_flow():
    # Input for Spotify playlist URL
    playlist_url = st.text_input("Enter Spotify Playlist URL", placeholder="https://open.spotify.com/playlist/...")
    
    if not playlist_url:
        st.info("Please enter a Spotify playlist URL to get started")
        return
    
    # Get API keys
    client_id = spotify_client_id
    client_secret = spotify_client_secret
    gemini_key = gemini_api_key
    
    if not client_id or not client_secret:
        st.error("Please provide Spotify API credentials in the sidebar")
        return
        
    if not gemini_key:
        st.error("Please provide a Gemini API key in the sidebar")
        return
    
    # Get Spotify token
    access_token = get_spotify_token(client_id, client_secret)
    if not access_token:
        st.error("Failed to authenticate with Spotify")
        return
    
    # Extract playlist ID
    try:
        playlist_id = extract_playlist_id(playlist_url)
    except Exception as e:
        st.error(f"Invalid playlist URL: {e}")
        return
    
    if st.button("Analyze Playlist", key="client_analyze_button"):
        st.session_state['active_tab'] = 0
        # Create analysis tabs
        tab1, tab2, tab3 = st.tabs(["Playlist Info", "Tracks List", "Analyze Track"])
        
        with st.spinner("Setting up AutoGen agents..."):
            agents = setup_autogen_agents(gemini_key)
        
        with st.spinner("Fetching playlist data..."):
            # Get playlist details
            playlist_data = get_playlist_details(access_token, playlist_id)
            if not playlist_data:
                st.error("Failed to fetch playlist details")
                return
                
            # Get tracks
            tracks = get_playlist_tracks(access_token, playlist_id)
            if not tracks:
                st.error("Failed to fetch playlist tracks")
                return
        
        # Process tracks to get lyrics and features
        with st.spinner(f"Processing {len(tracks)} tracks..."):
            progress_bar = st.progress(0)
            tracks_with_lyrics = process_tracks(tracks, progress_bar)
        
        # Save to session state for persistence between reruns
        st.session_state['playlist_data'] = playlist_data
        st.session_state['tracks_with_lyrics'] = tracks_with_lyrics
        st.session_state['agents'] = agents
        st.session_state['analysis_ready'] = True
        
        # Display in tabs
        with tab1:
            display_playlist_info(playlist_data, tracks_with_lyrics, agents)
        
        with tab2:
            display_tracks_list(tracks_with_lyrics)
        
        with tab3:
            display_track_analyzer(playlist_data, tracks_with_lyrics, agents)

# Main app function
def main():
    # Initialize session state for persistent data
    if 'analysis_ready' not in st.session_state:
        st.session_state['analysis_ready'] = False
    if 'active_tab' not in st.session_state:
        st.session_state['active_tab'] = 0

    # Check if we have analysis data from a previous run
    if st.session_state.get('analysis_ready'):
        # Display results using tabs
        tab1, tab2, tab3 = st.tabs(["Playlist Info", "Tracks List", "Track Analyzer"])
        
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
            
        if st.button("Start Over", key="start_over"):
            for key in ['analysis_ready', 'playlist_data', 'tracks_with_lyrics', 'agents', 'active_tab']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    
    else:
        # Let the user choose the method
        auth_method = st.radio(
            "Choose how you want to access playlists:",
            ["Login with your Spotify account", "Enter a Spotify playlist URL"],
            horizontal=True
        )
        
        if auth_method == "Login with your Spotify account":
            playlist_oauth_flow()
        else:
            # Use client credentials flow with playlist URL
            playlist_client_flow()

if __name__ == "__main__":
    main()
