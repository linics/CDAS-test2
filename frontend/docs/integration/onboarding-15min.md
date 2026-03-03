# Onboarding in 15 Minutes

## Canonical Repositories

- Frontend: `D:\githubfiles\CDAS-test2\CDAS-test2\frontend`
- Backend: `D:\githubfiles\CDAS-test2\CDAS-test2`

## 1) Backend setup (about 5 min)

```bash
cd D:\githubfiles\CDAS-test2\CDAS-test2
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Start backend:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Health check:

- `http://127.0.0.1:8000/health`

## 2) Frontend setup (about 5 min)

```bash
cd D:\githubfiles\CDAS-test2\CDAS-test2\frontend
npm install
copy .env.example .env
npm run dev:local
```

Frontend URL:

- `http://127.0.0.1:5173`

## 3) Baseline verification (about 5 min)

Frontend repo:

```bash
npm run check:all
```

Backend repo:

```bash
python scripts/check_backend_quality.py
```

After regression run cleanup (backend repo):

```bash
python scripts/clean_integration_artifacts.py
```

## Notes

- Legacy standalone frontend path `D:\githubfiles\cdas-frontend-main` is reference-only.
- Primary integration docs are in `frontend/docs/integration/`.
