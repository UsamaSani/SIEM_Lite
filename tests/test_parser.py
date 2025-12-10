import pytest
from datetime import datetime
from src.utils import (
    parse_apache_log, 
    enrich_ip, 
    enrich_user_agent, 
    is_suspicious
)


def test_parse_apache_log_valid():
    """Test parsing valid Apache log line."""
    line = '192.168.1.1 - - [01/Jul/1995:00:00:01 -0400] "GET /index.html HTTP/1.0" 200 1234 "-" "Mozilla/5.0"'
    
    event = parse_apache_log(line)
    
    assert event is not None
    assert event['ip'] == '192.168.1.1'
    assert event['method'] == 'GET'
    assert event['url'] == '/index.html'
    assert event['status'] == 200
    assert event['bytes'] == 1234
    assert event['user_agent'] == 'Mozilla/5.0'


def test_parse_apache_log_invalid():
    """Test parsing invalid log line."""
    line = 'invalid log line'
    
    event = parse_apache_log(line)
    
    assert event is None


def test_parse_apache_log_missing_bytes():
    """Test parsing log with missing bytes field."""
    line = '10.0.0.1 - - [01/Jul/1995:00:00:01 -0400] "POST /api HTTP/1.1" 404 - "-" "curl/7.0"'
    
    event = parse_apache_log(line)
    
    assert event is not None
    assert event['bytes'] == 0  # Should handle '-' as 0


def test_enrich_ip_private():
    """Test IP enrichment for private IP."""
    result = enrich_ip('192.168.1.1')
    
    assert result['ip_class'] == 'private'
    assert result['suspicious'] == False


def test_enrich_ip_public():
    """Test IP enrichment for public IP."""
    result = enrich_ip('8.8.8.8')
    
    assert result['ip_class'] == 'public'


def test_enrich_ip_caching():
    """Test that IP enrichment is cached."""
    # First call
    result1 = enrich_ip('1.2.3.4')
    
    # Second call should return cached result
    result2 = enrich_ip('1.2.3.4')
    
    assert result1 == result2


def test_enrich_user_agent_firefox():
    """Test user-agent enrichment for Firefox."""
    ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0'
    
    result = enrich_user_agent(ua)
    
    assert result['browser'] == 'Firefox'
    assert result['os'] == 'Windows'


def test_enrich_user_agent_chrome():
    """Test user-agent enrichment for Chrome."""
    ua = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/91.0'
    
    result = enrich_user_agent(ua)
    
    assert result['browser'] == 'Chrome'
    assert result['os'] == 'macOS'


def test_is_suspicious_error_status():
    """Test suspicious detection for error status."""
    event = {'status': 404, 'url': '/index.html'}
    
    assert is_suspicious(event) == True


def test_is_suspicious_attack_pattern():
    """Test suspicious detection for attack pattern."""
    event = {'status': 200, 'url': '/admin/../../../etc/passwd'}
    
    assert is_suspicious(event) == True


def test_is_suspicious_normal():
    """Test non-suspicious event."""
    event = {'status': 200, 'url': '/index.html'}
    
    assert is_suspicious(event) == False


def test_parse_apache_log_timestamp():
    """Test timestamp parsing."""
    line = '10.0.0.1 - - [01/Jul/1995:00:00:01 -0400] "GET / HTTP/1.0" 200 100 "-" "-"'
    
    event = parse_apache_log(line)
    
    assert isinstance(event['timestamp'], datetime)
    assert event['timestamp'].year == 1995
    assert event['timestamp'].month == 7
    assert event['timestamp'].day == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])