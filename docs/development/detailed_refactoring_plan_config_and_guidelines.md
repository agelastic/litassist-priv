# Detailed Refactoring Plan for Configuration and Project Guidelines

This document provides a detailed plan for refactoring the configuration management and improving adherence to the project's guidelines, as identified in the initial refactoring analysis.

## 1. Refactoring Configuration Management

**Problem:** The `COMMAND_CONFIGS` dictionary in `litassist/llm.py` is a large, hardcoded dictionary that maps commands to their LLM configurations. This makes it difficult to manage and update the configurations for different commands, and it clutters the `llm.py` file.

**Solution:** Move the command configurations to an external YAML file. This will separate the configuration from the code, making it easier to manage and update.

### Detailed Steps:

1.  **Create a `command_configs.yaml` file:**
    *   Create a new file named `command_configs.yaml` in the `litassist/` directory.
    *   Translate the existing `COMMAND_CONFIGS` Python dictionary from `litassist/llm.py` into YAML format.

    **Example `command_configs.yaml`:**
    ```yaml
    extractfacts:
        model: "anthropic/claude-sonnet-4"
        temperature: 0
        top_p: 0.15
        enforce_citations: True

    strategy:
        model: "openai/o3-pro"
        reasoning_effort: "high"
        enforce_citations: True

    # ... and so on for all other commands
    ```

2.  **Update `LLMClientFactory` to load the YAML file:**
    *   In `litassist/llm.py`, modify the `LLMClientFactory` class to read the `command_configs.yaml` file at startup.
    *   Use the `PyYAML` library (which is already a dependency) to parse the YAML file.
    *   Load the parsed configurations into a class-level variable, for example, `LLMClientFactory.COMMAND_CONFIGS`.

    ```python
    import yaml
    from pathlib import Path

    class LLMClientFactory:
        # Load configurations from YAML file
        config_path = Path(__file__).parent / "command_configs.yaml"
        with open(config_path, 'r') as f:
            COMMAND_CONFIGS = yaml.safe_load(f)

        # ... rest of the class
    ```

3.  **Remove the hardcoded `COMMAND_CONFIGS` dictionary:**
    *   Once the YAML file is being loaded correctly, delete the large, hardcoded `COMMAND_CONFIGS` dictionary from `litassist/llm.py`.

4.  **Add Error Handling:**
    *   Implement error handling in the `LLMClientFactory` to gracefully handle cases where the `command_configs.yaml` file is missing or contains invalid YAML. This could involve logging an error and falling back to a default configuration.

## 2. Improving Adherence to Project Guidelines (`GEMINI.md`)

**Problem:** The `extract_reasoning_trace` function in `litassist/utils.py` uses regular expressions to parse the LLM's output. This violates the "Minimize Local Parsing Through Better Prompt Engineering" guideline from `GEMINI.md`, which states that the LLM should be prompted to return structured data instead of relying on brittle parsing of free-form text.

**Solution:** Modify the prompts to request the reasoning trace in a structured JSON format, and update the `extract_reasoning_trace` function to parse this JSON.

### Detailed Steps:

1.  **Update the Reasoning Prompts:**
    *   Locate the prompts that are responsible for generating the reasoning trace (e.g., in `litassist/prompts/reasoning.yaml` or similar).
    *   Update these prompts to instruct the LLM to return the reasoning trace as a JSON object with a specific structure.

    **Example Prompt Modification:**
    ```yaml
    # old prompt instruction:
    # "Please provide a reasoning trace in the following format: ..."

    # new prompt instruction:
    # "Please provide a reasoning trace as a JSON object with the following keys: 'issue', 'applicable_law', 'application', 'conclusion', 'confidence', 'sources'."
    ```

2.  **Update the `extract_reasoning_trace` function:**
    *   Modify the `extract_reasoning_trace` function in `litassist/utils.py` to look for a JSON block in the LLM's response instead of using regular expressions.
    *   Use the `json` library to parse the JSON string into a Python dictionary.
    *   Create the `LegalReasoningTrace` object from the parsed dictionary.
    *   Add robust error handling to manage cases where the JSON is invalid or missing required keys. This will help in debugging prompt issues.

    **Example `extract_reasoning_trace` refactoring:**
    ```python
    import json
    import re

    def extract_reasoning_trace(content: str, command: str = None) -> Optional[LegalReasoningTrace]:
        # Look for a JSON block containing the reasoning trace
        trace_match = re.search(r"```json\s*({.*?})\s*```", content, re.DOTALL)
        if not trace_match:
            return None

        try:
            trace_data = json.loads(trace_match.group(1))
            # Validate that all required keys are present
            required_keys = ["issue", "applicable_law", "application", "conclusion", "confidence"]
            if not all(key in trace_data for key in required_keys):
                return None # Or log a warning

            return LegalReasoningTrace(
                issue=trace_data.get("issue"),
                applicable_law=trace_data.get("applicable_law"),
                application=trace_data.get("application"),
                conclusion=trace_data.get("conclusion"),
                confidence=trace_data.get("confidence"),
                sources=trace_data.get("sources", []),
                command=command,
            )
        except json.JSONDecodeError:
            return None # Or log a warning
    ```

3.  **Update the `create_reasoning_prompt` function:**
    *   The `create_reasoning_prompt` function in `litassist/utils.py` will also need to be updated to include the new JSON output instructions in the prompt it generates. This ensures that all commands that generate reasoning traces will use the new, more reliable method.

By implementing these changes, the project will have a more robust and maintainable configuration system, and it will better adhere to its own development guidelines, leading to more reliable and predictable behavior from the LLM.
