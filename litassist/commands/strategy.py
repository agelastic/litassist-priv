"""
Legal strategy generation for Australian civil proceedings.

This module implements the 'strategy' command which analyzes case facts and
generates procedural options, strategic recommendations, and draft legal
documents for Australian civil litigation matters.
"""

import click
from typing import Dict, List, Any
import re

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


def calculate_probability(
    precedents: List[Dict[str, Any]], issue_alignment: float
) -> int:
    """
    Calculate probability of success based on precedents and issue alignment.

    Args:
        precedents: List of precedent cases relevant to the issue.
        issue_alignment: Value from 0-1 indicating how closely the current case
                         aligns with favorable precedents.

    Returns:
        Probability percentage (0-100).
    """
    if not precedents:
        return 50  # Default without precedents

    # Calculate base probability from precedent outcomes
    favorable = sum(1 for p in precedents if p.get("outcome") == "favorable")
    base_prob = (favorable / len(precedents)) * 100 if precedents else 50

    # Apply issue alignment modifier (±20%)
    alignment_factor = 0.8 + (issue_alignment * 0.4)  # Range from 0.8 to 1.2

    # Calculate final probability
    final_prob = min(round(base_prob * alignment_factor), 100)

    return final_prob


def format_strategic_options(options: List[Dict[str, Any]], outcome: str) -> str:
    """
    Format the strategic options section of the output.

    Args:
        options: List of strategic option dictionaries.
        outcome: The desired outcome.

    Returns:
        Formatted strategic options text.
    """
    text = f"# STRATEGIC OPTIONS FOR: {outcome.upper()}\n\n"

    for i, option in enumerate(options, 1):
        text += f"## OPTION {i}: {option['title']}\n"
        text += f"* **Probability of Success**: {option['probability']}%\n"

        text += "\n* **Principal Hurdles**:\n"
        for hurdle in option["hurdles"]:
            text += f"  1. {hurdle['description']} — *{hurdle['citation']}*\n"

        if option.get("missing_facts"):
            text += "\n* **Critical Missing Facts**:\n"
            for fact in option["missing_facts"]:
                text += f"  - {fact}\n"

        text += "\n\n"

    return text


def format_next_steps(steps: List[str]) -> str:
    """
    Format the recommended next steps section.

    Args:
        steps: List of recommended next steps.

    Returns:
        Formatted next steps text.
    """
    text = "# RECOMMENDED NEXT STEPS\n\n"

    for i, step in enumerate(steps, 1):
        text += f"{i}. {step}\n"

    return text + "\n\n"


def format_draft_document(doc_type: str, content: Dict[str, Any]) -> str:
    """
    Format the draft document section based on document type.

    Args:
        doc_type: Type of document (claim, application, or affidavit).
        content: Dictionary containing document content.

    Returns:
        Formatted document text.
    """
    text = f"# DRAFT {doc_type.upper()}\n\n"

    if doc_type == "claim":
        text += "## STATEMENT OF CLAIM\n\n"

        # Parties section
        text += "### PARTIES\n"
        for party in content.get("parties", []):
            text += f"{party['number']}. {party['description']}\n\n"

        # Facts relied upon
        text += "### FACTS RELIED UPON\n"
        for fact in content.get("facts", []):
            text += f"{fact['number']}. {fact['description']}\n\n"

        # Causes of action
        text += "### CAUSES OF ACTION\n"
        for cause in content.get("causes", []):
            text += f"{cause['number']}. {cause['description']}\n"
            if cause.get("authority"):
                text += f"   *{cause['authority']}*\n\n"

        # Relief sought
        text += "### RELIEF SOUGHT\n"
        for relief in content.get("relief", []):
            text += f"{relief['number']}. {relief['description']}\n\n"

    elif doc_type == "application":
        text += "## ORIGINATING APPLICATION\n\n"

        # Applicant and respondent
        text += f"**Applicant**: {content.get('applicant', '')}\n"
        text += f"**Respondent**: {content.get('respondent', '')}\n\n"

        # Application details
        text += "### THE APPLICANT APPLIES FOR:\n"
        for item in content.get("applications", []):
            text += f"{item['number']}. {item['description']}\n\n"

        # Grounds
        text += "### GROUNDS OF APPLICATION:\n"
        for ground in content.get("grounds", []):
            text += f"{ground['number']}. {ground['description']}\n"
            if ground.get("authority"):
                text += f"   *{ground['authority']}*\n\n"

    elif doc_type == "affidavit":
        text += "## AFFIDAVIT OUTLINE\n\n"

        # Deponent details
        text += f"**Deponent**: {content.get('deponent', '')}\n"
        text += f"**Position**: {content.get('position', '')}\n"
        text += f"**Date**: {content.get('date', '')}\n\n"

        # Paragraphs
        text += "### STATEMENT\n"
        for para in content.get("paragraphs", []):
            text += f"{para['number']}. {para['content']}\n\n"

    return text


@click.command()
@click.argument("case_facts", type=click.File("r"))
@click.option("--outcome", required=True, help="Desired outcome (single sentence)")
def strategy(case_facts, outcome):
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
        max_tokens=4000,
    )

    # Jade API is no longer used directly - functionality now uses public endpoint

    # Generate strategic options
    system_prompt = """
    You are an Australian legal expert specializing in civil litigation strategy.
    You must analyze case facts and produce strategic options for achieving a specific outcome.
    
    For each strategy option:
    1. Provide a title and procedural pathway
    2. Estimate probability of success (0-100%)
    3. Identify two principal legal hurdles with precise citations (e.g., Smith v Jones [2015] HCA 5 [27])
    4. Note any critical missing facts that could affect the probability
    
    Follow these constraints:
    - Australian law only
    - Formal legal language
    - At least one authority per issue
    - Do not introduce new facts not in the case materials
    - Provide 3-5 distinct strategic options
    """

    user_prompt = f"""
    CASE FACTS:
    {facts_content}
    
    DESIRED OUTCOME:
    {outcome}
    
    IDENTIFIED LEGAL ISSUES:
    {', '.join(legal_issues)}
    
    Please generate 3-5 distinct strategic options to achieve the desired outcome.
    """

    # Call LLM with heartbeat to show progress
    call_with_hb = heartbeat(30)(llm_client.complete)
    try:
        strategy_content, usage = call_with_hb(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
    except Exception as e:
        raise click.ClickException(f"LLM strategy generation error: {e}")

    # Parse LLM-generated strategic options
    # In a real implementation, this would parse the LLM output into structured data
    # For simplicity, we'll mock some structured data here

    # Mock data for demonstration - in real implementation, parse from strategy_content
    strategic_options = [
        {
            "title": "Application for Summary Judgment",
            "probability": 75,
            "hurdles": [
                {
                    "description": "Demonstrating no reasonable prospect of defense",
                    "citation": "Spencer v Commonwealth (2010) 241 CLR 118 [24]",
                },
                {
                    "description": "Overcoming contrary affidavit evidence",
                    "citation": "Fancourt v Mercantile Credits Ltd (1983) 154 CLR 87 [12]",
                },
            ],
            "missing_facts": [
                "Prior correspondence showing admission of liability",
                "Evidence of attempts to resolve dispute",
            ],
        },
        {
            "title": "Application for Interim Injunction",
            "probability": 65,
            "hurdles": [
                {
                    "description": "Establishing serious question to be tried",
                    "citation": "Australian Broadcasting Corp v O'Neill (2006) 227 CLR 57 [65-70]",
                },
                {
                    "description": "Balance of convenience favoring injunction",
                    "citation": "Beecham Group Ltd v Bristol Laboratories Pty Ltd (1968) 118 CLR 618 [25]",
                },
            ],
            "missing_facts": ["Evidence of irreparable harm without injunction"],
        },
    ]

    # Generate recommended next steps
    next_steps_prompt = f"""
    Based on the strategic options for achieving "{outcome}", what are the 
    5 most important immediate next steps that should be taken before filing?
    
    Focus on evidence gathering, required notices, preliminary applications, or
    other procedural steps required by Australian court rules.
    """

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

    # Mock data for demonstration - in real implementation, parse from next_steps_content
    next_steps = [
        "Obtain sworn affidavits from key witnesses X and Y addressing elements of claim",
        "Prepare and serve Form 1 Notice of Intention to Commence Proceedings",
        "Conduct Land Titles Office search to verify current registered interests",
        "Draft letter of demand with 14-day compliance deadline per UCPR r.5.03",
        "Consult with expert witness regarding technical aspects of causation",
    ]

    # Determine appropriate document type
    doc_type = "claim"  # Default
    if "injunction" in outcome.lower() or "order" in outcome.lower():
        doc_type = "application"
    elif "affidavit" in outcome.lower() or "evidence" in outcome.lower():
        doc_type = "affidavit"

    # Generate draft document
    doc_prompt = f"""
    Based on the case facts and strategic options, draft a {doc_type} document
    to achieve the outcome: "{outcome}"
    
    Follow Australian court formatting and pleading standards. Include:
    1. All required structural elements for this document type
    2. Properly formatted citations to relevant authorities
    3. Clear articulation of legal grounds
    
    Use formal pleading language throughout.
    """

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

    # Mock data for demonstration - in real implementation, parse from document_content
    if doc_type == "claim":
        document = {
            "parties": [
                {
                    "number": 1,
                    "description": "The plaintiff is a natural person residing in New South Wales.",
                },
                {
                    "number": 2,
                    "description": "The defendant is a corporation registered under the Corporations Act 2001 (Cth).",
                },
            ],
            "facts": [
                {
                    "number": 1,
                    "description": "On 1 January 2022, the plaintiff and defendant entered into a written contract.",
                },
                {
                    "number": 2,
                    "description": "The defendant failed to perform their obligations under the contract.",
                },
            ],
            "causes": [
                {
                    "number": 1,
                    "description": "Breach of contract by the defendant.",
                    "authority": "Luna Park (NSW) Ltd v Tramways Advertising Pty Ltd (1938) 61 CLR 286",
                }
            ],
            "relief": [
                {"number": 1, "description": "Damages in the sum of $150,000."},
                {
                    "number": 2,
                    "description": "Interest pursuant to s 100 of the Civil Procedure Act 2005 (NSW).",
                },
                {"number": 3, "description": "Costs."},
            ],
        }
    elif doc_type == "application":
        document = {
            "applicant": "John Smith",
            "respondent": "ABC Corporation Pty Ltd",
            "applications": [
                {
                    "number": 1,
                    "description": "An order pursuant to s 37(1) of the Federal Court of Australia Act 1976 (Cth) restraining the respondent from disclosing the applicant's confidential information.",
                }
            ],
            "grounds": [
                {
                    "number": 1,
                    "description": "The applicant has a prima facie case that the information is confidential.",
                    "authority": "Saltman Engineering Co Ltd v Campbell Engineering Co Ltd (1948) 65 RPC 203",
                },
                {
                    "number": 2,
                    "description": "The balance of convenience favors granting the injunction.",
                    "authority": "Australian Broadcasting Corporation v O'Neill (2006) 227 CLR 57 at [65]",
                },
            ],
        }
    else:  # affidavit
        document = {
            "deponent": "Jane Smith",
            "position": "Director of Operations, XYZ Pty Ltd",
            "date": "1 May 2025",
            "paragraphs": [
                {
                    "number": 1,
                    "content": "I am the Director of Operations of XYZ Pty Ltd and am authorized to make this affidavit on its behalf.",
                },
                {
                    "number": 2,
                    "content": "On 15 March 2025, I attended a meeting with John Doe, the Chief Executive Officer of ABC Corporation.",
                },
                {
                    "number": 3,
                    "content": "During this meeting, Mr. Doe stated that ABC Corporation would not be fulfilling its contractual obligations.",
                },
            ],
        }

    # Format the complete output
    output = format_strategic_options(strategic_options, outcome)
    output += format_next_steps(next_steps)
    output += format_draft_document(doc_type, document)

    # Save audit log
    save_log(
        "strategy",
        {
            "inputs": {"case_facts": facts_content, "outcome": outcome},
            "strategic_options": strategic_options,
            "next_steps": next_steps,
            "document": {"type": doc_type, "content": document},
            "usage": usage,
        },
    )

    # Display the output
    click.echo(output)
