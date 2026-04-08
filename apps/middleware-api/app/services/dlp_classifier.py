"""DLP Classifier: deterministic classification of IOCs as internal or external."""

import ipaddress
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class DlpCache:
    """Immutable snapshot of DLP rules loaded from the database."""

    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = field(
        default_factory=list
    )
    domains: set[str] = field(default_factory=set)


class DlpClassifier:
    """Classifies IOCs as INTERNAL or PENDING based on cached DLP rules."""

    def __init__(self) -> None:
        self._cache = DlpCache()

    async def load(self, db: AsyncSession) -> None:
        """Load DLP rules from DB. Called at startup and on POST /api/dlp/refresh."""
        # Load internal CIDR blocks
        network_rows = await db.execute(
            text("SELECT cidr FROM internal_networks")
        )
        networks = [
            ipaddress.ip_network(str(row[0]), strict=False)
            for row in network_rows.fetchall()
        ]

        # Load internal domains (already lowercase in DB)
        domain_rows = await db.execute(
            text("SELECT domain FROM internal_domains")
        )
        domains = {str(row[0]) for row in domain_rows.fetchall()}

        # Atomic swap (GIL-safe reference assignment)
        self._cache = DlpCache(networks=networks, domains=domains)

    def is_internal_ip(self, ip: str) -> bool:
        """Check if IP falls within any internal CIDR block."""
        try:
            addr = ipaddress.ip_address(ip)
            return any(addr in net for net in self._cache.networks)
        except ValueError:
            return False

    def is_internal_domain(self, domain: str) -> bool:
        """Suffix match: api.staging.company.com matches company.com."""
        domain = domain.lower()
        parts = domain.split(".")
        for i in range(len(parts)):
            candidate = ".".join(parts[i:])
            if candidate in self._cache.domains:
                return True
        return False

    def classify(self, iocs: list[dict]) -> list[dict]:
        """Tag each IOC with status based on DLP rules.

        IP_ADDRESS and DOMAIN types are checked. Hashes always get PENDING.
        """
        for ioc in iocs:
            if ioc["type"] == "IP_ADDRESS" and self.is_internal_ip(ioc["value"]):
                ioc["status"] = "INTERNAL"
            elif ioc["type"] == "DOMAIN" and self.is_internal_domain(ioc["value"]):
                ioc["status"] = "INTERNAL"
            else:
                ioc["status"] = "PENDING"
        return iocs


# Module-level singleton
dlp_classifier = DlpClassifier()


def get_dlp_classifier() -> DlpClassifier:
    """FastAPI dependency: returns the DLP classifier singleton."""
    return dlp_classifier
