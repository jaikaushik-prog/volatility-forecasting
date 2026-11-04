"""Transactional append-only event ledger. Hashes detect edits, not authenticate authors."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


class Ledger:
    def __init__(self, path):
        path = Path(path); path.parent.mkdir(parents=True,exist_ok=True)
        self.db = sqlite3.connect(path,timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS events (
                sequence INTEGER PRIMARY KEY, kind TEXT NOT NULL, event_key TEXT NOT NULL,
                recorded_at TEXT NOT NULL, payload TEXT NOT NULL, previous_hash TEXT NOT NULL,
                record_hash TEXT NOT NULL, UNIQUE(kind,event_key));
            CREATE TRIGGER IF NOT EXISTS no_update BEFORE UPDATE ON events
                BEGIN SELECT RAISE(ABORT,'Ledger is append-only'); END;
            CREATE TRIGGER IF NOT EXISTS no_delete BEFORE DELETE ON events
                BEGIN SELECT RAISE(ABORT,'Ledger is append-only'); END;
        ''')
        try:
            self.verify()
        except Exception:
            self.db.close()
            raise

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def verify(self):
        previous = ''; expected = 1
        for row in self.db.execute('SELECT * FROM events ORDER BY sequence'):
            value = dict(row); recorded = value.pop('record_hash')
            if value['sequence'] != expected or value['previous_hash'] != previous or digest(value) != recorded:
                raise ValueError('Ledger integrity check failed')
            previous = recorded; expected += 1
        return expected-1

    def records(self, kind):
        return [dict(json.loads(row['payload']),_recorded_at=row['recorded_at'],_sequence=row['sequence'])
                for row in self.db.execute('SELECT * FROM events WHERE kind=? ORDER BY sequence',(kind,))]

    def get(self, kind, key):
        row = self.db.execute('SELECT payload FROM events WHERE kind=? AND event_key=?',(kind,key)).fetchone()
        return json.loads(row['payload']) if row else None

    def append_batch(self, items):
        """All events commit together; exact repeats are no-ops, conflicting repeats fail."""
        try:
            self.db.execute('BEGIN IMMEDIATE')
            self.verify()
            for kind,key,payload in items:
                serialized = canonical(payload)
                existing = self.db.execute('SELECT payload FROM events WHERE kind=? AND event_key=?',(kind,key)).fetchone()
                if existing:
                    if existing['payload'] != serialized:
                        raise ValueError(f'Conflicting immutable {kind} record: {key}')
                    continue
                last = self.db.execute('SELECT sequence,record_hash FROM events ORDER BY sequence DESC LIMIT 1').fetchone()
                value = dict(sequence=last['sequence']+1 if last else 1,kind=kind,event_key=key,
                    recorded_at=datetime.now(timezone.utc).isoformat(),payload=serialized,
                    previous_hash=last['record_hash'] if last else '')
                self.db.execute('INSERT INTO events VALUES (?,?,?,?,?,?,?)',
                    (*value.values(),digest(value)))
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
