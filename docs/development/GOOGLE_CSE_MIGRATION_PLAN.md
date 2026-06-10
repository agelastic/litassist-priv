# Google Custom Search JSON API -> Vertex AI Search Migration Plan

Last updated: 10/06/2026

Status: Validated design (scoping pass 10/06/2026 against official Google docs).
Not yet implemented. Deadline 01/01/2027.

## Background

Google announced (April 2026) that the Programmable Search Engine product family
is being restructured:

- The Programmable Search Element (JS widget) remains for site-specific search
  on <=50 domains.
- Vertex AI Search is the favoured alternative for users of the **Custom Search
  JSON API** with <=50 domains.
- A new "full web search" product is being introduced for use cases that need
  the entire Google index.
- All new engines must use "Sites to search" from the announcement date.
- Existing JSON API integrations must transition by **01/01/2027** (confirmed
  10/06/2026 at https://developers.google.com/custom-search/v1/overview; the API
  is already closed to new customers).

LitAssist uses the Custom Search JSON API directly (not the JS widget), so the
JSON API deprecation applies even though every CSE we use is under 50 domains.
Google publishes a dedicated migration guide for this exact path:
https://docs.cloud.google.com/generative-ai-app-builder/docs/migrate-from-cse

Note Google is mid-rebrand: "Vertex AI Search" is becoming "Agent Search" in the
docs; the product and API (`discoveryengine.googleapis.com`) are unchanged.

## Current usage map

JSON API call sites (all use `googleapiclient.discovery.build("customsearch", "v1", ...)`);
line numbers re-verified 10/06/2026:

| File | Purpose | CSE used |
|---|---|---|
| `litassist/cli.py:117` | Startup ping/health check | `cse_id` (Jade) |
| `litassist/citation/google_cse.py:56` | Citation verification | `cse_id` (Jade) |
| `litassist/citation_context.py:134` (build also at `:228`) | Citation context lookup | `cse_comprehensive` / `cse_austlii` |
| `litassist/commands/lookup/search.py:29` (build at `:67`) | Lookup command searches | `cse_id`, `cse_id_austlii`, `cse_id_comprehensive` |
| `test-scripts/test_integrations.py:184` | Integration smoke test | `cse_id` |
| `test-scripts/test_quality.py:520` | Quality test | `cse_id` |

Configured CSEs (per `docs/user/Google CSE setup.md`):

| Config key | Domains | Notes |
|---|---|---|
| `cse_id` (Jade.io) | `jade.io/*` (1 site) | Required |
| `cse_id_austlii` | `austlii.edu.au/*` (1 site) | Optional |
| `cse_id_comprehensive` | 6 patterns (austlii, *.gov.au, hcourt, fedcourt, lawcouncil, *.edu.au/law/*) | Optional, --comprehensive only |

All three are well under the 50-URL-pattern limit of basic website search.
Target replacement: **Vertex AI Search** with three corresponding website
"data stores" (basic website search, no advanced indexing).

## Validation findings (10/06/2026)

Confirmed against official Google Cloud docs (source URLs inline):

1. **Coverage confirmed.** A website data store is defined by "Sites to
   include"/"Sites to exclude" URL patterns spanning multiple domains; basic
   website search allows up to 50 included patterns, needs **no domain
   verification**, and is always created in the `global` location.
   (https://docs.cloud.google.com/generative-ai-app-builder/docs/prepare-data,
   .../create-data-store-es)
2. **Edition/pricing.** Website search (basic or advanced) requires
   **Enterprise edition**: USD 4.00 per 1,000 queries, with **10,000 free
   queries per account per month** (labelled "Free Trial"; no expiry stated -
   permanence unconfirmed). Compare CSE JSON API: 100 free/day (~3,000/month)
   then USD 5 per 1,000. Net: ~3x the free volume, cheaper per 1,000 after.
   Quota 300 search requests/minute - irrelevant headroom for this CLI.
   (https://cloud.google.com/generative-ai-app-builder/pricing,
   .../docs/enterprise-edition, .../quotas)
3. **Auth simplification.** The standard `search` method needs OAuth (ADC or
   service account), but **`servingConfigs.searchLite` accepts a plain API
   key** and exists specifically for CSE JSON API migrants searching public
   websites. This fits LitAssist's current API-key-in-`config.yaml` model -
   no service-account plumbing needed.
   (https://docs.cloud.google.com/generative-ai-app-builder/docs/authentication,
   .../reference/rest/v1/projects.locations.collections.engines.servingConfigs/searchLite)
4. **API shape confirmed.** discoveryengine v1; Google recommends searching at
   the **engine (app) level** (`engines.servingConfigs.search`) rather than the
   data-store level. Results carry `document.derivedStructData` with `title`,
   `link`, and (with `contentSearchSpec.snippetSpec.returnSnippet=true`) a
   `snippets` array - enough to preserve the `{title, link, snippet}` shape the
   wrapper promises. Python client: `google-cloud-discoveryengine` (currently
   0.20.0, still 0.x - pin the minor version).
   (https://docs.cloud.google.com/generative-ai-app-builder/docs/reference/rest/v1/projects.locations.collections.dataStores.servingConfigs/search,
   .../docs/snippets, https://pypi.org/project/google-cloud-discoveryengine/)
5. **Data residency.** Locations are `global`, `us`, `eu` only; **no Australian
   region**, and basic website data stores are global-only regardless. Accept
   `global`. (https://docs.cloud.google.com/generative-ai-app-builder/docs/locations)
6. **Open risk.** Whether a public-suffix pattern like `*.gov.au/*` is accepted
   by basic website search is not documented either way. Must be tested
   empirically in the spike before the comprehensive data store is committed.
7. **Snippet-quality risk stands.** Whether Vertex returns Jade.io snippets of
   equivalent quality for citation-variation matching still needs the spike
   regression (unchanged from the original sketch).

### Prototype status (blocked - named prerequisite)

A live one-query prototype was NOT run during this scoping pass. Local state
checked 10/06/2026: `gcloud` is installed and authenticated
(`vitaly.osipov@gmail.com`, project `gen-lang-client-0428254170`), but there is
no Application Default Credentials token, the `google-cloud-discoveryengine`
package is not installed, and no Vertex AI Search app/data store exists yet.
Creating one requires user-approved billable GCP actions:

1. Pick/confirm the GCP project and enable `discoveryengine.googleapis.com`.
2. Accept Enterprise-edition billing for website search.
3. Create the Jade-only website data store + search app (console or API).
4. Mint an API key for `searchLite` (the chosen path; `gcloud auth
   application-default login` only if the OAuth `search` fallback is ever
   needed).

Once those exist, the spike in Cutover step 2 is a <1h task.

## Target architecture

Replace the `googleapiclient` Custom Search calls with Vertex AI Search calls
scoped to a website data store per existing CSE, via **`searchLite` + API key**
(decision from finding 3; revisit only if searchLite limits bite).

Conceptual mapping:

| Today | After migration |
|---|---|
| Google Cloud project + API key + 3 CSE IDs | Same Google Cloud project + API key + 3 website data stores behind 1-3 search apps |
| `service.cse().list(q=..., cx=cse_id, num=N)` | `engines.servingConfigs.searchLite` with `pageSize=N`, `returnSnippet=true` |
| `items[].title / link / snippet` | `results[].document.derivedStructData.{title,link,snippets}` |
| API key in `config.yaml` (`google_cse.api_key`) | API key in `config.yaml` (`vertex_search.api_key`) plus project/engine IDs |

Each data store is configured with the same site patterns as the corresponding
CSE so result quality stays comparable.

## Code changes (planned)

Aim to keep the migration narrowly scoped: one new low-level wrapper plus
call-site replacements. No refactor of surrounding logic.

1. **New module** `litassist/search/vertex.py` exposing a single function:

   ```python
   def vertex_site_search(
       engine_id: str,
       query: str,
       page_size: int,
       engine_name: str = "",
   ) -> list[dict]:
       """Return a list of {title, link, snippet} from Vertex AI Search."""
   ```

   Internally: `searchLite` REST call (API key) or
   `google.cloud.discoveryengine_v1` client if the OAuth path is chosen at
   spike time; single project/location from config, engine chosen per call
   site.

2. **Config additions** (`config.yaml` template + `litassist/config.py`):

   ```yaml
   vertex_search:
     project_id:             "..."
     location:               "global"      # only option for basic website search
     api_key:                "..."         # searchLite path
     engine_jade:            "..."
     engine_austlii:         "..."         # optional
     engine_comprehensive:   "..."         # optional
   ```

   Old `google_cse.*` keys remain readable for one release, with a deprecation
   warning, then removed.

3. **Call-site replacements** (one per file in the usage map above). Each is a
   small, mechanical swap from `service.cse().list(...).execute()` to
   `vertex_site_search(...)`. Snippet/link/title shape is preserved by the
   wrapper so downstream parsers are untouched.

4. **Startup ping** (`litassist/cli.py:117`) calls `vertex_site_search` with
   `query="test"`, `page_size=1` against the Jade engine. Same failure-fast
   behaviour as today.

5. **Citation verification** (`litassist/citation/google_cse.py`): the existing
   variation-matching logic stays as-is; only the search call changes. Logging
   keys (`google_cse_validation`, `google_cse_search_error`) are renamed to
   `vertex_search_validation` / `vertex_search_error` for clarity in audit
   logs.

6. **Tests**:
   - Unit tests in `tests/unit/` already mock the search call; they get
     re-pointed at the new wrapper.
   - `test-scripts/test_integrations.py` and `test_quality.py` get equivalent
     manual smoke tests against Vertex AI Search.

7. **Docs**:
   - Replace `docs/user/Google CSE setup.md` with `docs/user/Vertex AI Search setup.md`
     (or rename in place) covering data store creation, IAM, quotas, billing.
   - Update `docs/user/LitAssist_Reference_Manual.md`, `INSTALLATION.md`,
     and `README.md` references.

## Cutover steps

Every step has an explicit test gate; a step is not done until its gate passes.

1. **[USER] GCP setup** (see Prototype status): enable API, accept Enterprise
   billing, create Jade data store + app, mint API key.
   **Test gate:** one raw `searchLite` REST call (curl) returns HTTP 200 with
   at least one Jade.io result for a known citation query.
2. **Spike**: prototype `vertex_site_search` against the Jade
   engine; run the citation-verification regression
   (`test-scripts/test_quality.py` Jade tests) against it and compare hit rate
   with the current CSE. Also test a throwaway data store with `*.gov.au/*` to
   settle finding 6.
   **Test gate:** hit-rate parity with the live CSE on the same citation set
   (document the two numbers in this file); `*.gov.au/*` verdict recorded.
   Gate everything below on parity.
3. Add `vertex_search.*` config keys side-by-side with `google_cse.*` behind
   `use_vertex_search: false` (default).
   **Test gate:** unit tests cover config parsing for both key families and
   the flag default; full pytest green.
4. Implement `litassist/search/vertex.py`; replace call sites one at a time
   (cli ping -> citation verification -> citation_context -> lookup), each
   behind the flag; re-point unit-test mocks per call site.
   **Test gate (per call site, before moving to the next):** full pytest green
   with the flag off AND on (mocked); manual smoke of the replaced site with
   the flag on against the real API (`test-scripts/test_integrations.py` for
   the ping/citation sites, a real `litassist lookup` run for search.py).
5. Create the austlii + comprehensive data stores/apps; flip default to
   `use_vertex_search: true`; keep the old path for one release.
   **Test gate:** full pytest; `test-scripts/test_quality.py` Jade + CSE tests
   against Vertex; `test-scripts/test_cli_comprehensive.sh` lookup and verify
   sections pass with the new default.
6. Remove old code paths and `google_cse.*` config keys; replace
   `docs/user/Google CSE setup.md`; update Reference Manual, INSTALLATION,
   README.
   **Test gate:** full pytest; `grep -rn "google_cse\|customsearch"` returns
   only historical doc mentions (CHANGELOG etc.); one end-to-end real run each
   of `litassist lookup` and `litassist verify --citations`.

Target: steps 1-4 by Q3 2026, default flip Q4 2026, removal of legacy code
before 01/01/2027.

## Out of scope

- Migrating to the new Google "full web search" product. None of LitAssist's
  use cases require it.
- Re-introducing the JS Search Element. LitAssist is a CLI; the widget does
  not apply.
- Adding AI-summarisation features that Vertex AI Search exposes. Result
  ranking/snippets are sufficient; LLM analysis already happens downstream.
