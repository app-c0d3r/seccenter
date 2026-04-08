-- PostgreSQL Initialisierungsschema fuer SECCENTER Phase 2A
-- Erstellt die Datenbankerweiterungen, Typen und Tabellen


-- Tabelle fuer Analyse-Sitzungen
CREATE TABLE sessions (
    id   CHAR(26)     PRIMARY KEY,       -- ULID (26 Zeichen)
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Aufzaehlungstyp fuer Asset-Kategorien
CREATE TYPE asset_type AS ENUM (
    'IP_ADDRESS',
    'DOMAIN',
    'FILE_HASH_MD5',
    'FILE_HASH_SHA1',
    'FILE_HASH_SHA256'
);

-- Aufzaehlungstyp fuer Bearbeitungsstatus eines Assets (vollstaendiger Lifecycle)
CREATE TYPE asset_status AS ENUM (
    'PENDING',
    'INTERNAL',
    'PROCESSING',
    'ENRICHED',
    'CRITICAL',
    'CONFIRMED',
    'IGNORED'
);

-- Tabelle fuer sicherheitsrelevante Assets einer Sitzung
CREATE TABLE assets (
    id         CHAR(26)     PRIMARY KEY,
    session_id CHAR(26)     REFERENCES sessions(id) ON DELETE CASCADE,
    value      TEXT         NOT NULL,
    type       asset_type   NOT NULL,
    status     asset_status DEFAULT 'PENDING',
    created_at TIMESTAMPTZ  DEFAULT NOW()
);

-- Index fuer schnelle Suche nach Sitzungs-ID
CREATE INDEX idx_assets_session ON assets(session_id);

-- DLP: Interne Netzwerke (CIDR-Bloecke)
-- cidr stored as TEXT; format is validated by Pydantic (IPvAnyNetwork) before DB insert
CREATE TABLE internal_networks (
    id         CHAR(26)     PRIMARY KEY,
    cidr       TEXT         NOT NULL,
    label      VARCHAR(255),
    created_at TIMESTAMPTZ  DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_internal_networks_cidr ON internal_networks(cidr);

-- DLP: Interne Domains
CREATE TABLE internal_domains (
    id         CHAR(26)     PRIMARY KEY,
    domain     VARCHAR(255) NOT NULL,
    label      VARCHAR(255),
    created_at TIMESTAMPTZ  DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_internal_domains_domain ON internal_domains(domain);
