"""Country normalisation + continent auto-mapping.

Single source of truth for cleaning messy country values and deriving the
continent automatically. Canonical country form is UPPERCASE to match the
existing stored data and the COUNTRIES dropdown.
"""

from __future__ import annotations

# Variant (UPPER, stripped) → canonical country (UPPER)
_COUNTRY_NORMALISE: dict[str, str] = {
    "AFHGHANISTAN": "AFGHANISTAN",
    "CANDA": "CANADA",
    "CANADA-CHINA": "CANADA",
    "CHEZ REPUBLIC": "CZECH REPUBLIC",
    "CZECHIA": "CZECH REPUBLIC",
    "DUBAI": "UNITED ARAB EMIRATES",
    "UAE": "UNITED ARAB EMIRATES",
    "U.A.E": "UNITED ARAB EMIRATES",
    "ISREAL": "ISRAEL",
    "LABENON": "LEBANON",
    "NETHERLAND": "NETHERLANDS",
    "NETHLANDS": "NETHERLANDS",
    "HOLLAND": "NETHERLANDS",
    "NEW ZEALEND": "NEW ZEALAND",
    "NEWZEALAND": "NEW ZEALAND",
    "PHILLIPINS": "PHILIPPINES",
    "PHILIPPINS": "PHILIPPINES",
    "NORTH MACDONIA": "NORTH MACEDONIA",
    "MACEDONIA": "NORTH MACEDONIA",
    "SEBIA": "SERBIA",
    "KOREA": "SOUTH KOREA",
    "REPUBLIC OF KOREA": "SOUTH KOREA",
    "UNTIED KINGDOM": "UNITED KINGDOM",
    "UK": "UNITED KINGDOM",
    "U.K": "UNITED KINGDOM",
    "GREAT BRITAIN": "UNITED KINGDOM",
    "ENGLAND": "UNITED KINGDOM",
    "VEITNAM": "VIETNAM",
    "VIET NAM": "VIETNAM",
    "USA": "UNITED STATES",
    "U.S.A": "UNITED STATES",
    "US": "UNITED STATES",
    "AMERICA": "UNITED STATES",
    "COTE DIVOIRE": "COTE D'IVOIRE",
    "IVORY COAST": "COTE D'IVOIRE",
    "KSA": "SAUDI ARABIA",
}

# Canonical country (UPPER) → continent
_COUNTRY_CONTINENT: dict[str, str] = {
    # Asia
    "INDIA": "Asia", "CHINA": "Asia", "JAPAN": "Asia", "SOUTH KOREA": "Asia",
    "VIETNAM": "Asia", "THAILAND": "Asia", "MALAYSIA": "Asia", "SINGAPORE": "Asia",
    "INDONESIA": "Asia", "PHILIPPINES": "Asia", "BANGLADESH": "Asia", "SRI LANKA": "Asia",
    "MALDIVES": "Asia", "LAOS": "Asia", "TAIWAN": "Asia", "HONG KONG": "Asia",
    "TAJIKISTAN": "Asia", "AFGHANISTAN": "Asia", "GEORGIA": "Asia",
    # GCC / Middle East → Asia
    "UNITED ARAB EMIRATES": "Asia", "SAUDI ARABIA": "Asia", "QATAR": "Asia",
    "KUWAIT": "Asia", "OMAN": "Asia", "BAHRAIN": "Asia", "YEMEN": "Asia",
    "IRAQ": "Asia", "IRAN": "Asia", "JORDAN": "Asia", "LEBANON": "Asia",
    "ISRAEL": "Asia", "TURKEY": "Asia",
    # Europe
    "GERMANY": "Europe", "FRANCE": "Europe", "UNITED KINGDOM": "Europe",
    "NETHERLANDS": "Europe", "ITALY": "Europe", "SPAIN": "Europe", "PORTUGAL": "Europe",
    "BELGIUM": "Europe", "SWEDEN": "Europe", "NORWAY": "Europe", "DENMARK": "Europe",
    "FINLAND": "Europe", "POLAND": "Europe", "AUSTRIA": "Europe", "SWITZERLAND": "Europe",
    "IRELAND": "Europe", "ROMANIA": "Europe", "HUNGARY": "Europe", "CZECH REPUBLIC": "Europe",
    "UKRAINE": "Europe", "RUSSIA": "Europe", "MOLDOVA": "Europe", "SERBIA": "Europe",
    "ALBANIA": "Europe", "NORTH MACEDONIA": "Europe", "ESTONIA": "Europe",
    "LATVIA": "Europe", "LITHUANIA": "Europe", "GREECE": "Europe",
    # Africa
    "NIGERIA": "Africa", "KENYA": "Africa", "SOUTH AFRICA": "Africa", "EGYPT": "Africa",
    "ALGERIA": "Africa", "MOROCCO": "Africa", "ANGOLA": "Africa", "CAMEROON": "Africa",
    "TANZANIA": "Africa", "LIBYA": "Africa", "MAURITANIA": "Africa", "COTE D'IVOIRE": "Africa",
    "GHANA": "Africa", "ETHIOPIA": "Africa", "UGANDA": "Africa",
    # North America
    "UNITED STATES": "North America", "CANADA": "North America", "MEXICO": "North America",
    "COSTA RICA": "North America", "ANGUILLA": "North America",
    # South America
    "BRAZIL": "South America", "ARGENTINA": "South America", "ECUADOR": "South America",
    "CHILE": "South America", "PERU": "South America", "COLOMBIA": "South America",
    # Oceania
    "AUSTRALIA": "Oceania", "NEW ZEALAND": "Oceania",
}


def normalize_country(raw: str | None) -> str | None:
    """Return the cleaned, standardized country name (UPPER), or None."""
    if not raw:
        return None
    key = " ".join(str(raw).strip().upper().split())  # collapse internal whitespace
    if not key:
        return None
    return _COUNTRY_NORMALISE.get(key, key)


def country_continent(raw: str | None) -> str | None:
    """Return the continent for a (raw or clean) country name, or None."""
    country = normalize_country(raw)
    if not country:
        return None
    return _COUNTRY_CONTINENT.get(country)


# Standardized lists for dropdowns / filters
CONTINENTS = ["Asia", "Africa", "Europe", "North America", "South America", "Oceania", "Antarctica"]

ALL_COUNTRIES = sorted(set(_COUNTRY_CONTINENT.keys()))


# Lead source normalisation (old stored values → new dropdown values)
LEAD_SOURCES = ["Go4", "Alibaba", "Trademo", "Dataverse", "AI", "LinkedIn", "Spice Exchange", "Other"]

_SOURCE_NORMALISE: dict[str, str] = {
    "GO4BUYER": "Go4",
    "GO4 BUYER": "Go4",
    "GO4": "Go4",
    "ALIBABA": "Alibaba",
    "TRADE MO": "Trademo",
    "TRADEMO": "Trademo",
    "DATA VERSE": "Dataverse",
    "DATAVERSE": "Dataverse",
    "AI": "AI",
    "LINKEDIN": "LinkedIn",
    "SPICE EXCHANGE": "Spice Exchange",
    "HPP": "Other",
    "YELLOW PAGES": "Other",
    "REFERRAL": "Other",
    "WEBSITE": "Other",
    "BUYER_MASTER": "Other",
    "EXHIBITION": "Other",
    "INDIAMART": "Other",
    "OTHER": "Other",
}


def normalize_source(raw: str | None) -> str | None:
    """Return the cleaned lead source matching the new dropdown, or None."""
    if not raw:
        return None
    key = " ".join(str(raw).strip().upper().split())
    return _SOURCE_NORMALISE.get(key, "Other")
