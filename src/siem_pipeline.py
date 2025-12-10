import argparse
import signal
import sys
import time
import sqlite3
import csv
from datetime import datetime, timedelta
from multiprocessing import Process, Queue, Event, Manager
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict, deque

import psutil

from utils import parse_apache_log, enrich_ip, enrich_user_agent, is_suspicious


# Global shutdown event
shutdown_event = Event()


def signal_handler(signum, frame):
    """Handle SIGINT (Ctrl+C) gracefully."""
    print("\\n🛑 Shutdown signal received. Flushing queues...")
    shutdown_event.set()


def setup_database(db_path: str) -> sqlite3.Connection:
    """
    Initialize SQLite database with proper schema.
    
    Args:
        db_path: Path to SQLite database
        
    Returns:
        Database connection
    """
    conn = sqlite3.connect(db_path, check_same_thread=False)
    
    # Enable WAL mode for better concurrency
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    
    # Create events table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            method TEXT,
            url TEXT,
            status INTEGER,
            bytes INTEGER,
            referer TEXT,
            user_agent TEXT,
            browser TEXT,
            os TEXT,
            ip_class TEXT,
            suspicious BOOLEAN,
            ingested_at TEXT NOT NULL,
            indexed_at TEXT
        )
    """)
    
    # Create alerts table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_type TEXT NOT NULL,
            ip TEXT,
            count INTEGER,
            window_start TEXT,
            window_end TEXT,
            created_at TEXT NOT NULL
        )
    """)
    
    # Create indices
    conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ip ON events(ip)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON events(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_suspicious ON events(suspicious)")
    
    conn.commit()
    return conn


def ingestor_process(
    input_file: str,
    ingestion_queue: Queue,
    rate: int,
    run_time: int
):
    """
    Read logs from file and push to ingestion queue.
    
    Args:
        input_file: Path to log file
        ingestion_queue: Queue for raw log lines
        rate: Events per second (0 = unlimited)
        run_time: Duration to run in seconds
    """
    print(f"[*] Ingestor starting: {input_file}, rate={rate} events/sec")
    
    start_time = time.time()
    events_sent = 0
    batch_size = max(1, rate // 10) if rate > 0 else 100
    batch_interval = 0.1 if rate > 0 else 0.01
    
    try:
        with open(input_file, 'r') as f:
            while not shutdown_event.is_set():
                lines = []
                for _ in range(batch_size):
                    line = f.readline()
                    if not line:
                        f.seek(0)
                        line = f.readline()
                        if not line:
                            break
                    if line.strip():
                        lines.append(line.strip())
                
                if not lines:
                    break
                
                # Send batch
                for line in lines:
                    message = {
                        'line': line,
                        'ingested_at': datetime.now()
                    }
                    ingestion_queue.put(message)
                    events_sent += 1
                
                # Rate limiting (batch-based)
                if rate > 0:
                    time.sleep(batch_interval)
                
                # Check runtime
                if run_time > 0 and (time.time() - start_time) >= run_time:
                    break
    
    except Exception as e:
        print(f"❌ Ingestor error: {e}")
    
    finally:
        print(f"[*] Ingestor finished: {events_sent} events sent")


def parser_worker(
    worker_id: int,
    ingestion_queue: Queue,
    parsed_queue: Queue
):
    """
    Parse and enrich log lines.
    
    Args:
        worker_id: Worker identifier
        ingestion_queue: Input queue with raw logs
        parsed_queue: Output queue with parsed events
    """
    print(f"[*] Parser worker {worker_id} starting")
    
    processed = 0
    
    try:
        while not shutdown_event.is_set():
            try:
                message = ingestion_queue.get(timeout=1)
                line = message['line']
                ingested_at = message['ingested_at']
                
                # Parse log line
                event = parse_apache_log(line)
                
                if event:
                    # Enrich event
                    event['ingested_at'] = ingested_at.isoformat()
                    
                    # IP enrichment (cached)
                    ip_data = enrich_ip(event['ip'])
                    event.update(ip_data)
                    
                    # User-agent enrichment
                    ua_data = enrich_user_agent(event.get('user_agent', ''))
                    event.update(ua_data)
                    
                    # Suspicious flag
                    event['suspicious'] = is_suspicious(event)
                    
                    parsed_queue.put(event)
                    processed += 1
                
            except Exception:
                # Queue timeout or shutdown
                if shutdown_event.is_set():
                    break
    
    except Exception as e:
        print(f"❌ Parser worker {worker_id} error: {e}")
    
    finally:
        print(f"[*] Parser worker {worker_id} finished: {processed} events processed")


def indexer_process(
    parsed_queue: Queue,
    db_path: str,
    batch_size: int,
    alert_queue: Queue
):
    """
    Batch insert events into database.
    
    Args:
        parsed_queue: Input queue with parsed events
        db_path: SQLite database path
        batch_size: Number of events per batch
        alert_queue: Queue for alerts
    """
    print(f"[*] Indexer starting: batch_size={batch_size}")
    
    conn = setup_database(db_path)
    cursor = conn.cursor()
    
    batch = []
    indexed_count = 0
    
    # For alert detection
    error_tracking = defaultdict(lambda: deque(maxlen=100))
    
    try:
        while not shutdown_event.is_set():
            try:
                event = parsed_queue.get(timeout=1)
                
                # Add indexed timestamp
                event['indexed_at'] = datetime.now().isoformat()
                
                batch.append(event)
                
                # Track errors for alerting
                if event.get('suspicious'):
                    error_tracking[event['ip']].append(datetime.fromisoformat(event['indexed_at']))
                
                # Flush batch
                if len(batch) >= batch_size:
                    _flush_batch(cursor, conn, batch)
                    indexed_count += len(batch)
                    batch.clear()
                    
                    # Check for alerts
                    _check_alerts(error_tracking, alert_queue, cursor, conn)
            
            except Exception:
                # Queue timeout or shutdown
                if shutdown_event.is_set():
                    break
    
    except Exception as e:
        print(f"❌ Indexer error: {e}")
    
    finally:
        # Flush remaining batch
        if batch:
            _flush_batch(cursor, conn, batch)
            indexed_count += len(batch)
        
        conn.close()
        print(f"[*] Indexer finished: {indexed_count} events indexed")


def _flush_batch(cursor, conn, batch: List[Dict]):
    """Insert batch of events into database."""
    cursor.executemany(
        """INSERT INTO events 
           (ip, timestamp, method, url, status, bytes, referer, user_agent, 
            browser, os, ip_class, suspicious, ingested_at, indexed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                e['ip'], e['timestamp'].isoformat(), e.get('method', ''),
                e.get('url', ''), e.get('status', 0), e.get('bytes', 0),
                e.get('referer', ''), e.get('user_agent', ''),
                e.get('browser', ''), e.get('os', ''),
                e.get('ip_class', ''), e.get('suspicious', False),
                e['ingested_at'], e['indexed_at']
            )
            for e in batch
        ]
    )
    conn.commit()


def _check_alerts(error_tracking: Dict, alert_queue: Queue, cursor, conn):
    """Check for alert conditions and create alerts."""
    now = datetime.now()
    window = timedelta(seconds=60)
    
    for ip, timestamps in error_tracking.items():
        # Count errors in last 60 seconds
        recent_errors = sum(1 for ts in timestamps if now - ts <= window)
        
        if recent_errors >= 5:
            alert = {
                'alert_type': 'HIGH_ERROR_RATE',
                'ip': ip,
                'count': recent_errors,
                'window_start': (now - window).isoformat(),
                'window_end': now.isoformat(),
                'created_at': now.isoformat()
            }
            
            # Insert alert
            cursor.execute(
                """INSERT INTO alerts 
                   (alert_type, ip, count, window_start, window_end, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (alert['alert_type'], alert['ip'], alert['count'],
                 alert['window_start'], alert['window_end'], alert['created_at'])
            )
            conn.commit()
            
            alert_queue.put(alert)


def metrics_collector(
    ingestion_queue: Queue,
    parsed_queue: Queue,
    alert_queue: Queue,
    metrics_file: str,
    interval: int = 5
):
    """
    Collect and persist metrics.
    
    Args:
        ingestion_queue: Ingestion queue for size monitoring
        parsed_queue: Parsed queue for size monitoring
        alert_queue: Alert queue for count tracking
        metrics_file: Output CSV file
        interval: Collection interval in seconds
    """
    print(f"[*] Metrics collector starting: interval={interval}s")
    
    process = psutil.Process()
    start_time = time.time()
    last_event_count = 0
    alerts_count = 0
    
    with open(metrics_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'timestamp', 'runtime_sec', 'events_processed', 
            'ingestion_queue_size', 'parsed_queue_size',
            'cpu_percent', 'memory_mb', 'throughput_eps', 'alerts_count'
        ])
        
        try:
            while not shutdown_event.is_set():
                time.sleep(interval)
                
                # Collect metrics
                runtime = time.time() - start_time
                cpu = process.cpu_percent(interval=0.1)
                memory = process.memory_info().rss / 1024 / 1024  # MB
                
                ingestion_size = ingestion_queue.qsize() if hasattr(ingestion_queue, 'qsize') else 0
                parsed_size = parsed_queue.qsize() if hasattr(parsed_queue, 'qsize') else 0
                
                # Drain alert queue
                while not alert_queue.empty():
                    try:
                        alert_queue.get_nowait()
                        alerts_count += 1
                    except:
                        break
                
                # Calculate throughput (approximate)
                current_count = last_event_count + parsed_size
                throughput = current_count / runtime if runtime > 0 else 0
                
                writer.writerow([
                    datetime.now().isoformat(),
                    f"{runtime:.1f}",
                    current_count,
                    ingestion_size,
                    parsed_size,
                    f"{cpu:.1f}",
                    f"{memory:.1f}",
                    f"{throughput:.1f}",
                    alerts_count
                ])
                f.flush()
        
        except Exception as e:
            print(f"❌ Metrics collector error: {e}")
        
        finally:
            print(f"[*] Metrics collector finished")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='SIEM-lite Log Processor')
    parser.add_argument('--input', required=True, help='Input log file')
    parser.add_argument('--workers', type=int, default=4, help='Number of parser workers')
    parser.add_argument('--rate', type=int, default=0, help='Events per second (0=unlimited)')
    parser.add_argument('--batch', type=int, default=100, help='Indexer batch size')
    parser.add_argument('--run-time', type=int, default=60, help='Runtime in seconds')
    parser.add_argument('--db', required=True, help='Output database path')
    parser.add_argument('--metrics', required=True, help='Output metrics CSV')
    
    args = parser.parse_args()
    
    # Validate input file
    if not Path(args.input).exists():
        print(f"❌ Input file not found: {args.input}")
        sys.exit(1)
    
    # Create output directories
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    Path(args.metrics).parent.mkdir(parents=True, exist_ok=True)
    
    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    print("="*60)
    print("[*] SIEM-lite Pipeline Starting")
    print("="*60)
    print(f"Input: {args.input}")
    print(f"Workers: {args.workers}")
    print(f"Rate: {args.rate} events/sec" if args.rate > 0 else "Rate: Unlimited")
    print(f"Batch size: {args.batch}")
    print(f"Runtime: {args.run_time}s")
    print(f"Database: {args.db}")
    print(f"Metrics: {args.metrics}")
    print("="*60)
    
    # Create queues (bounded to prevent memory issues)
    manager = Manager()
    ingestion_queue = manager.Queue(maxsize=args.workers * 100)
    parsed_queue = manager.Queue(maxsize=args.batch * 10)
    alert_queue = manager.Queue()
    
    # Start processes
    processes = []
    
    # Ingestor
    p_ingestor = Process(
        target=ingestor_process,
        args=(args.input, ingestion_queue, args.rate, args.run_time)
    )
    p_ingestor.start()
    processes.append(p_ingestor)
    
    # Parser workers
    for i in range(args.workers):
        p = Process(
            target=parser_worker,
            args=(i, ingestion_queue, parsed_queue)
        )
        p.start()
        processes.append(p)
    
    # Indexer
    p_indexer = Process(
        target=indexer_process,
        args=(parsed_queue, args.db, args.batch, alert_queue)
    )
    p_indexer.start()
    processes.append(p_indexer)
    
    # Metrics collector
    p_metrics = Process(
        target=metrics_collector,
        args=(ingestion_queue, parsed_queue, alert_queue, args.metrics)
    )
    p_metrics.start()
    processes.append(p_metrics)
    
    # Wait for completion or signal
    start = time.time()
    try:
        while time.time() - start < args.run_time and not shutdown_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    
    # Shutdown
    print("\n[!] Initiating shutdown...")
    shutdown_event.set()
    
    # Wait for processes to finish
    for p in processes:
        p.join(timeout=2)
        if p.is_alive():
            print(f"[WARNING] Force terminating {p.name}")
            p.terminate()
            p.join(timeout=1)
    
    # Print summary
    print("\n" + "="*60)
    print("[*] Pipeline Summary")
    print("="*60)
    
    conn = sqlite3.connect(args.db)
    cursor = conn.cursor()
    
    total_events = cursor.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    total_alerts = cursor.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    
    runtime = time.time() - start
    throughput = total_events / runtime if runtime > 0 else 0
    
    print(f"Runtime: {runtime:.1f}s")
    print(f"Total events: {total_events:,}")
    print(f"Total alerts: {total_alerts}")
    print(f"Throughput: {throughput:.1f} events/sec")
    
    # Latency statistics
    cursor.execute("""
        SELECT 
            AVG((julianday(indexed_at) - julianday(ingested_at)) * 86400000) as avg_latency_ms,
            MIN((julianday(indexed_at) - julianday(ingested_at)) * 86400000) as min_latency_ms,
            MAX((julianday(indexed_at) - julianday(ingested_at)) * 86400000) as max_latency_ms
        FROM events
        WHERE indexed_at IS NOT NULL
    """)
    
    latency_stats = cursor.fetchone()
    if latency_stats and latency_stats[0]:
        print(f"Avg latency: {latency_stats[0]:.1f}ms")
        print(f"Min/Max latency: {latency_stats[1]:.1f}ms / {latency_stats[2]:.1f}ms")
    
    conn.close()
    
    print("="*60)
    print("[OK] Pipeline completed successfully")
    print("="*60)


if __name__ == '__main__':
    main()