# Tests fuer den IOC-Extractor-Service
from app.services.ioc_extractor import extract_iocs


def test_extract_ipv4():
    text = "Server at 192.168.1.1 responded"
    results = extract_iocs(text)
    ips = [r for r in results if r["type"] == "IP_ADDRESS"]
    assert len(ips) == 1
    assert ips[0]["value"] == "192.168.1.1"


def test_reject_invalid_ip():
    text = "Invalid IP 999.999.999.999 in report"
    results = extract_iocs(text)
    ips = [r for r in results if r["type"] == "IP_ADDRESS"]
    assert len(ips) == 0


def test_extract_domain():
    text = "Visited evil.example.com today"
    results = extract_iocs(text)
    domains = [r for r in results if r["type"] == "DOMAIN"]
    assert any(d["value"] == "evil.example.com" for d in domains)


def test_defang_domain():
    text = "Visited evil[.]example[.]com today"
    results = extract_iocs(text)
    domains = [r for r in results if r["type"] == "DOMAIN"]
    assert any(d["value"] == "evil.example.com" for d in domains)


def test_extract_md5():
    text = "Hash: d41d8cd98f00b204e9800998ecf8427e"
    results = extract_iocs(text)
    hashes = [r for r in results if r["type"] == "FILE_HASH_MD5"]
    assert len(hashes) == 1
    assert hashes[0]["value"] == "d41d8cd98f00b204e9800998ecf8427e"


def test_extract_sha256():
    text = "SHA256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    results = extract_iocs(text)
    hashes = [r for r in results if r["type"] == "FILE_HASH_SHA256"]
    assert len(hashes) == 1


def test_defang_url():
    text = "URL: hxxps://malware[.]example[.]com/payload"
    results = extract_iocs(text)
    domains = [r for r in results if r["type"] == "DOMAIN"]
    assert any(d["value"] == "malware.example.com" for d in domains)


def test_deduplication():
    text = "IP 10.0.0.1 found again at 10.0.0.1"
    results = extract_iocs(text)
    ips = [r for r in results if r["type"] == "IP_ADDRESS"]
    assert len(ips) == 1


def test_empty_input():
    results = extract_iocs("")
    assert results == []
