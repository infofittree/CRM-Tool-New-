"""Lead management page."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
import streamlit as st

from app.db import ensure_startup, get_db, render_startup_status
from app.ui import configure_page, empty_state, page_header, require_login, score_badge, section_header, status_pill
from database.models import ALLOWED_STATUSES
from modules.clock import today as biz_today
from modules.crm_service import CRMService, COUNTRIES, LEAD_SOURCES


configure_page("Lead Management")
user = require_login("Lead Management")
page_header("Lead Management", "Search, filter, edit, and export live lead records from MySQL.", "Pipeline Control")

db = get_db()
startup_status = ensure_startup(db)
render_startup_status(startup_status)
if startup_status.errors:
    st.error(startup_status.errors[0])
    st.stop()
from app.db import load_leads_df, clear_data_cache
with db.session_scope() as session:
    service = CRMService(session)
    leads = load_leads_df(user["role"], user["full_name"], 1000)
    salespersons = service.get_salespersons()

    with st.expander("Add Lead", expanded=False):
        with st.form("add_lead_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            company_name = col1.text_input("Company Name *")
            contact_person = col2.text_input("Contact Person")
            phone = col3.text_input("Phone")
            email = col1.text_input("Email")
            country = col2.selectbox("Country", COUNTRIES)
            lead_source = col3.selectbox("Lead Source", LEAD_SOURCES)
            assigned_to = col1.selectbox("Assigned Salesperson *", salespersons)
            status = col2.selectbox("Status", ALLOWED_STATUSES)
            next_follow_up = col3.date_input("Next Follow-up Date", value=None)
            remarks = st.text_area("Remarks")
            submitted = st.form_submit_button("Save Lead", use_container_width=True)
        if submitted:
            result = service.save_lead_from_entry(
                {
                    "company_name": company_name,
                    "contact_person": contact_person,
                    "phone": phone,
                    "email": email,
                    "country": country,
                    "lead_source": lead_source,
                    "assigned_to": assigned_to,
                    "status": status,
                    "next_follow_up": next_follow_up,
                    "remarks": remarks,
                },
                user,
                force=False,
            )
            if result.ok:
                st.success(f"Lead saved: {result.lead_id}")
                st.rerun()
            elif result.duplicates:
                st.warning(result.message)
                st.dataframe(pd.DataFrame(result.duplicates), use_container_width=True, hide_index=True)
            else:
                st.error(result.message)

    section_header("Lead Table", "Live records with filters, pagination, and export.")
    if leads.empty:
        empty_state("No leads available", "Add a lead or sync Excel data to populate the table.")
        st.stop()

    # Derive score band for visibility / filtering / sorting
    def _band(score):
        s = float(score or 0)
        return "HOT" if s >= 90 else "WARM" if s >= 70 else "NURTURE" if s >= 50 else "COLD"
    if "lead_score" in leads.columns:
        leads["band"] = leads["lead_score"].map(_band)

    filter_col1, filter_col2, filter_col3, filter_col4, filter_col5 = st.columns(5)
    query = filter_col1.text_input("Search")
    status_filter = filter_col2.multiselect("Status", list(ALLOWED_STATUSES))
    salesperson_filter = filter_col3.multiselect("Salesperson", sorted(leads["assigned_to"].dropna().unique()))
    country_filter = filter_col4.multiselect("Country", sorted(leads["country"].dropna().unique()))
    band_filter = filter_col5.multiselect("Score Band", ["HOT", "WARM", "NURTURE", "COLD"])

    sort_choice = st.radio(
        "Sort", ["Highest score first", "Lowest score first", "Most recent"], horizontal=True
    )

    filtered = leads.copy()
    if query:
        mask = filtered.astype(str).apply(lambda col: col.str.contains(query, case=False, na=False)).any(axis=1)
        filtered = filtered[mask]
    if status_filter:
        filtered = filtered[filtered["status"].isin(status_filter)]
    if salesperson_filter:
        filtered = filtered[filtered["assigned_to"].isin(salesperson_filter)]
    if country_filter:
        filtered = filtered[filtered["country"].isin(country_filter)]
    if band_filter and "band" in filtered.columns:
        filtered = filtered[filtered["band"].isin(band_filter)]

    if "lead_score" in filtered.columns:
        if sort_choice == "Highest score first":
            filtered = filtered.sort_values("lead_score", ascending=False)
        elif sort_choice == "Lowest score first":
            filtered = filtered.sort_values("lead_score", ascending=True)

    if filtered.empty:
        empty_state("No leads match the current filters", "Adjust the search or remove one of the filters.")
        st.stop()

    # Surface score columns first for visibility
    if "lead_score" in filtered.columns:
        front = [c for c in ["lead_id", "company_name", "lead_score", "band", "standard_status", "assigned_to", "country"] if c in filtered.columns]
        rest = [c for c in filtered.columns if c not in front]
        filtered = filtered[front + rest]

    page_col1, page_col2 = st.columns([1, 1])
    page_size = page_col1.selectbox("Rows per page", [25, 50, 100, 250], index=1)
    total_pages = max((len(filtered) - 1) // page_size + 1, 1)
    page_number = page_col2.number_input("Page", min_value=1, max_value=total_pages, value=1)
    start = (page_number - 1) * page_size
    paged = filtered.iloc[start : start + page_size]

    st.caption(f"Showing {len(paged)} of {len(filtered)} leads")
    st.download_button("Export Filtered Leads CSV", filtered.to_csv(index=False), file_name=f"leads_{biz_today()}.csv", mime="text/csv")
    st.markdown("<div class='crm-table-shell'>", unsafe_allow_html=True)
    st.dataframe(paged, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

    section_header("Lead Detail", "Review and update the selected account.")
    selected = st.selectbox("Select Lead", filtered["lead_id"].tolist())
    detail = filtered[filtered["lead_id"] == selected].iloc[0].to_dict()
    left, right = st.columns([1, 1])
    with left:
        st.markdown(
            f"""
            <div class="crm-section">
                <div class="crm-section-title">{detail.get('company_name')}</div>
                <div class="crm-section-subtitle">{detail.get('lead_id')} | {detail.get('assigned_to') or 'Unassigned'}</div>
                <p><b>Score</b> {score_badge(detail.get('lead_score'), detail.get('band'))}</p>
                <p><b>Status</b> {status_pill(detail.get('standard_status') or detail.get('status'))}</p>
                <p><b>Contact</b> {detail.get('contact_person') or '-'} | {detail.get('phone') or '-'}</p>
                <p><b>Email</b> {detail.get('email') or '-'}</p>
                <p><b>Country</b> {detail.get('country') or '-'}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        from modules.dropdown_config import option_list
        from datetime import date, timedelta
        _lost_reasons = option_list("lost_reasons")
        _sl = list(ALLOWED_STATUSES)
        _si = _sl.index(detail["status"]) if detail["status"] in _sl else 0
        new_status = st.selectbox("Update Status", _sl, index=_si)
        # Lead Category — always editable (buyer quality changes over time)
        _cats = ["A", "B", "C"]
        _cur_cat = str(detail.get("lead_category") or "").strip().upper()
        _cat_opts = ["— select —"] + _cats
        _cat_idx = _cat_opts.index(_cur_cat) if _cur_cat in _cats else 0
        new_category = st.selectbox("Lead Category (A/B/C) *", _cat_opts, index=_cat_idx,
                                    help="Reclassify as buyer quality changes.")
        # Alibaba Buyer Level — only for Alibaba-source leads
        new_level = None
        if str(detail.get("lead_source") or "").strip().lower() == "alibaba":
            _lvls = ["— none —", "L1", "L2", "L3", "L4"]
            _cur_lvl = str(detail.get("buyer_tag") or "").strip().upper()
            _lvl_idx = _lvls.index(_cur_lvl) if _cur_lvl in _lvls else 0
            new_level = st.selectbox("Alibaba Buyer Level", _lvls, index=_lvl_idx)
            from modules.lead_scoring import suggest_category_from_alibaba_level
            _sug = suggest_category_from_alibaba_level(None if new_level == "— none —" else new_level)
            if _sug:
                st.caption(f"💡 Suggested category for {new_level}: **{_sug}** (override allowed)")
        # Lost reason appears (mandatory) only when Lost is chosen
        lost_reason = "—"
        if new_status == "Lost":
            lost_reason = st.selectbox("Lost Reason * (mandatory)", ["—"] + _lost_reasons)
        next_plan = st.text_input("Next Action Plan *", value=str(detail.get("next_action_plan") or ""))
        next_fu = st.date_input("Next Follow-up * (max 30 days)", value=biz_today() + timedelta(days=2),
                                max_value=biz_today() + timedelta(days=30))
        new_remarks = st.text_area("Add Notes", value=str(detail.get("remarks") or ""))
        if st.button("Save Updates", use_container_width=True):
            _is_lost = new_status == "Lost"
            if _is_lost and lost_reason == "—":
                st.error("Lost Reason is mandatory when marking a lead as Lost.")
            elif not _is_lost and not next_plan.strip():
                st.error("Next Action Plan is mandatory.")  # not required for Lost (Phase 5)
            elif new_category == "— select —":
                st.error("Lead Category (A/B/C) is mandatory.")
            else:
                service.update_lead_full(
                    selected,
                    {"discussion": new_remarks, "next_action": next_plan, "next_followup": next_fu,
                     "status": new_status, "lost_reason": None if lost_reason == "—" else lost_reason,
                     "lead_category": new_category,
                     "buyer_tag": None if (new_level in (None, "— none —")) else new_level},
                    user,
                )
                clear_data_cache()
                st.success("Lead updated and next follow-up scheduled.")
                st.rerun()
        if st.button("✅ Mark Order Closed (Won)", use_container_width=True):
            service.add_quick_followup(
                selected,
                {"discussion": "Order closed — won", "next_action": "Move to customer success",
                 "next_followup": biz_today() + timedelta(days=30), "status": "Order Closed"},
                user,
            )
            clear_data_cache()
            st.success("Lead marked Order Closed.")
            st.rerun()
        st.divider()
        # ---- Transfer Lead (Phase 4) ----
        st.markdown("**Transfer Lead**")
        _others = [s for s in salespersons if s != detail.get("assigned_to")]
        tcol1, tcol2 = st.columns([2, 1])
        transfer_to = tcol1.selectbox("Transfer to", _others if _others else salespersons, key=f"xfer_{selected}")
        transfer_reason = st.text_input("Transfer reason (optional)", key=f"xreason_{selected}")
        if tcol2.button("Transfer", use_container_width=True, key=f"xbtn_{selected}"):
            if service.transfer_lead(selected, transfer_to, user, transfer_reason or None):
                clear_data_cache()
                st.success(f"Lead transferred to {transfer_to}.")
                st.rerun()
            else:
                st.warning("Transfer not applied (same owner or lead missing).")

        st.divider()
        # ---- Delete Lead with confirmation (Phase 3) ----
        st.markdown("**Danger zone**")
        if not st.session_state.get(f"confirm_del_{selected}"):
            if st.button("🗑️ Delete Lead", use_container_width=True, key=f"del_{selected}"):
                st.session_state[f"confirm_del_{selected}"] = True
                st.rerun()
        else:
            st.error("Are you sure you want to delete this lead? It will be logged and recoverable.")
            del_reason = st.text_input("Reason (optional)", key=f"delreason_{selected}")
            dc1, dc2 = st.columns(2)
            if dc1.button("Yes, delete", use_container_width=True, key=f"delyes_{selected}"):
                service.delete_lead_logged(selected, user, del_reason or None)
                st.session_state.pop(f"confirm_del_{selected}", None)
                clear_data_cache()
                st.warning("Lead deleted and logged to deleted_leads.")
                st.rerun()
            if dc2.button("Cancel", use_container_width=True, key=f"delno_{selected}"):
                st.session_state.pop(f"confirm_del_{selected}", None)
                st.rerun()
