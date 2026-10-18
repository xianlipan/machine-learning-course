"""Atomic best-score updates and competition ranks (ties share rank)."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone


@contextmanager
def connect(path):
    connection = sqlite3.connect(path, timeout=30)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize(path):
    with connect(path) as db:
        db.execute('''CREATE TABLE IF NOT EXISTS leaderboard (
            student_id TEXT PRIMARY KEY, name TEXT NOT NULL,
            best_rmse REAL NOT NULL, submission_count INTEGER NOT NULL,
            updated_at TEXT NOT NULL)''')


def record(path, student_id, name, rmse):
    now = datetime.now(timezone.utc).isoformat()
    with connect(path) as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('''INSERT INTO leaderboard VALUES (?, ?, ?, 1, ?)
            ON CONFLICT(student_id) DO UPDATE SET
            name=excluded.name,
            best_rmse=MIN(leaderboard.best_rmse, excluded.best_rmse),
            submission_count=leaderboard.submission_count+1,
            updated_at=excluded.updated_at''', (student_id, name, rmse, now))
        own = db.execute('SELECT * FROM leaderboard WHERE student_id=?', (student_id,)).fetchone()
        rank = 1 + db.execute('SELECT COUNT(*) FROM leaderboard WHERE best_rmse < ?', (own['best_rmse'],)).fetchone()[0]
        total = db.execute('SELECT COUNT(*) FROM leaderboard').fetchone()[0]
        return dict(best_rmse=own['best_rmse'], rank=rank, total_students=total,
                    submission_count=own['submission_count'], submitted_at=now)


def leaderboard(path):
    with connect(path) as db:
        rows = db.execute('''SELECT RANK() OVER (ORDER BY best_rmse) AS rank,
            name, best_rmse AS rmse FROM leaderboard
            ORDER BY best_rmse, student_id LIMIT 20''').fetchall()
        return [dict(row) for row in rows]
