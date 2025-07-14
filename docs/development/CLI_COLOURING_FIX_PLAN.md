# Plan: Consistent CLI Output Colouring in LitAssist

## Objective

Ensure all CLI output lines with status prefixes (e.g., `[INFO]`, `[SUCCESS]`, `[ANALYZING]`, etc.) are consistently coloured, regardless of whether they originate from prompt templates or are constructed in code.

---

## Step 1: Add `analyzing_message` Function

**File:** `litassist/utils.py`

Add a new colour helper function for `[ANALYZING]` messages.  
Suggested colour: Magenta (distinct from other status colours).

```python
def analyzing_message(message: str) -> str:
    """Format an analyzing message with magenta [ANALYZING] prefix."""
    return colored_message("[ANALYZING]", message, Colors.MAGENTA)
```

---

## Step 2: Create Centralized Status Message Colouring

**File:** `litassist/utils.py`

Add a function that automatically detects and colours any status-prefixed message:

```python
def colour_status_message(message: str) -> str:
    """Automatically colour messages based on their status prefix."""
    if message.startswith("[INFO]"):
        return info_message(message[6:].strip())
    elif message.startswith("[SUCCESS]"):
        return success_message(message[9:].strip())
    elif message.startswith("[WARNING]"):
        return warning_message(message[9:].strip())
    elif message.startswith("[ERROR]"):
        return error_message(message[7:].strip())
    elif message.startswith("[STATS]"):
        return stats_message(message[7:].strip())
    elif message.startswith("[ANALYZING]"):
        return analyzing_message(message[11:].strip())
    elif message.startswith("[SAVED]"):
        return saved_message(message[7:].strip())
    elif message.startswith("[VERIFYING]"):
        return verifying_message(message[11:].strip())
    else:
        return message  # No status prefix, return as-is
```

---

## Step 3: Update `brainstorm.py` Output Calls

**File:** `litassist/commands/brainstorm.py`

Replace direct `click.echo(PROMPTS.get(...))` calls with:

```python
click.echo(colour_status_message(PROMPTS.get(...)))
```

This ensures all prompt-based messages get coloured automatically.

---

## Step 4: Search and Update Other Commands

Search for similar patterns in other command files:
- `litassist/commands/strategy.py`
- `litassist/commands/draft.py`
- `litassist/commands/verify.py`
- etc.

Apply the same `colour_status_message()` wrapper where needed.

---

## Step 5: Update Prompt Templates (Optional)

**Directory:** `litassist/prompts/`

Consider refactoring prompts to return message body only (without status prefix).  
Add status prefix in code for better control.  
This is optional but provides cleaner separation of concerns.

---

## Step 6: Test the Changes

Run various commands and verify all status messages are coloured:

```bash
litassist brainstorm --side plaintiff --area civil
litassist verify some_document.txt
# etc.
```

---

## Step 7: Add Developer Documentation

**File:** Create `docs/development/CLI_OUTPUT_FORMATTING.md`

Document the pattern for status messages.  
Explain when to use direct colour helpers vs `colour_status_message()`.  
Provide examples for future contributors.

---

### Status Prefix Table

| Status Prefix   | Colour Function         | Colour Example      |
|-----------------|------------------------|---------------------|
| [INFO]          | info_message           | Blue                |
| [SUCCESS]       | success_message        | Green               |
| [WARNING]       | warning_message        | Yellow              |
| [ERROR]         | error_message          | Red                 |
| [STATS]         | stats_message          | Cyan                |
| [ANALYZING]     | analyzing_message      | Magenta/Bold Blue   |
| [SAVED]         | saved_message          | Blue                |
| [VERIFYING]     | verifying_message      | Blue                |

---

**End of Plan**
