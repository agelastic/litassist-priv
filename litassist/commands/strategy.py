"""
Legal strategy generation for Australian civil proceedings.

This module implements the 'strategy' command which analyzes case facts and
generates procedural options, strategic recommendations, and draft legal
documents for Australian civil litigation matters.
"""

import click
from typing import Dict, List, Any
import re

from litassist.config import CONFIG
from litassist.utils import save_log, heartbeat
from litassist.llm import LLMClient


def validate_case_facts_format(text: str) -> bool:
    """
    Validates that the case facts file follows the required 10-heading structure.

    Args:
        text: The content of the case facts file.

    Returns:
        True if valid, False if not valid.
    """
    required_headings = [
        "Parties",
        "Background",
        "Key Events",
        "Legal Issues",
        "Evidence Available",
        "Opposing Arguments",
        "Procedural History",
        "Jurisdiction",
        "Applicable Law",
        "Client Objectives",
    ]

    # Check if all required headings exist in the text
    for heading in required_headings:
        if not re.search(
            r"^\s*" + re.escape(heading) + r"\s*:?\s*$", text, re.MULTILINE
        ):
            return False

    return True


def extract_legal_issues(case_text: str) -> List[str]:
    """
    Extract legal issues from the case facts text.

    Args:
        case_text: Full text of the case facts.

    Returns:
        List of identified legal issues.
    """
    # Extract the "Legal Issues" section
    match = re.search(
        r"Legal Issues\s*:?\s*\n(.*?)(?:\n\s*(?:Evidence Available|Opposing Arguments)\s*:?\s*\n)",
        case_text,
        re.DOTALL,
    )

    if not match:
        return []

    # Extract individual issues (assuming one per line or bullet point)
    issues_text = match.group(1).strip()
    issues = [
        issue.strip().strip("•-*")
        for issue in re.split(r"\n+|•|\*|-", issues_text)
        if issue.strip()
    ]

    return issues


@click.command()
@click.argument("case_facts", type=click.File("r"))
@click.option("--outcome", required=True, help="Desired outcome (single sentence)")
@click.option("--verify", is_flag=True, help="Enable self-critique pass (default: auto-enabled)")
def strategy(case_facts, outcome, verify):
    """
    Generate legal strategy options and draft documents for Australian civil matters.

    Analyses the provided case facts according to the ten-heading LitAssist structure
    and produces strategic options, recommended next steps, and appropriate draft
    legal documents to achieve the desired outcome.

    Args:
        case_facts: Path to the case facts text file (structured with 10 LitAssist headings).
        outcome: A single sentence describing the desired outcome.

    Examples:
        litassist strategy case_facts.txt --outcome "Obtain interim relocation orders"
        litassist strategy case_facts.txt --outcome "Set aside default judgment"
    """
    # Read and validate case facts
    facts_content = case_facts.read()
    if not validate_case_facts_format(facts_content):
        raise click.ClickException(
            "Case facts file does not follow the required 10-heading structure."
        )

    # Extract legal issues from case facts
    legal_issues = extract_legal_issues(facts_content)
    if not legal_issues:
        raise click.ClickException(
            "Could not extract legal issues from the case facts file."
        )

    # Initialize LLM client
    llm_client = LLMClient(
        "openai/gpt-4o",
        temperature=0.2,
        top_p=0.9,
        presence_penalty=0.0,
        frequency_penalty=0.0,
    )
    llm_client.command_context = "strategy"  # Set command context
    
    # strategy always needs verification as it creates foundational strategic documents
    verify = True  # Force verification for critical accuracy

    # Generate strategic options
    system_prompt = """You are an Australian legal expert specializing in civil litigation strategy.
You must analyze case facts and produce strategic options for achieving a specific outcome.

For the strategic options section, use EXACTLY this format:

# STRATEGIC OPTIONS FOR: [OUTCOME IN CAPS]

## OPTION 1: [Title of Strategy]
* **Probability of Success**: [X]%
* **Principal Hurdles**:
  1. [Description of hurdle] — *[Case citation with pinpoint reference]*
  2. [Description of hurdle] — *[Case citation with pinpoint reference]*
* **Critical Missing Facts**:
  - [Missing fact 1]
  - [Missing fact 2]

## OPTION 2: [Title of Strategy]
[Same format as above]

[Continue for 3-5 options total]

Requirements:
- Australian law only
- Use real case citations with pinpoint references (e.g., Smith v Jones [2015] HCA 5 [27])
- Be specific about probability percentages based on precedents
- Identify genuine hurdles based on the case facts provided
- Note actual missing facts from the case materials
- Do not introduce facts not in the case materials
"""

    user_prompt = f"""CASE FACTS:
{facts_content}

DESIRED OUTCOME:
{outcome}

IDENTIFIED LEGAL ISSUES:
{', '.join(legal_issues)}

Generate 3-5 distinct strategic options to achieve the desired outcome using the exact format specified."""

    # Call LLM with heartbeat to show progress
    call_with_hb = heartbeat(CONFIG.heartbeat_interval)(llm_client.complete)
    try:
        strategy_content, usage = call_with_hb(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
    except Exception as e:
        raise click.ClickException(f"LLM strategy generation error: {e}")

    # Generate recommended next steps
    next_steps_prompt = """Based on the strategic options above, provide EXACTLY 5 immediate next steps.

Format your response as:

# RECOMMENDED NEXT STEPS

1. [Specific action with reference to relevant rules/requirements]
2. [Specific action with reference to relevant rules/requirements]
3. [Specific action with reference to relevant rules/requirements]
4. [Specific action with reference to relevant rules/requirements]
5. [Specific action with reference to relevant rules/requirements]

Focus on evidence gathering, required notices, preliminary applications, or other procedural steps required by Australian court rules. Be specific to this case."""

    try:
        next_steps_content, _ = llm_client.complete(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": strategy_content},
                {"role": "user", "content": next_steps_prompt},
            ]
        )
    except Exception as e:
        raise click.ClickException(f"LLM next steps generation error: {e}")

    # Determine appropriate document type based on outcome
    doc_type = "claim"  # Default
    if any(term in outcome.lower() for term in ["injunction", "order", "interim", "stay", "restraint"]):
        doc_type = "application"
    elif any(term in outcome.lower() for term in ["affidavit", "evidence", "witness", "sworn"]):
        doc_type = "affidavit"

    # Generate draft document
    doc_formats = {
        "claim": """Draft a STATEMENT OF CLAIM using this exact format:

# DRAFT STATEMENT OF CLAIM

## PARTIES

1. [Description of plaintiff including relevant characteristics]

2. [Description of defendant including relevant characteristics]

## FACTS RELIED UPON

1. [Chronological fact 1]

2. [Chronological fact 2]

[Continue numbering for all relevant facts]

## CAUSES OF ACTION

### FIRST CAUSE OF ACTION - [Name]
[X]. [Description of cause of action]
     *[Authority with pinpoint reference]*

### SECOND CAUSE OF ACTION - [Name]
[Y]. [Description of cause of action]
     *[Authority with pinpoint reference]*

[Continue for all causes of action]

## RELIEF SOUGHT

The plaintiff claims:

1. [Specific relief sought]

2. [Specific relief sought]

3. Interest pursuant to [relevant statutory provision]

4. Costs

5. Such further or other relief as the Court deems just""",

        "application": """Draft an ORIGINATING APPLICATION using this exact format:

# DRAFT ORIGINATING APPLICATION

**IN THE [COURT NAME]**
**[DIVISION IF APPLICABLE]**

**File No:**

**Applicant**: [Full name and description]

**Respondent**: [Full name and description]

## THE APPLICANT APPLIES FOR:

1. [Specific order sought with reference to enabling provision]

2. [Additional order if applicable]

3. Such further or other orders as the Court deems just

4. Costs

## GROUNDS OF APPLICATION:

The grounds on which the application is made are:

1. [First ground with factual basis]
   *[Authority with pinpoint reference]*

2. [Second ground with factual basis]
   *[Authority with pinpoint reference]*

[Continue for all grounds]

## AFFIDAVIT EVIDENCE:

This application is supported by the affidavit of [name] sworn/affirmed [date]""",

        "affidavit": """Draft an AFFIDAVIT OUTLINE using this exact format:

# DRAFT AFFIDAVIT

**[COURT NAME]**
**[DIVISION IF APPLICABLE]**

**File No:**

**AFFIDAVIT OF [FULL NAME]**

I, [Full Name], of [Address], [Occupation], state on oath/affirm:

1. I am [position/relationship to proceedings] and have personal knowledge of the matters deposed to herein except where otherwise stated.

2. [Factual paragraph - one fact per paragraph]

3. [Factual paragraph - one fact per paragraph]

[Continue numbering for all relevant facts]

**Exhibits:**
[List any documents to be exhibited]

**Sworn/Affirmed at:** [Location]
**Date:** [Date]
**Before me:** [Commissioner for Affidavits/Solicitor]

**Deponent's signature:** _______________"""
    }

    doc_prompt = f"""Based on the case facts and strategic options, draft a {doc_type.upper()} to achieve the outcome: "{outcome}"

{doc_formats.get(doc_type, doc_formats['claim'])}

Requirements:
- Use formal Australian legal drafting style
- Include specific facts from the case materials
- Reference actual parties and dates from the case facts
- Cite relevant authorities with pinpoint references
- Do not invent facts not in the case materials"""

    try:
        document_content, _ = llm_client.complete(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": strategy_content},
                {"role": "user", "content": doc_prompt},
            ]
        )
    except Exception as e:
        raise click.ClickException(f"LLM document generation error: {e}")

    # Combine all outputs
    output = strategy_content + "\n\n" + next_steps_content + "\n\n" + document_content
    
    # Mandatory verification for strategy (creates critical strategic guidance)
    try:
        # Use heavy verification for strategic legal advice
        correction = llm_client.verify_with_level(output, "heavy")
        if correction.strip() and not correction.lower().startswith("no corrections needed"):
            output = output + "\n\n--- Strategic Legal Review ---\n" + correction
        
        # Run citation validation
        citation_issues = llm_client.validate_citations(output)
        if citation_issues:
            output += "\n\n--- Citation Warnings ---\n" + "\n".join(citation_issues)
            
    except Exception as e:
        raise click.ClickException(f"Verification error during strategy generation: {e}")

    # Save audit log
    save_log(
        "strategy",
        {
            "inputs": {"case_facts": facts_content, "outcome": outcome},
            "params": {
                "model": "openai/gpt-4o",
                "temperature": 0.2,
                "top_p": 0.9,
                "verification": "auto-enabled (heavy)"
            },
            "usage": usage,
            "response": output,
        },
    )

    # Display the output
    click.echo(output)