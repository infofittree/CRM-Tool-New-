# FitTree CRM — Project Context

## Overview

FitTree CRM is a sales lead management system built for FitTree's agricultural products sales operations. It manages the full lifecycle from lead capture through procurement inquiry and order closure.

**Domain**: Agricultural products — Spices, Pulses, Grains, Herbs, Plant Seeds, Dry Fruits, Oils.

**Deployed at**: https://crm-fittree.up.railway.app

---

## Architecture

```
Frontend (React SPA)
  web/src/
    ├── pages/              Page components
    ├── components/         Shared components (modals, UI primitives)
    ├── hooks/              Custom React hooks (useDashboard, useLeads, useAnalytics)
    ├── lib/                API client, auth, utilities, inquiries, taskTypes
    └── App.tsx             Router + route guards

Backend (FastAPI)
  sales_lead_system/
    ├── api/main.py         FastAPI entry point + static file serving
    ├── api/routers/        auth, leads, followups, dashboard, users, inquiries, analytics, transfers, products
    ├── api/schemas.py      Pydantic request/response schemas
    ├── api/deps.py         Auth dependencies (get_current_user, require_role)
    ├── database/models.py  SQLAlchemy ORM models
    ├── database/schema_manager.py  Idempotent schema migrations (Phase 2–13)
    ├── database/db_connection.py    PostgreSQL/SQLite connection
    ├── modules/            Business logic (crm_service, task_engine, activity_engine, analytics_engine, dashboard_queries)
    └── config/settings.py  Environment-driven config
```

**Deployment**: Single Railway service. Backend serves both API and frontend static files from `web/dist/`.

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS v4, React Query, Recharts, Lucide icons |
| Backend | Python 3.13, FastAPI, SQLAlchemy, Pydantic v2 |
| Database | PostgreSQL (Railway managed) |
| Auth | JWT (HS256, 8h expiry), PBKDF2-SHA256 password hashing |
| Hosting | Railway (single service: API + SPA) |
| Domain | crm-fittree.up.railway.app |

---

## Database

### Production Database
- **Engine**: PostgreSQL (Railway managed)
- **Connection**: via `DATABASE_URL` env var on Railway
- **Models**: Lead, FollowUp, User, Inquiry, EngagementEvent, ActivityLog, CrmAlert, LeadTransfer, LeadHandover, InquiryRevision, Product, LeadProduct, ErrorLog, OrderTracker

### Schema Migrations (idempotent, auto-run on startup)
Phase 2–9: Legacy column additions, status normalization, soft deletes, scoring
Phase 10: LeadHandover table (transfer system)
Phase 11: Products + LeadProducts tables (19 seeded products)
Phase 12: InquiryRevisions table (negotiation workflow)
Phase 13: Database cleanup (dead columns dropped, redundant indexes removed)
Phase 14: Performance indexes (7 new composite indexes, 1 redundant dropped)

### Key Relationships
- `Lead` → `FollowUp` (one-to-many)
- `Lead` → `LeadProduct` → `Product` (many-to-many)
- `Lead` → `Inquiry` (one-to-many)
- `Lead` → `EngagementEvent` (one-to-many)
- `Lead` → `ActivityLog` (one-to-many)
- `Inquiry` → `InquiryRevision` (one-to-many)
- `Lead` → `LeadHandover` / `LeadTransfer` (audit records)

---

## Authentication & Authorization

### Roles
| Role | Permissions |
|------|------------|
| Admin | Full access to everything |
| Manager | View team data, manage leads, respond to inquiries |
| Salesperson | Own leads only, own tasks, create inquiries |
| Procurement | Receive/respond to inquiries only |

### JWT Auth
- Token stored in `sessionStorage` (browser tab lifecycle)
- 8-hour expiry, HS256 signing
- Auto-logout on 20 minutes inactivity
- `JWT_SECRET_KEY` env var (stable across restarts)

### Auto-Assignment
- Leads auto-assigned to creating user if not specified
- Inquiries auto-assigned to first active Procurement user
- Handovers: request → accept/decline workflow

---

## Core Modules

### 1. Lead Management
- **Model**: 30+ fields including company, contact, status, assigned_to, priority, score, product_interest
- **Status Flow**: Prospect → Requirement Qualified → Technical Discussion → Quotation Sent → Sample Sent → Negotiation → Trial Order → Order Closed / Lost
- **Features**: Search, filter (status/country/priority/assigned/product), pagination, CSV export
- **Product interest**: Text field for free-text product names

### 2. Task System
- **Engine**: `task_engine.py` generates tasks from follow-ups, scoped by `Lead.assigned_to`
- **Task types**: Call Back, Send Quotation, Conduct Meeting, Follow Up, Check Response, Samples, Procurement
- **Task Workflow Modal**: Centered modal with portal rendering, multi-view (details → wizard → success)
- **Activity Wizard**: 4-step guided workflow for recording call/email/meeting outcomes
- **Completion lifecycle**: Task completed → follow-up created → task moved to Completed section

### 3. Inquiry System
- **Model**: `Inquiry` with statuses: OPEN → EOD_COMMITTED/PENDING_RESPONSE → RESPONDED → CLOSED
- **Negotiation**: `InquiryRevision` table tracks revision rounds within a single inquiry
- **Workflow Modal**: Centered modal with details, procurement response form, revision request form
- **Notifications**: WhatsApp via CallMeBot for urgent inquiries

### 4. Lead Transfer (Handover)
- **Model**: `LeadHandover` with PENDING → ACCEPTED/DECLINED flow
- **Workflow**: Request → recipient accepts/declines → ownership transfers
- **On accept**: Lead ownership, follow-ups, inquiries all re-assigned
- **Dashboard widget**: Pending transfers shown for recipient

### 5. Dashboard
- **Role-based views**: Salesperson (own tasks + pipeline), Manager (team overview), Admin (full view), Procurement (inquiry queue)
- **Salesperson Context Filter**: Admin/Manager can switch between "Entire Team" and individual salesperson
- **Widgets**: KPIs, pipeline health, action items, inquiry status, top producers, pending transfers

### 6. Analytics
- Executive summary, conversion funnel, pipeline stages, follow-up discipline
- Activity analytics, team comparison, productivity scores, trends
- CSV export with date range filtering
- Independent from Dashboard filter

### 7. Products
- **Model**: `Product` (name, category, is_active) + `LeadProduct` junction table
- **Catalog**: 19 seeded products across 5 categories (Spices, Pulses, Grains, Herbs, Seeds)
- **Data Entry**: Text field for product_interest on lead creation
- **Filters**: Product filter on Leads page
- **CSV Export**: Product column included

### 8. Database Performance
- **7 composite indexes** added in Phase 14 for query optimization
- **N+1 query fix**: `get_team_comparison()` reduced from 71+ queries to 3 batch queries
- **Full table scan fix**: `get_executive_summary()` now selects only needed columns
- **Index coverage**: `followups.completed_at`, `leads.(deleted_at,assigned_to,updated_at)`, `engagement_events.(lead_id,occurred_at)`, `inquiries.type`, `activity_logs.user_name`

---

## Frontend Pages

| Page | Route | Key Features |
|------|-------|-------------|
| Login | `/login` | JWT auth, auto-logout |
| Dashboard | `/` | Role-based views, context filter, pending transfers |
| Lead Management | `/leads` | Search, 5 filters, pagination, product filter |
| Lead Detail | `/leads/:id` | Full lead info, follow-ups, inquiries, edit, transfer button |
| Tasks | `/tasks` | Day-grouped view, TaskWorkflowModal (portal-based) |
| Data Entry | `/data-entry` | Country autocomplete, product text field, required fields |
| Analytics | `/analytics` | Recharts visualizations, CSV export, independent filter |
| Team | `/team` | Performance scores, team comparison (Admin/Manager only) |
| Inquiries | `/inquiries` | List with InquiryWorkflowModal, create inquiry |
| Settings | `/settings` | User management (Admin only) |

### Modal Architecture (Shared Pattern)
All modals use: `createPortal(content, document.body)` + `<main>` scroll lock + ESC key + centered positioning + `max-h-[85vh]`. Consistent across TaskWorkflowModal, InquiryWorkflowModal, HandoverResponseModal, TransferLeadModal.

---

## Environment Variables

| Variable | Purpose | Source |
|----------|---------|--------|
| `DATABASE_URL` | PostgreSQL connection | Railway auto-injected |
| `JWT_SECRET_KEY` | JWT signing secret | Set on Railway |
| `CORS_ORIGINS` | Allowed origins | `https://crm-fittree.up.railway.app` |
| `DEFAULT_USERS_JSON` | Initial user seeding | JSON array on Railway |
| `WHATSAPP_API_KEY` | CallMeBot WhatsApp | Optional |

---

## Security

- JWT auth with 8h expiry on all API endpoints
- Role-based access control (Admin/Manager/Salesperson/Procurement)
- PBKDF2-SHA256 password hashing (250k iterations)
- BOLA protection on leads and follow-ups
- CORS restricted to production domain
- Security headers: X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy
- Soft delete pattern for leads
- Audit logging via ActivityLog
- No hardcoded secrets in source code

---

## How To Run

**Backend:**
```bash
cd sales_lead_system
uvicorn api.main:app --reload --port 8000
```

**Frontend:**
```bash
cd web
VITE_API_URL=/api/v1 npm run dev
```

Open `http://localhost:5173` → Login with credentials from `DEFAULT_USERS_JSON` env var.

---

## Git & Deployment

- **Repo**: `infofittree/CRM-Tool-New-` on GitHub
- **Branch**: `main` (single branch workflow)
- **Deploy**: Push to main → Railway auto-deploys
- **web/dist/**: Must be committed (Railway has no Node.js buildpack)
- **Database password**: Rotated 2026-06-29. Old password compromised in git history. New password in Railway `DATABASE_URL` env var only.

---

## Users (8 active)

| Username | Role | Full Name |
|----------|------|-----------|
| yashsharma | Admin | Yash Sharma |
| shiksha | Admin | Shiksha |
| maruti | Admin | Maruti |
| poonam | Manager | Poonam |
| vaidehi | Salesperson | Vaidehi |
| rahul | Salesperson | Rahul |
| kusum | Salesperson | Kusum |
| vivek | Procurement | Vivek |

---

## Issues & Fixes

See `ISSUES.md` for a complete log of all issues encountered and resolved during development.
