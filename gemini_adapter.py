import google.generativeai as genai
from typing import Dict, List, Optional, Any

class GeminiLLM:
    """
    A custom adapter for Google's Gemini models to work with Autogen.
    """

    def __init__(self, api_key: str, model: str = "gemini-1.5-pro-001"):
        """
        Initialize the Gemini adapter.

        Args:
            api_key: The Google API key
            model: The Gemini model to use
        """
        genai.configure(api_key=api_key)
        self.model = model

        self.generation_config = {
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 8192,
        }

        self.safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]

        try:
            self.gemini_model = genai.GenerativeModel(
                model_name=model,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )
        except Exception as e:
            raise ValueError(f"Failed to initialize Gemini model: {e}")

    def create(self, 
               messages: List[Dict[str, str]], 
               model: Optional[str] = None, 
               **kwargs) -> Dict[str, Any]:
        """
        Create a response using the Gemini model.

        Args:
            messages: A list of message dictionaries with 'role' and 'content'
            model: Model override (optional)
            **kwargs: Additional arguments

        Returns:
            Response in a format compatible with Autogen
        """
        model = model or self.model
        prompt = self._convert_messages_to_prompt(messages)

        try:
            response = self.gemini_model.generate_content(prompt)

            return {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": response.text
                        },
                        "finish_reason": "stop"
                    }
                ],
                "model": model,
                "usage": {
                    "prompt_tokens": -1,
                    "completion_tokens": -1,
                    "total_tokens": -1
                }
            }
        except Exception as e:
            raise RuntimeError(f"Error generating content with Gemini: {e}")

    def _convert_messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """
        Convert OpenAI-style messages to a text prompt for Gemini.

        Args:
            messages: List of messages in OpenAI format

        Returns:
            A formatted prompt string
        """
        prompt = ""
        system_message = ""

        for message in messages:
            if message["role"] == "system":
                system_message = message["content"]
                break

        if system_message:
            prompt += f"System: {system_message}\n\n"

        for message in messages:
            if message["role"] == "user":
                prompt += f"User: {message['content']}\n\n"
            elif message["role"] == "assistant":
                prompt += f"Assistant: {message['content']}\n\n"

        return prompt.strip()
