import argparse
import random
from pathlib import Path
import re


def is_suspicious_line(line: str) -> bool:
    """Check if a log line contains suspicious patterns."""
    # Check for error status codes (400-599)
    if re.search(r'" [4-5]\d{2} ', line):
        return True
    
    # Check for attack patterns
    line_lower = line.lower()
    attack_patterns = [
        '../', 'union select', '/etc/passwd', 'cmd=', 
        '<script', 'exec(', 'eval(', 'phpinfo', 'shell',
        'wget', 'curl', '../../', 'base64'
    ]
    
    return any(pattern in line_lower for pattern in attack_patterns)


def preprocess_log(input_file: str, output_file: str, sample: int = 0):
    """
    Clean and optionally sample Apache log file.
    PRESERVES ALL SUSPICIOUS EVENTS - only samples normal traffic.
    
    Args:
        input_file: Path to raw log file
        output_file: Path to output cleaned log
        sample: Number of NORMAL lines to sample (0 = all)
    """
    print(f"📄 Preprocessing: {input_file}")
    
    normal_lines = []
    suspicious_lines = []
    
    with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
        for i, line in enumerate(f):
            line = line.strip()
            if line:  # Skip empty lines
                if is_suspicious_line(line):
                    suspicious_lines.append(line)
                else:
                    normal_lines.append(line)
            
            if i % 100000 == 0 and i > 0:
                print(f"  Read {i:,} lines...")
    
    print(f"\n  📊 Statistics:")
    print(f"     Total lines: {len(normal_lines) + len(suspicious_lines):,}")
    print(f"     Normal lines: {len(normal_lines):,}")
    print(f"     Suspicious lines: {len(suspicious_lines):,}")
    print(f"     Suspicious %: {len(suspicious_lines)/(len(normal_lines)+len(suspicious_lines))*100:.2f}%")
    
    # Sample ONLY normal lines, keep ALL suspicious ones
    if sample > 0 and sample < len(normal_lines):
        normal_lines = random.sample(normal_lines, sample)
        print(f"\n  ✂️  Sampled {len(normal_lines):,} normal lines")
    
    # Combine: ALL suspicious + sampled normal
    all_lines = suspicious_lines + normal_lines
    
    # Shuffle to mix suspicious events throughout
    random.shuffle(all_lines)
    
    # Write output
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        for line in all_lines:
            f.write(line + '\n')
    
    print(f"\n  ✅ Saved to: {output_file}")
    print(f"  ✅ Total output lines: {len(all_lines):,}")
    print(f"  ✅ Kept ALL {len(suspicious_lines):,} suspicious events!")
    
    if len(suspicious_lines) > 0:
        print(f"\n  🎯 Alert potential: {len(suspicious_lines):,} suspicious events preserved")
        print(f"     (Need 5+ from same IP within 60s to trigger alert)")


def main():
    parser = argparse.ArgumentParser(
        description='Preprocess Apache logs (smart sampling - keeps ALL suspicious events)'
    )
    parser.add_argument('--input', required=True, help='Input log file')
    parser.add_argument('--output', required=True, help='Output cleaned log')
    parser.add_argument('--sample', type=int, default=0, 
                       help='Sample N NORMAL lines (0=all). Suspicious events always kept!')
    
    args = parser.parse_args()
    
    if not Path(args.input).exists():
        print(f"❌ Error: Input file not found: {args.input}")
        return
    
    preprocess_log(args.input, args.output, args.sample)


if __name__ == '__main__':
    main()