### Google CSE Setup & Usage

LitAssist uses up to three Google Custom Search Engines for different legal databases:

## CSE 1: Jade.io (Primary - Required)

**Used by:**
- Citation verification (`citation_verify.py`) - validates all citations in LLM outputs
- Lookup command (`lookup.py`) - primary legal research source

1. **Create the Jade.io CSE**

   1. Go to [https://programmablesearchengine.google.com/about/](https://programmablesearchengine.google.com/about/) and click **Add**.
   2. In **Sites to search**, enter `jade.io/*` → Save.
   3. Under **Setup ▸ Basics ▸ Search engine ID**, copy the alphanumeric string — this is your **`cse_id`** for `config.yaml`.

## CSE 2: AustLII (Optional)

**Used by:**
- Lookup command (`lookup.py`) - secondary legal research source, searched after Jade.io

1. **Create the AustLII CSE**

   1. Go to [https://programmablesearchengine.google.com/about/](https://programmablesearchengine.google.com/about/) and click **Add**.
   2. In **Sites to search**, enter `austlii.edu.au/*` → Save.
   3. Under **Setup ▸ Basics ▸ Search engine ID**, copy the alphanumeric string — this is your **`cse_id_austlii`** for `config.yaml`.

## CSE 3: Comprehensive (Optional)

**Used by:**
- Lookup command (`lookup.py`) - only when `--comprehensive` flag is used

1. **Create the Comprehensive CSE**

   1. Go to [https://programmablesearchengine.google.com/](https://programmablesearchengine.google.com/) and click **Add**.
   2. In **Sites to search**, add these domains:
      ```
      austlii.edu.au
      *.gov.au
      hcourt.gov.au
      fedcourt.gov.au
      lawcouncil.asn.au
      *.edu.au/law/*
      ```
   3. Under **Setup ▸ Basics ▸ Search engine ID**, copy the alphanumeric string — this is your **`cse_id_comprehensive`** for `config.yaml`.

---

## Common Setup for All CSEs

2. **Enable the Custom Search JSON API**

   * Open [https://console.cloud.google.com/apis/library/customsearch.googleapis.com](https://console.cloud.google.com/apis/library/customsearch.googleapis.com), pick your project (or create one) and click **Enable**.

3. **Create an API key**

   * In the same project, go to **APIs & Services ▸ Credentials ▸ + Create credentials ▸ API key**.
   * Copy the key and store it as `google_cse.api_key` in `config.yaml`.

4. **Quota considerations**

   * Free tier = **100 requests/day**. Each `lookup` run uses:
     - Standard mode: **2 API calls** (Jade.io CSE + AustLII CSE if configured)
     - Comprehensive mode: **3 API calls** (Jade.io CSE + AustLII CSE if configured + Comprehensive CSE)
   * Citation verification: **1 API call** per command that generates citations
   * Raise quota in Google Cloud if you need more.

5. **Billing (optional)**

   * The first 100 requests/day are free; if you enable billing you can buy extra units at US \$5 per 1,000 queries (May 2025 rates).

6. **Testing the key**

   * LitAssist performs a small "ping" query on startup: if credentials are wrong, you'll get

     ```
     Error: Google CSE API test failed: ... 403 ...
     ```
   * Fix the key or CSE ID and rerun.

---

## Configuration

Once these values are in `config.yaml`:

```yaml
google_cse:
  api_key:  "YOUR_GOOGLE_API_KEY"                      # Shared API key for all CSEs
  cse_id:   "YOUR_JADE_CSE_ID"                        # Required: Jade.io CSE
  cse_id_austlii: "YOUR_AUSTLII_CSE_ID"               # Optional: AustLII CSE
  cse_id_comprehensive: "YOUR_COMPREHENSIVE_CSE_ID"    # Optional: Comprehensive CSE
```

---

## How the CSEs are Used

### Standard Lookup Mode

```bash
litassist lookup "contract formation elements"
```

Performs these searches:
1. **Jade.io CSE**: 5 results
2. **AustLII CSE**: 5 results (if configured)
3. 1.5 second delay between API calls

### Comprehensive Lookup Mode

```bash
litassist lookup "contract formation elements" --comprehensive
```

Performs these searches:
1. **Jade.io CSE**: 10 results (searches question only)
2. **AustLII CSE**: 10 results (searches question only, if configured)
3. **Comprehensive CSE**: 10 results (if configured)
   - Without `--context`: searches question only
   - With `--context`: searches combined "question context" string
4. 1.5 second delays between API calls

**Note**: When both `--comprehensive` and `--context` are used, the comprehensive CSE search combines them to find more contextually relevant results from broader sources.

### Citation Verification

Automatically triggered when any command generates content with citations:
- Uses only **Jade.io CSE**
- Searches for each citation to verify it exists
- Up to 10 results per citation search

---

## Context Option

The lookup command supports a `--context` option to provide additional guidance:

```bash
# Context guides LLM analysis for all searches
litassist lookup "negligence principles" --context "Focus on medical malpractice cases involving surgical errors"

# With --comprehensive, context is also included in comprehensive CSE search query
litassist lookup "negligence principles" --context "medical malpractice surgical errors" --comprehensive
```

In standard mode, context only guides the LLM's analysis of results. In comprehensive mode, context is also combined with the question for the comprehensive CSE search, helping find more relevant results from broader sources.

## Example

```bash
litassist lookup "Is frustration a defence to costs in Australian contract law?"
```

*Output* (truncated):

```
I – Issue
Whether frustration of the underlying contract can itself justify a departure from the usual costs order…

R – Rule
Hollis v Vabu Pty Ltd [2001] HCA 44; Laurinda Pty Ltd v Capalaba Park Shopping Centre Pty Ltd (1989) 166 CLR 623…

A – Application
The High Court in Hollis emphasised…

C – Conclusion
Frustration alone will rarely displace the orthodox indemnity principle; however, courts retain…
```

Citations include direct Jade.io links produced in step 1.