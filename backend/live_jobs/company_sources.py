"""Which companies to query, and from which public feed.

Each entry maps a canonical company display name to one or more
``(source_name, token)`` pairs, where ``source_name`` is a key in
``live_jobs.sources.SOURCES`` and ``token`` is that feed's board slug
(empty string for per-company adapters that don't need one).

Every token here was verified to return live postings from the ATS's
public, unauthenticated endpoint. Add or fix entries in this one file -
companies not listed here are simply not queried. ``companies.py`` stays
the broader "target universe"; this is the subset we can fetch today.
"""

from __future__ import annotations

COMPANY_SOURCES: dict[str, list[tuple[str, str]]] = {
    # -- Greenhouse -------------------------------------------------
    "Databricks": [("greenhouse", "databricks")],
    "Rubrik": [("greenhouse", "rubrik")],
    "Stripe": [("greenhouse", "stripe")],
    "Airbnb": [("greenhouse", "airbnb")],
    "Coinbase": [("greenhouse", "coinbase")],
    "Cloudflare": [("greenhouse", "cloudflare")],
    "Datadog": [("greenhouse", "datadog")],
    "GitLab": [("greenhouse", "gitlab")],
    "MongoDB": [("greenhouse", "mongodb")],
    "Elastic": [("greenhouse", "elastic")],
    "Postman": [("greenhouse", "postman")],
    "Okta": [("greenhouse", "okta")],
    "Zscaler": [("greenhouse", "zscaler")],
    "Twilio": [("greenhouse", "twilio")],
    "Reddit": [("greenhouse", "reddit")],
    "Figma": [("greenhouse", "figma")],
    "Discord": [("greenhouse", "discord")],
    "Instacart": [("greenhouse", "instacart")],
    "Robinhood": [("greenhouse", "robinhood")],
    "Brex": [("greenhouse", "brex")],
    "Anthropic": [("greenhouse", "anthropic")],
    "Scale AI": [("greenhouse", "scaleai")],
    "Observe.AI": [("greenhouse", "observeai")],
    "Groww": [("greenhouse", "groww")],
    "Toast": [("greenhouse", "toast")],
    "Gusto": [("greenhouse", "gusto")],
    "Samsara": [("greenhouse", "samsara")],
    "Affirm": [("greenhouse", "affirm")],
    "Chime": [("greenhouse", "chime")],
    "Wise": [("greenhouse", "wise")],
    "Monzo": [("greenhouse", "monzo")],
    "Vercel": [("greenhouse", "vercel")],
    "Grafana Labs": [("greenhouse", "grafanalabs")],
    "Thoughtworks": [("greenhouse", "thoughtworks")],
    "Slice": [("greenhouse", "slice")],
    "Turing": [("greenhouse", "turing")],
    "HighRadius": [("greenhouse", "highradius")],
    "Airtable": [("greenhouse", "airtable")],
    "Asana": [("greenhouse", "asana")],
    "Faire": [("greenhouse", "faire")],
    "Mercury": [("greenhouse", "mercury")],
    "GoCardless": [("greenhouse", "gocardless")],
    # -- Lever -----------------------------------------------------
    "CRED": [("lever", "cred")],
    "Meesho": [("lever", "meesho")],
    "Paytm": [("lever", "paytm")],
    "Zeta": [("lever", "zeta")],
    "Zomato": [("lever", "eternal")],
    "Match Group": [("lever", "matchgroup")],
    "Tala": [("lever", "tala")],
    # -- Ashby ---------------------------------------------------------
    "Snowflake": [("ashby", "snowflake")],
    "Confluent": [("ashby", "confluent")],
    "Plaid": [("ashby", "plaid")],
    "Ramp": [("ashby", "ramp")],
    "Notion": [("ashby", "notion")],
    "Vanta": [("ashby", "vanta")],
    "Linear": [("ashby", "linear")],
    "OpenAI": [("ashby", "openai")],
    "Sarvam AI": [("ashby", "sarvam")],
    "Benchling": [("ashby", "benchling")],
    "Nubank": [("ashby", "nubank")],
    "Temporal": [("ashby", "temporal")],
    "UiPath": [("ashby", "uipath")],
    "Navi Technologies": [("ashby", "navi")],
    "Miro": [("ashby", "miro")],
    "Wealthsimple": [("ashby", "wealthsimple")],
    "Airwallex": [("ashby", "airwallex")],
    # -- Per-company adapters ----------------------------------------
    "Amazon": [("amazon", "")],
}
