import sqlite3
from datetime import datetime

conn = sqlite3.connect("tickets.db", check_same_thread=False)
cursor = conn.cursor()

# Таблица тикетов
cursor.execute("""
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    message TEXT,
    status TEXT,
    assigned_to INTEGER,
    thread_id INTEGER,
    created_at TEXT
)
""")

# Таблица пользователей (бан/мут)
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    muted_until TEXT,
    banned_until TEXT
)
""")

# Таблица шаблонов саппорта
cursor.execute("""
CREATE TABLE IF NOT EXISTS templates (
    support_id INTEGER,
    title TEXT,
    text TEXT
)
""")

conn.commit()

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
