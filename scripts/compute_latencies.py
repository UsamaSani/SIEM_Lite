import argparse
import sqlite3
import json
import numpy as np


def compute_latencies(db_path: str, output_file: str = None):
    """
    Compute latency statistics.
    
    Args:
        db_path: Path to SQLite database
        output_file: Optional output JSON file
    """
    print(f"[*] Computing latencies from: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get latencies in milliseconds
    cursor.execute("""
        SELECT (julianday(indexed_at) - julianday(ingested_at)) * 86400000 as latency_ms
        FROM events
        WHERE indexed_at IS NOT NULL AND ingested_at IS NOT NULL
    """)
    
    latencies = [row[0] for row in cursor.fetchall()]
    
    if not latencies:
        print("[WARNING] No latency data found")
        return
    
    # Compute percentiles
    percentiles = {
        'count': len(latencies),
        'mean': float(np.mean(latencies)),
        'median': float(np.median(latencies)),
        'std': float(np.std(latencies)),
        'min': float(np.min(latencies)),
        'max': float(np.max(latencies)),
        'p50': float(np.percentile(latencies, 50)),
        'p90': float(np.percentile(latencies, 90)),
        'p95': float(np.percentile(latencies, 95)),
        'p99': float(np.percentile(latencies, 99)),
    }
    
    # Print results
    print("\\nLatency Statistics (ms):")
    print(f"  Count: {percentiles['count']:,}")
    print(f"  Mean:  {percentiles['mean']:.2f}")
    print(f"  Median: {percentiles['median']:.2f}")
    print(f"  Std:   {percentiles['std']:.2f}")
    print(f"  Min:   {percentiles['min']:.2f}")
    print(f"  Max:   {percentiles['max']:.2f}")
    print(f"  P50:   {percentiles['p50']:.2f}")
    print(f"  P90:   {percentiles['p90']:.2f}")
    print(f"  P95:   {percentiles['p95']:.2f}")
    print(f"  P99:   {percentiles['p99']:.2f}")
    
    # Save to file
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(percentiles, f, indent=2)
        print(f"\n[OK] Saved to: {output_file}")
    
    conn.close()


def main():
    parser = argparse.ArgumentParser(description='Compute latency statistics')
    parser.add_argument('--db', required=True, help='Database file')
    parser.add_argument('--output', help='Output JSON file (optional)')
    
    args = parser.parse_args()
    
    compute_latencies(args.db, args.output)


if __name__ == '__main__':
    main()