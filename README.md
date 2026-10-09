# PayBridge NG: Revenue & Profitability Diagnostic

A year-over-year financial performance analysis for a fictional Nigerian payments company, built end to end: from the business problem, to a SQL Server database, to a Power BI dashboard and recommendations.

> **About this project.** PayBridge NG is a fictional company, and all data is synthetic. I built a simplified reporting database to practise the full analyst workflow: defining the business problem, designing the data model, analysing performance, and recommending actions. Real payment systems are more complex. This project focuses on the part analysts do every day: turning transaction data into decisions.

**Author:** Sanya Ajibola Ebenezer | [LinkedIn](https://www.linkedin.com/in/ajibola-sanya-119a91384/) <!-- add your profile link -->

---

## The business problem

PayBridge NG processes merchant payments across POS, web checkout, mobile app, USSD and QR channels. Revenue is growing, but profit is not keeping pace, and management cannot say why.

**Core question:** where does revenue growth stop converting into profit, and what should management change first?

The full problem statement, with stakeholders, analytical questions, KPIs and six hypotheses, is in [`docs/PayBridge_NG_Problem_Statement_Brief.pdf`](docs/PayBridge_NG_Problem_Statement_Brief.pdf).

## Approach

| Phase | What I did | Where |
|---|---|---|
| 1. Problem framing | Wrote the problem statement brief: objective, stakeholders, questions, KPIs, hypotheses | `docs/` |
| 2. Data model | Designed a star schema: one transaction-level fact table and supporting dimensions, documented in a data dictionary | `docs/` |
| 3. Database | Built the schema in SQL Server (T-SQL) with primary keys, foreign keys and check constraints | `sql/01_create_schema.sql` |
| 4. Data generation | Simulated 24 months of business activity in Python, driven by one configuration file with a fixed seed | `generator/` |
| 5. Load and validate | Loaded about 1 million transactions with BULK INSERT, with constraint checking on, then checked row counts | `sql/02_load_data.sql` |
| 6. Dashboard | Power BI model, DAX measures and report pages | `powerbi/` *(in progress)* |
| 7. Insights | Findings and recommendations quantified in naira | *(to come)* |

## The data

- **Scale:** about 1 million transaction attempts, January 2024 to December 2025
- **Entities:** 400 merchants across 14 cities, with terminals, pricing plans and cost rates
- **Model:** 13 tables (one fact table, dimensions and one pricing-history bridge table)
- **Realism:** a few large merchants dominate volume; merchants join, churn or go quiet; cities launch at different times; volume rises at month-end and in the festive season; some transactions fail and are retried; pricing and costs change over time

The settings behind the simulation are in `generator/config.py`. A fixed random seed means every run produces the same dataset.

## Repository structure

```
paybridge/
├── README.md
├── requirements.txt
├── docs/          problem statement brief, data dictionary
├── sql/           database schema and load scripts
├── generator/     Python data generator
├── powerbi/       Power BI report and DAX measures
└── output/        generated CSV files (not committed, see below)
```

## How to reproduce

**Requirements:** Python 3.10+, SQL Server 2019+ (Developer edition is free) with SSMS, Power BI Desktop.

1. **Generate the data**
   ```
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   cd generator
   python generate.py
   ```
   This writes 13 CSV files to `output/`. They are not stored in this repository because the transaction file exceeds GitHub's file size limit.
2. **Create the database:** run `sql/01_create_schema.sql` in SSMS.
3. **Load the data:** copy the CSV files to a folder SQL Server can read (for example `C:\PayBridgeData\`), set the `@path` value in `sql/02_load_data.sql`, and run it. The script ends with row-count and reconciliation checks.

## Scope and limitations

- A simplified analytics-layer model: no customer table, settlements, refunds or chargebacks, and one currency
- Costs are recorded per transaction, whereas real costs often arrive as invoices and are allocated later
- All figures are illustrative and come from a simulation

## Status

Database, data generation and load are complete. The Power BI model and dashboard are next, followed by the insights and recommendations write-up.
