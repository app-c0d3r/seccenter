"""FastAPI router for DLP management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import ULID

from app.db.connection import get_db
from app.db import repository
from app.schemas.dlp import (
    InternalDomainCreate,
    InternalDomainResponse,
    InternalNetworkCreate,
    InternalNetworkResponse,
)
from app.services.dlp_classifier import dlp_classifier

router = APIRouter(prefix="/api/dlp", tags=["dlp"])


# --- Internal Networks ---


@router.post("/networks", response_model=InternalNetworkResponse, status_code=201)
async def create_network(
    body: InternalNetworkCreate,
    db: AsyncSession = Depends(get_db),
) -> InternalNetworkResponse:
    """Add an internal CIDR block to the DLP rules."""
    try:
        network = await repository.create_internal_network(
            db,
            network_id=str(ULID()),
            cidr=str(body.cidr),
            label=body.label,
        )
    except IntegrityError:
        raise HTTPException(status_code=409, detail="CIDR block already exists")
    return InternalNetworkResponse.model_validate(network)


@router.get("/networks", response_model=list[InternalNetworkResponse])
async def list_networks(
    db: AsyncSession = Depends(get_db),
) -> list[InternalNetworkResponse]:
    """List all internal network CIDR blocks."""
    networks = await repository.list_internal_networks(db)
    return [InternalNetworkResponse.model_validate(n) for n in networks]


@router.delete("/networks/{network_id}", status_code=204)
async def delete_network(
    network_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Remove an internal CIDR block."""
    deleted = await repository.delete_internal_network(db, network_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Network not found")
    return Response(status_code=204)


# --- Internal Domains ---


@router.post("/domains", response_model=InternalDomainResponse, status_code=201)
async def create_domain(
    body: InternalDomainCreate,
    db: AsyncSession = Depends(get_db),
) -> InternalDomainResponse:
    """Add an internal domain to the DLP rules."""
    try:
        entry = await repository.create_internal_domain(
            db,
            domain_id=str(ULID()),
            domain=body.domain,
            label=body.label,
        )
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Domain already exists")
    return InternalDomainResponse.model_validate(entry)


@router.get("/domains", response_model=list[InternalDomainResponse])
async def list_domains(
    db: AsyncSession = Depends(get_db),
) -> list[InternalDomainResponse]:
    """List all internal domains."""
    domains = await repository.list_internal_domains(db)
    return [InternalDomainResponse.model_validate(d) for d in domains]


@router.delete("/domains/{domain_id}", status_code=204)
async def delete_domain(
    domain_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Remove an internal domain."""
    deleted = await repository.delete_internal_domain(db, domain_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Domain not found")
    return Response(status_code=204)


# --- Cache Refresh ---


@router.post("/refresh", status_code=204)
async def refresh_cache(
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Force-reload the DLP classifier cache from the database."""
    await dlp_classifier.load(db)
    return Response(status_code=204)
