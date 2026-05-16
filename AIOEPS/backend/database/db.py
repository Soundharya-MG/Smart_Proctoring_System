"""
db.py - Database Initialization & Connection
AIOEPS - AI Based Online Examination Proctoring System
"""

import sqlite3
import os
from flask_sqlalchemy import SQLAlchemy

# SQLAlchemy instance (used by Flask app)
db = SQLAlchemy()

def get_db_connection():
    """Get a raw SQLite connection for direct queries."""
    db_path = os.path.join(os.path.dirname(__file__), 'aioeps.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Return dict-like rows
    return conn

def init_db(app):
    """Initialize the database: create tables and seed default data."""
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    db_path = os.path.join(os.path.dirname(__file__), 'aioeps.db')

    # Create DB from schema if it doesn't exist
    if not os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        with open(schema_path, 'r') as f:
            conn.executescript(f.read())
        conn.commit()
        conn.close()
        print("✅ Database initialized from schema.sql")
    else:
        print("✅ Database already exists")

    # Seed sample exams & questions if empty
    seed_sample_data()

def seed_sample_data():
    """Seed demo exams and questions for testing."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if exams exist
    cursor.execute("SELECT COUNT(*) FROM exams")
    count = cursor.fetchone()[0]

    if count == 0:
        # Insert sample exams
        exams = [
            ('EXM001', 'Data Structures', 'Computer Science', 'MCQ', 180, 50, 25, 'upcoming'),
            ('EXM002', 'OOPs in Java', 'Computer Science', 'Coding', 120, 50, 25, 'ongoing'),
            ('EXM003', 'DBMS MCQ Test', 'Database', 'MCQ', 60, 30, 15, 'upcoming'),
            ('EXM004', 'Operating Systems', 'Computer Science', 'MCQ', 90, 40, 20, 'upcoming'),
            ('EXM005', 'Computer Networks', 'Networking', 'Mixed', 150, 60, 30, 'upcoming'),
        ]
        cursor.executemany(
            "INSERT OR IGNORE INTO exams (exam_id,title,subject,exam_type,duration_minutes,total_marks,pass_marks,status) VALUES (?,?,?,?,?,?,?,?)",
            exams
        )

        # Insert sample MCQ questions for EXM001
        # EXM001: total_marks=50, pass_marks=25, 5 questions × 10 marks each = 50 total
        mcq_questions = [
            (1, 'Which data structure uses LIFO principle?', 'MCQ', 'Queue', 'Stack', 'Array', 'Linked List', 'B', 10, None),
            (1, 'What is the time complexity of binary search?', 'MCQ', 'O(n)', 'O(n²)', 'O(log n)', 'O(1)', 'C', 10, None),
            (1, 'Which traversal visits root first?', 'MCQ', 'Inorder', 'Postorder', 'Level-order', 'Preorder', 'D', 10, None),
            (1, 'What is a complete binary tree?', 'MCQ', 'All leaves at same level', 'Every node has 2 children', 'All levels fully filled except last', 'Root has no children', 'C', 10, None),
            (1, 'Which sorting is stable by default?', 'MCQ', 'Quick Sort', 'Heap Sort', 'Merge Sort', 'Selection Sort', 'C', 10, None),
        ]
        cursor.executemany(
            "INSERT OR IGNORE INTO questions (exam_id,question_text,question_type,option_a,option_b,option_c,option_d,correct_answer,marks,language) VALUES (?,?,?,?,?,?,?,?,?,?)",
            mcq_questions
        )

        # Coding questions for EXM002
        coding_q = [
            (2, 'Write a program to find the factorial of a number using recursion.\nInput: n = 5\nOutput: 120', 'Coding', None, None, None, None, None, 5, 'C++'),
            (2, 'Write a program to check whether a number is prime or not.\nInput: n = 7\nOutput: Prime number', 'Coding', None, None, None, None, None, 5, 'C++'),
            (2, 'Write a program to print Fibonacci series up to n terms.\nInput: n = 6\nOutput: 0 1 1 2 3 5', 'Coding', None, None, None, None, None, 5, 'Java'),
        ]
        cursor.executemany(
            "INSERT OR IGNORE INTO questions (exam_id,question_text,question_type,option_a,option_b,option_c,option_d,correct_answer,marks,language) VALUES (?,?,?,?,?,?,?,?,?,?)",
            coding_q
        )

        conn.commit()
        print("✅ Sample data seeded")

    conn.close()
