import sqlite3
import bcrypt
import io
from datetime import datetime

DB_PATH = "app_data.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS pdf_library (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        filename TEXT NOT NULL,
        file_data BLOB NOT NULL,
        file_size INTEGER,
        page_count INTEGER,
        summary TEXT,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        UNIQUE(user_id, filename)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    conn.commit()
    conn.close()


# ── Auth ──────────────────────────────────────────────────────────────────────

def register_user(username, password):
    if len(username.strip()) < 3:
        return False, "Username must be at least 3 characters."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                  (username.strip(), password_hash))
        conn.commit()
        conn.close()
        return True, "Account created!"
    except sqlite3.IntegrityError:
        return False, "Username already exists."


def login_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, password_hash FROM users WHERE username = ?", (username.strip(),))
    row = c.fetchone()
    conn.close()
    if row and bcrypt.checkpw(password.encode(), row[1].encode()):
        return True, row[0]
    return False, None


def get_username(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else "Unknown"


# ── PDF Library ───────────────────────────────────────────────────────────────

def save_pdf(user_id, uploaded_file, page_count=0, summary=""):
    file_bytes = uploaded_file.getvalue()
    file_size = len(file_bytes)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM pdf_library WHERE user_id=? AND filename=?",
              (user_id, uploaded_file.name))
    existing = c.fetchone()
    if existing:
        c.execute("""UPDATE pdf_library SET file_data=?, file_size=?, page_count=?, summary=?,
                     uploaded_at=CURRENT_TIMESTAMP WHERE user_id=? AND filename=?""",
                  (file_bytes, file_size, page_count, summary, user_id, uploaded_file.name))
    else:
        c.execute("""INSERT INTO pdf_library (user_id, filename, file_data, file_size, page_count, summary)
                     VALUES (?, ?, ?, ?, ?, ?)""",
                  (user_id, uploaded_file.name, file_bytes, file_size, page_count, summary))
    conn.commit()
    conn.close()


def get_user_pdfs(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT id, filename, file_size, page_count, summary, uploaded_at
                 FROM pdf_library WHERE user_id=? ORDER BY uploaded_at DESC""", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows


def get_pdf_bytes(user_id, filename):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT file_data FROM pdf_library WHERE user_id=? AND filename=?",
              (user_id, filename))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


def delete_pdf(user_id, pdf_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM pdf_library WHERE id=? AND user_id=?", (pdf_id, user_id))
    conn.commit()
    conn.close()


# ── Chat History ──────────────────────────────────────────────────────────────

def save_message(user_id, role, content):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO chat_messages (user_id, role, content) VALUES (?, ?, ?)",
              (user_id, role, content))
    conn.commit()
    conn.close()


def get_chat_history_db(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT role, content, created_at FROM chat_messages WHERE user_id=? ORDER BY id",
              (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows


def export_chat(user_id):
    rows = get_chat_history_db(user_id)
    lines = [f"Chat Export — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n{'='*50}\n"]
    for role, content, ts in rows:
        label = "You" if role == "user" else "Assistant"
        lines.append(f"[{ts}] {label}:\n{content}\n")
    return "\n".join(lines)