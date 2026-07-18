# FitTree CRM — Deployment Guide

## Quick Start (Local)

### 1. Install Dependencies
```bash
# Backend
pip install -r requirements.txt

# Frontend
cd web && npm install
```

### 2. Configure Environment
```bash
cp sales_lead_system/config/.env.example sales_lead_system/config/.env
# Edit .env with your settings
```

### 3. Start Servers
```bash
# Terminal 1: Backend
cd sales_lead_system
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Frontend (dev mode)
cd web
npm run dev
```

### 4. Access
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Production Deployment

### Option A: VPS / Server

1. Clone the repository
2. Install Python 3.11+ and Node.js 18+
3. Configure `.env` with production values
4. Build frontend: `cd web && npm run build`
5. Serve frontend from `web/dist/` using Nginx or similar
6. Run backend with Gunicorn: `gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000`

### Option B: Docker

```dockerfile
# Backend
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY sales_lead_system/ ./sales_lead_system/
EXPOSE 8000
CMD ["uvicorn", "sales_lead_system.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Option C: Railway / Render / Fly.io

1. Push to GitHub
2. Connect repository
3. Set environment variables
4. Deploy

---

## Default Users

Default users are seeded from the `DEFAULT_USERS_JSON` Railway env var
on first boot, in the format:

```json
[["username", "password", "Full Name", "Admin"], ...]
```

**Rotate every password before first use.** Plain-text default passwords
must not be committed to version control or shared in documentation.
Manage users in production through the in-app Settings page or via the
`POST /api/v1/users` endpoint (Admin role only).

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| USE_SQLITE | Yes | true | Use SQLite (true) or MySQL (false) |
| SQLITE_DB_PATH | If SQLite | - | Path to SQLite database |
| MYSQL_HOST | If MySQL | - | MySQL host |
| MYSQL_PORT | If MySQL | 3306 | MySQL port |
| MYSQL_USER | If MySQL | - | MySQL username |
| MYSQL_PASSWORD | If MySQL | - | MySQL password |
| MYSQL_DATABASE | If MySQL | - | MySQL database name |
| JWT_SECRET_KEY | No | random | JWT signing key |
| CORS_ORIGINS | No | http://localhost:5173 | Allowed origins |
| WHATSAPP_API_KEY | No | - | CallMeBot API key |
| CRM_ADMIN_USER | No | - | Default admin username |
| CRM_ADMIN_PASSWORD | No | - | Default admin password |

---

## Database

The application uses SQLite by default. The database file is at:
```
sales_lead_system/config/.env → SQLITE_DB_PATH
```

For MySQL, set `USE_SQLITE=false` and configure MySQL variables.

---

## API Endpoints

### Auth
- POST /api/v1/auth/login
- GET /api/v1/auth/me

### Dashboard
- GET /api/v1/dashboard/counts
- GET /api/v1/dashboard/leads
- GET /api/v1/dashboard/pipeline-health
- GET /api/v1/dashboard/salesperson-stats

### Leads
- GET /api/v1/leads
- GET /api/v1/leads/search
- POST /api/v1/leads
- PUT /api/v1/leads/{id}
- DELETE /api/v1/leads/{id}

### Follow-ups
- GET /api/v1/followups/tasks
- POST /api/v1/followups
- PATCH /api/v1/followups/{id}/complete

### Analytics
- GET /api/v1/analytics/executive-summary
- GET /api/v1/analytics/conversion-funnel
- GET /api/v1/analytics/pipeline-stages
- GET /api/v1/analytics/followup-discipline
- GET /api/v1/analytics/activity-analytics
- GET /api/v1/analytics/trends
- GET /api/v1/analytics/productivity
- GET /api/v1/analytics/team-comparison

### Users
- GET /api/v1/users
- POST /api/v1/users
- DELETE /api/v1/users/{username}

### Inquiries
- GET /api/v1/inquiries
- POST /api/v1/inquiries
- PUT /api/v1/inquiries/{id}
- POST /api/v1/inquiries/{id}/commit
