"""
heart_rate.py - rPPG Heart Rate / Stress Detection
AIOEPS - AI Based Online Examination Proctoring System
"""
import numpy as np
from collections import deque

class RPPGDetector:
    """
    Remote Photoplethysmography (rPPG) heart rate estimator.
    Uses forehead green-channel signal + FFT to estimate BPM.
    """
    def __init__(self, fps: int = 30, window_sec: int = 10):
        self.fps      = fps
        self.buf_size = fps * window_sec
        self.signal   = deque(maxlen=self.buf_size)
        self.bpm      = 75.0
        self.frame_n  = 0

    def update(self, frame_bgr, face_rect=None):
        """
        Feed one BGR frame. Optionally pass face_rect=(x,y,w,h).
        Updates self.bpm after enough frames.
        """
        h, w = frame_bgr.shape[:2]
        if face_rect:
            x, y, fw, fh = face_rect
            roi = frame_bgr[y:y+fh//4, x:x+fw]
        else:
            roi = frame_bgr[int(h*0.05):int(h*0.20),
                            int(w*0.30):int(w*0.70)]

        if roi.size:
            self.signal.append(float(np.mean(roi[:, :, 1])))  # green channel

        self.frame_n += 1
        if self.frame_n % self.fps == 0 and len(self.signal) >= self.fps * 3:
            self._calc_bpm()

    def _calc_bpm(self):
        sig = np.array(self.signal, dtype=np.float64)
        sig -= np.mean(sig)
        fft   = np.abs(np.fft.rfft(sig))
        freqs = np.fft.rfftfreq(len(sig), d=1.0 / self.fps)
        mask  = (freqs >= 40/60) & (freqs <= 180/60)
        if mask.any():
            self.bpm = float(freqs[mask][np.argmax(fft[mask])]) * 60

    @property
    def stress_level(self) -> str:
        if self.bpm > 100: return "High"
        if self.bpm > 85:  return "Medium"
        return "Normal"

    def get_status(self) -> dict:
        return {
            'bpm': round(self.bpm, 1),
            'stress_level': self.stress_level,
            'samples': len(self.signal)
        }
