import os
import streamlit as st
import networkx as nx
from pyvis.network import Network
from collections import defaultdict

def cluster_tracks(tracks_with_lyrics, cluster_by="genre"):
    """
    Clusters tracks based on the selected attribute.
    Args:
        tracks_with_lyrics: list of track dicts
        cluster_by: one of 'genre', 'mood', 'decade', 'event'
    Returns:
        clusters: dict mapping cluster value -> list of track IDs
        track_attrs: dict mapping track id -> attribute dict
    """

    clusters = defaultdict(list)
    track_attrs = {}

    for t in tracks_with_lyrics:
        tid = t.get("id", t.get("title"))
        title = t.get("title")
        artist = t.get("artist")
        lyrics = t.get("lyrics")

        # Determine attribute value based on cluster_by
        if cluster_by == "mood":
            # Dummy mood heuristic, replace with your sentiment scoring if needed
            attr_value = "happy" if "love" in lyrics.lower() else "neutral"
        elif cluster_by == "genre":
            attr_value = t.get("genre")
        elif cluster_by == "decade":
            release_date = t.get("release_date", None)
            if release_date and len(release_date) >= 4:
                attr_value = release_date[:3] + "0s"
            else:
                attr_value = "Unknown"
        elif cluster_by == "event":
            attr_value = t.get("event", "None")
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
    cluster_options = ["genre", "mood", "decade", "event"]
    cluster_by = st.selectbox("Select clustering criterion", cluster_options)

    if not tracks_with_lyrics:
        st.info("Please load a playlist first to see music clusters.")
        return

    clusters, track_attrs = cluster_tracks(tracks_with_lyrics, cluster_by=cluster_by)
    G = build_track_graph(clusters, track_attrs)
    html = visualize_graph_networkx(G)
    st.markdown(f"### Clustered by: {cluster_by.capitalize()}")
    st.components.v1.html(html, height=600, scrolling=True)

