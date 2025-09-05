"""
Tool definitions for LLM function calling.

This module defines tools that LLMs can call to get reliable information,
particularly for date/time which models often get wrong.
"""

from datetime import datetime
import pytz


def get_tool_definitions():
    """Return tool definitions for LLM function calling."""
    return [
        {
            "type": "function",
            "function": {
                "name": "now",
                "description": "Get the current date and time in Australia/Sydney timezone. You MUST call this before answering any date-related questions.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False
                }
            }
        }
    ]


def execute_tool(tool_name, arguments=None):
    """Execute a tool and return its result."""
    if tool_name == "now":
        # Get current time in Sydney
        sydney_tz = pytz.timezone('Australia/Sydney')
        now = datetime.now(sydney_tz)
        
        return {
            "date": now.strftime("%Y-%m-%d"),
            "datetime": now.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "timezone": "Australia/Sydney",
            "year": now.year,
            "month": now.month,
            "day": now.day,
            "formatted": now.strftime("%B %d, %Y")
        }
    
    raise ValueError(f"Unknown tool: {tool_name}")


def format_tool_response(tool_name, result):
    """Format tool response for injection into conversation."""
    if tool_name == "now":
        return (
            f"Current date/time (Australia/Sydney): {result['formatted']} "
            f"({result['datetime']}). You must use this date for all calculations "
            f"and references to 'today' or 'current date'."
        )
    return str(result)