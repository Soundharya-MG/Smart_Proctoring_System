"""
gaze_tracking.py - Eye Gaze Tracking Module
AIOEPS - AI Based Online Examination Proctoring System
"""
import numpy as np

try:
    import mediapipe as mp
    MP_OK = True
    _face_mesh = mp.solutions.face_mesh.FaceMesh(
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )
except ImportError:
    MP_OK = False

LEFT_IRIS  = [474, 475, 476, 477]
RIGHT_IRIS = [469, 470, 471, 472]
LEFT_EYE   = [33,  160, 158, 133, 153, 144]
RIGHT_EYE  = [362, 385, 387, 263, 373, 380]

_away_counter = 0
THRESHOLD = 12

def get_gaze_status(frame_rgb):
    """
    Analyze eye gaze from an RGB frame.
    Returns: {'status': 'Focused'|'Looking Away', 'ratio': float}
    """
    global _away_counter
    if not MP_OK:
        return {'status': 'Focused', 'ratio': 0.5}

    h, w = frame_rgb.shape[:2]
    result = _face_mesh.process(frame_rgb)

    if not result.multi_face_landmarks:
        return {'status': 'No Face', 'ratio': 0.5}

    lm = result.multi_face_landmarks[0].landmark

    def iris_ratio(eye_ids, iris_ids):
        eye_pts  = np.array([[lm[i].x * w, lm[i].y * h] for i in eye_ids])
        iris_pts = np.array([[lm[i].x * w, lm[i].y * h] for i in iris_ids])
        cx   = np.mean(iris_pts[:, 0])
        left = eye_pts[:, 0].min()
        right= eye_pts[:, 0].max()
        return (cx - left) / max(right - left, 1)

    lr = iris_ratio(LEFT_EYE,  LEFT_IRIS)
    rr = iris_ratio(RIGHT_EYE, RIGHT_IRIS)
    avg = (lr + rr) / 2

    if avg < 0.30 or avg > 0.70:
        _away_counter += 1
    else:
        _away_counter = max(0, _away_counter - 1)

    status = "Looking Away" if _away_counter > THRESHOLD else "Focused"
    return {'status': status, 'ratio': round(float(avg), 3), 'away_frames': _away_counter}
