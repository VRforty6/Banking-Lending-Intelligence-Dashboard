# HMDA ETL Process Documentation

## Execution Order

The HMDA ETL pipeline follows this sequence:

1. **Environment Setup**
   - Load database connection parameters from environment variables
   - Establish SQLAlchemy engine connection

2. **Database Preparation**
   - Execute SQL scripts in order:
     - `sql/02_create_schemas.sql` - Creates staging, analytics, audit schemas if they don't exist
     - `sql/03_create_tables.sql` - Creates tables if they don't exist (using CREATE TABLE IF NOT EXISTS patterns)
     - Note: Database creation (`sql/01_create_database.sql`) is assumed to be done separately

3. **Data Extraction and Staging**
   - Truncate staging table (`staging.hmda_raw`) to ensure clean load
   - Read source CSV file in chunks (configurable, default 100,000 rows)
   - For each chunk:
     - Clean column names (convert to snake_case)
     - Apply data type conversions
     - Compute profile_hash for applicant deduplication
     - Insert into staging table

4. **Dimension and Fact Population**
   - Insert distinct values into dimension tables:
     - dim_lender (from lei)
     - dim_geography (from geographic fields)
     - dim_loan (from loan characteristics)
     - dim_applicant_profile (from demographic fields, deduplicated by profile_hash)
     - dim_action_taken (from action_taken codes)
   - Populate fact table by joining staging with dimension tables to get surrogate keys

5. **Index Creation**
   - Create indexes on foreign key columns in fact table for query performance

6. **View Creation (Optional)**
   - Create or replace analytical views in `sql/05_create_views.sql`

7. **Validation (Optional)**
   - Run validation queries from `sql/06_validation_queries.sql`

## Load Behavior

### Full Refresh (Current Implementation)
The current implementation performs a full refresh each run:
1. TRUNCATE TABLE staging.hmda_raw RESTART IDENTITY CASCADE
2. Reload all data from source CSV
3. Re-populate all dimension and fact tables
4. Re-create views

This approach ensures data consistency but may be inefficient for large datasets.

### Incremental Load Considerations
For true incremental loading, the system would need:
1. **Source Change Detection**: Track modifications to source data
2. **Staging Table Strategy**: 
   - Option A: Append-only staging with processing watermarks
   - Option B: Replace-only changed partitions
3. **Dimension Table Handling**:
   - Type 1 (overwrite) for corrections
   - Type 2 (historical) for tracking changes over time
4. **Fact Table Updates**:
   - Insert new records
   - Update existing records if source data changes
   - Handle late-arriving facts

### Current Limitations
The current implementation does not support incremental loading because:
1. It uses TRUNCATE on staging table each run
2. Dimension table inserts use ON CONFLICT DO NOTHING, which prevents updates
3. Fact table is completely repopulated from scratch
4. No mechanism to identify new vs existing records in source

## Recommended Improvements for Incremental Support

1. **Add Watermark Column**: Add a `processed_timestamp` to track when records were last processed

2. **Staging Strategy**:
   - Use staging table as landing zone only
   - Add batch_id or process_date to track loading cycles
   - Implement MERGE/UPSERT patterns for dimension tables

3. **Change Data Capture**:
   - For file-based source: Compare file modification dates or use checksums
   - For database source: Use timestamps, version numbers, or CDC tools

4. **Performance Considerations**:
   - Partition fact table by application_year
   - Use bulk loading techniques (COPY) for large data volumes
   - Implement parallel processing where safe

## Rollback and Recovery

The current process supports:
- **Atomic Operations**: Each major step runs in a transaction where possible
- **Error Handling**: SQL execution uses try/except with transaction rollback
- **Idempotent Schema Creation**: CREATE ... IF NOT EXISTS patterns prevent failures on re-run

However, a full re-run is required to recover from data corruption since existing data is overwritten.

## Dependencies
- Source CSV file must be present at `data/raw/state_CA.csv`
- PostgreSQL database must be accessible with correct credentials
- Required Python packages: pandas, sqlalchemy, psycopg2-binary, pyarrow