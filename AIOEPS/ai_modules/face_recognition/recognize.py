"""
recognize.py - Real-time Face Recognition
AIOEPS - AI Based Online Examination Proctoring System
"""
import os, pickle, sys
import numpy as np

EMBEDDINGS_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'models', 'face_embeddings.pkl')

def recognize_face(frame_rgb, tolerance=0.50):
    """
    Recognize a face in an RGB frame against stored embeddings.
    Returns: {'name': str, 'confidence': float, 'matched': bool}
    """
    try:
        import face_recognition
    except ImportError:
        return {'name': 'Unknown', 'confidence': 0, 'matched': False}

    if not os.path.exists(EMBEDDINGS_PATH):
        return {'name': 'No DB', 'confidence': 0, 'matched': False}

    with open(EMBEDDINGS_PATH, 'rb') as f:
        db = pickle.load(f)

    known_ids  = list(db.keys())
    known_encs = list(db.values())

    locs = face_recognition.face_locations(frame_rgb, model='hog')
    if not locs:
        return {'name': 'No Face', 'confidence': 0, 'matched': False}

    encs = face_recognition.face_encodings(frame_rgb, locs)
    if not encs:
        return {'name': 'No Encoding', 'confidence': 0, 'matched': False}

    dists = face_recognition.face_distance(known_encs, encs[0])
    idx   = int(np.argmin(dists))
    dist  = float(dists[idx])

    if dist <= tolerance:
        return {'name': known_ids[idx], 'confidence': round(1 - dist, 3), 'matched': True}
    return {'name': 'Unknown', 'confidence': round(1 - dist, 3), 'matched': False}
