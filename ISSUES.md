# Issues Faced & Tackled — FitTree CRM

A chronological record of every issue encountered during development and the fix applied.

---

## 1. Backend 500 Error on Complete Task

**Date**: 2026-06-29  
**Symptom**: Clicking "Complete Task" returned `Internal server error` (500).  
**Root Cause**: `crud.py:add_followup()` was missing `session.flush()` after `session.add(followup)`. The auto-incremented `followup_id` was `None` when the `FollowUpResponse` Pydantic model tried to validate it.  
**Fix**: Added `session.flush()` after `session.add(followup)` in `crud.py`.  
**Files**: `sales_lead_system/database/crud.py`

---

## 2. Data Entry Form Missing Required Fields

**Date**: 2026-06-29  
**Symptom**: Creating a lead via Data Entry returned 400 with 5 validation errors.  
**Root Cause**: The React DataEntry form was missing fields that the backend required: `contact_person` (required), `lead_source` (required), `lead_category` (required), `next_action_plan` (required), `next_follow_up` (required). The form also had no `product_interest` field.  
**Fix**: Added all required fields to the form with validation. Added `product_interest` text field.  
**Files**: `web/src/pages/DataEntry.tsx`, `sales_lead_system/api/schemas.py` (added `product_ids` to `LeadCreate`), `sales_lead_system/api/routers/leads.py` (auto-assign `assigned_to`)

---

## 3. Gray Overlay/Block on Inquiry Modal

**Date**: 2026-06-29  
**Symptom**: Opening an inquiry showed a gray rectangular block instead of a smooth backdrop.  
**Root Cause**: The `InquiryWorkflowModal` was missing the `<main>` scroll lock that `TaskWorkflowModal` had. Without it, the page scrolled freely behind the semi-transparent `bg-black/25` backdrop, creating visible content behind the overlay.  
**Fix**: Added the same `overflow: hidden` / scrollTop save-restore pattern for `<main>` that TaskWorkflowModal uses.  
**Files**: `web/src/components/InquiryWorkflowModal.tsx`

---

## 4. Inquiry Creation Button Not Visible for Admin/Manager

**Date**: 2026-06-29  
**Symptom**: Admin and Manager users could not see the "New Inquiry" button.  
**Root Cause**: The variable `isProc` was defined as `Admin || Manager || Procurement`. The button condition `!isProc` therefore excluded Admin and Manager.  
**Fix**: Changed condition from `!isProc` to `user?.role !== "Procurement"`.  
**Files**: `web/src/pages/InquiryPortal.tsx`

---

## 5. Lead Transfer Recipients Not Visible for Salespersons

**Date**: 2026-06-29  
**Symptom**: When Rahul (Salesperson) clicked "Transfer Lead", no recipients were shown in the dropdown.  
**Root Cause**: The TransferLeadModal fetched users from `GET /users`, which requires Admin/Manager role. Salespersons got 403.  
**Fix**: Added `GET /users/transfer-recipients` endpoint accessible to any authenticated user. Updated TransferLeadModal to use this new endpoint.  
**Files**: `sales_lead_system/api/routers/users.py`, `web/src/components/TransferLeadModal.tsx`

---

## 6. Railway Backend Crash — Missing Import

**Date**: 2026-06-30  
**Symptom**: Backend crashed on startup with `NameError: name 'status' is not defined`.  
**Root Cause**: The new revision endpoints in `inquiries.py` used `status.HTTP_201_CREATED` but the `status` module was not imported from FastAPI.  
**Fix**: Added `status` to the FastAPI import line.  
**Files**: `sales_lead_system/api/routers/inquiries.py`

---

## 7. PostgreSQL Table Creation Failures

**Date**: 2026-06-30  
**Symptom**: `products` and `inquiry_revisions` tables returned 500 errors — tables didn't exist.  
**Root Cause**: Multi-part issue:
1. Migration SQL used `INTEGER PRIMARY KEY AUTOINCREMENT` (SQLite syntax) on PostgreSQL — should be `SERIAL PRIMARY KEY`
2. `Base.metadata.create_all()` created `products` table but without seed data, then `ensure_phase11_schema` skipped because the table already existed
3. `LeadProduct` had `ForeignKey("leads.lead_id")` but `leads.lead_id` lacks a UNIQUE constraint — PostgreSQL rejects FKs to non-unique columns
4. Seed INSERT didn't include `is_active` column — PostgreSQL NOT NULL constraint rejected it

**Fix**: 
- Added `_is_postgres()` helper for dialect detection
- Branch SQL: PostgreSQL uses `SERIAL PRIMARY KEY`, SQLite uses `INTEGER PRIMARY KEY AUTOINCREMENT`
- Removed FK constraints from `LeadProduct` junction table
- Added separate seed block that checks `COUNT(*) = 0` after table creation
- Added `is_active = TRUE` to INSERT statements

**Files**: `sales_lead_system/database/schema_manager.py`, `sales_lead_system/database/models.py`

---

## 8. Schema Manager Catastrophic Overwrite

**Date**: 2026-06-30  
**Symptom**: After editing `schema_manager.py`, the entire file was replaced with only Phase 11 and Phase 12 functions (98 lines instead of 600+). All Phase 2-10 migrations and helper functions were lost.  
**Root Cause**: The `write` tool was used instead of `edit` for a targeted change. `write` replaces the entire file content.  
**Fix**: Restored from git using `git checkout b751231 -- sales_lead_system/database/schema_manager.py`.  
**Lesson**: Always use `edit` for surgical changes on existing files. Only use `write` for brand new files.

---

## 9. Task Completion Tasks Remaining in Active Queue

**Date**: 2026-06-29  
**Symptom**: After completing a task via the Activity Wizard, the task still appeared in the Today/Overdue/Upcoming sections.  
**Root Cause**: The task engine's completion check only examined the LATEST follow-up per lead (`MAX(followup_id)`). When the wizard completed follow-up N and created N+1, the engine saw N+1 (not completed) and generated an active task — making it look like the old task wasn't completed.  
**Fix**: Added a secondary query in `task_engine.py` that finds recently completed follow-ups (within 7 days) that are NOT the latest, and adds them to the completed bucket.  
**Files**: `sales_lead_system/modules/task_engine.py`

---

## 10. Task Modal Gray Block (Portal Issue)

**Date**: 2026-06-29  
**Symptom**: Opening a task showed a gray block behind the modal instead of a clean backdrop.  
**Root Cause**: The `TaskWorkflowModal` was NOT rendering via portal to `document.body`. It was rendered inside the page's scroll container (`<main>` with `overflow-y-auto`). The `position: fixed` backdrop was inside a scrollable parent, creating layout artifacts.  
**Fix**: Used `createPortal(content, document.body)` to render the modal outside the page DOM tree. Also locked `<main>` scroll (the real scroll container — body never scrolls due to `h-screen overflow-hidden` on the root).  
**Files**: `web/src/components/TaskWorkflowModal.tsx`

---

## 11. Task Modal Scroll Position Not Preserved

**Date**: 2026-06-29  
**Symptom**: After closing the task modal, the page scrolled back to the top.  
**Root Cause**: The initial scroll lock used `document.body.style.overflow = "hidden"`, but body never scrolls — `<main>` does.  
**Fix**: Changed to save `<main>` scrollTop, set `overflow: hidden`, restore on unmount.  
**Files**: `web/src/components/TaskWorkflowModal.tsx`

---

## 12. Inquiry Revision Form Too Complex

**Date**: 2026-06-30  
**Symptom**: The revision request form had 6 structured fields + dropdown + textarea — too complex for sales users.  
**Root Cause**: Over-engineered form with fields like Target Price, Quantity, Packaging, Delivery Timeline, Payment Terms.  
**Fix**: Simplified to just two textareas: "What did the customer say?" and "What do you need from procurement?"  
**Files**: `web/src/components/InquiryWorkflowModal.tsx`

---

## 13. Product System Not Functional

**Date**: 2026-06-30  
**Symptom**: Products endpoint returned 500, lead creation with products failed.  
**Root Cause**: Three-layer failure:
1. `INTEGER PRIMARY KEY AUTOINCREMENT` (SQLite syntax) used on PostgreSQL
2. `Base.metadata.create_all()` created table without seed data, then migration skipped
3. `LeadProduct` had foreign key to non-unique column on PostgreSQL
4. Seed INSERT missing `is_active` column

**Fix**: Added PostgreSQL dialect detection, branched SQL, removed FK constraints, added separate seed block.  
**Files**: `sales_lead_system/database/schema_manager.py`, `sales_lead_system/database/models.py`

---

## 14. Product Chip Selector Replaced with Text Input

**Date**: 2026-06-30  
**Symptom**: User wanted a simple text field for products, not a chip/tag multi-select.  
**Root Cause**: Initial implementation used a multi-select chip UI.  
**Fix**: Replaced with plain text input bound to `product_interest` field.  
**Files**: `web/src/pages/DataEntry.tsx`

---

## 15. Country Field Not Searchable

**Date**: 2026-06-30  
**Symptom**: Country field was a plain text input with no suggestions.  
**Root Cause**: FormField component used for all text fields without autocomplete.  
**Fix**: Replaced with inline autocomplete component — 79 countries, client-side filtering, free-text fallback.  
**Files**: `web/src/pages/DataEntry.tsx`

---

## 16. Dashboard Context Filter 404 Error

**Date**: 2026-06-30  
**Symptom**: Selecting a salesperson on the Dashboard caused 404 errors from analytics endpoints.  
**Root Cause**: The `_resolve_salesperson_user` and `_resolve_user` functions queried `User.role == "Salesperson"`, rejecting Admin/Manager users. When an Admin selected another Admin from the dropdown, the lookup found no matching Salesperson-role user.  
**Fix**: Removed `role == "Salesperson"` filter from both resolver functions. Now any active user can be selected.  
**Files**: `sales_lead_system/api/routers/dashboard.py`, `sales_lead_system/api/routers/analytics.py`

---

## 17. Inquiry Revision Request Crash

**Date**: 2026-06-30  
**Symptom**: Backend crashed on startup — `NameError: name 'status' is not defined` in inquiries.py.  
**Root Cause**: New revision endpoints used `status.HTTP_201_CREATED` but `status` wasn't imported from FastAPI.  
**Fix**: Added `status` to the FastAPI import line.  
**Files**: `sales_lead_system/api/routers/inquiries.py`

---

## 18. PostgreSQL Table Creation Failures

**Date**: 2026-06-30  
**Symptom**: `products` table returned 500 — table didn't exist despite migration code.  
**Root Cause**: Multi-part:
1. Migration used SQLite-specific `INTEGER PRIMARY KEY AUTOINCREMENT`
2. `Base.metadata.create_all()` created table first, migration skipped
3. Seed data not inserted because table already existed
4. Seed INSERT missing `is_active` column for PostgreSQL NOT NULL constraint
5. `LeadProduct` had ForeignKey to non-unique `leads.lead_id`

**Fix**: PostgreSQL dialect detection, `SERIAL PRIMARY KEY`, removed FK constraints, separate seed block with `COUNT(*) = 0` check.  
**Files**: `sales_lead_system/database/schema_manager.py`, `sales_lead_system/database/models.py`

---

## 19. Schema Manager Catastrophic Overwrite

**Date**: 2026-06-30  
**Symptom**: `schema_manager.py` reduced from 600+ lines to 98 lines — all Phase 2-10 migrations lost.  
**Root Cause**: Used `write` tool instead of `edit` for a targeted change. `write` replaces entire file content.  
**Fix**: Restored from git: `git checkout b751231 -- schema_manager.py`  
**Lesson**: Always use `edit` for surgical changes. Only `write` for new files.

---

## 20. Task Engine Completed Tasks Not Visible

**Date**: 2026-06-29  
**Symptom**: Completed tasks appeared in active queue instead of Completed section.  
**Root Cause**: Task engine only checked `MAX(followup_id)` per lead. When wizard completed follow-up N and created N+1, the engine saw N+1 (active) as the latest — old completed task invisible.  
**Fix**: Added secondary query to find recently completed follow-ups (within 7 days) that are NOT the latest, and add them to the completed bucket.  
**Files**: `sales_lead_system/modules/task_engine.py`

---

## 21. Task Modal Gray Block

**Date**: 2026-06-29  
**Symptom**: Gray rectangle appeared behind the task modal instead of clean backdrop.  
**Root Cause**: Modal rendered inside `<main>` scroll container, not via portal. `position: fixed` inside scrollable parent created layout artifacts.  
**Fix**: `createPortal(content, document.body)` + `<main>` scroll lock (save/restore scrollTop).  
**Files**: `web/src/components/TaskWorkflowModal.tsx`

---

## 22. Task Modal Page Scroll Jump

**Date**: 2026-06-29  
**Symptom**: Page scrolled to top when modal opened/closed.  
**Root Cause**: Scroll lock targeted `document.body` but body never scrolls — `<main>` does.  
**Fix**: Save `<main>` scrollTop, set `overflow: hidden`, restore on unmount.  
**Files**: `web/src/components/TaskWorkflowModal.tsx`

---

## 23. Product Chip Selector UX Issue

**Date**: 2026-06-30  
**Symptom**: Multi-select chip UI was complex for sales users.  
**Root Cause**: Initial design used chip/tag selector with category labels.  
**Fix**: Replaced with plain text input — users type comma-separated product names.  
**Files**: `web/src/pages/DataEntry.tsx`

---

## 24. Country Field Not Searchable

**Date**: 2026-06-30  
**Symptom**: Country field was plain text with no suggestions.  
**Root Cause**: Used generic FormField component without autocomplete.  
**Fix**: Inline autocomplete with 79 countries, client-side filtering, free-text fallback.  
**Files**: `web/src/pages/DataEntry.tsx`

---

## 25. Dashboard Context Filter 404

**Date**: 2026-06-30  
**Symptom**: Selecting a salesperson on Dashboard caused 404 errors.  
**Root Cause**: `_resolve_salesperson_user` and `_resolve_user` filtered by `User.role == "Salesperson"`, rejecting Admin/Manager selections.  
**Fix**: Removed role filter — any active user can now be selected.  
**Files**: `sales_lead_system/api/routers/dashboard.py`, `sales_lead_system/api/routers/analytics.py`

---

## 26. Backend Crash — Missing Import

**Date**: 2026-06-30  
**Symptom**: Backend crashed on startup with `NameError: status not defined`.  
**Root Cause**: New revision endpoints in `inquiries.py` used `status.HTTP_201_CREATED` without importing `status` from FastAPI.  
**Fix**: Added `status` to FastAPI import line.  
**Files**: `sales_lead_system/api/routers/inquiries.py`

---

## 27. PostgreSQL Migration Failures (Multiple)

**Date**: 2026-06-30  
**Symptom**: `products` and `inquiry_revisions` tables didn't exist despite migration code.  
**Root Causes**:
1. `INTEGER PRIMARY KEY AUTOINCREMENT` — SQLite syntax on PostgreSQL
2. `Base.metadata.create_all()` created table first, migration skipped  
3. `LeadProduct` FK to non-unique `leads.lead_id`
4. Seed INSERT missing `is_active` column for PostgreSQL NOT NULL
5. Seed data not inserted because table already existed

**Fix**: PostgreSQL dialect detection, `SERIAL PRIMARY KEY`, removed FK constraints, separate seed block with `COUNT(*) = 0` check, added `is_active = TRUE` to INSERT.  
**Files**: `sales_lead_system/database/schema_manager.py`, `sales_lead_system/database/models.py`

---

## 28. Schema Manager Catastrophic Overwrite

**Date**: 2026-06-30  
**Symptom**: `schema_manager.py` reduced from 600+ lines to 98 — all Phase 2-10 migrations lost.  
**Root Cause**: `write` tool used instead of `edit`. `write` replaces entire file content.  
**Fix**: Restored from git: `git checkout b751231 -- schema_manager.py`  
**Lesson**: Always use `edit` for surgical changes on existing files.

---

## 29. Task Engine Completed Tasks Not Visible

**Date**: 2026-06-29  
**Symptom**: Completed tasks appeared in active queue.  
**Root Cause**: Task engine only checked `MAX(followup_id)` per lead. New follow-up after completion became the "latest" and had no `completed_at`.  
**Fix**: Added secondary query for recently completed follow-ups that are NOT the latest.  
**Files**: `sales_lead_system/modules/task_engine.py`

---

## 30. Task Modal Portal Issue

**Date**: 2026-06-29  
**Symptom**: Gray block behind task modal.  
**Root Cause**: Modal rendered inside `<main>` scroll container, not via portal.  
**Fix**: `createPortal(content, document.body)` + `<main>` scroll lock.  
**Files**: `web/src/components/TaskWorkflowModal.tsx`

---

## 31. Task Modal Scroll Jump

**Date**: 2026-06-29  
**Symptom**: Page scrolled to top when modal opened.  
**Root Cause**: Scroll lock targeted `document.body` (never scrolls) instead of `<main>` (actual scroll container).  
**Fix**: Save `<main>` scrollTop, set `overflow: hidden`, restore on unmount.  
**Files**: `web/src/components/TaskWorkflowModal.tsx`

---

## 32. Database Performance — N+1 Queries

**Date**: 2026-06-30  
**Symptom**: Analytics pages slow due to excessive database queries.  
**Root Causes**:
1. `get_team_comparison()`: 7 queries × N salespeople (71+ for 10 users)
2. `get_trend_data()`: 15 queries with `total_leads` computed 3× redundantly
3. `get_executive_summary()`: Full table load into Python for average calculation
4. `get_inquiry_analytics()`: 6 separate COUNT queries replaceable with 1 GROUP BY

**Fix**: Rewrote all N+1 patterns to batch queries with GROUP BY.  
**Files**: `sales_lead_system/modules/analytics_engine.py`

---

## 33. Missing Database Indexes

**Date**: 2026-06-30  
**Symptom**: Dashboard and analytics queries slow on growing data.  
**Root Causes**: Missing indexes on frequently queried columns.
- `followups.completed_at` — used in 10+ WHERE clauses across dashboard/analytics
- `followups.(lead_id, followup_id)` — used in MAX() GROUP BY pattern
- `leads.(deleted_at, assigned_to, updated_at DESC)` — scope + ORDER BY
- `engagement_events.(lead_id, occurred_at)` — JOIN + date range
- `inquiries.type` — GROUP BY analytics
- `activity_logs.user_name` — filter by user
- Redundant `ix_leads_lead_id_prefix` duplicates PK

**Fix**: Phase 14 migration — 7 new composite indexes, 1 redundant index dropped.  
**Files**: `sales_lead_system/database/schema_manager.py`

---

## 34. Dead Code & Unused Files Cleanup

**Date**: 2026-06-30  
**Symptom**: Codebase bloated with unused modules, dead pages, and stale references.  
**Root Causes**:
- 11 dead Python files (lead_manager.py, followup_manager.py, init_db.py, tools/)
- 3 dead React pages (MyWorkspace, Nurturing, Reports)
- Dead component (input.tsx), dead module (products.ts)
- Unused hooks, types, and functions across frontend
- console.error in production code
- Duplicate constants and imports

**Fix**: Deleted all dead files, removed unused exports, cleaned console statements.  
**Files**: Multiple (11 Python files deleted, 4 frontend files deleted)

---

## 35. Dead Database Columns

**Date**: 2026-06-30  
**Symptom**: Database bloated with unused columns across 4 tables.  
**Root Causes**:
- `leads`: 7 dead columns (moq_requirement, expected_quantity, budget_range, follow_up_stage, legacy_status, first_contact_date, sheet_source)
- `followups`: 4 dead columns (legacy_buyer_id, buyer_name, country, transfer_to)
- `inquiries`: 3 dead columns (acknowledged_at, estimated_response_time, acknowledgement_note)
- `engagement_events`: 3 dead columns (channel, direction, outcome)

**Fix**: Phase 13 migration dropped all 17 dead columns. Updated ORM models to match.  
**Files**: `sales_lead_system/database/schema_manager.py`, `sales_lead_system/database/models.py`, `sales_lead_system/modules/crm_service.py`, `sales_lead_system/modules/activity_engine.py`

---

## 36. Dashboard Context Filter 404

**Date**: 2026-06-30  
**Symptom**: Selecting a salesperson on Dashboard caused 404 errors.  
**Root Cause**: Backend resolver functions filtered by `User.role == "Salesperson"`, rejecting Admin/Manager selections.  
**Fix**: Removed role filter from both `dashboard.py` and `analytics.py` resolvers.  
**Files**: `sales_lead_system/api/routers/dashboard.py`, `sales_lead_system/api/routers/analytics.py`

---

## 37. Lead Transfer Recipients Not Visible

**Date**: 2026-06-29  
**Symptom**: Salespersons couldn't see recipients when transferring leads.  
**Root Cause**: TransferLeadModal fetched from `GET /users` (Admin/Manager only).  
**Fix**: Added `GET /users/transfer-recipients` endpoint accessible to any authenticated user.  
**Files**: `sales_lead_system/api/routers/users.py`, `web/src/components/TransferLeadModal.tsx`

---

## 38. PostgreSQL Password Compromised in Git History

**Date**: 2026-06-29  
**Symptom**: GitGuardian flagged PostgreSQL URI in repository.  
**Root Cause**: Test file `check_followup.py` contained hardcoded PostgreSQL connection string with password. Was committed and then removed, but remains in git history.  
**Fix**: 
1. Rotated password via SQL (`ALTER USER postgres WITH PASSWORD ...`)
2. Updated `DATABASE_URL` on Railway
3. Verified old password is rejected
4. File removed from current tree
**Status**: Git history still contains the old credential. User must manually rotate via Railway dashboard for complete remediation.  
**Files**: Password rotated via direct SQL, Railway env var updated

---

## 39. Inquiry Modal Gray Block

**Date**: 2026-06-29  
**Symptom**: Gray rectangle appeared behind inquiry modal.  
**Root Cause**: `InquiryWorkflowModal` was missing the `<main>` scroll lock that `TaskWorkflowModal` had. Page scrolled freely behind the backdrop.  
**Fix**: Added same `<main>` scroll lock pattern (save scrollTop, set overflow hidden, restore on unmount).  
**Files**: `web/src/components/InquiryWorkflowModal.tsx`

---

## 40. Backend Crash — Missing Import

**Date**: 2026-06-30  
**Symptom**: `NameError: name 'status' is not defined` in inquiries.py.  
**Root Cause**: New revision endpoints used `status.HTTP_201_CREATED` without importing `status` from FastAPI.  
**Fix**: Added `status` to FastAPI import line.  
**Files**: `sales_lead_system/api/routers/inquiries.py`

---

## 41. PostgreSQL Migration Failures (Multi-part)

**Date**: 2026-06-30  
**Symptom**: `products` and `inquiry_revisions` tables didn't exist.  
**Root Causes**: SQLite-specific DDL on PostgreSQL, FK constraints on non-unique columns, seed data not inserted, `is_active` column missing from INSERT.  
**Fix**: PostgreSQL dialect detection, removed FK constraints, separate seed blocks, added `is_active = TRUE` to INSERT.  
**Files**: `sales_lead_system/database/schema_manager.py`, `sales_lead_system/database/models.py`

---

## 42. Schema Manager Catastrophic Overwrite

**Date**: 2026-06-30  
**Symptom**: `schema_manager.py` reduced from 600+ lines to 98 lines.  
**Root Cause**: Used `write` tool instead of `edit`.  
**Fix**: Restored from git: `git checkout b751231 -- schema_manager.py`  
**Lesson**: Always use `edit` for existing files. Only `write` for new files.

---

## 43. Task Engine Completed Tasks Not Visible

**Date**: 2026-06-29  
**Symptom**: Completed tasks appeared in active queue.  
**Root Cause**: Engine only checked `MAX(followup_id)` per lead — new follow-up after completion became "latest" with no `completed_at`.  
**Fix**: Added secondary query for recently completed follow-ups that are NOT the latest.  
**Files**: `sales_lead_system/modules/task_engine.py`

---

## 44. Task Modal Portal Issue

**Date**: 2026-06-29  
**Symptom**: Gray block behind task modal.  
**Root Cause**: Modal rendered inside `<main>` scroll container, not via portal.  
**Fix**: `createPortal(content, document.body)` + `<main>` scroll lock.  
**Files**: `web/src/components/TaskWorkflowModal.tsx`

---

## 45. Database Performance — N+1 Queries

**Date**: 2026-06-30  
**Symptom**: Analytics pages slow on growing data.  
**Root Causes**: `get_team_comparison()` executed 7 queries per salesperson (71+ for 10 users). `get_trend_data()` computed `total_leads` 3× redundantly. `get_executive_summary()` loaded all leads into Python. `get_inquiry_analytics()` used 6 separate COUNT queries.  
**Fix**: Rewrote all to batch queries with GROUP BY.  
**Files**: `sales_lead_system/modules/analytics_engine.py`

---

## 46. Missing Database Indexes

**Date**: 2026-06-30  
**Symptom**: Dashboard/analytics slow on growing data.  
**Fix**: Phase 14 — 7 new composite indexes + 1 redundant index dropped.  
**Files**: `sales_lead_system/database/schema_manager.py`
