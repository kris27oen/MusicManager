import streamlit as st
import json

def render_sidebar():
    with st.sidebar:
        st.header("Settings")
        st.selectbox("Language", ["English", "繁體中文"], index=0)

        with st.expander("API Configuration"):
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