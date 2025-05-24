"""
Legal strategy generation for Australian civil proceedings.

This module implements the 'strategy' command which analyzes case facts and
generates procedural options, strategic recommendations, and draft legal
documents for Australian civil litigation matters.
"""

import click
from typing import Dict, List, Any
import re
import time
import os

from litassist.config import CONFIG
from litassist.utils import save_log, heartbeat, OUTPUT_DIR
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

    missing_headings = []
    
    # Check if all required headings exist in the text (less restrictive)
    for heading in required_headings:
        # Look for heading with flexible formatting:
        # - Can have non-alphabetical chars before/after
        # - Case insensitive
        # - Must be on its own line (but can have punctuation)
        pattern = r"^\s*[^a-zA-Z]*" + re.escape(heading) + r"[^a-zA-Z]*\s*$"
        if not re.search(pattern, text, re.MULTILINE | re.IGNORECASE):
            missing_headings.append(heading)
    
    if missing_headings:
        import click
        click.echo(f"Missing required headings: {', '.join(missing_headings)}")
        click.echo("Note: Headings are now case-insensitive and can have punctuation.")
        return False

    return True


def parse_strategies_file(strategies_text: str) -> Dict[str, Any]:
    """
    Parse the strategies.txt file to extract basic counts and metadata.
    
    Since we pass the full content to the LLM anyway, we just need rough counts
    for the user display, not detailed parsing.
    
    Args:
        strategies_text: Content of the strategies.txt file.
        
    Returns:
        Dictionary containing basic strategies information.
    """
    parsed = {
        "metadata": {},
        "orthodox_count": 0,
        "unorthodox_count": 0,
        "most_likely_count": 0,
        "raw_content": strategies_text
    }
    
    # Extract metadata from header comments
    metadata_match = re.search(r"# Side: (.+)\n# Area: (.+)", strategies_text)
    if metadata_match:
        parsed["metadata"]["side"] = metadata_match.group(1).strip()
        parsed["metadata"]["area"] = metadata_match.group(2).strip()
    
    # Simple counting approach - just count numbered items in each section
    lines = strategies_text.split('\n')
    current_section = None
    
    for line in lines:
        line_upper = line.upper().strip()
        
        # Detect section headers
        if "ORTHODOX" in line_upper and "STRATEG" in line_upper and "UNORTHODOX" not in line_upper:
            current_section = "orthodox"
        elif "UNORTHODOX" in line_upper and "STRATEG" in line_upper:
            current_section = "unorthodox"
        elif "MOST LIKELY" in line_upper and "SUCCEED" in line_upper:
            current_section = "likely"
        
        # Count numbered items (handles "1.", "10.", etc.)
        if current_section and re.match(r'^\d+\.\s+', line.strip()):
            if current_section == "orthodox":
                parsed["orthodox_count"] += 1
            elif current_section == "unorthodox":
                parsed["unorthodox_count"] += 1
            elif current_section == "likely":
                parsed["most_likely_count"] += 1
    
    return parsed


def extract_legal_issues(case_text: str) -> List[str]:
    """
    Extract legal issues from the case facts text.

    Args:
        case_text: Full text of the case facts.

    Returns:
        List of identified legal issues.
    """
    # Extract the "Legal Issues" section (less restrictive)
    # Look for "Legal Issues" with flexible formatting
    match = re.search(
        r"[^a-zA-Z]*Legal\s+Issues[^a-zA-Z]*\s*\n(.*?)(?:\n\s*[^a-zA-Z]*(?:Evidence\s+Available|Opposing\s+Arguments)[^a-zA-Z]*)",
        case_text,
        re.DOTALL | re.IGNORECASE,
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
@click.option("--strategies", type=click.File("r"), help="Optional strategies file from brainstorm command")
@click.option("--verify", is_flag=True, help="Enable self-critique pass (default: auto-enabled)")
def strategy(case_facts, outcome, strategies, verify):
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
    
    # Check file size to prevent token limit issues
    if len(facts_content) > 50000:  # ~10,000 words
        raise click.ClickException(
            f"Case facts file too large ({len(facts_content):,} characters). "
            "Please provide a structured summary under 50,000 characters (~10,000 words). "
            "The strategy command expects concise, well-organized facts under 10 headings."
        )
    
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
    
    # Read and parse strategies file if provided
    strategies_content = ""
    parsed_strategies = None
    if strategies:
        strategies_content = strategies.read()
        
        # Check strategies file size
        if len(strategies_content) > 100000:  # ~20,000 words, larger limit for strategies
            raise click.ClickException(
                f"Strategies file too large ({len(strategies_content):,} characters). "
                "Please provide a file under 100,000 characters (~20,000 words)."
            )
        
        parsed_strategies = parse_strategies_file(strategies_content)
        
        # Display what was found
        click.echo(f"Using strategies from brainstorm:")
        click.echo(f"  - {parsed_strategies['orthodox_count']} orthodox strategies")
        click.echo(f"  - {parsed_strategies['unorthodox_count']} unorthodox strategies")
        click.echo(f"  - {parsed_strategies['most_likely_count']} marked as most likely to succeed")
        
        if parsed_strategies['metadata']:
            click.echo(f"  - Generated for: {parsed_strategies['metadata'].get('side', 'unknown')} in {parsed_strategies['metadata'].get('area', 'unknown')} law")
        
        # Show warning if no "most likely to succeed" found
        if parsed_strategies['most_likely_count'] == 0:
            click.echo("  - Warning: No strategies marked as 'most likely to succeed' found")
    
    # strategy always needs verification as it creates foundational strategic documents
    verify = True  # Force verification for critical accuracy

    # Generate strategic options
    system_prompt = """You are an Australian legal expert specializing in civil litigation strategy.
You must analyze case facts and produce strategic options for achieving a specific outcome."""
    
    # Enhance prompt if strategies are provided
    if parsed_strategies and parsed_strategies['most_likely_count'] > 0:
        system_prompt += f"\n\nYou have been provided with brainstormed strategies including {parsed_strategies['most_likely_count']} strategies marked as most likely to succeed. Pay particular attention to these when developing your strategic options."
    elif parsed_strategies:
        system_prompt += "\n\nYou have been provided with brainstormed strategies including orthodox and unorthodox approaches. Consider these when developing your strategic options, but focus on those most relevant to the specific outcome requested."
    
    system_prompt += """

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
"""
    
    # Add strategies content if provided
    if parsed_strategies:
        user_prompt += f"\nBRAINSTORMED STRATEGIES PROVIDED:\n"
        user_prompt += f"- {parsed_strategies['orthodox_count']} orthodox strategies\n"
        user_prompt += f"- {parsed_strategies['unorthodox_count']} unorthodox strategies\n"
        user_prompt += f"- {parsed_strategies['most_likely_count']} marked as most likely to succeed\n"
        user_prompt += f"\nFULL BRAINSTORMED CONTENT:\n{strategies_content}\n"
        user_prompt += "\nBuild upon the strategies marked as most likely to succeed, and consider how the orthodox strategies can be refined for the specific outcome requested.\n"
    
    user_prompt += "\nGenerate 3-5 distinct strategic options to achieve the desired outcome using the exact format specified."""

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

    # Save output to timestamped file
    # Create a slug from the outcome for the filename
    outcome_slug = re.sub(r'[^\w\s-]', '', outcome.lower())
    outcome_slug = re.sub(r'[-\s]+', '_', outcome_slug)
    # Limit slug length and ensure it's not empty
    outcome_slug = outcome_slug[:40].strip('_') or 'strategy'
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(OUTPUT_DIR, f"strategy_{outcome_slug}_{timestamp}.txt")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"Strategy Generation\n")
        f.write(f"Desired Outcome: {outcome}\n")
        f.write(f"Case Facts File: {case_facts.name}\n")
        if strategies:
            f.write(f"Strategies File: {strategies.name}\n")
        f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("-" * 80 + "\n\n")
        f.write(output)
    
    click.echo(f"\nOutput saved to: {output_file}")

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
            "output_file": output_file,
        },
    )

    # Display the output
    click.echo(output)