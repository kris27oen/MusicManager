import re
import streamlit as st
from core.autogen import setup_autogen_agents
from core.playback import (
    search_tracks, add_track_to_queue, add_track_to_playlist,
    create_playlist, play_playlist, pause_playback, next_track, get_spotify_client, play_track 
)

def is_song_request(text):
    keywords = ["play", "queue", "add", "點歌", "放", "我想聽", "來一首"]
    playlist_keywords = ["playlist", "歌單", "播放清單", "加入歌單", "建立歌單"]
    return any(k in text.lower() for k in keywords) and not any(p in text.lower() for p in playlist_keywords)

def is_playback_control_request(text):
    keywords = [
        "play music", "pause", "resume", "stop", "next", "skip",
        "上一首", "下一首", "暫停", "繼續", "停止"
    ]
    return any(k in text.lower() for k in keywords)

def render_pending_song_results():
    if st.session_state.get("pending_song_results"):
        for track in st.session_state["pending_song_results"]:
            title = track["name"]
            artist = ", ".join([a["name"] for a in track["artists"]])
            uri = track["uri"]
            if st.button(f"🎵 Add to Queue: {title} - {artist}", key=f"queue-{uri}"):
                access_token = st.session_state.get("access_token")
                result = add_track_to_queue(access_token, uri)
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": f"✅ Queued: {title} - {artist}\n{result}"
                })
                st.session_state["pending_song_results"] = None
                st.session_state["song_offset"] = 0
                st.experimental_rerun()

        if st.button("▶️ Show more", key="song-more"):
            st.session_state["song_offset"] = st.session_state.get("song_offset", 0) + 10
            access_token = st.session_state.get("access_token")
            query = st.session_state.get("last_song_query")
            if query and access_token:
                st.session_state["pending_song_results"] = search_tracks(access_token, query, limit=10, offset=st.session_state["song_offset"])
            st.experimental_rerun()

        if st.button("❌ None of these", key="song-none"):
            st.session_state["pending_song_results"] = None
            st.session_state["song_offset"] = 0
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": "Okay! You can enter a new song or artist to try again."
            })
            st.experimental_rerun()
        return True
    return False

def process_song_request(user_input):
    access_token = st.session_state.get("access_token")
    if not access_token:
        return "⚠️ Please log in to Spotify first to queue a song."

    st.session_state["last_song_query"] = user_input
    st.session_state["song_offset"] = 0
    results = search_tracks(access_token, user_input, limit=10, offset=0)
    if results:
        st.session_state.pending_song_results = results
        st.session_state.chat_history.append({"role": "assistant", "content": "🎶 Select a song below to add to your playback queue:"})
        st.experimental_rerun()
    return "❌ No songs found for your request."

def process_playback_control(user_input):
    access_token = st.session_state.get("access_token")
    if not access_token:
        return "⚠️ Please log in to Spotify first to control playback."

    text = user_input.lower()

    if "play music" in text or "resume" in text or "繼續" in text:
        return play_track(access_token)
    elif "pause" in text or "暫停" in text or "stop" in text or "停止" in text:
        return pause_playback(access_token)
    elif "next" in text or "skip" in text or "下一首" in text:
        return next_track(access_token)
    else:
        return "Playback command not recognized."

def music_chatbot_ui(agents, tracks_with_lyrics):
    sp = get_spotify_client()
    access_token = sp.auth_manager.get_access_token(as_dict=False)
    st.session_state["access_token"] = access_token
    
    with st.container(key="chat_container"):
        st.subheader("💬 Chatbot")

        # Initialize session state for chat
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        if "chat_input_key" not in st.session_state:
            st.session_state.chat_input_key = 0

        def send_message():
            user_input = st.session_state.get(f"chat_input_{st.session_state.chat_input_key}", "").strip()
            if user_input:
                st.session_state.chat_history.append({"role": "user", "content": user_input})

                if is_playback_control_request(user_input):
                    reply = process_playback_control(user_input)
                elif is_song_request(user_input):
                    reply = process_song_request(user_input)
                else:
                    # Original chatbot conversation logic
                    context_messages = st.session_state.chat_history[-6:]
                    prompt = "\n".join(f"{msg['role']}: {msg['content']}" for msg in context_messages)

                    if tracks_with_lyrics and agents:
                        system_message = (
                            "You are a helpful and friendly music assistant chatbot. "
                            "You can recommend music, generate lyrics based on user mood or ideas, "
                            "analyze user playlists, and chat casually about music. "
                            "Avoid repeating songs already in the playlist. "
                            "IMPORTANT: Only respond with plain text, no HTML or special formatting. "
                            f"Here is the current playlist: {tracks_with_lyrics}. "
                        )
                    else:
                        system_message = (
                            "You are a helpful and friendly music assistant chatbot. "
                            "You can recommend music, generate lyrics based on user mood or ideas, "
                            "discuss music genres, artists, and chat casually about music. "
                            "The user hasn't loaded a playlist yet, so focus on general music conversation, "
                            "recommendations, and music-related topics. "
                            "IMPORTANT: Only respond with plain text, no HTML or special formatting. "
                        )

                    try:
                        if agents and "gemini_llm" in agents:
                            gemini_llm = agents["gemini_llm"]
                            messages = [
                                {"role": "system", "content": system_message},
                                {"role": "user", "content": prompt}
                            ]
                            response_obj = gemini_llm.chat.completions.create(
                                model="gemini-2.0-flash-lite",
                                messages=messages
                            )
                            reply = response_obj.choices[0].message.content if response_obj and response_obj.choices else "Sorry, I couldn't generate a response."
                        else:
                            reply = (
                                "Hi! I'm your music assistant. I can help you discover new music, "
                                "discuss artists and genres, or chat about anything music-related. "
                                "Load a playlist to unlock advanced features like playlist analysis! "
                                "What would you like to talk about?"
                            )
                    except Exception as e:
                        reply = f"Error in chatbot: {str(e)}"

                st.session_state.chat_history.append({"role": "assistant", "content": reply})
                st.session_state.chat_input_key += 1

        # Render pending song selection buttons first if exist
        if render_pending_song_results():
            return

        # Chat display container
        with st.container(key="chat_container_display"):
            with st.container(key="chat_display", height=350):
                if st.session_state.chat_history:
                    for msg in st.session_state.chat_history[-20:]:
                        if msg["role"] == "user":
                            st.markdown(
                                f'<div class="user-message"><strong>You:</strong> {msg["content"]}</div>',
                                unsafe_allow_html=True
                            )
                        else:
                            st.markdown(
                                f'<div class="assistant-message"><strong>Assistant:</strong> {msg["content"]}</div>',
                                unsafe_allow_html=True
                            )
                else:
                    st.markdown(
                        '<div style="text-align: center; color: #888; padding: 20px;">Start a conversation!</div>',
                        unsafe_allow_html=True
                    )

            # Chat input box container
            with st.container(key="chat_input_container"):
                st.text_input(
                    "",
                    placeholder="Ask Chatbot...",
                    key=f"chat_input_{st.session_state.chat_input_key}",
                    on_change=send_message,
                    label_visibility="collapsed"
                )

    # Preserve original CSS exactly as you requested
    st.markdown("""
        <style>
        .st-key-chat_container {
            position: fixed;
            bottom: 20px;
            background-color: #262730;
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            padding: 15px;
            padding-top: 5px;
            overflow-y: none;
            margin-left: 20px;
        }
        .user-message {
            background-color: rgba(255, 255, 255, 0.1);
            padding: 10px;
            border-radius: 8px;
            margin: 8px 20px 8px 0;
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: white;
        }
        .assistant-message {
            background-color: rgba(255, 255, 255, 0.05);
            padding: 10px;
            border-radius: 8px;
            margin: 8px 0 8px 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: white;
        }
        .st-key-chat_container_display [data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #0E1117;   
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 8px;  
        }
        </style>
    """, unsafe_allow_html=True)
