#!/bin/bash
# Script for running LitAssist quality validation tests

# ANSI color codes
BLUE="\033[1;36m"
BOLD="\033[1m"
GREEN="\033[1;32m"
RED="\033[1;31m"
NC="\033[0m" # No Color

echo -e "${BLUE}==============================================${NC}"
echo -e "${BLUE}    LitAssist Quality Validation Tests        ${NC}"
echo -e "${BLUE}==============================================${NC}"

# Check if python is available
if ! command -v python &> /dev/null; then
    echo -e "${RED}Error: Python is not installed or not in PATH${NC}"
    exit 1
fi

# Check for required packages
MISSING=""
for pkg in openai yaml requests googleapiclient; do
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
    echo -e "${RED}Missing required packages: $MISSING${NC}"
    echo -e "Install with: pip install $MISSING"
    exit 1
fi

# Check if config.yaml exists and has API keys
if [ ! -f "config.yaml" ]; then
    echo -e "${RED}Error: config.yaml file not found${NC}"
    exit 1
fi

# Display usage info if no arguments provided
if [ $# -eq 0 ]; then
    echo -e "${BOLD}Available options:${NC}"
    echo "  --all          Run all quality tests (fast models only)"
    echo "  --openai       Test OpenAI quality"
    echo "  --openrouter   Test OpenRouter quality (all models)"
    echo "  --jade         Test Jade quality"
    echo "  --google       Test Google CSE quality"
    echo "  --slow         Test slow/expensive models (o3-pro, etc)"
    echo "  --verification Test verification system quality"
    echo ""
    echo -e "${BOLD}Running all quality tests by default...${NC}"
fi

# Execute the test with passed arguments
python test-scripts/test_quality.py "$@"

# Check exit code
EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "\n${GREEN}All quality tests passed successfully!${NC}"
else
    echo -e "\n${RED}Some quality tests failed. Check the output above for details.${NC}"
    echo "See quality_results_*.json for complete results."
fi

exit $EXIT_CODE
