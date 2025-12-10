import argparse
import itertools
import subprocess
import json
from pathlib import Path
from datetime import datetime


def run_experiment(input_file: str, workers: int, rate: int, batch: int, 
                   duration: int, output_dir: str) -> dict:
    """
    Run single experiment with given parameters.
    
    Returns:
        Dictionary with experiment results
    """
    exp_id = f"w{workers}_r{rate}_b{batch}"
    db_file = f"{output_dir}/events_{exp_id}.db"
    metrics_file = f"{output_dir}/metrics_{exp_id}.csv"
    
    print(f"\\n{'='*60}")
    print(f"[TEST] Experiment: {exp_id}")
    print(f"   Workers: {workers}, Rate: {rate}, Batch: {batch}")
    print(f"{'='*60}")
    
    # Run pipeline
    cmd = [
        'python', 'src/siem_pipeline.py',
        '--input', input_file,
        '--workers', str(workers),
        '--rate', str(rate),
        '--batch', str(batch),
        '--run-time', str(duration),
        '--db', db_file,
        '--metrics', metrics_file
    ]
    
    start = datetime.now()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=duration+30)
        success = result.returncode == 0
    except subprocess.TimeoutExpired:
        success = False
        result = None
    
    end = datetime.now()
    
    return {
        'exp_id': exp_id,
        'workers': workers,
        'rate': rate,
        'batch': batch,
        'duration': duration,
        'success': success,
        'start_time': start.isoformat(),
        'end_time': end.isoformat(),
        'db_file': db_file,
        'metrics_file': metrics_file
    }


def main():
    parser = argparse.ArgumentParser(description='Run experiment grid')
    parser.add_argument('--input', required=True, help='Input log file')
    parser.add_argument('--workers', nargs='+', type=int, default=[1, 2, 4, 8],
                       help='Worker counts to test')
    parser.add_argument('--rates', nargs='+', type=int, default=[200, 500, 1000],
                       help='Ingestion rates to test')
    parser.add_argument('--batches', nargs='+', type=int, default=[50, 100, 200],
                       help='Batch sizes to test')
    parser.add_argument('--duration', type=int, default=60,
                       help='Duration per experiment')
    parser.add_argument('--output-dir', default='results',
                       help='Output directory')
    
    args = parser.parse_args()
    
    # Create output directory
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    
    # Generate parameter combinations
    combinations = list(itertools.product(args.workers, args.rates, args.batches))
    
    print(f"\n[*] Running {len(combinations)} experiments...")
    print(f"   Workers: {args.workers}")
    print(f"   Rates: {args.rates}")
    print(f"   Batches: {args.batches}")
    print(f"   Duration: {args.duration}s per experiment")
    
    results = []
    
    for i, (workers, rate, batch) in enumerate(combinations, 1):
        print(f"\\n[{i}/{len(combinations)}] ", end='')
        
        result = run_experiment(
            args.input, workers, rate, batch, 
            args.duration, args.output_dir
        )
        
        results.append(result)
    
    # Save summary
    summary_file = f"{args.output_dir}/experiments_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\\n{'='*60}")
    print(f"[OK] All experiments complete!")
    print(f"[*] Summary saved to: {summary_file}")
    print(f"{'='*60}")
    
    # Print success rate
    successful = sum(1 for r in results if r['success'])
    print(f"\\nSuccess rate: {successful}/{len(results)} experiments")


if __name__ == '__main__':
    main()