"""Datenbank-Repository: alle Datenbankoperationen fuer Sessions und Assets."""

from ulid import ULID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AssetModel, SessionModel


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
