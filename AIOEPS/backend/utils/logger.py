"""
logger.py - Logging Utility
AIOEPS - AI Based Online Examination Proctoring System
"""

import logging
import os
from datetime import datetime

LOGS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

def _get_logger(name: str, filename: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(os.path.join(LOGS_DIR, filename), encoding='utf-8')
        fh.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s'))
        logger.addHandler(fh)
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s'))
        logger.addHandler(ch)
    return logger

activity_logger = _get_logger('activity', 'activity.log')
cheating_logger  = _get_logger('cheating',  'cheating.log')
error_logger     = _get_logger('error',     'errors.log')

def log_activity(student_id, session_id, action: str, details: str = ''):
    """Log general activity."""
    activity_logger.info(f"student={student_id} session={session_id} action={action} | {details}")
    # Also persist to DB
    try:
        from database.db import get_db_connection
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO activity_logs (student_id, session_id, action, details) VALUES (?,?,?,?)",
            (student_id, session_id, action, details)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

def log_cheating(session_id, student_id, warning_type: str, severity: str):
    """Log cheating/proctoring event."""
    cheating_logger.warning(
        f"session={session_id} student={student_id} type={warning_type} severity={severity}"
    )

def log_error(context: str, error: Exception):
    """Log application errors."""
    error_logger.error(f"{context} | {type(error).__name__}: {error}")
