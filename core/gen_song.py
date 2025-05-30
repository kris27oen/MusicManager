import threading
import subprocess
import time
import os
import json
import socket
from flask import Flask, request, jsonify
import streamlit as st
import requests

spotify_client_id = "b9e0979d54c449d4a1b7f23a1be1d329"
spotify_client_secret = "03559d2dc6b643e8af412d5930ee4ec2"
suno_api_key = "b05e6e742e5b2a4043bd9c32bed4c57f"

flask_app = Flask(__name__)

def find_available_port(start=5050):
    port = start
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
            port += 1

callback_port = find_available_port()

@flask_app.route("/callback", methods=["POST"])
def receive_callback():
    try:
        data = request.json
        os.makedirs("data", exist_ok=True)

        if os.path.exists("data/music.json"):
            try:
                existing_data = json.load(open("data/music.json", "r", encoding="utf-8"))
                if "data" in existing_data and "data" in existing_data["data"]:
                    if "data" in data and "data" in data["data"]:
                        existing_data["data"]["data"].extend(data["data"]["data"])
                        data = existing_data
            except Exception as e:
                st.error(f"Error merging data: {str(e)}")

        with open("data/music.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        with open("data/music_updated.flag", "w") as f:
            f.write(str(time.time()))

        return jsonify({"code": 200, "msg": "Callback received"})
    except Exception as e:
        return jsonify({"code": 500, "msg": f"Error: {str(e)}"})

def run_flask():
    flask_app.run(host="0.0.0.0", port=callback_port)

def start_callback_server():
    threading.Thread(target=run_flask, daemon=True).start()

def start_ngrok():
    try:
        tunnels = requests.get("http://localhost:4040/api/tunnels").json().get("tunnels", [])
        for t in tunnels:
            if t.get("proto") == "https":
                return t["public_url"] + "/callback"
    except:
        pass

    ngrok_path = "/usr/local/bin/ngrok"
    subprocess.Popen([ngrok_path, "http", str(callback_port)], stdout=subprocess.DEVNULL)
    time.sleep(2)
    try:
        tunnels = requests.get("http://localhost:4040/api/tunnels").json().get("tunnels", [])
        for t in tunnels:
            if t.get("proto") == "https":
                return t["public_url"] + "/callback"
    except:
        pass

    return f"http://127.0.0.1:{callback_port}/callback"

def auto_rerun_on_file_change():
    flag_path = "data/music_updated.flag"
    if os.path.exists(flag_path):
        mtime = os.path.getmtime(flag_path)
        last = st.session_state.get("music_flag_mtime", 0)
        if mtime != last:
            st.session_state["music_flag_mtime"] = mtime
            os.remove(flag_path)
            st.experimental_set_query_params(music_mtime=mtime)

def gen_song_ui():
    st.header("Create Music with Suno")

    auto_rerun_on_file_change()
    start_callback_server()
    callback_url = start_ngrok()
    st.markdown(f"**Callback URL:** `{callback_url}`")

    if st.session_state.get("generation_in_progress", False):
        st.info("⏳ Music generation in progress... Please wait for callback.")

        if os.path.exists("data/music.json"):
            mtime = os.path.getmtime("data/music.json")
            last = st.session_state.get("last_music_check", 0)
            if mtime > last:
                st.session_state["generation_in_progress"] = False
                st.session_state["active_tab"] = 1
                st.session_state["last_music_check"] = mtime
                st.experimental_rerun()

    with st.form("music_form"):
        prompt = st.text_area("Prompt (idea or lyrics)")
        style = st.text_input("Music Style (e.g., Jazz, Pop)")
        title = st.text_input("Track Title")
        model_sel = st.selectbox("Model Version", ["V3_5", "V4", "V4_5"])
        instrumental = st.checkbox("Instrumental Only", value=False)
        neg_styles = st.text_input("Exclude Styles (e.g., Heavy Metal)")

        submitted = st.form_submit_button("Generate Music")
        if submitted:
            if not prompt:
                st.error("Please provide a prompt!")
            else:
                payload = {
                    "prompt": prompt,
                    "style": style,
                    "title": title or "Untitled",
                    "customMode": True,
                    "instrumental": instrumental,
                    "model": model_sel,
                    "negativeTags": neg_styles,
                    "callBackUrl": callback_url
                }
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {suno_api_key}"
                }

                try:
                    with st.spinner("Sending generation request..."):
                        r = requests.post("https://apibox.erweima.ai/api/v1/generate",
                                          headers=headers, json=payload)

                    if r.status_code == 200:
                        st.success("Music generation request sent! Waiting for callback...")
                        st.session_state["generation_in_progress"] = True
                        st.session_state["last_music_check"] = time.time()
                    else:
                        st.error(f"Error {r.status_code}: {r.text}")
                        st.json(r.json())
                except Exception as e:
                    st.error(f"Request failed: {str(e)}")

def gen_song_player_ui():
    st.header("Your Generated Music")
    path = "data/music.json"
    if os.path.exists(path):
        try:
            data = json.load(open(path, encoding="utf-8"))
            music_data = data.get("data", {}).get("data", [])

            if not music_data:
                st.info("No music data yet.")
            else:
                for i, t in enumerate(music_data, 1):
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.subheader(f"{i}. {t.get('title', 'Untitled')}")
                        img = t.get("image_url", "").strip()
                        if img:
                            st.image(img, width=200)
                    with col2:
                        audio_url = t.get("audio_url") or t.get("stream_audio_url", "")
                        if audio_url:
                            st.audio(audio_url)
                        else:
                            st.info("Audio not ready yet.")
                        st.markdown(f"**Prompt:** {t.get('prompt', 'N/A')}")
                        st.markdown(f"**Style:** {t.get('style', 'N/A')}")
        except Exception as e:
            st.error(f"Error reading music data: {str(e)}")
    else:
        st.info("No music generated yet. Use the Music Creator tab to create music.")
