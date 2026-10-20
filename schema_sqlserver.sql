/*
    schema_sqlserver.sql
    Migrasi struktur database bank_data_pipeline dari PostgreSQL ke SQL Server.

    Cara pakai:
    1. Buka file ini di SQL Server Management Studio (SSMS).
    2. Pastikan server SQL Server sudah berjalan.
    3. Jalankan seluruh script (F5).

    Catatan migrasi:
    - Script ini membuat database bank_data_pipeline jika belum ada.
    - Script hanya membuat STRUKTUR, bukan memindahkan data dari PostgreSQL.
    - UNIQUE constraint yang duplikat di schema PostgreSQL dirapikan menjadi satu.
    - PostgreSQL boolean -> SQL Server bit.
    - PostgreSQL timestamp with time zone -> datetimeoffset(7).
    - PostgreSQL timestamp without time zone -> datetime2(7).
    - PostgreSQL text -> nvarchar(max), character varying -> nvarchar.
    - Fungsi/trigger PostgreSQL set_updated_at() diterjemahkan menjadi trigger T-SQL.
    - financial_data.value tetap nullable, mengikuti struktur database aktual.
    - Schema aktual tidak memiliki kolom raw_value atau normalized_value; kolom tersebut
      tidak ditambahkan otomatis agar struktur tidak berubah tanpa keputusan eksplisit.
*/

IF DB_ID(N'bank_data_pipeline_test') IS NULL
BEGIN
    CREATE DATABASE [bank_data_pipeline_test];
END;
GO

USE [bank_data_pipeline_test];
GO

/* ================================================================
   1. MASTER TABLES
   ================================================================ */

CREATE TABLE dbo.banks (
    bank_id       int IDENTITY(1,1) NOT NULL,
    bank_name     nvarchar(100) NOT NULL,
    bank_type     nvarchar(20) NOT NULL,
    period_type   nvarchar(20) NOT NULL,
    report_url    nvarchar(max) NULL,
    is_active     bit NOT NULL CONSTRAINT DF_banks_is_active DEFAULT (1),
    created_at    datetimeoffset(7) NOT NULL CONSTRAINT DF_banks_created_at DEFAULT (SYSDATETIMEOFFSET()),
    updated_at    datetimeoffset(7) NOT NULL CONSTRAINT DF_banks_updated_at DEFAULT (SYSDATETIMEOFFSET()),
    CONSTRAINT PK_banks PRIMARY KEY (bank_id),
    CONSTRAINT UQ_banks_bank_name UNIQUE (bank_name),
    CONSTRAINT CK_banks_bank_type CHECK (bank_type IN (N'Konvensional', N'Syariah')),
    CONSTRAINT CK_banks_period_type CHECK (period_type IN (N'Monthly', N'Quarterly'))
);
GO

CREATE TABLE dbo.master_metrics (
    metric_alias  nvarchar(80) NOT NULL,
    category      nvarchar(60) NOT NULL,
    sub_category  nvarchar(80) NOT NULL,
    metric_name   nvarchar(200) NOT NULL,
    metric_order  int NULL,
    created_at    datetimeoffset(7) NOT NULL CONSTRAINT DF_master_metrics_created_at DEFAULT (SYSDATETIMEOFFSET()),
    updated_at    datetimeoffset(7) NOT NULL CONSTRAINT DF_master_metrics_updated_at DEFAULT (SYSDATETIMEOFFSET()),
    CONSTRAINT PK_master_metrics PRIMARY KEY (metric_alias)
);
GO

/* ================================================================
   2. BANK METRIC MAPPING
   ================================================================ */

CREATE TABLE dbo.bank_metric_mapping (
    mapping_id    int IDENTITY(1,1) NOT NULL,
    bank_id       int NOT NULL,
    metric_alias  nvarchar(80) NOT NULL,
    is_applicable bit NOT NULL CONSTRAINT DF_bank_metric_mapping_is_applicable DEFAULT (1),
    local_term    nvarchar(200) NULL,
    created_at    datetimeoffset(7) NOT NULL CONSTRAINT DF_bank_metric_mapping_created_at DEFAULT (SYSDATETIMEOFFSET()),
    updated_at    datetimeoffset(7) NOT NULL CONSTRAINT DF_bank_metric_mapping_updated_at DEFAULT (SYSDATETIMEOFFSET()),
    CONSTRAINT PK_bank_metric_mapping PRIMARY KEY (mapping_id),
    CONSTRAINT UQ_bank_metric_mapping_bank_metric UNIQUE (bank_id, metric_alias),
    CONSTRAINT FK_bank_metric_mapping_banks FOREIGN KEY (bank_id)
        REFERENCES dbo.banks(bank_id) ON DELETE CASCADE,
    CONSTRAINT FK_bank_metric_mapping_master_metrics FOREIGN KEY (metric_alias)
        REFERENCES dbo.master_metrics(metric_alias) ON DELETE CASCADE
);
GO

/* ================================================================
   3. FINANCIAL REPORTS AND DATA
   ================================================================ */

CREATE TABLE dbo.financial_reports (
    report_id     int IDENTITY(1,1) NOT NULL,
    bank_id       int NOT NULL,
    period_date   date NOT NULL,
    period_type   nvarchar(20) NOT NULL,
    source_url    nvarchar(max) NULL,
    file_path     nvarchar(max) NULL,
    file_hash     nvarchar(64) NULL,
    downloaded_at datetimeoffset(7) NULL,
    parsed_at     datetimeoffset(7) NULL,
    status        nvarchar(20) NOT NULL CONSTRAINT DF_financial_reports_status DEFAULT (N'pending'),
    error_message nvarchar(max) NULL,
    created_at    datetimeoffset(7) NOT NULL CONSTRAINT DF_financial_reports_created_at DEFAULT (SYSDATETIMEOFFSET()),
    updated_at    datetimeoffset(7) NOT NULL CONSTRAINT DF_financial_reports_updated_at DEFAULT (SYSDATETIMEOFFSET()),
    CONSTRAINT PK_financial_reports PRIMARY KEY (report_id),
    CONSTRAINT UQ_financial_reports_bank_period UNIQUE (bank_id, period_date),
    CONSTRAINT CK_financial_reports_period_type CHECK (period_type IN (N'Monthly', N'Quarterly')),
    CONSTRAINT CK_financial_reports_status CHECK (status IN (N'pending', N'downloaded', N'parsed', N'failed', N'reviewed')),
    CONSTRAINT FK_financial_reports_banks FOREIGN KEY (bank_id)
        REFERENCES dbo.banks(bank_id) ON DELETE CASCADE
);
GO

CREATE TABLE dbo.financial_data (
    data_id            bigint IDENTITY(1,1) NOT NULL,
    report_id          int NOT NULL,
    bank_id            int NOT NULL,
    period_date        date NOT NULL,
    metric_alias       nvarchar(80) NOT NULL,
    value              decimal(20,2) NULL,
    unit               nvarchar(20) NOT NULL CONSTRAINT DF_financial_data_unit DEFAULT (N'juta rupiah'),
    raw_text           nvarchar(max) NULL,
    is_manual_override bit NOT NULL CONSTRAINT DF_financial_data_is_manual_override DEFAULT (0),
    created_at         datetimeoffset(7) NOT NULL CONSTRAINT DF_financial_data_created_at DEFAULT (SYSDATETIMEOFFSET()),
    updated_at         datetimeoffset(7) NOT NULL CONSTRAINT DF_financial_data_updated_at DEFAULT (SYSDATETIMEOFFSET()),
    sign_type          nchar(1) NULL,
    CONSTRAINT PK_financial_data PRIMARY KEY (data_id),
    CONSTRAINT UQ_financial_data_report_metric UNIQUE (report_id, metric_alias),
    CONSTRAINT CK_financial_data_sign_type CHECK (sign_type IN (N'+', N'-') OR sign_type IS NULL),
    CONSTRAINT FK_financial_data_financial_reports FOREIGN KEY (report_id)
        REFERENCES dbo.financial_reports(report_id) ON DELETE CASCADE,
    CONSTRAINT FK_financial_data_banks FOREIGN KEY (bank_id)
        REFERENCES dbo.banks(bank_id),
    CONSTRAINT FK_financial_data_master_metrics FOREIGN KEY (metric_alias)
        REFERENCES dbo.master_metrics(metric_alias)
);
GO

/* ================================================================
   4. BANK STATEMENT / REKENING KORAN MODULE
   ================================================================ */

CREATE TABLE dbo.bank_accounts (
    account_id    bigint IDENTITY(1,1) NOT NULL,
    bank_id       int NOT NULL,
    account_number nvarchar(50) NOT NULL,
    account_name  nvarchar(200) NULL,
    currency      nvarchar(10) NOT NULL,
    is_active     bit NOT NULL CONSTRAINT DF_bank_accounts_is_active DEFAULT (1),
    created_at    datetime2(7) NOT NULL CONSTRAINT DF_bank_accounts_created_at DEFAULT (SYSDATETIME()),
    updated_at    datetime2(7) NOT NULL CONSTRAINT DF_bank_accounts_updated_at DEFAULT (SYSDATETIME()),
    CONSTRAINT PK_bank_accounts PRIMARY KEY (account_id),
    CONSTRAINT UQ_bank_accounts_bank_account_number UNIQUE (bank_id, account_number),
    CONSTRAINT FK_bank_accounts_banks FOREIGN KEY (bank_id)
        REFERENCES dbo.banks(bank_id)
);
GO

CREATE TABLE dbo.bank_statements (
    statement_id   bigint IDENTITY(1,1) NOT NULL,
    account_id     bigint NOT NULL,
    period_start   date NOT NULL,
    period_end     date NOT NULL,
    currency       nvarchar(10) NOT NULL,
    opening_balance decimal(20,2) NULL,
    closing_balance decimal(20,2) NULL,
    total_credit   decimal(20,2) NULL,
    total_debit    decimal(20,2) NULL,
    credit_count   int NULL,
    debit_count    int NULL,
    total_pages    int NULL,
    source_url     nvarchar(max) NULL,
    file_path      nvarchar(max) NULL,
    file_hash      nvarchar(64) NULL,
    downloaded_at  datetime2(7) NULL,
    parsed_at      datetime2(7) NULL,
    status         nvarchar(50) NOT NULL,
    error_message  nvarchar(max) NULL,
    created_at     datetime2(7) NOT NULL CONSTRAINT DF_bank_statements_created_at DEFAULT (SYSDATETIME()),
    updated_at     datetime2(7) NOT NULL CONSTRAINT DF_bank_statements_updated_at DEFAULT (SYSDATETIME()),
    CONSTRAINT PK_bank_statements PRIMARY KEY (statement_id),
    CONSTRAINT FK_bank_statements_bank_accounts FOREIGN KEY (account_id)
        REFERENCES dbo.bank_accounts(account_id)
);
GO

CREATE TABLE dbo.bank_transactions (
    transaction_id    bigint IDENTITY(1,1) NOT NULL,
    statement_id      bigint NOT NULL,
    transaction_date  date NOT NULL,
    value_date        date NULL,
    page_number       int NULL,
    description       nvarchar(max) NULL,
    branch_code       nvarchar(20) NULL,
    amount            decimal(20,2) NOT NULL,
    transaction_type  nvarchar(30) NOT NULL,
    balance           decimal(20,2) NULL,
    transaction_hash  nvarchar(64) NOT NULL,
    raw_text          nvarchar(max) NULL,
    confidence_score  decimal(5,4) NULL,
    is_manual_override bit NOT NULL CONSTRAINT DF_bank_transactions_is_manual_override DEFAULT (0),
    created_at        datetime2(7) NOT NULL CONSTRAINT DF_bank_transactions_created_at DEFAULT (SYSDATETIME()),
    updated_at        datetime2(7) NOT NULL CONSTRAINT DF_bank_transactions_updated_at DEFAULT (SYSDATETIME()),
    CONSTRAINT PK_bank_transactions PRIMARY KEY (transaction_id),
    CONSTRAINT UQ_bank_transactions_statement_hash UNIQUE (statement_id, transaction_hash),
    CONSTRAINT FK_bank_transactions_bank_statements FOREIGN KEY (statement_id)
        REFERENCES dbo.bank_statements(statement_id)
);
GO

/* ================================================================
   5. PIPELINE RUN LOG
   ================================================================ */

CREATE TABLE dbo.pipeline_run_log (
    run_id            int IDENTITY(1,1) NOT NULL,
    run_type          nvarchar(20) NOT NULL,
    bank_id           int NULL,
    started_at        datetimeoffset(7) NOT NULL CONSTRAINT DF_pipeline_run_log_started_at DEFAULT (SYSDATETIMEOFFSET()),
    finished_at       datetimeoffset(7) NULL,
    status            nvarchar(20) NOT NULL CONSTRAINT DF_pipeline_run_log_status DEFAULT (N'running'),
    records_processed int NULL CONSTRAINT DF_pipeline_run_log_records_processed DEFAULT (0),
    error_log         nvarchar(max) NULL,
    CONSTRAINT PK_pipeline_run_log PRIMARY KEY (run_id),
    CONSTRAINT CK_pipeline_run_log_run_type CHECK (run_type IN (N'scrape', N'parse', N'full')),
    CONSTRAINT CK_pipeline_run_log_status CHECK (status IN (N'running', N'success', N'partial', N'failed')),
    CONSTRAINT FK_pipeline_run_log_banks FOREIGN KEY (bank_id)
        REFERENCES dbo.banks(bank_id)
);
GO

/* ================================================================
   6. INDEXES (equivalent to the indexes in PostgreSQL)
   ================================================================ */

CREATE INDEX idx_bank_metric_mapping_bank ON dbo.bank_metric_mapping(bank_id);
CREATE INDEX idx_bank_metric_mapping_metric ON dbo.bank_metric_mapping(metric_alias);
CREATE INDEX idx_bank_statements_account ON dbo.bank_statements(account_id);
CREATE INDEX idx_bank_transactions_date ON dbo.bank_transactions(transaction_date);
CREATE INDEX idx_bank_transactions_statement ON dbo.bank_transactions(statement_id);
CREATE INDEX idx_financial_data_bank_period ON dbo.financial_data(bank_id, period_date);
CREATE INDEX idx_financial_data_metric ON dbo.financial_data(metric_alias);
CREATE INDEX idx_financial_data_period ON dbo.financial_data(period_date);
CREATE INDEX idx_financial_reports_period ON dbo.financial_reports(period_date);
CREATE INDEX idx_financial_reports_status ON dbo.financial_reports(status);
CREATE INDEX idx_master_metrics_category ON dbo.master_metrics(category, sub_category);
CREATE INDEX idx_pipeline_run_log_started ON dbo.pipeline_run_log(started_at DESC);
GO

/* ================================================================
   7. UPDATED_AT TRIGGERS
   PostgreSQL BEFORE UPDATE triggers translated to SQL Server AFTER UPDATE.
   ================================================================ */

CREATE OR ALTER TRIGGER dbo.trg_banks_updated_at
ON dbo.banks
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    IF TRIGGER_NESTLEVEL() > 1 RETURN;
    UPDATE b
       SET updated_at = SYSDATETIMEOFFSET()
    FROM dbo.banks AS b
    INNER JOIN inserted AS i ON i.bank_id = b.bank_id;
END;
GO

CREATE OR ALTER TRIGGER dbo.trg_master_metrics_updated_at
ON dbo.master_metrics
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    IF TRIGGER_NESTLEVEL() > 1 RETURN;
    UPDATE m
       SET updated_at = SYSDATETIMEOFFSET()
    FROM dbo.master_metrics AS m
    INNER JOIN inserted AS i ON i.metric_alias = m.metric_alias;
END;
GO

CREATE OR ALTER TRIGGER dbo.trg_bank_metric_mapping_updated_at
ON dbo.bank_metric_mapping
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    IF TRIGGER_NESTLEVEL() > 1 RETURN;
    UPDATE m
       SET updated_at = SYSDATETIMEOFFSET()
    FROM dbo.bank_metric_mapping AS m
    INNER JOIN inserted AS i ON i.mapping_id = m.mapping_id;
END;
GO

CREATE OR ALTER TRIGGER dbo.trg_financial_reports_updated_at
ON dbo.financial_reports
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    IF TRIGGER_NESTLEVEL() > 1 RETURN;
    UPDATE r
       SET updated_at = SYSDATETIMEOFFSET()
    FROM dbo.financial_reports AS r
    INNER JOIN inserted AS i ON i.report_id = r.report_id;
END;
GO

CREATE OR ALTER TRIGGER dbo.trg_financial_data_updated_at
ON dbo.financial_data
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    IF TRIGGER_NESTLEVEL() > 1 RETURN;
    UPDATE d
       SET updated_at = SYSDATETIMEOFFSET()
    FROM dbo.financial_data AS d
    INNER JOIN inserted AS i ON i.data_id = d.data_id;
END;
GO

/* ================================================================
   8. VIEW
   ================================================================ */

CREATE OR ALTER VIEW dbo.v_financial_data_summary
AS
SELECT
    fd.data_id,
    b.bank_id,
    b.bank_name,
    b.bank_type,
    fd.period_date,
    mm.category,
    mm.sub_category,
    mm.metric_name,
    fd.metric_alias,
    fd.value,
    fd.sign_type,
    fd.unit,
    fr.status AS report_status,
    fd.is_manual_override
FROM dbo.financial_data AS fd
INNER JOIN dbo.banks AS b
    ON b.bank_id = fd.bank_id
INNER JOIN dbo.master_metrics AS mm
    ON mm.metric_alias = fd.metric_alias
INNER JOIN dbo.financial_reports AS fr
    ON fr.report_id = fd.report_id;
GO

/* ================================================================
   END OF SCHEMA
   ================================================================ */
