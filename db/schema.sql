CREATE TABLE IF NOT EXISTS wilayah (
    kode varchar(20) PRIMARY KEY,
    nama text NOT NULL
);

CREATE INDEX IF NOT EXISTS wilayah_nama_idx ON wilayah (nama);

CREATE TABLE IF NOT EXISTS wilayah_profil (
    kode        varchar(13) PRIMARY KEY,
    nama        text,
    ibukota     text,
    lat         double precision,
    lng         double precision,
    elv         double precision,
    tz          smallint,
    luas        double precision,
    penduduk    double precision,
    bbox_west   double precision,
    bbox_south  double precision,
    bbox_east   double precision,
    bbox_north  double precision
);

CREATE TABLE IF NOT EXISTS flood_reports (
    id                    text PRIMARY KEY,
    kab_kode              varchar(13) NOT NULL,
    desa_kode             varchar(13) NOT NULL,
    desa_name             text NOT NULL DEFAULT '',
    kecamatan_kode        varchar(13) NOT NULL DEFAULT '',
    kecamatan             text NOT NULL DEFAULT '',
    flood_level           text NOT NULL,
    boost_score           double precision NOT NULL DEFAULT 0,
    boost_breakdown       jsonb NOT NULL DEFAULT '{}'::jsonb,
    reporter              text NOT NULL DEFAULT '',
    notes                 text NOT NULL DEFAULT '',
    reported_at           timestamptz NOT NULL,
    base_score_at_report  double precision
);

CREATE INDEX IF NOT EXISTS flood_reports_kab_time_idx
    ON flood_reports (kab_kode, reported_at DESC);

CREATE TABLE IF NOT EXISTS inarisk_baselines (
    kab_kode       varchar(13) PRIMARY KEY,
    features_json  jsonb NOT NULL,
    base_score     double precision NOT NULL,
    polygons_json  jsonb,
    fetched_at     timestamptz NOT NULL,
    source         text NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS inarisk_baselines_fetched_idx
    ON inarisk_baselines (fetched_at);

CREATE TABLE IF NOT EXISTS weather_cache (
    kab_kode      varchar(13) PRIMARY KEY,
    payload_json  jsonb NOT NULL,
    fetched_at    timestamptz NOT NULL
);
