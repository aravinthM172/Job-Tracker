import { useState } from "react";

// Careers pages usually live on an ATS host, not the employer's own
// domain - fall back to a slug of the company name for those.
const ATS_HOSTS = [
  "greenhouse.io",
  "boards.greenhouse.io",
  "lever.co",
  "jobs.lever.co",
  "myworkdayjobs.com",
  "myworkdaysite.com",
  "wd1.myworkdayjobs.com",
  "ashbyhq.com",
  "jobs.ashbyhq.com",
  "smartrecruiters.com",
  "jobs.smartrecruiters.com",
  "oraclecloud.com",
  "taleo.net",
  "icims.com",
  "successfactors.com",
  "successfactors.eu",
  "keka.com",
  "darwinbox.com",
  "darwinbox.in",
  "mynexthire.com",
  "adzuna.com",
  "adzuna.in",
  "radancy.com",
  "avature.net",
  "eightfold.ai",
  "phenom.com",
];

// Company -> real domain, for the many cases where a name slug isn't the
// domain ("Walmart Global Tech" != walmartglobaltech.com). Keyed by the
// lower-cased company name. Anything not here falls back to the slug.
const COMPANY_DOMAINS: Record<string, string> = {
  "walmart global tech": "walmart.com",
  "sap labs india": "sap.com",
  "samsung r&d institute india": "samsung.com",
  "bosch global software technologies": "bosch.com",
  "kpmg global services": "kpmg.com",
  kpmg: "kpmg.com",
  "mercedes-benz r&d india": "mercedes-benz.com",
  "bmw group india": "bmwgroup.com",
  "jpmorgan chase": "jpmorganchase.com",
  "goldman sachs": "goldmansachs.com",
  "morgan stanley": "morganstanley.com",
  "bank of america": "bankofamerica.com",
  "wells fargo": "wellsfargo.com",
  "standard chartered": "sc.com",
  "deutsche bank": "db.com",
  "state street": "statestreet.com",
  "s&p global": "spglobal.com",
  "american express": "americanexpress.com",
  "capital one": "capitalone.com",
  "cadence design systems": "cadence.com",
  "motorola solutions": "motorolasolutions.com",
  "ge vernova": "gevernova.com",
  "volvo group": "volvogroup.com",
  "commonwealth bank of australia": "commbank.com.au",
  "natwest group": "natwestgroup.com",
  "societe generale": "societegenerale.com",
  "red hat": "redhat.com",
  "dell technologies": "dell.com",
  "publicis sapient": "publicissapient.com",
  "mckinsey & company": "mckinsey.com",
  "hashedin by deloitte": "hashedin.com",
  "tiger analytics": "tigeranalytics.com",
  "fractal analytics": "fractal.ai",
  "navi technologies": "navi.com",
  "pine labs": "pinelabs.com",
  "cashfree payments": "cashfree.com",
  "yellow.ai": "yellow.ai",
  "observe.ai": "observe.ai",
  "sarvam ai": "sarvam.ai",
  sharechat: "sharechat.com",
  "bank of new york": "bny.com",
  arm: "arm.com",
};

export function companyDomain(company: string, url?: string | null): string {
  const mapped = COMPANY_DOMAINS[company.trim().toLowerCase()];
  if (mapped) return mapped;

  if (url) {
    try {
      const host = new URL(url).hostname.replace(/^www\./, "");
      const isAts = ATS_HOSTS.some(
        (ats) => host === ats || host.endsWith(`.${ats}`),
      );
      if (!isAts && host.includes(".")) {
        return host.split(".").slice(-2).join(".");
      }
    } catch {
      /* fall through to the name slug */
    }
  }
  const slug = company.toLowerCase().replace(/[^a-z0-9]/g, "");
  return slug ? `${slug}.com` : "";
}

function logoCandidates(domain: string): string[] {
  if (!domain) return [];
  return [
    // square site icon, 128px - the crispest square mark that's free and
    // keyless. Wordmark-logo services return wide white-background images
    // that look wrong in a small tile, so we stick to favicons.
    `https://www.google.com/s2/favicons?domain=${domain}&sz=128`,
    `https://icons.duckduckgo.com/ip3/${domain}.ico`,
  ];
}

interface CompanyLogoProps {
  company: string;
  url?: string | null;
  className?: string;
}

export function CompanyLogo({ company, url, className = "h-10 w-10" }: CompanyLogoProps) {
  const candidates = logoCandidates(companyDomain(company, url));
  const [index, setIndex] = useState(0);
  const src = candidates[index];

  return (
    <div
      className={`relative flex shrink-0 items-center justify-center overflow-hidden rounded-lg bg-slate-100 text-xs font-semibold text-slate-500 dark:bg-slate-800 dark:text-slate-400 ${className}`}
    >
      {company.slice(0, 2).toUpperCase()}
      {src && (
        <img
          src={src}
          alt=""
          onError={() => setIndex((i) => i + 1)}
          // white plate in light mode so pale logos read; transparent in
          // dark mode so it blends into the tile instead of a white patch
          className="absolute inset-0 h-full w-full bg-white object-contain p-1 dark:bg-transparent"
        />
      )}
    </div>
  );
}
