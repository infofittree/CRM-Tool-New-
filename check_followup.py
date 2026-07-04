import psycopg2
conn = psycopg2.connect("postgresql://postgres:ddEXovimSCzsYKVQZMZgiTuyiQugHCtJ@hayabusa.proxy.rlwy.net:38877/railway", sslmode="require", connect_timeout=30)
cur = conn.cursor()
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'followups' AND column_name = 'followup_id'")
print("followup_id:", cur.fetchone())
cur.execute("SELECT followup_id, typeof(followup_id) FROM followups LIMIT 3")
for r in cur.fetchall():
    print(f"  value={r[0]} type={r[1]}")
conn.close()
