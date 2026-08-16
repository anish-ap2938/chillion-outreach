# Leads Rebuild Progress

## Overall Goal

Rebuild the Leads workflow so a user can enter a **company name** and **target job title(s)**, find matching decision makers through a legitimate B2B people provider (Prospeo), attach LinkedIn URL and work email when available, classify email verification honestly, store the contact, and explicitly promote selected contacts into Outreach so they appear in the Email Agent and LinkedIn Agent.

This is **not** LinkedIn scraping, Selenium, or authenticated LinkedIn automation.

---

## Phase 0 — Architecture Analysis

Status: **COMPLETE**. No application code was modified in this phase.

### Current Frontend Flow

Page: `app/leads/page.tsx` renders `LeadDiscoveryAgent` inside `AppShell`.

`LeadDiscoveryAgent` has three tabs. **Job title is not an input anywhere.**

#### Companies tab

- **Inputs:** newline-separated company names; checkboxes `discoverWebsites` (default true) and `enrich` (default true).
- **Discover call:** `discoverCompanies({ company_names, discover_websites, enrich })` → `POST /api/v1/lead-gen/companies/discover`.
- **Saved call:** `getDiscoveredCompanies({ limit, offset, industry, is_target })` → `GET /api/v1/lead-gen/companies`.
- **State:** `companyNames`, `results` (latest discover), `savedCompanies`, pagination (`page`, `pageSize=20`, `total`), `industryFilter`, `targetOnly`, `error`, `loading`, `showSaved`.
- **Result table:** name, domain, industry, size, location, target-score badge.
- **Filters:** industry LIKE, target-matches-only.
- **Saved views:** `localStorage["company-views"]`.
- **Export:** client-side CSV of the *current page/result set*, not a backend export.
- **Density:** `localStorage["lead-density"]`.

#### Contacts tab

- **Inputs:** company name (required), company domain (optional). **No title / profession field.**
- **Discover call:** `discoverContacts({ company_name, company_domain })` → `POST /api/v1/lead-gen/contacts/discover`.
- **Saved call:** `getDiscoveredContacts({ limit, offset, has_email })` → `GET /api/v1/lead-gen/contacts`.
- **State:** `results` vs `savedContacts`, pagination (`pageSize=25`), `hasEmailFilter`.
- **Result table:** name, title + seniority badge, company, email, LinkedIn link.
- **Saved views:** `localStorage["contact-views"]`.
- **Copy mismatch:** button says “Discover IT & Engineering Contacts”; empty state still says “Find Finance Decision Makers”.

#### Email Finder tab

- **Inputs:** first name, last name, company domain.
- **Call:** `generateEmailCandidates({ first_name, last_name, company_domain, num_patterns: 8 })` → `POST /api/v1/lead-gen/email/generate`.
- **Does not persist a contact.** Shows `best_guess` and a confidence bar per pattern. Copy-to-clipboard only.

#### Stats

On mount: `getLeadGenStats()` → `GET /api/v1/lead-gen/stats`. Cards show `total_companies`, `total_contacts`, `contacts_with_email`. Refreshed after successful discover.

API base: `NEXT_PUBLIC_AGENTS_API_URL` or `http://localhost:8000` (`lib/api/agents.ts`).

### Current Backend Flow

Mounted in `chillion_agents/app/main.py` as `/api/v1/lead-gen`.

| Method | Path | Request | Services | DB writes | Response | Fallback / notes |
|---|---|---|---|---|---|---|
| POST | `/companies/discover` | `company_names[]`, `discover_websites`, `enrich` | `CompanyDiscoveryService` (always dummy providers unless injected; API does **not** inject) | `insert_company` + audit | companies + target_matches | Dummy search guesses `{name}.com`. Dummy enrich fills Technology / SF / 100–500 / $50M–$100M. Errors → HTTP 500 |
| GET | `/companies` | filters: industry, is_target, pagination, sort | `LeadDatabase.get_companies` | none | `{ success, count, companies }` | sort whitelist: `target_score`, `name`, `industry` |
| POST | `/contacts/discover` | `company_name`, optional `company_domain`, `company_website` | If no domain/website → dummy company website discover, then `ContactDiscoveryService.discover_contacts`, then `EmailDiscoveryService.discover_email` per contact | `insert_contact` + audit **per contact** | contacts list | No title param. Website miss → empty list. Duplicate `(company_name, full_name)` skipped. HTTP 500 on exception |
| GET | `/contacts` | company, seniority, has_email, pagination, sort | `get_contacts` | none | `{ success, count, contacts }` | default sort `relevance_score` (almost always 0.0) |
| POST | `/email/generate` | first, last, domain, num_patterns | `EmailPatternGenerator.generate_and_validate` | audit only, **no contact row** | `best_guess` + candidates | Local regex “validation” only |
| GET | `/stats` | none | `get_stats` | none | counts including social | — |

`LeadDatabase` is initialized at **router import time** (`db = LeadDatabase(); db.initialize()`).

### Current Contact Discovery

`ContactDiscoveryService` (`contacts/discovery.py`) is **website HTML scraping**, not a people database.

1. **Does it search LinkedIn?** No. The file contains **zero** `linkedin` references. Person `linkedin_url` is never set.
2. **Does it call an external people database?** No.
3. **Does it search company websites?** Yes, with `requests` + BeautifulSoup, rate-limited.
4. **Paths inspected:** `/about/leadership`, `/about/team`, `/leadership`, `/team`, `/management`, `/executives`, `/our-team`, investor-relations variants, then homepage `<a>` text/href containing leadership keywords, then `sitemap.xml` loc tags containing leadership/team/management/executive/about. Capped at 3 pages.
5. **Name identification:** 2–5 capitalized words, no digits/`@`/http. From `h2`/`h3`/`h4`/`.name`/`strong` in bio blocks, or line-above-title on unstructured pages.
6. **Title identification:** `.title`/`.position`/`.role`/`p`/`span` that contain CEO/CFO/CTO/CIO/VP/director/manager/head/etc., or substring of a configured `target_titles` value.
7. **Relevance:** `_is_finance_title()` (name is leftover finance). It lowercases global `config.company.target_titles` and requires that **entire configured string** be a substring of the scraped title. Example: configured `"IT Director"` matches `"Senior IT Director"`; it does **not** match `"Director of Information Technology"` unless that exact phrase is in config. Titles are **not** sent by the UI request.
8. **Dedup:** in-memory by `full_name.lower()`; DB unique `(company_name, full_name)`.
9. **Seniority:** keyword buckets C-Level / VP / Director / Manager / Other. `is_decision_maker` and `relevance_score` are **never assigned** (stay false / 0.0).
10. **No leadership page:** returns `[]`. No people-DB fallback.

Default `target_titles` (from `config.py`, not the outdated README): CTO, CIO, IT Director, Director IT, Head of IT, VP Infrastructure, Infrastructure Manager, Network Manager, Security Manager, Procurement Manager, Program Manager, Project Manager, Director Engineering, Head of Engineering, Defense Program Manager, Technical Director, Chief Technology Officer, Chief Information Officer.

### Current Email Discovery

`EmailDiscoveryService.discover_email`:

- If contact already has email → local-validate and set `email_status` to validator `status`.
- Else requires `first_name`, `last_name`, `company_domain`. Generates patterns, picks `best_guess`, sets `email_status = "pattern_guess"`.

Patterns (priority order): `first.last`, `firstlast`, `first_last`, `flast`, `first`, `last.first`, `lastf`, `first.l`. Confidence starts at `1.0 - (priority-1)*0.1` (min 0.3). Local validator then +0.2 if `valid` else −0.3.

`LocalEmailValidator` **actual** behavior (not the comment):

- Regex format check.
- Disposable domain denylist.
- Hardcoded “known corporate” allowlist (google.com, microsoft.com, etc.) → `status=valid`, `confidence=0.9`.
- Everything else format-ok → `status=unverified`, `valid=True` (meaning format, **not mailbox**).
- `mx_found` and `smtp_valid` are **always `None`**. No MX lookup. No SMTP. No Hunter/ZeroBounce/Apollo.

`is_validated=True` on `EmailCandidate` only means “we ran the local function”. It does **not** mean the mailbox exists.

`best_guess`: first candidate with `validation_result in ('valid', 'unverified')`, else first candidate. For a typical company domain this is almost always `first.last@domain`.

`find_public_email()` is an explicit **PLACEHOLDER**: logs and returns `None`. **Not called** from the API or CLI path.

Honest labels:

| Label used in code | What it actually means |
|---|---|
| `verified` / `valid` | Either a domain on a tiny hardcoded list, or a comment — **not mailbox verification** |
| `pattern_guess` | Constructed from name+domain. No proof it exists |
| `unverified` | Format looks like an email |
| `invalid_format` / `disposable` | Local regex/denylist |

### Current Databases

Lead-generation config path: `./data/leads.db` (`LeadGenerationConfig.storage.database_path`). Relative to FastAPI process CWD (typically `chillion_agents/data/leads.db`). This config is a pydantic `BaseModel`, **not** `BaseSettings` — env prefix `LEADGEN_` does **not** auto-load from `.env`.

SQLAlchemy outreach DB: `settings.database_url` default `sqlite:///./chillion_agents.db` (`chillion_agents/app/config.py`). **Does** load `.env`.

Prisma auth: `DATABASE_URL="file:./prisma/dev.db"` (frontend `.env.example`).

| Purpose | Database | Engine | Used by |
|---|---|---|---|
| Login / workspaces | `prisma/dev.db` | Prisma SQLite | Next.js `/api/auth/*` only |
| Discovered companies, contacts, social leads, audit | `data/leads.db` | raw `sqlite3` (`LeadDatabase`) | `/leads`, `/intent`, dashboard `ActivityFeed` |
| Outreach list, CRM-shaped `prospects`, campaigns, Gmail OAuth tokens | `chillion_agents.db` | SQLAlchemy | Email Agent, LinkedIn Agent, CSV save, Gmail |

`contacts` columns today: `id`, `company_id`, `company_name`, `company_domain`, `full_name`, `first_name`, `last_name`, `title`, `email`, `email_status`, `phone`, `linkedin_url`, `twitter_handle`, `source`, `source_url`, `discovered_at`, `bio`, `seniority_level`, `department` (default `'Finance'`), `enrichment_data`, `is_decision_maker`, `relevance_score`. Unique: `(company_name, full_name)`. Inserts only; IntegrityError → skip. **No UPDATE.**

`_ensure_column()` already exists for additive SQLite migrations. Provider/email-verification columns can be added without recreating the DB.

`SavedProspect` fields: `id`, `name`, `email`, `company`, `title`, `linkedin_url`, `industry`, `notes`, `source` (`"manual"` \| `"csv"` \| `"intent"`), timestamps. Routes: `GET /`, `POST /`, `POST /bulk`, `GET /{id}`, `PUT /{id}`, `DELETE /{id}`, `DELETE /`. **No unique constraint. No duplicate check.** Bulk create always inserts.

Homonym: SQLAlchemy `Company` / `Prospect` in `chillion_agents.db` are **unused by the Leads UI**. Frontend `getProspects()` exists but Email/LinkedIn agents call `getSavedProspects()` instead.

### Current Lead → Outreach Gap

There is **no code path** from `leads.db.contacts` → `saved_prospects`.

Email Agent (`components/agents/EmailAgent.tsx`):

- Loads `getSavedProspects()` only.
- Does **not** call `getDiscoveredContacts`.
- Adding a prospect requires **name + email**.
- Generate requires selected prospects **with email**.
- Gmail: real OAuth + Gmail API drafts if `GOOGLE_OAUTH_*` are set (`gmail_service.py`).

LinkedIn Agent (`components/agents/LinkedInAgent.tsx`):

- Loads `getSavedProspects()` only.
- Add requires **name only**. LinkedIn URL optional.
- Generate does **not** require `linkedin_url`; it is not even passed into `generateLinkedInDM` (`prospect_profile` is name/title/company/industry). Filter “Has LinkedIn” is display-only.

Therefore a contact discovered on `/leads` cannot appear in Email or LinkedIn until someone re-enters it (or CSV-uploads it) as a SavedProspect.

### Key Problems Identified

1. Contact search is website scraping + global title list, not “company + titles → people DB”.
2. Company website/enrichment providers are **dummy**; results look complete but are invented.
3. Person LinkedIn URLs are not discovered. Company LinkedIn URLs are name-slug guesses.
4. Emails are pattern guesses labeled in ways that can be read as “verified”.
5. `find_public_email()` is unimplemented and unused.
6. Leads and Outreach live in different SQLite files with no promotion API.
7. `SavedProspect` accepts unlimited duplicates.
8. Finance leftover naming: `FinanceContact`, `department='Finance'`, `_is_finance_title`, README AR/O2C, empty-state copy.
9. Dummy ICP usually scores ~0.3 (US + “Technology” vs India/defense ICP) so companies are **not** marked target.
10. No tests under `tests/` for lead generation.
11. `LeadStatus` exists but is never updated by any API.
12. Search-provider toggle in config applies to **forums**, not company discovery.

### Important Existing Components to Preserve

- `/leads` UI shell, tables, pagination, CSV client export, stats cards.
- FastAPI `/api/v1/lead-gen` shape (extend, do not throw away).
- `LeadDatabase` SQLite + `_ensure_column` additive migrations.
- `SearchProvider` / `CompanyEnrichmentProvider` / `EmailValidator` ABC pattern — reuse the same idea for people search.
- Website scraper as an optional **fallback** provider.
- `SavedProspect` as the outreach working set (Email + LinkedIn already depend on it).
- Prisma auth remaining separate.
- Do **not** introduce LinkedIn scraping / Selenium.

### Proposed Future Architecture

Keep three databases. Add a people-provider layer. Keep Leads and Outreach as **separate tables** with an explicit promote step.

```
Company Name + Target Title(s)
        ↓
PeopleSearchProvider (Apollo first; website scrape fallback)
        ↓
Normalized Contact (name, title, company, linkedin_url, email, verification)
        ↓
LeadDatabase.contacts  (discovery store)
        ↓
User selects row → “Add to Outreach”
        ↓
SavedProspect  (outreach store, with duplicate check)
        ↓
Email Agent (requires email) / LinkedIn Agent (name sufficient)
```

Do **not** put Apollo calls inside `ContactDiscoveryService` HTML parsing. Introduce `PeopleSearchProvider` (ABC) next to the existing provider interfaces. `ContactDiscoveryService` can become an orchestrator: request titles → provider → email enrichment → persist.

### Proposed Data Flow

```
/leads
  LeadDiscoveryAgent
    lib/api/agents.ts
      FastAPI /api/v1/lead-gen
        People provider + existing LeadDatabase
          data/leads.db

[explicit promotion]

POST /api/v1/saved-prospects  (new mapping from contact)
  chillion_agents.db.saved_prospects
    EmailAgent / LinkedInAgent
```

Auth stays:

```
login → Prisma → prisma/dev.db
```

### Likely Files to Modify

See “Files Likely to Change” in the Phase 0 report below (also listed in the chat response). No files other than this document were modified in Phase 0.

### Risks

| Risk | Severity | Why |
|---|---|---|
| Guessed emails shown as Verified | **High** | `valid`/`is_validated` already overstate local regex; Apollo email_status must map 1:1 to provider truth |
| Duplicate SavedProspects | **High** | create/bulk have zero uniqueness |
| Dummy data mistaken for production | **High** | Dummy enrich looks like real firmographics |
| SQLite schema drift without `_ensure_column` | **High** | existing `leads.db` will fail if we add columns carelessly |
| Python/TS contract mismatch | **Medium** | TS `DiscoveredContact` already omits several backend fields |
| Breaking Email/LinkedIn agents | **Medium** | they depend on SavedProspect shape; promotion must write that shape |
| Apollo key missing / rate limits / partial results | **Medium** | no key handling today; provider must degrade explicitly |
| Contact unique key `(company, full_name)` too weak | **Medium** | same name at one company, or name variations, will collide or duplicate |
| Website scrape leftover as silent “success with 0 rows” | **Low** | needs a distinct empty vs error vs fallback |
| Auth DB merge temptation | **Low** | no reason to merge |

### Decisions / Recommendations

1. **People provider abstraction, not inlining Apollo into the scraper.** Same pattern as `SearchProvider` / `EmailValidator`.
2. **Keep Leads contacts and SavedProspects as separate tables.** Discovery is noisy; outreach should be a curated copy. Unify *later* only if a real CRM is built. Do not merge into SQLAlchemy `Prospect` either — the UI does not use it.
3. **Keep Prisma auth separate.** It has no prospect models by design.
4. **`APOLLO_API_KEY` lives in `chillion_agents/app/config.py` `Settings` and `chillion_agents/.env.example`**, because that class already loads `.env`. Do not put it only on the unused `LEADGEN_` BaseModel prefix.
5. **Website scraping remains as fallback**, behind the same provider interface, never as the primary people source.
6. **Promotion = copy** via `saveProspect` / a dedicated `POST .../contacts/{id}/promote` that maps fields and checks duplicates on normalized email, else `linkedin_url`, else `(lower(name), lower(company))`.
7. **Email status must be an explicit enum** (e.g. `verified` / `unverified` / `guessed` / `unavailable` / `invalid`) never inferred from `is_validated=True`.
8. **Title list becomes a request field**, with config `target_titles` as default chips only.
9. **Do not scrape LinkedIn.** Provider-supplied `linkedin_url` only.

### Proposed implementation phases (not started)

**Phase 1 — Contracts + UI inputs**
- Goal: company + title(s) in the Contacts tab; TS/Python request types; honest email-status labels in the UI; no Apollo yet.
- Likely files: `LeadDiscoveryAgent.tsx`, `lib/api/agents.ts`, `lead_generation.py` request models, `models.py` (rename/fields), maybe contacts table additive columns via `_ensure_column`.
- Tests: request validation, default titles from config, UI type compile.
- Expected output: user can submit titles; backend accepts them but still uses current scraper.
- Do **not**: call Apollo, change Email/LinkedIn agents, merge DBs.

**Phase 2 — Apollo provider**
- Goal: `PeopleSearchProvider` + `ApolloPeopleProvider`; key in Settings; map Apollo fields to contact model; never label guessed email verified.
- Likely files: new `contacts/providers.py` (or similar), `config.py` Settings, `.env.example`, contact model fields.
- Tests: mocked Apollo HTTP, status mapping, missing key → clear error.
- Do **not**: delete website scraper; do not auto-promote to outreach.

**Phase 3 — Discovery pipeline**
- Goal: orchestrate Apollo-first, website fallback; persist provider metadata; LinkedIn URL from provider; domain handling when omitted.
- Likely files: `contacts/discovery.py`, `lead_generation.py` POST `/contacts/discover`, `database.py`.
- Tests: fallback when Apollo empty; dedup insert.
- Do **not**: rewrite company dummy enrich unless needed for domain.

**Phase 4 — Lead → Outreach bridge**
- Goal: “Add to Outreach” copies selected contacts into `saved_prospects` with duplicate detection; Email/LinkedIn then see them.
- Likely files: `LeadDiscoveryAgent.tsx`, `saved_prospects.py`, `lib/api/agents.ts`. Optionally a dedicated promote route.
- Tests: duplicate skip, missing-email still promotable for LinkedIn, Email agent still requires email to generate.
- Do **not**: make leads.db the outreach source of truth.

**Phase 5 — Cleanup + tests**
- Goal: rename `FinanceContact`, fix copy, department default, README; integration tests; hide dummy behind explicit flag.
- Do **not**: large unrelated refactors (social intent, Prisma merge, SQLAlchemy Prospect revival).

### Hidden dependencies (must not break)

- `components/dashboard/ActivityFeed.tsx` — `getDiscoveredCompanies` / `getDiscoveredContacts` / `getSocialLeads`
- `components/agents/IntentSignalsAgent.tsx` — shares `/lead-gen/stats` and social search
- `chillion_agents/app/lead_generation/cli.py` — full pipeline uses the same services
- `chillion_agents/app/lead_generation/storage/csv_export.py` — `FinanceContact` CSV columns
- `chillion_agents/app/lead_generation/__init__.py` — public exports `FinanceContact`
- `chillion_agents/app/scheduler.py` — social only, not company/contact
- Frontend `getProspects` / SQLAlchemy `Prospect` — unused by Leads/Email/LinkedIn UIs

---

## Phase 1 — Contracts + UI Inputs

Status: **COMPLETE**. No Apollo integration. Existing website scraping remains the contact source.

### Changes Made

- Contacts tab now requires Company Name + Target Job Titles, with optional domain, max results (1–50, default 10), and Find Work Emails (default on).
- `POST /api/v1/lead-gen/contacts/discover` accepts `target_titles`, `max_results`, and `find_emails`.
- Title matching is request-scoped (not a global mutation). Private helper renamed `_is_finance_title` → `_matches_target_title`.
- Pattern-generated emails are stored and displayed as **Pattern Guess**, never Verified.
- `find_emails: false` skips `EmailDiscoveryService` and returns contacts with `email_status = not_found`.
- Optional Pydantic fields added: `provider`, `provider_id`, `email_confidence`. Website discoveries set `provider = "company_website"`. **No new SQLite columns** (deferred to Phase 2).
- `FinanceContact.department` default changed from `"Finance"` to `None`.
- Finance-only empty-state copy removed from the Contacts tab only.

### Files Changed

- `chillion_agents/app/api/routes/lead_generation.py` — request contract + discover handler
- `chillion_agents/app/lead_generation/contacts/discovery.py` — request titles, max_results, matcher rename
- `chillion_agents/app/lead_generation/contacts/email.py` — honest status (`pattern_guess` / `not_found`)
- `chillion_agents/app/lead_generation/models.py` — optional provider/email fields; department default
- `lib/api/agents.ts` — `target_titles` / `max_results` / `find_emails` + response fields
- `components/agents/LeadDiscoveryAgent.tsx` — Contacts form, table, copy
- `chillion_agents/tests/test_contact_search_phase1.py` — Phase 1 tests
- `chillion_agents/pytest.ini` — pythonpath for tests

### API Contract

```python
class ContactSearchRequest(BaseModel):
    company_name: str                 # trimmed, non-blank
    company_domain: Optional[str] = None
    company_website: Optional[str] = None
    target_titles: Optional[List[str]] = None  # omit = config fallback; explicit [] is invalid
    max_results: int = 10             # ge=1, le=50
    find_emails: bool = True
```

**Back-compat:** If `target_titles` is omitted, the API uses `config.company.target_titles`. An explicit empty list is **not** replaced with defaults. The `/leads` UI always sends `target_titles`.

### Title Matching Behavior

Case-insensitive substring: requested title must appear in the scraped title.

- `"IT Director"` matches `"Senior IT Director"`
- `"Head of IT"` matches `"Head of IT Infrastructure"`
- `"Security Director"` does not match `"Chief Financial Officer"`

Applied after parse + dedup; then `max_results` slices the list.

### Email Status Behavior

| Situation | `email_status` | UI |
|---|---|---|
| Pattern generator produced an address | `pattern_guess` | Pattern Guess |
| `find_emails=false` or no address | `not_found` | Not Found |
| Local format check on an existing address | `unverified` (local `"valid"` is remapped) | Unverified |

UI never displays **Verified** for current fallback emails.

### Tests Added

`chillion_agents/tests/test_contact_search_phase1.py`

- Request validation (valid payload, blank name, `[]` titles, whitespace titles, max_results 0/51, omitted titles)
- Title matching cases above
- Mocked HTML website discovery + max_results after dedup
- `find_emails` false does not construct `EmailDiscoveryService`
- Pattern email → `pattern_guess`, not `verified`

### Test Results

```text
cd chillion_agents && python -m pytest tests/test_contact_search_phase1.py -q
20 passed, 37 warnings in 0.58s
```

Import sanity: `from app.lead_generation.contacts.discovery import ContactDiscoveryService` — ok.

### Known Issues

- Repo-wide `npm run lint` / `npm run build` still fail on **pre-existing** files (`components/gtm/SkillsWorkbench.tsx` parse error, and other agent `any` types). Phase 1 files were not the cause of the build failure.
- Website scrape still often returns zero people LinkedIn URLs (expected).
- Company enrichment remains dummy (Phase 2+).
- `provider` / `email_confidence` are in the Pydantic/API payload for discover responses but **not** persisted in SQLite yet.

### Deferred to Phase 2

- Apollo / `PeopleSearchProvider`
- `APOLLO_API_KEY`
- Persist provider columns via `_ensure_column`
- Real person LinkedIn URLs from a people database
- Real mailbox verification
- Add to Outreach / SavedProspect promotion
- Global rename of `FinanceContact`

### Phase Status (as of end of Phase 1)

```
Phase 0: COMPLETE
Phase 1: COMPLETE
Phase 2: NOT STARTED
Phase 3: NOT STARTED
Phase 4: NOT STARTED
Phase 5: NOT STARTED
```

---

## Phase 2 — Apollo People Provider

Status: **COMPLETE**. Production-capable Apollo people provider with mocked tests. Full Apollo → website → pattern fallback orchestration is **not** implemented (Phase 3).

### Architecture

Apollo HTTP stays inside `ApolloPeopleProvider`. Website HTML parsing stays inside `ContactDiscoveryService`. FastAPI maps errors and injects the provider; it does not call Apollo directly.

A single `PeopleSearchProvider.search_people(...)` method was chosen over a two-method `search`/`enrich` split because callers need `List[FinanceContact]`. Search vs enrich is an Apollo implementation detail.

```text
POST /contacts/discover
        ↓
if APOLLO_API_KEY and user-supplied company_domain:
    ContactDiscoveryService(people_provider=ApolloPeopleProvider)
        ↓
    PeopleSearchProvider.search_people
        ↓
    ApolloPeopleProvider
        ↓
    POST /api/v1/mixed_people/api_search
        ↓
    POST /api/v1/people/bulk_match  (batches of 10)
        ↓
    FinanceContact (provider=apollo)
else:
    existing website scraper (Phase 1)
```

Dummy company-website domain guessing is never passed to Apollo. Only `request.company_domain` from the caller enables Apollo.

### Apollo Search Flow

1. Require a real company domain (`ApolloDomainRequiredError` if missing; never invent `{name}.com`).
2. Map `target_titles` → `person_titles[]`, domain → `q_organization_domains_list[]`.
3. `per_page = min(max_results, 100)`, paginate only until `max_results`.
4. Treat People Search as discovery only. Do not read emails from search results.
5. Dedupe search people by Apollo `id` before enrichment.

Do **not** use `q_organization_job_titles[]` (job postings, not person titles).

### Apollo Enrichment Flow

- Endpoint: `POST /api/v1/people/bulk_match` (official bulk limit: 10 people per request).
- Identify people by Apollo `id` in `{ "details": [{"id": "..."}] }`.
- Query params: `reveal_personal_emails=false`, `reveal_phone_number=false`.
- Do **not** send `run_waterfall_email`.
- Enrichment still runs when `find_emails=false` (needed for `linkedin_url`), but emails are stripped before mapping.

### Provider Mapping

| Apollo | FinanceContact |
|---|---|
| `id` | `provider_id` |
| `name` / first+last | `full_name`, `first_name`, `last_name` |
| `title` | `title` |
| request company | `company_name`, `company_domain` |
| enrich `email` | `email` (only if `find_emails=true`) |
| enrich `email_status` | `email_status` via `map_apollo_email_status` |
| `extrapolated_email_confidence` | `email_confidence` if present; else `None` |
| `linkedin_url` | `linkedin_url` (never constructed) |
| — | `provider = "apollo"`, `source = "apollo"` |

Raw Apollo payloads are not returned. `enrichment_data` keeps only `organization_id`, `organization_name`, `headline`.

### Email Status Mapping

Central function: `map_apollo_email_status()`.

| Situation | Internal `email_status` |
|---|---|
| Apollo `verified` | `verified` |
| Apollo `unverified` | `unverified` |
| Apollo `likely` / `likely to engage` | `likely` |
| No email | `not_found` |
| Pattern generator (website path, Phase 1) | `pattern_guess` (never produced by Apollo) |
| HTTP 200 without an email | `not_found` (never `verified`) |
| `find_emails=false` | email unset, `not_found` even if Apollo returned one |

### Database Changes

Additive via `LeadDatabase._ensure_column()`. Existing rows remain valid. DB is not deleted or recreated.

`contacts` columns added:

- `provider` TEXT
- `provider_id` TEXT
- `email_confidence` REAL

Reused: `email_status`, `linkedin_url`, `source`, `enrichment_data`.

### Files Changed

**Created**

- `chillion_agents/app/lead_generation/providers/base.py` — `PeopleSearchProvider` ABC
- `chillion_agents/app/lead_generation/providers/apollo.py` — Apollo client + mapping
- `chillion_agents/app/lead_generation/providers/errors.py` — provider exceptions
- `chillion_agents/app/lead_generation/providers/__init__.py` — exports
- `chillion_agents/tests/test_apollo_provider_phase2.py` — mocked HTTP tests

**Modified**

- `chillion_agents/app/config.py` — `apollo_api_key: Optional[str] = None`
- `chillion_agents/.env.example` — empty `APOLLO_API_KEY=`
- `chillion_agents/app/lead_generation/models.py` — `ContactSource.APOLLO`
- `chillion_agents/app/lead_generation/storage/database.py` — columns + insert
- `chillion_agents/app/lead_generation/contacts/discovery.py` — optional `people_provider` injection
- `chillion_agents/app/api/routes/lead_generation.py` — inject Apollo when key+domain; map errors; skip pattern email for Apollo contacts
- `components/agents/LeadDiscoveryAgent.tsx` — display source `Apollo`; show Verified only for `email_status=verified` and `provider=apollo`
- `PROGRESS.md` — this section

No new Python packages. Reused existing `requests` (already used by lead gen). Apollo SDK was not added.

### Tests Added

`chillion_agents/tests/test_apollo_provider_phase2.py` (mocked HTTP only):

- Missing/blank key → `ApolloNotConfiguredError`; Settings default remains `None` (app startup does not require a key)
- Provider initializes with a supplied key
- Domain required / no guessed domain
- Search maps `microsoft.com` + titles → `q_organization_domains_list[]`, `person_titles[]`, `per_page=10`, `x-api-key` header
- Search IDs + enrichment mapping (name, title, company, LinkedIn, email, status, provider)
- `verified` / `unverified` / missing email
- HTTP 200 is not treated as email `verified`
- `find_emails=false` strips incidental email
- Missing LinkedIn still returns the person
- Duplicate provider IDs → one contact
- Bulk enrich batches of 10 (25 people → 1 search + 3 enrich)
- 401/403 → `ApolloAuthenticationError`; 429 → `ApolloRateLimitError`; 422/5xx/timeout → `ApolloAPIError`
- Enrichment does not set waterfall / personal email / phone reveal
- Provider metadata survives SQLite round-trip
- `ContactDiscoveryService` delegates to an injected mock provider

### Test Results

```text
cd chillion_agents && python -m pytest tests/test_contact_search_phase1.py tests/test_apollo_provider_phase2.py -q
42 passed, 72 warnings in 0.49s
```

- Phase 1: 20 passed (all preserved)
- Phase 2: 22 passed
- Warnings: pre-existing Pydantic class-based Config deprecation and `datetime.utcnow()` — not introduced as failures
- Broader backend suite: these two files are the entire `chillion_agents/tests/` tree
- No automated test calls the live Apollo API

Optional local check (not in pytest; does not print the key):

```text
cd chillion_agents
python -c "from app.config import settings; from app.lead_generation.providers.apollo import ApolloPeopleProvider
assert settings.apollo_api_key, 'skip: APOLLO_API_KEY not set'
p=ApolloPeopleProvider(); cs=p.search_people('Microsoft','microsoft.com',['IT Director'],1,False)
print('count', len(cs), 'linkedin', bool(cs and cs[0].linkedin_url), 'email_set', bool(cs and cs[0].email))"
```

### Error Handling

| Condition | Provider exception | HTTP (discover route) |
|---|---|---|
| Missing/empty `APOLLO_API_KEY` | `ApolloNotConfiguredError` (provider not constructed; website path used) | not raised at startup |
| No domain | `ApolloDomainRequiredError` | 400 |
| 401 / 403 | `ApolloAuthenticationError` | 401 / 403 |
| 422 | `ApolloAPIError` (`status_code=422`) | 400 |
| 429 | `ApolloRateLimitError` | 429 |
| 5xx | `ApolloAPIError` | 502 |
| Timeout / network | `ApolloAPIError` | 502 |

No retries. Every request uses timeout = `rate_limit.request_timeout_seconds` (30s). API key is never logged or returned to the frontend.

### Known Issues

- Repo-wide `npm run lint` / `npm run build` still fail on **pre-existing** files, especially `components/gtm/SkillsWorkbench.tsx` (`->` parse error). Phase 2 frontend-only changes did not introduce that build failure. `LeadDiscoveryAgent.tsx` / `lib/api/agents.ts` lint issues (`catch (e: any)`, `as any` tab keys, `loadStats` before declaration) predate Phase 2 source/status mapping.
- When Apollo is selected (key + domain) and returns zero people, the website scraper is **not** used. That fallback is Phase 3.
- Pattern email guessing is skipped for `provider=apollo` contacts even when `find_emails=true` and Apollo has no email. Filling those gaps is Phase 3.
- Company website dummy enrichment is unchanged.

### Deferred to Phase 3

- Apollo-primary then website scraper fallback then pattern-email fallback
- Domain resolution when the user omits `company_domain`
- Returning empty Apollo results into website discovery automatically
- Waterfall enrichment, webhooks, phone reveal, personal emails
- Add to Outreach / `saved_prospects` (Phase 4)
- Global rename of `FinanceContact` (Phase 5)

### Phase Status (as of end of Phase 2)

```
Phase 0: COMPLETE
Phase 1: COMPLETE
Phase 2: COMPLETE
Phase 3: NOT STARTED
Phase 4: NOT STARTED
Phase 5: NOT STARTED
```

---

## Phase 3 — Discovery Pipeline

Status: **COMPLETE**. Apollo-primary discovery with current-employer/title verification, website fallback, pattern-email fallback, merge/dedupe, and upsert persistence. Add to Outreach is **not** implemented (Phase 4).

### Orchestration

`ContactDiscoveryOrchestrator` owns the decision tree. The FastAPI route is thin: construct orchestrator, call `discover()`, return contacts + warnings.

```text
ContactDiscoveryOrchestrator
        ├── trusted domain resolution (user-supplied only)
        ├── ApolloPeopleProvider  (when configured + trusted domain)
        ├── current employer + title verification
        ├── ContactDiscoveryService (website scrape fallback / fill-to-max)
        ├── EmailDiscoveryService (pattern guess on trusted domains only)
        └── LeadDatabase.upsert_contact
```

Website HTML parsing remains in `ContactDiscoveryService`. Apollo HTTP remains in `ApolloPeopleProvider`.

### Trusted Domain Rules

Trusted sources:

- User-supplied `company_domain` after normalization/validation
- User-supplied `company_website` URL (domain extracted)

Not trusted:

- DummySearchProvider `{name}.com` guesses
- Inventing `microsoft.com` from `"Microsoft"`
- Malformed strings (no TLD, spaces, company names)

Dummy discovery is **not** called from the contact pipeline. No trusted domain → skip Apollo and skip pattern email; website scrape may still run without a dummy domain (usually 0 pages).

Normalization: `https://www.microsoft.com/` → `microsoft.com`. Matching treats `www.` and `https://` as equivalent, allows `careers.microsoft.com` vs `microsoft.com`, rejects `notmicrosoft.com`.

### Apollo Primary Flow

When Apollo is configured and a trusted domain exists:

1. Search with `company_domain` + `target_titles` + `max_results`
2. Pre-filter search hits whose known org/title already cannot match (saves enrichment credits)
3. Enrich remaining people (still bounded by `max_results`)
4. Keep only people whose **current** org domain matches the requested domain
5. Keep only people whose **current** title matches requested titles
6. If `len < max_results`, run website fallback to fill
7. Merge, dedupe, truncate

### Current Employer Verification

After enrichment, `enrichment_data.organization_primary_domain` (from Apollo `organization.primary_domain` / `website_url` / `domain`) is compared with the trusted request domain.

If current org is Google/`google.com` while the user searched Microsoft/`microsoft.com`, the person is dropped even if they once worked at Microsoft. Missing current-org domain is also dropped (cannot confirm current employer).

### Current Title Verification

Uses the shared Phase 1 substring matcher (`matches_target_title`). Enriched current title is the source of truth, not the search filter.

- `"IT Director"` matches `"Senior IT Director"`
- `"IT Director"` does not match `"VP Sales"`

### Website Fallback

Runs when:

- Apollo is not configured
- no trusted domain
- Apollo auth/rate-limit/timeout/5xx/API error (including missing endpoint access)
- Apollo returns 0 usable contacts after verification
- Apollo returns fewer than `max_results` (fill remaining)

Does **not** run when Apollo already produced a full `max_results` set. Leadership/team/sitemap scrape is unchanged.

Recoverable Apollo failures never become HTTP 429/401/502 if website fallback can run. Empty both paths → HTTP 200 with 0 contacts.

### Email Fallback

`find_emails=false`: response emails are `None` / `not_found`. Pattern generator is not called. Persistence does **not** wipe an existing stronger stored email.

`find_emails=true`:

- Apollo professional email kept with Apollo status (`verified` / `unverified` / `likely`)
- Apollo person, no email, trusted domain → `EmailPatternGenerator`, `email_status=pattern_guess`, `email_source=pattern_guess`, `provider` stays `apollo`
- Website person + trusted domain → same pattern guess
- No trusted domain → no pattern, `not_found`

Dummy domains never feed the pattern generator.

Optional `email_source`: `apollo` | `pattern_guess` | `none`. Added because person-source vs email-source must stay distinct for upsert and dedupe.

### Merge / Dedup Rules

Apollo records first. Duplicates matched by:

1. provider ID
2. normalized LinkedIn URL (`https://www.linkedin.com/in/jane-doe/` ≡ `linkedin.com/in/jane-doe`)
3. normalized non-pattern email
4. normalized full name + company
5. full name + current title + company

Pattern-guess emails are not used as a high-confidence cross-provider key. When the same person exists in both sources, keep Apollo and fill missing fields from website.

Final `len(contacts) <= max_results` after merge/dedupe.

### Persistence / Upsert Rules

`LeadDatabase.upsert_contact()` matches existing rows by `provider`+`provider_id`, then `(company_name, full_name)` case-insensitive.

Email strength: `verified > likely > unverified > pattern_guess > not_found`. Never replace verified with pattern_guess. Never erase populated fields with `None`. Apollo LinkedIn URL fills missing LinkedIn. Apollo provider_id upgrades a website row.

Added column: `contacts.email_source` TEXT via `_ensure_column`.

### Files Changed

**Created**

- `chillion_agents/app/lead_generation/contacts/orchestrator.py`
- `chillion_agents/app/lead_generation/contacts/domain.py`
- `chillion_agents/app/lead_generation/contacts/titles.py`
- `chillion_agents/tests/test_discovery_pipeline_phase3.py`

**Modified**

- `chillion_agents/app/api/routes/lead_generation.py` — thin discover route + `warnings`
- `chillion_agents/app/lead_generation/providers/apollo.py` — org domain metadata, search pre-filter, `email_source`
- `chillion_agents/app/lead_generation/contacts/discovery.py` — shared title matcher
- `chillion_agents/app/lead_generation/contacts/email.py` — do not clobber Apollo emails; set `email_source`
- `chillion_agents/app/lead_generation/models.py` — optional `email_source`
- `chillion_agents/app/lead_generation/storage/database.py` — `email_source` column + upsert
- `lib/api/agents.ts` — `warnings`, `email_source`
- `components/agents/LeadDiscoveryAgent.tsx` — Verified from `email_status`; warning banner; never source=LinkedIn
- `chillion_agents/tests/test_contact_search_phase1.py` — route tests patch orchestrator
- `PROGRESS.md` — this section

### Tests Added

`tests/test_discovery_pipeline_phase3.py` (mocked providers, no live Apollo):

- domain normalize / no invented domain / www match / notmicrosoft.com rejected
- former Google employee excluded; current microsoft.com included
- Senior IT Director included; VP Sales excluded
- Apollo full set skips website; Apollo zero / all-invalid / rate-limit / auth / timeout / missing key fall back
- missing trusted domain does not call Apollo
- fill-to-max 4 Apollo + 10 website → 10, Apollo first
- Jane Doe cross-provider dedupe prefers Apollo
- Apollo missing email → pattern_guess, provider stays apollo
- verified email not overwritten
- `find_emails=false` strips response email; stored verified email preserved
- dummy guessed domain unused for Apollo and pattern email
- upsert upgrades pattern_guess website row to Apollo verified + LinkedIn

### Test Results

```text
cd chillion_agents && python -m pytest tests/test_contact_search_phase1.py tests/test_apollo_provider_phase2.py tests/test_discovery_pipeline_phase3.py -q
66 passed, 254 warnings in 0.37s
```

- Phase 1: 20 passed
- Phase 2: 22 passed
- Phase 3: 24 passed
- Failed: none
- Warnings: pre-existing Pydantic Config / `datetime.utcnow()`
- Baseline before edits: 42 passed

### Known Issues

- Without a user-supplied domain, Apollo is skipped and website scrape usually returns 0 (dummy `{name}.com` is no longer treated as a website). Users should supply a domain or rely on Apollo when the key is present.
- `npm run lint` / `npm run build` still fail on **pre-existing** `SkillsWorkbench.tsx` and prior `any` / `loadStats` issues. Phase 3 did not introduce those.
- Company DummySearchProvider remains for the Companies tab, not contact discovery.

### Deferred to Phase 4

- Add to Outreach
- `saved_prospects` / SavedProspect changes
- EmailAgent / LinkedInAgent
- Waterfall enrichment, personal emails, phones
- Global rename of `FinanceContact`

### Phase Status

```
Phase 0: COMPLETE
Phase 1: COMPLETE
Phase 2: SUPERSEDED BY PHASE 3.5
Phase 3: COMPLETE
Phase 3.5: COMPLETE
Phase 4: NOT STARTED
Phase 5: NOT STARTED
```

---

## Phase 3.5 — Apollo Replaced by Prospeo

Status: **COMPLETE**. Apollo has been fully removed from the runtime. People discovery now uses Prospeo, then company-website fallback. Add to Outreach is **not** implemented (Phase 4).

### Why Apollo Was Removed

Live testing confirmed Apollo People Search returned `API_INACCESSIBLE` on the Free plan.

`POST /api/v1/mixed_people/api_search` is not included in Apollo’s Free plan, even with a master key. That made Apollo unusable for this project, so it was replaced with Prospeo rather than kept as a second fallback.

### Final Provider Architecture

```text
PeopleSearchProvider
        ↓
ProspeoPeopleProvider
        ↓
Website fallback
```

```text
ContactDiscoveryOrchestrator
        ↓
PeopleSearchProvider
        ↓
ProspeoPeopleProvider
        ↓
POST /search-person
        ↓
POST /bulk-enrich-person   (only when find_emails=true)
        ↓
current employer validation
        ↓
current title validation
        ↓
verified professional email when available
        ↓
pattern email fallback when needed
        ↓
website contact fallback when needed
        ↓
merge + dedupe
        ↓
LeadDatabase upsert
```

The generic `PeopleSearchProvider` abstraction in `providers/base.py` was kept. HTTP details stay inside `ProspeoPeopleProvider`. Tests still inject mock providers. FastAPI and React do not call Prospeo.

There is no Apollo branch and no Prospeo → Apollo → website chain.

### Prospeo Search Flow

Base URL: `https://api.prospeo.io`  
Auth header: `X-KEY` (server-side `PROSPEO_API_KEY` only)  
Content type: `application/json`

`POST /search-person` with:

```json
{
  "page": 1,
  "filters": {
    "person_job_title": {
      "include": ["Technical Recruiter"],
      "match_mode": "CONTAINS"
    },
    "company": {
      "websites": {
        "include": ["microsoft.com"]
      }
    }
  }
}
```

- Only a **trusted** user-supplied domain is sent. Dummy `{name}.com` guesses are never invented.
- Title filter uses `CONTAINS`, then the shared Phase 3 title matcher still runs on results.
- 25 people per page. Pagination stops once `max_results` can be satisfied (e.g. `max_results=5` fetches one page).
- `NO_RESULTS` is treated as 0 people, not a 500.

### Prospeo Enrichment Flow

Search is person discovery only. When `find_emails=true`:

`POST /bulk-enrich-person` (up to 50 records):

```json
{
  "only_verified_email": true,
  "enrich_mobile": false,
  "data": [
    {"identifier": "contact-0", "person_id": "abc123"},
    {"identifier": "contact-1", "person_id": "def456"}
  ]
}
```

Responses are reconciled by `identifier`, never by list order. `matched` people receive a verified work email. `not_matched` / `invalid_datapoints` keep the person and may later get a pattern guess. Phones are never requested.

When `find_emails=false`, Search Person still runs and Bulk Enrich Person does **not**.

### Email Strategy

- Revealed Prospeo email with `status=VERIFIED` → `email_status=verified`, `email_source=prospeo`
- No verified Prospeo email, trusted domain, `find_emails=true` → `EmailPatternGenerator`, `email_status=pattern_guess`, `email_source=pattern_guess`, **`provider` stays `prospeo`**
- `find_emails=false` → `email=None`, `email_status=not_found`, `email_source=none` on the response
- Upsert does not destroy a stored verified email just because a later request used `find_emails=false`
- Pattern guess never replaces a verified email
- UI Verified badge uses `email_status === "verified"` only, never `provider === "prospeo"`

### Current Employer Validation

Even after Prospeo website filtering, the returned current company domain (`enrichment_data.organization_primary_domain` from Prospeo `company.domain` / `company.website`) is compared with the trusted request domain using the shared `domains_match` helper.

- Requested `microsoft.com`, current `google.com` → DROP
- Requested `microsoft.com`, current `www.microsoft.com` → KEEP
- Missing current-org domain → DROP

### Current Title Validation

Shared `matches_target_title` (case-insensitive substring):

- Requested `Technical Recruiter`, current `Senior Technical Recruiter` → KEEP
- Requested `Technical Recruiter`, current `Account Executive` → DROP

### Website Fallback

Runs when:

- Prospeo is not configured
- no trusted domain
- Prospeo authentication failure
- Prospeo rate limit
- Prospeo credits exhausted
- Prospeo plan/access failure
- Prospeo API / timeout / 5xx failure
- Prospeo zero usable contacts
- Prospeo returns fewer than `max_results` (fill remaining)

Does **not** run when Prospeo already produced a full `max_results` set.

Provider **failure** vs provider **succeeded with zero people** are separate warnings. An auth failure does not also claim “Prospeo returned no current employees.”

### Merge / Dedup Rules

Priority:

1. Provider ID
2. Normalized LinkedIn URL
3. Non-pattern email
4. Normalized full name + company
5. Normalized full name + title + company

Pattern-guess emails are not a strong duplicate key. When Prospeo and website find the same person, keep Prospeo (verified email, LinkedIn, person ID). Final `len(contacts) <= max_results`.

### Persistence / Upsert

Existing generic columns `provider`, `provider_id`, `email_confidence`, `email_source` are used. There is no `prospeo_person_id` column. Ranking remains `verified > likely > unverified > pattern_guess > not_found`. Populated fields are never erased with `None`.

### Apollo Removal

Removed from the runtime:

- `chillion_agents/app/lead_generation/providers/apollo.py`
- Apollo exception classes from `providers/errors.py`
- Apollo exports from `providers/__init__.py`
- `apollo_api_key` / `APOLLO_API_KEY` from `app/config.py` and `.env.example`
- `ContactSource.APOLLO`
- Apollo selection logic from `orchestrator.py` and the discover route
- Apollo source labels in `LeadDiscoveryAgent.tsx`
- `tests/test_apollo_provider_phase2.py`

Historical Phase 0–3 documentation in this file still describes the original Apollo work. That implementation has been replaced.

### Files Changed

**Created**

- `chillion_agents/app/lead_generation/providers/prospeo.py` — Prospeo Search + Bulk Enrich client
- `chillion_agents/tests/test_prospeo_provider_phase35.py` — mocked HTTP + orchestrator tests

**Modified**

- `chillion_agents/app/lead_generation/providers/base.py` — kept
- `chillion_agents/app/lead_generation/providers/errors.py` — Prospeo exceptions only
- `chillion_agents/app/lead_generation/providers/__init__.py` — Prospeo exports
- `chillion_agents/app/lead_generation/contacts/orchestrator.py` — Prospeo-first; distinct failed vs zero-result warnings
- `chillion_agents/app/lead_generation/contacts/email.py` — do not clobber Prospeo emails
- `chillion_agents/app/lead_generation/contacts/titles.py` / `discovery.py` — comments
- `chillion_agents/app/lead_generation/models.py` — `ContactSource.PROSPEO`; `email_source` comment
- `chillion_agents/app/lead_generation/storage/database.py` — upsert prefers `prospeo`
- `chillion_agents/app/api/routes/lead_generation.py` — discover docstring
- `chillion_agents/app/config.py` — `prospeo_api_key`; Apollo key removed
- `chillion_agents/.env.example` — `PROSPEO_API_KEY=`; `APOLLO_API_KEY` removed
- `chillion_agents/tests/test_discovery_pipeline_phase3.py` — Prospeo → website behavior
- `components/agents/LeadDiscoveryAgent.tsx` — source display `Prospeo`
- `PROGRESS.md` — this section

**Deleted**

- `chillion_agents/app/lead_generation/providers/apollo.py`
- `chillion_agents/tests/test_apollo_provider_phase2.py`

### Tests Added / Updated

`tests/test_prospeo_provider_phase35.py` (mocked HTTP only; no live Prospeo calls):

- missing/blank key → `ProspeoNotConfiguredError`
- search body: `company.websites.include`, `person_job_title.include`, `match_mode=CONTAINS`, `page=1`
- mapping of `person_id`, provider, name, title, company, LinkedIn
- employer + title validation
- bulk enrich `only_verified_email=true`, `enrich_mobile=false`, unique identifiers
- verified email skips pattern; `not_matched` keeps person then pattern_guess
- `find_emails=false` skips bulk enrich
- `INVALID_API_KEY`, `INSUFFICIENT_CREDITS`, `PLAN_REQUIRED`, `NO_RESULTS`, 429, timeout, 5xx
- Prospeo failure / zero results → website; no Apollo
- partial fill + cross-source dedupe + upsert upgrade

Phase 3 pipeline tests were updated to Prospeo → website while preserving employer/title/domain/email/dedupe/upsert guarantees.

### Test Results

```text
cd chillion_agents && python -m pytest tests/test_contact_search_phase1.py tests/test_discovery_pipeline_phase3.py tests/test_prospeo_provider_phase35.py -q
67 passed, 274 warnings in 0.40s

cd chillion_agents && python -m pytest -q
67 passed, 274 warnings in 0.34s
```

- Phase 1: 20 passed
- Phase 3 (updated to Prospeo): 24 passed
- Phase 3.5: 23 passed
- Failed: none
- Apollo tests: removed (`test_apollo_provider_phase2.py`)
- Warnings: pre-existing Pydantic Config / `datetime.utcnow()`
- Baseline before edits: 66 passed (including 22 Apollo tests)
- Intermediate (Prospeo + Apollo still present): 89 passed
- Safe key check (does not print the key): `Prospeo key loaded: False` until `PROSPEO_API_KEY` is added to `chillion_agents/.env`

### Manual Test Instructions

1. Add `PROSPEO_API_KEY=<real key>` to `chillion_agents/.env` only. Do not commit it.
2. Confirm the key loads without printing it:

```bash
cd chillion_agents
python -c "from app.config import settings; print('Prospeo key loaded:', bool(settings.prospeo_api_key))"
```

3. Restart the backend, then in Contacts:

- Company: Microsoft
- Company Domain: microsoft.com
- Target Job Titles: Technical Recruiter
- Max Results: 5
- Find Work Emails: true

Expected: current Microsoft employees, Source = Prospeo, LinkedIn when Prospeo supplies it, Verified email when Prospeo finds one, Pattern Guess otherwise.

### Known Issues

- Without a user-supplied domain, Prospeo is skipped and website scrape usually returns 0.
- `npm run lint` / `npm run build` still fail on **pre-existing** `SkillsWorkbench.tsx`. Phase 3.5 did not introduce those.
- leftover `APOLLO_API_KEY` in a local `.env` is ignored (`extra="ignore"`) and is unused.

### Deferred to Phase 4

- Add to Outreach
- `saved_prospects` / SavedProspect changes
- EmailAgent / LinkedInAgent
- Waterfall enrichment, personal emails, phones
- Global rename of `FinanceContact`

### Phase Status (as of end of Phase 3.5)

```
Phase 0: COMPLETE
Phase 1: COMPLETE
Phase 2: SUPERSEDED BY PHASE 3.5
Phase 3: COMPLETE
Phase 3.5: COMPLETE
Phase 4: NOT STARTED
Phase 5: NOT STARTED
```
