"""Tests for the DLP masking context used in AI agent proxy."""

import pytest

from app.services.dlp_masking import DLPMaskingContext


class FakeAsset:
    """Minimal asset stand-in for testing (matches AssetModel interface)."""

    def __init__(self, value: str, type: str, status: str):
        self.value = value
        self.type = type
        self.status = status


class TestDLPMaskingContext:
    """Tests for ephemeral mask/unmask map construction."""

    def test_internal_ip_masked(self):
        """Internal IP assets get [INTERNAL_IP_NNN] tokens."""
        assets = [FakeAsset("192.168.1.1", "IP_ADDRESS", "INTERNAL")]
        ctx = DLPMaskingContext(assets)
        assert ctx.mask("Found 192.168.1.1 in logs") == "Found [INTERNAL_IP_001] in logs"

    def test_external_assets_not_masked(self):
        """Non-INTERNAL assets are not masked."""
        assets = [
            FakeAsset("8.8.8.8", "IP_ADDRESS", "ENRICHED"),
            FakeAsset("1.1.1.1", "IP_ADDRESS", "PENDING"),
        ]
        ctx = DLPMaskingContext(assets)
        assert ctx.mask("DNS: 8.8.8.8 and 1.1.1.1") == "DNS: 8.8.8.8 and 1.1.1.1"

    def test_multiple_internal_ips_numbered(self):
        """Multiple internal IPs get sequential tokens."""
        assets = [
            FakeAsset("10.0.0.1", "IP_ADDRESS", "INTERNAL"),
            FakeAsset("10.0.0.2", "IP_ADDRESS", "INTERNAL"),
        ]
        ctx = DLPMaskingContext(assets)
        masked = ctx.mask("Hosts: 10.0.0.1 and 10.0.0.2")
        assert "[INTERNAL_IP_001]" in masked
        assert "[INTERNAL_IP_002]" in masked
        assert "10.0.0.1" not in masked
        assert "10.0.0.2" not in masked

    def test_domain_masked(self):
        """Internal domains get [INTERNAL_DOMAIN_NNN] tokens."""
        assets = [FakeAsset("private.corp.local", "DOMAIN", "INTERNAL")]
        ctx = DLPMaskingContext(assets)
        assert ctx.mask("Resolved private.corp.local") == "Resolved [INTERNAL_DOMAIN_001]"

    def test_unmask_reverses_mask(self):
        """Unmasking restores original values."""
        assets = [
            FakeAsset("10.0.0.1", "IP_ADDRESS", "INTERNAL"),
            FakeAsset("internal.corp", "DOMAIN", "INTERNAL"),
        ]
        ctx = DLPMaskingContext(assets)
        original = "Attack from 10.0.0.1 targeting internal.corp"
        masked = ctx.mask(original)
        assert "10.0.0.1" not in masked
        assert "internal.corp" not in masked
        assert ctx.unmask(masked) == original

    def test_file_hash_masked(self):
        """Internal file hashes get [INTERNAL_FILE_NNN] tokens."""
        assets = [FakeAsset("abc123def456", "FILE_HASH_MD5", "INTERNAL")]
        ctx = DLPMaskingContext(assets)
        assert ctx.mask("Hash: abc123def456") == "Hash: [INTERNAL_FILE_001]"

    def test_mixed_types_counted_separately(self):
        """Each type has its own counter."""
        assets = [
            FakeAsset("10.0.0.1", "IP_ADDRESS", "INTERNAL"),
            FakeAsset("private.corp", "DOMAIN", "INTERNAL"),
            FakeAsset("10.0.0.2", "IP_ADDRESS", "INTERNAL"),
        ]
        ctx = DLPMaskingContext(assets)
        masked = ctx.mask("IP 10.0.0.1, domain private.corp, IP 10.0.0.2")
        assert "[INTERNAL_IP_001]" in masked
        assert "[INTERNAL_IP_002]" in masked
        assert "[INTERNAL_DOMAIN_001]" in masked
