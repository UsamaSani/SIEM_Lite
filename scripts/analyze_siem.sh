#!/bin/bash

# SIEM Pipeline Complete Analysis Workflow
# This script runs experiments, computes statistics, and generates visualizations

set -e  # Exit on error

echo "============================================================"
echo "SIEM PIPELINE PERFORMANCE ANALYSIS"
echo "============================================================"
echo ""

# Configuration
INPUT_FILE="sample_data/cleaned.log"
OUTPUT_DIR="results/analysis_$(date +%Y%m%d_%H%M%S)"
DURATION=60

# Check if input file exists
if [ ! -f "$INPUT_FILE" ]; then
    echo "❌ Error: Input file not found: $INPUT_FILE"
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "📁 Output directory: $OUTPUT_DIR"
echo "📄 Input file: $INPUT_FILE"
echo "⏱️  Duration per experiment: ${DURATION}s"
echo ""

# ============================================================
# Step 1: Run Grid Experiments
# ============================================================
echo "============================================================"
echo "STEP 1: Running Grid Experiments"
echo "============================================================"
echo ""

python scripts/run_experiments.py \
    --input "$INPUT_FILE" \
    --workers 2 4 6 8 \
    --rates 300 500 1000 \
    --batches 50 100 \
    --duration $DURATION \
    --output-dir "$OUTPUT_DIR"

echo ""
echo "✅ Grid experiments complete"
echo ""

# ============================================================
# Step 2: Compute Latency Statistics for Each Experiment
# ============================================================
echo "============================================================"
echo "STEP 2: Computing Latency Statistics"
echo "============================================================"
echo ""

for db_file in "$OUTPUT_DIR"/events_*.db; do
    if [ -f "$db_file" ]; then
        exp_name=$(basename "$db_file" .db | sed 's/events_//')
        echo "📊 Processing: $exp_name"
        
        python scripts/compute_latencies.py \
            --db "$db_file" \
            --output "$OUTPUT_DIR/latency_${exp_name}.json"
    fi
done

echo ""
echo "✅ Latency analysis complete"
echo ""

# ============================================================
# Step 3: Generate Visualizations
# ============================================================
echo "============================================================"
echo "STEP 3: Generating Visualizations"
echo "============================================================"
echo ""

python scripts/plot_metrics.py \
    --metrics-dir "$OUTPUT_DIR" \
    --output-dir "$OUTPUT_DIR/plots"

echo ""
echo "✅ Visualizations complete"
echo ""

# ============================================================
# Step 4: Generate Comprehensive Report
# ============================================================
echo "============================================================"
echo "STEP 4: Generating Comprehensive Report"
echo "============================================================"
echo ""

REPORT_FILE="$OUTPUT_DIR/ANALYSIS_REPORT.txt"

cat > "$REPORT_FILE" << EOF
================================================================================
SIEM PIPELINE PERFORMANCE ANALYSIS REPORT
================================================================================
Generated: $(date)
Input File: $INPUT_FILE
Duration: ${DURATION}s per experiment
Output Directory: $OUTPUT_DIR

================================================================================
EXPERIMENTS RUN
================================================================================

EOF

# Add experiment summary
if [ -f "$OUTPUT_DIR/experiments_summary.json" ]; then
    python3 << PYTHON_EOF >> "$REPORT_FILE"
import json
with open('$OUTPUT_DIR/experiments_summary.json') as f:
    data = json.load(f)
    
print(f"Total Experiments: {len(data)}")
print(f"Successful: {sum(1 for x in data if x['success'])}")
print(f"Failed: {sum(1 for x in data if not x['success'])}")
print("\nExperiment Configurations:")
for exp in data:
    status = "✓" if exp['success'] else "✗"
    print(f"  [{status}] {exp['exp_id']}: workers={exp['workers']}, rate={exp['rate']}, batch={exp['batch']}")
PYTHON_EOF
fi

cat >> "$REPORT_FILE" << EOF

================================================================================
LATENCY STATISTICS SUMMARY
================================================================================

EOF

# Add latency summaries
for latency_file in "$OUTPUT_DIR"/latency_*.json; do
    if [ -f "$latency_file" ]; then
        exp_name=$(basename "$latency_file" .json | sed 's/latency_//')
        echo "Experiment: $exp_name" >> "$REPORT_FILE"
        python3 << PYTHON_EOF >> "$REPORT_FILE"
import json
with open('$latency_file') as f:
    data = json.load(f)
    print(f"  Count: {data['count']:,}")
    print(f"  Mean: {data['mean']:.2f}ms")
    print(f"  P50: {data['p50']:.2f}ms")
    print(f"  P95: {data['p95']:.2f}ms")
    print(f"  P99: {data['p99']:.2f}ms")
    print()
PYTHON_EOF
    fi
done

cat >> "$REPORT_FILE" << EOF

================================================================================
VISUALIZATIONS
================================================================================

Generated plots:
  - throughput.png
  - queue_sizes.png
  - resource_usage.png
  - alerts_over_time.png
  - scalability.png

All visualizations saved to: $OUTPUT_DIR/plots/

================================================================================
RECOMMENDATIONS
================================================================================

Based on the analysis, consider the following optimizations:

1. Worker Scaling:
   - Review scalability.png to find optimal worker count
   - More workers = better throughput, but diminishing returns
   - Sweet spot is usually 4-8 workers for most systems

2. Batch Size:
   - Larger batches (100-200) reduce database overhead
   - Smaller batches (25-50) reduce latency
   - Balance based on your latency requirements

3. Rate Limiting:
   - If actual throughput << target rate, increase rate limit
   - If queues are backing up, reduce rate or add workers

4. Latency Targets:
   - P95 < 50ms: Excellent
   - P95 < 100ms: Good
   - P95 > 200ms: Investigate bottlenecks

================================================================================
END OF REPORT
================================================================================
EOF

echo "✅ Report generated: $REPORT_FILE"
echo ""

# ============================================================
# Step 5: Display Summary
# ============================================================
echo "============================================================"
echo "ANALYSIS COMPLETE!"
echo "============================================================"
echo ""
echo "📊 Results saved to: $OUTPUT_DIR"
echo ""
echo "📁 Key files:"
echo "   - ANALYSIS_REPORT.txt (comprehensive report)"
echo "   - plots/ (visualizations)"
echo "   - experiments_summary.json (raw data)"
echo "   - latency_*.json (latency statistics)"
echo ""
echo "📈 To view plots:"
echo "   Open files in: $OUTPUT_DIR/plots/"
echo ""
echo "📄 To view report:"
echo "   cat $REPORT_FILE"
echo ""
echo "============================================================"