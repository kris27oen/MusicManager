import os
import re
import streamlit as st
import networkx as nx
from pyvis.network import Network
from collections import defaultdict

def cluster_tracks(tracks_with_lyrics, cluster_by="genre"):
    """
    Clusters tracks based on the selected attribute.
    Args:
        tracks_with_lyrics: list of track dicts
        cluster_by: one of 'genre', 'mood', 'event'
    Returns:
        clusters: dict mapping cluster value -> list of track IDs
        track_attrs: dict mapping track id -> attribute dict
    """
    clusters = defaultdict(list)
    track_attrs = {}

    def count_keyword_matches(lyrics, keywords):
        return sum(len(re.findall(rf'\b{re.escape(word)}\b', lyrics)) for word in keywords)
    
    mood_keywords = {
        'happy': ['happy', 'joy', 'smile', 'sunshine', 'celebrate', 'yay', 'yay!', 'fun'],
        'sad': ['cry', 'sad', 'tears', 'alone', 'broken', 'missing', 'goodbye'],
        'energetic': ['party', 'fire', 'jump', 'run', 'crazy', 'nonstop', 'go', 'burn'],
        'calm': ['calm', 'peace', 'gentle', 'breeze', 'dream', 'soft', 'slow', 'quiet'],
        'angry': ['hate', 'rage', 'scream', 'fight', 'burn', 'war', 'revenge']
    }

    event_keywords = {
        'Party': ['party', 'dance', 'club', 'celebrate', 'lights', 'disco', 'drink'],
        'Romance': ['love', 'heart', 'kiss', 'romance', 'darling', 'together', 'baby'],
        'Workout': ['run', 'push', 'sweat', 'lift', 'strong', 'fit', 'power', 'move'],
        'Relaxation': ['relax', 'calm', 'peace', 'easy', 'chill', 'breathe', 'slow'],
        'Travel': ['travel', 'journey', 'road', 'fly', 'away', 'adventure', 'explore']
    }

    def determine_genre(track):
        for key in ("genres", "track_genre", "artist_genres"):
            candidate = track.get(key)
            if candidate:
                if isinstance(candidate, list) and len(candidate) > 0:
                    return candidate[0]
                elif isinstance(candidate, str):
                    return candidate

        danceability   = float(track.get("danceability", 0.5))
        energy         = float(track.get("energy", 0.5))
        valence        = float(track.get("valence", 0.5))
        tempo          = float(track.get("tempo", 120))
        instrumental   = float(track.get("instrumentalness", 0))
        acousticness   = float(track.get("acousticness", 0))
        loudness       = float(track.get("loudness", -10))

        if instrumental > 0.6 and energy > 0.6:
            return "Electronic"
        if acousticness > 0.7 and energy < 0.5:
            return "Acoustic"
        if danceability > 0.7 and energy > 0.7 and tempo > 115:
            return "Dance/Pop"
        if energy > 0.75 and loudness > -6 and tempo > 120:
            return "Rock"
        if danceability > 0.6 and 80 < tempo < 120 and energy > 0.65:
            return "Hip-Hop"
        if energy < 0.5 and acousticness > 0.4:
            return "Indie/Alternative"
        if energy < 0.6 and valence > 0.5 and acousticness < 0.5:
            return "R&B/Soul"
        if danceability > 0.4 and valence > 0.4 and energy > 0.4:
            return "Pop"

        return "Other"

    for t in tracks_with_lyrics:
        tid = t.get("id", t.get("title"))
        title = t.get("title", "Unknown Title")
        artist = t.get("artist", "Unknown Artist")
        lyrics = t.get("lyrics", "").lower()

        # Determine attribute value based on cluster_by
        if cluster_by == "mood":
            mood_scores = {
                mood: count_keyword_matches(lyrics, keywords)
                for mood, keywords in mood_keywords.items()
            }
            attr_value = max(mood_scores.items(), key=lambda x: x[1])[0] if any(mood_scores.values()) else "neutral"

        elif cluster_by == "genre":
            attr_value = determine_genre(t)

        elif cluster_by == "event":
            event_scores = {
                event: count_keyword_matches(lyrics, keywords)
                for event, keywords in event_keywords.items()
            }
            attr_value = max(event_scores.items(), key=lambda x: x[1])[0] if any(event_scores.values()) else "Other"

        else:
            attr_value = "Unknown"

        clusters[attr_value].append(tid)
        track_attrs[tid] = {
            "title": title,
            "artist": artist,
            cluster_by: attr_value
        }

    return clusters, track_attrs

def build_track_graph(clusters, track_attrs):
    """
    Build NetworkX graph connecting tracks that share the same cluster attribute.
    """
    G = nx.Graph()

    # Add nodes
    for tid, attrs in track_attrs.items():
        G.add_node(tid, label=attrs["title"], artist=attrs["artist"])

    # Connect tracks in the same cluster
    for attr_value, track_ids in clusters.items():
        for i, tid1 in enumerate(track_ids):
            for tid2 in track_ids[i+1:]:
                if G.has_edge(tid1, tid2):
                    G[tid1][tid2]["weight"] += 1
                else:
                    G.add_edge(tid1, tid2, weight=1)

    return G

def visualize_graph_networkx(G, height="600px", width="100%"):
    net = Network(height=height, width=width, notebook=False)

    net.from_nx(G)

    for node in net.nodes:
        node['title'] = f"{node['label']} - Artist: {G.nodes[node['id']]['artist']}"
        node['shape'] = 'dot'
        node['size'] = 15

    net.show_buttons(filter_=['physics'])
    net.repulsion(node_distance=150, central_gravity=0.2, spring_length=100, spring_strength=0.05)

    # Save to temporary html file and read content for embedding
    parent_folder = os.path.dirname(os.path.abspath(__file__))
    if not os.path.exists("/tmp"):
        os.makedirs("/tmp")
    path = os.path.join(parent_folder, "/tmp/track_graph.html")
    net.save_graph(path)
    with open(path, 'r', encoding='utf-8') as f:
        html = f.read()
    return html

def render_music_clusters_graph(tracks_with_lyrics):
    st.subheader("Music Clusters Visualization")
    cluster_options = ["genre", "mood", "event"]
    cluster_by = st.selectbox("Select clustering criterion", cluster_options)

    if not tracks_with_lyrics:
        st.info("Please load a playlist first to see music clusters.")
        return

    clusters, track_attrs = cluster_tracks(tracks_with_lyrics, cluster_by=cluster_by)
    G = build_track_graph(clusters, track_attrs)
    html = visualize_graph_networkx(G)
    st.markdown(f"### Clustered by: {cluster_by.capitalize()}")
    st.components.v1.html(html, height=600, scrolling=True)

