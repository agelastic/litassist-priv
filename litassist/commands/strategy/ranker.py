"""
Ranking and reasoning trace functions for strategy command.

This module contains functions for creating consolidated reasoning traces
and managing strategy rankings.
"""

import time
from litassist.timing import timed
from litassist.prompts import PROMPTS


@timed
def create_consolidated_reasoning_trace(option_traces, outcome, overall_reasoning=None):
    """Create a consolidated reasoning trace from multiple strategy options."""

    # Use centralized consolidated reasoning template
    header = PROMPTS.get("reasoning.consolidated.header").format(
        outcome=outcome, timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
    )

    consolidated_content = header + "\n\n"

    # Add overall strategic reasoning if present
    if overall_reasoning:
        consolidated_content += "## OVERALL STRATEGIC ANALYSIS\n\n"

        if overall_reasoning:
            overall_trace = PROMPTS.get("reasoning.consolidated.option_trace").format(
                issue=overall_reasoning.issue,
                applicable_law=overall_reasoning.applicable_law,
                application=overall_reasoning.application,
                conclusion=overall_reasoning.conclusion,
                confidence=overall_reasoning.confidence,
                sources=", ".join(overall_reasoning.sources)
                if overall_reasoning.sources
                else "None",
            )
            consolidated_content += overall_trace + "\n\n"

    for trace_data in option_traces:
        option_num = trace_data["option_number"]
        trace = trace_data["trace"]

        option_header = PROMPTS.get("reasoning.consolidated.option_header").format(
            option_num=option_num
        )
        consolidated_content += option_header + "\n\n"

        if trace:
            option_trace = PROMPTS.get("reasoning.consolidated.option_trace").format(
                issue=trace.issue,
                applicable_law=trace.applicable_law,
                application=trace.application,
                conclusion=trace.conclusion,
                confidence=trace.confidence,
                sources=", ".join(trace.sources) if trace.sources else "None",
            )
            consolidated_content += option_trace + "\n\n"
        else:
            consolidated_content += (
                PROMPTS.get("reasoning.consolidated.no_trace") + "\n\n"
            )

    return consolidated_content
