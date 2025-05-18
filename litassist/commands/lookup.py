"""
Rapid case-law lookup via Google CSE + Gemini.

This module implements the 'lookup' command which searches for legal information
on AustLII via Google Custom Search, then processes the results with Google Gemini
to produce a structured legal answer citing relevant cases.
"""

import click
import re
from googleapiclient.discovery import build

from litassist.config import CONFIG
from litassist.utils import save_log, heartbeat
from litassist.llm import LLMClient


@click.command()
@click.argument("question")
@click.option("--mode", type=click.Choice(["irac", "broad"]), default="irac")
@click.option("--verify", is_flag=True, help="Enable self-critique pass")
def lookup(question, mode, verify):
    """
    Rapid case-law lookup via Google CSE + Gemini.

    Searches for legal information on AustLII via Google Custom Search,
    then processes the results with Google Gemini to produce a structured
    legal answer citing relevant cases.

    Args:
        question: The legal question to search for.
        mode: Answer format - 'irac' (Issue, Rule, Application, Conclusion) for
              structured analysis, or 'broad' for more creative exploration.
        verify: Whether to run a self-critique verification pass on the answer.

    Raises:
        click.ClickException: If there are errors with the Google CSE or LLM API calls.
    """
    # Fetch AustLII links via Google Custom Search
    try:
        service = build("customsearch", "v1", developerKey=CONFIG.g_key)
        res = (
            service.cse()
            .list(q=question, cx=CONFIG.cse_id, num=3, siteSearch="austlii.edu.au")
            .execute()
        )
    except Exception as e:
        raise click.ClickException(f"Google CSE error: {e}")
    links = [item.get("link") for item in res.get("items", [])]
    click.echo("Found links:")
    for link in links:
        click.echo(f"- {link}")

    # Prepare prompt
    prompt = f"Question: {question}\nLinks:\n" + "\n".join(links)
    # Select parameters based on mode
    if mode == "irac":
        overrides = {"temperature": 0, "top_p": 0.1, "max_tokens": 512}
    else:
        overrides = {"temperature": 0.5, "top_p": 0.9, "max_tokens": 800}

    # Call the LLM
    client = LLMClient("google/gemini-2.5-pro-preview", temperature=0, top_p=0.2)
    call_with_hb = heartbeat(30)(client.complete)
    try:
        content, usage = call_with_hb(
            [
                {"role": "system", "content": "Australian law only. Cite sources."},
                {"role": "user", "content": prompt},
            ],
            **overrides,
        )
    except Exception as e:
        raise click.ClickException(f"LLM error during lookup: {e}")
    # Citation guard: retry once if no AustLII pattern found
    if not re.search(r"austlii\.edu\.au", content):
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

    # Optional self-critique verification
    if verify:
        try:
            correction = client.verify(content)
            content = content + "\n\n--- Corrections ---\n" + correction
        except Exception as e:
            raise click.ClickException(f"Self-verification error during lookup: {e}")

    # Save audit log and output
    save_log(
        "lookup",
        {
            "params": f"mode={mode}, verify={verify}",
            "inputs": {
                "question": question,
                "links": "\n".join(links),
                "prompt": prompt,
            },
            "response": content,
            "usage": usage,
        },
    )
    click.echo(content)
