"""
head_pose.py - Head Pose Estimation Module
AIOEPS - AI Based Online Examination Proctoring System
"""
import numpy as np

try:
    import cv2
    CV2_OK = True
except ImportError:
    CV2_OK = False

try:
    import mediapipe as mp
    _mesh = mp.solutions.face_mesh.FaceMesh(
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )
    MP_OK = True
except ImportError:
    MP_OK = False

MODEL_POINTS = np.array([
    (0.0,    0.0,    0.0),
    (0.0,  -330.0, -65.0),
    (-225.0, 170.0,-135.0),
    ( 225.0, 170.0,-135.0),
    (-150.0,-150.0,-125.0),
    ( 150.0,-150.0,-125.0),
], dtype=np.float64)

LANDMARK_IDS = [1, 152, 33, 263, 61, 291]
_turned_counter = 0
THRESHOLD = 10

def get_head_pose(frame_rgb):
    """
    Estimate head pose (yaw, pitch, roll) from an RGB frame.
    Returns: {'status': str, 'yaw': float, 'pitch': float, 'roll': float}
    """
    global _turned_counter
    if not (CV2_OK and MP_OK):
        return {'status': 'Stable', 'yaw': 0, 'pitch': 0, 'roll': 0}

    h, w = frame_rgb.shape[:2]
    result = _mesh.process(frame_rgb)
    if not result.multi_face_landmarks:
        return {'status': 'No Face', 'yaw': 0, 'pitch': 0, 'roll': 0}

    lm = result.multi_face_landmarks[0].landmark
    img_pts = np.array([
        [lm[i].x * w, lm[i].y * h] for i in LANDMARK_IDS
    ], dtype=np.float64)

    focal = w
    cam_mat = np.array([[focal,0,w/2],[0,focal,h/2],[0,0,1]], dtype=np.float64)
    dist    = np.zeros((4,1))

    ok, rvec, _ = cv2.solvePnP(MODEL_POINTS, img_pts, cam_mat, dist,
                                flags=cv2.SOLVEPNP_ITERATIVE)
    if not ok:
        return {'status': 'Stable', 'yaw': 0, 'pitch': 0, 'roll': 0}

    rot_mat, _ = cv2.Rodrigues(rvec)
    angles, *_ = cv2.RQDecomp3x3(rot_mat)
    yaw, pitch, roll = angles[1], angles[0], angles[2]

    if abs(yaw) > 20 or abs(pitch) > 15:
        _turned_counter += 1
    else:
        _turned_counter = max(0, _turned_counter - 1)

    status = "Head Turned" if _turned_counter > THRESHOLD else "Stable"
    return {
        'status': status,
        'yaw':   round(float(yaw), 1),
        'pitch': round(float(pitch), 1),
        'roll':  round(float(roll), 1)
    }
