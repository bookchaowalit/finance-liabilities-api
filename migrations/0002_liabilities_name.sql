-- Fix the generated plural: liabilities.liabilitys -> liabilities.liabilities (route /v1/liabilities).
-- Grants, row-level security and policies follow the table; the sequence and index names keep the old spelling.
ALTER TABLE liabilities.liabilitys RENAME TO liabilities;
