import argparse
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import glob
import numpy as np


sns.set_style("whitegrid")
sns.set_palette("husl")


def plot_throughput(metrics_files: list, output_dir: str):
    """Plot throughput over time for all experiments."""
    plt.figure(figsize=(14, 6))
    
    for metrics_file in metrics_files:
        df = pd.read_csv(metrics_file)
        label = Path(metrics_file).stem.replace('metrics_', '').replace('_', ' ')
        plt.plot(df['runtime_sec'], df['throughput_eps'], label=label, marker='o', alpha=0.7)
    
    plt.xlabel('Runtime (seconds)', fontsize=12)
    plt.ylabel('Throughput (events/sec)', fontsize=12)
    plt.title('Throughput Over Time', fontsize=14, fontweight='bold')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/throughput.png", dpi=300, bbox_inches='tight')
    print(f"✅ Saved: {output_dir}/throughput.png")
    plt.close()


def plot_queue_sizes(metrics_files: list, output_dir: str):
    """Plot queue sizes (backpressure indicator)."""
    fig, axes = plt.subplots(1, 2, figsize=(16, 5))
    
    for metrics_file in metrics_files:
        df = pd.read_csv(metrics_file)
        label = Path(metrics_file).stem.replace('metrics_', '').replace('_', ' ')
        
        axes[0].plot(df['runtime_sec'], df['ingestion_queue_size'], 
                    label=label, marker='o', alpha=0.7)
        axes[1].plot(df['runtime_sec'], df['parsed_queue_size'], 
                    label=label, marker='o', alpha=0.7)
    
    axes[0].set_xlabel('Runtime (seconds)', fontsize=11)
    axes[0].set_ylabel('Queue Size', fontsize=11)
    axes[0].set_title('Ingestion Queue Size', fontsize=12, fontweight='bold')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    axes[1].set_xlabel('Runtime (seconds)', fontsize=11)
    axes[1].set_ylabel('Queue Size', fontsize=11)
    axes[1].set_title('Parsed Queue Size', fontsize=12, fontweight='bold')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f"{output_dir}/queue_sizes.png", dpi=300)
    print(f"✅ Saved: {output_dir}/queue_sizes.png")
    plt.close()


def plot_resource_usage(metrics_files: list, output_dir: str):
    """Plot CPU and memory usage."""
    fig, axes = plt.subplots(1, 2, figsize=(16, 5))
    
    for metrics_file in metrics_files:
        df = pd.read_csv(metrics_file)
        label = Path(metrics_file).stem.replace('metrics_', '').replace('_', ' ')
        
        axes[0].plot(df['runtime_sec'], df['cpu_percent'], 
                    label=label, marker='o', alpha=0.7)
        axes[1].plot(df['runtime_sec'], df['memory_mb'], 
                    label=label, marker='o', alpha=0.7)
    
    axes[0].set_xlabel('Runtime (seconds)', fontsize=11)
    axes[0].set_ylabel('CPU %', fontsize=11)
    axes[0].set_title('CPU Utilization', fontsize=12, fontweight='bold')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    axes[1].set_xlabel('Runtime (seconds)', fontsize=11)
    axes[1].set_ylabel('Memory (MB)', fontsize=11)
    axes[1].set_title('Memory Usage', fontsize=12, fontweight='bold')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f"{output_dir}/resource_usage.png", dpi=300)
    print(f"✅ Saved: {output_dir}/resource_usage.png")
    plt.close()


def plot_scalability(metrics_dir: str, output_dir: str):
    """Plot scalability analysis (workers vs throughput)."""
    # Find all metrics files
    metrics_files = glob.glob(f"{metrics_dir}/metrics_w*.csv")
    
    if not metrics_files:
        print("⚠️  No structured metrics files found for scalability plot")
        print("    Expected format: metrics_w{workers}_r{rate}_b{batch}.csv")
        return
    
    # Extract final throughput for each configuration
    data = []
    for metrics_file in metrics_files:
        try:
            df = pd.read_csv(metrics_file)
            
            # Parse filename: metrics_w{W}_r{R}_b{B}.csv
            parts = Path(metrics_file).stem.replace('metrics_', '').split('_')
            workers = int(parts[0][1:])
            rate = int(parts[1][1:])
            batch = int(parts[2][1:])
            
            # Get average throughput from last 50% of run
            mid = len(df) // 2
            avg_throughput = df['throughput_eps'].iloc[mid:].mean()
            max_throughput = df['throughput_eps'].max()
            
            data.append({
                'workers': workers,
                'rate': rate,
                'batch': batch,
                'avg_throughput': avg_throughput,
                'max_throughput': max_throughput
            })
        except Exception as e:
            print(f"⚠️  Error processing {metrics_file}: {e}")
            continue
    
    if not data:
        print("⚠️  No valid data for scalability plot")
        return
    
    df = pd.DataFrame(data)
    
    # Create figure with 3 subplots
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    # Plot 1: Workers vs Throughput (grouped by rate)
    for rate in sorted(df['rate'].unique()):
        subset = df[df['rate'] == rate].groupby('workers')['avg_throughput'].mean()
        axes[0].plot(subset.index, subset.values, marker='o', linewidth=2, 
                    markersize=8, label=f'Rate: {rate}')
    
    axes[0].set_xlabel('Number of Workers', fontsize=11)
    axes[0].set_ylabel('Average Throughput (events/sec)', fontsize=11)
    axes[0].set_title('Scalability: Workers vs Throughput', fontsize=12, fontweight='bold')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # Plot 2: Batch Size vs Throughput
    batch_data = df.groupby('batch')['avg_throughput'].mean()
    axes[1].plot(batch_data.index, batch_data.values, marker='o', linewidth=2, 
                markersize=8, color='green')
    axes[1].set_xlabel('Batch Size', fontsize=11)
    axes[1].set_ylabel('Average Throughput (events/sec)', fontsize=11)
    axes[1].set_title('Batch Size Impact', fontsize=12, fontweight='bold')
    axes[1].grid(True, alpha=0.3)
    
    # Plot 3: Rate vs Throughput
    rate_data = df.groupby('rate')['avg_throughput'].mean()
    axes[2].plot(rate_data.index, rate_data.values, marker='o', linewidth=2, 
                markersize=8, color='orange')
    axes[2].set_xlabel('Target Rate (events/sec)', fontsize=11)
    axes[2].set_ylabel('Actual Throughput (events/sec)', fontsize=11)
    axes[2].set_title('Rate Limit Impact', fontsize=12, fontweight='bold')
    axes[2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f"{output_dir}/scalability.png", dpi=300)
    print(f"✅ Saved: {output_dir}/scalability.png")
    plt.close()


def plot_alerts_over_time(metrics_files: list, output_dir: str):
    """Plot alert generation over time."""
    plt.figure(figsize=(14, 6))
    
    for metrics_file in metrics_files:
        df = pd.read_csv(metrics_file)
        label = Path(metrics_file).stem.replace('metrics_', '').replace('_', ' ')
        plt.plot(df['runtime_sec'], df['alerts_count'], label=label, 
                marker='o', linewidth=2, alpha=0.7)
    
    plt.xlabel('Runtime (seconds)', fontsize=12)
    plt.ylabel('Cumulative Alerts', fontsize=12)
    plt.title('Alert Generation Over Time', fontsize=14, fontweight='bold')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/alerts_over_time.png", dpi=300, bbox_inches='tight')
    print(f"✅ Saved: {output_dir}/alerts_over_time.png")
    plt.close()


def generate_summary_report(metrics_files: list, output_dir: str):
    """Generate a summary report comparing all experiments."""
    summary_data = []
    
    for metrics_file in metrics_files:
        df = pd.read_csv(metrics_file)
        filename = Path(metrics_file).stem
        
        # Calculate statistics
        mid = len(df) // 2
        summary = {
            'Experiment': filename.replace('metrics_', '').replace('_', ' '),
            'Avg Throughput': f"{df['throughput_eps'].iloc[mid:].mean():.1f}",
            'Max Throughput': f"{df['throughput_eps'].max():.1f}",
            'Avg CPU %': f"{df['cpu_percent'].mean():.1f}",
            'Max Memory (MB)': f"{df['memory_mb'].max():.1f}",
            'Total Alerts': df['alerts_count'].iloc[-1] if len(df) > 0 else 0,
            'Total Events': df['events_processed'].iloc[-1] if len(df) > 0 else 0
        }
        summary_data.append(summary)
    
    # Create summary DataFrame and save
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv(f"{output_dir}/summary_report.csv", index=False)
    
    # Also save as formatted text
    with open(f"{output_dir}/summary_report.txt", 'w') as f:
        f.write("="*80 + "\n")
        f.write("SIEM PIPELINE PERFORMANCE SUMMARY\n")
        f.write("="*80 + "\n\n")
        f.write(summary_df.to_string(index=False))
        f.write("\n\n" + "="*80 + "\n")
    
    print(f"✅ Saved: {output_dir}/summary_report.csv")
    print(f"✅ Saved: {output_dir}/summary_report.txt")
    
    # Print summary to console
    print("\n" + "="*80)
    print("PERFORMANCE SUMMARY")
    print("="*80)
    print(summary_df.to_string(index=False))
    print("="*80 + "\n")


def main():
    parser = argparse.ArgumentParser(description='Generate performance analysis plots')
    parser.add_argument('--metrics-dir', default='results',
                       help='Directory with metrics CSV files')
    parser.add_argument('--output-dir', default='results/plots',
                       help='Output directory for plots')
    
    args = parser.parse_args()
    
    # Create output directory
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    
    # Find metrics files
    metrics_files = glob.glob(f"{args.metrics_dir}/*metrics*.csv")
    
    if not metrics_files:
        print(f"❌ No metrics files found in {args.metrics_dir}")
        print(f"   Looking for files matching: *metrics*.csv")
        return
    
    print(f"\n{'='*80}")
    print(f"SIEM PIPELINE VISUALIZATION")
    print(f"{'='*80}")
    print(f"📊 Found {len(metrics_files)} experiment(s)")
    print(f"📁 Output directory: {args.output_dir}")
    print(f"{'='*80}\n")
    
    # Generate plots
    print("Generating plots...")
    plot_throughput(metrics_files, args.output_dir)
    plot_queue_sizes(metrics_files, args.output_dir)
    plot_resource_usage(metrics_files, args.output_dir)
    plot_alerts_over_time(metrics_files, args.output_dir)
    plot_scalability(args.metrics_dir, args.output_dir)
    
    # Generate summary report
    print("\nGenerating summary report...")
    generate_summary_report(metrics_files, args.output_dir)
    
    print(f"\n{'='*80}")
    print(f"✅ All visualizations saved to: {args.output_dir}")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    main()