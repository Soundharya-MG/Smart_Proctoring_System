"""
voice_service.py - Text-to-Speech Voice Alert Service
AIOEPS - AI Based Online Examination Proctoring System
"""

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

def speak_alert(message: str):
    """Speak a voice alert to the student."""
    if not TTS_AVAILABLE:
        print(f"[VOICE ALERT] {message}")
        return
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        engine.setProperty('volume', 0.9)
        engine.say(message)
        engine.runAndWait()
    except Exception as e:
        print(f"[VOICE ERROR] {e}")

ALERT_MESSAGES = {
    'Looking Away':      "Please look at the screen.",
    'Head Turned':       "Please keep your head straight.",
    'Multiple Faces':    "Multiple faces detected. Only the registered student is allowed.",
    'Face Mismatch':     "Unauthorized person detected. Exam will be terminated.",
    'Mobile Detected':   "Mobile phone detected. Please remove it immediately.",
    'Voice Detected':    "Noise detected. Please maintain silence.",
    'Eye Off Screen':    "Please focus on the screen.",
    'Tab Switch':        "Tab switching is not allowed during the exam.",
}

def get_alert_message(warning_type: str) -> str:
    return ALERT_MESSAGES.get(warning_type, "Please follow exam guidelines.")
