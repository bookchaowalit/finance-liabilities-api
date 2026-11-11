-- SPEC-006 (2026-11-11): cross-service references between the finance cells (liabilities).
-- Append-only: do not edit once applied.

-- The relay sends a record's events in insert order (the row lock makes it the commit order).
ALTER TABLE liabilities.outbox ADD COLUMN seq bigint GENERATED ALWAYS AS IDENTITY;
DROP INDEX liabilities.outbox_unrelayed;
CREATE INDEX outbox_unrelayed ON liabilities.outbox (seq) WHERE relayed_at IS NULL;

-- SPEC-006: cross-service references, fed by finance.events.v1.
CREATE TABLE liabilities.ref_targets (
    workspace_id   uuid NOT NULL,
    target         text NOT NULL,
    record_id      bigint NOT NULL,
    status         text,
    deleted        boolean NOT NULL DEFAULT false,
    record_version bigint NOT NULL DEFAULT 0,
    event_seq      bigint NOT NULL DEFAULT 0,
    updated_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, target, record_id)
);
CREATE TABLE liabilities.ref_sources (
    workspace_id    uuid NOT NULL,
    source          text NOT NULL,
    source_id       bigint NOT NULL,
    field           text NOT NULL,
    target_resource text NOT NULL,
    target_id       bigint,
    deleted         boolean NOT NULL DEFAULT false,
    record_version  bigint NOT NULL DEFAULT 0,
    event_seq       bigint NOT NULL DEFAULT 0,
    updated_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, source, source_id, field)
);
CREATE INDEX ref_sources_live ON liabilities.ref_sources (workspace_id, target_resource, target_id) WHERE NOT deleted;
CREATE TABLE liabilities.ref_offsets (
    topic       text NOT NULL,
    partition   integer NOT NULL,
    next_offset bigint NOT NULL,
    PRIMARY KEY (topic, partition)
);
ALTER TABLE liabilities.ref_targets ENABLE ROW LEVEL SECURITY;
ALTER TABLE liabilities.ref_targets FORCE ROW LEVEL SECURITY;
CREATE POLICY workspace_isolation ON liabilities.ref_targets USING (workspace_id = liabilities.current_workspace());
CREATE POLICY publisher_sync ON liabilities.ref_targets TO liabilities_publisher USING (true) WITH CHECK (true);
GRANT SELECT ON liabilities.ref_targets TO liabilities_api;
GRANT SELECT, INSERT, UPDATE ON liabilities.ref_targets TO liabilities_publisher;
ALTER TABLE liabilities.ref_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE liabilities.ref_sources FORCE ROW LEVEL SECURITY;
CREATE POLICY workspace_isolation ON liabilities.ref_sources USING (workspace_id = liabilities.current_workspace());
CREATE POLICY publisher_sync ON liabilities.ref_sources TO liabilities_publisher USING (true) WITH CHECK (true);
GRANT SELECT ON liabilities.ref_sources TO liabilities_api;
GRANT SELECT, INSERT, UPDATE ON liabilities.ref_sources TO liabilities_publisher;
GRANT SELECT, INSERT, UPDATE ON liabilities.ref_offsets TO liabilities_publisher;

-- Rows written before SPEC-005 announce themselves once, so other cells learn their ids.
ALTER TABLE liabilities.outbox NO FORCE ROW LEVEL SECURITY;
ALTER TABLE liabilities.liabilities NO FORCE ROW LEVEL SECURITY;
INSERT INTO liabilities.outbox (workspace_id, type, subject, classification, payload, correlation_id) SELECT workspace_id, 'liabilities.liability.snapshot', 'empire:liabilities:liability:' || id, 'confidential', jsonb_build_object('liability_type', liability_type, 'scope', scope, 'account_id', account_id, 'currency', currency, 'due_date', due_date, 'status', status, 'version', version, 'deleted', false), 'spec-006-snapshot' FROM liabilities.liabilities ORDER BY id;
ALTER TABLE liabilities.liabilities FORCE ROW LEVEL SECURITY;
ALTER TABLE liabilities.outbox FORCE ROW LEVEL SECURITY;
