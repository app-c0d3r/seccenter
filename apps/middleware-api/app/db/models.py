"""SQLAlchemy ORM-Modelle fuer die Datenbanktabellen."""

import enum

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import ARRAY, CIDR, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Basis-Klasse fuer alle ORM-Modelle."""


class SessionModel(Base):
    """Datenbanktabelle fuer Analyse-Sitzungen."""

    __tablename__ = "sessions"

    # Primaerschluessel als ULID (26 Zeichen)
    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        "created_at",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Beziehung zu Assets (Kaskaden-Loeschung)
    assets: Mapped[list["AssetModel"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class AssetModel(Base):
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
            "INTERNAL",
            "PROCESSING",
            "ENRICHED",
            "CRITICAL",
            "CONFIRMED",
            "IGNORED",
            name="asset_status",
            create_type=False,
        ),
        server_default="PENDING",
        nullable=False,
    )

    created_at: Mapped[DateTime] = mapped_column(
        "created_at",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Threat intelligence results from n8n enrichment pipeline
    enrichment_data: Mapped[dict] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb"), nullable=False
    )

    # Beziehung zur uebergeordneten Sitzung
    session: Mapped["SessionModel"] = relationship(back_populates="assets")

    # Index fuer effiziente Abfragen nach Sitzung
    __table_args__ = (
        Index("idx_assets_session", "session_id"),
    )


class InternalNetworkModel(Base):
    """Database table for internal CIDR blocks (DLP rules)."""

    __tablename__ = "internal_networks"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    cidr: Mapped[str] = mapped_column(CIDR, nullable=False)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        "created_at",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class InternalDomainModel(Base):
    """Database table for internal domains (DLP rules)."""

    __tablename__ = "internal_domains"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        "created_at",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class EnrichmentBatchModel(Base):
    """Database table for enrichment batch tracking."""

    __tablename__ = "enrichment_batches"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    asset_ids: Mapped[list[str]] = mapped_column(ARRAY(String(26)), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), server_default="DISPATCHED", nullable=False
    )
    dispatched_at: Mapped[DateTime] = mapped_column(
        "dispatched_at",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[DateTime | None] = mapped_column(
        "completed_at",
        DateTime(timezone=True),
        nullable=True,
    )
