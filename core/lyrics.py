### File: core/lyrics.py
import re
import jieba
import numpy as np
import streamlit as st
from wordcloud import WordCloud
from opencc import OpenCC
import requests

chinese_converter = OpenCC('s2t')

def get_lyrics_en(artist, title):
    url = f"https://api.lyrics.ovh/v1/{artist.strip().lower().replace(' ', '%20')}/{title.strip().lower().replace(' ', '%20')}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json().get("lyrics")
        return None
    except:
        return None

def get_lyrics_zh(artist, title):
    params = {"s": f"{title} {artist}", "type": 1, "limit": 1}
    try:
        res = requests.post("http://music.163.com/api/search/get", data=params)
        result = res.json()
        if not result.get("result", {}).get("songs"):
            return None
        song_id = result["result"]["songs"][0]["id"]
        lyric_url = f"http://music.163.com/api/song/lyric?os=pc&id={song_id}&lv=-1&kv=-1&tv=-1"
        lyric_res = requests.get(lyric_url)
        lyrics_json = lyric_res.json()
        raw_lyrics = lyrics_json.get("lrc", {}).get("lyric", '')
        if "纯音乐" in raw_lyrics:
            return None
        lyrics = re.sub(r'\[\s*\d{2}:\d{2}(\.\d+)?\s*\]', '', raw_lyrics)
        filtered_lines = [line.strip() for line in lyrics.splitlines() if line.strip() and not re.match(r'(作词|作曲|编曲|制作人).*', line)]
        simplified_lyric = ' '.join(filtered_lines)
        traditional_lyric = chinese_converter.convert(simplified_lyric).replace("咪", "夢")
        return traditional_lyric
    except:
        return None

def get_lyrics_auto(artist, title):
    return get_lyrics_en(artist, title) or get_lyrics_zh(artist, title)

def process_tracks(tracks, progress_bar=None):
    tracks_with_lyrics = []
    for i, item in enumerate(tracks):
        if not item.get("track"):
            continue
        track = item["track"]
        lyrics = get_lyrics_auto(track["artists"][0]["name"], track["name"])
        tracks_with_lyrics.append({
            "id": track["id"],
            "artist": track["artists"][0]["name"],
            "title": track["name"],
            "lyrics": lyrics or "Lyrics not found",
            "preview_url": track.get("preview_url"),
            "album": track.get("album", {}).get("name", "Unknown Album")
        })
        if progress_bar:
            progress_bar.progress((i + 1) / len(tracks))
    return tracks_with_lyrics

def generate_wordcloud(text):
    words = jieba.cut(text)
    return WordCloud(
        width=800, height=400, background_color='white', font_path="TaipeiSansTCBeta-Regular.ttf"
    ).generate(" ".join(words))

def generate_wordcloud_for_song(text):
    words = jieba.cut(text)
    return WordCloud(
        width=268, height=229, background_color='white' , font_path="TaipeiSansTCBeta-Regular.ttf"
    ).generate(" ".join(words))

def compute_sentiment_scores(lyrics):
    if not lyrics:
        return {e: 0.5 for e in ["joy", "sadness", "anger", "fear", "love", "surprise"]}
    text = lyrics.lower()
    emotion_words = {
        "joy": ["happy", "joy", "delight"],
        "sadness": ["sad", "cry", "tear"],
        "anger": ["angry", "rage", "hate"],
        "fear": ["fear", "scared", "panic"],
        "love": ["love", "adore", "kiss"],
        "surprise": ["surprise", "shock", "amazed"]
    }
    counts = {e: 0 for e in emotion_words}
    for e, words in emotion_words.items():
        for w in words:
            counts[e] += text.split().count(w)
    max_count = max(counts.values()) or 1
    return {e: 0.1 + 0.8 * (c / max_count) for e, c in counts.items()}

def plot_mood_radar(mood_dict):
    import matplotlib.pyplot as plt
    labels = list(mood_dict.keys())
    values = list(mood_dict.values())
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    values += values[:1]
    angles += angles[:1]
    fig, ax = plt.subplots(figsize=(4, 4), subplot_kw=dict(polar=True))
    ax.plot(angles, values, linewidth=2)
    ax.fill(angles, values, alpha=0.3)
    ax.set_yticklabels([])
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    return fig