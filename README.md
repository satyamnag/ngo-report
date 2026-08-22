# NGO Report Studio

Generate, edit and export NGO annual reports from Word templates.

A customer fills a **dynamic form** (driven by the template's `schema.json`),
the backend renders the `.docx` template with **docxtpl**, swaps placeholder
images, converts to **PDF via LibreOffice**, and the customer can preview,
**edit sections in TipTap**, rebuild, and download `.docx` / `.pdf`.

## High-level architecture

```
Browser (Next.js web app)
   ├── TipTap editor (edit sections)
   ├── Dynamic form (driven by template schema)
   └── Downloads (.docx / .pdf / HTML preview)
            │
            ▼
   FastAPI backend ── Celery worker (Redis)
     │  ├─ docxtpl + python-docx  → editable .docx
     │  ├─ LibreOffice headless   → .pdf
     │  └─ mammoth                → HTML preview
     ├─ PostgreSQL 16 (users, orgs, templates, projects, sections, assets, generations, audit)
     └─ Object storage (MinIO or local FS): templates, generated files, images
```

## Repository layout

```
apps/api            FastAPI backend + Celery worker (Python 3.12)
apps/web            Next.js 15 frontend (React 19, TypeScript, TipTap 3)
infra/nginx         nginx reverse proxy config
templates/          bundled sample NGO report template (.docx + schema.json + images)
docker-compose.yml  full production stack (nextjs, api, celery, redis, postgres, minio, nginx)
```

## Local development (no Docker required)

Requirements: Python 3.12, PostgreSQL 16 running, Redis running, LibreOffice.

```bash
# 1. Database role/db (once)
sudo -u postgres psql -c "CREATE ROLE ngo_app LOGIN PASSWORD 'ngo_app_dev_password';"
sudo -u postgres createdb -O ngo_app ngo_report

# 2. Python deps
python3.12 -m venv .venv
.venv/bin/pip install -r apps/api/requirements.txt

# 3. API (creates tables + seeds demo user + sample template on startup)
cd apps/api && ../.venv/bin/uvicorn app.main:app --reload --port 8000

# 4. Celery worker (in another shell)
cd apps/api && ../.venv/bin/celery -A app.celery_app worker --loglevel=info

# 5. Frontend (Node 22+)
cd apps/web && npm install && npm run dev   # http://localhost:3000
```

Demo login: `demo@brightpath.org` / `demo-password-123`.

Object storage defaults to a local folder (`data/storage`). Set `STORAGE_BACKEND=minio`
and `MINIO_*` env vars to use MinIO/S3.

## Docker deployment (single VPS)

```bash
cp .env.example .env            # set POSTGRES_PASSWORD, JWT_SECRET, MINIO keys
docker compose up -d --build    # nginx on :80
```

## Core flow

1. `POST /api/projects` → create project from a template.
2. `PUT /api/projects/:id/details` → save form input (validated by the schema).
3. `POST /api/projects/:id/generate` → enqueue Celery job: docxtpl render →
   image-marker swap → save `.docx` → LibreOffice `.pdf`.
4. `GET /api/projects/:id/report` → HTML preview (mammoth).
5. `PUT /api/projects/:id/sections/:key` → edit a section in TipTap.
6. `POST /api/projects/:id/rebuild` → regenerate with edited sections folded in.
7. `GET /api/projects/:id/download?format=docx|pdf` → download.

## Template authoring

A template is a `.docx` (built in Word/Google Docs) plus a `schema.json` that
drives the dynamic customer form.

- Text placeholders use jinja2 syntax: `{{ org_name }}`, `{{ financial.total }}`
  (nested values supported).
- Image placeholders use `[img:name]` markers, e.g. `[img:logo]`,
  `[img:chart_funding]`. At render time they are replaced with the customer's
  uploaded image, or the template's bundled default.
- `schema.json` shape:

```json
{
  "title": "NGO Annual Report",
  "sections": [{ "key": "mission", "label": "Mission", "sort": 1 }],
  "section_map": { "mission": "mission.statement" },
  "fields": [
    {
      "group": "Cover",
      "fields": [
        { "name": "org_name", "label": "Organization name", "type": "text",
          "path": "org_name", "required": true },
        { "name": "logo", "label": "Logo image", "type": "image",
          "path": "logo", "placeholder": "logo" }
      ]
    }
  ]
}
```

## API surface

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/api/auth/register` `/api/auth/login` | JWT auth (Argon2) |
| GET | `/api/templates` `/api/templates/:id/schema` | template list / form schema |
| POST | `/api/templates` | upload + validate new `.docx` template |
| POST | `/api/projects` | create project |
| PUT | `/api/projects/:id/details` | save customer-entered details |
| POST | `/api/projects/:id/generate` | enqueue generation job |
| POST | `/api/projects/:id/rebuild` | regenerate with edited sections |
| GET | `/api/projects/:id/download?format=docx\|pdf` | download artifacts |
| GET | `/api/projects/:id/report` | HTML preview |
| PUT | `/api/projects/:id/sections/:key` | edit section (TipTap HTML) |
| POST | `/api/projects/:id/assets` | upload/replace placeholder images |
| GET | `/api/projects/:id/audit` | audit trail |

Swagger UI: `http://localhost:8000/api/docs`

## Security baseline

- Argon2 password hashing (pwdlib), JWT access + refresh tokens.
- Uploaded files validated by MIME type and size; stored under random server-generated
  keys — user filenames are never used as object keys.
- `docxtpl` never executes macros; rendering runs in a sandboxed worker (no network).
- Secrets injected via environment only; `.env` is gitignored.
- Audit log on every register/login/generate/edit/download.
- Pydantic strict schemas + rate-limit-friendly input length caps.

## Tests

```bash
cd apps/api && CELERY_TASK_EAGER=true ../.venv/bin/python -m pytest tests -q
```