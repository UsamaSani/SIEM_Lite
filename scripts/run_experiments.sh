!/bin/bash
# Automated experiment runner

set -e

INPUT_FILE="${INPUT_FILE:-sample_data/apache_sample.log}"
DURATION="${DURATION:-60}"
OUTPUT_DIR="${OUTPUT_DIR:-results}"

echo "========================================="
echo "🧪 Running SIEM-lite Experiments"
echo "========================================="
echo "Input: $INPUT_FILE"
echo "Duration: ${DURATION}s per experiment"
echo "Output: $OUTPUT_DIR"
echo "========================================="

mkdir -p "$OUTPUT_DIR"

# Parameter grid
WORKERS=(1 2 4 8)
RATES=(200 500 1000)
BATCHES=(50 100 200)

# Run experiments
for workers in "${WORKERS[@]}"; do
  for rate in "${RATES[@]}"; do
    for batch in "${BATCHES[@]}"; do
      EXP_ID="w${workers}_r${rate}_b${batch}"
      echo ""
      echo "🔬 Experiment: $EXP_ID"
      
      python src/siem_pipeline.py \\
        --input "$INPUT_FILE" \\
        --workers "$workers" \\
        --rate "$rate" \\
        --batch "$batch" \\
        --run-time "$DURATION" \\
        --db "$OUTPUT_DIR/events_$EXP_ID.db" \\
        --metrics "$OUTPUT_DIR/metrics_$EXP_ID.csv"
      
      echo "✅ $EXP_ID complete"
    done
  done
done

echo ""
echo "========================================="
echo "✅ All experiments complete!"
echo "Results in: $OUTPUT_DIR"
echo "========================================="