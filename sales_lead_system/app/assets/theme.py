"""Shared CRM theme constants and Plotly helpers."""

from __future__ import annotations

from typing import Any


COLORS = {
    "primary": "#4F46E5",
    "secondary": "#7C3AED",
    "accent": "#06B6D4",
    "success": "#10B981",
    "warning": "#F59E0B",
    "danger": "#EF4444",
    "background": "#F8FAFC",
    "card": "#FFFFFF",
    "text": "#0F172A",
    "muted": "#64748B",
    "border": "#E2E8F0",
}

CHART_SEQUENCE = [
    COLORS["primary"],
    COLORS["accent"],
    COLORS["success"],
    COLORS["warning"],
    COLORS["secondary"],
    COLORS["danger"],
    "#0EA5E9",
    "#14B8A6",
]

STATUS_COLORS = {
    # New 10-stage funnel
    "Prospect": "#2563EB",
    "Requirement Qualified": "#0284C7",
    "Technical Discussion": "#0E7490",
    "Quotation Sent": "#D97706",
    "Sample Sent": "#C2410C",
    "Negotiation": "#92400E",
    "Trial Order": "#5B21B6",
    "Order Closed": "#15803D",
    "Nurturing": COLORS["secondary"],
    "Lost": COLORS["danger"],
    # Legacy values (for un-migrated or old chart data)
    "NEW": "#2563EB",
    "Active": "#2563EB",
    "Nurture": COLORS["secondary"],
    "Inactive": COLORS["muted"],
    "Negotiation_old": COLORS["warning"],
    "Converted": "#15803D",
}

KPI_META = {
    "Total Leads": ("TL", COLORS["primary"]),
    "Active Leads": ("AL", COLORS["accent"]),
    "Nurturing Leads": ("NL", COLORS["secondary"]),
    "Due Today": ("DT", COLORS["warning"]),
    "Overdue": ("OF", COLORS["danger"]),
    "Hot Leads": ("HL", COLORS["warning"]),
    "Inactive Leads": ("IL", COLORS["muted"]),
    "Converted": ("CL", COLORS["success"]),
    "Conversion Rate": ("CR", "#0EA5E9"),
}


def style_plotly(fig: Any, height: int = 420) -> Any:
    """Apply the CRM visual theme to a Plotly figure."""
    fig.update_layout(
        height=height,
        paper_bgcolor=COLORS["card"],
        plot_bgcolor=COLORS["card"],
        font={"family": "Inter, Segoe UI, sans-serif", "color": COLORS["text"], "size": 13},
        title={"font": {"size": 16, "color": COLORS["text"]}, "x": 0.02, "xanchor": "left"},
        colorway=CHART_SEQUENCE,
        margin={"l": 12, "r": 12, "t": 48, "b": 16},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
    )
    fig.update_xaxes(showgrid=True, gridcolor="#EEF2F7", zeroline=False, linecolor=COLORS["border"])
    fig.update_yaxes(showgrid=True, gridcolor="#EEF2F7", zeroline=False, linecolor=COLORS["border"])
    return fig
