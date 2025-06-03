import streamlit as st

def show_readme(file_path: str):
    """
    Load and display a Markdown file in Streamlit.

    Args:
        file_path (str): Path to the markdown file (e.g., README.md)
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        st.markdown(content)
    except FileNotFoundError:
        st.error(f"File not found: {file_path}")
    except Exception as e:
        st.error(f"Error loading file: {e}")