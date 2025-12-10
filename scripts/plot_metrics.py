import argparse
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import glob


sns.set_style("whitegrid")
sns.set_palette("husl")


def plot_throughput(metrics_files: list, output_dir: str):
    """Plot throughput over time for all experiments."""
    plt.figure(figsize=(12, 6))
    
    for metrics_file in metrics_files:
        df = pd.read_csv(metrics_file)
        label = Path(metrics_file).stem.replace('metrics_', '')
        plt.plot(df['runtime_sec'], df['throughput_eps'], label=label, marker='o')
    
    plt.xlabel('Runtime (seconds)')
    plt.ylabel('Throughput (events/sec)')
    plt.title('Throughput Over Time')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(f"{output_dir}/throughput.png", dpi=300, bbox_inches='tight')
    print(f"[OK] Saved: {output_dir}/throughput.png")
    plt.close()


def plot_queue_sizes(metrics_files: list, output_dir: str):
    """Plot queue sizes (backpressure indicator)."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    for metrics_file in metrics_files:
        df = pd.read_csv(metrics_file)
        label = Path(metrics_file).stem.replace('metrics_', '')
        
        axes[0].plot(df['runtime_sec'], df['ingestion_queue_size'], 
                    label=label, marker='o')
        axes[1].plot(df['runtime_sec'], df['parsed_queue_size'], 
                    label=label, marker='o')
    
    axes[0].set_xlabel('Runtime (seconds)')
    axes[0].set_ylabel('Queue Size')
    axes[0].set_title('Ingestion Queue Size')
    axes[0].legend()
    
    axes[1].set_xlabel('Runtime (seconds)')
    axes[1].set_ylabel('Queue Size')
    axes[1].set_title('Parsed Queue Size')
    axes[1].legend()
    
    plt.tight_layout()
    plt.savefig(f"{output_dir}/queue_sizes.png", dpi=300)
    print(f"[OK] Saved: {output_dir}/queue_sizes.png")
    plt.close()


def plot_resource_usage(metrics_files: list, output_dir: str):
    """Plot CPU and memory usage."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    for metrics_file in metrics_files:
        df = pd.read_csv(metrics_file)
        label = Path(metrics_file).stem.replace('metrics_', '')
        
        axes[0].plot(df['runtime_sec'], df['cpu_percent'], 
                    label=label, marker='o')
        axes[1].plot(df['runtime_sec'], df['memory_mb'], 
                    label=label, marker='o')
    
    axes[0].set_xlabel('Runtime (seconds)')
    axes[0].set_ylabel('CPU %')
    axes[0].set_title('CPU Utilization')
    axes[0].legend()
    
    axes[1].set_xlabel('Runtime (seconds)')
    axes[1].set_ylabel('Memory (MB)')
    axes[1].set_title('Memory Usage')
    axes[1].legend()
    
    plt.tight_layout()
    plt.savefig(f"{output_dir}/resource_usage.png", dpi=300)
    print(f"[OK] Saved: {output_dir}/resource_usage.png")
    plt.close()


def plot_scalability(metrics_dir: str, output_dir: str):
    """Plot scalability analysis (workers vs throughput)."""
    # Find all metrics files
    metrics_files = glob.glob(f"{metrics_dir}/metrics_w*.csv")
    
    if not metrics_files:
        print("[WARNING] No metrics files found")
        return
    
    # Extract final throughput for each configuration
    data = []
    for metrics_file in metrics_files:
        df = pd.read_csv(metrics_file)
        
        # Parse filename: metrics_w{W}_r{R}_b{B}.csv
        parts = Path(metrics_file).stem.replace('metrics_', '').split('_')
        workers = int(parts[0][1:])
        rate = int(parts[1][1:])
        batch = int(parts[2][1:])
        
        # Get average throughput from last 50% of run
        mid = len(df) // 2
        avg_throughput = df['throughput_eps'].iloc[mid:].mean()
        
        data.append({
            'workers': workers,
            'rate': rate,
            'batch': batch,
            'throughput': avg_throughput
        })
    
    df = pd.DataFrame(data)
    
    # Plot workers vs throughput (grouped by rate)
    plt.figure(figsize=(10, 6))
    
    for rate in df['rate'].unique():
        subset = df[df['rate'] == rate].groupby('workers')['throughput'].mean()
        plt.plot(subset.index, subset.values, marker='o', label=f'Rate: {rate}')
    
    plt.xlabel('Number of Workers')
    plt.ylabel('Average Throughput (events/sec)')
    plt.title('Scalability: Workers vs Throughput')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/scalability.png", dpi=300)
    print(f"[OK] Saved: {output_dir}/scalability.png")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description='Generate plots')
    parser.add_argument('--metrics-dir', default='results',
                       help='Directory with metrics CSV files')
    parser.add_argument('--output-dir', default='results/plots',
                       help='Output directory for plots')
    
    args = parser.parse_args()
    
    # Create output directory
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    
    # Find metrics files
    metrics_files = glob.glob(f"{args.metrics_dir}/metrics_*.csv")
    
    if not metrics_files:
        print(f"[WARNING] No metrics files found in {args.metrics_dir}")
        return
    
    print(f"[*] Generating plots from {len(metrics_files)} experiments...")
    
    # Generate plots
    plot_throughput(metrics_files, args.output_dir)
    plot_queue_sizes(metrics_files, args.output_dir)
    plot_resource_usage(metrics_files, args.output_dir)
    plot_scalability(args.metrics_dir, args.output_dir)
    
    print(f"\n[OK] All plots saved to: {args.output_dir}")


if __name__ == '__main__':
    main()