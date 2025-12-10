# SIEM-lite: Streaming Log Analytics Engine

A lightweight, high-performance Security Information and Event Management (SIEM) system built with Python multiprocessing. Processes Apache web server logs in real-time with configurable parallelism and generates security alerts.

## Features

- **Streaming log processing** with configurable ingestion rates
- **Parallel parsing & enrichment** using Python multiprocessing
- **Real-time alerting** with sliding-window rules
- **Batched indexing** to SQLite (or optional ClickHouse/Elasticsearch)
- **Performance metrics** collection (throughput, latency, CPU, memory)
- **Automated experiments** with parameter grid search
- **Analysis notebooks** with publication-quality plots

## Architecture

```
Log File → Replay → [Queue] → Parser Workers (N) → [Queue] → Indexer → SQLite
                                     ↓
                              Alerting Engine
                                     ↓
                              Metrics Collector
```

## Installation

### Prerequisites
- Python 3.10+
- Kaggle API credentials (for dataset download)

### Setup

1. Clone the repository:
```bash
git clone <repo-url>
cd siem-lite
```

2. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### Download Dataset

We use the **LogHub - Apache Log Data** from Kaggle.

1. Install Kaggle CLI:
```bash
pip install kaggle
```

2. Setup Kaggle credentials:
   - Download your `kaggle.json` from https://www.kaggle.com/settings
   - Place it in `~/.kaggle/` (Linux/Mac) or `C:\\Users\\<username>\\.kaggle\\` (Windows)
   - Set permissions: `chmod 600 ~/.kaggle/kaggle.json`

3. Download the dataset:
```bash
bash scripts/download_kaggle.sh
```

Or manually:
```bash
kaggle datasets download -d omduggineni/loghub-apache-log-data
unzip loghub-apache-log-data.zip -d raw/
```

## Quick Start

### Run with Sample Data (No Download Required)

```bash
# Test with included sample data (1k lines)
python src/siem_pipeline.py \\
    --input sample_data/apache_sample.log \\
    --workers 4 \\
    --rate 500 \\
    --batch 100 \\
    --run-time 30 \\
    --db results/test.db \\
    --metrics results/test_metrics.csv
```

### Verify Results
```bash
# Check event count
sqlite3 results/test.db "SELECT COUNT(*) FROM events;"

# View recent alerts
sqlite3 results/test.db "SELECT * FROM alerts LIMIT 10;"

# Check metrics
head results/test_metrics.csv
```

## Usage Guide

### 1. Preprocess Raw Logs

```bash
python scripts/preprocess.py \\
    --input raw/Apache.log \\
    --output cleaned.log \\
    --sample 10000  # Optional: create a sample
```

### 2. Run Single Experiment

```bash
python src/siem_pipeline.py \\
    --input cleaned.log \\
    --workers 8 \\
    --rate 1000 \\
    --batch 200 \\
    --run-time 60 \\
    --db results/events.db \\
    --metrics results/metrics.csv
```

**Parameters:**
- `--input`: Path to log file
- `--workers`: Number of parser processes (default: 4)
- `--rate`: Events per second (0 = unlimited, default: 0)
- `--batch`: Indexer batch size (default: 100)
- `--run-time`: Duration in seconds (default: 60)
- `--db`: Output SQLite database path
- `--metrics`: Output metrics CSV path

### 3. Run Experiment Matrix

```bash
# Bash version
bash scripts/run_experiments.sh

# Python version (more flexible)
python scripts/run_experiments.py \\
    --input cleaned.log \\
    --workers 1 2 4 8 \\
    --rates 200 500 1000 \\
    --batches 50 100 200 \\
    --duration 60
```

This runs a parameter grid search testing different combinations of workers, ingestion rates, and batch sizes.

### 4. Compute Latencies

```bash
python scripts/compute_latencies.py \\
    --db results/events_w4_r500_b100.db \\
    --output results/latency_stats.json
```

### 5. Generate Plots

```bash
python scripts/plot_metrics.py \\
    --metrics-dir results/ \\
    --output-dir results/plots/
```

### 6. Analyze Results

```bash
jupyter notebook notebooks/analysis.ipynb
```

## Docker Support (Optional)

For higher-throughput experiments with ClickHouse:

```bash
# Start ClickHouse
docker-compose up -d clickhouse

# Run pipeline with ClickHouse backend
python src/siem_pipeline.py \\
    --input cleaned.log \\
    --backend clickhouse \\
    --workers 16 \\
    --rate 5000 \\
    --batch 500
```

## Testing

```bash
# Run unit tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## Performance Tuning

### SQLite Bottleneck
If you see queue backpressure:
- Increase `--batch` size (e.g., 500-1000)
- Reduce `--workers` (fewer producers)
- Use `--backend clickhouse` for higher throughput

### Memory Usage
- Use bounded queues (already implemented)
- Monitor with: `python scripts/plot_metrics.py` (memory graph)

### CPU Utilization
- Optimal workers ≈ CPU cores - 2 (leave room for indexer & metrics)
- Test with: `--workers 1 2 4 8 16`

## Dataset Citation

```
Omduggineni. (2024). LogHub - Apache Log Data [Dataset]. Kaggle.
https://www.kaggle.com/datasets/omduggineni/loghub-apache-log-data
```

## Project Structure

- `src/`: Core SIEM pipeline and utilities
- `scripts/`: Preprocessing, replay, experiments, analysis
- `notebooks/`: Jupyter analysis notebooks
- `tests/`: Unit tests
- `sample_data/`: Small sample log file for testing
- `results/`: Experiment outputs (databases, metrics, plots)
- `docs/`: Report template and documentation

## Troubleshooting

### "Kaggle credentials not found"
- Ensure `kaggle.json` is in `~/.kaggle/` with 600 permissions

### "Queue full" warnings
- Increase batch size: `--batch 500`
- Reduce ingestion rate: `--rate 500`

### Low throughput
- Check SQLite write performance (switch to ClickHouse for 5000+ events/sec)
- Verify CPU utilization (should be 70-90% across workers)

### Database locked errors
- Use `PRAGMA journal_mode=WAL` (already in code)
- Ensure only one indexer process

## Demo Commands

For a 2-minute demo:

```bash
# Quick test with sample data
python src/siem_pipeline.py \\
    --input sample_data/apache_sample.log \\
    --workers 4 --rate 200 --run-time 15 \\
    --db demo.db --metrics demo.csv

# Check results
sqlite3 demo.db "SELECT status, COUNT(*) FROM events GROUP BY status;"
sqlite3 demo.db "SELECT * FROM alerts;"
cat demo.csv | column -t -s,
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass: `pytest tests/`
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Future Work

- [ ] Distributed processing with Ray/Dask
- [ ] Web UI for alert dashboard
- [ ] ML-based anomaly detection
- [ ] Support for additional log formats (Nginx, Syslog)
- [ ] Prometheus metrics export
- [ ] Kubernetes deployment manifests


