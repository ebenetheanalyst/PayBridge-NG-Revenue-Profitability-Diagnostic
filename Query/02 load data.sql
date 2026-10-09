/* =====================================================================
   PayBridge NG | Revenue & Profitability Diagnostic
   Script 02: Load the CSV files into PayBridgeDB and validate the load
   Run AFTER 01_create_schema.sql, in SSMS.

   BEFORE YOU RUN:
   1. Copy all 13 CSV files from your generator "output" folder to a simple
      folder such as C:\PayBridgeData\  (SQL Server's service account often
      cannot read files on your Desktop, which causes "Access denied" errors).
   2. If you used a different folder, change @path below. Keep the final backslash.
   ===================================================================== */

USE PayBridgeDB;
GO
SET NOCOUNT ON;

DECLARE @path NVARCHAR(260) = 'C:\Users\Ebenezer\Desktop\Project Folder\PayBridge\output\';

/* ---------- Step 1: empty the tables (safe to re-run; children first) ---------- */
DROP INDEX IF EXISTS IX_Txn_date     ON fact.Transactions;
DROP INDEX IF EXISTS IX_Txn_merchant ON fact.Transactions;
DROP INDEX IF EXISTS IX_Txn_channel  ON fact.Transactions;
DROP INDEX IF EXISTS IX_Txn_location ON fact.Transactions;
DROP INDEX IF EXISTS IX_Txn_status   ON fact.Transactions;
DELETE FROM fact.Transactions;
DELETE FROM bridge.MerchantPricing;
DELETE FROM dim.Terminal;
DELETE FROM dim.Merchant;
DELETE FROM dim.CostRate;
DELETE FROM dim.PricingPlan;
DELETE FROM dim.ResponseCode;
DELETE FROM dim.SalesRep;
DELETE FROM dim.Bank;
DELETE FROM dim.Channel;
DELETE FROM dim.Product;
DELETE FROM dim.Location;
DELETE FROM dim.[Date];

/* ---------- Step 2: load in dependency order (parents before children) ---------- */
DECLARE @tables TABLE (ord INT, tbl NVARCHAR(100), file_name NVARCHAR(100));
INSERT INTO @tables (ord, tbl, file_name) VALUES
 (1,  N'dim.[Date]',             N'dim_Date.csv'),
 (2,  N'dim.Location',           N'dim_Location.csv'),
 (3,  N'dim.Product',            N'dim_Product.csv'),
 (4,  N'dim.Channel',            N'dim_Channel.csv'),
 (5,  N'dim.Bank',               N'dim_Bank.csv'),
 (6,  N'dim.SalesRep',           N'dim_SalesRep.csv'),
 (7,  N'dim.ResponseCode',       N'dim_ResponseCode.csv'),
 (8,  N'dim.PricingPlan',        N'dim_PricingPlan.csv'),
 (9,  N'dim.CostRate',           N'dim_CostRate.csv'),
 (10, N'dim.Merchant',           N'dim_Merchant.csv'),
 (11, N'dim.Terminal',           N'dim_Terminal.csv'),
 (12, N'bridge.MerchantPricing', N'bridge_MerchantPricing.csv'),
 (13, N'fact.Transactions',      N'fact_Transactions.csv');

DECLARE @sql NVARCHAR(MAX), @tbl NVARCHAR(100), @file NVARCHAR(100);
DECLARE c CURSOR LOCAL FAST_FORWARD FOR SELECT tbl, file_name FROM @tables ORDER BY ord;
OPEN c;
FETCH NEXT FROM c INTO @tbl, @file;
WHILE @@FETCH_STATUS = 0
BEGIN
    SET @sql = N'BULK INSERT ' + @tbl + N' FROM ''' + @path + @file + N''' WITH ('
             + N'FORMAT = ''CSV'', FIRSTROW = 2, FIELDTERMINATOR = '','', CODEPAGE = ''65001'', '
             + N'KEEPNULLS, CHECK_CONSTRAINTS, TABLOCK);';
    PRINT 'Loading ' + @tbl + ' ...';
    BEGIN TRY
        EXEC sys.sp_executesql @sql;
    END TRY
    BEGIN CATCH
        PRINT 'FAILED on ' + @tbl + ': ' + ERROR_MESSAGE();
        THROW;   -- stop here so later tables are not loaded on top of a failure
    END CATCH
    FETCH NEXT FROM c INTO @tbl, @file;
END
CLOSE c;
DEALLOCATE c;
GO

/* ---------- Step 3: indexes (built after the load, which is faster) ---------- */
IF NOT EXISTS (SELECT 1 FROM fact.Transactions)
BEGIN
    RAISERROR('fact.Transactions is empty. Fix the load errors above, then run the script again.', 16, 1);
    RETURN;
END
CREATE NONCLUSTERED INDEX IX_Txn_date     ON fact.Transactions (date_key)    INCLUDE (fee_charged_ngn, transaction_amount_ngn);
CREATE NONCLUSTERED INDEX IX_Txn_merchant ON fact.Transactions (merchant_id) INCLUDE (date_key, fee_charged_ngn);
CREATE NONCLUSTERED INDEX IX_Txn_channel  ON fact.Transactions (channel_id, product_id);
CREATE NONCLUSTERED INDEX IX_Txn_location ON fact.Transactions (location_key);
CREATE NONCLUSTERED INDEX IX_Txn_status   ON fact.Transactions (txn_status, response_code);
GO

/* =====================================================================
   VALIDATION: run each block and compare with the expected result
   ===================================================================== */

/* 1. Row counts. Expected: Date 746, Location 14, Product 4, Channel 5, Bank 14, SalesRep 10,
      ResponseCode 9, PricingPlan 5, CostRate 64, Merchant 400, Terminal 901,
      MerchantPricing 410, Transactions 1,000,151 */
SELECT 'dim.Date' AS table_name, COUNT(*) AS row_count FROM dim.[Date]
UNION ALL SELECT 'dim.Location',           COUNT(*) FROM dim.Location
UNION ALL SELECT 'dim.Product',            COUNT(*) FROM dim.Product
UNION ALL SELECT 'dim.Channel',            COUNT(*) FROM dim.Channel
UNION ALL SELECT 'dim.Bank',               COUNT(*) FROM dim.Bank
UNION ALL SELECT 'dim.SalesRep',           COUNT(*) FROM dim.SalesRep
UNION ALL SELECT 'dim.ResponseCode',       COUNT(*) FROM dim.ResponseCode
UNION ALL SELECT 'dim.PricingPlan',        COUNT(*) FROM dim.PricingPlan
UNION ALL SELECT 'dim.CostRate',           COUNT(*) FROM dim.CostRate
UNION ALL SELECT 'dim.Merchant',           COUNT(*) FROM dim.Merchant
UNION ALL SELECT 'dim.Terminal',           COUNT(*) FROM dim.Terminal
UNION ALL SELECT 'bridge.MerchantPricing', COUNT(*) FROM bridge.MerchantPricing
UNION ALL SELECT 'fact.Transactions',      COUNT(*) FROM fact.Transactions;

/* 2. Constraints must be trusted. Both queries should return NO rows. */
SELECT name AS untrusted_foreign_key FROM sys.foreign_keys WHERE is_not_trusted = 1;
SELECT name AS untrusted_check       FROM sys.check_constraints WHERE is_not_trusted = 1;

/* 3. Does SQL Server tell the same story as the generator?
      Expected: 2024 -> 448,408 rows | fee revenue ~117.9m | net revenue ~48.6m | margin ~41.2%
                2025 -> 551,743 rows | fee revenue ~144.0m | net revenue ~51.1m | margin ~35.5% */
SELECT LEFT(CAST(date_key AS VARCHAR(8)), 4)                                              AS yr,
       COUNT(*)                                                                           AS txns,
       ROUND(SUM(fee_charged_ngn) / 1e6, 1)                                               AS fee_revenue_m,
       ROUND(SUM(fee_charged_ngn - processing_cost_ngn - switching_cost_ngn
                 - bank_charge_ngn - other_cost_ngn) / 1e6, 1)                            AS net_revenue_m,
       ROUND(100.0 * SUM(fee_charged_ngn - processing_cost_ngn - switching_cost_ngn
                 - bank_charge_ngn - other_cost_ngn) / SUM(fee_charged_ngn), 1)           AS net_margin_pct
FROM fact.Transactions
GROUP BY LEFT(CAST(date_key AS VARCHAR(8)), 4)
ORDER BY yr;