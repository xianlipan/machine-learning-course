"""Atomic best-score updates and competition ranks (ties share rank)."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

MAX_SUBMISSIONS = 3


class SubmissionLimitReached(ValueError):
    pass


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
        db.execute('''CREATE TABLE IF NOT EXISTS submission_limits (
            kind TEXT NOT NULL, identity TEXT NOT NULL, submission_count INTEGER NOT NULL,
            PRIMARY KEY (kind, identity))''')
        # Import existing valid submissions without clearing scores or counters.
        db.execute('''INSERT OR IGNORE INTO submission_limits
            SELECT 'student_id', student_id, submission_count FROM leaderboard''')
        db.execute('''INSERT OR IGNORE INTO submission_limits
            SELECT 'name', name, SUM(submission_count) FROM leaderboard GROUP BY name''')


def _check_limit(db, student_id, name):
    rows = db.execute('''SELECT submission_count FROM submission_limits
        WHERE (kind='student_id' AND identity=?) OR (kind='name' AND identity=?)''',
        (student_id, name)).fetchall()
    used = max((row['submission_count'] for row in rows), default=0)
    if used >= MAX_SUBMISSIONS:
        raise SubmissionLimitReached('已达到提交上限：同一姓名或同一学号最多可成功提交三次。')
    return used


def check_limit(path, student_id, name):
    with connect(path) as db:
        _check_limit(db, student_id, name)


def record(path, student_id, name, rmse):
    now = datetime.now(timezone.utc).isoformat()
    with connect(path) as db:
        db.execute('BEGIN IMMEDIATE')
        used = _check_limit(db, student_id, name)
        for kind, identity in (('student_id', student_id), ('name', name)):
            db.execute('''INSERT INTO submission_limits VALUES (?, ?, 1)
                ON CONFLICT(kind, identity) DO UPDATE SET
                submission_count=submission_limits.submission_count+1''', (kind, identity))
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
                    submission_count=own['submission_count'], submitted_at=now,
                    remaining_submissions=MAX_SUBMISSIONS-used-1)


def leaderboard(path):
    with connect(path) as db:
        rows = db.execute('''SELECT RANK() OVER (ORDER BY best_rmse) AS rank,
            name, best_rmse AS rmse FROM leaderboard
            ORDER BY best_rmse, student_id LIMIT 20''').fetchall()
        return [dict(row) for row in rows]
