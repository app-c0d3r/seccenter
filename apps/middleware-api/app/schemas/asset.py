"""Pydantic-Schemas fuer Asset-Objekte."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class AssetTyp(str, Enum):
    """Moegliche Asset-Typen im Security Cockpit."""

    IP_ADDRESS = "IP_ADDRESS"
    DOMAIN = "DOMAIN"
    FILE_HASH_MD5 = "FILE_HASH_MD5"
    FILE_HASH_SHA1 = "FILE_HASH_SHA1"
    FILE_HASH_SHA256 = "FILE_HASH_SHA256"


# Alias fuer englische Kompatibilitaet
AssetType = AssetTyp


class AssetStatus(str, Enum):
    """Moegliche Verarbeitungszustaende eines Assets."""

    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    IGNORED = "IGNORED"


class AssetAntwort(BaseModel):
    """Antwort-Schema fuer ein einzelnes Asset."""

    id: str
    session_id: str
    value: str
    type: AssetTyp
    status: AssetStatus
    created_at: datetime

    model_config = {"from_attributes": True}


# Alias
AssetResponse = AssetAntwort


class AssetStatusAktualisierung(BaseModel):
    """Anfrage-Schema fuer Status-Aenderung eines Assets."""

    status: AssetStatus


# Alias
AssetStatusUpdate = AssetStatusAktualisierung


class UploadAntwort(BaseModel):
    """Antwort-Schema nach einem Datei-Upload."""

    assets: list[AssetAntwort]


# Alias
UploadResponse = UploadAntwort
