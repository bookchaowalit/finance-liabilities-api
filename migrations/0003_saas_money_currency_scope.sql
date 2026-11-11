-- SPEC-003 (2026-11-11): exact money, ISO 4217 currency, workspace-defined scope (liabilities).
-- Amounts move from double precision to numeric; currency codes must be three upper-case letters;
-- owner_scope (the owner's own life areas) becomes scope, a free label each workspace defines.
-- Append-only: do not edit once applied.

-- liability
ALTER TABLE liabilities.liabilities NO FORCE ROW LEVEL SECURITY;
UPDATE liabilities.liabilities SET currency = upper(btrim(currency));
ALTER TABLE liabilities.liabilities FORCE ROW LEVEL SECURITY;
ALTER TABLE liabilities.liabilities RENAME COLUMN owner_scope TO scope;
DO $$ DECLARE c text; BEGIN FOR c IN SELECT conname FROM pg_constraint WHERE conrelid = 'liabilities.liabilities'::regclass AND contype = 'c' AND conkey = ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid = 'liabilities.liabilities'::regclass AND attname = 'scope')] LOOP EXECUTE format('ALTER TABLE liabilities.liabilities DROP CONSTRAINT %I', c); END LOOP; END $$;
ALTER TABLE liabilities.liabilities ALTER COLUMN scope SET DEFAULT '';
ALTER TABLE liabilities.liabilities ADD CONSTRAINT liabilities_scope_check CHECK (length(scope) <= 64);
DO $$ DECLARE i text; BEGIN SELECT indexname INTO i FROM pg_indexes WHERE schemaname = 'liabilities' AND tablename = 'liabilities' AND indexdef LIKE '%(workspace_id, scope)'; IF i IS NOT NULL THEN EXECUTE format('ALTER INDEX liabilities.%I RENAME TO liabilities_scope', i); END IF; END $$;
DO $$ DECLARE c text; BEGIN FOR c IN SELECT conname FROM pg_constraint WHERE conrelid = 'liabilities.liabilities'::regclass AND contype = 'c' AND conkey = ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid = 'liabilities.liabilities'::regclass AND attname = 'principal_amount')] LOOP EXECUTE format('ALTER TABLE liabilities.liabilities DROP CONSTRAINT %I', c); END LOOP; END $$;
ALTER TABLE liabilities.liabilities ALTER COLUMN principal_amount TYPE numeric(19,4) USING principal_amount::numeric(19,4);
ALTER TABLE liabilities.liabilities ADD CONSTRAINT liabilities_principal_amount_check CHECK (principal_amount IS NULL OR (principal_amount >= 0));
DO $$ DECLARE c text; BEGIN FOR c IN SELECT conname FROM pg_constraint WHERE conrelid = 'liabilities.liabilities'::regclass AND contype = 'c' AND conkey = ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid = 'liabilities.liabilities'::regclass AND attname = 'outstanding_amount')] LOOP EXECUTE format('ALTER TABLE liabilities.liabilities DROP CONSTRAINT %I', c); END LOOP; END $$;
ALTER TABLE liabilities.liabilities ALTER COLUMN outstanding_amount TYPE numeric(19,4) USING outstanding_amount::numeric(19,4);
ALTER TABLE liabilities.liabilities ADD CONSTRAINT liabilities_outstanding_amount_check CHECK (outstanding_amount IS NULL OR (outstanding_amount >= 0));
DO $$ DECLARE c text; BEGIN FOR c IN SELECT conname FROM pg_constraint WHERE conrelid = 'liabilities.liabilities'::regclass AND contype = 'c' AND conkey = ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid = 'liabilities.liabilities'::regclass AND attname = 'minimum_payment')] LOOP EXECUTE format('ALTER TABLE liabilities.liabilities DROP CONSTRAINT %I', c); END LOOP; END $$;
ALTER TABLE liabilities.liabilities ALTER COLUMN minimum_payment TYPE numeric(19,4) USING minimum_payment::numeric(19,4);
ALTER TABLE liabilities.liabilities ADD CONSTRAINT liabilities_minimum_payment_check CHECK (minimum_payment IS NULL OR (minimum_payment >= 0));
DO $$ DECLARE c text; BEGIN FOR c IN SELECT conname FROM pg_constraint WHERE conrelid = 'liabilities.liabilities'::regclass AND contype = 'c' AND conkey = ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid = 'liabilities.liabilities'::regclass AND attname = 'interest_rate_percent')] LOOP EXECUTE format('ALTER TABLE liabilities.liabilities DROP CONSTRAINT %I', c); END LOOP; END $$;
ALTER TABLE liabilities.liabilities ALTER COLUMN interest_rate_percent TYPE numeric(30,10) USING interest_rate_percent::numeric(30,10);
ALTER TABLE liabilities.liabilities ADD CONSTRAINT liabilities_interest_rate_percent_check CHECK (interest_rate_percent IS NULL OR (interest_rate_percent >= 0));
DO $$ DECLARE c text; BEGIN FOR c IN SELECT conname FROM pg_constraint WHERE conrelid = 'liabilities.liabilities'::regclass AND contype = 'c' AND conkey = ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid = 'liabilities.liabilities'::regclass AND attname = 'currency')] LOOP EXECUTE format('ALTER TABLE liabilities.liabilities DROP CONSTRAINT %I', c); END LOOP; END $$;
ALTER TABLE liabilities.liabilities ADD CONSTRAINT liabilities_currency_check CHECK (currency ~ '^[A-Z]{3}$');
