# SIEM_Lite

> **A lightweight, high-performance streaming log analytics engine**
> Built with Python `multiprocessing` — ingest, parse, enrich, index, alert, and measure, all in a compact, reproducible codebase.

---

## Abstract

The escalating volume and velocity of log data present a significant challenge for modern cybersecurity operations, often requiring Security Information and Event Management (SIEM) systems burdened by high costs and operational complexity. **SIEM_Lite** is a lightweight, high-performance log processing pipeline engineered to address this challenge. Built using Python's `multiprocessing` library, the system implements a distributed pipeline architecture to ingest, parse, enrich, and index log data concurrently. Its key features include parallel worker processes for scalable analysis, a batched indexer for efficient data storage, a real-time alerting engine with sliding-window rules, and an integrated metrics collector for performance monitoring.

By processing real Apache log data, SIEM_Lite demonstrates a scalable, parallel approach to performing real-time, SIEM-style security analysis — offering a flexible framework for high-throughput log processing on a single machine.

**Keywords:** SIEM, Log Processing, Python Multiprocessing, Real-Time Analytics, Parallel Processing, Apache Logs, Distributed Pipeline

---

## Table of contents

* [Features](#features)
* [Architecture](#architecture)
* [Quick Start](#quick-start)
* [Installation](#installation)
* [Dataset (LogHub - Apache)](#dataset-loghub---apache)
* [Usage Guide](#usage-guide)
* [Experiments & Analysis](#experiments--analysis)
* [Performance Findings (summary)](#performance-findings-summary)
* [Performance Tuning & Troubleshooting](#performance-tuning--troubleshooting)
* [Future Work](#future-work)
* [Recommendations](#recommendations)
* [Project structure](#project-structure)
* [Testing](#testing)
* [References](#references)
* [License](#license)
* [Contact](#contact)

---

## Features

* Streaming log processing with configurable ingestion rates
* Parallel parsing & enrichment using Python `multiprocessing`
* Real-time alerting using sliding-window rules
* Batched indexing to SQLite (default) with optional ClickHouse/Elasticsearch backends for scale
* Performance metrics collection (throughput, latency, CPU, memory)
* Automated experiment scripts for parameter grid search
* Jupyter notebooks for analysis and publication-quality plots

---

## Architecture

At a glance:

```
Log File → Replay → [Queue] → Parser Workers (N) → [Queue] → Indexer → Database (SQLite / ClickHouse)
                                               ↓
                                         Alerting Engine
                                               ↓
                                       Metrics Collector
```

* **Replay/Ingest:** simulates streaming by reading a log file and emitting events at a configurable rate.
* **Parser Workers:** multiple processes parse raw log lines and enrich events (IP, timestamp, user-agent, etc.).
* **Queues:** `multiprocessing.Queue` decouples stages and provides backpressure behavior.
* **Indexer:** batches events and performs efficient writes to the DB.
* **Alerting Engine:** evaluates sliding-window rules and writes alerts for investigation.
* **Metrics Collector:** records throughput, latency, and resource usage for analysis.

> *Place an architecture diagram here (e.g., `docs/arch.svg`).*

---

## Quick start

Try a quick demo using the included sample data (no Kaggle download required):

```bash
python src/siem_pipeline.py \
  --input sample_data/apache_sample.log \
  --workers 4 \
  --rate 500 \
  --batch 100 \
  --run-time 30 \
  --db results/test.db \
  --metrics results/test_metrics.csv
```

Verify results:

```bash
# Event count
sqlite3 results/test.db "SELECT COUNT(*) FROM events;"

# Recent alerts
sqlite3 results/test.db "SELECT * FROM alerts LIMIT 10;"

# Metrics preview
head results/test_metrics.csv
```

---

## Installation

**Prerequisites**

* Python 3.10+
* (Optional) Docker + Docker Compose — for ClickHouse backend
* (Optional) Kaggle API credentials to download LogHub dataset

**Clone and set up:**

```bash
git clone https://github.com/UsamaSani/SIEM_Lite.git
cd SIEM_Lite
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## Dataset (LogHub - Apache)

This project uses the LogHub - Apache Log Data dataset from Kaggle for experiments.

**Using Kaggle CLI (recommended):**

```bash
pip install kaggle
# place kaggle.json in ~/.kaggle/ (Linux/Mac) or C:\Users\<username>\.kaggle\ (Windows)
chmod 600 ~/.kaggle/kaggle.json
bash scripts/download_kaggle.sh
# or
kaggle datasets download -d omduggineni/loghub-apache-log-data
unzip loghub-apache-log-data.zip -d raw/
```

> If you don't want to download the full dataset, use `sample_data/apache_sample.log` for quick testing.

---

## Usage guide

### Preprocess raw logs

(Optional) create a cleaned / sampled log:

```bash
python scripts/preprocess.py \
  --input raw/Apache.log \
  --output cleaned.log \
  --sample 10000
```

### Run single experiment

```bash
python src/siem_pipeline.py \
  --input cleaned.log \
  --workers 8 \
  --rate 1000 \
  --batch 200 \
  --run-time 60 \
  --db results/events.db \
  --metrics results/metrics.csv
```

**Important parameters**

* `--input` : Path to log file
* `--workers` : Number of parser processes (default: 4)
* `--rate` : Events/sec (0 = unlimited)
* `--batch` : Indexer batch size (default: 100)
* `--run-time` : Duration in seconds
* `--db` : Output SQLite database path
* `--metrics`: Output metrics CSV path

---

## Experiments & analysis

Run a grid search of configurations to measure throughput and latency:

**Bash version**

```bash
bash scripts/run_experiments.sh
```

**Python (more flexible)**

```bash
python scripts/run_experiments.py \
  --input cleaned.log \
  --workers 1 2 4 8 \
  --rates 200 500 1000 \
  --batches 50 100 200 \
  --duration 60
```

Post-process:

```bash
python scripts/compute_latencies.py \
  --db results/events_w4_r500_b100.db \
  --output results/latency_stats.json

python scripts/plot_metrics.py \
  --metrics-dir results/ \
  --output-dir results/plots/
```

Open `notebooks/analysis.ipynb` for interactive exploration and figure generation.

> *Recommended: save experiment outputs to separate folders for easy comparison.*

---

## Performance findings (summary)

* **Primary bottleneck:** default SQLite backend becomes the limiting factor under very high ingestion rates (≥ ~5000 events/sec) due to write contention.
* **Parallel parsing:** parser workers scale with CPU cores (CPU-bound).
* **Indexer I/O:** single-threaded indexer is I/O-bound; batching significantly improves throughput.
* **Latency trends:** P50 and P95 latencies improve with more workers, but P99 may increase slightly due to scheduling and contention effects.
* **Empirical rule:** `workers ≈ CPU_cores - 2` is a practical starting point to avoid starving the indexer and metrics collector.

(Plots such as `latency_distribution.png`, `latency_percentiles.png`, and `queue_sizes.png` are generated by the analysis scripts — add them into `results/plots/`.)

---

## Performance tuning & troubleshooting

**Queue full / backpressure**

* Increase `--batch` (e.g., 500 or 1000) to reduce write overhead.
* Reduce `--rate` if indexer cannot keep up.
* Switch to `--backend clickhouse` for high-throughput experiments.

**Database locked / SQLite issues**

* The code configures `PRAGMA journal_mode=WAL`.
* Ensure a single indexer writes to the DB. For very high concurrency, use ClickHouse.

**CPU & memory**

* Use bounded queues (implemented) to limit memory growth.
* Start with `workers ≈ (cpu_cores - 2)` and tune experimentally.

---

## Future work

* Distributed processing with Ray/Dask for multi-node scaling
* Web UI for alert management and visualization (Flask/React or Grafana dashboards)
* ML-based anomaly detection to complement rule-based alerts
* Support for additional log formats (Nginx, Syslog)
* Prometheus metrics export for integration with Grafana
* Kubernetes manifests for cloud-native deployment

---

## Recommendations

1. **Choose database backend by expected load:**

   * SQLite is fine up to moderate rates (< ~5k events/sec).
   * Use ClickHouse for high-throughput workloads.

2. **Worker configuration:**

   * Start with `workers = cpu_cores - 2` and iterate using experiment scripts.

3. **Manage backpressure:**

   * Increase `--batch` first; it's a more efficient solution than throttling ingestion.
   * Use experiment scripts to find stable operating points before production deployment.

4. **Use the experiment automation:**

   * The `run_experiments` scripts help systematically identify the best configuration for your hardware and dataset.

---

## Project structure

```
src/               # core pipeline and utilities (siem_pipeline.py)
scripts/           # preprocessing, replay, experiments, analysis
notebooks/         # analysis notebooks
tests/             # unit tests
sample_data/       # small sample logs
results/           # experiment outputs (DBs, metrics, plots)
docs/              # documentation / report templates
```

---

## Testing

Run unit tests and coverage:

```bash
pytest tests/ -v
pytest tests/ --cov=src --cov-report=html
```

---

## References

* Omduggineni. (2024). LogHub - Apache Log Data [Dataset]. Kaggle. Accessed: November 23, 2024.
  `https://www.kaggle.com/datasets/omduggineni/loghub-apache-log-data`


## Contact

If you have questions, feature requests, or want to contribute:

* GitHub: `https://github.com/UsamaSani/SIEM_Lite`
* Issues & PRs are welcome!

