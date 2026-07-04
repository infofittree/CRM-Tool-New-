# Sales Lead Automation System

This project contains the Phase 1 Excel preprocessing pipeline, a MySQL backend, and the Phase 2 Streamlit CRM dashboard. Excel remains supported for import/export, but MySQL and the web CRM are now the primary operational system.

## Folder Structure

```text
sales_lead_system/
|-- app/
|   |-- dashboard.py
|   |-- login.py
|   |-- security.py
|   |-- ui.py
|   |-- db.py
|   `-- pages/
|       |-- 1_Lead_Management.py
|       |-- 2_Followups.py
|       |-- 3_Nurturing_Leads.py
|       |-- 4_Analytics.py
|       |-- 5_Sales_Team.py
|       |-- 6_Reports.py
|       |-- 7_Settings.py
|       `-- 8_Data_Entry.py
|-- data/
|   |-- raw/
|   |-- processed/
|   `-- backup/
|-- database/
|   |-- db_connection.py
|   |-- models.py
|   |-- schema.sql
|   |-- crud.py
|   |-- init_db.py
|   `-- migrations/
|-- exports/
|-- logs/
|-- modules/
|-- config/
|-- main.py
|-- requirements.txt
`-- README.md
```

## Capabilities

- Cleans and validates raw Excel workbooks.
- Imports cleaned data into MySQL.
- Provides SQLAlchemy ORM models, CRUD functions, sync engine, validation, and exports.
- Runs a Streamlit CRM dashboard for daily sales operations.
- Supports session login with Admin, Manager, and Salesperson roles.
- Lets sales users create leads and follow-ups directly from the web app.
- Provides Plotly analytics, reports, team performance, nurturing intelligence, and settings.

## MySQL Setup

Install dependencies:

```powershell
cd "C:\Users\yash\Documents\Sales Lead Master Tracker\sales_lead_system"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell cannot find `mysql`, use the full MySQL path:

```powershell
Get-Content .\database\schema.sql | & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p
```

For an existing Phase 1 MySQL database, apply the Phase 2 migration:

```powershell
Get-Content .\database\migrations\002_phase2_crm_app.sql | & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p sales_lead_crm
```

Configure `config/.env`:

```text
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=sales_lead_crm
CRM_ADMIN_USER=admin
CRM_ADMIN_PASSWORD=change_this_password
```

Verify:

```powershell
python main.py healthcheck-mysql
python main.py init-mysql
```

## Run The CRM

```powershell
streamlit run app/dashboard.py
```

Default first-run admin credentials come from `.env`. Change them after first login by creating a new Admin user in Settings.

## CRM Pages

- Dashboard: KPI cards, funnel chart, daily priorities, activity feed, salesperson performance.
- Lead Management: add leads, search, filters, export, detail view, status updates, soft delete, conversion action.
- Followups: overdue, today, and upcoming queues with quick update forms.
- Nurturing Leads: HOT/WARM/COLD health, days since contact, suggested actions.
- Analytics: Plotly source, status, country, salesperson, and follow-up charts.
- Sales Team: performance table and leaderboard.
- Reports: downloadable lead, follow-up, inactive, and conversion reports.
- Settings: user creation, statuses, lead sources, reminder thresholds.
- Data Entry: structured lead submission, duplicate review, bulk upload, quick follow-up entry.

## Data Entry Workflow

The Data Entry page validates mandatory fields, email, phone, status rules, duplicate email, fuzzy company similarity, and phone matches. On save it cleans inputs, generates a MySQL-backed lead ID, inserts the lead, creates the first follow-up, writes an activity log, and refreshes app data.

Bulk upload supports Excel and CSV files. Valid rows are imported, duplicate rows are skipped, and invalid rows are summarized.

## Preprocess Raw Excel

```powershell
python main.py preprocess --input "C:\path\to\Sales_Master_Tracker.xlsx" --year 2026
```

## Import Or Sync Cleaned Excel To MySQL

```powershell
python main.py import-mysql --cleaned-file "data\processed\20260528_114516\cleaned_sales_leads.xlsx" --user admin
python main.py sync-mysql --cleaned-file "data\processed\20260528_114516\cleaned_sales_leads.xlsx" --user scheduler
```

## Export MySQL Data

```powershell
python main.py export-mysql
```

Exports include:

- `leads_export.xlsx`
- `followups_export.csv`
- `reports_export.xlsx`

## Screenshot Layout Descriptions

- Dashboard: seven KPI cards across the top, lead funnel left, daily priorities right, activity and team performance below.
- Lead Management: collapsible lead form, filter toolbar, full-width table, detail/update panel.
- Followups: tabbed follow-up queue with cards and inline completion forms.
- Data Entry: tabs for single lead entry, bulk upload preview/import, and quick follow-up entry.

## Troubleshooting

- `mysql` not recognized: use the full path to `mysql.exe` shown above.
- `Access denied for user`: check `MYSQL_USER` and `MYSQL_PASSWORD` in `config/.env`.
- `Unknown database`: run `database/schema.sql` first.
- `ModuleNotFoundError`: activate the virtual environment and run `pip install -r requirements.txt`.
- Streamlit cannot connect to MySQL: run `python main.py healthcheck-mysql`.
- Login fails on first run: confirm `users` table exists and `.env` has `CRM_ADMIN_USER` / `CRM_ADMIN_PASSWORD`.

