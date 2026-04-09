"""Datenbank-Repository: alle Datenbankoperationen fuer Sessions und Assets."""

from datetime import datetime, timezone

from ulid import ULID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import AssetModel, EnrichmentBatchModel, InternalDomainModel, InternalNetworkModel, SessionModel


async def create_session(db: AsyncSession, name: str) -> SessionModel:
    """Erstellt eine neue Analyse-Sitzung mit generierter ULID."""
    new_session = SessionModel(
        id=str(ULID()),
        name=name,
    )
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    return new_session


async def list_sessions(db: AsyncSession) -> list[SessionModel]:
    """Gibt alle Sitzungen absteigend nach Erstellungsdatum zurueck."""
    result = await db.execute(
        select(SessionModel).order_by(SessionModel.created_at.desc())
    )
    return list(result.scalars().all())


async def get_session(
    db: AsyncSession, session_id: str
) -> SessionModel | None:
    """Gibt eine Sitzung anhand ihrer ID zurueck oder None."""
    result = await db.execute(
        select(SessionModel).where(SessionModel.id == session_id)
    )
    return result.scalar_one_or_none()


async def get_session_with_assets(
    db: AsyncSession, session_id: str
) -> SessionModel | None:
    """Get a session with eager-loaded assets (avoids lazy-load outside async context)."""
    result = await db.execute(
        select(SessionModel)
        .where(SessionModel.id == session_id)
        .options(selectinload(SessionModel.assets))
    )
    return result.scalar_one_or_none()


async def create_assets(
    db: AsyncSession, session_id: str, assets: list[dict]
) -> list[AssetModel]:
    """Erstellt mehrere Assets fuer eine Sitzung auf einmal (Bulk-Insert)."""
    new_assets: list[AssetModel] = []
    for asset_data in assets:
        new_asset = AssetModel(
            id=str(ULID()),
            session_id=session_id,
            **asset_data,
        )
        db.add(new_asset)
        new_assets.append(new_asset)

    await db.commit()

    # Alle Assets aktualisieren (server-seitige Standardwerte laden)
    for asset in new_assets:
        await db.refresh(asset)

    return new_assets


async def update_asset_status(
    db: AsyncSession, asset_id: str, status: str
) -> AssetModel | None:
    """Aktualisiert den Status eines Assets und gibt das aktualisierte Asset zurueck."""
    result = await db.execute(
        select(AssetModel).where(AssetModel.id == asset_id)
    )
    asset = result.scalar_one_or_none()

    if asset is None:
        return None

    asset.status = status
    await db.commit()
    await db.refresh(asset)
    return asset


async def create_internal_network(
    db: AsyncSession, network_id: str, cidr: str, label: str | None
) -> InternalNetworkModel:
    """Create a new internal network CIDR block."""
    network = InternalNetworkModel(id=network_id, cidr=cidr, label=label)
    db.add(network)
    await db.commit()
    await db.refresh(network)
    return network


async def list_internal_networks(db: AsyncSession) -> list[InternalNetworkModel]:
    """List all internal networks ordered by creation date."""
    result = await db.execute(
        select(InternalNetworkModel).order_by(InternalNetworkModel.created_at.desc())
    )
    return list(result.scalars().all())


async def delete_internal_network(db: AsyncSession, network_id: str) -> bool:
    """Delete an internal network. Returns True if deleted, False if not found."""
    result = await db.execute(
        select(InternalNetworkModel).where(InternalNetworkModel.id == network_id)
    )
    network = result.scalar_one_or_none()
    if network is None:
        return False
    await db.delete(network)
    await db.commit()
    return True


async def create_internal_domain(
    db: AsyncSession, domain_id: str, domain: str, label: str | None
) -> InternalDomainModel:
    """Create a new internal domain."""
    entry = InternalDomainModel(id=domain_id, domain=domain, label=label)
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def list_internal_domains(db: AsyncSession) -> list[InternalDomainModel]:
    """List all internal domains ordered by creation date."""
    result = await db.execute(
        select(InternalDomainModel).order_by(InternalDomainModel.created_at.desc())
    )
    return list(result.scalars().all())


async def delete_internal_domain(db: AsyncSession, domain_id: str) -> bool:
    """Delete an internal domain. Returns True if deleted, False if not found."""
    result = await db.execute(
        select(InternalDomainModel).where(InternalDomainModel.id == domain_id)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        return False
    await db.delete(entry)
    await db.commit()
    return True


async def create_enrichment_batch(
    db: AsyncSession, batch_id: str, session_id: str, asset_ids: list[str]
) -> EnrichmentBatchModel:
    """Create a new enrichment batch record."""
    batch = EnrichmentBatchModel(
        id=batch_id, session_id=session_id, asset_ids=asset_ids
    )
    db.add(batch)
    await db.commit()
    await db.refresh(batch)
    return batch


async def get_enrichment_batch(
    db: AsyncSession, batch_id: str
) -> EnrichmentBatchModel | None:
    """Get an enrichment batch by ID."""
    result = await db.execute(
        select(EnrichmentBatchModel).where(EnrichmentBatchModel.id == batch_id)
    )
    return result.scalar_one_or_none()


async def update_batch_status(
    db: AsyncSession, batch_id: str, status: str
) -> None:
    """Update batch status and set completed_at if terminal."""
    result = await db.execute(
        select(EnrichmentBatchModel).where(EnrichmentBatchModel.id == batch_id)
    )
    batch = result.scalar_one_or_none()
    if batch:
        batch.status = status
        if status in ("COMPLETED", "PARTIAL", "FAILED"):
            batch.completed_at = datetime.now(timezone.utc)
        await db.commit()


async def bulk_mark_assets_processing(
    db: AsyncSession, asset_ids: list[str]
) -> None:
    """Mark multiple assets as PROCESSING in one transaction."""
    for asset_id in asset_ids:
        result = await db.execute(
            select(AssetModel).where(AssetModel.id == asset_id)
        )
        asset = result.scalar_one_or_none()
        if asset:
            asset.status = "PROCESSING"
    await db.commit()


async def bulk_revert_assets_to_pending(
    db: AsyncSession, asset_ids: list[str]
) -> None:
    """Revert assets from PROCESSING back to PENDING (compensating transaction)."""
    for asset_id in asset_ids:
        result = await db.execute(
            select(AssetModel).where(
                AssetModel.id == asset_id,
            )
        )
        asset = result.scalar_one_or_none()
        if asset and asset.status == "PROCESSING":
            asset.status = "PENDING"
    await db.commit()


async def update_asset_enrichment(
    db: AsyncSession, asset_id: str, status: str, enrichment_data: dict
) -> bool:
    """Update asset status and enrichment data. Only updates if currently PROCESSING."""
    result = await db.execute(
        select(AssetModel).where(
            AssetModel.id == asset_id,
        )
    )
    asset = result.scalar_one_or_none()
    if asset and asset.status == "PROCESSING":
        asset.status = status
        asset.enrichment_data = enrichment_data
        return True
    return False


async def get_assets_by_ids(
    db: AsyncSession, session_id: str, asset_ids: list[str]
) -> list[AssetModel]:
    """Get assets by IDs within a session."""
    result = await db.execute(
        select(AssetModel).where(
            AssetModel.session_id == session_id,
            AssetModel.id.in_(asset_ids),
        )
    )
    return list(result.scalars().all())
