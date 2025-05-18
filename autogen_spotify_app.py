import streamlit as st
import requests
import re
import time
import autogen
import google.generativeai as genai
from typing import Dict, List, Optional, Union, Any
import os
import json
import pandas as pd
import matplotlib.pyplot as plt
from gemini_adapter import GeminiLLM
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
from opencc import OpenCC

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
        spotify_client_id = st.text_input("Spotify Client ID", value="YOUR_API_KEY", type="password")
        spotify_client_secret = st.text_input("Spotify Client Secret", value="YOUR_API_KEY", type="password")
        gemini_api_key = st.text_input("Gemini API Key", type="password")
        
        if st.button("Save API Keys"):
            st.success("API keys saved!")
            
            # Save Gemini API key to config file
            if gemini_api_key:
                config = {
                    "config_list": [
                        {
                            "model": "gemini-1.5-pro-001",
                            "api_key": gemini_api_key
                        }
                    ]
                }
                
                with open("config.json", "w") as f:
                    json.dump(config, f, indent=4)

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


def setup_autogen_agents(gemini_api_key):
    gemini_llm = GeminiLLM(api_key=gemini_api_key)

    playlist_agent_config = {
        "name": "playlist_agent",
        "llm_config": {
            "config_list": [{"model": "gemini-1.5-pro-001", "api_key": gemini_api_key}],
            "cache_seed": 42
        },
        "system_message": """You are a Playlist Agent specialized in extracting and organizing data 
        from Spotify playlists. You analyze track listings, metadata, and provide well-structured 
        information about playlists. Focus on identifying trends, themes, and the overall purpose 
        or mood of the playlist."""
    }

    lyrics_agent_config = {
        "name": "lyrics_agent",
        "llm_config": {
            "config_list": [{"model": "gemini-1.5-pro-001", "api_key": gemini_api_key}],
            "cache_seed": 42
        },
        "system_message": """You are a Lyrics Analysis Agent specialized in analyzing song lyrics. 
        You identify themes, sentiment, vocabulary complexity, and provide insightful analysis of 
        lyrical content. Look for patterns in language, emotional tones, and storytelling elements."""
    }

    playlist_agent = autogen.AssistantAgent(**playlist_agent_config)
    lyrics_agent = autogen.AssistantAgent(**lyrics_agent_config)

    user_proxy = autogen.UserProxyAgent(
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

def analyze_playlist_with_agents(agents, playlist_data, tracks_with_lyrics, analysis_type):
    user_proxy = agents["user_proxy"]
    gemini_llm = agents["gemini_llm"]

    if analysis_type == "lyrics":
        target_agent = agents["lyrics_agent"]
        lyrics_data = ""
        for track in tracks_with_lyrics[:5]:
            lyrics_data += f"Song: {track['title']} by {track['artist']}\n"
            lyrics_data += f"Lyrics sample: {track['lyrics'][:500]}...\n\n"
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
        response_obj = gemini_llm.create(messages=messages)
        if response_obj and "choices" in response_obj:
            response = response_obj["choices"][0]["message"]["content"]
        else:
            chat_result = user_proxy.initiate_chat(target_agent, message=prompt)
            for msg in chat_result.chat_history:
                if msg["role"] == "assistant":
                    response = msg["content"]
                    break
    except Exception as e:
        st.error(f"Error analyzing with AutoGen: {str(e)}")
        response = f"Analysis failed due to an error: {str(e)}"

    return response

# Main app functionality
def main():
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
    
    # Create analysis tabs
    tab1, tab2, tab3 = st.tabs(["Playlist Info", "Lyrics Analysis", "Tracks"])
    
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
    tracks_with_lyrics = []
    
    with st.spinner(f"Processing {len(tracks)} tracks..."):
        progress_bar = st.progress(0)
        
        for i, item in enumerate(tracks):
            if not item.get("track"):
                continue
                
            track = item["track"]
            track_id = track["id"]
            artist = track["artists"][0]["name"]
            title = track["name"]
            
            # Get lyrics (if available)
            lyrics = get_lyrics_auto(artist, title)
            
            tracks_with_lyrics.append({
                "id": track_id,
                "artist": artist,
                "title": title,
                "lyrics": lyrics if lyrics else "Lyrics not found",
                "preview_url": track.get("preview_url"),
                "album": track.get("album", {}).get("name", "Unknown Album")
            })
            
            # Update progress
            progress_bar.progress((i + 1) / len(tracks))
    
    # Display playlist information in Tab 1
    with tab1:
        if playlist_data.get("images"):
            col1, col2 = st.columns([1, 3])
            with col1:
                st.image(playlist_data["images"][0]["url"], width=200)
            with col2:
                st.header(playlist_data["name"])
                st.write(f"Created by: {playlist_data.get('owner', {}).get('display_name', 'Unknown')}")
                st.write(f"Tracks: {playlist_data.get('tracks', {}).get('total', 0)}")
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
    
    # Display lyrics analysis in Tab 2
    with tab2:
        with st.spinner("Analyzing lyrics with Autogen..."):
            st.subheader("Lyrical Analysis (via AutoGen)")
            lyrics_count = sum(1 for track in tracks_with_lyrics if track["lyrics"] != "Lyrics not found")
            st.write(f"Found lyrics for {lyrics_count} out of {len(tracks_with_lyrics)} tracks")
            
            if lyrics_count > 0:
                lyrics_analysis = analyze_playlist_with_agents(agents, playlist_data, tracks_with_lyrics, "lyrics")
                st.write(lyrics_analysis)
            else:
                st.warning("No lyrics found to analyze")
    
    # Display tracks in Tab 3
    with tab3:
        st.subheader("Tracks in Playlist")
        
        for i, track in enumerate(tracks_with_lyrics):
            with st.expander(f"{i+1}. {track['title']} - {track['artist']}"):
                cols = st.columns(1)
                
                with cols[0]:
                    if track['lyrics'] != "Lyrics not found":
                        # Display first few lines of lyrics
                        lyrics_preview = "\n".join(track['lyrics'].split("\n")[:10])
                        st.markdown(f"**Lyrics Preview:**\n```\n{lyrics_preview}\n```")
                    else:
                        st.info("Lyrics not found")

if __name__ == "__main__":
    main()