"""
Accessible Audio & Text-to-Speech (TTS) helper for GoldenCare.
Enables instant voice readouts of medications and schedules for elderly users
with visual or cognitive impairments using the Web Speech API.
"""

from __future__ import annotations

import html
import streamlit.components.v1 as components


def render_speech_button(text_to_speak: str, label: str = "🔊 Read Out Loud", button_id: str = "tts_btn") -> None:
    """
    Renders an accessible HTML/JS button that speaks the provided text
    using the browser's native Web Speech synthesis engine.
    Requires 0 cloud API keys and works offline on all modern browsers!
    """
    safe_text = html.escape(text_to_speak.replace('"', '\\"').replace("\n", " "))
    html_code = f"""
    <div style="margin: 8px 0;">
        <button id="{button_id}" onclick="speakElderlyText_{button_id}()" 
            style="
                background: linear-gradient(135deg, #10B981, #059669);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 18px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                display: inline-flex;
                align-items: center;
                gap: 8px;
                box-shadow: 0 3px 6px rgba(0,0,0,0.15);
                transition: transform 0.1s ease-in-out;
            "
            onmouseover="this.style.transform='scale(1.02)'"
            onmouseout="this.style.transform='scale(1.0)'"
        >
            <span>{label}</span>
        </button>
        <script>
            function speakElderlyText_{button_id}() {{
                if ('speechSynthesis' in window) {{
                    window.speechSynthesis.cancel();
                    const text = "{safe_text}";
                    const utterance = new SpeechSynthesisUtterance(text);
                    utterance.rate = 0.9; // Slightly slower, clearer tempo for elderly users
                    utterance.pitch = 1.0;
                    utterance.lang = 'en-US';
                    window.speechSynthesis.speak(utterance);
                }} else {{
                    alert("Text-to-speech is not supported on this browser.");
                }}
            }}
        </script>
    </div>
    """
    components.html(html_code, height=60)


def speak_text_script(text: str) -> str:
    """Generate raw JS snippet for auto-playing speech."""
    safe_text = html.escape(text.replace('"', '\\"').replace("\n", " "))
    return f"""
    <script>
        if ('speechSynthesis' in window) {{
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance("{safe_text}");
            utterance.rate = 0.9;
            utterance.pitch = 1.0;
            utterance.lang = 'en-US';
            window.speechSynthesis.speak(utterance);
        }}
    </script>
    """
