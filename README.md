# 🎵 Music Assistant

This project uses AutoGen with Gemini Pro to manage user's playlist from spotify. 

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://autogenlyrics-krgsknod3xugbb6mghgokr.streamlit.app/)

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

4. **Replace your APIs**
   Update the autogen_spotify_app.py file with your Spotify API keys.
   Update the config.json file with your Gemini API key. Make sure that your API key is compatible with the Gemini model being used.

5. **Run the script**

```bash
streamlit run app.py
```
