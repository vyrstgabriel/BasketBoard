"""
run_queries.py — execute every .sql file in queries/ against basketboard.db
and save each result to results/<name>.csv.

Run: python src/run_queries.py
"""

import sqlite3
import pandas as pd
from pathlib import Path

ROOT        = Path(__file__).parent.parent
DB_PATH     = ROOT / "data" / "basketboard.db"
QUERIES_DIR = ROOT / "queries"
RESULTS_DIR = ROOT / "results"

RESULTS_DIR.mkdir(exist_ok=True)


def run():
    con = sqlite3.connect(DB_PATH)

    sql_files = sorted(QUERIES_DIR.glob("*.sql"))
    for sql_file in sql_files:
        sql = sql_file.read_text()
        df  = pd.read_sql_query(sql, con)

        out = RESULTS_DIR / f"{sql_file.stem}.csv"
        df.to_csv(out, index=False)
        print(f"{sql_file.name:45s} → {len(df):>5} rows  →  {out.name}")

    con.close()


if __name__ == "__main__":
    run()
