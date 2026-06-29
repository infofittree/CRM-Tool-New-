"""Shared CRM theme constants and Plotly helpers."""

from __future__ import annotations

from typing import Any


# ── Brand colors ──
COLORS = {
    "primary": "#4F46E5",
    "primary_light": "#6366F1",
    "primary_dark": "#4338CA",
    "secondary": "#7C3AED",
    "accent": "#06B6D4",
    "accent_light": "#22D3EE",
    "success": "#10B981",
    "success_light": "#34D399",
    "warning": "#F59E0B",
    "warning_light": "#FBBF24",
    "danger": "#EF4444",
    "danger_light": "#F87171",
    # Surfaces
    "background": "#F1F5F9",
    "card": "#FFFFFF",
    "glass": "rgba(255, 255, 255, 0.72)",
    # Text
    "text": "#0F172A",
    "text_secondary": "#334155",
    "muted": "#64748B",
    "muted_light": "#94A3B8",
    # Borders
    "border": "#E2E8F0",
    "border_light": "#F1F5F9",
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
    # Legacy
    "NEW": "#2563EB",
    "Active": "#2563EB",
    "Nurture": COLORS["secondary"],
    "Inactive": COLORS["muted"],
    "Negotiation_old": COLORS["warning"],
    "Converted": "#15803D",
}

SCORE_BAND_COLORS = {
    "HOT": {"bg": "#FEE2E2", "text": "#B91C1C", "border": "#FECACA", "emoji": "🔥"},
    "WARM": {"bg": "#FFEDD5", "text": "#C2410C", "border": "#FED7AA", "emoji": "🟠"},
    "NURTURE": {"bg": "#FEF9C3", "text": "#854D0E", "border": "#FDE047", "emoji": "🟡"},
    "COLD": {"bg": "#E0F2FE", "text": "#0369A1", "border": "#BAE6FD", "emoji": "🔵"},
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
    "Today's Tasks": ("TT", COLORS["primary"]),
    "Upcoming 7d": ("U7", COLORS["accent"]),
    "Negotiation": ("NG", "#92400E"),
    "Task Completion": ("TC", COLORS["success"]),
}

BAND_ORDER = ["HOT", "WARM", "NURTURE", "COLD"]


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
