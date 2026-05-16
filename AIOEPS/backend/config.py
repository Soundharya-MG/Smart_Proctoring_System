"""
config.py - Application Configuration
AIOEPS - AI Based Online Examination Proctoring System
"""

import os
from datetime import timedelta

class Config:
    # ─── App Settings ────────────────────────────────────────────────────────
    SECRET_KEY = os.environ.get('SECRET_KEY', 'aioeps-secret-key-2025-change-in-production')
    DEBUG = os.environ.get('DEBUG', 'True') == 'True'
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5000))

    # ─── Database ────────────────────────────────────────────────────────────
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'database', 'aioeps.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ─── JWT ─────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-aioeps-2025')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)

    # ─── File Paths ───────────────────────────────────────────────────────────
    PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..'))
    DATASET_DIR = os.path.join(PROJECT_ROOT, 'dataset')
    MODELS_DIR = os.path.join(PROJECT_ROOT, 'models')
    UPLOADS_DIR = os.path.join(PROJECT_ROOT, 'uploads')
    LOGS_DIR = os.path.join(PROJECT_ROOT, 'logs')

    # ─── AI Module Settings ──────────────────────────────────────────────────
    FACE_RECOGNITION_TOLERANCE = 0.5       # Lower = stricter matching
    FACE_DETECTION_CONFIDENCE = 0.7
    YOLO_MODEL_PATH = os.path.join(MODELS_DIR, 'yolo_model.pt')
    FACE_EMBEDDINGS_PATH = os.path.join(MODELS_DIR, 'face_embeddings.pkl')
    KEYSTROKE_MODEL_PATH = os.path.join(MODELS_DIR, 'keystroke_model.pkl')

    # ─── Proctoring Thresholds ───────────────────────────────────────────────
    EYE_GAZE_THRESHOLD = 15                # Frames before alert
    HEAD_POSE_THRESHOLD = 20              # Degrees before alert
    MULTIPLE_FACES_THRESHOLD = 1
    VOICE_DETECTION_THRESHOLD = 0.5
    RPPG_HIGH_STRESS_BPM = 100

    # ─── Exam Settings ───────────────────────────────────────────────────────
    MAX_WARNINGS = 5
    AUTO_TERMINATE_ON_WARNINGS = True

    # ─── Socket.IO ───────────────────────────────────────────────────────────
    SOCKETIO_ASYNC_MODE = 'eventlet'
    CORS_HEADERS = 'Content-Type'
