import os
import sqlite3

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "seo_tools.db")

# Colonnes ajoutées après la première version du schéma. Elles sont créées à la volée au
# démarrage : une base existante (celle du service en production) doit continuer de servir,
# sans script de migration ni perte d'utilisateurs.
USER_COLUMNS = {
    "premium": "INTEGER NOT NULL DEFAULT 0",
    "stripe_customer_id": "TEXT",
    "premium_since": "TEXT",
}


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
        c.execute("""CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT "",
            price TEXT,
            price_value REAL,
            currency TEXT NOT NULL DEFAULT "",
            captured_at TEXT NOT NULL
        )""")
        # L'historique d'un compte est lu à chaque ouverture de panneau : sans index, SQLite
        # balaie toute la table.
        c.execute("CREATE INDEX IF NOT EXISTS idx_audit_email ON audit_history(email, created_at DESC)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_price_url ON price_history(url, captured_at DESC)")
        existing = {row["name"] for row in c.execute("PRAGMA table_info(users)")}
        for name, ddl in USER_COLUMNS.items():
            if name not in existing:
                c.execute(f"ALTER TABLE users ADD COLUMN {name} {ddl}")
        c.commit()


def create_user(email, name, password_hash, created_at):
    with _conn() as c:
        c.execute(
            "INSERT INTO users (email, name, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (email, name, password_hash, created_at),
        )
        c.commit()


def get_user(email):
    with _conn() as c:
        row = c.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return dict(row) if row else None


def get_user_by_customer(customer_id):
    if not customer_id:
        return None
    with _conn() as c:
        row = c.execute("SELECT * FROM users WHERE stripe_customer_id = ?", (customer_id,)).fetchone()
        return dict(row) if row else None


def set_premium(email, premium, customer_id=None, since=None):
    """Enregistre l'état d'abonnement. C'est la seule source de vérité du statut premium :
    avant, il vivait dans un dictionnaire en mémoire, perdu au premier redémarrage."""
    with _conn() as c:
        if customer_id:
            cursor = c.execute(
                "UPDATE users SET premium = ?, stripe_customer_id = ?, premium_since = ? WHERE email = ?",
                (1 if premium else 0, customer_id, since if premium else None, email),
            )
        else:
            cursor = c.execute(
                "UPDATE users SET premium = ?, premium_since = ? WHERE email = ?",
                (1 if premium else 0, since if premium else None, email),
            )
        changed = cursor.rowcount
        c.commit()
        return changed > 0


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


def save_price_point(url, price, currency, captured_at, title=""):
    """Ajoute un relevé de prix. `price_value` est la valeur numérique extraite, pour tracer
    une courbe sans re-parser les chaînes affichées."""
    value = parse_price_value(price)
    with _conn() as c:
        c.execute(
            "INSERT INTO price_history (url, title, price, price_value, currency, captured_at) VALUES (?, ?, ?, ?, ?, ?)",
            (url, title or "", price, value, currency or "", captured_at),
        )
        c.commit()


def get_price_history(url, limit=60):
    with _conn() as c:
        rows = c.execute(
            "SELECT price, price_value, currency, captured_at FROM price_history WHERE url = ? "
            "ORDER BY captured_at DESC LIMIT ?",
            (url, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def parse_price_value(price):
    """Extrait un nombre d'une chaîne de prix affichée (« 1 234,50 € », « $99.99 »)."""
    if price is None:
        return None
    if isinstance(price, (int, float)):
        return float(price)
    import re
    text = str(price).replace("\u00a0", " ").replace(" ", "")
    match = re.search(r"\d+(?:[.,]\d+)?", text)
    if not match:
        return None
    raw = match.group(0)
    if "," in raw and "." in raw:
        raw = raw.replace(",", "") if raw.rindex(".") > raw.rindex(",") else raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        raw = raw.replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None
