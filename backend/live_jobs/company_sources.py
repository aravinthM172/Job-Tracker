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
    "Block": [("greenhouse", "block")],
    "Dropbox": [("greenhouse", "dropbox")],
    "Druva": [("greenhouse", "druva")],
    "Netradyne": [("greenhouse", "netradyne")],
    "Pinterest": [("greenhouse", "pinterest")],
    "Roblox": [("greenhouse", "roblox")],
    "Roku": [("greenhouse", "roku")],
    "Twitch": [("greenhouse", "twitch")],
    "Razorpay": [("greenhouse", "razorpaysoftwareprivatelimited")],
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
    # -- Workday (token = "tenant/wd-host/site") --------------------
    # Workday only exposes a relative post date, so effectively only
    # "today / yesterday" postings clear the 48h gate for these.
    "NVIDIA": [("workday", "nvidia/wd5/NVIDIAExternalCareerSite")],
    "Adobe": [("workday", "adobe/wd5/external_experienced")],
    "Salesforce": [("workday", "salesforce/wd12/External_Career_Site")],
    "Workday": [("workday", "workday/wd5/Workday")],
    "Intel": [("workday", "intel/wd1/External")],
    "Broadcom": [("workday", "broadcom/wd1/External_Career")],
    "Autodesk": [("workday", "autodesk/wd1/Ext")],
    "Samsung": [("workday", "sec/wd3/Samsung_Careers")],
    "Citi": [("workday", "citi/wd5/2")],
    "Mastercard": [("workday", "mastercard/wd1/CorporateCareers")],
    "PayPal": [("workday", "paypal/wd1/jobs")],
    "Capital One": [("workday", "capitalone/wd12/Capital_One")],
    "BlackRock": [("workday", "blackrock/wd1/BlackRock_Professional")],
    "Morgan Stanley": [("workday", "ms/wd5/External")],
    "Deutsche Bank": [("workday", "db/wd3/DBWebsite")],
    "Wells Fargo": [("workday", "wf/wd1/WellsFargoJobs")],
    "Target": [("workday", "target/wd5/targetcareers")],
    "PwC": [("workday", "pwc/wd3/Global_Experienced_Careers")],
    "CrowdStrike": [("workday", "crowdstrike/wd5/crowdstrikecareers")],
    "Cloudera": [("workday", "cloudera/wd5/External_Career")],
    "BrowserStack": [("workday", "browserstack/wd3/External")],
    "Barclays": [("workday", "barclays/wd3/External_Career_Site_Barclays")],
    "Cadence Design Systems": [("workday", "cadence/wd1/External_Careers")],
    "Fractal Analytics": [("workday", "fractal/wd1/Careers")],
    "Zoom": [("workday", "zoom/wd5/Zoom")],
    "S&P Global": [("workday", "spgi/wd5/SPGI_Careers")],
    "Motorola Solutions": [("workday", "motorolasolutions/wd5/Careers")],
    "Red Hat": [("workday", "redhat/wd5/jobs")],
    "State Street": [("workday", "statestreet/wd1/Global")],
    "Genpact": [("workday", "genpact/wd108/External_Careers")],
    "Lowe's": [("workday", "lowes/wd5/LWS_External_CS")],
    "Commonwealth Bank of Australia": [
        ("workday", "cba/wd3/CommBank_Careers")
    ],
    "Sony": [("workday", "sonyglobal/wd1/SonyGlobalCareers")],
    # -- Oracle Cloud Recruiting (token = "host|site") -------------
    "KPMG Global Services": [
        ("oracle", "ejgk.fa.em2.oraclecloud.com|CX_3")
    ],
    "Uber": [("oracle", "iaziqy.fa.ocs.oraclecloud.com|CX_1")],
    "Oracle": [("oracle", "eeho.fa.us2.oraclecloud.com|CX_1")],
    "Nokia": [
        ("oracle", "fa-evmr-saasfaprod1.fa.ocs.oraclecloud.com|CX_1")
    ],
    "EXL": [
        ("oracle", "fa-ewjt-saasfaprod1.fa.ocs.oraclecloud.com|CX_1")
    ],
    "JPMorgan Chase": [("oracle", "jpmc.fa.oraclecloud.com|CX_1")],
    # -- SmartRecruiters (token = company id) ----------------------
    "ServiceNow": [("smartrecruiters", "ServiceNow")],
    "Freshworks": [("smartrecruiters", "Freshworks")],
    "Bosch Global Software Technologies": [
        ("smartrecruiters", "BoschGroup")
    ],
    "PhonePe": [("smartrecruiters", "PHONEPELIMITED")],
    # -- Radancy / TalentBrew (token = site base URL) --------------
    "Synopsys": [("radancy", "https://careers.synopsys.com")],
    "Arm": [("radancy", "https://careers.arm.com")],
    # -- Per-company adapters ----------------------------------------
    "Amazon": [("amazon", "")],
    "Swiggy": [("swiggy", "")],
    "Bank of America": [("bofa", "")],
    # -- Keka (token = "tenant|portalId") -------------------------
    "Jupiter": [
        ("keka", "jupiter|b5279857-cf81-4dde-a215-fc48957ee2b5")
    ],
    # -- Darwinbox (token = "tenant|companyId") ------------------
    "Moneyview": [("darwinbox", "moneyview|main")],
    "Zepto": [("darwinbox", "zepto|main")],
    # -- Sitemap + JobPosting JSON-LD (token = sitemap URL) ------
    "Intuit": [("sitemap", "https://jobs.intuit.com/sitemap.xml")],
    "OpenText": [("sitemap", "https://careers.opentext.com/sitemap.xml")],
    # -- Guarded (aggressive anti-scraping - slowest cadence) -------
    "Meta": [("meta", "")],
    # "Google": [("google", "")],  # adapter parked - job-array fields
    # (location / post date) still unmapped; re-enable once a full
    # batchexecute response is captured. See sources/google.py.
}

