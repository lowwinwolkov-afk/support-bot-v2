import sqlite3
from utils import fmt

conn = sqlite3.connect("tickets.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    message TEXT,
    status TEXT,
    assigned_to INTEGER,
    thread_id INTEGER,
    tag TEXT,
    first_response TEXT,
    created_at TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    last_message_time TEXT,
    muted_until TEXT,
    banned_until TEXT,
    note TEXT
)
""")

conn.commit()

# ---------------- TICKETS ----------------

def create_ticket(uid, username, msg):
    cursor.execute("""
        INSERT INTO tickets (user_id, username, message, status, created_at)
        VALUES (?, ?, ?, 'NEW', ?)
    """, (uid, username, msg, fmt()))
    conn.commit()
    return cursor.lastrowid


def set_thread(tid, thread_id):
    cursor.execute("UPDATE tickets SET thread_id=? WHERE id=?", (thread_id, tid))
    conn.commit()


def assign_ticket(tid, support_id):
    cursor.execute("""
        UPDATE tickets 
        SET assigned_to=?, status='IN_PROGRESS'
        WHERE id=?
    """, (support_id, tid))
    conn.commit()


def close_ticket(tid):
    cursor.execute("UPDATE tickets SET status='CLOSED' WHERE id=?", (tid,))
    conn.commit()


def set_tag(tid, tag):
    cursor.execute("UPDATE tickets SET tag=? WHERE id=?", (tag, tid))
    conn.commit()


def set_first_response(tid):
    cursor.execute("""
        UPDATE tickets 
        SET first_response=?
        WHERE id=?
    """, (fmt(), tid))
    conn.commit()


def get_ticket(tid):
    cursor.execute("SELECT * FROM tickets WHERE id=?", (tid,))
    return cursor.fetchone()

# ---------------- USERS ----------------

def set_user(uid, field, value):
    cursor.execute(f"""
    INSERT INTO users(user_id, {field})
    VALUES (?, ?)
    ON CONFLICT(user_id) DO UPDATE SET {field}=excluded.{field}
    """, (uid, value))
    conn.commit()


def get_user(uid):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    return cursor.fetchone()
