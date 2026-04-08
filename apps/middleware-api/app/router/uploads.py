"""FastAPI-Router fuer Datei-Upload-Endpunkte."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.connection import get_db
from app.db import repository
from app.schemas.asset import UploadResponse
from app.services.ioc_extractor import extract_iocs

# Router teilt den Praefix mit dem Sessions-Router
router = APIRouter(prefix="/api/sessions", tags=["uploads"])


@router.post("/{session_id}/upload", response_model=UploadResponse, status_code=201)
async def upload_file(
    session_id: str,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
) -> UploadResponse:
    """
    Laedt eine Textdatei hoch und extrahiert IOCs daraus.

    Schritte:
    1. Sitzung pruefen (404 wenn nicht vorhanden)
    2. Dateiinhalt lesen, Groesse pruefen (413 wenn zu gross)
    3. UTF-8 dekodieren und IOCs extrahieren
    4. Assets anlegen und Antwort zurueckgeben
    """
    # Schritt 1: Pruefen ob die Sitzung existiert
    session = await repository.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Sitzung nicht gefunden")

    # Schritt 2: Dateiinhalt lesen und Groesse pruefen
    content_bytes = await file.read()
    if len(content_bytes) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Datei zu gross – Maximum ist {settings.max_upload_bytes} Bytes",
        )

    # Schritt 3: UTF-8 dekodieren und IOCs extrahieren
    text = content_bytes.decode("utf-8", errors="replace")
    iocs = extract_iocs(text)

    # Schritt 4: Assets in der Datenbank anlegen (leer wenn keine IOCs gefunden)
    if iocs:
        assets = await repository.create_assets(db, session_id=session_id, assets=iocs)
    else:
        assets = []

    # Antwort mit allen erstellten Assets zusammenstellen
    from app.schemas.asset import AssetResponse
    return UploadResponse(
        assets=[AssetResponse.model_validate(a) for a in assets]
    )
