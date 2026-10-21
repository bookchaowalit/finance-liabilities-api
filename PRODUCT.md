# Product

<!-- impeccable:product-schema 1 -->

## Platform

api

## Users

- The Solo Empire owner, through `life-dashboard-web` (finance page: open liabilities, those with
  status active or overdue, ordered by due date, with the outstanding amount summed per currency),
  the cell's own MCP server (`liabilities-mcp`) and the hosted tool hub
  (`platform-mcp-remote-worker`).
- Automations with an `empire-platform` token (for example `owner-mcp`), within the permissions
  `liabilities.liability:read|write|delete`.
- `finance-ledger-core` (`book-finance-api`): its boundary doc
  `docs/gates/BOO-140-finance-api-boundary.md` maps `/api/finance/v1/summary` to read
  `/v1/liabilities` [ต้องยืนยัน: whether that mapping is live].

## Product Purpose

The list of money owed: loans, credit, tax, payables, subscriptions and other liabilities, each
with principal, outstanding amount, minimum payment, interest rate, due date and status, per owner
scope. `account_id` can name the account in `finance-accounts-api` the liability is paid from.

Success: every debt the owner carries exists once with a current outstanding amount, and anything
past due is marked overdue so the dashboard shows it.

## Positioning

One capability, one service: its own API (Railway), its own database (Neon) with row-level
security per workspace, and authorization, executions and audit through `empire-platform`. It is
workspace-scoped, so the same service can serve other tenants without code changes.

## Operating Context

- Production: `https://liabilities-api-production.up.railway.app` (`/health`), deployed by merging
  to `main` after CI.
- Data starts empty (created 2026-10-12 from the retired `finance_*` tables' fields); imports keep
  old ids in `legacy_id`.
- Monitored by `platform-uptime-worker` (probed hourly, because the service sleeps when idle);
  errors go to Sentry without personal data.

## Capabilities and Constraints

- `/v1/liabilities`: list (filters `liability_type`, `owner_scope`, `status`, repeatable for
  any-of; ordered by id), stats (grouped by one of those filters), get, get-by-legacy-id, create
  (with `Idempotency-Key`), patch (with `expected_version`), delete.
- Rules: `name` (at most 200 characters) and `liability_type` are required; `liability_type` is
  one of loan, credit, tax, payable, subscription, other; `status` is one of planned, active
  (default), overdue, settled, cancelled; `owner_scope` defaults to personal; `principal_amount`,
  `outstanding_amount`, `minimum_payment` and `interest_rate_percent` cannot be negative (zero is
  allowed); `currency` defaults to THB (at most 12 characters); `metadata` is a JSON object.
- Names are not unique. `account_id` is a plain number, not a foreign key: this service does not
  check that the account exists.
- Nothing here marks a liability overdue when its `due_date` passes; the caller sets the status
  [ต้องยืนยัน: which job or person does it].
- Out of scope: payment schedules, interest accrual, and the payments themselves
  (`finance-transactions-api`).

## Measures

Proposed (nothing collects them yet):

- Total outstanding amount of active and overdue liabilities, per currency (the dashboard already
  shows it).
- Liabilities with status overdue (target: 0).
- 5xx rate and p95 latency on `/v1/liabilities` (Sentry and uptime worker).
