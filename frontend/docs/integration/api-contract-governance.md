# API Contract Governance (`/api/v2`)

## Purpose

Define contract rules for backend APIs consumed by `CDAS-test2/CDAS-test2/frontend` to keep integration stable during ongoing feature delivery.

## Scope

- Backend runtime: `D:\githubfiles\CDAS-test2\CDAS-test2`
- Frontend consumer: `D:\githubfiles\CDAS-test2\CDAS-test2\frontend`
- Governed API namespace: `/api/v2/*`

## Stability Policy

- `/api/v2` is treated as a stable integration contract.
- Default policy is non-breaking, additive evolution.
- Breaking changes require explicit approval and migration notes before merge.

## Contract Conventions

- **JSON naming**: snake_case for request/response fields.
- **Identifiers**: numeric `id` fields are stable and immutable.
- **Datetime**: ISO 8601 string (UTC-aware where available).
- **Enums**: fixed string values (do not rename existing enum values in-place).
- **List endpoints**: keep current envelope style (resource list + `total`) where already used.

## Error Contract

- Baseline error payload follows FastAPI default:
  - `{"detail": "..."}`
- Status semantics:
  - `400`: invalid request/data state
  - `401`: authentication required or token invalid
  - `403`: authenticated but forbidden
  - `404`: resource not found
  - `409`: conflict (when introduced)
  - `422`: request validation failure
  - `500`: server-side fault
- If richer error fields are introduced later, they must be additive and must preserve `detail`.

## Allowed vs Disallowed Changes

Allowed (non-breaking):

- Add new endpoint under `/api/v2`.
- Add new optional request field.
- Add new optional response field.
- Add new enum value only when frontend fallback behavior is documented.

Disallowed (breaking without migration process):

- Remove or rename existing endpoint.
- Remove or rename existing response field.
- Change data type of existing field.
- Change existing enum value semantics in-place.
- Change auth/permission behavior without release notes.

## Change Process

For every API-impacting PR:

1. Update mapping doc: `docs/integration/api-mapping.md`.
2. Include compatibility note (breaking/non-breaking).
3. Run regression:
   - `python scripts/run_api_e2e.py` (frontend repo)
   - `python scripts/check_backend_quality.py` (backend repo)
4. If breaking, include migration strategy and rollout sequence.

## Frontend Consumer Rules

- Frontend must tolerate unknown response fields.
- Frontend should use defensive defaults for optional fields.
- Error UI should continue to rely on `detail` as primary message source.

## Current Day-4 Baseline Verification

- OpenAPI endpoint reachable: `GET /openapi.json`
- `/api/v2` paths detected in runtime spec: 39
- Baseline checks pass:
  - `python scripts/check_backend_quality.py`
  - `python scripts/run_api_e2e.py`
