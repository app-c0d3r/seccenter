-- PostgreSQL Initialisierungsschema fuer SECCENTER Phase 1
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

-- Aufzaehlungstyp fuer Bearbeitungsstatus eines Assets
CREATE TYPE asset_status AS ENUM (
    'PENDING',
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
