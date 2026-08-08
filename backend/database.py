import sqlite3, os

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "seo_tools.db")

def _conn():
    os.makedirs(DB_DIR, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with _conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            name TEXT NOT NULL DEFAULT "",
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS audit_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            url TEXT NOT NULL,
            score INTEGER NOT NULL,
            analysis TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (email) REFERENCES users(email)
        )""")
        c.commit()

def create_user(email, name, password_hash, created_at):
    with _conn() as c:
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (email, name, password_hash, created_at))
        c.commit()

def get_user(email):
    with _conn() as c:
        row = c.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return dict(row) if row else None

def save_audit(email, url, score, analysis, created_at):
    with _conn() as c:
        c.execute("INSERT INTO audit_history (email, url, score, analysis, created_at) VALUES (?, ?, ?, ?, ?)",
                  (email, url, score, analysis, created_at))
        c.commit()

def get_history(email, limit=20):
    with _conn() as c:
        rows = c.execute("SELECT url, score, created_at FROM audit_history WHERE email = ? ORDER BY created_at DESC LIMIT ?",
                         (email, limit)).fetchall()
        return [dict(r) for r in rows]
