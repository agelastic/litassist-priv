"""
Rapid case-law lookup via Google CSE or Jade + Gemini.

This module implements the 'lookup' command which searches for legal information
via Google Custom Search (AustLII) or Jade, then processes the results with Google Gemini
to produce a structured legal answer citing relevant cases.
"""

import click
import re
import requests
import warnings
import os
import time

from litassist.config import CONFIG
from litassist.utils import save_log, heartbeat, timed, OUTPUT_DIR
from litassist.llm import LLMClient

# Suppress Google API cache warning
os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"
warnings.filterwarnings("ignore", message=".*file_cache.*")


@timed
def format_lookup_output(content: str, extract: str = None) -> str:
    """
    Add basic structure to lookup output or extract specific information.

    Args:
        content: The raw LLM response
        extract: Type of extraction - 'citations', 'principles', or 'checklist'

    Returns:
        Formatted output based on extraction type
    """
    if extract == "citations":
        # Extract citations using multiple regex patterns
        citations = set()

        # Pattern 1: [Year] Court abbreviation number
        citations.update(re.findall(r"\[\d{4}\]\s+[A-Z]+[A-Za-z]*\s+\d+", content))

        # Pattern 2: (Year) volume court page
        citations.update(
            re.findall(r"\(\d{4}\)\s+\d+\s+[A-Z]+[A-Za-z]*\s+\d+", content)
        )

        # Pattern 3: Act references
        citations.update(re.findall(r"[A-Za-z\s]+Act\s+\d{4}\s*\([A-Z]+\)", content))

        # Pattern 4: Section references with acts
        citations.update(
            re.findall(
                r"[A-Za-z\s]+Act\s+\d{4}\s*\([A-Z]+\)\s+s\s*\d+[A-Za-z]*", content
            )
        )

        if citations:
            return "CITATIONS FOUND:\n" + "\n".join(sorted(citations))
        else:
            return "No clear citations found in the response."

    elif extract == "principles":
        # Extract sentences that contain legal principles (simple heuristic)
        lines = content.split("\n")
        principles = []

        for line in lines:
            line = line.strip()
            # Look for lines that start with numbers or contain key legal terms
            if re.match(r"^\d+\.", line) or any(
                term in line.lower()
                for term in [
                    "must",
                    "requires",
                    "establishes",
                    "principle",
                    "rule",
                    "test",
                    "elements",
                ]
            ):
                if len(line) > 20:  # Filter out very short lines
                    principles.append(line)

        if principles:
            return "LEGAL PRINCIPLES:\n" + "\n".join(
                f"• {p}" for p in principles[:10]
            )  # Limit to 10
        else:
            return "No clear legal principles extracted from the response."

    elif extract == "checklist":
        # Extract actionable items or requirements
        lines = content.split("\n")
        checklist_items = []

        for line in lines:
            line = line.strip()
            # Look for lines that suggest requirements or steps
            if any(
                word in line.lower()
                for word in [
                    "must",
                    "should",
                    "require",
                    "need",
                    "evidence",
                    "prove",
                    "establish",
                    "demonstrate",
                ]
            ):
                if len(line) > 15 and not line.startswith(
                    "http"
                ):  # Filter out URLs and short lines
                    # Clean up the line
                    clean_line = re.sub(r"^[-•*]\s*", "", line)  # Remove bullet points
                    clean_line = re.sub(
                        r"^\d+\.\s*", "", clean_line
                    )  # Remove numbering
                    if clean_line and len(clean_line) > 10:
                        checklist_items.append(clean_line)

        if checklist_items:
            return "PRACTICAL CHECKLIST:\n" + "\n".join(
                f"□ {item}" for item in checklist_items[:15]
            )  # Limit to 15
        else:
            return "No clear checklist items extracted from the response."

    else:
        # Default: Add basic structure markers to the content
        structured = content

        # Add structure markers if they don't already exist
        if "=== LEGAL PRINCIPLES ===" not in structured:
            # Try to identify and mark sections
            structured = re.sub(
                r"(Legal principles?|Principles?|Rules?):?\s*\n",
                r"=== LEGAL PRINCIPLES ===\n",
                structured,
                flags=re.IGNORECASE,
            )
            structured = re.sub(
                r"(Key cases?|Cases?|Authorities?):?\s*\n",
                r"=== KEY CASES ===\n",
                structured,
                flags=re.IGNORECASE,
            )
            structured = re.sub(
                r"(Citations?|References?|Sources?):?\s*\n",
                r"=== CITATIONS LIST ===\n",
                structured,
                flags=re.IGNORECASE,
            )
            structured = re.sub(
                r"(Checklist|Requirements?|Elements?):?\s*\n",
                r"=== PRACTICAL CHECKLIST ===\n",
                structured,
                flags=re.IGNORECASE,
            )

        return structured


@timed
def fetch_jade_links(question):
    """
    Fetch Australian case law links relevant to the query.

    This function retrieves links from Jade's public site when possible,
    or falls back to selected landmark Australian cases.

    Args:
        question: The legal question to search for.

    Returns:
        A list of relevant Australian case law links.
    """
    # Simplify the search string to avoid complex queries
    # Focus on key legal terms that are likely to yield results
    search_terms = question.lower()
    for term in ["what is", "how to", "can i", "should", "would", "could"]:
        search_terms = search_terms.replace(term, "")
    search_terms = re.sub(r"[^\w\s]", "", search_terms).strip()

    # Map common legal topics to known important cases (fallback mechanism)
    landmark_cases = {
        "defamation": [
            "https://jade.io/article/68176",  # Lange v Australian Broadcasting Corporation
            "https://jade.io/article/182648",  # Dow Jones v Gutnick
        ],
        "privacy": [
            "https://jade.io/article/228583",  # Australian Broadcasting Corp v Lenah Game Meats
            "https://jade.io/article/206177",  # Giller v Procopets
        ],
        "negligence": [
            "https://jade.io/article/67193",  # Donoghue v Stevenson
            "https://jade.io/article/67538",  # Wyong Shire Council v Shirt
        ],
        "contract": [
            "https://jade.io/article/66168",  # Carlill v Carbolic Smoke Ball Co
            "https://jade.io/article/66987",  # Toll (FGCT) Pty Ltd v Alphapharm Pty Ltd
        ],
        "copyright": [
            "https://jade.io/article/260168",  # IceTV v Nine Network
            "https://jade.io/article/66452",  # Computer Edge v Apple Computer
        ],
        "constitutional": [
            "https://jade.io/article/410717",  # McCloy v New South Wales
            "https://jade.io/article/409090",  # Commonwealth v Tasmania (Tasmanian Dam Case)
        ],
        "criminal": [
            "https://jade.io/article/67604",  # He Kaw Teh v The Queen
            "https://jade.io/article/68001",  # R v Tang
        ],
    }

    # Try to fetch from homepage first (reliable but may not be topic-specific)
    try:
        jade_homepage = "https://jade.io/"
        response = requests.get(
            jade_homepage,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            },
            timeout=10,
        )

        # Find citation links on the homepage
        jade_links = []
        if response.status_code == 200:
            matches = re.findall(
                r'href="(https://jade\.io/(?:article|j)[^"]+)"', response.text
            )

            # Process and clean up links
            for match in matches:
                # Remove any query parameters or fragments
                clean_link = match.split("?")[0].split("#")[0]
                if clean_link not in jade_links and "/article/" in clean_link:
                    jade_links.append(clean_link)

        if jade_links:
            # If we have links from the homepage, use the first three
            click.echo("Found recent Australian case law from Jade.")
            return jade_links[:3]

    except Exception as e:
        click.echo(f"Warning: Could not access Jade homepage: {e}")

    # If homepage approach failed, look for topic-specific landmark cases
    for topic, cases in landmark_cases.items():
        if topic in search_terms or topic in question.lower():
            click.echo(f"Using landmark Australian cases related to {topic}.")
            return cases[:3]

    # If no specific topic matched, return general important cases
    click.echo("Using general landmark Australian cases.")
    general_cases = [
        "https://jade.io/article/68176",  # Lange v Australian Broadcasting Corporation
        "https://jade.io/article/260168",  # Google Inc v Australian Competition and Consumer Commission
        "https://jade.io/article/410717",  # McCloy v New South Wales
    ]
    return general_cases


@click.command()
@click.argument("question")
@click.option("--mode", type=click.Choice(["irac", "broad"]), default="irac")
@click.option(
    "--engine",
    type=click.Choice(["google", "jade"]),
    default="google",
    help="Search engine to use (google for AustLII via CSE, jade for Jade.io)",
)
@click.option(
    "--extract",
    type=click.Choice(["citations", "principles", "checklist"]),
    help="Extract specific information in a structured format",
)
@timed
def lookup(question, mode, engine, extract):
    """
    Rapid case-law lookup via Google CSE or Jade + Gemini.

    Searches for legal information using either:
    - Google Custom Search on AustLII (default)
    - Jade.io public search

    Then processes the results with Google Gemini to produce a structured
    legal answer citing relevant cases.

    Args:
        question: The legal question to search for.
        mode: Answer format - 'irac' (Issue, Rule, Application, Conclusion) for
              structured analysis, or 'broad' for more creative exploration.
        engine: The search engine to use - 'google' for AustLII via CSE, or 'jade' for Jade.io.
        extract: Extract specific information - 'citations' for case references,
                'principles' for legal rules, or 'checklist' for practical items.

    Raises:
        click.ClickException: If there are errors with the search or LLM API calls.
    """
    # Fetch case links based on the selected engine
    if engine == "google":
        # Fetch AustLII links via Google Custom Search
        try:
            from googleapiclient.discovery import build

            # Disable cache to avoid warning
            service = build(
                "customsearch", "v1", developerKey=CONFIG.g_key, cache_discovery=False
            )
            res = (
                service.cse()
                .list(q=question, cx=CONFIG.cse_id, num=3, siteSearch="austlii.edu.au")
                .execute()
            )
        except Exception as e:
            raise click.ClickException(f"Google CSE error: {e}")
        links = [item.get("link") for item in res.get("items", [])]
    else:  # engine == "jade"
        # Fetch links via Jade's public search
        links = fetch_jade_links(question)

    # Display found links
    click.echo("Found links:")
    for link in links:
        click.echo(f"- {link}")

    # Prepare prompt
    prompt = f"Question: {question}\nLinks:\n" + "\n".join(links)

    # Add extraction-specific instructions
    if extract:
        if extract == "citations":
            prompt += "\n\nAlso provide a clear 'CITATIONS' section that lists all case citations and legislation references in a format easy to copy and use."
        elif extract == "principles":
            prompt += "\n\nAlso provide a clear 'LEGAL PRINCIPLES' section that lists the key legal rules and principles in a structured format suitable for advice letters."
        elif extract == "checklist":
            prompt += "\n\nAlso provide a clear 'PRACTICAL CHECKLIST' section that lists actionable requirements, evidence needed, and steps to take."
    # Set parameters based on mode
    # IRAC mode uses lower temperature for more precise, deterministic answers
    # Broad mode uses higher temperature for more creative exploration
    if mode == "irac":
        overrides = {"temperature": 0, "top_p": 0.1}
    else:
        overrides = {"temperature": 0.5, "top_p": 0.9}

    # Call the LLM
    client = LLMClient("google/gemini-2.5-pro-preview", temperature=0, top_p=0.2)
    call_with_hb = heartbeat(CONFIG.heartbeat_interval)(client.complete)
    try:
        content, usage = call_with_hb(
            [
                {
                    "role": "system",
                    "content": "Australian law only. Cite sources. Provide well-structured, concise responses with clear sections. Begin with a summary, then provide analysis with supporting case law, and end with a definitive conclusion. Avoid repeating yourself and maintain coherence throughout the response.",
                },
                {"role": "user", "content": prompt},
            ],
            **overrides,
        )
    except Exception as e:
        raise click.ClickException(f"LLM error during lookup: {e}")

    # Citation guard: retry once if no AustLII or Jade pattern found
    if not re.search(r"(austlii|jade)", content, re.IGNORECASE):
        try:
            content, usage = call_with_hb(
                [
                    {"role": "system", "content": "Australian law only. Cite sources."},
                    {"role": "user", "content": prompt + "\n\n(Cite your sources!)"},
                ],
                **overrides,
            )
        except Exception as e:
            raise click.ClickException(f"LLM retry error during lookup: {e}")

    # CRITICAL: Validate citations immediately to prevent cascade errors
    citation_issues = client.validate_citations(content)
    if citation_issues:
        # Prepend warnings to content so they appear prominently
        citation_warning = "--- CITATION VALIDATION WARNINGS ---\n"
        citation_warning += "\n".join(citation_issues)
        citation_warning += "\n" + "-" * 40 + "\n\n"
        content = citation_warning + content

    # Apply formatting based on extract option
    formatted_content = format_lookup_output(content, extract)

    # Save output to timestamped file
    # Create a slug from the question for the filename
    question_slug = re.sub(r"[^\w\s-]", "", question.lower())
    question_slug = re.sub(r"[-\s]+", "_", question_slug)
    # Limit slug length and ensure it's not empty
    question_slug = question_slug[:50].strip("_") or "query"

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    # Include extract type in filename if specified
    extract_suffix = f"_{extract}" if extract else ""
    output_file = os.path.join(
        OUTPUT_DIR, f"lookup{extract_suffix}_{question_slug}_{timestamp}.txt"
    )

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"Lookup Query: {question}\n")
        f.write(f"Mode: {mode}\n")
        f.write(f"Engine: {engine}\n")
        if extract:
            f.write(f"Extract: {extract}\n")
        f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("-" * 80 + "\n\n")
        f.write(formatted_content)

    click.echo(f'\nOutput saved to: "{output_file}"')

    # Save audit log
    params_str = f"mode={mode}, engine={engine}"
    if extract:
        params_str += f", extract={extract}"

    save_log(
        "lookup",
        {
            "params": params_str,
            "inputs": {
                "question": question,
                "links": "\n".join(links),
                "prompt": prompt,
            },
            "response": content,
            "formatted_output": formatted_content,
            "usage": usage,
            "output_file": output_file,
        },
    )

    # Show summary instead of full content
    click.echo("\n✅ Lookup complete!")
    click.echo(f'📄 Output saved to: "{output_file}"')

    # Show what was found
    if extract:
        extract_type = extract.capitalize()
        click.echo(f"\n📊 {extract_type} extracted from search results")
    else:
        click.echo(f"\n📊 Legal analysis for: {question}")

    # Show links that were searched
    click.echo(f"\n🔍 Searched {len(links)} sources:")
    for i, link in enumerate(links, 1):
        click.echo(f"   {i}. {link}")

    click.echo(f'\n💡 View full analysis: open "{output_file}"')
