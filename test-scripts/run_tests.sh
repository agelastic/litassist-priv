#!/bin/bash
# Simple wrapper script for running LitAssist integration tests

# Print header
echo -e "\033[1;36m=============================================\033[0m"
echo -e "\033[1;36m    LitAssist Integration Test Runner        \033[0m"
echo -e "\033[1;36m=============================================\033[0m"

# Check if python is available
if ! command -v python &> /dev/null; then
    echo -e "\033[1;31mError: Python is not installed or not in PATH\033[0m"
    exit 1
fi

# Check for required packages
MISSING=""
for pkg in openai yaml numpy; do
    # yaml package imports as 'yaml' not 'pyyaml'
    if ! python -c "import $pkg" &> /dev/null; then
        # Map package names for display
        display_name=$pkg
        if [ "$pkg" = "yaml" ]; then
            display_name="pyyaml"
        fi
        if [ -z "$MISSING" ]; then
            MISSING="$display_name"
        else
            MISSING="$MISSING, $display_name"
        fi
    fi
done

if [ ! -z "$MISSING" ]; then
    echo -e "\033[1;33mWarning: Missing required packages: $MISSING\033[0m"
    echo -e "Install with: pip install $MISSING"
    echo ""
    
    # Ask if user wants to continue anyway
    read -p "Continue anyway? (y/n): " CONT
    if [[ ! $CONT =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if config.yaml exists and has API keys
if [ ! -f "config.yaml" ]; then
    echo -e "\033[1;31mError: config.yaml file not found\033[0m"
    exit 1
fi

# Check for placeholder values in config.yaml
if grep -q "YOUR_" config.yaml; then
    echo -e "\033[1;33mWarning: config.yaml contains placeholder API keys\033[0m"
    echo "Please update config.yaml with your actual API keys before running tests."
    echo ""
    
    # Ask if user wants to continue anyway
    read -p "Continue anyway? (y/n): " CONT
    if [[ ! $CONT =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Display usage info if no arguments provided
if [ $# -eq 0 ]; then
    echo -e "\033[1mAvailable options:\033[0m"
    echo "  --all         Run all integration tests"
    echo "  --openrouter  Run OpenRouter tests only"
    echo "  --google      Run Google CSE tests only"
    echo "  --jade        Run Jade public endpoint tests only"
    echo "  --citations   Run citation fetching tests only (Google CSE / Jade)"
    echo ""
    echo -e "\033[1mUsage examples:\033[0m"
    echo "  ./run_tests.sh --all"
    echo "  ./run_tests.sh --openrouter --google"
    echo "  ./run_tests.sh --jade"
    echo "  ./run_tests.sh --citations"
    echo ""
    echo -e "\033[1mRunning all tests by default...\033[0m"
fi

# Decide what to run. Citation fetching (real Google CSE / Jade) is not covered
# by test_integrations.py, so it runs on a full run (no args or --all) or on its
# own via --citations. A targeted service filter (--openrouter/--google/--jade)
# without --all runs integrations only.
RUN_INTEGRATIONS=1
RUN_CITATIONS=0
case " $* " in
    *" --citations "*) RUN_INTEGRATIONS=0; RUN_CITATIONS=1 ;;
esac
if [ $# -eq 0 ] || [[ " $* " == *" --all "* ]]; then
    RUN_CITATIONS=1
fi

EXIT_CODE=0

# Execute integration tests with passed arguments (or all by default)
if [ $RUN_INTEGRATIONS -eq 1 ]; then
    python test-scripts/test_integrations.py "$@"
    EXIT_CODE=$?
fi

# Execute citation fetching tests (real Google CSE / Jade)
if [ $RUN_CITATIONS -eq 1 ]; then
    echo -e "\n\033[1mRunning citation fetching tests (real Google CSE / Jade)...\033[0m"
    python test-scripts/test_citation_fetching.py
    CITATION_EXIT=$?
    [ $CITATION_EXIT -ne 0 ] && EXIT_CODE=$CITATION_EXIT
fi

# Report
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "\n\033[1;32mAll tests completed successfully!\033[0m"
else
    echo -e "\n\033[1;31mSome tests failed. Check the output above for details.\033[0m"
    echo "See test_results_*.json for complete results."
fi

# Remind about test status doc
echo -e "\n\033[1mFor more information about these tests, see TESTS_STATUS.md\033[0m"

exit $EXIT_CODE
