"""FastAPI-Router fuer Session-Endpunkte."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.connection import get_db
from app.db import repository
from app.schemas.asset import AssetResponse, AssetStatusUpdate
from app.schemas.session import SessionCreate, SessionResponse, SessionWithAssetsResponse

# Router mit Praefix und Tag fuer API-Dokumentation
router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    body: SessionCreate,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Erstellt eine neue Analyse-Sitzung."""
    session = await repository.create_session(db, name=body.name)
    return SessionResponse.model_validate(session)


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
) -> list[SessionResponse]:
    """Gibt alle Sitzungen absteigend nach Erstellungsdatum zurueck."""
    sessions = await repository.list_sessions(db)
    return [SessionResponse.model_validate(s) for s in sessions]


@router.get("/{session_id}", response_model=SessionWithAssetsResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> SessionWithAssetsResponse:
    """Get a single session with all its assets (for frontend polling)."""
    session = await repository.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionWithAssetsResponse.model_validate(session)


@router.patch("/{session_id}/assets/{asset_id}", response_model=AssetResponse)
async def update_asset_status(
    session_id: str,
    asset_id: str,
    body: AssetStatusUpdate,
    db: AsyncSession = Depends(get_db),
) -> AssetResponse:
    """Aktualisiert den Status eines Assets – gibt 404 zurueck wenn nicht gefunden."""
    # Pruefen ob die Sitzung existiert
    session = await repository.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Sitzung nicht gefunden")

    # Asset-Status aktualisieren
    asset = await repository.update_asset_status(db, asset_id=asset_id, status=body.status)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset nicht gefunden")

    return AssetResponse.model_validate(asset)
