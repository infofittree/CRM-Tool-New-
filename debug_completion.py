import psycopg2

conn = psycopg2.connect("postgresql://postgres:keKjc24pGE0g21SGZkSbHEZSOiA89L_j@hayabusa.proxy.rlwy.net:38877/railway", sslmode="require", connect_timeout=30)
cur = conn.cursor()

# Check: how many follow-ups have completed_at set?
cur.execute("SELECT COUNT(*) FROM followups WHERE completed_at IS NOT NULL")
print(f"Follow-ups with completed_at: {cur.fetchone()[0]}")

# Check: how many follow-ups are the LATEST for their lead?
cur.execute("""
    SELECT f.followup_id, f.lead_id, f.completed_at, f.completed_by
    FROM followups f
    INNER JOIN (
        SELECT lead_id, MAX(followup_id) as max_id
        FROM followups GROUP BY lead_id
    ) latest ON f.followup_id = latest.max_id
    WHERE f.completed_at IS NOT NULL
    LIMIT 5
""")
rows = cur.fetchall()
print(f"Latest follow-ups with completed_at: {len(rows)}")
for r in rows:
    print(f"  followup={r[0]}, lead={r[1]}, completed_at={r[2]}, by={r[3]}")

# Check: follow-ups that are completed but NOT the latest
cur.execute("""
    SELECT f.followup_id, f.lead_id, f.completed_at, f.completed_by, latest.max_id
    FROM followups f
    INNER JOIN (
        SELECT lead_id, MAX(followup_id) as max_id
        FROM followups GROUP BY lead_id
    ) latest ON f.lead_id = latest.lead_id
    WHERE f.completed_at IS NOT NULL
    AND f.followup_id < latest.max_id
    LIMIT 10
""")
rows2 = cur.fetchall()
print(f"\nCompleted but NOT latest: {len(rows2)}")
for r in rows2:
    print(f"  followup={r[0]}, lead={r[1]}, completed_at={r[2]}, by={r[3]}, latest_id={r[4]}")

conn.close()
