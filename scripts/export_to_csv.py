import argparse
import csv
import sqlite3
from pathlib import Path
from typing import Optional


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def export_to_csv(db_path: str, output_csv: str, limit: int = 0) -> int:
    """Export rows from the `events` table to CSV.

    Returns the number of rows written.
    """
    print(f"📤 Exporting events from: {db_path}")
    conn = _connect(db_path)
    cur = conn.cursor()

    # Ensure output directory exists
    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)

    # Get columns for events table
    try:
        cur.execute("PRAGMA table_info(events)")
        cols = [r[1] for r in cur.fetchall()]
        if not cols:
            raise RuntimeError("Table 'events' not found or has no columns")
    except Exception as e:
        conn.close()
        raise

    query = "SELECT * FROM events"
    if limit and limit > 0:
        query += f" LIMIT {int(limit)}"

    cur.execute(query)

    count = 0
    with open(output_csv, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(cols)
        for row in cur:
            writer.writerow([row[c] for c in cols])
            count += 1
            if count % 10000 == 0:
                print(f"  Exported {count:,} rows...")

    conn.close()
    print(f"[OK] Exported {count:,} rows to: {output_csv}")
    return count


def export_alerts(db_path: str, output_csv: str) -> int:
    """Export rows from the `alerts` table to CSV.

    Returns the number of rows written.
    """
    print(f"🚨 Exporting alerts from: {db_path}")
    conn = _connect(db_path)
    cur = conn.cursor()

    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)

    # Try to fetch column names from alerts table
    cur.execute("PRAGMA table_info(alerts)")
    cols = [r[1] for r in cur.fetchall()]
    if not cols:
        # Fallback to a sensible header if table doesn't exist
        cols = ["id", "alert_type", "ip", "count", "window_start", "window_end", "created_at"]

    cur.execute(f"SELECT * FROM alerts ORDER BY created_at DESC")

    count = 0
    with open(output_csv, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(cols)
        for row in cur:
            # row may be sqlite3.Row; ensure order matches cols
            try:
                writer.writerow([row[c] for c in cols])
            except Exception:
                writer.writerow(list(row))
            count += 1

    conn.close()
    print(f"[OK] Exported {count:,} alerts to: {output_csv}")
    return count


def export_summary(db_path: str, output_csv: str) -> int:
    """Write a small summary CSV with key/value pairs and a top-IP section.

    Returns the number of rows in the summary CSV (not including section separators).
    """
    print(f"[*] Generating summary from: {db_path}")
    conn = _connect(db_path)
    cur = conn.cursor()

    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)

    rows_written = 0
    with open(output_csv, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)

        # Total events
        try:
            cur.execute("SELECT COUNT(*) as cnt FROM events")
            total = cur.fetchone()[0]
        except Exception:
            total = 0
        writer.writerow(["Total Events", total])
        rows_written += 1

        # Events by status (top 10)
        writer.writerow([])
        writer.writerow(["Status", "Count"])
        rows_written += 1
        try:
            cur.execute(
                "SELECT status, COUNT(*) as cnt FROM events GROUP BY status ORDER BY cnt DESC LIMIT 10"
            )
            for r in cur.fetchall():
                writer.writerow([r[0], r[1]])
                rows_written += 1
        except Exception:
            pass

        # Top IPs
        writer.writerow([])
        writer.writerow(["Top IP", "Count"])
        rows_written += 1
        try:
            cur.execute("SELECT ip, COUNT(*) as cnt FROM events GROUP BY ip ORDER BY cnt DESC LIMIT 50")
            for r in cur.fetchall():
                writer.writerow([r[0], r[1]])
                rows_written += 1
        except Exception:
            pass

    conn.close()
    print(f"[OK] Summary written to: {output_csv}")
    return rows_written


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Export SIEM-LITE SQLite data to CSV")
    p.add_argument("db", help="Path to SQLite database file")
    p.add_argument("mode", choices=["events", "alerts", "summary"], help="Export mode")
    p.add_argument("out", help="Output CSV file path")
    p.add_argument("--limit", type=int, default=0, help="Limit number of rows when exporting events")
    return p.parse_args()


def main(argv: Optional[argparse.Namespace] = None) -> None:
    args = _parse_args() if argv is None else argv

    if args.mode == "events":
        export_to_csv(args.db, args.out, limit=getattr(args, "limit", 0))
    elif args.mode == "alerts":
        export_alerts(args.db, args.out)
    elif args.mode == "summary":
        export_summary(args.db, args.out)


if __name__ == "__main__":
    main()
