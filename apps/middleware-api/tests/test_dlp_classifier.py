"""Unit tests for the DLP classifier service."""

import ipaddress

import pytest

from app.services.dlp_classifier import DlpCache, DlpClassifier


class TestIsInternalIp:
    """Tests for IP address classification against CIDR blocks."""

    def setup_method(self) -> None:
        self.classifier = DlpClassifier()
        self.classifier._cache = DlpCache(
            networks=[
                ipaddress.ip_network("10.0.0.0/8"),
                ipaddress.ip_network("192.168.1.0/24"),
            ],
            domains=set(),
        )

    def test_ip_in_private_range_is_internal(self) -> None:
        assert self.classifier.is_internal_ip("10.0.0.1") is True

    def test_ip_in_specific_subnet_is_internal(self) -> None:
        assert self.classifier.is_internal_ip("192.168.1.100") is True

    def test_ip_outside_all_ranges_is_not_internal(self) -> None:
        assert self.classifier.is_internal_ip("8.8.8.8") is False

    def test_ip_in_adjacent_subnet_is_not_internal(self) -> None:
        assert self.classifier.is_internal_ip("192.168.2.1") is False

    def test_malformed_ip_returns_false(self) -> None:
        assert self.classifier.is_internal_ip("not-an-ip") is False

    def test_empty_string_returns_false(self) -> None:
        assert self.classifier.is_internal_ip("") is False


class TestIsInternalDomain:
    """Tests for domain classification with suffix matching."""

    def setup_method(self) -> None:
        self.classifier = DlpClassifier()
        self.classifier._cache = DlpCache(
            networks=[],
            domains={"company.com", "internal.net"},
        )

    def test_exact_match_is_internal(self) -> None:
        assert self.classifier.is_internal_domain("company.com") is True

    def test_subdomain_matches_parent(self) -> None:
        assert self.classifier.is_internal_domain("api.company.com") is True

    def test_deep_subdomain_matches_parent(self) -> None:
        assert self.classifier.is_internal_domain("staging.api.company.com") is True

    def test_unrelated_domain_is_not_internal(self) -> None:
        assert self.classifier.is_internal_domain("google.com") is False

    def test_partial_name_does_not_match(self) -> None:
        """evilcompany.com should NOT match company.com."""
        assert self.classifier.is_internal_domain("evilcompany.com") is False

    def test_case_insensitive_matching(self) -> None:
        assert self.classifier.is_internal_domain("API.Company.COM") is True

    def test_second_domain_matches(self) -> None:
        assert self.classifier.is_internal_domain("mail.internal.net") is True


class TestClassify:
    """Tests for the full classify() pipeline."""

    def setup_method(self) -> None:
        self.classifier = DlpClassifier()
        self.classifier._cache = DlpCache(
            networks=[ipaddress.ip_network("10.0.0.0/8")],
            domains={"company.com"},
        )

    def test_internal_ip_gets_internal_status(self) -> None:
        iocs = [{"type": "IP_ADDRESS", "value": "10.1.2.3"}]
        result = self.classifier.classify(iocs)
        assert result[0]["status"] == "INTERNAL"

    def test_external_ip_gets_pending_status(self) -> None:
        iocs = [{"type": "IP_ADDRESS", "value": "8.8.8.8"}]
        result = self.classifier.classify(iocs)
        assert result[0]["status"] == "PENDING"

    def test_internal_domain_gets_internal_status(self) -> None:
        iocs = [{"type": "DOMAIN", "value": "api.company.com"}]
        result = self.classifier.classify(iocs)
        assert result[0]["status"] == "INTERNAL"

    def test_external_domain_gets_pending_status(self) -> None:
        iocs = [{"type": "DOMAIN", "value": "evil.com"}]
        result = self.classifier.classify(iocs)
        assert result[0]["status"] == "PENDING"

    def test_hash_always_gets_pending_status(self) -> None:
        iocs = [{"type": "FILE_HASH_SHA256", "value": "a" * 64}]
        result = self.classifier.classify(iocs)
        assert result[0]["status"] == "PENDING"

    def test_mixed_iocs_classified_correctly(self) -> None:
        iocs = [
            {"type": "IP_ADDRESS", "value": "10.0.0.1"},
            {"type": "IP_ADDRESS", "value": "1.1.1.1"},
            {"type": "DOMAIN", "value": "api.company.com"},
            {"type": "DOMAIN", "value": "google.com"},
            {"type": "FILE_HASH_MD5", "value": "d" * 32},
        ]
        result = self.classifier.classify(iocs)
        assert [r["status"] for r in result] == [
            "INTERNAL", "PENDING", "INTERNAL", "PENDING", "PENDING"
        ]

    def test_empty_list_returns_empty(self) -> None:
        assert self.classifier.classify([]) == []
