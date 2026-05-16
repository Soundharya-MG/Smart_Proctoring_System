"""
voice_monitor.py - Microphone / Voice Activity Detection
AIOEPS - AI Based Online Examination Proctoring System
"""
import threading
import time

try:
    import pyaudio
    import numpy as np
    AUDIO_OK = True
except ImportError:
    AUDIO_OK = False

CHUNK       = 1024
FORMAT      = 8       # pyaudio.paInt16
CHANNELS    = 1
RATE        = 16000
THRESHOLD   = 800     # RMS amplitude threshold (tune per mic)

class VoiceMonitor:
    """Continuously monitors mic and fires callback on voice detection."""
    def __init__(self, on_voice_detected=None, cooldown: float = 5.0):
        self.on_voice = on_voice_detected or (lambda: None)
        self.cooldown = cooldown
        self._running = False
        self._last_alert = 0.0
        self._thread = None

    def start(self):
        if not AUDIO_OK:
            print("⚠️  pyaudio not installed. Voice monitoring disabled.")
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor, daemon=True)
        self._thread.start()
        print("🎤 Voice monitor started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        print("🎤 Voice monitor stopped")

    def _monitor(self):
        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT, channels=CHANNELS,
                        rate=RATE, input=True,
                        frames_per_buffer=CHUNK)
        try:
            while self._running:
                data  = stream.read(CHUNK, exception_on_overflow=False)
                audio = np.frombuffer(data, dtype=np.int16)
                rms   = float(np.sqrt(np.mean(audio.astype(np.float32)**2)))
                if rms > THRESHOLD:
                    now = time.time()
                    if now - self._last_alert > self.cooldown:
                        self._last_alert = now
                        self.on_voice()
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()

def is_voice_active(duration: float = 0.5) -> bool:
    """Quick one-shot check: returns True if voice detected in `duration` seconds."""
    if not AUDIO_OK:
        return False
    try:
        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT, channels=CHANNELS,
                        rate=RATE, input=True,
                        frames_per_buffer=CHUNK)
        frames = int(RATE / CHUNK * duration)
        detected = False
        for _ in range(frames):
            data  = stream.read(CHUNK, exception_on_overflow=False)
            audio = np.frombuffer(data, dtype=np.int16)
            rms   = float(np.sqrt(np.mean(audio.astype(np.float32)**2)))
            if rms > THRESHOLD:
                detected = True
                break
        stream.stop_stream()
        stream.close()
        p.terminate()
        return detected
    except Exception:
        return False
