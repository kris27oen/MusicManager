import streamlit as st
from core.autogen import setup_autogen_agents

# Music chatbot UI and logic
def music_chatbot_ui(agents, tracks_with_lyrics):
    st.header("🎵 Music Chatbot")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    user_input = st.text_input("Ask me anything about your music, playlists, or moods:", key="music_chat_input")
    lyrics_input = " | ".join([f"{track['title']} by {track['artist']}" for track in tracks_with_lyrics[:5]])

    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        # Compose prompt from last few messages for context
        context_messages = st.session_state.chat_history[-6:]
        prompt = "\n".join(f"{msg['role']}: {msg['content']}" for msg in context_messages)

        system_message = (
            "You are a helpful and friendly music assistant chatbot. "
            "You can recommend music, generate lyrics based on user mood or ideas, "
            "analyze user playlists, and chat casually about music."
            f' Use the following song data for context: {lyrics_input}. '
            "If you don't know the answer, say 'I don't know' or ask for more details."
        )

        try:
            gemini_llm = agents["gemini_llm"]
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ]

            response_obj = gemini_llm.chat.completions.create(
                model="gemini-2.0-flash-lite",
                messages=messages
            )

            if response_obj and response_obj.choices:
                reply = response_obj.choices[0].message.content
            else:
                reply = "Sorry, I couldn't generate a response at this time."

        except Exception as e:
            reply = f"Error in chatbot: {str(e)}"

        st.session_state.chat_history.append({"role": "assistant", "content": reply})

    # Display chat history
    for msg in st.session_state.chat_history[-10:]:
        if msg["role"] == "user":
            st.markdown(f"**You:** {msg['content']}")
        else:
            st.markdown(f"**Bot:** {msg['content']}")