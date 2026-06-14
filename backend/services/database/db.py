"""
database/db.py
--------------
All database logic lives here.
main.py imports and calls these functions — it never touches SQLite directly.

Tables:
  users         — registered accounts
  symptom_logs  — each AI analysis a user has done
"""

import sqlite3
import os
import hashlib
import secrets

# DB file sits in the same folder as this script
DB_PATH = os.path.join(os.path.dirname(__file__), "healthsync.db")


# ─────────────────────────────────────────────
#  Connection helper
# ─────────────────────────────────────────────
def get_connection():
    """
    Open and return a sqlite3 connection.
    row_factory = sqlite3.Row lets us do row["email"] instead of row[1]
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ─────────────────────────────────────────────
#  Init — run once to create tables
# ─────────────────────────────────────────────
def init_db():
    conn = get_connection()
    cur  = conn.cursor()

    # users table — one row per registered account
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name    TEXT NOT NULL,
            last_name     TEXT NOT NULL,
            email         TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            salt          TEXT NOT NULL,
            created_at    TEXT DEFAULT (datetime('now'))
        )
    """)

    # symptom_logs — one row per AI analysis
    cur.execute("""
        CREATE TABLE IF NOT EXISTS symptom_logs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            symptoms        TEXT NOT NULL,
            condition       TEXT,
            severity        TEXT,
            recommendations TEXT,
            created_at      TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
#  Password helpers  (stdlib only, no bcrypt needed)
# ─────────────────────────────────────────────
def _hash_password(plain: str, salt: str) -> str:
    """SHA-256 of  salt + password."""
    return hashlib.sha256((salt + plain).encode()).hexdigest()

def _make_salt() -> str:
    return secrets.token_hex(16)   # 32 random hex chars


# ─────────────────────────────────────────────
#  User functions
# ─────────────────────────────────────────────
def create_user(first_name: str, last_name: str, email: str, plain_password: str):
    """
    Insert a new user row.
    Returns the new user id on success.
    Raises ValueError if the email already exists.
    """
    salt          = _make_salt()
    password_hash = _hash_password(plain_password, salt)

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (first_name, last_name, email, password_hash, salt)
            VALUES (?, ?, ?, ?, ?)
        """, (first_name, last_name, email.lower().strip(), password_hash, salt))
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        raise ValueError("An account with that email already exists.")
    finally:
        conn.close()


def get_user_by_email(email: str):
    """Return user dict or None."""
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),))
    row  = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id: int):
    """Return user dict or None."""
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row  = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def verify_password(email: str, plain_password: str):
    """
    Check credentials.
    Returns user dict on success, None on wrong password / unknown email.
    """
    user = get_user_by_email(email)
    if not user:
        return None
    expected = _hash_password(plain_password, user["salt"])
    if secrets.compare_digest(expected, user["password_hash"]):
        return user
    return None


# ─────────────────────────────────────────────
#  Symptom log functions
# ─────────────────────────────────────────────
def save_symptom_log(user_id: int, symptoms: str,
                     condition: str, severity: str, recommendations: str):
    """
    Save one AI analysis.
    recommendations = JSON string e.g. '["Drink water","Rest"]'
    """
    conn = get_connection()
    conn.execute("""
        INSERT INTO symptom_logs
            (user_id, symptoms, condition, severity, recommendations)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, symptoms, condition, severity, recommendations))
    conn.commit()
    conn.close()


def get_logs_for_user(user_id: int) -> list:
    """Return all logs for a user, newest first."""
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT id, symptoms, condition, severity, recommendations, created_at
        FROM   symptom_logs
        WHERE  user_id = ?
        ORDER  BY created_at DESC
    """, (user_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# run directly to create the DB
if __name__ == "__main__":
    init_db()
    print(f"DB ready -> {DB_PATH}")