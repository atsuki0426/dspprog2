# src/fetch_once.py
import json
import sqlite3
from datetime import datetime, timezone

import requests

URL = "https://api-public.odpt.org/api/v4/odpt:TrainInformation?odpt:operator=odpt.Operator:Toei"
DB_PATH = "data/transport.sqlite"

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS train_info_snapshot (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fetched_at TEXT NOT NULL,
  dc_date TEXT,
  valid_until TEXT,
  railway TEXT,
  text_ja TEXT,
  status_flag INTEGER NOT NULL,
  raw_json TEXT NOT NULL
);
"""

def status_from_text(text: str | None) -> int:
  if not text:
    return 0

  # まず「平常」系（否定文・平常運転）を優先して0にする
  normal_patterns = [
    "遅延はありません",
    "見合わせはありません",
    "運休はありません",
    "平常通り",
    "平常運転",
    "通常通り",
  ]
  if any(p in text for p in normal_patterns):
    return 0

  # 次に「異常」系
  abnormal_keywords = [
    "遅延",
    "見合わせ",
    "運休",
    "運転を見合わせ",
    "運転見合わせ",
    "大幅な遅れ",
  ]
  return 1 if any(k in text for k in abnormal_keywords) else 0

def main() -> None:
  r = requests.get(URL, timeout=20)
  r.raise_for_status()
  data = r.json()
  if not isinstance(data, list):
    raise ValueError("Unexpected response: not a list")

  fetched_at = datetime.now(timezone.utc).isoformat()

  conn = sqlite3.connect(DB_PATH)
  cur = conn.cursor()
  cur.execute(CREATE_SQL)

  rows = 0
  for item in data:
    dc_date = item.get("dc:date")
    valid_until = item.get("dct:valid")
    railway = item.get("odpt:railway")
    text_ja = (item.get("odpt:trainInformationText") or {}).get("ja")

    status_flag = status_from_text(text_ja)
    raw_json = json.dumps(item, ensure_ascii=False)

    cur.execute(
      """INSERT INTO train_info_snapshot
         (fetched_at, dc_date, valid_until, railway, text_ja, status_flag, raw_json)
         VALUES (?, ?, ?, ?, ?, ?, ?)""",
      (fetched_at, dc_date, valid_until, railway, text_ja, status_flag, raw_json),
    )
    rows += 1

  conn.commit()
  conn.close()
  print(f"Inserted {rows} rows into {DB_PATH}")

if __name__ == "__main__":
  main()
  
