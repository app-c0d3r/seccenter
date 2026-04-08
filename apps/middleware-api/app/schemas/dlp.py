"""Pydantic schemas for DLP management endpoints."""

from datetime import datetime

from pydantic import BaseModel, IPvAnyNetwork, field_validator


class InternalNetworkCreate(BaseModel):
    """Request schema for creating an internal network CIDR block."""

    cidr: IPvAnyNetwork
    label: str | None = None


class InternalNetworkResponse(BaseModel):
    """Response schema for an internal network entry."""

    id: str
    cidr: str
    label: str | None
    created_at: datetime

    @field_validator("cidr", mode="before")
    @classmethod
    def cidr_to_str(cls, v: object) -> str:
        """Convert IPv4Network/IPv6Network from DB to string."""
        return str(v)

    model_config = {"from_attributes": True}


class InternalDomainCreate(BaseModel):
    """Request schema for creating an internal domain."""

    domain: str
    label: str | None = None

    @field_validator("domain")
    @classmethod
    def normalize_domain(cls, v: str) -> str:
        """Normalize domain to lowercase and strip whitespace."""
        return v.strip().lower()


class InternalDomainResponse(BaseModel):
    """Response schema for an internal domain entry."""

    id: str
    domain: str
    label: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
