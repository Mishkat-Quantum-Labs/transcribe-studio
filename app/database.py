import sqlite3

from app.paths import data_dir

DATA_DIR = data_dir()
DB_PATH = DATA_DIR / "transcribe.db"


def get_conn() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS recordings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
            title TEXT NOT NULL,
            filename TEXT NOT NULL,
            duration_ms INTEGER,
            notes TEXT DEFAULT '',
            llm_transcript_file TEXT DEFAULT '',
            llm_transcript_lang TEXT DEFAULT 'en',
            llm_transcript_format TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recording_id INTEGER NOT NULL REFERENCES recordings(id) ON DELETE CASCADE,
            start_ms INTEGER NOT NULL,
            end_ms INTEGER NOT NULL,
            speaker TEXT NOT NULL DEFAULT '',
            transcript TEXT NOT NULL DEFAULT '',
            llm_transcript TEXT NOT NULL DEFAULT '',
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        """
    )
    conn.commit()
    conn.close()


def migrate_add_llm_transcript() -> None:
    """Add llm_transcript column to segments if it doesn't exist."""
    conn = get_conn()
    try:
        conn.execute("ALTER TABLE segments ADD COLUMN llm_transcript TEXT NOT NULL DEFAULT ''")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists
    finally:
        conn.close()


def migrate_add_recording_llm_fields() -> None:
    """Add LLM transcript fields to recordings table if they don't exist."""
    conn = get_conn()
    for sql in (
        "ALTER TABLE recordings ADD COLUMN llm_transcript_file TEXT DEFAULT ''",
        "ALTER TABLE recordings ADD COLUMN llm_transcript_lang TEXT DEFAULT 'en'",
        "ALTER TABLE recordings ADD COLUMN llm_transcript_format TEXT DEFAULT ''",
    ):
        try:
            conn.execute(sql)
            conn.commit()
        except sqlite3.OperationalError:
            pass
    conn.close()


def migrate_add_projects() -> None:
    """Ensure projects exist and recordings are assigned."""
    conn = get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()
    try:
        conn.execute(
            "ALTER TABLE recordings ADD COLUMN project_id INTEGER REFERENCES projects(id)"
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass

    default = conn.execute(
        "SELECT id FROM projects WHERE name = 'Default project' LIMIT 1"
    ).fetchone()
    if not default:
        cur = conn.execute(
            "INSERT INTO projects (name, description) VALUES (?, ?)",
            ("Default project", "Imported and new recordings"),
        )
        default_id = cur.lastrowid
    else:
        default_id = default["id"]

    conn.execute(
        "UPDATE recordings SET project_id = ? WHERE project_id IS NULL",
        (default_id,),
    )
    conn.commit()
    conn.close()