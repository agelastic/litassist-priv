### Google CSE (Jade.io) Setup & Usage  🔑

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

   * Free tier = **100 requests/day**. Each `lookup` run uses **1 API call**.
   * Raise quota in Google Cloud if you need more.

5. **Billing (optional)**

   * The first 100 requests/day are free; if you enable billing you can buy extra units at US \$5 per 1,000 queries (May 2025 rates).

6. **Testing the key**

   * LitAssist performs a small “ping” query on startup: if credentials are wrong, you’ll get

     ```
     Error: Google CSE API test failed: ... 403 ...
     ```
   * Fix the key or CSE ID and rerun.

Once these two values are in `config.yaml`:

```yaml
google_cse:
  api_key:  "YOUR_GOOGLE_API_KEY"
  cse_id:   "YOUR_JADE_CSE_ID"
```

the **lookup** command will automatically:

1. Query Google CSE for Jade.io pages (max 3).
2. Feed the links into **Gemini 2.5 Pro**.
3. Return an IRAC-style answer with citations.

---

### Example

```bash
./litassist.py lookup "Is frustration a defence to costs in Australian contract law?"
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