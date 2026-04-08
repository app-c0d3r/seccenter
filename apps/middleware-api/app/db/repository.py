"""Datenbank-Repository: alle Datenbankoperationen fuer Sessions und Assets."""

from python_ulid import ULID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AssetModell, SitzungsModell


async def sitzung_erstellen(db: AsyncSession, name: str) -> SitzungsModell:
    """Erstellt eine neue Analyse-Sitzung mit generierter ULID."""
    neue_sitzung = SitzungsModell(
        id=str(ULID()),
        name=name,
    )
    db.add(neue_sitzung)
    await db.commit()
    await db.refresh(neue_sitzung)
    return neue_sitzung


# Alias fuer englische API-Kompatibilitaet
create_session = sitzung_erstellen


async def sitzungen_auflisten(db: AsyncSession) -> list[SitzungsModell]:
    """Gibt alle Sitzungen absteigend nach Erstellungsdatum zurueck."""
    ergebnis = await db.execute(
        select(SitzungsModell).order_by(SitzungsModell.erstellt_am.desc())
    )
    return list(ergebnis.scalars().all())


# Alias
list_sessions = sitzungen_auflisten


async def sitzung_abrufen(
    db: AsyncSession, sitzungs_id: str
) -> SitzungsModell | None:
    """Gibt eine Sitzung anhand ihrer ID zurueck oder None."""
    ergebnis = await db.execute(
        select(SitzungsModell).where(SitzungsModell.id == sitzungs_id)
    )
    return ergebnis.scalar_one_or_none()


# Alias
get_session = sitzung_abrufen


async def assets_erstellen(
    db: AsyncSession, sitzungs_id: str, assets: list[dict]
) -> list[AssetModell]:
    """Erstellt mehrere Assets fuer eine Sitzung auf einmal (Bulk-Insert)."""
    neue_assets: list[AssetModell] = []
    for asset_daten in assets:
        neues_asset = AssetModell(
            id=str(ULID()),
            session_id=sitzungs_id,
            **asset_daten,
        )
        db.add(neues_asset)
        neue_assets.append(neues_asset)

    await db.commit()

    # Alle Assets aktualisieren (server-seitige Standardwerte laden)
    for asset in neue_assets:
        await db.refresh(asset)

    return neue_assets


# Alias
create_assets = assets_erstellen


async def asset_status_aktualisieren(
    db: AsyncSession, asset_id: str, status: str
) -> AssetModell | None:
    """Aktualisiert den Status eines Assets und gibt das aktualisierte Asset zurueck."""
    ergebnis = await db.execute(
        select(AssetModell).where(AssetModell.id == asset_id)
    )
    asset = ergebnis.scalar_one_or_none()

    if asset is None:
        return None

    asset.status = status
    await db.commit()
    await db.refresh(asset)
    return asset


# Alias
update_asset_status = asset_status_aktualisieren
