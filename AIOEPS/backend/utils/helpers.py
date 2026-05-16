"""
helpers.py - Utility Helper Functions
AIOEPS - AI Based Online Examination Proctoring System
"""

import random
import string
from datetime import datetime

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    import hashlib

def hash_password(password: str) -> str:
    """Hash a password securely."""
    if BCRYPT_AVAILABLE:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    # Fallback: SHA-256 (less secure, use bcrypt in production)
    return hashlib.sha256(password.encode()).hexdigest()

def check_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    if BCRYPT_AVAILABLE:
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            pass
    # Fallback SHA-256
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest() == hashed

def generate_student_id() -> str:
    """Generate a unique student ID like S104221044100."""
    prefix = 'S'
    year = datetime.now().strftime('%y')  # e.g., '25'
    random_part = ''.join(random.choices(string.digits, k=9))
    return f"{prefix}{year}{random_part}"

def format_datetime(dt) -> str:
    """Format datetime for display."""
    if dt is None:
        return '-'
    if isinstance(dt, str):
        return dt
    return dt.strftime('%d %b %Y %I:%M %p')

def calculate_percentage(obtained: float, total: float) -> float:
    """Safe percentage calculation."""
    if total == 0:
        return 0.0
    return round((obtained / total) * 100, 2)

def paginate(data: list, page: int = 1, per_page: int = 10) -> dict:
    """Simple pagination helper."""
    total = len(data)
    start = (page - 1) * per_page
    end = start + per_page
    return {
        'items': data[start:end],
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page
    }
