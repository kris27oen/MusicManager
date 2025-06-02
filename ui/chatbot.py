import streamlit as st
from core.autogen import setup_autogen_agents

def music_chatbot_ui(agents, tracks_with_lyrics):
    with st.container(key="chat_container"):
        st.subheader("💬 Chatbot")

        # Initialize session state for chat
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        if "chat_input_key" not in st.session_state:
            st.session_state.chat_input_key = 0

        def send_message():
            """Callback function to process chat message on Enter"""
            user_input = st.session_state.get(f"chat_input_{st.session_state.chat_input_key}", "").strip()
            
            if user_input:
                # Add user message to chat history
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                
                # Prepare context for the chatbot
                context_messages = st.session_state.chat_history[-6:]
                prompt = "\n".join(f"{msg['role']}: {msg['content']}" for msg in context_messages)

                if tracks_with_lyrics and agents:
                    system_message = (
                        "You are a helpful and friendly music assistant chatbot. "
                        "You can recommend music, generate lyrics based on user mood or ideas, "
                        "analyze user playlists, and chat casually about music. "
                        "Avoid repeating songs already in the playlist. "
                        "IMPORTANT: Only respond with plain text, no HTML or special formatting. "
                        f"Here is the current playlist: {tracks_with_lyrics}. "
                    )
                else:
                    system_message = (
                        "You are a helpful and friendly music assistant chatbot. "
                        "You can recommend music, generate lyrics based on user mood or ideas, "
                        "discuss music genres, artists, and chat casually about music. "
                        "The user hasn't loaded a playlist yet, so focus on general music conversation, "
                        "recommendations, and music-related topics. "
                        "IMPORTANT: Only respond with plain text, no HTML or special formatting. "
                    )

                try:
                    if agents and "gemini_llm" in agents:
                        gemini_llm = agents["gemini_llm"]
                        messages = [
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": prompt}
                        ]

                        response_obj = gemini_llm.chat.completions.create(
                            model="gemini-2.0-flash-lite",
                            messages=messages
                        )

                        reply = response_obj.choices[0].message.content if response_obj and response_obj.choices else "Sorry, I couldn't generate a response."
                    else:
                        reply = (
                            "Hi! I'm your music assistant. I can help you discover new music, "
                            "discuss artists and genres, or chat about anything music-related. "
                            "Load a playlist to unlock advanced features like playlist analysis! "
                            "What would you like to talk about?"
                        ) 
                except Exception as e:
                    reply = f"Error in chatbot: {str(e)}"

                # Clean the reply to remove any HTML artifacts
                clean_reply = reply.replace("</div>", "").replace("<div>", "").strip()
                
                # Add bot response to chat history
                st.session_state.chat_history.append({"role": "assistant", "content": clean_reply})
                
                # Clear the input by updating the key
                st.session_state.chat_input_key += 1
        
        # Create chat display area
        with st.container(key="chat_container_display"):
            with st.container(key="chat_display", height=250):
                if st.session_state.chat_history:
                    for msg in st.session_state.chat_history[-20:]:
                        if msg["role"] == "user":
                            st.markdown(
                                f'<div class="user-message"><strong>You:</strong> {msg["content"]}</div>',
                                unsafe_allow_html=True
                            )
                        else:
                            st.markdown(
                                f'<div class="assistant-message"><strong>Assistant:</strong> {msg["content"]}</div>',
                                unsafe_allow_html=True
                            )
                else:
                    st.markdown(
                        '<div style="text-align: center; color: #888; padding: 20px;">Start a conversation!</div>',
                        unsafe_allow_html=True
                    )

            # Chat input section
            with st.container(key="chat_input_container"):
                st.text_input(
                    "",
                    placeholder="Ask Chatbot...",
                    key=f"chat_input_{st.session_state.chat_input_key}",
                    on_change=send_message,
                    label_visibility="collapsed"
                )
        
    # Custom CSS for styling - no more nested containers
    st.markdown("""
        <style>
        .st-key-chat_container {
            position: fixed;
            background-color: #262730;
            border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            padding: 15px;
            padding-top: 5px;
            overflow-y: none;
            margin-left: 20px;
        }
        .user-message {
            background-color: rgba(255, 255, 255, 0.1);
            padding: 10px;
            border-radius: 8px;
            margin: 8px 20px 8px 0;
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: white;
        }
        .assistant-message {
            background-color: rgba(255, 255, 255, 0.05);
            padding: 10px;
            border-radius: 8px;
            margin: 8px 0 8px 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: white;
        }
        .st-key-chat_container_display [data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #0E1117;   
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 8px;  
        }
        
        </style>
    """, unsafe_allow_html=True)