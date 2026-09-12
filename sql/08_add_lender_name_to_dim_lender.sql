-- Add optional lender-name enrichment to the lender dimension.
-- This preserves the existing LEI grain, surrogate keys, uniqueness, and fact FKs.

ALTER TABLE analytics.dim_lender
ADD COLUMN IF NOT EXISTS lender_name TEXT;
