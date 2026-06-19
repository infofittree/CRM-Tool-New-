"""Fast, minimal lead entry — only what a salesperson needs to capture."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
import streamlit as st

from app.db import ensure_startup, get_db, render_startup_status
from app.ui import configure_page, empty_state, page_header, require_login, section_header
from modules.clock import today as biz_today
from modules.crm_service import CRMService
from modules.dropdown_config import option_list
from modules.geo import ALL_COUNTRIES, LEAD_SOURCES, country_continent
from modules.status_taxonomy import CANONICAL_STATUSES

COUNTRIES = ALL_COUNTRIES

configure_page("Data Entry")
user = require_login("Data Entry")
page_header("Add Lead", "Capture the essentials and move on — the CRM handles the rest.", "Fast Entry")

db = get_db()
startup_status = ensure_startup(db)
render_startup_status(startup_status)
if startup_status.errors:
    st.error(startup_status.errors[0])
    st.stop()

LOST_REASONS = option_list("lost_reasons")
CATEGORIES = ["— select —", "A", "B", "C"]
ENGAGEMENT = ["Frequent", "Medium", "Low"]
MAX_FU = biz_today() + timedelta(days=30)

with db.session_scope() as session:
    service = CRMService(session)
    salespersons = service.get_salespersons()
    leads_df = service.leads_dataframe(user, limit=2000)

    entry_tab, followup_tab, bulk_tab = st.tabs(["➕ New Lead", "⚡ Quick Follow-up", "📥 Bulk Upload"])

    # ---------------- NEW LEAD (slim) ----------------
    with entry_tab:
        if st.session_state.get("pending_duplicates"):
            st.warning("Possible duplicate detected:")
            st.dataframe(pd.DataFrame(st.session_state["pending_duplicates"]), use_container_width=True, hide_index=True)
            cc1, cc2 = st.columns(2)
            if cc1.button("Save Anyway", use_container_width=True):
                r = service.save_lead_from_entry(st.session_state["pending_payload"], user, force=True)
                st.session_state.pop("pending_duplicates", None); st.session_state.pop("pending_payload", None)
                st.success(f"Saved {r.lead_id}") if r.ok else st.error(r.message)
                st.rerun()
            if cc2.button("Cancel", use_container_width=True):
                st.session_state.pop("pending_duplicates", None); st.session_state.pop("pending_payload", None)
                st.rerun()

        # Source + Alibaba level live OUTSIDE the form so the Alibaba field and
        # category suggestion react instantly (Streamlit forms don't rerun mid-edit).
        from modules.lead_scoring import suggest_category_from_alibaba_level
        sc1, sc2 = st.columns(2)
        lead_source = sc1.selectbox("Lead Source *", LEAD_SOURCES, key="de_source")
        alibaba_level = None
        suggested_cat = None
        if lead_source == "Alibaba":
            alibaba_level = sc2.selectbox("Alibaba Buyer Level *", ["NEW", "L1", "L2", "L3", "L4"], key="de_alibaba",
                                          help="NEW = just enquired · L4/L3 = strong → A · L2 = medium → B · L1 = low → C")
            suggested_cat = suggest_category_from_alibaba_level(alibaba_level)
            if suggested_cat:
                sc2.caption(f"💡 Suggested category: **{suggested_cat}** (you can override below)")
        # Default category index → suggestion when present
        _cat_default = CATEGORIES.index(suggested_cat) if suggested_cat in CATEGORIES else 0

        with st.form("fast_lead", clear_on_submit=True):
            st.caption("Fields marked * are mandatory. The CRM will block save without them.")
            c1, c2, c3 = st.columns(3)
            company_name = c1.text_input("Company Name (optional)")
            contact_person = c2.text_input("Contact Person *")
            country = c3.selectbox("Country *", COUNTRIES)
            phone = c1.text_input("Contact Number (optional)")
            email = c2.text_input("Email (optional)")
            product_interest = c3.text_input("Product Requirement")
            # Continent auto-fills from country — shown read-only for confidence
            c3.caption(f"🌍 Continent (auto): {country_continent(country) or '—'}")

            c4, c5, c6 = st.columns(3)
            status = c4.selectbox("Funnel Status *", list(CANONICAL_STATUSES))
            lead_category = c5.selectbox("Lead Category *", CATEGORIES, index=_cat_default,
                                         help="A = High potential · B = Medium · C = Low. You must choose.")
            c6.caption(f"Source: **{lead_source}**" + (f" · Level: **{alibaba_level}**" if alibaba_level else ""))

            c7, c8, c9 = st.columns(3)
            engagement = c7.selectbox("Buyer Engagement *", ENGAGEMENT,
                                      help="How often the buyer communicates with us")
            assigned_to = c8.selectbox("Owner / Salesperson *", salespersons)
            inquiry_date = c9.date_input("Inquiry Date (when buyer enquired)",
                                         value=biz_today(), max_value=biz_today())
            next_follow_up = c7.date_input("Follow-up Date * (max 30 days)",
                                           value=biz_today() + timedelta(days=2),
                                           min_value=biz_today() - timedelta(days=1),
                                           max_value=MAX_FU)
            lost_reason = c8.selectbox("Lost Reason (only if Lost)", ["—"] + LOST_REASONS)

            next_action_plan = st.text_input("Next Action Plan *",
                                             placeholder="e.g. Call buyer for quotation feedback")
            with st.expander("Optional details"):
                oc1, oc2 = st.columns(2)
                website = oc1.text_input("Website")
                notes = oc2.text_input("Notes")

            submitted = st.form_submit_button("💾 Save Lead", use_container_width=True)

        if submitted:
            payload = {
                "company_name": company_name, "contact_person": contact_person, "country": country,
                "phone": phone, "email": email, "product_interest": product_interest,
                "status": status,
                "lead_category": "" if lead_category == "— select —" else lead_category,
                "lead_source": lead_source,
                "buyer_tag": alibaba_level if lead_source == "Alibaba" else None,
                "buyer_engagement_frequency": engagement, "assigned_to": assigned_to,
                "next_follow_up": next_follow_up, "next_action_plan": next_action_plan,
                "lost_reason": None if lost_reason == "—" else lost_reason,
                "inquiry_date": inquiry_date,
                "website": website, "remarks": notes,
            }
            with st.spinner("Validating & saving..."):
                result = service.save_lead_from_entry(payload, user, force=False)
            if result.ok:
                st.success(f"✅ Lead saved: {result.lead_id}")
                st.cache_data.clear(); st.rerun()
            elif result.duplicates:
                st.session_state["pending_payload"] = payload
                st.session_state["pending_duplicates"] = result.duplicates
                st.rerun()
            else:
                st.error("❌ " + result.message)

    # ---------------- QUICK FOLLOW-UP ----------------
    with followup_tab:
        section_header("Log a Follow-up", "Update status + schedule the next action in one step.")
        if leads_df.empty:
            empty_state("No leads yet", "Add a lead first.")
        else:
            opts = {f"{r.company_name} | {r.lead_id}": r.lead_id for r in leads_df.itertuples()}
            with st.form("quick_fu", clear_on_submit=True):
                pick = st.selectbox("Company", list(opts))
                discussion = st.text_area("What happened?")
                f1, f2 = st.columns(2)
                new_status = f1.selectbox("Update Status", list(CANONICAL_STATUSES))
                next_fu = f2.date_input("Next Follow-up * (max 30d)", value=biz_today() + timedelta(days=2),
                                        max_value=MAX_FU)
                next_plan = st.text_input("Next Action Plan *", placeholder="What will you do next?")
                lr = st.selectbox("Lost Reason (if Lost)", ["—"] + LOST_REASONS)
                done = st.form_submit_button("Save Follow-up", use_container_width=True)
            if done:
                if not next_plan.strip():
                    st.error("Next Action Plan is mandatory.")
                elif new_status == "Lost" and lr == "—":
                    st.error("Lost Reason is mandatory when status is Lost.")
                else:
                    service.add_quick_followup(
                        opts[pick],
                        {"discussion": discussion, "next_action": next_plan, "next_followup": next_fu,
                         "status": new_status, "lost_reason": None if lr == "—" else lr},
                        user,
                    )
                    st.success("Follow-up saved."); st.cache_data.clear(); st.rerun()

    # ---------------- BULK ----------------
    with bulk_tab:
        section_header("Bulk Upload", "Preview then import valid rows.")
        up = st.file_uploader("Excel or CSV", type=["xlsx", "csv"])
        if up:
            try:
                bdf = pd.read_csv(up) if up.name.lower().endswith(".csv") else pd.read_excel(up, engine="openpyxl")
                st.dataframe(bdf.head(30), use_container_width=True, hide_index=True)
                if st.button("Import Valid Rows", use_container_width=True):
                    summary = service.bulk_import_dataframe(bdf, user)
                    st.json(summary); st.cache_data.clear()
            except Exception as exc:
                st.error(f"Could not import: {exc}")
