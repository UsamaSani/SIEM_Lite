import json
from pathlib import Path


def create_notebook():
    """Create analysis.ipynb programmatically."""
    
    notebook = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "# SIEM-lite Performance Analysis\\n",
                    "\\n",
                    "This notebook analyzes the results from SIEM-lite experiments.\\n",
                    "\\n",
                    "**Contents:**\\n",
                    "1. Load experiment data\\n",
                    "2. Throughput analysis\\n",
                    "3. Latency distributions\\n",
                    "4. Scalability analysis\\n",
                    "5. Resource utilization\\n",
                    "6. Bottleneck identification"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "import pandas as pd\\n",
                    "import numpy as np\\n",
                    "import matplotlib.pyplot as plt\\n",
                    "import seaborn as sns\\n",
                    "import sqlite3\\n",
                    "import glob\\n",
                    "from pathlib import Path\\n",
                    "\\n",
                    "sns.set_style('whitegrid')\\n",
                    "sns.set_palette('husl')\\n",
                    "plt.rcParams['figure.figsize'] = (12, 6)\\n",
                    "\\n",
                    "# Directories\\n",
                    "RESULTS_DIR = '../results'\\n",
                    "PLOTS_DIR = f'{RESULTS_DIR}/plots'\\n",
                    "Path(PLOTS_DIR).mkdir(parents=True, exist_ok=True)"
                ]
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": ["## 1. Load Experiment Data"]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "# Find all metrics files\\n",
                    "metrics_files = glob.glob(f'{RESULTS_DIR}/metrics_*.csv')\\n",
                    "print(f'Found {len(metrics_files)} experiment results')\\n",
                    "\\n",
                    "# Load all metrics\\n",
                    "all_metrics = []\\n",
                    "\\n",
                    "for f in metrics_files:\\n",
                    "    # Parse filename: metrics_w{W}_r{R}_b{B}.csv\\n",
                    "    parts = Path(f).stem.replace('metrics_', '').split('_')\\n",
                    "    workers = int(parts[0][1:])\\n",
                    "    rate = int(parts[1][1:])\\n",
                    "    batch = int(parts[2][1:])\\n",
                    "    \\n",
                    "    df = pd.read_csv(f)\\n",
                    "    df['workers'] = workers\\n",
                    "    df['rate'] = rate\\n",
                    "    df['batch'] = batch\\n",
                    "    df['exp_id'] = f'w{workers}_r{rate}_b{batch}'\\n",
                    "    \\n",
                    "    all_metrics.append(df)\\n",
                    "\\n",
                    "metrics_df = pd.concat(all_metrics, ignore_index=True)\\n",
                    "metrics_df.head()"
                ]
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": ["## 2. Throughput Analysis"]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "# Calculate steady-state throughput (last 50% of each run)\\n",
                    "steady_state = []\\n",
                    "\\n",
                    "for exp_id in metrics_df['exp_id'].unique():\\n",
                    "    exp_data = metrics_df[metrics_df['exp_id'] == exp_id]\\n",
                    "    mid = len(exp_data) // 2\\n",
                    "    \\n",
                    "    steady = exp_data.iloc[mid:]\\n",
                    "    \\n",
                    "    steady_state.append({\\n",
                    "        'exp_id': exp_id,\\n",
                    "        'workers': exp_data['workers'].iloc[0],\\n",
                    "        'rate': exp_data['rate'].iloc[0],\\n",
                    "        'batch': exp_data['batch'].iloc[0],\\n",
                    "        'avg_throughput': steady['throughput_eps'].mean(),\\n",
                    "        'max_throughput': steady['throughput_eps'].max(),\\n",
                    "        'avg_cpu': steady['cpu_percent'].mean(),\\n",
                    "        'avg_memory': steady['memory_mb'].mean()\\n",
                    "    })\\n",
                    "\\n",
                    "ss_df = pd.DataFrame(steady_state)\\n",
                    "print('Top 10 configurations by throughput:')\\n",
                    "ss_df.nlargest(10, 'avg_throughput')[['exp_id', 'avg_throughput', 'workers', 'batch']]"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "# Plot throughput over time\\n",
                    "fig, ax = plt.subplots(figsize=(14, 6))\\n",
                    "\\n",
                    "target_rate = 500\\n",
                    "target_batch = 100\\n",
                    "\\n",
                    "for workers in [1, 2, 4, 8]:\\n",
                    "    subset = metrics_df[\\n",
                    "        (metrics_df['workers'] == workers) & \\n",
                    "        (metrics_df['rate'] == target_rate) & \\n",
                    "        (metrics_df['batch'] == target_batch)\\n",
                    "    ]\\n",
                    "    \\n",
                    "    if not subset.empty:\\n",
                    "        ax.plot(subset['runtime_sec'], subset['throughput_eps'], \\n",
                    "                marker='o', label=f'{workers} workers')\\n",
                    "\\n",
                    "ax.set_xlabel('Runtime (seconds)')\\n",
                    "ax.set_ylabel('Throughput (events/sec)')\\n",
                    "ax.set_title(f'Throughput Over Time (rate={target_rate}, batch={target_batch})')\\n",
                    "ax.legend()\\n",
                    "ax.grid(True, alpha=0.3)\\n",
                    "plt.tight_layout()\\n",
                    "plt.savefig(f'{PLOTS_DIR}/throughput_over_time.png', dpi=300)\\n",
                    "plt.show()"
                ]
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": ["## 3. Scalability Analysis"]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "# Workers vs throughput\\n",
                    "fig, ax = plt.subplots(figsize=(10, 6))\\n",
                    "\\n",
                    "for rate in ss_df['rate'].unique():\\n",
                    "    subset = ss_df[ss_df['rate'] == rate].groupby('workers')['avg_throughput'].mean()\\n",
                    "    ax.plot(subset.index, subset.values, marker='o', linewidth=2, label=f'Rate: {rate}')\\n",
                    "\\n",
                    "# Ideal linear scalability\\n",
                    "baseline = ss_df[ss_df['workers'] == 1]['avg_throughput'].mean()\\n",
                    "ax.plot([1, 2, 4, 8], [baseline*i for i in [1, 2, 4, 8]], \\n",
                    "        'k--', alpha=0.5, label='Ideal Linear')\\n",
                    "\\n",
                    "ax.set_xlabel('Number of Workers')\\n",
                    "ax.set_ylabel('Average Throughput (events/sec)')\\n",
                    "ax.set_title('Scalability: Workers vs Throughput')\\n",
                    "ax.legend()\\n",
                    "ax.grid(True, alpha=0.3)\\n",
                    "plt.tight_layout()\\n",
                    "plt.savefig(f'{PLOTS_DIR}/scalability.png', dpi=300)\\n",
                    "plt.show()"
                ]
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": ["## 4. Summary Report"]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "print('='*60)\\n",
                    "print('SIEM-LITE PERFORMANCE SUMMARY')\\n",
                    "print('='*60)\\n",
                    "\\n",
                    "print(f'\\\\nTotal experiments: {len(ss_df)}')\\n",
                    "\\n",
                    "print('\\\\n📊 Throughput:')\\n",
                    "print(f'  Peak: {ss_df[\"avg_throughput\"].max():.0f} events/sec')\\n",
                    "best_config = ss_df.loc[ss_df['avg_throughput'].idxmax()]\\n",
                    "print(f'  Best config: w={best_config[\"workers\"]}, batch={best_config[\"batch\"]}')\\n",
                    "\\n",
                    "print('\\\\n🔧 Resource Usage:')\\n",
                    "print(f'  Avg CPU: {ss_df[\"avg_cpu\"].mean():.1f}%')\\n",
                    "print(f'  Avg Memory: {ss_df[\"avg_memory\"].mean():.0f} MB')\\n",
                    "\\n",
                    "print('\\\\n' + '='*60)"
                ]
            }
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "codemirror_mode": {
                    "name": "ipython",
                    "version": 3
                },
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbconvert_exporter": "python",
                "pygments_lexer": "ipython3",
                "version": "3.10.0"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 4
    }
    
    # Write notebook
    notebook_path = Path('notebooks/analysis.ipynb')
    notebook_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(notebook_path, 'w') as f:
        json.dump(notebook, f, indent=1)
    
    print(f"[OK] Created: {notebook_path}")


if __name__ == '__main__':
    create_notebook()