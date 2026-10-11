import datetime
import os
import sqlite3

DB_PATH = os.environ.get("DB_PATH") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "bot.db",
)


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _run(query: str, params: tuple = (), fetch: str | None = None):
    conn = _conn()
    try:
        cur = conn.execute(query, params)

        if fetch == "one":
            result = cur.fetchone()
        elif fetch == "all":
            result = cur.fetchall()
        else:
            result = None

        conn.commit()
        return result
    finally:
        conn.close()


def now_iso() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def init() -> None:
    conn = _conn()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                tg_id        TEXT PRIMARY KEY,
                login        TEXT,
                name         TEXT,
                blocked      INTEGER NOT NULL DEFAULT 0,
                human_delays INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS actions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ts          TEXT NOT NULL,
                tg_id       TEXT,
                login       TEXT,
                subject     TEXT,
                topic_id    TEXT,
                topic_title TEXT,
                score       INTEGER,
                total       INTEGER,
                status      INTEGER,
                ok          INTEGER
            );

            CREATE INDEX IF NOT EXISTS idx_actions_ts ON actions (ts);

            CREATE TABLE IF NOT EXISTS broadcasts (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_run TEXT NOT NULL,
                text   TEXT NOT NULL,
                target TEXT NOT NULL,
                sent   INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


# ---------- users ----------

def sync_users(db: dict[str, str]) -> None:
    conn = _conn()
    try:
        for tg_id, login in db.items():
            conn.execute(
                "INSERT INTO users (tg_id, login) VALUES (?, ?) "
                "ON CONFLICT(tg_id) DO UPDATE SET login = excluded.login",
                (tg_id, login),
            )
        conn.commit()
    finally:
        conn.close()


def get_user(tg_id: str) -> dict | None:
    row = _run(
        "SELECT * FROM users WHERE tg_id = ?",
        (tg_id,),
        fetch="one",
    )
    return dict(row) if row else None


def list_users() -> list[dict]:
    rows = _run(
        "SELECT * FROM users ORDER BY tg_id",
        fetch="all",
    )
    return [dict(row) for row in rows]


def set_name(tg_id: str, name: str) -> None:
    _run(
        "UPDATE users SET name = ? WHERE tg_id = ?",
        (name, tg_id),
    )


def set_blocked(tg_id: str, blocked: bool) -> None:
    _run(
        "UPDATE users SET blocked = ? WHERE tg_id = ?",
        (1 if blocked else 0, tg_id),
    )


def is_blocked(tg_id: str) -> bool:
    user = get_user(tg_id)
    return bool(user and user["blocked"])


def get_human_delays(tg_id: str) -> bool:
    user = get_user(tg_id)
    return bool(user and user["human_delays"])


def set_human_delays(tg_id: str, enabled: bool) -> None:
    _run(
        "UPDATE users SET human_delays = ? WHERE tg_id = ?",
        (1 if enabled else 0, tg_id),
    )


# ---------- actions ----------

def log_action(
    tg_id: str,
    login: str,
    subject: str,
    topic_id: str,
    topic_title: str,
    score: int,
    total: int,
    status: int,
    ok: bool,
) -> None:
    _run(
        "INSERT INTO actions "
        "(ts, tg_id, login, subject, topic_id, topic_title, score, total, status, ok) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            now_iso(),
            tg_id,
            login,
            subject,
            topic_id,
            topic_title,
            score,
            total,
            status,
            1 if ok else 0,
        ),
    )


def recent_actions(limit: int = 15) -> list[dict]:
    rows = _run(
        "SELECT * FROM actions ORDER BY id DESC LIMIT ?",
        (limit,),
        fetch="all",
    )
    return [dict(row) for row in rows]


def count_since(since_iso: str) -> int:
    row = _run(
        "SELECT COUNT(*) FROM actions WHERE ts >= ? AND ok = 1",
        (since_iso,),
        fetch="one",
    )
    return row[0] if row else 0


def count_by_subject(since_iso: str) -> list[tuple[str, int]]:
    rows = _run(
        "SELECT subject, COUNT(*) AS c FROM actions "
        "WHERE ts >= ? AND ok = 1 GROUP BY subject ORDER BY c DESC",
        (since_iso,),
        fetch="all",
    )
    return [(row["subject"], row["c"]) for row in rows]


def count_by_user(since_iso: str) -> list[tuple[str, str, int]]:
    rows = _run(
        "SELECT tg_id, login, COUNT(*) AS c FROM actions "
        "WHERE ts >= ? AND ok = 1 GROUP BY tg_id ORDER BY c DESC",
        (since_iso,),
        fetch="all",
    )
    return [(row["tg_id"], row["login"], row["c"]) for row in rows]


def user_action_count(tg_id: str, since_iso: str) -> int:
    row = _run(
        "SELECT COUNT(*) FROM actions WHERE tg_id = ? AND ts >= ? AND ok = 1",
        (tg_id, since_iso),
        fetch="one",
    )
    return row[0] if row else 0


# ---------- broadcasts ----------

def add_broadcast(ts_run_iso: str, text: str, target: str) -> None:
    _run(
        "INSERT INTO broadcasts (ts_run, text, target) VALUES (?, ?, ?)",
        (ts_run_iso, text, target),
    )


def due_broadcasts(now_iso_value: str) -> list[dict]:
    rows = _run(
        "SELECT * FROM broadcasts WHERE sent = 0 AND ts_run <= ?",
        (now_iso_value,),
        fetch="all",
    )
    return [dict(row) for row in rows]


def pending_broadcasts() -> list[dict]:
    rows = _run(
        "SELECT * FROM broadcasts WHERE sent = 0 ORDER BY ts_run",
        fetch="all",
    )
    return [dict(row) for row in rows]


def mark_sent(broadcast_id: int) -> None:
    _run(
        "UPDATE broadcasts SET sent = 1 WHERE id = ?",
        (broadcast_id,),
    )
