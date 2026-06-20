"""Weekly Sales Review — executive weekly intelligence & meeting mode."""

from __future__ import annotations

import io
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
import plotly.express as px
import streamlit as st

from app.assets.theme import STATUS_COLORS, style_plotly
from app.db import ensure_startup, get_db, render_startup_status
from app.ui import configure_page, empty_state, page_header, require_login, score_badge, section_header, status_pill
from modules import weekly_review as wr
from modules.crm_service import CRMService

configure_page("Weekly Review")
user = require_login("Weekly Review")
page_header("Weekly Sales Review", "Executive weekly intelligence for review meetings — who did what, with which company, and what's next.", "Weekly Performance")

db = get_db()
startup_status = ensure_startup(db)
render_startup_status(startup_status)
if startup_status.errors:
    st.error(startup_status.errors[0])
    st.stop()

# ----------------------- Week + filters (Section 9) -----------------------
ctrl1, ctrl2, ctrl3 = st.columns([1.2, 1, 1])
week_choice = ctrl1.selectbox("Week", ["This Week", "Last Week", "2 Weeks Ago", "Custom"])
offset = {"This Week": 0, "Last Week": -1, "2 Weeks Ago": -2}.get(week_choice, 0)
if week_choice == "Custom":
    default_mon, default_sun = wr.week_bounds()
    custom = ctrl1.date_input("Custom range", value=(default_mon, default_sun))
    if isinstance(custom, tuple) and len(custom) == 2:
        start, end = custom
    else:
        start, end = wr.week_bounds()
else:
    start, end = wr.week_bounds(offset_weeks=offset)
ctrl2.metric("Week Start (Mon)", start.strftime("%d %b %Y"))
ctrl3.metric("Week End (Sun)", end.strftime("%d %b %Y"))

with db.session_scope() as session:
    service = CRMService(session)
    all_salespersons = service.get_salespersons()

    # Role-aware focus: Admin/Manager can drill into one salesperson
    focus_user = user
    if user["role"] in ("Admin", "Manager"):
        chosen = st.selectbox("Focus salesperson (optional)", ["All Team"] + all_salespersons)
        if chosen != "All Team":
            focus_user = {"role": "Salesperson", "full_name": chosen}

    tabs = st.tabs([
        "📊 Overview", "👤 Salespeople", "🏢 Company Activity", "🕑 Company Timeline",
        "❌ Lost Analysis", "🧠 Insights", "📅 Next Week", "🎤 Present My Week", "⬇️ Export",
    ])

    # ===================== SECTION 1 — OVERVIEW =====================
    with tabs[0]:
        section_header("Weekly Overview", f"{start:%d %b} → {end:%d %b}  ·  trend vs previous week")
        t = wr.overview_with_trend(session, focus_user, start, end)
        cur, dlt = t["current"], t["deltas"]

        def fmt_delta(key):
            d = dlt.get(key)
            if not d or d["pct"] == 0:
                return None
            sign = "+" if d["dir"] == "up" else "-"
            return f"{sign}{abs(d['pct']):.0f}% vs last wk"

        # ---- THIS WEEK (activity that happened inside the selected window) ----
        st.markdown("##### 🗓️ This Week")
        r1 = st.columns(5)
        r1[0].metric("New Leads (week)", cur["assigned_week"])
        r1[1].metric("Companies Contacted", cur["contacted_week"], fmt_delta("contacted_week"))
        r1[2].metric("Follow-ups Done", cur["followups_completed"], fmt_delta("followups_completed"))
        r1[3].metric("Meetings Done", cur["meetings_done"], fmt_delta("meetings_done"))
        r1[4].metric("Conversions (wk)", cur["conversions_week"], fmt_delta("conversions_week"))
        r2 = st.columns(5)
        r2[0].metric("Calls", cur["calls"], fmt_delta("calls"))
        r2[1].metric("WhatsApp", cur["whatsapp"], fmt_delta("whatsapp"))
        r2[2].metric("Emails", cur["emails"], fmt_delta("emails"))
        r2[3].metric("Task Completion %", f"{cur['task_completion_pct']}%")
        r2[4].metric("Engagement %", f"{cur['engagement_pct']}%")
        st.caption("Channel breakdown (Calls/WhatsApp/Emails) populates as the team picks a Channel when logging follow-ups.")

        st.divider()
        # ---- PIPELINE SNAPSHOT (current state of all leads in scope, not weekly) ----
        st.markdown("##### 📌 Pipeline Snapshot · current (all-time, not this week)")
        r3 = st.columns(5)
        r3[0].metric("Interested", cur["interested"])
        r3[1].metric("Negotiation", cur["negotiation"])
        r3[2].metric("Quotations Sent", cur["quotations_sent"])
        r3[3].metric("Converted (total)", cur["converted_total"])
        r3[4].metric("Lost (total)", cur["lost_total"])
        r4 = st.columns(4)
        r4[0].metric("Pending Follow-ups", cur["pending_followups"])
        r4[1].metric("Overdue Follow-ups", cur["overdue_followups"])
        r4[2].metric("Conversion % (lifetime)", f"{cur['conversion_pct']}%")
        r4[3].metric("Hot / Warm Leads", f"{cur['hot']} / {cur['warm']}")

        st.divider()
        section_header("Lead Quality Mix")
        mix = pd.DataFrame({"band": ["HOT", "WARM", "NURTURE", "COLD"],
                            "count": [cur["hot"], cur["warm"], cur["nurture"], cur["cold"]]})
        st.plotly_chart(style_plotly(px.bar(mix, x="band", y="count", color="band",
                        color_discrete_map={"HOT": "#ef4444", "WARM": "#f59e0b", "NURTURE": "#eab308", "COLD": "#38bdf8"}),
                        height=300), use_container_width=True)

    # ===================== SECTION 2 — SALESPEOPLE =====================
    with tabs[1]:
        section_header("Salesperson Performance", "Ranked by lead-handling score. Spot top, average, and weak performers.")
        perf = wr.salesperson_performance(session, start, end)
        perf = [p for p in perf if p["salesperson"] != "Unassigned"] or perf
        if not perf:
            empty_state("No salesperson data", "Assign leads to build performance review.")
        for p in perf:
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(p["rank"], f"#{p['rank']}")
            with st.container():
                st.markdown(
                    f"""<div class="crm-section">
                    <div class="crm-section-title">{medal} {p['salesperson']}
                    <span style="color:#64748b;font-weight:600">Handling {p['handling_score']} · Completion {p['completion_pct']}%</span></div>
                    </div>""", unsafe_allow_html=True)
                cc = st.columns(6)
                cc[0].metric("Assigned", p["assigned"])
                cc[1].metric("Worked", p["worked"])
                cc[2].metric("Ignored", p["ignored"])
                cc[3].metric("Calls", p["calls"])
                cc[4].metric("WhatsApp", p["whatsapp"])
                cc[5].metric("Overdue", p["overdue"])
                cc2 = st.columns(6)
                cc2[0].metric("Emails", p["emails"])
                cc2[1].metric("Notes", p["notes"])
                cc2[2].metric("Negotiation", p["negotiation"])
                cc2[3].metric("Converted", p["converted"])
                cc2[4].metric("Productivity", p["productivity"])
                cc2[5].metric("FU Quality", p["followup_quality"])

    # ===================== SECTION 3 — COMPANY ACTIVITY =====================
    with tabs[2]:
        section_header("Companies Worked On This Week", "Only leads with real activity — follow-ups, stage changes, notes, new entries. No CRM dump.")
        rows = wr.company_activity(session, focus_user, start, end, only_worked=True)
        if not rows:
            empty_state("No work logged this week", "When the team logs follow-ups, stage changes or notes, those companies appear here.")
        else:
            df = pd.DataFrame(rows)
            f1, f2, f3 = st.columns(3)
            band_f = f1.multiselect("Lead Type", ["HOT", "WARM", "COLD"])
            status_f = f2.multiselect("Stage", sorted(df["current_status"].unique()))
            country_search = f3.text_input("Search company")
            view = df.copy()
            if band_f:
                view = view[view["band"].isin(band_f)]
            if status_f:
                view = view[view["current_status"].isin(status_f)]
            if country_search:
                view = view[view["company"].str.contains(country_search, case=False, na=False)]
            st.caption(f"{len(view)} companies")
            display_cols = ["company", "salesperson", "score", "band", "current_status", "status_movement",
                            "work_done", "calls", "whatsapp", "emails", "followups", "response", "quotation_status",
                            "negotiation", "last_activity", "next_followup", "priority", "risk", "probability", "notes_summary"]
            st.markdown("<div class='crm-table-shell'>", unsafe_allow_html=True)
            st.dataframe(view[display_cols], use_container_width=True, hide_index=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # ===================== SECTION 4 — COMPANY TIMELINE =====================
    with tabs[3]:
        section_header("Company Deep Timeline", "Chronological week history for one company — mini CRM view.")
        rows = wr.company_activity(session, focus_user, start, end, only_worked=True)
        if not rows:
            empty_state("No worked companies", "No companies were worked on in this week.")
        else:
            options = {f"{r['company']} · {r['lead_id']}": r["lead_id"] for r in rows}
            pick = st.selectbox("Select company", list(options))
            lead_id = options[pick]
            tl = wr.company_timeline(session, lead_id, start, end)
            if not tl:
                empty_state("No activity this week", "No logged actions for this company in the selected week.")
            else:
                st.markdown("<div class='crm-timeline'>", unsafe_allow_html=True)
                for ev in tl:
                    st.markdown(
                        f"""<div class="crm-timeline-item">
                        <div class="crm-timeline-title">{ev['day']} · {ev['type']} <span style="color:#64748b">({ev['source']})</span></div>
                        <div class="crm-timeline-meta">{ev['time']} · {ev['user']} — {ev['detail'] or 'No detail'}</div>
                        </div>""", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

    # ===================== SECTION 5 — LOST ANALYSIS =====================
    with tabs[4]:
        section_header("Lost Opportunity Analysis", f"Deals marked Lost this week ({start:%d %b} → {end:%d %b}) — reason from lost-reason field, falling back to notes.")
        la = wr.lost_analysis(session, focus_user, start, end)
        if la["total_lost"] == 0:
            empty_state("No leads lost this week", "Leads marked Lost inside the selected week will appear here.")
        else:
            st.metric("Lost This Week", la["total_lost"])
            rdf = pd.DataFrame([{"reason": k, "count": v} for k, v in la["reasons"].items()])
            st.plotly_chart(style_plotly(px.bar(rdf, x="reason", y="count", title="Top Loss Reasons"), height=320), use_container_width=True)
            c1, c2 = st.columns(2)
            with c1:
                st.caption("By Salesperson")
                st.dataframe(pd.DataFrame(la["by_person"]).fillna(0).T, use_container_width=True)
            with c2:
                st.caption("By Country")
                st.dataframe(pd.DataFrame(la["by_country"]).fillna(0).T, use_container_width=True)
            st.caption("Lost companies")
            st.dataframe(pd.DataFrame(la["rows"]), use_container_width=True, hide_index=True)

    # ===================== SECTION 7 — INSIGHTS =====================
    with tabs[5]:
        section_header("Management Insights", "Auto-generated business intelligence for this week.")
        for ins in wr.management_insights(session, focus_user, start, end):
            st.markdown(f"""<div class="crm-timeline-item"><div class="crm-timeline-title">💡 {ins}</div></div>""", unsafe_allow_html=True)

    # ===================== SECTION 8 — NEXT WEEK =====================
    with tabs[6]:
        section_header("Next Week Priority Pipeline", "Start Monday with ready tasks.")
        pipe = wr.next_week_pipeline(session, focus_user)
        labels = {"hot_followup": "🔥 Hot/Warm Follow-ups", "negotiation": "🤝 Negotiation",
                  "interested": "👍 Interested", "pending_quotation": "📄 Pending Quotations",
                  "overdue": "⚠️ Overdue", "high_nurture": "🌱 High-potential Nurture"}
        for key, label in labels.items():
            data = pipe.get(key, [])
            with st.expander(f"{label} ({len(data)})", expanded=(key in ("negotiation", "hot_followup"))):
                if not data:
                    st.caption("Nothing here.")
                else:
                    st.dataframe(pd.DataFrame(data)[["company", "salesperson", "score", "band", "status", "next_followup"]],
                                 use_container_width=True, hide_index=True)

    # ===================== SECTION 6 — PRESENT MY WEEK =====================
    with tabs[7]:
        section_header("Present My Week", "Meeting-ready auto-summary for the selected salesperson / team.")
        if st.button("▶ Generate Presentation", use_container_width=True):
            st.session_state["present_ready"] = True
        if st.session_state.get("present_ready"):
            ov = wr.weekly_overview(session, focus_user, start, end)
            who = focus_user.get("full_name") if focus_user["role"] == "Salesperson" else "The Team"
            st.markdown(f"### 🎤 {who} — Week of {start:%d %b} to {end:%d %b}")
            st.markdown("**1. Weekly Summary**")
            st.write(f"Contacted {ov['contacted_week']} companies · {ov['calls']} calls · {ov['whatsapp']} WhatsApp · "
                     f"{ov['emails']} emails · {ov['followups_completed']} follow-ups done · {ov['conversions_week']} conversions.")
            pipe = wr.next_week_pipeline(session, focus_user)
            st.markdown("**2. Wins**")
            st.write(f"{ov['converted_total']} total converted · {ov['negotiation']} in negotiation · {ov['quotations_sent']} quotations out.")
            st.markdown("**3. Challenges / Pending**")
            st.write(f"{ov['overdue_followups']} overdue follow-ups · {ov['pending_followups']} pending.")
            st.markdown("**4. Hot Leads for Next Week**")
            hot = pipe["hot_followup"][:8]
            st.dataframe(pd.DataFrame(hot)[["company", "score", "band", "status"]] if hot else pd.DataFrame(), use_container_width=True, hide_index=True)
            st.markdown("**5. Negotiation Pipeline**")
            neg = pipe["negotiation"][:8]
            st.dataframe(pd.DataFrame(neg)[["company", "score", "next_followup"]] if neg else pd.DataFrame(), use_container_width=True, hide_index=True)
            st.markdown("**6. Companies Needing Management Help** (overdue + high score)")
            help_rows = [r for r in pipe["overdue"] if r["score"] >= 60][:8]
            st.dataframe(pd.DataFrame(help_rows)[["company", "salesperson", "score", "status"]] if help_rows else pd.DataFrame(), use_container_width=True, hide_index=True)

    # ===================== SECTION 10 — EXPORT =====================
    with tabs[8]:
        section_header("Export Weekly Report", "Download Excel / CSV for the meeting.")
        ov = wr.weekly_overview(session, focus_user, start, end)
        perf = wr.salesperson_performance(session, start, end)
        comp = wr.company_activity(session, focus_user, start, end, only_worked=True)
        la = wr.lost_analysis(session, focus_user, start, end)
        pipe = wr.next_week_pipeline(session, focus_user)

        overview_df = pd.DataFrame([ov])
        perf_df = pd.DataFrame(perf)
        comp_df = pd.DataFrame(comp)
        lost_df = pd.DataFrame(la["rows"])
        next_df = pd.DataFrame([{**r, "bucket": k} for k, rows in pipe.items() for r in rows])

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            overview_df.to_excel(writer, sheet_name="Overview", index=False)
            perf_df.to_excel(writer, sheet_name="Salespeople", index=False)
            comp_df.to_excel(writer, sheet_name="Company Activity", index=False)
            (lost_df if not lost_df.empty else pd.DataFrame({"info": ["No lost leads"]})).to_excel(writer, sheet_name="Lost Analysis", index=False)
            (next_df if not next_df.empty else pd.DataFrame({"info": ["No pipeline"]})).to_excel(writer, sheet_name="Next Week", index=False)
        st.download_button("⬇️ Download Full Weekly Report (Excel)", buffer.getvalue(),
                           file_name=f"weekly_review_{start:%Y%m%d}_{end:%Y%m%d}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)
        c1, c2 = st.columns(2)
        if not comp_df.empty:
            c1.download_button("Company Activity CSV", comp_df.to_csv(index=False),
                               file_name=f"company_activity_{start:%Y%m%d}.csv", mime="text/csv", use_container_width=True)
        if not perf_df.empty:
            c2.download_button("Salesperson Report CSV", perf_df.to_csv(index=False),
                               file_name=f"salesperson_{start:%Y%m%d}.csv", mime="text/csv", use_container_width=True)
