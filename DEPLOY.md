# Deploying the Sales Lead CRM to Streamlit Cloud

## 1. Push this repo to GitHub (infofittree)
After creating an empty repo `sales-lead-crm` (no README/license) at
github.com/infofittree, from this folder run:

```bash
git remote add origin https://github.com/infofittree/sales-lead-crm.git
git push -u origin main
```

## 2. Provision a cloud MySQL (Streamlit Cloud cannot reach localhost)
Create a free MySQL on any host — e.g. **Aiven**, **Railway**, or **Clever Cloud**.
Note the host, port, user, password, and create a database named `sales_lead_crm`.
(The app auto-creates all tables on first run.)

## 3. Create the Streamlit Cloud app
- Go to share.streamlit.io → **New app** → pick the `infofittree/sales-lead-crm` repo.
- **Main file path:** `sales_lead_system/app/dashboard.py`
- **Python:** 3.12

## 4. Add Secrets (App → Settings → Secrets)
Paste, with real values (template: `sales_lead_system/.streamlit/secrets.toml.example`):

```toml
[mysql]
host = "your-cloud-mysql-host"
port = 3306
user = "your_db_user"
password = "your_db_password"
database = "sales_lead_crm"

CRM_ADMIN_USER = "admin"
CRM_ADMIN_PASSWORD = "a-strong-password"
```

## 5. First run
- The app creates tables and a first admin (CRM_ADMIN_USER / CRM_ADMIN_PASSWORD).
- Log in, then load data via **Data Entry** or by importing your workbook.

## Notes
- `requirements.txt` is at the repo root for Streamlit Cloud.
- The DB layer reads Streamlit secrets first, then `.env` for local runs.
- It stays on MySQL (schema/migrations are MySQL-specific) — use a hosted MySQL.
- Local development is unchanged: keep using `config/.env` + local MySQL.
