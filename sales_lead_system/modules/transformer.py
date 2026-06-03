"""Transform cleaned workbook sheets into CRM-ready entities."""

from __future__ import annotations

import logging
from datetime import date

import pandas as pd


class DataTransformer:
    """Convert cleaned sheet dataframes into leads and follow-up tables."""

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    def build_leads(self, sheets: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Build one lead dataframe from lead-like workbook sheets."""
        frames: list[pd.DataFrame] = []
        for sheet_name, df in sheets.items():
            if not self._is_lead_sheet(df):
                continue
            source = sheet_name.strip()
            frame = pd.DataFrame(
                {
                    "legacy_buyer_id": self._first(df, ["buyer_id"]),
                    "buyer_tag": self._first(df, ["buyer_tag"]),
                    "company_name": self._first(df, ["company_buyer_name", "buyer_name", "company_name"]),
                    "website": self._first(df, ["website"]),
                    "industry": self._first(df, ["industry"]),
                    "city": self._first(df, ["city"]),
                    "continent": self._first(df, ["continent"]),
                    "contact_person": self._first(df, ["contact_person"]),
                    "designation": self._first(df, ["designation"]),
                    "phone": self._first(df, ["phone"]),
                    "alternate_number": self._first(df, ["alternate_number"]),
                    "whatsapp_number": self._first(df, ["whatsapp_number", "whatsapp"]),
                    "email": self._first(df, ["email"]),
                    "country": self._first(df, ["country"]),
                    "status": self._first(df, ["status"]).fillna("NEW"),
                    "assigned_to": self._first(df, ["assigned_to"]),
                    "transfer_to": self._first(df, ["transfer_to"]),
                    "lead_source": self._first(df, ["source"]).fillna(source),
                    "created_date": self._first(df, ["first_contact_date", "created_date"]).fillna(date.today().isoformat()),
                    "last_contact_date": self._first(df, ["last_contact_date"]),
                    "next_follow_up": self._first(df, ["next_follow_up", "next_follow_up_date", "next_followup"]),
                    "product_interest": self._first(df, ["product_interest", "product"]),
                    "probability": self._first(df, ["propability", "probability"]),
                    "follow_up_stage": self._first(df, ["follow_up_stage"]),
                    "mode": self._first(df, ["mode"]),
                    "quotation_status": self._first(df, ["quotation_status"]),
                    "remarks": self._first(df, ["remarks", "procurment_remarks", "procurement_remarks"]),
                    "procurement_remarks": self._first(df, ["procurement_remarks", "procurment_remarks"]),
                    # Phase 3 fields — aligned with updated Google Sheet (2026-06-01)
                    "first_contact_date": self._first(df, ["first_contact_date"]),
                    "sheet_source": source,
                }
            )
            frame["company_name"] = frame["company_name"].fillna(frame["contact_person"]).fillna(frame["legacy_buyer_id"])
            frames.append(frame)

        if not frames:
            self.logger.warning("No lead-like sheets were found")
            return pd.DataFrame()

        leads = pd.concat(frames, ignore_index=True)
        leads = leads.dropna(how="all")
        leads = leads[leads["company_name"].notna() | leads["email"].notna() | leads["phone"].notna()].copy()
        leads = leads.drop_duplicates(subset=["legacy_buyer_id", "company_name", "email", "phone"], keep="first")
        self.logger.info("Built %s normalized lead rows", len(leads))
        return leads

    def build_followups(self, sheets: dict[str, pd.DataFrame], leads: pd.DataFrame) -> pd.DataFrame:
        """Build follow-up dataframe and map legacy buyer IDs to generated lead IDs."""
        frames: list[pd.DataFrame] = []
        lead_lookup = (
            leads.dropna(subset=["legacy_buyer_id"])
            .drop_duplicates("legacy_buyer_id")
            .set_index("legacy_buyer_id")["lead_id"]
            .to_dict()
            if "legacy_buyer_id" in leads.columns and "lead_id" in leads.columns
            else {}
        )

        for _, df in sheets.items():
            if not self._is_followup_sheet(df):
                continue
            legacy_ids = self._first(df, ["buyer_id"])
            frame = pd.DataFrame(
                {
                    "lead_id": legacy_ids.map(lead_lookup),
                    "legacy_buyer_id": legacy_ids,
                    "buyer_name": self._first(df, ["buyer_name", "company_buyer_name", "company_name"]),
                    "country": self._first(df, ["country"]),
                    "assigned_to": self._first(df, ["assigned_to"]),
                    "transfer_to": self._first(df, ["transfer_to"]),
                    "followup_date": self._first(df, ["last_contact_date", "followup_date"]),
                    "discussion": self._first(df, ["discussion_summary", "discussion", "remarks"]),
                    "next_action": self._first(df, ["next_action", "status"]),
                    "next_followup": self._first(df, ["next_follow_up_date", "next_followup", "next_follow_up"]),
                    "mode": self._first(df, ["mode"]),
                    "status": self._first(df, ["status"]),
                    "updated_by": self._first(df, ["assigned_to", "updated_by"]),
                }
            )
            frames.append(frame)

        if not frames:
            return pd.DataFrame()
        followups = pd.concat(frames, ignore_index=True)
        followups = followups[followups["lead_id"].notna() | followups["discussion"].notna()].copy()
        self.logger.info("Built %s normalized follow-up rows", len(followups))
        return followups

    def build_orders(self, sheets: dict[str, pd.DataFrame], leads: pd.DataFrame) -> pd.DataFrame:
        """Build order tracker rows from the Order_Tracker tab."""
        df = sheets.get("Order_Tracker")
        if df is None or df.empty:
            return pd.DataFrame()
        lead_lookup = (
            leads.dropna(subset=["legacy_buyer_id"])
            .drop_duplicates("legacy_buyer_id")
            .set_index("legacy_buyer_id")["lead_id"]
            .to_dict()
            if "legacy_buyer_id" in leads.columns and "lead_id" in leads.columns
            else {}
        )
        legacy_ids = self._first(df, ["buyer_id"])
        orders = pd.DataFrame(
            {
                "lead_id": legacy_ids.map(lead_lookup),
                "legacy_buyer_id": legacy_ids,
                "buyer_name": self._first(df, ["buyer_name"]),
                "product": self._first(df, ["product"]),
                "category": self._first(df, ["category"]),
                "quantity": self._first(df, ["quantity"]),
                "order_value": self._first(df, ["order_value"]),
                "currency": self._first(df, ["currency"]),
                "order_date": self._first(df, ["order_date"]),
                "dispatch_date": self._first(df, ["dispatch_date"]),
                "payment_terms": self._first(df, ["payment_terms"]),
                "payment_status": self._first(df, ["payment_status"]),
                "order_status": self._first(df, ["order_status"]),
                "handled_by": self._first(df, ["handled_by", "assigned_to"]),
            }
        )
        orders = orders[orders["legacy_buyer_id"].notna() | orders["buyer_name"].notna() | orders["product"].notna()].copy()
        # Drop rows where order_value is clearly not numeric (corrupted column mapping)
        def _is_numeric(v):
            if v is None:
                return True
            try:
                float(str(v).replace(",", ""))
                return True
            except (ValueError, TypeError):
                return False
        if "order_value" in orders.columns:
            orders = orders[orders["order_value"].apply(_is_numeric)].copy()
        self.logger.info("Built %s normalized order rows", len(orders))
        return orders

    @staticmethod
    def _first(df: pd.DataFrame, columns: list[str]) -> pd.Series:
        for column in columns:
            if column in df.columns:
                return df[column]
        return pd.Series([None] * len(df), index=df.index)

    @staticmethod
    def _is_lead_sheet(df: pd.DataFrame) -> bool:
        return bool({"company_buyer_name", "company_name", "email", "phone"} & set(df.columns))

    @staticmethod
    def _is_followup_sheet(df: pd.DataFrame) -> bool:
        return bool({"discussion_summary", "next_follow_up_date", "next_followup"} & set(df.columns))
