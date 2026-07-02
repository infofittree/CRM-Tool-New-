"""Seed PostgreSQL database with CSV data."""
import csv
import os
import psycopg2

DATABASE_URL = "postgresql://postgres:ddEXovimSCzsYKVQZMZgiTuyiQugHCtJ@hayabusa.proxy.rlwy.net:38877/railway?sslmode=require"

CSV_DIR = r"C:\Users\Kunj Mistry\Desktop\studies\Fittree\db_export_2026-07-01\csv"

def get_connection():
    return psycopg2.connect(DATABASE_URL, connect_timeout=30)

def create_table_from_csv(cur, csv_path, table_name):
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        headers = next(reader)
        rows = list(reader)

    cols_def = ", ".join(f'"{h}" TEXT' for h in headers)
    cur.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
    cur.execute(f"CREATE TABLE {table_name} ({cols_def})")

    placeholders = ", ".join(["%s"] * len(headers))
    inserted = 0
    for row in rows:
        while len(row) < len(headers):
            row.append("")
        clean_row = [None if v == "" else v for v in row[:len(headers)]]
        try:
            cur.execute(f"INSERT INTO {table_name} VALUES ({placeholders})", clean_row)
            inserted += 1
        except Exception as e:
            print(f"  Row error: {e}")
            conn.rollback()

    print(f"  {table_name}: {inserted} rows")
    return inserted

tables = [
    ("users.csv", "users"),
    ("leads.csv", "leads"),
    ("followups.csv", "followups"),
    ("engagement_events.csv", "engagement_events"),
    ("activity_logs.csv", "activity_logs"),
    ("deleted_leads.csv", "deleted_leads"),
    ("lead_transfers.csv", "lead_transfers"),
    ("duplicate_reports.csv", "duplicate_reports"),
    ("app_settings.csv", "app_settings"),
    ("lead_sequences.csv", "lead_sequences"),
]

print("Seeding PostgreSQL...")
conn = get_connection()
cur = conn.cursor()
total = 0

for csv_file, table_name in tables:
    csv_path = os.path.join(CSV_DIR, csv_file)
    if os.path.exists(csv_path):
        try:
            count = create_table_from_csv(cur, csv_path, table_name)
            conn.commit()
            total += count
        except Exception as e:
            print(f"  {table_name} error: {e}")
            conn.rollback()
            conn = get_connection()
            cur = conn.cursor()
    else:
        print(f"  {csv_file}: NOT FOUND")

# Create indexes
print("\nCreating indexes...")
for idx in [
    "CREATE INDEX IF NOT EXISTS ix_leads_status ON leads(status)",
    "CREATE INDEX IF NOT EXISTS ix_leads_assigned ON leads(assigned_to)",
    "CREATE INDEX IF NOT EXISTS ix_followups_lead ON followups(lead_id)",
    "CREATE INDEX IF NOT EXISTS ix_followups_next ON followups(next_followup)",
    "CREATE INDEX IF NOT EXISTS ix_users_username ON users(username)",
]:
    try:
        cur.execute(idx)
    except:
        pass

conn.commit()
conn.close()
print(f"\nDone! {total} rows imported")
