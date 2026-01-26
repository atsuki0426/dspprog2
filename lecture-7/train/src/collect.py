import argparse
import json
import re
import sqlite3
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests

DEFAULT_URL = (
    "https://api-public.odpt.org/api/v4/odpt:TrainInformation"
    "?odpt:operator=odpt.Operator:Toei"
)

DB_PATH_DEFAULT = "data/transport_pretty.db"

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS train_info (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  railway_name TEXT NOT NULL,
  is_delayed INTEGER NOT NULL CHECK(is_delayed IN (0,1)),
  delay_minutes INTEGER,
  delay_label TEXT NOT NULL,
  info_text TEXT,
  raw_json TEXT NOT NULL
);
"""

INDEX_SQLS = [
    "CREATE INDEX IF NOT EXISTS idx_train_info_created_at ON train_info(created_at);",
    "CREATE INDEX IF NOT EXISTS idx_train_info_railway_name ON train_info(railway_name);",
    "CREATE INDEX IF NOT EXISTS idx_train_info_is_delayed ON train_info(is_delayed);",
]

JST = timezone(timedelta(hours=9))


def railway_name_from_id(railway: Optional[str]) -> Optional[str]:
    if not railway:
        return None
    return railway.replace("odpt.Railway:Toei.", "")


def parse_delay_fields(text: Optional[str]) -> tuple[int, Optional[int], str]:
    """
    is_delayed: 0/1
    delay_minutes: 分数が取れたらint、取れなければNone
    delay_label: none / 15+ / unknown など
    """
    if not text:
        return 0, None, "unknown"

    if "遅延はありません" in text or "平常" in text or "通常通り" in text:
        return 0, 0, "none"

    m = re.search(r"(\d+)\s*分以上", text)
    if m:
        minutes = int(m.group(1))
        if "ありません" in text:
            return 0, 0, "none"
        return 1, minutes, f"{minutes}+"

    if any(k in text for k in ["遅延", "見合わせ", "運休", "運転見合わせ", "運転を見合わせ", "大幅な遅れ"]):
        return 1, None, "unknown"

    return 0, 0, "none"


def fetch_json(url: str, timeout: int = 20) -> list[dict]:
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        raise ValueError("Unexpected response (not a list)")
    return data


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(CREATE_SQL)
    for sql in INDEX_SQLS:
        conn.execute(sql)
    conn.commit()


def insert_snapshot(conn: sqlite3.Connection, created_at: str, items: list[dict]) -> int:
    cur = conn.cursor()
    rows = 0

    for item in items:
        railway = item.get("odpt:railway")
        railway_name = railway_name_from_id(railway)
        if not railway_name:
            continue

        info_text = (item.get("odpt:trainInformationText") or {}).get("ja")
        is_delayed, delay_minutes, delay_label = parse_delay_fields(info_text)
        raw_json = json.dumps(item, ensure_ascii=False)

        cur.execute(
            """INSERT INTO train_info
               (created_at, railway_name, is_delayed, delay_minutes, delay_label, info_text, raw_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (created_at, railway_name, is_delayed, delay_minutes, delay_label, info_text, raw_json),
        )
        rows += 1

    conn.commit()
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DB_PATH_DEFAULT)
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--interval", type=int, default=600)
    ap.add_argument("--duration", type=int, default=3600)
    ap.add_argument("--timeout", type=int, default=20)
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    init_db(conn)

    start = time.time()
    loops = 0

    try:
        while True:
            # JSTの 'YYYY-MM-DD HH:MM:SS' で保存（画像のイメージに合わせる）
            created_at = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")

            try:
                items = fetch_json(args.url, timeout=args.timeout)
                n = insert_snapshot(conn, created_at, items)
                loops += 1
                print(f"[{loops}] created_at={created_at} inserted={n}")
            except Exception as e:
                print(f"[{loops+1}] ERROR: {e}")

            if time.time() - start >= args.duration:
                break

            time.sleep(args.interval)
    finally:
        conn.close()


if __name__ == "__main__":
    main()