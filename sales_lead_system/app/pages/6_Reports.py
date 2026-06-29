"""Enterprise Reports — per-funnel-stage analytics with deep filters."""

from __future__ import annotations

import io
import sys
from datetime import date
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
import plotly.express as px
import streamlit as st

from app.assets.theme import STATUS_COLORS, style_plotly
from app.db import ensure_startup, get_db, render_startup_status
from app.ui import configure_page, data_table, empty_state, page_header, require_login, section_header
from modules import reporting as rp
from modules.crm_service import CRMService
from modules.status_taxonomy import FUNNEL_ORDER, is_won

configure_page("Reports")
user = require_login("Reports")
page_header("Enterprise Reports", "Funnel-stage reporting, conversion analysis, and management insights.", "CRM Reporting")

db = get_db()
startup_status = ensure_startup(db)
render_startup_status(startup_status)
if startup_status.errors:
    st.error(startup_status.errors[0])
    st.stop()

with db.session_scope() as session:
    service = CRMService(session)
    leads = service.leads_dataframe(user, limit=10000)
    followups = service.followups_dataframe(user, horizon_days=365)
    salespersons = service.get_salespersons()

if leads.empty:
    empty_state("No data", "Add or sync leads to build reports.")
    st.stop()

leads = rp.attach_followups(leads, followups)

with st.expander("Filters", expanded=True):
    fc = st.columns(4)
    f_sales = fc[0].multiselect("Salesperson", sorted(leads["assigned_to"].dropna().unique()))
    f_country = fc[1].multiselect("Country", sorted(leads["country"].dropna().unique()))
    f_cont = fc[2].multiselect("Continent", sorted(leads["continent"].dropna().unique()) if "continent" in leads.columns else [])
    f_source = fc[3].multiselect("Source", sorted(leads["lead_source"].dropna().unique()) if "lead_source" in leads.columns else [])
    fc2 = st.columns(4)
    f_cat = fc2[0].multiselect("Category", ["A", "B", "C"])
    f_fu = fc2[1].multiselect("Follow-up", ["Overdue", "Due Today", "Upcoming", "None"])
    f_band = fc2[2].multiselect("Health", ["HOT", "WARM", "COLD"])
    f_dates = fc2[3].date_input("Created between", value=())

date_from = date_to = None
if isinstance(f_dates, tuple) and len(f_dates) == 2:
    date_from, date_to = f_dates

filtered_all = rp.apply_filters(
    leads, salesperson=f_sales, country=f_country, continent=f_cont, source=f_source,
    category=f_cat, followup_state=f_fu, band=f_band, date_from=date_from, date_to=date_to,
)

report_names = ["Funnel Overview"] + [f"{i+1}. {s} Report" for i, s in enumerate(rp.STAGE_REPORTS)]
choice = st.selectbox("Report", report_names)

DISPLAY_COLS = ["lead_id", "company_name", "assigned_to", "lead_category", "lead_score",
                "country", "continent", "lead_source", "standard_status", "followup_state",
                "next_followup", "aging_days", "last_contact_date"]


def _present(df):
    return [c for c in DISPLAY_COLS if c in df.columns]


def _export(df, name):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, sheet_name=name[:30], index=False)
    st.download_button(f"Export {name} (Excel)", buf.getvalue(),
                       file_name=f"{name.lower().replace(' ', '_')}_{date.today()}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       use_container_width=True)
    st.download_button("CSV", df.to_csv(index=False),
                       file_name=f"{name.lower().replace(' ', '_')}_{date.today()}.csv", mime="text/csv")

if choice.startswith("Funnel"):
    section_header("Sales Funnel Overview", "Stage-by-stage pipeline and drop-off.")
    counts = filtered_all["standard_status"].value_counts()
    fk = st.columns(5)
    fk[0].markdown(f"<div style='background:var(--crm-card);border:1px solid var(--crm-border);border-radius:12px;padding:0.7rem;text-align:center;'><div style='font-size:1.3rem;font-weight:850;'>{len(filtered_all)}</div><div style='font-size:0.7rem;color:var(--crm-muted);text-transform:uppercase;letter-spacing:0.3px;font-weight:700;'>Total</div></div>", unsafe_allow_html=True)
    fk[1].markdown(f"<div style='background:var(--crm-card);border:1px solid var(--crm-border);border-radius:12px;padding:0.7rem;text-align:center;'><div style='font-size:1.3rem;font-weight:850;'>{int(filtered_all['standard_status'].isin(FUNNEL_ORDER).sum())}</div><div style='font-size:0.7rem;color:var(--crm-muted);text-transform:uppercase;letter-spacing:0.3px;font-weight:700;'>Open</div></div>", unsafe_allow_html=True)
    fk[2].markdown(f"<div style='background:var(--crm-card);border:1px solid var(--crm-border);border-radius:12px;padding:0.7rem;text-align:center;'><div style='font-size:1.3rem;font-weight:850;'>{int(counts.get('Negotiation', 0))}</div><div style='font-size:0.7rem;color:var(--crm-muted);text-transform:uppercase;letter-spacing:0.3px;font-weight:700;'>Negotiation</div></div>", unsafe_allow_html=True)
    fk[3].markdown(f"<div style='background:var(--crm-card);border:1px solid var(--crm-border);border-radius:12px;padding:0.7rem;text-align:center;'><div style='font-size:1.3rem;font-weight:850;'>{int(counts.get('Order Closed', 0))}</div><div style='font-size:0.7rem;color:var(--crm-muted);text-transform:uppercase;letter-spacing:0.3px;font-weight:700;'>Closed</div></div>", unsafe_allow_html=True)
    fk[4].markdown(f"<div style='background:var(--crm-card);border:1px solid var(--crm-border);border-radius:12px;padding:0.7rem;text-align:center;'><div style='font-size:1.3rem;font-weight:850;'>{int(counts.get('Lost', 0))}</div><div style='font-size:0.7rem;color:var(--crm-muted);text-transform:uppercase;letter-spacing:0.3px;font-weight:700;'>Lost</div></div>", unsafe_allow_html=True)

    fd = counts.reindex(FUNNEL_ORDER).fillna(0).reset_index()
    fd.columns = ["stage", "count"]
    fd = fd[fd["count"] > 0]
    st.plotly_chart(style_plotly(px.funnel(fd, x="count", y="stage", color="stage",
                    color_discrete_map=STATUS_COLORS).update_layout(showlegend=False), height=420), use_container_width=True)

    section_header("Funnel Conversion Rates", "Drop-off between consecutive stages.")
    rows = []
    for i in range(len(FUNNEL_ORDER) - 1):
        a, b = FUNNEL_ORDER[i], FUNNEL_ORDER[i + 1]
        idx_a = FUNNEL_ORDER.index(a)
        reached_a = sum(counts.get(s, 0) for s in FUNNEL_ORDER[idx_a:])
        reached_b = sum(counts.get(s, 0) for s in FUNNEL_ORDER[idx_a + 1:])
        rate = round(reached_b / reached_a * 100, 1) if reached_a else 0
        rows.append({"transition": f"{a} → {b}", "conversion_%": rate})
    data_table(pd.DataFrame(rows))

else:
    stage = choice.split(". ", 1)[1].rsplit(" Report", 1)[0]
    df = filtered_all[filtered_all["standard_status"] == stage].copy()
    section_header(f"{stage} Report", rp.STAGE_REPORTS.get(stage, ""))

    k = rp.stage_kpis(df, stage)
    kc = st.columns(5)
    kc[0].markdown(f"<div style='background:var(--crm-card);border:1px solid var(--crm-border);border-radius:10px;padding:0.5rem;text-align:center;'><div style='font-size:1.1rem;font-weight:800;'>{k['count']}</div><div style='font-size:0.7rem;color:var(--crm-muted);text-transform:uppercase;letter-spacing:0.3px;font-weight:700;'>Total</div></div>", unsafe_allow_html=True)
    kc[1].markdown(f"<div style='background:var(--crm-card);border:1px solid var(--crm-border);border-radius:10px;padding:0.5rem;text-align:center;'><div style='font-size:1.1rem;font-weight:800;'>{k['overdue']}</div><div style='font-size:0.7rem;color:var(--crm-muted);text-transform:uppercase;letter-spacing:0.3px;font-weight:700;'>Overdue</div></div>", unsafe_allow_html=True)
    kc[2].markdown(f"<div style='background:var(--crm-card);border:1px solid var(--crm-border);border-radius:10px;padding:0.5rem;text-align:center;'><div style='font-size:1.1rem;font-weight:800;'>{int(k['avg_age_days'])}</div><div style='font-size:0.7rem;color:var(--crm-muted);text-transform:uppercase;letter-spacing:0.3px;font-weight:700;'>Avg Age</div></div>", unsafe_allow_html=True)
    kc[3].markdown(f"<div style='background:var(--crm-card);border:1px solid var(--crm-border);border-radius:10px;padding:0.5rem;text-align:center;'><div style='font-size:1.1rem;font-weight:800;'>{k['a_category']}</div><div style='font-size:0.7rem;color:var(--crm-muted);text-transform:uppercase;letter-spacing:0.3px;font-weight:700;'>A-Category</div></div>", unsafe_allow_html=True)
    kc[4].markdown(f"<div style='background:var(--crm-card);border:1px solid var(--crm-border);border-radius:10px;padding:0.5rem;text-align:center;'><div style='font-size:1.1rem;font-weight:800;'>{k['avg_score']}</div><div style='font-size:0.7rem;color:var(--crm-muted);text-transform:uppercase;letter-spacing:0.3px;font-weight:700;'>Avg Score</div></div>", unsafe_allow_html=True)

    if df.empty:
        empty_state("No leads in this stage", "Adjust filters or pick another report.")
    else:
        c1, c2 = st.columns(2)
        bsales = rp.breakdown(df, "assigned_to")
        c1.plotly_chart(style_plotly(px.bar(bsales, x="assigned_to", y="count", title="By Salesperson"), height=300), use_container_width=True)
        bsrc = rp.breakdown(df, "lead_source")
        c2.plotly_chart(style_plotly(px.bar(bsrc, x="lead_source", y="count", title="By Source"), height=300), use_container_width=True)
        c3, c4 = st.columns(2)
        bcountry = rp.breakdown(df, "country", top=8)
        c3.plotly_chart(style_plotly(px.bar(bcountry, x="country", y="count", title="By Country"), height=300), use_container_width=True)
        if stage == "Lost" and "lost_reason" in df.columns:
            blr = df["lost_reason"].fillna("Unspecified").value_counts().reset_index()
            blr.columns = ["lost_reason", "count"]
            c4.plotly_chart(style_plotly(px.pie(blr, names="lost_reason", values="count", title="Lost Reasons"), height=300), use_container_width=True)
        else:
            bcat = rp.breakdown(df, "lead_category")
            c4.plotly_chart(style_plotly(px.pie(bcat, names="lead_category", values="count", title="By Category"), height=300), use_container_width=True)

        section_header("Detailed Records", "Drill-down, searchable, export-ready.")
        search = st.text_input("Search company")
        view = df[df["company_name"].str.contains(search, case=False, na=False)] if search else df
        st.caption(f"{len(view)} records")
        data_table(view[_present(view)].sort_values("lead_score", ascending=False))
        _export(view[_present(view)], f"{stage} Report")
