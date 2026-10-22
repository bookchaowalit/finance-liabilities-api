# SPEC-001 — L2 baseline: locked dependencies, strict types, domain rules under test

Standard: ADR-0004 — TDD + SDD (architecture-docs, `docs/architecture/decisions/ADR-0004-tdd-sdd-standard.md`).
Big Loop Plan Wave 2 (solo-empire `repository-catalog/roadmaps/BIG-LOOP-PLAN-2026-10-21.md`).

## Document control

| Field | Value |
|---|---|
| Spec ID / version | SPEC-001 / 1.0 |
| Status | in review (implemented; owner approval pending) |
| Repository / path | bookchaowalit/finance-liabilities-api / `specs/001-l2-baseline/spec.md` |
| Owner (maker) | Claude Code (Wave 2 cells session) |
| Reviewer (checker) | Fresh Claude reviewer session (no maker context) |
| Approver | Owner (bookchaowalit): pending, see the Wave 2 report owner actions |
| Requirement links | Big Loop DoD L2: `PRODUCT.md`, ≥ 3 test files, Sentry, type check; L1 lockfile |
| Main-only | yes: committed straight to `main`, so the red run is local (ADR-0004 rule 2, v1.1) |
| Created / approved | 2026-10-22 / pending owner |

## 1. Problem and intent

- **Problem:** Dependencies were installed unpinned, there was no type check, and the only tests were the generic contract suite; the liability rules (kinds, non-negative money, object metadata, filters) were not tested.
- **Outcome:** the image installs exactly `uv.lock` (`uv sync --frozen`), CI runs Ruff, mypy
  (strict on `src/`) and a coverage gate on shared CI v1.1.1, and the cell's own rules have
  tests of their own beyond the generic contract suite.
- **Why now:** Wave 2 of the Big Loop Plan; milestone M1 is 2026-11-15.

## 2. Scope

| In scope | Out of scope (non-goals) |
|---|---|
| `uv.lock`, Dockerfile, CI caller bump, Ruff/mypy config and fixes, domain tests, `PRODUCT.md` | New endpoints or fields; database migrations; a shared cellkit package (owner decision 2026-10-21: each service owns its code) |

## 3. Behaviour — scenarios

### AC-01 — A liability needs a name and a known type

- **Given** an owner with write permission
- **When** they create a liability without a name, without a type, with type `mortgage` or with a 201-character name
- **Then** the API answers 422 for each; every listed type (loan, credit, tax, payable, subscription, other) is accepted
- **Test:** `tests/test_liability_validation.py::test_liability_type_must_be_a_known_kind` · level: integration (API + throwaway PostgreSQL)

### AC-02 — Money and interest cannot be negative

- **Given** an owner with write permission
- **When** they create or update a liability with a negative principal, outstanding amount, minimum payment or interest rate
- **Then** the API answers 422 and a stored value is unchanged; 0 is accepted
- **Test:** `tests/test_liability_validation.py::test_money_amounts_cannot_be_negative` · level: integration (API + throwaway PostgreSQL)

### AC-03 — Metadata must be a JSON object

- **Given** an owner with write permission
- **When** they create a liability with metadata that is an array, a string or a number
- **Then** the API answers 422; an object is stored unchanged
- **Test:** `tests/test_liability_validation.py::test_metadata_must_be_an_object` · level: integration (API + throwaway PostgreSQL)

### AC-04 — New liabilities default to personal, active, THB

- **Given** a create request with only a name and a type
- **When** the liability is created
- **Then** `owner_scope` is personal, `status` is active, `currency` is THB, `version` is 1 and the optional amounts are empty
- **Test:** `tests/test_liability_defaults.py::test_new_liability_defaults_to_personal_active_thb` · level: integration (API + throwaway PostgreSQL)

### AC-05 — The account id is a plain number

- **Given** no account with id 424242 is known to this service
- **When** a liability is created with `account_id` 424242
- **Then** it is created and keeps the number; a non-number is refused with 422
- **Test:** `tests/test_liability_defaults.py::test_account_id_is_a_plain_number_not_a_checked_reference` · level: integration (API + throwaway PostgreSQL)

### AC-06 — Listing filters accept several statuses

- **Given** overdue, settled and planned liabilities
- **When** the owner lists with `status=overdue&status=settled`
- **Then** only overdue and settled liabilities come back; an unknown status or a non-filter field is refused with 422
- **Test:** `tests/test_liability_queries.py::test_list_filters_by_several_statuses_at_once` · level: integration (API + throwaway PostgreSQL)

### AC-07 — Changing a liability bumps its version once

- **Given** a liability at version 1
- **When** a patch lowers the outstanding amount, then repeats unchanged values
- **Then** the version becomes 2 on the change and stays the same on a patch that changes nothing; a stale `expected_version` gets 409
- **Test:** `tests/test_liability_queries.py::test_paying_down_a_liability_bumps_its_version` · level: integration (API + throwaway PostgreSQL)

### AC-08 — Numbers fit their columns

- **Given** an int field (PostgreSQL integer) or a real field
- **When** a client sends 2**31, or NaN / Infinity / 1e400 as raw JSON
- **Then** the API answers 422 naming the field (before: a 500 from PostgreSQL, or the value silently stored as null)
- **Test:** `tests/test_contract.py::test_numbers_fit_their_columns` · level: integration (API + throwaway PostgreSQL)

## 4. Interfaces and data

| Interface | Change | Contract |
|---|---|---|
| `/v1/*` (all resources) | unchanged | same routes and payloads; see README |

- **Data model / migration:** N/A — no schema change. Range rules are checked by the API on
  create and update; rows already stored are not rewritten.
- **Backward compatibility:** clients keep the same routes. A write that would store a range
  ending before it starts now gets `422 invalid_value` instead of `201/200`.

## 5. Non-functional requirements

| NFR | Target | How it is tested |
|---|---|---|
| Performance | N/A — no hot-path change beyond one comparison per declared range | — |
| Security / privacy | Same authorization, RLS and Sentry scrubbing as before | contract suite (`tests/test_contract.py`), `tests/test_sentry.py` |
| Reliability / observability | Reproducible image from `uv.lock`; failed inline publishes reach Sentry | image rehearsal before push; `test_inline_publish_failure_is_reported` |
| Accessibility / UX | N/A — API only | — |

## 6. Test plan (TDD)

- **Test levels:** integration tests against the FastAPI app with a throwaway local PostgreSQL
  (pgserver) and a fake platform; no hosted database or platform.
- **Test data:** generated in each test; no production data.
- **Coverage:** CI gate `coverage-threshold: "55"` (measured 57.58% on 2026-10-22, minus 2 points).
- **Not test-first (exceptions):** tests that pin behaviour the service already had
  (characterization tests, marked below) were written after the code by nature; tooling and
  config changes are covered by CI itself.

### Red / green log

| Scenario | Test | Red: commit / run + failure message | Green: commit / run | Refactor note |
|---|---|---|---|---|
| AC-01 | `tests/test_liability_validation.py::test_liability_type_must_be_a_known_kind` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-02 | `tests/test_liability_validation.py::test_money_amounts_cannot_be_negative` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-03 | `tests/test_liability_validation.py::test_metadata_must_be_an_object` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-04 | `tests/test_liability_defaults.py::test_new_liability_defaults_to_personal_active_thb` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-05 | `tests/test_liability_defaults.py::test_account_id_is_a_plain_number_not_a_checked_reference` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-06 | `tests/test_liability_queries.py::test_list_filters_by_several_statuses_at_once` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-07 | `tests/test_liability_queries.py::test_paying_down_a_liability_bumps_its_version` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-08 | `tests/test_contract.py::test_numbers_fit_their_columns` | 9ce8d79 · `.venv/bin/pytest -q -k numbers_fit` · `ValueError: Out of range float values are not JSON compliant: nan` | CI run of the pushed tip | none |

## 7. Risks and open questions

| # | Risk or question | Impact | Owner | Resolution / date |
|---|---|---|---|---|
| 1 | Stored rows written before a range rule existed may already be inverted | a patch touching one of those dates is refused until both are fixed | owner | patches that do not touch the range still work |

## 8. Change log

| Version | Date | Change | Scenarios affected | Approved by |
|---|---|---|---|---|
| 1.0 | 2026-10-22 | Implemented with the Wave 2 baseline | all | pending owner |

## Approval

| Gate | Role | Name / date | Decision | Evidence |
|---|---|---|---|---|
| Implemented (DoD) | Reviewer (checker) | Fresh Claude reviewer / 2026-10-22 | see Wave 2 report | CI run of the pushed tip |
| Implemented (DoD) | Approver | Owner | pending | Wave 2 report |
