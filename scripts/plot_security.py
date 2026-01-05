"""
Security-focused visualization script for SIEM-lite pipeline.

Generates visualizations for:
- Suspicious events timeline
- Top attacking IPs
- Attack type distribution
- HTTP error breakdown
- Targeted URLs analysis
- Hourly attack heatmap

Usage:
    python scripts/plot_security.py --db results/events.db --output-dir results/security_plots
"""

import argparse
import sqlite3
from pathlib import Path
from collections import Counter
import re
import sys
import io

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.facecolor'] = 'white'


def get_attack_category(url: str) -> str:
    """Categorize attack type based on URL patterns."""
    url_lower = url.lower() if url else ''
    
    # Path traversal
    if '../' in url_lower or '..\\' in url_lower or '%2e%2e' in url_lower:
        return 'Path Traversal'
    
    # Script/CGI probing
    if '/cgi-bin/' in url_lower or '.cgi' in url_lower or '.pl' in url_lower:
        return 'CGI Probing'
    
    # Admin/Management probing
    if any(x in url_lower for x in ['phpmyadmin', 'phpgroupware', 'mambo', 'drupal', 'wordpress', 'awstats']):
        return 'CMS/Admin Probing'
    
    # File inclusion attempts
    if any(x in url_lower for x in ['/etc/passwd', 'cmd=', 'exec=']):
        return 'File Inclusion'
    
    # XSS patterns
    if 'script>' in url_lower or '<script' in url_lower:
        return 'XSS Attempt'
    
    # SQL Injection
    if any(x in url_lower for x in ['union', 'select', 'drop', "'"]):
        return 'SQL Injection'
    
    # Directory scanning
    if any(x in url_lower for x in ['scripts/', '_vti_bin', '_mem_bin', 'msadc']):
        return 'Directory Scanning'
    
    # Default for error status codes
    return 'Error Response'


def load_data(db_path: str) -> tuple:
    """Load events and alerts from database."""
    conn = sqlite3.connect(db_path)
    
    # Load events
    events_df = pd.read_sql_query("""
        SELECT * FROM events 
        ORDER BY timestamp
    """, conn)
    
    # Load alerts
    alerts_df = pd.read_sql_query("""
        SELECT * FROM alerts 
        ORDER BY created_at
    """, conn)
    
    conn.close()
    
    return events_df, alerts_df


def plot_suspicious_timeline(events_df: pd.DataFrame, output_dir: str):
    """Plot suspicious events over time."""
    suspicious = events_df[events_df['suspicious'] == 1].copy()
    
    if len(suspicious) == 0:
        print("[WARN] No suspicious events found for timeline plot")
        return
    
    # Parse timestamps
    suspicious['ts'] = pd.to_datetime(suspicious['timestamp'], errors='coerce')
    suspicious = suspicious.dropna(subset=['ts'])
    
    if len(suspicious) == 0:
        print("[WARN] Could not parse timestamps for timeline")
        return
    
    # Group by minute
    suspicious['minute'] = suspicious['ts'].dt.floor('1min')
    timeline = suspicious.groupby('minute').size()
    
    plt.figure(figsize=(14, 6))
    plt.fill_between(timeline.index, timeline.values, alpha=0.7, color='crimson')
    plt.plot(timeline.index, timeline.values, color='darkred', linewidth=1.5)
    
    plt.xlabel('Time', fontsize=12)
    plt.ylabel('Suspicious Events', fontsize=12)
    plt.title('[ALERT] Suspicious Events Timeline', fontsize=14, fontweight='bold')
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/suspicious_timeline.png", dpi=300, bbox_inches='tight')
    print(f"[OK] Saved: {output_dir}/suspicious_timeline.png")
    plt.close()


def plot_top_attacking_ips(events_df: pd.DataFrame, output_dir: str, top_n: int = 15):
    """Plot top IPs with suspicious activity."""
    suspicious = events_df[events_df['suspicious'] == 1]
    
    if len(suspicious) == 0:
        print("[WARN] No suspicious events found for IP analysis")
        return
    
    # Filter out empty IPs and get top counts
    ip_counts = suspicious[suspicious['ip'].str.strip() != '']['ip'].value_counts().head(top_n)
    
    if len(ip_counts) == 0:
        print("[WARN] No valid IPs found")
        return
    
    plt.figure(figsize=(12, 8))
    colors = sns.color_palette("Reds_r", n_colors=len(ip_counts))
    bars = plt.barh(range(len(ip_counts)), ip_counts.values, color=colors)
    plt.yticks(range(len(ip_counts)), ip_counts.index)
    
    # Add count labels
    for i, (bar, count) in enumerate(zip(bars, ip_counts.values)):
        plt.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2, 
                f'{count:,}', va='center', fontsize=9)
    
    plt.xlabel('Suspicious Events Count', fontsize=12)
    plt.ylabel('IP Address', fontsize=12)
    plt.title(f'Top {len(ip_counts)} Suspicious IP Addresses', fontsize=14, fontweight='bold')
    plt.gca().invert_yaxis()
    plt.grid(True, alpha=0.3, axis='x')
    plt.tight_layout()
    plt.savefig(f"{output_dir}/top_attacking_ips.png", dpi=300, bbox_inches='tight')
    print(f"[OK] Saved: {output_dir}/top_attacking_ips.png")
    plt.close()


def plot_attack_distribution(events_df: pd.DataFrame, output_dir: str):
    """Plot distribution of attack types as horizontal bar chart."""
    suspicious = events_df[events_df['suspicious'] == 1]
    
    if len(suspicious) == 0:
        print("[WARN] No suspicious events found for attack distribution")
        return
    
    # Categorize attacks
    attack_types = suspicious['url'].apply(get_attack_category)
    attack_counts = attack_types.value_counts()
    
    # Use horizontal bar chart instead of pie for clarity
    plt.figure(figsize=(12, 6))
    colors = sns.color_palette("husl", n_colors=len(attack_counts))
    
    bars = plt.barh(range(len(attack_counts)), attack_counts.values, color=colors)
    plt.yticks(range(len(attack_counts)), attack_counts.index)
    
    # Add percentage labels
    total = attack_counts.sum()
    for i, (bar, count) in enumerate(zip(bars, attack_counts.values)):
        pct = count / total * 100
        plt.text(bar.get_width() + 50, bar.get_y() + bar.get_height()/2, 
                f'{count:,} ({pct:.1f}%)', va='center', fontsize=9)
    
    plt.xlabel('Number of Suspicious Events', fontsize=12)
    plt.ylabel('Attack Category', fontsize=12)
    plt.title('Attack Type Distribution', fontsize=14, fontweight='bold')
    plt.gca().invert_yaxis()
    plt.grid(True, alpha=0.3, axis='x')
    plt.tight_layout()
    plt.savefig(f"{output_dir}/attack_distribution.png", dpi=300, bbox_inches='tight')
    print(f"[OK] Saved: {output_dir}/attack_distribution.png")
    plt.close()


def plot_http_status_breakdown(events_df: pd.DataFrame, output_dir: str):
    """Plot HTTP error status code distribution."""
    # Filter error status codes
    errors = events_df[events_df['status'] >= 400].copy()
    
    if len(errors) == 0:
        print("[WARN] No HTTP errors found")
        return
    
    status_counts = errors['status'].value_counts().head(10)
    
    plt.figure(figsize=(12, 6))
    
    # Color by severity
    def get_status_color(code):
        if code >= 500:
            return '#d62728'  # Red for 5xx
        elif code == 404:
            return '#ff7f0e'  # Orange for 404
        elif code == 403:
            return '#9467bd'  # Purple for 403
        else:
            return '#1f77b4'  # Blue for others
    
    colors = [get_status_color(code) for code in status_counts.index]
    
    bars = plt.bar(range(len(status_counts)), status_counts.values, color=colors)
    plt.xticks(range(len(status_counts)), status_counts.index)
    
    # Add labels with status descriptions
    status_names = {
        400: 'Bad Request',
        401: 'Unauthorized',
        403: 'Forbidden',
        404: 'Not Found',
        405: 'Method Not Allowed',
        500: 'Server Error',
        502: 'Bad Gateway',
        503: 'Service Unavailable'
    }
    
    for i, (bar, code) in enumerate(zip(bars, status_counts.index)):
        name = status_names.get(code, '')
        if name:
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10, 
                    name, ha='center', va='bottom', fontsize=8, rotation=45)
    
    plt.xlabel('HTTP Status Code', fontsize=12)
    plt.ylabel('Count', fontsize=12)
    plt.title('HTTP Error Status Distribution', fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    plt.savefig(f"{output_dir}/http_status_breakdown.png", dpi=300, bbox_inches='tight')
    print(f"[OK] Saved: {output_dir}/http_status_breakdown.png")
    plt.close()


def plot_targeted_urls(events_df: pd.DataFrame, output_dir: str, top_n: int = 15):
    """Plot most targeted URLs."""
    suspicious = events_df[events_df['suspicious'] == 1]
    
    if len(suspicious) == 0:
        print("[WARN] No suspicious events found for URL analysis")
        return
    
    # Clean URLs (take first 50 chars for display)
    url_counts = suspicious['url'].apply(lambda x: x[:50] if x else 'Unknown').value_counts().head(top_n)
    
    plt.figure(figsize=(14, 8))
    colors = sns.color_palette("YlOrRd", n_colors=top_n)
    
    bars = plt.barh(range(len(url_counts)), url_counts.values, color=colors)
    plt.yticks(range(len(url_counts)), url_counts.index, fontsize=9)
    
    plt.xlabel('Hit Count', fontsize=12)
    plt.ylabel('URL Pattern', fontsize=12)
    plt.title(f'Top {top_n} Targeted URLs', fontsize=14, fontweight='bold')
    plt.gca().invert_yaxis()
    plt.grid(True, alpha=0.3, axis='x')
    plt.tight_layout()
    plt.savefig(f"{output_dir}/targeted_urls.png", dpi=300, bbox_inches='tight')
    print(f"[OK] Saved: {output_dir}/targeted_urls.png")
    plt.close()


def plot_hourly_heatmap(events_df: pd.DataFrame, output_dir: str):
    """Plot hourly attack heatmap by day of week."""
    suspicious = events_df[events_df['suspicious'] == 1].copy()
    
    if len(suspicious) == 0:
        print("[WARN] No suspicious events found for heatmap")
        return
    
    # Parse timestamps
    suspicious['ts'] = pd.to_datetime(suspicious['timestamp'], errors='coerce')
    suspicious = suspicious.dropna(subset=['ts'])
    
    if len(suspicious) == 0:
        print("[WARN] Could not parse timestamps for heatmap")
        return
    
    suspicious['hour'] = suspicious['ts'].dt.hour
    suspicious['day'] = suspicious['ts'].dt.day_name()
    
    # Create pivot table
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    heatmap_data = suspicious.groupby(['day', 'hour']).size().unstack(fill_value=0)
    
    # Reindex to ensure all days are present
    heatmap_data = heatmap_data.reindex(day_order, fill_value=0)
    
    plt.figure(figsize=(14, 6))
    sns.heatmap(heatmap_data, cmap='Reds', annot=False, fmt='d', 
                linewidths=0.5, cbar_kws={'label': 'Suspicious Events'})
    
    plt.xlabel('Hour of Day', fontsize=12)
    plt.ylabel('Day of Week', fontsize=12)
    plt.title('Suspicious Activity Heatmap', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(f"{output_dir}/hourly_heatmap.png", dpi=300, bbox_inches='tight')
    print(f"[OK] Saved: {output_dir}/hourly_heatmap.png")
    plt.close()


def plot_alerts_summary(alerts_df: pd.DataFrame, output_dir: str):
    """Plot alerts summary."""
    if len(alerts_df) == 0:
        print("[WARN] No alerts found")
        return
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Left: Alerts by IP
    ip_alerts = alerts_df['ip'].value_counts().head(10)
    axes[0].barh(range(len(ip_alerts)), ip_alerts.values, color='crimson')
    axes[0].set_yticks(range(len(ip_alerts)))
    axes[0].set_yticklabels(ip_alerts.index)
    axes[0].set_xlabel('Alert Count')
    axes[0].set_title('Top Alerted IPs', fontweight='bold')
    axes[0].invert_yaxis()
    axes[0].grid(True, alpha=0.3, axis='x')
    
    # Right: Alert counts distribution
    alert_counts = alerts_df['count'].value_counts().sort_index()
    axes[1].bar(alert_counts.index, alert_counts.values, color='darkred')
    axes[1].set_xlabel('Suspicious Events in Window')
    axes[1].set_ylabel('Number of Alerts')
    axes[1].set_title('Alert Severity Distribution', fontweight='bold')
    axes[1].grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(f"{output_dir}/alerts_summary.png", dpi=300, bbox_inches='tight')
    print(f"[OK] Saved: {output_dir}/alerts_summary.png")
    plt.close()


def generate_security_report(events_df: pd.DataFrame, alerts_df: pd.DataFrame, output_dir: str):
    """Generate text summary report."""
    total_events = len(events_df)
    suspicious_events = len(events_df[events_df['suspicious'] == 1])
    total_alerts = len(alerts_df)
    # Filter empty IPs
    valid_ips = events_df[events_df['ip'].str.strip() != '']
    unique_ips = valid_ips['ip'].nunique()
    suspicious_ips = valid_ips[valid_ips['suspicious'] == 1]['ip'].nunique()
    
    report = f"""
{'='*70}
SIEM-LITE SECURITY ANALYSIS REPORT
{'='*70}

OVERVIEW
-----------
Total Events Processed:     {total_events:,}
Suspicious Events:          {suspicious_events:,} ({suspicious_events/total_events*100:.1f}%)
Unique IP Addresses:        {unique_ips:,}
IPs with Suspicious Activity: {suspicious_ips:,}
Total Alerts Generated:     {total_alerts}

NOTE: Alerts are triggered when an IP accumulates 5+ suspicious events 
      within a 60-second window. Multiple suspicious events per IP = 1 alert.

"""
    
    if suspicious_events > 0:
        # Top attacking IPs (filter empty)
        suspicious_valid = valid_ips[valid_ips['suspicious'] == 1]
        top_ips = suspicious_valid['ip'].value_counts().head(5)
        report += "TOP SUSPICIOUS IPs\n"
        report += "-" * 30 + "\n"
        for ip, count in top_ips.items():
            report += f"  {ip}: {count:,} events\n"
        report += "\n"
        
        # Attack type breakdown
        attack_types = events_df[events_df['suspicious'] == 1]['url'].apply(get_attack_category)
        attack_counts = attack_types.value_counts()
        report += "ATTACK TYPE BREAKDOWN\n"
        report += "-" * 30 + "\n"
        for attack_type, count in attack_counts.items():
            report += f"  {attack_type}: {count:,} ({count/suspicious_events*100:.1f}%)\n"
        report += "\n"
    
    # HTTP Status breakdown
    error_status = events_df[events_df['status'] >= 400]['status'].value_counts().head(5)
    if len(error_status) > 0:
        report += "HTTP ERROR STATUS CODES\n"
        report += "-" * 30 + "\n"
        for status, count in error_status.items():
            report += f"  HTTP {status}: {count:,}\n"
        report += "\n"
    
    report += "=" * 70 + "\n"
    report += "Report generated by SIEM-lite Security Analysis\n"
    report += "=" * 70 + "\n"
    
    # Save report
    with open(f"{output_dir}/security_report.txt", 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"[OK] Saved: {output_dir}/security_report.txt")
    print(report)


def main():
    parser = argparse.ArgumentParser(description='Generate security analysis plots')
    parser.add_argument('--db', required=True, help='Path to events database')
    parser.add_argument('--output-dir', default='results/security_plots',
                       help='Output directory for plots')
    
    args = parser.parse_args()
    
    # Validate database exists
    if not Path(args.db).exists():
        print(f"[ERROR] Database not found: {args.db}")
        print("   Run the SIEM pipeline first to generate events.")
        return
    
    # Create output directory
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*70}")
    print(f"SIEM-LITE SECURITY VISUALIZATION")
    print(f"{'='*70}")
    print(f"Database: {args.db}")
    print(f"Output: {args.output_dir}")
    print(f"{'='*70}\n")
    
    # Load data
    print("Loading data from database...")
    events_df, alerts_df = load_data(args.db)
    print(f"  {len(events_df):,} events loaded")
    print(f"  {len(alerts_df):,} alerts loaded")
    print(f"  {len(events_df[events_df['suspicious'] == 1]):,} suspicious events\n")
    
    # Generate plots
    print("Generating security visualizations...")
    plot_suspicious_timeline(events_df, args.output_dir)
    plot_top_attacking_ips(events_df, args.output_dir)
    plot_attack_distribution(events_df, args.output_dir)
    plot_http_status_breakdown(events_df, args.output_dir)
    plot_targeted_urls(events_df, args.output_dir)
    plot_hourly_heatmap(events_df, args.output_dir)
    plot_alerts_summary(alerts_df, args.output_dir)
    
    # Generate text report
    print("\nGenerating security report...")
    generate_security_report(events_df, alerts_df, args.output_dir)
    
    print(f"\n{'='*70}")
    print(f"[OK] All security visualizations saved to: {args.output_dir}")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    main()
