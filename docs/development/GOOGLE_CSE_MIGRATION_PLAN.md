# Google Custom Search JSON API -> Vertex AI Search Migration Plan

Last updated: 13/05/2026

Status: Design sketch. Not yet implemented. Deadline 01/01/2027.

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
- Existing JSON API integrations must transition by **01/01/2027**.

LitAssist uses the Custom Search JSON API directly (not the JS widget), so the
JSON API deprecation applies even though every CSE we use is under 50 domains.

## Current usage map

JSON API call sites (all use `googleapiclient.discovery.build("customsearch", "v1", ...)`):

| File | Purpose | CSE used |
|---|---|---|
| `litassist/cli.py:141` | Startup ping/health check | `cse_id` (Jade) |
| `litassist/citation/google_cse.py:36-55` | Citation verification | `cse_id` (Jade) |
| `litassist/citation_context.py:122` | Citation context lookup | `cse_id` (Jade) |
| `litassist/commands/lookup/search.py:29` | Lookup command searches | `cse_id`, `cse_id_austlii`, `cse_id_comprehensive` |
| `test-scripts/test_integrations.py:354` | Integration smoke test | `cse_id` |
| `test-scripts/test_quality.py:638` | Quality test | `cse_id` |

Configured CSEs (per `docs/user/Google CSE setup.md`):

| Config key | Domains | Notes |
|---|---|---|
| `cse_id` (Jade.io) | `jade.io/*` (1 site) | Required |
| `cse_id_austlii` | `austlii.edu.au/*` (1 site) | Optional |
| `cse_id_comprehensive` | 6 patterns (austlii, *.gov.au, hcourt, fedcourt, lawcouncil, *.edu.au/law/*) | Optional, --comprehensive only |

All three are well under 50 domains, all use "Sites to search". Target
replacement: **Vertex AI Search** with three corresponding "data stores".

## Target architecture

Replace the `googleapiclient` Custom Search calls with Vertex AI Search
"search" API calls scoped to a website data store per existing CSE.

Conceptual mapping:

| Today | After migration |
|---|---|
| Google Cloud project + API key + 3 CSE IDs | Same Google Cloud project + service account + 3 Vertex AI Search data stores |
| `service.cse().list(q=..., cx=cse_id, num=N)` | Vertex AI Search `serving_configs.search` with `pageSize=N` |
| `items[].title / link / snippet` | `results[].document.derivedStructData.{title,link,snippets}` |
| API key in `config.yaml` (`google_cse.api_key`) | Service account JSON path or ADC, plus project/location IDs |

Each data store is configured with the same site patterns as the corresponding
CSE so result quality stays comparable.

## Code changes (planned)

Aim to keep the migration narrowly scoped: one new low-level wrapper plus
call-site replacements. No refactor of surrounding logic.

1. **New module** `litassist/search/vertex.py` exposing a single function:

   ```python
   def vertex_site_search(
       data_store_id: str,
       query: str,
       page_size: int,
       data_store_name: str = "",
   ) -> list[dict]:
       """Return a list of {title, link, snippet} from Vertex AI Search."""
   ```

   Internally: `google.cloud.discoveryengine_v1` client, single project/location
   from config, `data_store_id` chosen per call site.

2. **Config additions** (`config.yaml` template + `litassist/config.py`):

   ```yaml
   vertex_search:
     project_id:                 "..."
     location:                   "global"      # or eu / au if available
     credentials_file:           "..."         # optional; ADC if omitted
     data_store_jade:            "..."
     data_store_austlii:         "..."         # optional
     data_store_comprehensive:   "..."         # optional
   ```

   Old `google_cse.*` keys remain readable for one release, with a deprecation
   warning, then removed.

3. **Call-site replacements** (one per file in the usage map above). Each is a
   small, mechanical swap from `service.cse().list(...).execute()` to
   `vertex_site_search(...)`. Snippet/link/title shape is preserved by the
   wrapper so downstream parsers are untouched.

4. **Startup ping** (`litassist/cli.py:141`) calls `vertex_site_search` with
   `query="test"`, `page_size=1` against the Jade data store. Same failure-fast
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

## Open questions

- Pricing/quotas for Vertex AI Search vs current 100/day free tier of the JSON
  API. Need confirmation before recommending migration to existing users.
- Australian region availability for the data stores (data residency). Default
  to `location: "global"` unless an au/eu region offers acceptable latency.
- Whether Vertex AI Search returns Jade.io snippets of equivalent quality for
  citation matching. Spike: run the citation verification suite against a
  Jade-only data store and compare hit rate to current CSE.
- Authentication preference: service-account JSON vs Application Default
  Credentials. ADC is cleaner for developer machines; JSON is simpler in
  containerised deployments.

## Rollout

1. Spike: build a single data store mirroring the Jade CSE, prototype
   `vertex_site_search`, run citation verification regression. Gate further
   work on parity.
2. Add config keys side-by-side with the old `google_cse.*` keys; keep both
   working behind a feature flag (`use_vertex_search: false` default).
3. Replace call sites one at a time (cli ping -> citation verification ->
   citation_context -> lookup), each behind the flag.
4. Flip default to `use_vertex_search: true`, keep old path for one release.
5. Remove old code paths and `google_cse.*` config keys. Update all docs.

Target: complete steps 1-3 by Q3 2026, default flip Q4 2026, removal of legacy
code before 01/01/2027.

## Out of scope

- Migrating to the new Google "full web search" product. None of LitAssist's
  use cases require it.
- Re-introducing the JS Search Element. LitAssist is a CLI; the widget does
  not apply.
- Adding AI-summarisation features that Vertex AI Search exposes. Result
  ranking/snippets are sufficient; LLM analysis already happens downstream.
