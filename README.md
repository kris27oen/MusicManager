# 🎵 Music Assistant

This project uses AutoGen with Gemini Pro to manage user's playlist from spotify. 

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://musicmanager.streamlit.app/)

## 🚀 Features
- Streamlit UI-based interaction
- Integrate chatbot and song analyzer with Gemini model via Autogen API
- Spotify authentication (Login) with user's account to access their playlist
- Playlist analysis with word cloud and mood graph
- Specific song analysis with word cloud and mood graph
- Chatbot as an music assistant that can recommend music and QnA interaction
- Interactive song web cluster like graph database connection

## 🛠️ Setup

1. **Clone the repository**

```bash
git clone https://github.com/gelicheng/autogen_lyrics.git
cd autogen_lyrics
```

2. **Create and activate a virtual environment**

```bash
python -m venv autogen-env
autogen-env\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Run the script**

```bash
streamlit run app.py
```

## Problem you might encounter during Spotify Authorization Process (Login)

1. When you first open streamlit, you have to always place in your Spotify Client ID, Spotify Client Secret, Gemini API Key.
2. Click Login and it will redirect you for authorization.
3. After authorization, you will have to insert your APIs configuration once more as it refresh your API on every authorization.
4. Click login again, but return from teh authorization page, you should be able to see your playlist by then.
5. Remember to open your spotify and play the current song to open the jukebox. Also, turn your playlist to public so that the chatbot can see it.
6. Enjoy !!! 
