"""voice_detect_service.py — Voice Activity Detection Service"""
import threading, time

try:
    import pyaudio, numpy as np
    _AUDIO_OK = True
except ImportError:
    _AUDIO_OK = False

CHUNK = 1024; RATE = 16000; THRESHOLD = 800

_is_active   = False
_last_detect = 0.0

def start_monitoring(on_detect=None, cooldown=5.0):
    """Start mic monitoring in background thread."""
    if not _AUDIO_OK:
        print("⚠️  PyAudio not available")
        return
    def _monitor():
        global _is_active, _last_detect
        p = pyaudio.PyAudio()
        s = p.open(format=8, channels=1, rate=RATE, input=True, frames_per_buffer=CHUNK)
        _is_active = True
        while _is_active:
            d = s.read(CHUNK, exception_on_overflow=False)
            rms = float(np.sqrt(np.mean(np.frombuffer(d, np.int16).astype(np.float32)**2)))
            if rms > THRESHOLD and time.time() - _last_detect > cooldown:
                _last_detect = time.time()
                if on_detect: on_detect()
        s.stop_stream(); s.close(); p.terminate()
    threading.Thread(target=_monitor, daemon=True).start()

def stop_monitoring():
    global _is_active
    _is_active = False
