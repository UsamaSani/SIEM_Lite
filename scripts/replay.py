import argparse
import time
from datetime import datetime


def replay_log(input_file: str, rate: int, duration: int = 0):
    """
    Replay log file to stdout at specified rate.
    
    Args:
        input_file: Path to log file
        rate: Events per second (0 = unlimited)
        duration: Duration in seconds (0 = until EOF)
    """
    print(f"▶️  Replaying: {input_file} at {rate} events/sec", flush=True)
    
    start_time = time.time()
    events_sent = 0
    
    with open(input_file, 'r') as f:
        while True:
            line = f.readline()
            
            # Loop back if EOF
            if not line:
                f.seek(0)
                continue
            
            # Output event
            print(line.strip())
            events_sent += 1
            
            # Rate limiting
            if rate > 0:
                time.sleep(1.0 / rate)
            
            # Check duration
            if duration > 0 and (time.time() - start_time) >= duration:
                break
    
    print(f"[OK] Replayed {events_sent:,} events", flush=True)


def main():
    parser = argparse.ArgumentParser(description='Replay logs')
    parser.add_argument('--input', required=True, help='Input log file')
    parser.add_argument('--rate', type=int, default=100, help='Events per second')
    parser.add_argument('--duration', type=int, default=0, 
                       help='Duration in seconds (0=unlimited)')
    
    args = parser.parse_args()
    
    replay_log(args.input, args.rate, args.duration)


if __name__ == '__main__':
    main()

