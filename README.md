# Banking Lending Intelligence Dashboard

## Business Problem
A bank needs visibility into loan applications, approval outcomes, borrower characteristics, lending geography, lender performance, and portfolio trends to make data-driven lending decisions and monitor risk.

## Planned Technology Stack
- **Language**: Python for data processing and analysis
- **Database**: PostgreSQL for data storage
- **Query Language**: SQL for data extraction and transformation
- **Visualization**: Power BI for interactive dashboarding
- **Version Control**: Git and GitHub for source code management

## Planned Dashboard Pages
1. Loan Application Overview
2. Approval and Denial Analysis
3. Borrower Demographics
4. Geographic Lending Distribution
5. Lender Performance Metrics
6. Portfolio Trends and Risk Indicators

## Repository Structure
- `data/raw/`: Original data files as received from sources
- `data/processed/`: Cleaned and transformed data ready for analysis
- `src/`: Python scripts for ETL, analysis, and modeling
- `sql/`: SQL queries for data extraction and transformation
- `powerbi/`: Power BI dataset (.pbix) and related files
- `docs/`: Project documentation, data dictionaries, and methodology
- `reports/`: Generated reports and presentations
- `screenshots/`: Dashboard screenshots and visualizations
- `tests/`: Test suite organized by type:
  - `unit/`: Unit tests for individual functions and components
  - `integration/`: Integration tests for system interactions
  - `data_quality/`: Data validation and quality checks
- `scripts/`: Command-line utilities and project automation (core ETL logic remains in src/ and scripts/)
- `notebooks/`: Exploratory data analysis only (production transformations must remain in src/ and scripts/)

## Project Status
Planning