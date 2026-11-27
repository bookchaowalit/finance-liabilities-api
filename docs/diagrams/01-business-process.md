# 01 — Business process (As-Is / To-Be)

finance-liabilities-api (cell `liabilities`) เก็บหนี้และภาระที่ต้องจ่าย (loan, credit, tax, payable, subscription, other) พร้อมเงินต้น ยอดคงค้าง ค่างวดขั้นต่ำ ดอกเบี้ย วันครบกำหนด และสถานะ ต่อ scope; `account_id` ชี้ไปที่ account ใน `finance-accounts-api` และ owner ใช้ผ่าน `life-dashboard-web`, `finance-api` และ MCP

Last reviewed: 2026-11-27 · commit `c3b9751`

## As-Is (จากโค้ดวันนี้)

```mermaid
flowchart LR
  DASH["life-dashboard-web (หน้า finance)"] --> API
  BFF["finance-api (views, export, erase)"] --> API
  MCP["liabilities-mcp / platform-mcp-remote-worker"] --> API
  API["liabilities-api (Railway serverless)<br/>/v1/liabilities"] --> AUTH{"Bearer JWT ผ่าน?"}
  AUTH -->|no| E401["401 unauthenticated"]
  AUTH -->|yes| PDP["empire-platform /v1/authz/decide<br/>liabilities.liability:read/write/delete"]
  PDP -->|"deny / platform ล่ม"| E403["403 deny / 503 authorization_unavailable"]
  PDP -->|read| READ["list (limit 1-1000), stats, get, get-by-legacy-id"]
  PDP -->|"create / patch / delete / erase"| TX["transaction เดียว: ตรวจกฎ, เขียน liabilities + outbox 1 แถวต่อ record"]
  TX -->|"ส่ง account_id"| REF{"account_id อยู่ใน ref_targets?<br/>(finance-accounts.account)"}
  REF -->|"ไม่เจอ"| CATCH["refs.sync: catch up จาก Kafka แล้วตรวจซ้ำ"]
  CATCH -->|"ยังไม่เจอ / ถูกลบ / closed / Kafka อ่านไม่ได้"| EREF["422 reference_not_found / reference_closed / 503 references_unavailable"]
  TX -->|ผิดกฎ| E422["422 invalid_value / 428 version_required / 409 conflict"]
  READ --> DB[("Neon liabilities: liabilities, create_keys, outbox,<br/>ref_targets, ref_offsets; RLS ต่อ workspace")]
  TX --> DB
  TX --> EXEC["empire-platform /v1/executions<br/>begin ก่อน commit, finish หลัง commit (row hash)"]
  EXEC --> INLINE["inline relay หลังเขียน (background, best effort)"]
  JOB["platform-jobs-worker 43 * * * * UTC<br/>GitHub Actions relay-outbox.yml"] --> RELAY["liabilities-relay: ส่ง outbox ทุก workspace + catch up refs"]
  INLINE --> KAFKA[["Kafka finance.events.v1<br/>เฉพาะ graph fields"]]
  RELAY --> KAFKA
  KAFKA -->|"event ของ finance-accounts.account"| CATCH
  RELAY --> HB["heartbeat finance-relay-liabilities<br/>(relay fail หรือ backlog เกิน 3 ชม.)"]
  KAFKA --> SINK["data-lake-pipelines event-sink → Bronze"]
```

Sources: `cell.yaml`, `pyproject.toml` (platform-cellkit v1.1.1: `cellkit/app.py`, `cellkit/refs.py`, `cellkit/relay.py`, `cellkit/gateway.py`), `migrations/0001_liabilities.sql`–`0005_cross_references.sql`, `.github/workflows/relay-outbox.yml`, `.railway/railway.ts`, `README.md`, `PRODUCT.md`, `specs/006-cross-service-references/spec.md`

ข้อเท็จจริงสำคัญจากโค้ด:

- โค้ดของ cell มีแค่ `cell.yaml`; route, auth, outbox, refs และ relay มาจาก platform-cellkit v1.1.1 (`src/solo_liabilities/` ว่าง)
- กฎ: `name` (ไม่เกิน 200 ตัว) และ `liability_type` บังคับ; `status` ค่าเริ่มต้น active (planned, active, overdue, settled, cancelled); `principal_amount`, `outstanding_amount`, `minimum_payment` เป็น `money` และ `interest_rate_percent` เป็น `decimal` ติดลบไม่ได้; `currency` ISO 4217 ค่าเริ่มต้น THB; `metadata` เป็น JSON object; PATCH ที่ส่งฟิลด์เงินต้องมี `expected_version` (428, SPEC-009)
- `account_id` (`references: finance-accounts.account`, `refuse_status: [closed]`): create หรือ patch ที่ตั้งค่านี้ถูกตรวจกับสำเนาที่มาจาก event; patch ที่ไม่เปลี่ยนค่าไม่ถูกตรวจซ้ำ (SPEC-006)
- liability ไม่มี `referenced_by`: ลบหรือ erase ได้โดยไม่ต้องรอ cell อื่น; event `deleted` ทำให้ finance-accounts รู้ว่า account ไม่ถูกชี้แล้ว
- event `liabilities.liability.created/updated/deleted` มีเฉพาะ `liability_type`, `scope`, `account_id`, `currency`, `due_date`, `status` (ไม่มียอดเงิน ชื่อ หรือ notes)
- ไม่มีโค้ดเปลี่ยน `status` เป็น overdue เมื่อเลย `due_date`; ผู้เรียกต้องตั้งเอง [ต้องยืนยัน: job หรือคนที่ทำ]
- `POST /v1/liabilities/erase` ต้องมี `confirm` = workspace ของผู้เรียก ลบทีละ 1-500 แถว (ค่าเริ่มต้น 200; SPEC-008)
- การตรวจ `X-Gateway-Assertion` (off/report/enforce), inline relay และ `LIABILITIES_REFS_DATABASE_URL` ขึ้นกับตัวแปรบน Railway [ต้องยืนยัน: ค่าใน production]

## To-Be (จาก `PRODUCT.md` §Measures และ `specs/004-identity-issuer-trust/spec.md`)

- `specs/004-identity-issuer-trust/spec.md`: cell เชื่อ token ของ platform-identity เคียงข้าง empire-platform; โค้ดอยู่ใน kit แล้ว แต่ "production activation needs a separate owner go"
- `PRODUCT.md` §Measures (Proposed, ยังไม่มีอะไรเก็บ): ยอดคงค้างรวมของ liability active และ overdue ต่อสกุลเงิน (dashboard แสดงอยู่แล้ว), จำนวน liability ที่ overdue (เป้า 0), 5xx และ p95 latency ของ `/v1/liabilities`
- `PRODUCT.md` §Product Purpose: อะไรที่เลยกำหนดต้องถูกทำเครื่องหมาย overdue ให้ dashboard แสดง
- `PRODUCT.md` §Capabilities: out of scope = ตารางผ่อน, การคิดดอกเบี้ย และการจ่ายเงินจริง (`finance-transactions-api`)

## Gap

| ID | As-Is → To-Be | Status | Owner | Evidence |
|---|---|---|---|---|
| G1 | รับ token ของ platform-identity ได้ในโค้ด แต่ยังไม่ยืนยันว่าเปิดใน production → owner ตัดสินเปิดใช้ (ตั้ง `LIABILITIES_JWT_IDENTITY_*`) | decide | owner | `specs/004-identity-issuer-trust/spec.md` (Status) |
| G2 | ไม่มีอะไรเก็บ Measures ที่เสนอไว้ → เก็บและรายงานตาม `PRODUCT.md` | decide | owner | `PRODUCT.md` §Measures ("Proposed (nothing collects them yet)") |
| G3 | ไม่มีอะไรตั้ง overdue เมื่อเลย `due_date` → สิ่งที่เลยกำหนดถูกทำเครื่องหมาย overdue | decide | owner | `PRODUCT.md` §Product Purpose และ §Capabilities [ต้องยืนยัน] |

## Open questions

- `PRODUCT.md` §Capabilities ยังเขียนว่า `account_id` "does not check that the account exists" แต่โค้ดวันนี้ (SPEC-006) ตรวจและปฏิเสธ account ที่ไม่มีหรือปิดแล้ว; ควรแก้ `PRODUCT.md`
- `finance-ledger-core` (`book-finance-api`) อ่าน `/v1/liabilities` จริงหรือไม่ (PRODUCT.md ระบุ `[ต้องยืนยัน]`)
- โหมด gateway assertion และ signed events (`LIABILITIES_EVENT_SIGNATURES`) ใน production เป็นค่าใด
