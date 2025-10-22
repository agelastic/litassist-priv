# LitAssist LLM Usage Analysis and Enhancement Report

**Note**: This is a historical analysis document. Model references reflect pre-October 2025 configurations. Current models (October 2025) implement a three-tier strategy: GPT-5 Pro for critical verification (<1% hallucination), GPT-5 for fast verification (1.4% hallucination), Claude Sonnet 4.5 for legal reasoning (state-of-the-art), Grok 4 for creative strategies, and o3-pro for technical drafting.

## 1. Introduction

The purpose of this review is to analyze the current Large Language Model (LLM) usage within the LitAssist application. This report details findings from an examination of `litassist/llm.py`, assesses the existing configuration against goals of precision, creativity, and legal accuracy, and proposes recommendations for modifications to further enhance these qualities.

## 2. Current LLM Usage Overview

The `litassist/llm.py` file defines a sophisticated framework for interacting with various LLMs, primarily managed by the `LLMClientFactory` and `LLMClient` classes. The system is designed to provide a unified interface across different providers, handling parameter management and response processing.

**Key Commands and Configurations:**

*   **`extractfacts`**: Uses `anthropic/claude-sonnet-4` with low temperature (0) and top_p (0.15) for high precision. `enforce_citations` is `True`.
*   **`strategy`**: Employs `openai/o3-pro` with `reasoning_effort` set to high. System messages are merged into the user prompt. `enforce_citations` is `True`.
*   **`strategy-analysis`**: Uses `openai/o3-pro` with `reasoning_effort` set to high.
*   **`brainstorm-orthodox`**: Uses `anthropic/claude-opus-4` (temp=0.3, top_p=0.7). `enforce_citations` is `True`.
*   **`brainstorm-unorthodox`**: Leverages `x-ai/grok-3` with high temperature (0.9) and top_p (0.95) for creativity. `enforce_citations` is `True` (auto-verify Grok).
*   **`draft`**: Utilizes `openai/o3-pro` (fixed parameters, similar to `strategy`).
*   **`digest-summary` / `digest-issues`**: Use `anthropic/claude-sonnet-4` (temp=0.1, top_p=0) for summary and `anthropic/claude-opus-4` (temp=0.2, top_p=0.5) for issues.
*   **`lookup`**: Uses `google/gemini-2.5-pro` (temp=0.1, top_p=0.2). `enforce_citations` is `False`.
*   **`verify` (command)**: Uses `openai/o3-pro` (temp=0, top_p=0.2, reasoning_effort=high) for post-hoc verification. `enforce_citations` is `False`.

**Infrastructure and Philosophy:**

*   **`LLMClientFactory`**: Centralizes model and parameter configurations for each command, allowing for command-specific LLM behaviors. It also handles falling back to default configurations (`anthropic/claude-sonnet-4`, temp=0.3, top_p=0.7) if a specific command config is missing.
*   **`OpenRouter`**: Used for accessing non-OpenAI models and specialized OpenAI models like `o1-pro`/`o3-pro`. The client dynamically changes `openai.api_base` and `openai.api_key` when these models are invoked.
*   **Parameter Selection Philosophy**: The configurations demonstrate a clear intent:
    *   Low temperature/top_p for factual, deterministic tasks (e.g., `extractfacts`, `digest-summary`).
    *   Higher temperature/top_p for creative or brainstorming tasks (e.g., `brainstorm-unorthodox`).
    *   `openai/o3-pro` is reserved for tasks requiring advanced reasoning or drafting, understanding its fixed parameter limitations.
*   **Citation Verification**: A critical component is the built-in citation verification system (`validate_and_verify_citations` method within `LLMClient`). This system checks citations against the AustLII database in real-time. The `enforce_citations` flag in command configurations dictates whether strict verification is mandatory. Failed verifications can trigger retries with enhanced prompting or removal of unverified citations.
*   **Token Limits**: The system implements model-specific token limits (e.g., for Gemini, Claude, GPT-4, o3-pro, Grok) if `CONFIG.use_token_limits` is enabled. These limits are applied both for general completions and more constrained for verification tasks.
*   **Prompting**: A base prompt (`base.australian_law`) ensuring Australian legal context and English conventions is systematically added to messages.

## 3. Assessment of Current Setup

The current LLM setup in LitAssist is robust and well-structured, demonstrating a thoughtful approach to leveraging different models for their strengths.

**Precision:**

*   **Strengths**:
    *   Dedicated low-temperature settings for commands like `extractfacts` and `digest-summary` promote factual accuracy.
    *   The `verify` command using `anthropic/claude-opus-4` at temperature 0 provides a strong mechanism for post-hoc analysis.
    *   The citation verification system is a significant asset for ensuring the reliability of legal references.
    *   Use of `openai/o3-pro` for `strategy` and `draft` likely aims for high-quality, precise outputs despite its fixed higher temperature, relying on the model's inherent capabilities.
*   **Areas for Improvement**:
    *   While `o3-pro` is powerful, its fixed high temperature might occasionally introduce variability where extreme precision is needed. The control is limited to prompting and `reasoning_effort`.
    *   The effectiveness of `enforce_citations` depends on the thoroughness of the `verify_all_citations` logic and the underlying database.

**Creativity:**

*   **Strengths**:
    *   The `brainstorm-unorthodox` command explicitly uses `x-ai/grok-3` with high temperature (0.9) and top_p (0.95), which is well-suited for generating diverse and novel ideas.
    *   Commands like `brainstorm-orthodox` and `strategy-analysis` use moderate temperatures (0.3-0.2), allowing for controlled creativity.
*   **Areas for Improvement**:
    *   Could explore additional models known for creative outputs for specific brainstorming sub-tasks.
    *   The range of temperature/top_p settings for creative tasks could be further diversified or made more dynamic based on user needs or context.

**Legal Accuracy:**

*   **Strengths**:
    *   The mandatory inclusion of the `PROMPTS.get("base.australian_law")` system message ensures a baseline legal and regional context.
    *   The citation verification system (`validate_and_verify_citations`, `verify_all_citations`) is crucial for legal accuracy.
    *   The `verify` command and its variants (`verify_with_level`) provide dedicated workflows for reviewing and correcting legal text.
    *   `enforce_citations = True` for critical commands like `extractfacts` and `strategy` underscores a commitment to accuracy.
    *   Retry mechanisms for failed citation verification enhance the robustness of generated content.
*   **Areas for Improvement**:
    *   Legal accuracy is highly dependent on the LLM's training data and the comprehensiveness of the citation database. Continuous monitoring of model performance on legal tasks is essential.
    *   The definition of "legal inaccuracies" in the `verify` prompt is broad; more nuanced verification prompts could be developed for specific legal aspects.

## 4. Recommendations for Enhancement

The following recommendations aim to build upon the existing strong foundation of `litassist/llm.py`. Many of these may align with ideas potentially discussed in `docs/development/LLM_IMPROVEMENTS.md`.

**A. Enhancing Precision:**

1.  **Refine `reasoning_effort` for `o3-pro`**:
    *   **Action**: Systematically test and document the impact of different `reasoning_effort` values for `openai/o3-pro` in commands like `strategy` and `draft`.
    *   **Rationale**: Since temperature/top_p are fixed for `o3-pro`, `reasoning_effort` is a key lever for output quality and precision. Understanding its effect can optimize these commands. (Aligned with general LLM optimization principles).
2.  **Introduce a "Max-Precision" Profile for Sensitive Tasks**:
    *   **Action**: For commands like `extractfacts`, consider adding an optional profile that uses a model like `anthropic/claude-opus-4` (currently in `verify`) with temperature 0, if not already the case, or explore models specifically fine-tuned for information extraction.
    *   **Rationale**: Provides an even higher tier of precision for the most critical information extraction tasks where cost is secondary to accuracy.

**B. Boosting Creativity:**

1.  **Dynamic Temperature/Top_p Adjustment**:
    *   **Action**: For brainstorming commands, explore allowing users (or an intermediary logic) to suggest a "creativity level" that dynamically adjusts temperature and top_p within reasonable bounds.
    *   **Rationale**: Offers more fine-grained control over creative output beyond the orthodox/unorthodox split. (Aligned with providing users more control over LLM behavior).
2.  **Expand Model Palette for Brainstorming**:
    *   **Action**: Periodically evaluate and integrate new models known for strong creative or divergent thinking capabilities into `brainstorm-unorthodox` or new sub-commands.
    *   **Rationale**: Leverages the rapidly evolving LLM landscape to continuously improve creative output quality and diversity.

**C. Maximizing Legal Accuracy:**

1.  **Tiered Verification Prompts in `verify_with_level`**:
    *   **Action**: Further differentiate the prompts used in `verify_with_level` for "light", "medium", and "heavy". For "heavy", the prompt could instruct the LLM to specifically check for logical fallacies in legal arguments, outdated legal principles, or jurisdictional relevance, beyond general accuracy and Australian English.
    *   **Rationale**: Provides more targeted verification. "Heavy" verification could become a more powerful analytical tool. (This refines the existing `verify_with_level` structure).
2.  **Feedback Loop for Citation Verification**:
    *   **Action**: Implement a mechanism to log and review frequently failing or problematic citations. This data could be used to refine citation parsing logic or identify gaps in the verification database.
    *   **Rationale**: Improves the long-term reliability of the citation verification system.
3.  **Enhanced `enforce_citations` Strictness**:
    *   **Action**: For commands with `enforce_citations = True`, ensure that if citation retry fails, the operation either halts with a clear error or the problematic section is explicitly marked/removed with user notification, rather than just silently removing citations in lenient mode (current behavior suggests strict mode failure leads to retry, then potential error).
    *   **Rationale**: Increases the guarantee that outputs from `enforce_citations` commands are either fully compliant or clearly flag issues.

**D. General Recommendations:**

1.  **Configuration for `CONFIG.use_token_limits`**:
    *   **Action**: Ensure that the `CONFIG.use_token_limits` flag and the specific token limit values are easily configurable, perhaps outside of the core code, to adapt to different operational environments or new model versions.
    *   **Rationale**: Improves maintainability and adaptability of the system.
2.  **Regular Model Evaluation**:
    *   **Action**: Establish a process for regularly evaluating the performance of all used models (especially for accuracy, cost, and speed) and updating the `COMMAND_CONFIGS` as newer, better, or more cost-effective models become available via OpenRouter or direct integrations.
    *   **Rationale**: Keeps LitAssist at the forefront of LLM technology and efficiency. (Standard MLOps practice).
3.  **Parameterization of `reasoning_effort`**:
    *   **Action**: If `reasoning_effort` proves highly beneficial for `o3-pro`, consider adding it as an explicit, albeit optional, parameter in the `COMMAND_CONFIGS` for `o3-pro` based commands, rather than only as a potential override.
    *   **Rationale**: Makes this important control more visible and consistently manageable.

## 5. Conclusion

LitAssist possesses a well-engineered and flexible LLM integration framework. The current system effectively segments tasks to different models and configurations, with a strong emphasis on legal context and citation accuracy. By implementing the proposed recommendations, many of which may resonate with existing internal improvement plans (as would be detailed in `docs/development/LLM_IMPROVEMENTS.md`), LitAssist can significantly elevate its performance, delivering even greater precision in factual tasks, fostering more potent creativity in brainstorming, and ensuring the highest possible degree of legal accuracy in its outputs.
