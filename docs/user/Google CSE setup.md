### Google CSE Setup & Usage

1. **Create a CSE**

   1. Go to [https://programmablesearchengine.google.com/about/](https://programmablesearchengine.google.com/about/) and click **Add**.
   2. In **Sites to search**, enter `jade.io/*` → Save.
   3. Under **Setup ▸ Basics ▸ Search engine ID**, copy the alphanumeric string — this is your **`cse_id`** for `config.yaml`.

2. **Enable the Custom Search JSON API**

   * Open [https://console.cloud.google.com/apis/library/customsearch.googleapis.com](https://console.cloud.google.com/apis/library/customsearch.googleapis.com), pick your project (or create one) and click **Enable**.

3. **Create an API key**

   * In the same project, go to **APIs & Services ▸ Credentials ▸ + Create credentials ▸ API key**.
   * Copy the key and store it as `google_cse.api_key` in `config.yaml`.

4. **Quota considerations**

   * Free tier = **100 requests/day**. Each `lookup` run uses:
     - Standard mode: **2 API calls** (5 results each from Jade.io and AustLII CSE if configured)
     - Comprehensive mode: **3 API calls** (10 results each from Jade.io, AustLII CSE if configured, and secondary CSE)
   * Raise quota in Google Cloud if you need more.

5. **Billing (optional)**

   * The first 100 requests/day are free; if you enable billing you can buy extra units at US \$5 per 1,000 queries (May 2025 rates).

6. **Testing the key**

   * LitAssist performs a small “ping” query on startup: if credentials are wrong, you’ll get

     ```
     Error: Google CSE API test failed: ... 403 ...
     ```
   * Fix the key or CSE ID and rerun.

Once these values are in `config.yaml`:

```yaml
google_cse:
  api_key:  "YOUR_GOOGLE_API_KEY"
  cse_id:   "YOUR_JADE_CSE_ID"
  cse_id_comprehensive: "YOUR_COMPREHENSIVE_CSE_ID"  # Optional: for broader legal sources
```

the **lookup** command will automatically:

1. Query Google CSE for legal sources:
   - Standard: up to 5 Jade.io + 5 AustLII sources
   - Comprehensive: up to 10 Jade.io + 10 AustLII + 10 broader sources
2. Feed the links into **Gemini 2.5 Pro**.
3. Return an IRAC-style answer with citations.

---

### Setting Up a Secondary CSE for Comprehensive Mode (Optional)

To enable broader legal searches beyond Jade.io when using `--comprehensive`:

1. **Create a second CSE** at [https://programmablesearchengine.google.com/](https://programmablesearchengine.google.com/)
2. **Add broader legal sites**:
   ```
   austlii.edu.au
   *.gov.au
   hcourt.gov.au
   fedcourt.gov.au
   lawcouncil.asn.au
   *.edu.au/law/*
   ```
3. **Copy the Search engine ID** and add it to config.yaml as `cse_id_comprehensive`
4. **Use the same API key** - no need for a separate key

When configured, the `--comprehensive` flag will search both:
- **Primary CSE (Jade)**: Up to 10 Jade.io sources
- **AustLII CSE**: Up to 10 AustLII sources
- **Secondary CSE**: Up to 10 additional sources from government, courts, and academic sites

---

### Comprehensive Mode

The lookup command supports a `--comprehensive` flag for exhaustive analysis:

```bash
# Standard search (up to 5 Jade.io + 5 AustLII sources)
litassist lookup "contract formation elements"

# Comprehensive search (up to 10 Jade.io + 10 AustLII + 10 broader sources)
litassist lookup "contract formation elements" --comprehensive
``` 

**Note**: Comprehensive mode uses significantly more API calls. Consider your daily quota when using this feature.

### Context Option

The lookup command supports a `--context` option to provide additional guidance:

```bash
litassist lookup "negligence principles" --context "Focus on medical malpractice cases involving surgical errors"
```

This helps narrow the analysis to specific aspects of your legal question.

### Example

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
