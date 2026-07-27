import sqlite3
import json
from datetime import datetime

WAL_DB = 'oms_wal.db'

def init_wal() -> None:
    conn = sqlite3.connect(WAL_DB)
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS wal (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, payload TEXT)''')
    conn.commit()
    conn.close()

init_wal()

def append_to_wal(payload: dict) -> None:
    conn = sqlite3.connect(WAL_DB)
    cur = conn.cursor()
    cur.execute('INSERT INTO wal (timestamp, payload) VALUES (?, ?)', (datetime.utcnow().isoformat(), json.dumps(payload)))
    conn.commit()
    conn.close()

def replay_wal_on_startup(process_func) -> None:
    conn = sqlite3.connect(WAL_DB)
    cur = conn.cursor()
    rows = cur.execute('SELECT payload FROM wal ORDER BY id').fetchall()
    for (payload_json,) in rows:
        payload = json.loads(payload_json)
        process_func(payload)
    # Clear WAL after replay
    cur.execute('DELETE FROM wal')
    conn.commit()
    conn.close()
