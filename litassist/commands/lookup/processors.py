"""
Response processing and orchestration for the lookup command.

This module handles prompt building, LLM interaction, response processing,
and output generation for the lookup command.
"""

import click
import time
import os
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit
from litassist.logging import save_command_output, log_task_event
from litassist.utils.formatting import (
    success_message,
    saved_message,
    stats_message,
    info_message,
    verifying_message,
    tip_message,
)
from litassist.logging import LOG_DIR
from litassist.llm.factory import LLMClientFactory
from litassist.citation.trust import is_trusted_legal_host
from litassist.prompts import PROMPTS
from .fetchers import PendingOcrContent, _fetch_url_content


def _is_pdf_link(link: str) -> bool:
    """Return True when a link path points to a PDF."""
    return urlsplit(link).path.lower().endswith(".pdf")


class LookupProcessor:
    """Orchestrates the lookup processing workflow."""

    def __init__(self, config):
        """
        Initialise the lookup processor.

        Args:
            config: Configuration object containing lookup settings
        """
        self.config = config

    def fetch_content(self, links, all_snippets, no_fetch):
        """
        Fetch content from all provided links with appropriate handling
        for different site types and JavaScript rendering.
        
        Returns:
            List of (source_name, content) tuples
        """
        contents = []
        fetched_count = 0
        skipped_count = 0
        pdf_count = 0

        # Skip fetching if --no-fetch flag is set
        if no_fetch:
            click.echo("  [Info: Content fetching disabled by --no-fetch flag]")
            # Add search snippets to content even if not fetching URLs
            if all_snippets:
                contents.append(("Search Snippets", self._build_snippet_content(all_snippets)))
            return contents

        max_time = self.config.max_fetch_time
        start_time = time.time()

        # Fetch PDFs first so any OCR fallback can run while other sources
        # continue fetching.
        pdf_links = []
        prioritized_links = []
        other_links = []
        for link in links:
            if _is_pdf_link(link):
                pdf_links.append(link)
            elif is_trusted_legal_host(link):
                # Use parsed-hostname trust check (austlii.edu.au,
                # legislation.gov.au, jade.io, etc.) so prioritisation cannot
                # be tricked by attacker URLs that mention a trusted host in
                # query strings or paths.
                prioritized_links.append(link)
            else:
                other_links.append(link)

        # Try PDF links first, then high-value legal hosts, then others.
        ordered_links = pdf_links + prioritized_links + other_links

        # Track last fetch time per domain for rate limiting
        domain_last_fetch = {}

        click.echo(
            f"  Attempting to fetch content from {len(ordered_links)} sources..."
        )

        def record_content(link, content):
            nonlocal fetched_count, skipped_count, pdf_count
            method = (
                getattr(content, "fetch_method", "unknown") if content else "Failed"
            )
            if content:
                # Save fetched page to logs
                self._save_fetched_content(content, link)
                # Store as tuple of (link, content) for truncation manager
                contents.append((link, content))

                # Check if it's PDF content for appropriate user message
                if content.startswith("[PDF DOCUMENT EXTRACTED"):
                    click.echo(
                        f"  [OK Extracted text from PDF at {link.split('/')[2]} "
                        f"via {method}]"
                    )
                    pdf_count += 1
                elif content.startswith("[RTF DOCUMENT EXTRACTED"):
                    click.echo(
                        f"  [OK Extracted text from RTF at {link.split('/')[2]} "
                        f"via {method}]"
                    )
                elif content.startswith("[OCR DOCUMENT EXTRACTED"):
                    click.echo(
                        f"  [OK OCR extracted text from PDF at {link.split('/')[2]} "
                        f"via {method}]"
                    )
                    pdf_count += 1
                else:
                    click.echo(
                        f"  [OK Fetched {len(content)} chars from {link.split('/')[2]} via {method}]"
                    )
                fetched_count += 1
            else:
                click.echo(
                    f"  [x Failed to fetch from {link.split('/')[2]}]"
                )
                skipped_count += 1

        pending_ocr: list[tuple[str, PendingOcrContent]] = []
        with ThreadPoolExecutor(max_workers=2) as ocr_executor:
            for i, link in enumerate(ordered_links):
                # Safety check: don't run forever
                if time.time() - start_time > max_time:
                    click.echo(
                        f"  [! Time limit reached, stopping after {fetched_count} successful fetches]"
                    )
                    break

                # Skip jade.io URLs except ndfv.jade.io which we'll transform
                if "jade.io" in link.lower():
                    # Allow ndfv.jade.io URLs (will be transformed to download URLs)
                    if "ndfv.jade.io" in link.lower():
                        pass  # Continue to fetch this URL
                    else:
                        click.echo(
                            "  [-> Jade.io: Using search snippet only (site restrictions)]"
                        )
                        skipped_count += 1
                        continue

                # Domain-based rate limiting (0.5s between requests to same domain)
                domain = link.split("/")[2]
                if domain in domain_last_fetch:
                    elapsed = time.time() - domain_last_fetch[domain]
                    if elapsed < 0.5:
                        time.sleep(0.5 - elapsed)
                domain_last_fetch[domain] = time.time()

                content = _fetch_url_content(
                    link,
                    timeout=self.config.fetch_timeout,
                    ocr_executor=ocr_executor,
                )

                if isinstance(content, PendingOcrContent):
                    pending_ocr.append((link, content))
                    continue

                record_content(link, content)

            if pending_ocr:
                click.echo(
                    f"  Waiting for OCR from {len(pending_ocr)} PDF document(s)..."
                )
            for link, pending in pending_ocr:
                try:
                    content = pending.future.result()
                except Exception as e:
                    click.echo(
                        f"  x OCR failed for {link.split('/')[2]}: {str(e)[:100]}"
                    )
                    content = ""
                if content:
                    record_content(link, content)
                else:
                    click.echo(
                        f"  [x PDF skipped after OCR attempt at {link.split('/')[2]}]"
                    )
                    skipped_count += 1

        # Summary of fetch results
        if fetched_count > 0:
            click.echo(
                f"\n  Successfully fetched content from {fetched_count} source(s)"
            )
        if pdf_count > 0:
            click.echo(f"  Extracted text from {pdf_count} PDF document(s)")
        if skipped_count > 0:
            click.echo(
                f"  Skipped {skipped_count} source(s) (JavaScript, empty content, or non-extractable PDFs)"
            )

        # Add search snippets to the beginning of content if available
        if all_snippets:
            contents.insert(0, ("Search Snippets", self._build_snippet_content(all_snippets)))

        return contents

    def _save_fetched_content(self, content, link):
        """Save fetched content to log file."""
        # Sub-second suffix prevents same-second filename collisions when the
        # fetcher pulls multiple URLs from the same domain in quick
        # succession (e.g. a curl_cffi failure followed by an immediate Jina
        # fallback).
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        sub_second = f"{time.monotonic_ns() % 1_000_000_000:09d}"
        domain = link.split("/")[2].replace(".", "_")

        # Check if it's PDF content for appropriate file naming
        if content.startswith("[PDF DOCUMENT EXTRACTED"):
            log_file = os.path.join(
                LOG_DIR,
                f"pdf_extracted_{domain}_{timestamp}_{sub_second}.txt",
            )
        else:
            log_file = os.path.join(
                LOG_DIR, f"fetched_{domain}_{timestamp}_{sub_second}.html"
            )

        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"<!-- URL: {link} -->\n")
            f.write(f"<!-- Fetched: {time.strftime('%Y-%m-%d %H:%M:%S')} -->\n")
            f.write(content)

    def _build_snippet_content(self, all_snippets):
        """Build formatted snippet content for inclusion in prompt."""
        snippet_text = "=== GOOGLE CSE SEARCH SNIPPETS ===\n"
        snippet_text += PROMPTS.get("lookup.google_cse_note") + "\n"

        # Group snippets by domain for better organization
        snippet_by_domain = {}
        for snippet in all_snippets:
            lines = snippet.split("\n")
            link_line = next((line for line in lines if line.startswith("http")), "")
            domain = (
                link_line.split("/")[2] if link_line and "/" in link_line else "unknown"
            )

            if domain not in snippet_by_domain:
                snippet_by_domain[domain] = []
            snippet_by_domain[domain].append(snippet)

        # Add snippets grouped by domain
        for domain in sorted(snippet_by_domain.keys()):
            snippet_text += f"\n--- {domain} ---\n"
            snippet_text += "\n\n".join(snippet_by_domain[domain])
            snippet_text += "\n"

        snippet_text += "\n=== END OF SEARCH SNIPPETS ===\n"
        return snippet_text


    def build_prompt(
        self,
        question,
        mode,
        extract,
        comprehensive,
        context,
        guidance,
        links,
        documents,
    ):
        """Build the appropriate prompt based on available content and options.

        Args:
            documents: List of (source, content) tuples

        --context and --guidance are wrapped in their own separately-framed
        blocks (SEARCH CONTEXT and USER GUIDANCE respectively) and
        prepended independently. Context is prepended first and guidance
        second so the final layout reads `USER GUIDANCE -> SEARCH CONTEXT
        -> question/links/content` from top to bottom -- the more-specific
        narrative gets top billing.
        """
        if documents:
            # Build content text from documents
            content_sections = []
            for source, content in documents:
                if source == "Search Snippets":
                    # Snippets are already formatted
                    content_sections.append(content)
                else:
                    # Add document separators for fetched content
                    content_sections.append(
                        f"=== ACTUAL CONTENT FROM: {source} ===\n{content}\n=== END OF CONTENT FROM: {source} ==="
                    )
            content_text = "\n\n".join(content_sections)

            # Create a rich prompt with actual content
            prompt = PROMPTS.get("lookup.content_qa").format(
                question=question,
                count=len(documents),
                links=chr(10).join(links),
                content=content_text,
            )
        else:
            # Fallback to URL-only prompt
            prompt = PROMPTS.get("analysis.lookup.question_prompt").format(
                question=question, links="\n".join(links)
            )

        if context:
            prompt = PROMPTS.get("analysis.lookup.context_prompt").format(
                context=context, prompt=prompt
            )
        if guidance:
            prompt = PROMPTS.get("analysis.lookup.guidance_prompt").format(
                guidance=guidance, prompt=prompt
            )

        # Add extraction-specific instructions
        if extract:
            if extract == "citations":
                prompt += (
                    f"\n\n{PROMPTS.get('lookup.extraction_instructions.citations')}"
                )
            elif extract == "principles":
                prompt += (
                    f"\n\n{PROMPTS.get('lookup.extraction_instructions.principles')}"
                )
            elif extract == "checklist":
                prompt += (
                    f"\n\n{PROMPTS.get('lookup.extraction_instructions.checklist')}"
                )

        return prompt

    def get_llm_client(self, mode, comprehensive):
        """Get appropriately configured LLM client.

        The mode (irac | broad) selects the YAML sub-type
        (`lookup-irac` | `lookup-broad`) in
        `litassist/llm/model_configs.yaml`. All LLM parameters live there;
        this function only routes by switch.

        IMPORTANT: if a new switch is introduced that should change LLM
        parameters (a third mode, an effort tier, etc.), add the
        corresponding `lookup-<sub_type>` entry to `model_configs.yaml`
        and extend the routing logic here. Do NOT reintroduce hardcoded
        parameter overrides in this file -- the factory must resolve
        parameters from YAML so they can be tuned without code edits.

        The `comprehensive` flag still controls search depth (number of
        CSE queries, result count) in `litassist/commands/lookup/search.py`
        but no longer overrides LLM sampling parameters; the previous
        comprehensive-vs-standard tweak was collapsed into the mode
        baseline.
        """
        del comprehensive  # No LLM-parameter effect; see docstring.
        return LLMClientFactory.for_command("lookup", mode)

    def build_system_prompt(self, extract, comprehensive):
        """Build the system prompt based on mode and options."""
        base_system = PROMPTS.get("base.australian_law")

        # Special system prompt for extraction mode
        if extract:
            extraction_system = PROMPTS.get("lookup.extraction_system")
            return f"{base_system}\n\n{extraction_system}"
        elif comprehensive:
            requirements = PROMPTS.get("lookup.comprehensive_analysis.requirements")
            citation_requirements = PROMPTS.get(
                "lookup.comprehensive_analysis.citation_requirements"
            )
            output_structure = PROMPTS.get(
                "lookup.comprehensive_analysis.output_structure"
            )
            return f"""{base_system} Provide exhaustive legal analysis.

{requirements}

{citation_requirements}

{output_structure}"""
        else:
            standard_instructions = PROMPTS.get("lookup.standard_analysis.instructions")
            return f"{base_system}\n\n{standard_instructions}"

    def execute_llm_request(
        self, client, system_content, question, mode, extract, comprehensive,
        context, guidance, links, documents
    ):
        """Execute LLM request with retry logic and drop-largest truncation.

        Args:
            documents: List of (source, content) tuples that will be managed for truncation
        """
        from litassist.utils.truncation import execute_with_truncation
        from litassist.utils.formatting import warning_message
        from litassist.logging import save_log

        if documents:
            click.echo(info_message(f"Processing {len(documents)} documents for analysis..."))

        def build_prompt_fn(current_documents):
            """Build prompt with current set of documents."""
            return self.build_prompt(
                question, mode, extract, comprehensive,
                context, guidance, links, current_documents
            )
        
        def execute_fn(prompt):
            """Execute the LLM call. Errors propagate to the truncation loop."""
            try:
                log_task_event(
                    "lookup",
                    "generation",
                    "llm_call",
                    "Sending lookup prompt to LLM",
                    {"model": client.model}
                )
            except Exception:
                pass

            result = client.complete([
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt},
            ])

            try:
                log_task_event(
                    "lookup",
                    "generation",
                    "llm_response",
                    "Lookup LLM response received",
                    {"model": client.model}
                )
            except Exception:
                pass

            return result
        
        def log_drop(dropped_name, remaining_docs, attempt):
            """Log when a document is dropped."""
            save_log(
                "lookup_truncation_drop",
                {
                    "command": "lookup",
                    "dropped_source": dropped_name,
                    "remaining_sources": remaining_docs,
                    "attempt": attempt,
                },
            )
            
            try:
                log_task_event(
                    "lookup",
                    "truncation",
                    "drop",
                    f"Dropped document: {dropped_name}",
                    {"remaining_docs": len(remaining_docs), "attempt": attempt}
                )
            except Exception:
                pass
        
        # If no documents, just execute directly without truncation
        if not documents:
            prompt = self.build_prompt(
                question, mode, extract, comprehensive,
                context, guidance, links, documents
            )
            return execute_fn(prompt)
        
        # Execute with truncation management
        try:
            if documents and len(documents) > 1:
                click.echo(verifying_message("Adjusting content to fit model limits..."))
            
            return execute_with_truncation(
                client=client,
                build_prompt_fn=build_prompt_fn,
                documents=documents,
                execute_fn=execute_fn,
                log_fn=log_drop,
                system_content=system_content
            )
        except Exception as e:
            if "Failed to get LLM response after dropping all documents" in str(e):
                click.echo(
                    warning_message(
                        "Failed to get response even after dropping all documents. "
                        "The query may be too complex or the model may be unavailable."
                    )
                )
            raise

    def save_output(
        self, content, question, mode, extract, comprehensive, context, guidance, output
    ):
        """Save the lookup output with appropriate metadata.

        `Context:` and `Guidance:` are recorded as separate metadata
        entries so the audit trail preserves which path each input fed
        (CSE-side vs LLM-only), even though both end up in the same
        analysis prompt.
        """
        if extract:
            command_name = f"{output}_{extract}" if output else f"lookup_{extract}"
        else:
            command_name = output if output else "lookup"

        metadata = {"Query": question, "Mode": mode}
        if extract:
            metadata["Extract"] = extract
        if context:
            metadata["Context"] = context
        if guidance:
            metadata["Guidance"] = guidance
        if comprehensive:
            metadata["Comprehensive"] = "True"

        return save_command_output(
            command_name,
            content,
            "" if output else question,
            metadata=metadata,
        )

    def display_completion_summary(
        self, output_file, question, extract, comprehensive, context, guidance, links
    ):
        """Display completion summary and statistics."""
        # Show summary instead of full content
        click.echo(f"\n{success_message('Lookup complete!')}")
        click.echo(saved_message(f'Output saved to: "{output_file}"'))

        # Show what was found
        if extract:
            extract_type = extract.capitalize()
            msg = stats_message(f"{extract_type} extracted from search results")
            click.echo(f"\n{msg}")
        else:
            analysis_type = "Exhaustive" if comprehensive else "Standard"
            msg = stats_message(f"{analysis_type} legal analysis for: {question}")
            click.echo(f"\n{msg}")

        # Show context if provided
        if context:
            click.echo(info_message(f"Context: '{context}'"))
        if guidance:
            click.echo(info_message(f"Guidance: '{guidance}'"))

        # Show links that were searched
        if comprehensive:
            msg = verifying_message(f"Exhaustive search: {len(links)} sources analyzed")
            click.echo(f"\n{msg}")
        else:
            msg = verifying_message(f"Standard search: {len(links)} sources analyzed")
            click.echo(f"\n{msg}")

        for i, link in enumerate(links, 1):
            click.echo(f"   {i}. {link}")

        tip_msg = tip_message(f'View full analysis: open "{output_file}"')
        click.echo(f"\n{tip_msg}")
