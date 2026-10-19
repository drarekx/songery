-- Esquema de la base de dades de Cançoners v1.0.0 (PRAGMA user_version = 0), sense dades.
-- Per als tests d'actualització: tests/test_actualitzacio_dades.py
CREATE TABLE canco (
    id TEXT PRIMARY KEY,
    titol TEXT NOT NULL DEFAULT '',
    autor TEXT NOT NULL DEFAULT '',
    doc TEXT NOT NULL,
    creada TEXT NOT NULL,
    actualitzada TEXT NOT NULL
, tipus TEXT NOT NULL DEFAULT 'canco');
CREATE TABLE versio (
    id TEXT PRIMARY KEY,
    canco_id TEXT NOT NULL REFERENCES canco(id) ON DELETE CASCADE,
    numero INTEGER NOT NULL,
    titol TEXT NOT NULL,
    autor TEXT NOT NULL,
    doc TEXT NOT NULL,
    nota TEXT NOT NULL DEFAULT '',
    creada TEXT NOT NULL,
    UNIQUE (canco_id, numero)
);
CREATE TABLE canconer (
    id TEXT PRIMARY KEY,
    dades TEXT NOT NULL,
    creat TEXT NOT NULL,
    actualitzat TEXT NOT NULL
);
CREATE TABLE entrada (
    canconer_id TEXT NOT NULL REFERENCES canconer(id) ON DELETE CASCADE,
    canco_id TEXT NOT NULL REFERENCES canco(id) ON DELETE CASCADE,
    posicio INTEGER NOT NULL,
    versio_id TEXT REFERENCES versio(id) ON DELETE SET NULL,
    inclosa INTEGER NOT NULL DEFAULT 1,
    transport INTEGER NOT NULL DEFAULT 0, inici TEXT NOT NULL DEFAULT 'esquerra',
    PRIMARY KEY (canconer_id, canco_id)
);
CREATE TABLE imatge (
    id TEXT PRIMARY KEY,
    fitxer TEXT NOT NULL,
    tipus TEXT NOT NULL,
    nom TEXT NOT NULL DEFAULT '',
    creada TEXT NOT NULL
);
CREATE INDEX idx_versio_canco ON versio (canco_id, numero);
CREATE INDEX idx_entrada_canco ON entrada (canco_id);
CREATE TABLE element (
    id TEXT PRIMARY KEY,
    nom TEXT NOT NULL,
    dades TEXT NOT NULL,
    creat TEXT NOT NULL
);
CREATE TABLE tipografia (
    id TEXT PRIMARY KEY,
    nom TEXT NOT NULL,
    fitxer TEXT NOT NULL,
    format TEXT NOT NULL,
    pes INTEGER NOT NULL DEFAULT 400,
    estil TEXT NOT NULL DEFAULT 'normal',
    creada TEXT NOT NULL
);
CREATE TABLE marge (
    id TEXT PRIMARY KEY,
    dades TEXT NOT NULL,
    creat TEXT NOT NULL
);
