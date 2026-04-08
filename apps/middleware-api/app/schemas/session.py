"""Pydantic-Schemas fuer Sitzungs-Objekte."""

from datetime import datetime

from pydantic import BaseModel


class SessionCreate(BaseModel):
    """Anfrage-Schema fuer das Anlegen einer neuen Sitzung."""

    name: str


class SessionResponse(BaseModel):
    """Antwort-Schema fuer eine Sitzung."""

    id: str
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}
