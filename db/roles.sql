-- Roles for the liabilities database. Locally a superuser runs this; on Neon
-- `liabilities-db provision` creates the same roles through the migrator.
--
-- liabilities_migrator  owns the schema and runs migrations only.
-- liabilities_api       the API at runtime: no superuser, no BYPASSRLS, owns nothing.
-- liabilities_publisher sweeps and marks the outbox across workspaces; nothing else.

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'liabilities_migrator') THEN
        CREATE ROLE liabilities_migrator LOGIN NOSUPERUSER NOCREATEROLE NOBYPASSRLS;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'liabilities_api') THEN
        CREATE ROLE liabilities_api LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS NOINHERIT;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'liabilities_publisher') THEN
        CREATE ROLE liabilities_publisher LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS NOINHERIT;
    END IF;
END
$$;
