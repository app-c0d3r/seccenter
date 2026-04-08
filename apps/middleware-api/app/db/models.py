"""SQLAlchemy ORM-Modelle fuer die Datenbanktabellen."""

import enum

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Basis(DeclarativeBase):
    """Basis-Klasse fuer alle ORM-Modelle."""


class SitzungsModell(Basis):
    """Datenbanktabelle fuer Analyse-Sitzungen."""

    __tablename__ = "sessions"

    # Primaerschluessel als ULID (26 Zeichen)
    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    erstellt_am: Mapped[DateTime] = mapped_column(
        "created_at",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Beziehung zu Assets (Kaskaden-Loeschung)
    assets: Mapped[list["AssetModell"]] = relationship(
        back_populates="sitzung", cascade="all, delete-orphan"
    )


class AssetModell(Basis):
    """Datenbanktabelle fuer gefundene Assets (IPs, Domains, Hashes)."""

    __tablename__ = "assets"

    # Primaerschluessel als ULID
    id: Mapped[str] = mapped_column(String(26), primary_key=True)

    # Fremdschluessel zur Sitzung mit Kaskaden-Loeschung
    session_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )

    value: Mapped[str] = mapped_column(String, nullable=False)

    # Asset-Typ (Enum aus DB-Sicht ohne automatische Typ-Erstellung)
    type: Mapped[str] = mapped_column(
        Enum(
            "IP_ADDRESS",
            "DOMAIN",
            "FILE_HASH_MD5",
            "FILE_HASH_SHA1",
            "FILE_HASH_SHA256",
            name="asset_type",
            create_type=False,
        ),
        nullable=False,
    )

    # Verarbeitungsstatus
    status: Mapped[str] = mapped_column(
        Enum(
            "PENDING",
            "CONFIRMED",
            "IGNORED",
            name="asset_status",
            create_type=False,
        ),
        server_default="PENDING",
        nullable=False,
    )

    erstellt_am: Mapped[DateTime] = mapped_column(
        "created_at",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Beziehung zur uebergeordneten Sitzung
    sitzung: Mapped["SitzungsModell"] = relationship(back_populates="assets")

    # Index fuer effiziente Abfragen nach Sitzung
    __table_args__ = (
        Index("idx_assets_session", "session_id"),
    )
