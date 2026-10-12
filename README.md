# liabilities

The Liabilities cell: its own API (Railway, serverless) and its own Neon
database, first generated from `cell.yaml` (one of the ten finance
services split on 2026-10-12). It
reuses empire-platform for identity, authorization, executions and audit over
HTTP with the caller's token.

| | |
|---|---|
| API | Railway project `liabilities`, service `liabilities-api` (Serverless) |
| Data | Neon project `liabilities`, database `liabilities` |
| Registry | solo-empire `repository-catalog/registries/online-systems.yaml` (`liabilities`) |

## API

Every resource has list, stats, get, get-by-legacy-id, create, patch and delete
(see `cellkit/app.py`). Permissions are `liabilities.<resource>:read|write|delete`.

| Path | Resource | Filters |
|---|---|---|
| `/v1/liabilities` | liability | `liability_type`, `owner_scope`, `status` |

## Develop and operate

```bash
uv venv .venv && uv pip install --python .venv/bin/python -e ".[dev]"
.venv/bin/pytest -q
NEON_API_KEY=... .venv/bin/liabilities-db provision
npm install && railway config apply && railway up --ci --service liabilities-api
railway scale --service liabilities-api asia-southeast1-eqsg3a=1 us-east4-eqdc4a=0   # next to Neon and the platform
```

Railway variables: `LIABILITIES_DB_MODE=hosted`, `LIABILITIES_DB_URL_API`,
`LIABILITIES_JWT_PUBLIC_KEY_PEM`, `LIABILITIES_JWT_ISSUER`, `EMPIRE_PLATFORM_URL`.
