-- ============================================================================
-- Schema: Bank Financial Statement Data Pipeline
-- Project: BCA Syariah - Competitor Financial Data Recap (MIS Internship)
-- Target : PostgreSQL 14+
--
-- Design notes
-- - Sesuai struktur Excel: Banks, Bank Mapping, Master Metric
-- - master_metrics       -> sheet "Master Metric" (kamus utama)
-- - bank_metric_mapping  -> sheet "Bank Mapping" (True/False/istilah lokal per bank)
--   Catatan: tabel metric_parsing_aliases yang ada di desain awal DIHAPUS dari
--   versi ini -- setelah parser.py benar-benar diimplementasikan & diuji ke
--   PDF asli, ternyata bank_metric_mapping.local_term sudah cukup jadi kamus
--   lookup-nya, tabel terpisah itu jadi redundant.
-- - financial_reports & financial_data -> hasil pipeline (fact tables)
-- - pipeline_run_log     -> monitoring job bulanan
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. BANKS  (sheet: Banks)
-- ----------------------------------------------------------------------------
CREATE TABLE banks (
    bank_id         SERIAL PRIMARY KEY,
    bank_name       VARCHAR(100) NOT NULL UNIQUE,
    bank_type       VARCHAR(20)  NOT NULL CHECK (bank_type IN ('Konvensional', 'Syariah')),
    period_type     VARCHAR(20)  NOT NULL CHECK (period_type IN ('Monthly', 'Quarterly')),
    report_url      TEXT,
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

COMMENT ON TABLE banks IS 'Master data bank (kompetitor) beserta sumber laporan keuangannya';

-- ----------------------------------------------------------------------------
-- 2. MASTER_METRICS  (sheet: Master Metric)
-- ----------------------------------------------------------------------------
CREATE TABLE master_metrics (
    metric_alias    VARCHAR(80) PRIMARY KEY,      -- e.g. 'cash', 'placement_bank_indonesia'
    category        VARCHAR(60) NOT NULL,          -- e.g. 'Assets', 'Liabilities', 'Equity'
    sub_category    VARCHAR(80) NOT NULL,          -- e.g. 'Cash', 'Placements'
    nama_akun       VARCHAR(200) NOT NULL,         -- nama akun standar (Bahasa Indonesia)
    metric_order    INT,                           -- urutan tampilan di laporan standar
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE master_metrics IS 'Kamus utama metrik/akun laporan keuangan yang distandardisasi';

CREATE INDEX idx_master_metrics_category ON master_metrics (category, sub_category);

-- ----------------------------------------------------------------------------
-- 3. BANK_METRIC_MAPPING  (sheet: Bank Mapping)
-- Tabel ini yang dipakai LANGSUNG oleh parser.py sebagai kamus lookup:
-- COALESCE(local_term, nama_akun standar) = istilah yang dicari di PDF.
-- ----------------------------------------------------------------------------
CREATE TABLE bank_metric_mapping (
    mapping_id      SERIAL PRIMARY KEY,
    bank_id         INT NOT NULL REFERENCES banks (bank_id) ON DELETE CASCADE,
    metric_alias    VARCHAR(80) NOT NULL REFERENCES master_metrics (metric_alias) ON DELETE CASCADE,
    is_applicable   BOOLEAN NOT NULL DEFAULT TRUE,   -- FALSE jika bank tsb tidak punya akun ini ('-' di Excel)
    local_term      VARCHAR(200),                    -- istilah literal bank tsb jika beda dari nama_akun standar
                                                       -- NULL/kosong = pakai istilah standar apa adanya (True di Excel)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (bank_id, metric_alias)
);

COMMENT ON TABLE bank_metric_mapping IS 'Menentukan apakah suatu metrik berlaku utk bank tertentu, dan istilah lokal yg dipakai -- ini kamus lookup utama parser';

CREATE INDEX idx_bank_metric_mapping_bank ON bank_metric_mapping (bank_id);
CREATE INDEX idx_bank_metric_mapping_metric ON bank_metric_mapping (metric_alias);

-- ----------------------------------------------------------------------------
-- 4. FINANCIAL_REPORTS  (tracking dokumen sumber per bank per periode)
-- ----------------------------------------------------------------------------
CREATE TABLE financial_reports (
    report_id       SERIAL PRIMARY KEY,
    bank_id         INT NOT NULL REFERENCES banks (bank_id) ON DELETE CASCADE,
    period_date     DATE NOT NULL,                   -- tanggal akhir periode laporan, mis. 2026-06-30
    period_type     VARCHAR(20) NOT NULL CHECK (period_type IN ('Monthly', 'Quarterly')),
    source_url      TEXT,
    file_path       TEXT,                            -- lokasi PDF tersimpan (local/S3/etc)
    file_hash       VARCHAR(64),                      -- SHA-256, utk deteksi duplikat/perubahan file
    downloaded_at   TIMESTAMPTZ,
    parsed_at       TIMESTAMPTZ,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'downloaded', 'parsed', 'failed', 'reviewed')),
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (bank_id, period_date)
);

COMMENT ON TABLE financial_reports IS 'Satu baris per dokumen laporan keuangan (bank x periode) yang diproses pipeline';

CREATE INDEX idx_financial_reports_status ON financial_reports (status);
CREATE INDEX idx_financial_reports_period ON financial_reports (period_date);

-- ----------------------------------------------------------------------------
-- 5. FINANCIAL_DATA  (fact table - angka hasil extract)
-- bank_id & period_date didenormalisasi dari financial_reports untuk
-- mempercepat query rekap lintas bank/periode (use case utama tim MIS).
-- ----------------------------------------------------------------------------
CREATE TABLE financial_data (
    data_id             BIGSERIAL PRIMARY KEY,
    report_id           INT NOT NULL REFERENCES financial_reports (report_id) ON DELETE CASCADE,
    bank_id             INT NOT NULL REFERENCES banks (bank_id),
    period_date         DATE NOT NULL,
    metric_alias        VARCHAR(80) NOT NULL REFERENCES master_metrics (metric_alias),
    value               NUMERIC(20, 2) NOT NULL,
    unit                VARCHAR(20) NOT NULL DEFAULT 'juta rupiah',
    raw_text            TEXT,                         -- baris/teks asli dari PDF (audit trail)
    confidence_score    NUMERIC(4, 3),                 -- opsional, jika parser pakai fuzzy/OCR matching
    is_manual_override  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (report_id, metric_alias)
);

COMMENT ON TABLE financial_data IS 'Fact table: nilai tiap metrik per bank per periode hasil ekstraksi PDF';

CREATE INDEX idx_financial_data_bank_period ON financial_data (bank_id, period_date);
CREATE INDEX idx_financial_data_metric ON financial_data (metric_alias);
CREATE INDEX idx_financial_data_period ON financial_data (period_date);

-- ----------------------------------------------------------------------------
-- 6. PIPELINE_RUN_LOG  (monitoring eksekusi job otomatis)
-- ----------------------------------------------------------------------------
CREATE TABLE pipeline_run_log (
    run_id              SERIAL PRIMARY KEY,
    run_type            VARCHAR(20) NOT NULL CHECK (run_type IN ('scrape', 'parse', 'full')),
    bank_id             INT REFERENCES banks (bank_id),   -- NULL = menjalankan semua bank
    started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at         TIMESTAMPTZ,
    status              VARCHAR(20) NOT NULL DEFAULT 'running'
                            CHECK (status IN ('running', 'success', 'partial', 'failed')),
    records_processed   INT DEFAULT 0,
    error_log           TEXT
);

COMMENT ON TABLE pipeline_run_log IS 'Log tiap eksekusi pipeline (scheduler bulanan) utk monitoring & debugging';

CREATE INDEX idx_pipeline_run_log_started ON pipeline_run_log (started_at DESC);

-- ----------------------------------------------------------------------------
-- VIEW: rekap laporan keuangan siap pakai (join semua master data)
-- ----------------------------------------------------------------------------
CREATE VIEW v_financial_data_summary AS
SELECT
    fd.data_id,
    b.bank_id,
    b.bank_name,
    b.bank_type,
    fd.period_date,
    mm.category,
    mm.sub_category,
    mm.nama_akun,
    fd.metric_alias,
    fd.value,
    fd.unit,
    fr.status AS report_status,
    fd.is_manual_override
FROM financial_data fd
JOIN banks b            ON b.bank_id = fd.bank_id
JOIN master_metrics mm  ON mm.metric_alias = fd.metric_alias
JOIN financial_reports fr ON fr.report_id = fd.report_id;

COMMENT ON VIEW v_financial_data_summary IS 'View siap pakai untuk rekap/dashboard: 1 baris = 1 metrik, 1 bank, 1 periode';

-- ----------------------------------------------------------------------------
-- Trigger sederhana: auto-update updated_at
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_banks_updated_at BEFORE UPDATE ON banks
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_master_metrics_updated_at BEFORE UPDATE ON master_metrics
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_bank_metric_mapping_updated_at BEFORE UPDATE ON bank_metric_mapping
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_financial_reports_updated_at BEFORE UPDATE ON financial_reports
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_financial_data_updated_at BEFORE UPDATE ON financial_data
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMIT;

-- ============================================================================
-- Contoh query rekap (setelah data terisi)
-- ============================================================================
-- 1. Bandingkan Total Assets semua bank untuk periode terakhir:
--
-- SELECT bank_name, bank_type, value AS total_assets
-- FROM v_financial_data_summary
-- WHERE metric_alias = 'total_assets'
--   AND period_date = (SELECT MAX(period_date) FROM financial_data)
-- ORDER BY value DESC;
--
-- 2. Tren satu metrik untuk satu bank sepanjang waktu:
--
-- SELECT period_date, value
-- FROM v_financial_data_summary
-- WHERE bank_name = 'BSI' AND metric_alias = 'cash'
-- ORDER BY period_date;
-- ============================================================================
