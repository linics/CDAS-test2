# CDAS Frontend (Canonical)

## Repository Role

This directory is the canonical frontend source for CDAS integration work.

- Canonical frontend: `D:\githubfiles\CDAS-test2\CDAS-test2\frontend`
- Canonical backend: `D:\githubfiles\CDAS-test2\CDAS-test2`
- Legacy standalone frontend (reference only): `D:\githubfiles\cdas-frontend-main`

## Local Development

### 1) Install dependencies

```bash
npm install
```

Optional environment setup:

```bash
copy .env.example .env
```

### 2) Start frontend

```bash
npm run dev:local
```

Frontend URL: `http://127.0.0.1:5173`

### 3) Ensure backend is running

Backend URL: `http://127.0.0.1:8000`

Backend `.env` template is available at:

- `D:\githubfiles\CDAS-test2\CDAS-test2\.env.example`

## Quality Baseline Commands

Run these before handoff:

```bash
npm run check:build
npm run check:api-e2e
```

Or run both:

```bash
npm run check:all
```

## Integration Docs

- Phase plan: `docs/integration/phase-plan.md`
- Verification log: `docs/integration/verification-log.md`
- Normalization plan: `docs/integration/normalization-plan-2weeks.md`
- Repo governance: `docs/integration/repo-governance.md`
- API governance: `docs/integration/api-contract-governance.md`
- Backend quality baseline: `docs/integration/backend-quality-baseline.md`
- 15-minute onboarding: `docs/integration/onboarding-15min.md`
