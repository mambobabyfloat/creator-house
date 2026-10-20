"""Optional durable SQL database; do not store credentials or access tokens.
Cloud deployments should configure DATABASE_URL (PostgreSQL).
"""
import json
from datetime import datetime, timezone
import pandas as pd
from sqlalchemy import create_engine, text

_TABLE = 'mambo_candidates'

def configured(url):
    return bool(url)

def _engine(url):
    if not url:
        raise ValueError('请先配置 DATABASE_URL，云端不使用临时文件作为长期存储。')
    if url.startswith('postgres://'):
        url = 'postgresql://' + url[len('postgres://'):]
    return create_engine(url, pool_pre_ping=True, connect_args={'connect_timeout': 10} if url.startswith('postgresql') else {})

def save(dataframe, url):
    engine = _engine(url)
    rows = dataframe.where(pd.notnull(dataframe), None).to_dict('records')
    with engine.begin() as conn:
        conn.execute(text(f'CREATE TABLE IF NOT EXISTS {_TABLE} (username VARCHAR(100) PRIMARY KEY, payload TEXT NOT NULL, updated_at TEXT NOT NULL)'))
        # Upsert: never delete unrelated records from another browser session.
        for row in rows:
            username = str(row.get('username') or '').strip().lstrip('@').lower()
            if not username: continue
            safe = {k: (None if v is None else str(v)) for k, v in row.items() if 'token' not in k.lower() and 'password' not in k.lower()}
            conn.execute(text(f'''INSERT INTO {_TABLE}(username,payload,updated_at) VALUES (:username,:payload,:updated_at)
            ON CONFLICT(username) DO UPDATE SET payload=:payload,updated_at=:updated_at'''),
            {'username':username,'payload':json.dumps(safe, ensure_ascii=False), 'updated_at':datetime.now(timezone.utc).isoformat()})
    engine.dispose()
    return len(rows)

def load(url):
    if not url: return pd.DataFrame()
    engine = _engine(url)
    with engine.begin() as conn:
        conn.execute(text(f'CREATE TABLE IF NOT EXISTS {_TABLE} (username VARCHAR(100) PRIMARY KEY, payload TEXT NOT NULL, updated_at TEXT NOT NULL)'))
        rows = conn.execute(text(f'SELECT payload FROM {_TABLE} ORDER BY updated_at DESC')).fetchall()
    engine.dispose()
    return pd.DataFrame([json.loads(row[0]) for row in rows])
