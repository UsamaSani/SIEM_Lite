import argparse
import random
from pathlib import Path


def preprocess_log(input_file: str, output_file: str, sample: int = 0):
    """
    Clean and optionally sample Apache log file.
    
    Args:
        input_file: Path to raw log file
        output_file: Path to output cleaned log
        sample: Number of lines to sample (0 = all)
    """
    print(f"📄 Preprocessing: {input_file}")
    
    lines = []
    with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
        for i, line in enumerate(f):
            line = line.strip()
            if line:  # Skip empty lines
                lines.append(line)
            
            if i % 100000 == 0 and i > 0:
                print(f"  Read {i:,} lines...")
    
    print(f"  Total lines: {len(lines):,}")
    
    # Sample if requested
    if sample > 0 and sample < len(lines):
        lines = random.sample(lines, sample)
        print(f"  Sampled: {len(lines):,} lines")
    
    # Write output
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        for line in lines:
            f.write(line + '\\n')
    
    print(f"[OK] Saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Preprocess Apache logs')
    parser.add_argument('--input', required=True, help='Input log file')
    parser.add_argument('--output', required=True, help='Output cleaned log')
    parser.add_argument('--sample', type=int, default=0, 
                       help='Sample N lines (0=all)')
    
    args = parser.parse_args()
    
    preprocess_log(args.input, args.output, args.sample)


if __name__ == '__main__':
    main()