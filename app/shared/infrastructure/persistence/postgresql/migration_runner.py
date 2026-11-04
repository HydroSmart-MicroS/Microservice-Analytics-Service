import hashlib
import os
from pathlib import Path
import psycopg

def migrate(directory: Path):
    with psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=10) as conn:
        conn.execute('SELECT pg_advisory_xact_lock(77310224)')
        conn.execute('CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, checksum TEXT NOT NULL, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())')
        for path in sorted(directory.glob('*.sql')):
            sql = path.read_text(encoding='utf-8')
            checksum = hashlib.sha256(sql.encode()).hexdigest()
            row = conn.execute('SELECT checksum FROM schema_migrations WHERE version = %s', (path.name,)).fetchone()
            if row:
                if row[0] != checksum:
                    raise RuntimeError(f'Migration changed after application: {path.name}')
                continue
            conn.execute(sql)
            conn.execute('INSERT INTO schema_migrations (version, checksum) VALUES (%s, %s)', (path.name, checksum))
    print('Analytics schema migrated.')
