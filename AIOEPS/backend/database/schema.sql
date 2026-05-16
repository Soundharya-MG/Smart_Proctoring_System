-- ============================================================
-- schema.sql - AIOEPS Database Schema
-- AI Based Online Examination Proctoring System
-- ============================================================

-- Users table (students + admins)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT UNIQUE,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'student',  -- 'student' or 'admin'
    face_encoded INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active INTEGER DEFAULT 1
);

-- Exams table
CREATE TABLE IF NOT EXISTS exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    subject TEXT NOT NULL,
    exam_type TEXT DEFAULT 'MCQ',  -- 'MCQ', 'Coding', 'Mixed'
    duration_minutes INTEGER NOT NULL,
    total_marks INTEGER NOT NULL,
    pass_marks INTEGER NOT NULL,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    status TEXT DEFAULT 'upcoming',  -- 'upcoming','ongoing','completed'
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    instructions TEXT,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- Questions table
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id INTEGER NOT NULL,
    question_text TEXT NOT NULL,
    question_type TEXT DEFAULT 'MCQ',  -- 'MCQ' or 'Coding'
    option_a TEXT,
    option_b TEXT,
    option_c TEXT,
    option_d TEXT,
    correct_answer TEXT,
    marks INTEGER DEFAULT 1,
    language TEXT,  -- for coding: 'C','C++','Java','Python'
    sample_input TEXT,
    expected_output TEXT,
    order_num INTEGER,
    FOREIGN KEY (exam_id) REFERENCES exams(id)
);

-- Exam sessions
CREATE TABLE IF NOT EXISTS exam_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    exam_id INTEGER NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    submitted_at TIMESTAMP,
    status TEXT DEFAULT 'active',  -- 'active','submitted','terminated'
    score REAL DEFAULT 0,
    percentage REAL DEFAULT 0,
    result TEXT,  -- 'Pass' or 'Fail'
    total_warnings INTEGER DEFAULT 0,
    face_verified INTEGER DEFAULT 0,
    ip_address TEXT,
    FOREIGN KEY (student_id) REFERENCES users(id),
    FOREIGN KEY (exam_id) REFERENCES exams(id)
);

-- Student answers
CREATE TABLE IF NOT EXISTS answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    student_answer TEXT,
    is_correct INTEGER DEFAULT 0,
    marks_obtained REAL DEFAULT 0,
    answered_at TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES exam_sessions(id),
    FOREIGN KEY (question_id) REFERENCES questions(id)
);

-- Proctoring warnings/alerts
CREATE TABLE IF NOT EXISTS warnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    warning_id TEXT UNIQUE,
    session_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    exam_id INTEGER NOT NULL,
    warning_type TEXT NOT NULL,  -- 'Face Mismatch','Looking Away','Multiple Faces','Mobile Detected','Voice Detected','Head Turned','Eye Off Screen','Suspicious Activity'
    severity TEXT DEFAULT 'Medium',  -- 'Low','Medium','High','Critical'
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    snapshot_path TEXT,
    action_taken TEXT,
    resolved INTEGER DEFAULT 0,
    FOREIGN KEY (session_id) REFERENCES exam_sessions(id)
);

-- rPPG / Stress monitoring
CREATE TABLE IF NOT EXISTS stress_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    session_id INTEGER NOT NULL,
    bpm REAL,
    stress_level TEXT,  -- 'Normal','Medium','High'
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES users(id)
);

-- Keystroke dynamics logs
CREATE TABLE IF NOT EXISTS keystroke_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    session_id INTEGER NOT NULL,
    key_data TEXT,  -- JSON: dwell times, flight times
    anomaly_score REAL DEFAULT 0,
    flagged INTEGER DEFAULT 0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES users(id)
);

-- Activity log
CREATE TABLE IF NOT EXISTS activity_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    session_id INTEGER,
    action TEXT NOT NULL,
    details TEXT,
    ip_address TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default admin
INSERT OR IGNORE INTO users (student_id, name, email, password_hash, role)
VALUES ('ADMIN001', 'Administrator', 'admin@aioeps.com',
        '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'admin');
-- Default admin password: 'admin123' (bcrypt hash)

-- ── Auto Plagiarism Results (added v7) ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS plagiarism_results (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   INTEGER NOT NULL,
    question_id  INTEGER NOT NULL,
    student_id   INTEGER NOT NULL,
    score        REAL    DEFAULT 0,
    level        TEXT    DEFAULT 'Normal',
    matched_with TEXT,
    details      TEXT,
    checked_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, question_id)
);
