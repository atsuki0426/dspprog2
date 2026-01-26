import argparse
import sqlite3
import csv
import os

def write_csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="SQLite DB path")
    ap.add_argument("--table", default="train_info", help="table name")
    ap.add_argument("--outdir", default="data", help="output dir")
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    cur = conn.cursor()

    # table check
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (args.table,))
    if cur.fetchone() is None:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = [r[0] for r in cur.fetchall()]
        raise SystemExit(f"ERROR: table '{args.table}' not found. tables={tables}")

    q1 = f"""
      SELECT
        railway_name AS railway,
        COUNT(*) AS n,
        SUM(is_delayed) AS n_abnormal,
        ROUND(1.0 * SUM(is_delayed) / COUNT(*), 4) AS abnormal_rate
      FROM {args.table}
      GROUP BY railway_name
      ORDER BY abnormal_rate DESC, n DESC;
    """
    cur.execute(q1)
    rows1 = cur.fetchall()

    q2 = f"""
      SELECT
        CAST(SUBSTR(created_at, 12, 2) AS INTEGER) AS hour_jst,
        COUNT(*) AS n,
        SUM(is_delayed) AS n_abnormal,
        ROUND(1.0 * SUM(is_delayed) / COUNT(*), 4) AS abnormal_rate
      FROM {args.table}
      GROUP BY hour_jst
      ORDER BY hour_jst;
    """
    cur.execute(q2)
    rows2 = cur.fetchall()

    conn.close()

    out1 = os.path.join(args.outdir, "summary_by_railway.csv")
    out2 = os.path.join(args.outdir, "summary_by_hour_jst.csv")

    write_csv(out1, ["railway", "n", "n_abnormal", "abnormal_rate"], rows1)
    write_csv(out2, ["hour_jst", "n", "n_abnormal", "abnormal_rate"], rows2)

    print("Saved:")
    print(" -", out1)
    print(" -", out2)

if __name__ == "__main__":
    main()
