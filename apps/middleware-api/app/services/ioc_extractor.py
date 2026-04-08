"""
IOC-Extractor-Service: Extrahiert Indicators of Compromise aus Text.
Unterstuetzt IPs, Domains, MD5-, SHA1- und SHA256-Hashes mit Defanging.
"""
import re
import ipaddress

# Erlaubte Top-Level-Domains fuer die Domain-Validierung
VALID_TLDS = {
    "com", "net", "org", "io", "de", "ru", "cn", "uk", "info", "biz",
    "co", "us", "xyz", "top", "site", "online", "club", "app", "dev",
    "gov", "edu", "mil", "int",
}

# Regulaere Ausdruecke fuer die IOC-Extraktion (Reihenfolge: laengste Hashes zuerst)
_PATTERNS: list[tuple[str, str]] = [
    ("FILE_HASH_SHA256", r"\b[a-fA-F0-9]{64}\b"),
    ("FILE_HASH_SHA1",   r"\b[a-fA-F0-9]{40}\b"),
    ("FILE_HASH_MD5",    r"\b[a-fA-F0-9]{32}\b"),
    ("IP_ADDRESS",       r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    ("DOMAIN",           r"\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b"),
]

# Vorkompilierte Regex-Objekte fuer bessere Performance
_COMPILED: list[tuple[str, re.Pattern[str]]] = [
    (ioc_type, re.compile(pattern))
    for ioc_type, pattern in _PATTERNS
]


def _defang(text: str) -> str:
    """Normalisiert 'defangte' IOC-Schreibweisen zurueck in Klartextform."""
    # Protokoll-Defanging: hxxps -> https, hxxp -> http
    text = re.sub(r"hxxps", "https", text, flags=re.IGNORECASE)
    text = re.sub(r"hxxp",  "http",  text, flags=re.IGNORECASE)
    # Punkt-Defanging: [.] und [dot] -> .
    text = text.replace("[.]", ".")
    text = re.sub(r"\[dot\]", ".", text, flags=re.IGNORECASE)
    # Doppelpunkt-Defanging: [:] -> :
    text = text.replace("[:]", ":")
    return text


def _validate_ip(value: str) -> bool:
    """Prueft ob eine IP-Adresse gueltig ist (alle Oktette 0-255)."""
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def _validate_domain(value: str) -> bool:
    """Prueft ob eine Domain eine bekannte TLD hat."""
    tld = value.rsplit(".", 1)[-1].lower()
    return tld in VALID_TLDS


def extract_iocs(text: str) -> list[dict[str, str]]:
    """
    Extrahiert IOCs aus dem uebergebenen Text.

    Verarbeitung:
    1. Defanging des gesamten Textes
    2. Regex-Extraktion (SHA256 -> SHA1 -> MD5 -> IP -> Domain)
    3. Positions-Tracking verhindert Substring-Doppeltreffer
    4. Validierung der extrahierten Werte
    5. Deduplizierung nach (value, type)

    Args:
        text: Rohtext mit moeglichen IOCs (auch defangte Schreibweisen)

    Returns:
        Liste von Dicts mit den Schluesseln 'type' und 'value'
    """
    if not text:
        return []

    # Schritt 1: Defanging des Eingabetexts
    defanged_text = _defang(text)

    # Bereits gematchte Positionen (verhindert Substring-Ueberschneidungen)
    matched_positions: set[int] = set()

    # Ergebnisliste und Deduplizierungs-Set
    results: list[dict[str, str]] = []
    seen_values: set[tuple[str, str]] = set()

    for ioc_type, pattern in _COMPILED:
        for match in pattern.finditer(defanged_text):
            start, end = match.start(), match.end()
            match_positions = set(range(start, end))

            # Ueberspringe Treffer die bereits durch laengere Matches abgedeckt sind
            if match_positions & matched_positions:
                continue

            value = match.group()

            # Validierung je nach IOC-Typ
            if ioc_type == "IP_ADDRESS" and not _validate_ip(value):
                continue
            if ioc_type == "DOMAIN" and not _validate_domain(value):
                continue

            # Deduplizierung
            key = (value, ioc_type)
            if key in seen_values:
                continue

            # Positionen als belegt markieren
            matched_positions |= match_positions
            seen_values.add(key)
            results.append({"type": ioc_type, "value": value})

    return results
