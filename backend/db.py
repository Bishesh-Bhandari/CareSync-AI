import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'healthsync.db')


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT DEFAULT 'patient',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            symptoms_text TEXT NOT NULL,
            symptoms_parsed TEXT DEFAULT '[]',
            severity INTEGER DEFAULT 5,
            health_score INTEGER DEFAULT 50,
            mood TEXT DEFAULT 'okay',
            medications TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            summary_text TEXT NOT NULL,
            trend TEXT DEFAULT 'stable',
            trend_percent REAL DEFAULT 0,
            generated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    """)
    conn.commit()
    conn.close()


# ── User operations ──

def create_user(username, email, password_hash, full_name, role='patient'):
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO users (username, email, password_hash, full_name, role) VALUES (?, ?, ?, ?, ?)",
            (username, email, password_hash, full_name, role)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def get_user_by_email(email):
    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return dict(user) if user else None


def get_user_by_id(user_id):
    conn = get_connection()
    user = conn.execute("SELECT id, username, email, full_name, role, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None


# ── Checkin operations ──

def create_checkin(user_id, symptoms_text, symptoms_parsed, severity, health_score, mood, medications, notes=''):
    conn = get_connection()
    import json
    cursor = conn.execute(
        """INSERT INTO checkins 
           (user_id, symptoms_text, symptoms_parsed, severity, health_score, mood, medications, notes) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, symptoms_text, json.dumps(symptoms_parsed), severity, health_score, mood, medications, notes)
    )
    conn.commit()
    checkin_id = cursor.lastrowid
    conn.close()
    return checkin_id


def get_checkins(user_id, limit=30):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM checkins WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_checkin_count(user_id):
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) as c FROM checkins WHERE user_id = ?", (user_id,)).fetchone()['c']
    conn.close()
    return count


# ── Summary operations ──

def save_summary(user_id, summary_text, trend, trend_percent):
    conn = get_connection()
    conn.execute(
        "INSERT INTO summaries (user_id, summary_text, trend, trend_percent) VALUES (?, ?, ?, ?)",
        (user_id, summary_text, trend, trend_percent)
    )
    conn.commit()
    conn.close()


def get_latest_summary(user_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM summaries WHERE user_id = ? ORDER BY generated_at DESC LIMIT 1",
        (user_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ── Seed demo data ──

def seed_demo_data():
    from werkzeug.security import generate_password_hash

    if get_user_by_email('sarah@healthsync.ai'):
        return False

    uid = create_user(
        'sarahjohnson', 'sarah@healthsync.ai',
        generate_password_hash('patient123'),
        'Sarah Johnson'
    )
    if not uid:
        return False

    checkins = [
        ("Severe headache all day, very tired, can't sleep well, feeling terrible",
         "bad", "Ibuprofen 400mg", "Worst day this month"),
        ("Terrible migraine again, extreme fatigue, feeling miserable and depressed",
         "bad", "Ibuprofen 400mg, Paracetamol 500mg", "Had to leave work early"),
        ("Bad headache but not as intense as before, still very tired, no sleep",
         "bad", "Ibuprofen 400mg", ""),
        ("Moderate headache today, fatigue is noticeable, feeling sick to my stomach after lunch",
         "okay", "Ibuprofen 400mg", "New symptom: nausea"),
        ("Mild headache today, still tired but a bit better, some nausea in the morning",
         "okay", "Ibuprofen 400mg", ""),
        ("Slight headache, fatigue improving, mild nausea still there after meals",
         "okay", "Ibuprofen 200mg", "Reduced ibuprofen dose"),
        ("Minor headache, feeling better overall, a bit of nausea sometimes",
         "good", "Ibuprofen 200mg", "Was able to go for a short walk"),
        ("Very mild headache, energy is coming back, slight nausea but manageable",
         "good", "Ibuprofen 200mg", ""),
        ("Barely any headache, feeling much better, tiny bit of nausea sometimes in the evening",
         "good", "", "Stopped taking ibuprofen"),
    ]

    from processor import parse_symptoms, calculate_overall_severity

    for i, (text, mood, meds, notes) in enumerate(checkins):
        symptoms = parse_symptoms(text)
        severity = calculate_overall_severity(symptoms)
        health_score = (10 - severity) * 10
        create_checkin(uid, text, symptoms, severity, health_score, mood, meds, notes)

    return True