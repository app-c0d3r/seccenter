"""Datenbank-Repository: alle Datenbankoperationen fuer Sessions und Assets."""

from ulid import ULID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AssetModel, InternalDomainModel, InternalNetworkModel, SessionModel


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
