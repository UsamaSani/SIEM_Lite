import re
from datetime import datetime
from typing import Dict, Optional, Tuple, Any
from functools import lru_cache


def parse_apache_log(line: str) -> Optional[Dict[str, Any]]:
    """
    Parse Apache log lines (both error/notice and request formats).

    Supports:
    1. Error/Notice format: [timestamp] [level] [context] message
    2. Request format: IP - - [timestamp] "METHOD /path HTTP/1.1" status bytes

    Args:
        line: Raw log line

    Returns:
        Dictionary with parsed fields or None if parsing fails
    """
    line = line.strip()
    if not line:
        return None
    
    # Try Apache error/notice log format: [timestamp] [level] [context] message
    error_pattern = r'^\[([\w\s:/\+\-]+)\] \[(\w+)\](?:\s\[([^\]]+)\])?\s(.+)$'
    match = re.match(error_pattern, line)
    if match:
        timestamp_str, level, context, message = match.groups()
        try:
            timestamp = datetime.strptime(timestamp_str, '%a %b %d %H:%M:%S %Y')
        except ValueError:
            timestamp = datetime.now()
        
        # Extract IP from context if present
        ip_match = re.search(r'client\s([\d\.]+)', context or '')
        ip = ip_match.group(1) if ip_match else ''
        
        return {
            'ip': ip,
            'timestamp': timestamp,
            'method': 'LOG',
            'url': message[:100],
            'status': 400 if level == 'error' else 200,
            'bytes': 0,
            'referer': context or '',
            'user_agent': level,
        }
    
    # Try Apache Combined Log Format: IP - - [timestamp] "METHOD /path HTTP/1.1" status bytes "referer" "user-agent"
    clf_pattern = r'^(\S+) \S+ \S+ \[([\w:/]+\s[+\-]\d{4})\] "(\S+) (\S+) \S+" (\d{3}) (\S+)(?: "([^"]*)" "([^"]*)")?'
    match = re.match(clf_pattern, line)
    if match:
        ip, timestamp_str, method, url, status, bytes_sent, referer, user_agent = match.groups()
        try:
            timestamp = datetime.strptime(timestamp_str.split()[0], '%d/%b/%Y:%H:%M:%S')
        except ValueError:
            timestamp = datetime.now()
        
        try:
            bytes_sent = int(bytes_sent) if bytes_sent != '-' else 0
        except ValueError:
            bytes_sent = 0
        
        return {
            'ip': ip,
            'timestamp': timestamp,
            'method': method,
            'url': url,
            'status': int(status),
            'bytes': bytes_sent,
            'referer': referer if referer else '',
            'user_agent': user_agent if user_agent else '',
        }
    
    return None


@lru_cache(maxsize=10000)
def enrich_ip(ip: str) -> Dict[str, str]:
    """
    Lightweight IP enrichment with caching.

    In production, this would do GeoIP lookup. For this demo,
    we classify IPs into simple categories.

    Args:
        ip: IP address

    Returns:
        Dictionary with enrichment data
    """
    # Simple classification based on IP prefix
    if ip.startswith('10.') or ip.startswith('192.168.') or ip.startswith('172.'):
        return {'ip_class': 'private', 'suspicious': False}
    elif ip.startswith('127.'):
        return {'ip_class': 'localhost', 'suspicious': False}
    else:
        return {'ip_class': 'public', 'suspicious': False}


def enrich_user_agent(user_agent: str) -> Dict[str, Any]:
    """
    Simple user-agent enrichment.

    Args:
        user_agent: User-Agent string

    Returns:
        Dictionary with browser/os info
    """
    ua_lower = user_agent.lower()
    
    # Detect browser
    if 'firefox' in ua_lower:
        browser = 'Firefox'
    elif 'chrome' in ua_lower:
        browser = 'Chrome'
    elif 'safari' in ua_lower:
        browser = 'Safari'
    elif 'msie' in ua_lower or 'trident' in ua_lower:
        browser = 'Internet Explorer'
    else:
        browser = 'Other'
    
    # Detect OS
    if 'windows' in ua_lower:
        os = 'Windows'
    elif 'mac' in ua_lower or 'darwin' in ua_lower:
        os = 'macOS'
    elif 'linux' in ua_lower:
        os = 'Linux'
    elif 'android' in ua_lower:
        os = 'Android'
    elif 'ios' in ua_lower or 'iphone' in ua_lower or 'ipad' in ua_lower:
        os = 'iOS'
    else:
        os = 'Other'
    
    return {'browser': browser, 'os': os}


def is_suspicious(event: Dict[str, Any]) -> bool:
    """
    Determine if an event is suspicious.

    Simple heuristics:
    - Status code >= 400 (client/server errors)
    - Known attack patterns in URL

    Args:
        event: Parsed event dictionary

    Returns:
        True if suspicious, False otherwise
    """
    # Error status codes
    if event.get('status', 0) >= 400:
        return True
    
    # Common attack patterns
    url = event.get('url', '').lower()
    attack_patterns = [
        '../',  # Path traversal
        'script>',  # XSS
        'union select',  # SQL injection
        '/etc/passwd',  # File inclusion
        'cmd=',  # Command injection
    ]
    
    return any(pattern in url for pattern in attack_patterns)


def format_metrics_row(metrics: Dict[str, Any]) -> str:
    """Format metrics dictionary as CSV row."""
    return ','.join(str(v) for v in metrics.values())


def get_metrics_header() -> str:
    """Get CSV header for metrics."""
    return 'timestamp,events_processed,queue_size,cpu_percent,memory_mb,throughput,alerts_count'
