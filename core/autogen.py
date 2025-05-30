### File: core/autogen.py
from openai import OpenAI
from autogen import AssistantAgent, UserProxyAgent
import streamlit as st

def setup_autogen_agents(gemini_api_key):
    gemini_llm = OpenAI(api_key=gemini_api_key, base_url="https://generativelanguage.googleapis.com/v1beta/")

    playlist_agent = AssistantAgent(
        name="playlist_agent",
        llm_config={"config_list": [{"model": "gemini-2.0-flash-lite", "api_key": gemini_api_key, "base_url": "https://generativelanguage.googleapis.com/v1beta/"}]},
        system_message="""You are a Playlist Agent specializing in organizing data from Spotify playlists."""
    )

    lyrics_agent = AssistantAgent(
        name="lyrics_agent",
        llm_config={"config_list": [{"model": "gemini-2.0-flash-lite", "api_key": gemini_api_key, "base_url": "https://generativelanguage.googleapis.com/v1beta/"}]},
        system_message="""You are a Lyrics Agent for analyzing lyrics, emotions, and themes."""
    )

    user_proxy = UserProxyAgent(
        name="user_proxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=10,
        code_execution_config={"use_docker": False},
        llm_config=False,
        system_message="User proxy coordinating specialized agents."
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
        lyrics_data = "\n\n".join([
            f"Song: {t['title']} by {t['artist']}\nLyrics sample: {t['lyrics'][:500]}..." for t in tracks_with_lyrics[:5]
        ])
        prompt = f"""
            Analyze the lyrics from playlist \"{playlist_data.get('name')}\".
            {lyrics_data}
            Provide insights on themes, sentiment, and language use.
        """
    else:
        target_agent = agents["playlist_agent"]
        top_artists = sorted({t['artist']:0 for t in tracks_with_lyrics}.keys())[:5]
        prompt = f"""
            Analyze the Spotify playlist \"{playlist_data.get('name')}\" by {playlist_data.get('owner', {}).get('display_name')}.
            Top artists: {top_artists}
            Description: {playlist_data.get('description')}
            Summarize its theme and purpose.
        """

    try:
        messages = [{"role": "user", "content": prompt}]
        response_obj = gemini_llm.chat.completions.create(model="gemini-2.0-flash-lite", messages=messages)
        if response_obj and response_obj.choices:
            return response_obj.choices[0].message.content
        chat_result = user_proxy.initiate_chat(target_agent, message=prompt)
        for msg in chat_result.chat_history:
            if msg["role"] == "assistant":
                return msg["content"]
    except Exception as e:
        st.error(f"AutoGen analysis failed: {str(e)}")
    return "No analysis available."