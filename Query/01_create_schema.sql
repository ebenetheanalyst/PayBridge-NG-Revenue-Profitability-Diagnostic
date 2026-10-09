/* =====================================================================
   PayBridge NG | Revenue & Profitability Diagnostic
   Script 01: Create database, schemas, tables, keys and constraints
   Target: SQL Server 2019 or later (Developer edition is fine)
   Note: all data is synthetic. PayBridge NG is a fictional company.
   Primary keys are supplied by the data generator (no IDENTITY),
   so foreign keys line up exactly when the CSV files are loaded.
   ===================================================================== */

IF DB_ID(N'PayBridgeDB') IS NULL
    CREATE DATABASE PayBridgeDB;
GO
USE PayBridgeDB;
GO

/* ---------- Schemas ---------- */
IF SCHEMA_ID(N'dim')    IS NULL EXEC(N'CREATE SCHEMA dim');
IF SCHEMA_ID(N'fact')   IS NULL EXEC(N'CREATE SCHEMA fact');
IF SCHEMA_ID(N'bridge') IS NULL EXEC(N'CREATE SCHEMA bridge');
GO

/* ---------- Drop in reverse dependency order (safe to re-run) ---------- */
DROP TABLE IF EXISTS fact.Transactions;
DROP TABLE IF EXISTS bridge.MerchantPricing;
DROP TABLE IF EXISTS dim.Terminal;
DROP TABLE IF EXISTS dim.Merchant;
DROP TABLE IF EXISTS dim.CostRate;
DROP TABLE IF EXISTS dim.PricingPlan;
DROP TABLE IF EXISTS dim.ResponseCode;
DROP TABLE IF EXISTS dim.SalesRep;
DROP TABLE IF EXISTS dim.Bank;
DROP TABLE IF EXISTS dim.Channel;
DROP TABLE IF EXISTS dim.Product;
DROP TABLE IF EXISTS dim.Location;
DROP TABLE IF EXISTS dim.[Date];
GO

/* ---------- Dimensions ---------- */
CREATE TABLE dim.[Date] (
    date_key         INT          NOT NULL,  -- YYYYMMDD
    full_date        DATE         NOT NULL,
    [year]           SMALLINT     NOT NULL,
    [quarter]        TINYINT      NOT NULL,
    month_num        TINYINT      NOT NULL,
    month_name       VARCHAR(10)  NOT NULL,
    year_month       CHAR(7)      NOT NULL,  -- e.g. 2025-03
    week_of_year     TINYINT      NOT NULL,
    day_of_week      TINYINT      NOT NULL,  -- 1 = Monday
    is_weekend       BIT          NOT NULL,
    is_month_end     BIT          NOT NULL,
    is_public_holiday BIT         NOT NULL,
    holiday_name     VARCHAR(60)  NULL,
    is_peak_season   BIT          NOT NULL,
    fiscal_year      SMALLINT     NOT NULL,
    fiscal_quarter   TINYINT      NOT NULL,
    same_date_py     DATE         NULL,      -- same date in prior year
    CONSTRAINT PK_Date PRIMARY KEY (date_key),
    CONSTRAINT UQ_Date_full_date UNIQUE (full_date)
);

CREATE TABLE dim.Location (
    location_key      INT           NOT NULL,
    city              VARCHAR(60)   NOT NULL,
    [state]           VARCHAR(60)   NOT NULL,
    geopolitical_zone VARCHAR(20)   NOT NULL,
    latitude          DECIMAL(9,6)  NOT NULL,
    longitude         DECIMAL(9,6)  NOT NULL,
    market_type       VARCHAR(12)   NOT NULL,
    launch_date       DATE          NOT NULL,
    CONSTRAINT PK_Location PRIMARY KEY (location_key),
    CONSTRAINT CK_Location_market CHECK (market_type IN ('Core','Growth','New market'))
);

CREATE TABLE dim.Product (
    product_id          INT          NOT NULL,
    product_name        VARCHAR(60)  NOT NULL,
    product_category    VARCHAR(20)  NOT NULL,
    product_launch_date DATE         NOT NULL,
    CONSTRAINT PK_Product PRIMARY KEY (product_id),
    CONSTRAINT CK_Product_category CHECK (product_category IN ('Acquiring','Transfers','Payments','Value-added'))
);

CREATE TABLE dim.Channel (
    channel_id   INT          NOT NULL,
    channel_name VARCHAR(30)  NOT NULL,
    channel_type VARCHAR(10)  NOT NULL,
    CONSTRAINT PK_Channel PRIMARY KEY (channel_id),
    CONSTRAINT CK_Channel_type CHECK (channel_type IN ('Physical','Digital'))
);

CREATE TABLE dim.Bank (
    issuer_bank_id INT          NOT NULL,
    bank_name      VARCHAR(60)  NOT NULL,
    bank_type      VARCHAR(15)  NOT NULL,
    CONSTRAINT PK_Bank PRIMARY KEY (issuer_bank_id),
    CONSTRAINT CK_Bank_type CHECK (bank_type IN ('Commercial','Microfinance','Fintech'))
);

CREATE TABLE dim.SalesRep (
    sales_rep_id VARCHAR(10)  NOT NULL,
    rep_name     VARCHAR(60)  NOT NULL,
    team         VARCHAR(30)  NOT NULL,
    region       VARCHAR(30)  NOT NULL,
    CONSTRAINT PK_SalesRep PRIMARY KEY (sales_rep_id)
);

CREATE TABLE dim.ResponseCode (
    response_code    VARCHAR(4)    NOT NULL,
    [description]    VARCHAR(100)  NOT NULL,
    failure_category VARCHAR(15)   NOT NULL,   -- 'None' for approved
    is_platform_fault BIT          NOT NULL,
    is_retryable     BIT           NOT NULL,
    CONSTRAINT PK_ResponseCode PRIMARY KEY (response_code),
    CONSTRAINT CK_ResponseCode_cat CHECK (failure_category IN ('None','Customer','Issuer bank','Network','Platform','Fraud'))
);

CREATE TABLE dim.PricingPlan (
    plan_id               INT           NOT NULL,
    plan_name             VARCHAR(50)   NOT NULL,
    fee_model             VARCHAR(12)   NOT NULL,
    fee_pct               DECIMAL(7,5)  NULL,
    flat_fee_ngn          DECIMAL(12,2) NULL,
    fee_cap_ngn           DECIMAL(12,2) NULL,
    standard_discount_pct DECIMAL(5,2)  NOT NULL DEFAULT 0,
    CONSTRAINT PK_PricingPlan PRIMARY KEY (plan_id),
    CONSTRAINT CK_PricingPlan_model CHECK (fee_model IN ('Percentage','Flat','Hybrid','Tiered'))
);

CREATE TABLE dim.CostRate (
    cost_rate_id   INT           NOT NULL,
    cost_type      VARCHAR(15)   NOT NULL,
    channel_id     INT           NOT NULL,
    product_id     INT           NOT NULL,
    rate_pct       DECIMAL(7,5)  NULL,
    flat_cost_ngn  DECIMAL(12,2) NULL,
    cost_cap_ngn   DECIMAL(12,2) NULL,
    effective_from DATE          NOT NULL,
    effective_to   DATE          NULL,          -- NULL = still current
    CONSTRAINT PK_CostRate PRIMARY KEY (cost_rate_id),
    CONSTRAINT FK_CostRate_Channel FOREIGN KEY (channel_id) REFERENCES dim.Channel(channel_id),
    CONSTRAINT FK_CostRate_Product FOREIGN KEY (product_id) REFERENCES dim.Product(product_id),
    CONSTRAINT CK_CostRate_type CHECK (cost_type IN ('Processing','Switching','Bank charge','Scheme'))
);

CREATE TABLE dim.Merchant (
    merchant_id         VARCHAR(10)  NOT NULL,
    merchant_name       VARCHAR(100) NOT NULL,
    merchant_segment    VARCHAR(12)  NOT NULL,
    industry            VARCHAR(40)  NOT NULL,
    is_key_account      BIT          NOT NULL DEFAULT 0,
    onboarding_date     DATE         NOT NULL,
    acquisition_channel VARCHAR(20)  NOT NULL,
    home_location_key   INT          NOT NULL,
    sales_rep_id        VARCHAR(10)  NOT NULL,
    merchant_status     VARCHAR(10)  NOT NULL,
    churn_date          DATE         NULL,
    CONSTRAINT PK_Merchant PRIMARY KEY (merchant_id),
    CONSTRAINT FK_Merchant_Location FOREIGN KEY (home_location_key) REFERENCES dim.Location(location_key),
    CONSTRAINT FK_Merchant_SalesRep FOREIGN KEY (sales_rep_id) REFERENCES dim.SalesRep(sales_rep_id),
    CONSTRAINT CK_Merchant_segment CHECK (merchant_segment IN ('Micro','SME','Mid-market','Enterprise')),
    CONSTRAINT CK_Merchant_status  CHECK (merchant_status IN ('Active','Dormant','Churned')),
    CONSTRAINT CK_Merchant_churn   CHECK (churn_date IS NULL OR churn_date >= onboarding_date)
);

CREATE TABLE dim.Terminal (
    terminal_id               VARCHAR(12)   NOT NULL,
    merchant_id               VARCHAR(10)   NOT NULL,
    terminal_type             VARCHAR(15)   NOT NULL,
    deployment_date           DATE          NOT NULL,
    terminal_status           VARCHAR(10)   NOT NULL,
    monthly_terminal_cost_ngn DECIMAL(12,2) NOT NULL,
    CONSTRAINT PK_Terminal PRIMARY KEY (terminal_id),
    CONSTRAINT FK_Terminal_Merchant FOREIGN KEY (merchant_id) REFERENCES dim.Merchant(merchant_id),
    CONSTRAINT CK_Terminal_status CHECK (terminal_status IN ('Active','Idle','Retired'))
);

/* ---------- Bridge ---------- */
CREATE TABLE bridge.MerchantPricing (
    merchant_id    VARCHAR(10) NOT NULL,
    plan_id        INT         NOT NULL,
    effective_from DATE        NOT NULL,
    effective_to   DATE        NULL,           -- NULL = current plan
    CONSTRAINT PK_MerchantPricing PRIMARY KEY (merchant_id, effective_from),
    CONSTRAINT FK_MerchantPricing_Merchant FOREIGN KEY (merchant_id) REFERENCES dim.Merchant(merchant_id),
    CONSTRAINT FK_MerchantPricing_Plan FOREIGN KEY (plan_id) REFERENCES dim.PricingPlan(plan_id),
    CONSTRAINT CK_MerchantPricing_dates CHECK (effective_to IS NULL OR effective_to >= effective_from)
);

/* ---------- Fact ---------- */
CREATE TABLE fact.Transactions (
    transaction_id         VARCHAR(20)   NOT NULL,
    transaction_ts         DATETIME2(0)  NOT NULL,
    date_key               INT           NOT NULL,
    txn_hour               TINYINT       NOT NULL,
    merchant_id            VARCHAR(10)   NOT NULL,
    terminal_id            VARCHAR(12)   NULL,      -- NULL for non-POS channels
    location_key           INT           NOT NULL,
    product_id             INT           NOT NULL,
    channel_id             INT           NOT NULL,
    issuer_bank_id         INT           NOT NULL,
    plan_id                INT           NOT NULL,
    response_code          VARCHAR(4)    NOT NULL,
    txn_status             VARCHAR(10)   NOT NULL,
    transaction_amount_ngn DECIMAL(18,2) NOT NULL,
    list_fee_ngn           DECIMAL(12,2) NOT NULL,
    discount_ngn           DECIMAL(12,2) NOT NULL DEFAULT 0,
    fee_charged_ngn        DECIMAL(12,2) NOT NULL,  -- 0 for failed transactions
    processing_cost_ngn    DECIMAL(12,2) NOT NULL,
    switching_cost_ngn     DECIMAL(12,2) NOT NULL,
    bank_charge_ngn        DECIMAL(12,2) NOT NULL,
    other_cost_ngn         DECIMAL(12,2) NOT NULL,
    is_retry               BIT           NOT NULL DEFAULT 0,
    original_txn_id        VARCHAR(20)   NULL,      -- first attempt, if a retry (not an FK, to allow bulk load)
    settlement_date_key    INT           NULL,
    CONSTRAINT PK_Transactions PRIMARY KEY (transaction_id),
    CONSTRAINT FK_Txn_Date       FOREIGN KEY (date_key)            REFERENCES dim.[Date](date_key),
    CONSTRAINT FK_Txn_Settlement FOREIGN KEY (settlement_date_key) REFERENCES dim.[Date](date_key),
    CONSTRAINT FK_Txn_Merchant   FOREIGN KEY (merchant_id)         REFERENCES dim.Merchant(merchant_id),
    CONSTRAINT FK_Txn_Terminal   FOREIGN KEY (terminal_id)         REFERENCES dim.Terminal(terminal_id),
    CONSTRAINT FK_Txn_Location   FOREIGN KEY (location_key)        REFERENCES dim.Location(location_key),
    CONSTRAINT FK_Txn_Product    FOREIGN KEY (product_id)          REFERENCES dim.Product(product_id),
    CONSTRAINT FK_Txn_Channel    FOREIGN KEY (channel_id)          REFERENCES dim.Channel(channel_id),
    CONSTRAINT FK_Txn_Bank       FOREIGN KEY (issuer_bank_id)      REFERENCES dim.Bank(issuer_bank_id),
    CONSTRAINT FK_Txn_Plan       FOREIGN KEY (plan_id)             REFERENCES dim.PricingPlan(plan_id),
    CONSTRAINT FK_Txn_Response   FOREIGN KEY (response_code)       REFERENCES dim.ResponseCode(response_code),
    CONSTRAINT CK_Txn_status   CHECK (txn_status IN ('Success','Failed','Reversed')),
    CONSTRAINT CK_Txn_hour     CHECK (txn_hour BETWEEN 0 AND 23),
    CONSTRAINT CK_Txn_amount   CHECK (transaction_amount_ngn > 0),
    CONSTRAINT CK_Txn_fees     CHECK (list_fee_ngn >= 0 AND discount_ngn >= 0 AND discount_ngn <= list_fee_ngn AND fee_charged_ngn >= 0),
    CONSTRAINT CK_Txn_costs    CHECK (processing_cost_ngn >= 0 AND switching_cost_ngn >= 0 AND bank_charge_ngn >= 0 AND other_cost_ngn >= 0)
);
GO

/* ---------- Indexes: run AFTER the data has been loaded (faster bulk load) ---------- */
-- CREATE NONCLUSTERED INDEX IX_Txn_date     ON fact.Transactions (date_key)    INCLUDE (fee_charged_ngn, transaction_amount_ngn);
-- CREATE NONCLUSTERED INDEX IX_Txn_merchant ON fact.Transactions (merchant_id) INCLUDE (date_key, fee_charged_ngn);
-- CREATE NONCLUSTERED INDEX IX_Txn_channel  ON fact.Transactions (channel_id, product_id);
-- CREATE NONCLUSTERED INDEX IX_Txn_location ON fact.Transactions (location_key);
-- CREATE NONCLUSTERED INDEX IX_Txn_status   ON fact.Transactions (txn_status, response_code);
GO