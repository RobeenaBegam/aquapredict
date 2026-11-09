import sqlite3

DB_FILE = "aquapredict.db"


def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    conn = get_connection()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS tanks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        capacity REAL NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );

    CREATE TABLE IF NOT EXISTS readings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tank_id INTEGER NOT NULL,
        level REAL NOT NULL,
        fill_speed REAL NOT NULL,
        motor_on INTEGER NOT NULL,
        minutes_left REAL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (tank_id) REFERENCES tanks (id)
    );

    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tank_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        status TEXT NOT NULL,
        ring INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY (tank_id) REFERENCES tanks (id)
    );
    """)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_tables()
    print("Database and tables created.")