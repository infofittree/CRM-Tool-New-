# FitTree CRM — Project Context

## Overview

A CRM system for managing sales leads, follow-ups, team performance, and analytics. Built for FitTree's sales operations with 359 leads and 5 sales team members.

---

## Architecture

```
web/                          React SPA (Vite + React 19 + TypeScript + Tailwind v4)
  └─ src/
      ├─ pages/              12 pages (all built)
      ├─ components/ui/      3 base components (Button, Card, Input)
      ├─ hooks/              2 hook files (useDashboard, useLeads)
      ├─ lib/                API client (Axios), Auth context, Utils
      └─ App.tsx             Router with all routes

sales_lead_system/
  ├─ api/                    FastAPI backend (port 8000)
  │   └─ routers/            auth, leads, followups, dashboard, users
  ├─ app/                    (Legacy Streamlit — no longer used)
  ├─ database/               SQLAlchemy models, migrations, connection
  ├─ modules/                Business logic (scoring, task engine, CRM service)
  └─ config/                 .env, settings, dropdown configs
```

### Data Flow
```
Browser → Vite (port 5173) → proxy /api → FastAPI (port 8000) → SQLAlchemy → SQLite/MySQL
```

---

## Current Status — All Pages Built

| Page | Route | Status | Data Source |
|---|---|---|---|
| Login | `/login` | ✅ Done | POST /auth/login |
| Dashboard | `/` | ✅ Done | 5 API endpoints (counts, tasks, engagement, team stats, activities) |
| Lead Management | `/leads` | ✅ Done | GET /leads (search, filter, paginate 25/page) |
| Lead Detail | `/leads/:id` | ✅ Done | GET /leads/:id, GET /leads/:id/followups |
| Tasks | `/tasks` | ✅ Done | GET /followups/tasks (Today/Overdue/Upcoming tabs) |
| Data Entry | `/data-entry` | ✅ Done | POST /leads (create form) |
| Analytics | `/analytics` | ✅ Done | Recharts (status pie, source bar, country bar) |
| Team | `/team` | ✅ Done | GET /dashboard/salesperson-stats (leaderboard) |
| Reports | `/reports` | ✅ Done | CSV export, summary stats |
| Nurturing | `/nurturing` | ✅ Done | Filtered leads list |
| Weekly Review | `/weekly-review` | ✅ Done | Per-status pipeline counts with date range |
| My Workspace | `/workspace` | ✅ Done | User-scoped assigned leads |
| Settings | `/settings` | ✅ Done | User list (add user coming) |

### Database
- **Primary**: SQLite (existing `.db` file with 359 leads, 68 followups)
- **Alternative**: MySQL (configurable via `.env`)
- **Migrations**: Schema manager auto-runs on startup (Phase 2–7)
- **Bootstrap**: Admin user seeded on first run (`admin` / `admin123`)

### API Health
- All REST endpoints return 200 OK with real data
- JWT auth (8h expiry, HS256)
- Role-based access (Admin/Manager/Salesperson)
- Leads: search/filter/paginate/create/update/delete/transfer/reschedule
- Tasks: 20 today + 202 overdue + 0 upcoming

---

## How To Run

**Terminal 1 — Backend:**
```powershell
cd sales_lead_system
uvicorn api.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```powershell
cd web
npm run dev
```

Open `http://localhost:5173` → Login with `admin` / `admin123`

---

## Known Issues / Next Steps

1. **Engagement stats show zeros** — no engagement_events in DB; needs data or seeding
2. **Settings page** — "Add User" button is disabled (POST /users not wired in form yet)
3. **No delete lead from detail page** — DELETE endpoint exists but not wired in UI
4. **No edit lead from detail page** — PUT endpoint exists but not wired in UI
5. **Dashboard score band** — uses `score` field from tasks API (was previously mismatched as `lead_score`)
6. **Some Radix UI + recharts packages unused** — installed but only recharts is used now
7. **No mobile sidebar collapse** — sidebar is fixed 256px
8. **No toast notifications** — success/error feedback uses inline text
