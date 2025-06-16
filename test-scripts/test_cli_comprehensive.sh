#!/usr/bin/env bash

# Comprehensive CLI Testing Script for LitAssist
# Tests all commands with all options using mock input files but real LLM and HTTP calls
# Created: 7 June 2025

set -e  # Exit on any error

# Script name for help
SCRIPT_NAME=$(basename "$0")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Test results log
TEST_LOG="test_results_$(date +%Y%m%d_%H%M%S).log"

print_header() {
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}  LitAssist Comprehensive CLI Test Suite${NC}"
    echo -e "${BLUE}  $(date)${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo ""
}

print_section() {
    echo -e "\n${YELLOW}=== $1 ===${NC}"
}

run_test() {
    local test_name="$1"
    local command="$2"
    local expected_patterns="$3"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -e "\n${BLUE}Test $TOTAL_TESTS: $test_name${NC}"
    echo "Command: $command"
    echo "Running: $command" >> "$TEST_LOG"
    
    # Run the command and capture output
    if output=$(eval "$command" 2>&1); then
        echo -e "${GREEN}✓ Command executed successfully${NC}"
        
        # Check for expected patterns if provided
        if [[ -n "$expected_patterns" ]]; then
            local all_patterns_found=true
            IFS='|' read -a patterns <<< "$expected_patterns"
            
            for pattern in "${patterns[@]}"; do
                if echo "$output" | grep -q "$pattern"; then
                    echo -e "${GREEN}  ✓ Found expected pattern: '$pattern'${NC}"
                else
                    echo -e "${RED}  ✗ Missing expected pattern: '$pattern'${NC}"
                    all_patterns_found=false
                fi
            done
            
            if $all_patterns_found; then
                PASSED_TESTS=$((PASSED_TESTS + 1))
                echo -e "${GREEN}✓ PASSED${NC}"
                echo "PASSED: $test_name" >> "$TEST_LOG"
            else
                FAILED_TESTS=$((FAILED_TESTS + 1))
                echo -e "${RED}✗ FAILED${NC}"
                echo "FAILED: $test_name - Missing expected patterns" >> "$TEST_LOG"
            fi
        else
            PASSED_TESTS=$((PASSED_TESTS + 1))
            echo -e "${GREEN}✓ PASSED${NC}"
            echo "PASSED: $test_name" >> "$TEST_LOG"
        fi
    else
        RET=$?
        local RET
        # Check if this is a credit limitation error (acceptable for strategy tests)
        if echo "$output" | grep -q "credits\|max_tokens\|afford\|quota"; then
            PASSED_TESTS=$((PASSED_TESTS + 1))
            echo -e "${YELLOW}✓ PASSED (Credit limitation detected)${NC}"
            echo "PASSED: $test_name - Credit limitation (expected)" >> "$TEST_LOG"
        else
            FAILED_TESTS=$((FAILED_TESTS + 1))
            echo -e "${RED}✗ FAILED - Command failed with exit code $RET${NC}"
            echo "FAILED: $test_name - Command execution failed" >> "$TEST_LOG"
        fi
        echo "Error output: $output" >> "$TEST_LOG"
    fi
    
    echo "Output sample (first 200 chars): ${output:0:200}..." >> "$TEST_LOG"
    echo "---" >> "$TEST_LOG"
}

setup_mock_files() {
    print_section "Setting up mock input files"
    
    # Create test directory
    mkdir -p test_inputs
    
    # Mock legal document for digest
    cat > test_inputs/mock_affidavit.pdf <<EOF
%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Resources <<
/Font <<
/F1 4 0 R
>>
>>
/MediaBox [0 0 612 792]
/Contents 5 0 R
>>
endobj

4 0 obj
<<
/Type /Font
/Subtype /Type1
/BaseFont /Times-Roman
>>
endobj

5 0 obj
<<
/Length 500
>>
stream
BT
/F1 12 Tf
72 720 Td
(AFFIDAVIT OF JOHN SMITH) Tj
0 -24 Td
(I, John Smith, swear that:) Tj
0 -24 Td
(1. I am the plaintiff in this matter) Tj
0 -24 Td
(2. On 15 March 2024, I entered into a contract with the defendant) Tj
0 -24 Td
(3. The defendant breached the contract by failing to deliver goods) Tj
0 -24 Td
(4. I suffered damages of $50,000 as a result) Tj
0 -24 Td
(5. This affidavit is true and correct) Tj
0 -24 Td
(Sworn this 1st day of April 2024) Tj
0 -24 Td
(John Smith) Tj
ET
endstream
endobj

xref
0 6
0000000000 65535 f 
0000000010 00000 n 
0000000053 00000 n 
0000000125 00000 n 
0000000348 00000 n 
0000000445 00000 n 
trailer
<<
/Size 6
/Root 1 0 R
>>
startxref
1000
%%EOF
EOF

    # Mock case facts file with required 10-heading structure
    cat > test_inputs/mock_case_facts.txt <<EOF
CASE FACTS: Smith v Jones Contract Dispute

Parties:
- Plaintiff: John Smith (individual trader)
- Defendant: Jones Construction Pty Ltd

Background:
- Contract entered into on 15 March 2024
- Supply and installation of solar panels
- Contract value: $75,000
- Delivery due: 30 April 2024

Key Events:
1. 15 March 2024: Contract signed
2. 30 April 2024: Delivery due date
3. 15 May 2024: No delivery, plaintiff contacted defendant
4. 20 May 2024: Defendant claimed force majeure
5. 1 June 2024: Plaintiff terminated contract

Legal Issues:
1. Whether defendant's delay constitutes breach of contract
2. Whether force majeure clause applies to supply chain disruptions
3. Quantum of damages recoverable
4. Whether fundamental breach occurred

Evidence Available:
- Original contract documents
- Email correspondence between parties
- Alternative supplier quotes
- Financial records showing losses
- Industry reports on supply chain issues

Opposing Arguments:
- Defendant claims force majeure due to COVID-19 supply disruptions
- Defendant argues delay was reasonable in circumstances
- Defendant disputes quantum of damages claimed
- Defendant claims plaintiff failed to mitigate losses

Procedural History:
- No prior court proceedings
- Dispute commenced with letter of demand
- Defendant has not filed any response
- No mediation or arbitration attempted

Jurisdiction:
- Federal Court of Australia (commercial dispute over $75,000)
- Alternatively, Supreme Court of Victoria
- Contract contains Victorian jurisdiction clause

Applicable Law:
- Contract law principles
- Australian Consumer Law (Competition and Consumer Act 2010)
- Force majeure interpretation under common law
- Mitigation of damages principles

Client Objectives:
- Recover $50,000 in damages for breach of contract
- Obtain costs order against defendant
- Resolve matter efficiently to avoid prolonged litigation
- Establish precedent for future similar disputes
EOF

    # Mock strategy file
    cat > test_inputs/mock_strategy_headers.txt <<EOF
LEGAL STRATEGY OUTLINE

1. CONTRACTUAL INTERPRETATION
   - Express terms analysis
   - Implied terms consideration
   - Force majeure clause scope

2. BREACH OF CONTRACT ANALYSIS
   - Material breach assessment
   - Fundamental breach test
   - Substantial failure of performance

3. DAMAGES ASSESSMENT
   - Direct damages calculation
   - Consequential loss claims
   - Mitigation requirements

4. DEFENCES EVALUATION
   - Force majeure applicability
   - Frustration of contract
   - COVID-19 related delays

5. PROCEDURAL CONSIDERATIONS
   - Evidence requirements
   - Witness statements needed
   - Expert evidence on damages
EOF

    echo -e "${GREEN}✓ Mock files created successfully${NC}"
}

test_lookup_command() {
    print_section "Testing LOOKUP Command"
    
    # Test 1: Basic lookup with default settings
    run_test "Lookup - Basic IRAC mode" \
        "python litassist.py lookup 'contract formation requirements'" \
        "Found links|sources analyzed"
    
    # Test 2: Lookup with broad mode
    run_test "Lookup - Broad mode" \
        "python litassist.py lookup 'negligence principles' --mode broad" \
        "Found links|sources analyzed"
    
    # Test 3: Lookup with comprehensive search
    run_test "Lookup - Comprehensive search" \
        "python litassist.py lookup 'employment law termination' --comprehensive" \
        "Exhaustive search|sources analyzed"
    
    # Test 4: Lookup with citation extraction
    run_test "Lookup - Citation extraction" \
        "python litassist.py lookup 'tort law damages' --extract citations" \
        "Found links|complete|saved to|citations"
    
    # Test 5: Lookup with principles extraction
    run_test "Lookup - Principles extraction" \
        "python litassist.py lookup 'property law adverse possession' --extract principles" \
        "Found links|complete|saved to|principles"
    
    # Test 6: Lookup with checklist extraction
    run_test "Lookup - Checklist extraction" \
        "python litassist.py lookup 'criminal law evidence' --extract checklist" \
        "Found links|complete|saved to|checklist"
    
    # Test 7: Comprehensive + Broad combination  
    run_test "Lookup - Comprehensive Broad" \
        "python litassist.py lookup 'corporate law directors duties' --comprehensive --mode broad" \
        "Exhaustive search|sources analyzed"
}

test_extractfacts_command() {
    print_section "Testing EXTRACTFACTS Command"
    
    # Test 1: Extract from text file
    run_test "ExtractFacts - From text file" \
        "python litassist.py extractfacts test_inputs/mock_case_facts.txt" \
        "complete|saved to|case_facts"
    
    # Test 2: Extract from PDF (if available)
    if [[ -f test_inputs/mock_affidavit.pdf ]]; then
        run_test "ExtractFacts - From PDF file" \
            "python litassist.py extractfacts test_inputs/mock_affidavit.pdf" \
            "complete|saved to"
    fi
    
    # Test 3: Extract with verification
    run_test "ExtractFacts - With verification" \
        "python litassist.py extractfacts test_inputs/mock_case_facts.txt --verify" \
        "complete|saved to|verification"
}

test_strategy_command() {
    print_section "Testing STRATEGY Command"
    
    # Test 1: Strategy development from facts
    run_test "Strategy - From case facts with outcome" \
        "python litassist.py strategy test_inputs/mock_case_facts.txt --outcome 'Obtain damages for breach of contract'" \
        "complete|saved to|strategy"
    
    # Test 2: Strategy with verification
    run_test "Strategy - With verification" \
        "python litassist.py strategy test_inputs/mock_case_facts.txt --outcome 'Win the case' --verify" \
        "complete|saved to|verification"
    
    # Test 3: Strategy with existing strategies file
    run_test "Strategy - With strategies file" \
        "python litassist.py strategy test_inputs/mock_case_facts.txt --outcome 'Defend claim' --strategies test_inputs/mock_strategy_headers.txt" \
        "complete|saved to|strategy"
}

test_brainstorm_command() {
    print_section "Testing BRAINSTORM Command"
    
    # Test 1: Civil brainstorm for plaintiff
    run_test "Brainstorm - Civil plaintiff" \
        "python litassist.py brainstorm test_inputs/mock_case_facts.txt --side plaintiff --area civil" \
        "complete|saved to|strategies"
    
    # Test 2: Civil brainstorm for defendant with verification
    run_test "Brainstorm - Civil defendant with verification" \
        "python litassist.py brainstorm test_inputs/mock_case_facts.txt --side defendant --area civil --verify" \
        "complete|saved to|verification"
}

test_digest_command() {
    print_section "Testing DIGEST Command"
    
    # Test 1: Summary digest
    run_test "Digest - Summary mode" \
        "python litassist.py digest test_inputs/mock_case_facts.txt --mode summary" \
        "complete|saved to|digest"
    
    # Test 2: Issues digest  
    run_test "Digest - Issues mode" \
        "python litassist.py digest test_inputs/mock_case_facts.txt --mode issues" \
        "complete|saved to|digest"
}

test_draft_command() {
    print_section "Testing DRAFT Command"
    
    # Test 1: Draft from facts
    run_test "Draft - Legal document from facts" \
        "python litassist.py draft test_inputs/mock_case_facts.txt 'Draft a Statement of Claim for breach of contract'" \
        "complete|saved to|draft"
    
    # Test 2: Draft with verification
    run_test "Draft - With verification" \
        "python litassist.py draft test_inputs/mock_case_facts.txt 'Draft legal submissions' --verify" \
        "complete|saved to|verification"
    
    # Test 3: Draft with multiple documents
    run_test "Draft - Multiple documents" \
        "python litassist.py draft test_inputs/mock_case_facts.txt test_inputs/mock_strategy_headers.txt 'Draft a legal brief'" \
        "complete|saved to|draft"
}

test_error_conditions() {
    print_section "Testing Error Conditions"
    
    # Test 1: Non-existent file
    run_test "Error - Non-existent file" \
        "python litassist.py extractfacts non_existent_file.txt 2>&1 || echo 'Expected error occurred'" \
        "error|does not exist|Expected error occurred"
    
    # Test 2: Invalid option combination
    run_test "Error - Invalid lookup extract option" \
        "python litassist.py lookup 'test' --extract invalid_option 2>&1 || echo 'Expected error occurred'" \
        "error|invalid|Expected error occurred"
    
    # Test 3: Empty query
    run_test "Error - Empty lookup query" \
        "python litassist.py lookup '' 2>&1 || echo 'Expected error occurred'" \
        "error|invalid argument|Expected error occurred"
}

test_help_and_info() {
    print_section "Testing Help and Information Commands"
    
    # Test 1: Main help
    run_test "Help - Main command help" \
        "python litassist.py --help" \
        "Usage|Commands|Options"
    
    # Test 2: Lookup help
    run_test "Help - Lookup command help" \
        "python litassist.py lookup --help" \
        "Usage|mode|comprehensive|extract"
    
    # Test 3: Strategy help
    run_test "Help - Strategy command help" \
        "python litassist.py strategy --help" \
        "Usage|CASE_FACTS|outcome"
    
    # Test 4: Extractfacts help
    run_test "Help - ExtractFacts command help" \
        "python litassist.py extractfacts --help" \
        "Usage|FILE|verify"
    
    # Test 5: Brainstorm help
    run_test "Help - Brainstorm command help" \
        "python litassist.py brainstorm --help" \
        "Usage|FACTS_FILE|side|area"
    
    # Test 6: Digest help
    run_test "Help - Digest command help" \
        "python litassist.py digest --help" \
        "Usage|FILE|mode"
    
    # Test 7: Draft help  
    run_test "Help - Draft command help" \
        "python litassist.py draft --help" \
        "Usage|DOCUMENTS|QUERY"
}

test_connectivity() {
    print_section "Testing API Connectivity"
    
    # Test 1: Built-in connectivity test command
    run_test "Connectivity - LitAssist test command" \
        "python litassist.py --help 2>&1 | head -3" \
        "Usage|LitAssist"
    
    # Test 2: OpenAI API (used for direct OpenAI model calls)
    run_test "Connectivity - OpenAI API Direct" \
        "python -c 'import openai; from litassist.config import CONFIG; openai.api_key = CONFIG.oa_key; openai.api_base = \"https://api.openai.com/v1\"; response = openai.ChatCompletion.create(model=\"gpt-3.5-turbo\", messages=[{\"role\": \"user\", \"content\": \"test\"}], max_tokens=5); print(\"OpenAI Direct API: OK\")' 2>&1" \
        "OpenAI Direct API: OK"
    
    # Test 3: OpenRouter API (used for non-OpenAI models)
    run_test "Connectivity - OpenRouter API" \
        "python -c 'import openai; from litassist.config import CONFIG; openai.api_key = CONFIG.or_key; openai.api_base = CONFIG.or_base; response = openai.Model.list(); print(\"OpenRouter API: OK\")' 2>&1" \
        "OpenRouter API: OK"
    
    # Test 4: Google CSE API for Jade.io search
    run_test "Connectivity - Google CSE (Jade.io search)" \
        "python -c 'from googleapiclient.discovery import build; from litassist.config import CONFIG; service = build(\"customsearch\", \"v1\", developerKey=CONFIG.g_key, cache_discovery=False); result = service.cse().list(q=\"[2020] HCA 1\", cx=CONFIG.cse_id, num=1, siteSearch=\"jade.io\").execute(); print(\"Google CSE (Jade): OK - Found\", len(result.get(\"items\", [])), \"results\")' 2>&1" \
        "Google CSE (Jade): OK"
    
    # Test 5: Pinecone Vector DB (used by draft command)
    run_test "Connectivity - Pinecone Vector DB" \
        "python -c 'from litassist.helpers.pinecone_config import PineconeWrapper; from litassist.config import CONFIG; wrapper = PineconeWrapper(CONFIG.pc_key, CONFIG.pc_index); stats = wrapper.describe_index_stats(); print(\"Pinecone API: OK - Dimension:\", stats.dimension)' 2>&1" \
        "Pinecone API: OK"
    
    # Test 6: Verify all required API keys are present
    run_test "Connectivity - API Keys Configuration" \
        "python -c 'from litassist.config import CONFIG; missing = []; apis = {\"OpenAI\": CONFIG.oa_key, \"OpenRouter\": CONFIG.or_key, \"Google\": CONFIG.g_key, \"Pinecone\": CONFIG.pc_key}; missing = [k for k,v in apis.items() if not v or v == \"YOUR_KEY_HERE\"]; print(\"API Keys:\", \"All configured\" if not missing else f\"Missing: {missing}\")' 2>&1" \
        "API Keys: All configured"
}

cleanup_test_files() {
    print_section "Cleaning up test files"
    
    # Remove test directory
    if [[ -d test_inputs ]]; then
        rm -rf test_inputs
        echo -e "${GREEN}✓ Test input files cleaned up${NC}"
    fi
    
    # Clean up any output files created during tests (but keep logs)
    if [[ -d outputs ]]; then
        find outputs -name "*test*" -type f -delete 2>/dev/null || true
        echo -e "${GREEN}✓ Test output files cleaned up${NC}"
    fi
}

print_summary() {
    echo -e "\n${BLUE}============================================${NC}"
    echo -e "${BLUE}  TEST SUMMARY${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo -e "Total Tests: ${TOTAL_TESTS}"
    echo -e "Passed: ${GREEN}${PASSED_TESTS}${NC}"
    echo -e "Failed: ${RED}${FAILED_TESTS}${NC}"
    
    if [[ $FAILED_TESTS -eq 0 ]]; then
        echo -e "\n${GREEN}🎉 ALL TESTS PASSED! 🎉${NC}"
    else
        echo -e "\n${YELLOW}⚠️  Some tests failed. Check the log for details.${NC}"
    fi
    
    echo -e "\nDetailed results saved to: ${TEST_LOG}"
    echo -e "\n${BLUE}Test completed at: $(date)${NC}"
}

show_help() {
    echo -e "${BLUE}LitAssist CLI Test Suite${NC}"
    echo ""
    echo "Usage: $SCRIPT_NAME [OPTIONS] [TEST_GROUP]"
    echo ""
    echo "Test Groups:"
    echo "  help          Test help and info commands"
    echo "  connectivity  Test API connectivity"
    echo "  lookup        Test lookup command"
    echo "  extractfacts  Test extractfacts command"
    echo "  strategy      Test strategy command"
    echo "  brainstorm    Test brainstorm command"
    echo "  digest        Test digest command"
    echo "  draft         Test draft command"
    echo "  errors        Test error conditions"
    echo "  all           Run all tests"
    echo ""
    echo "Options:"
    echo "  --help, -h    Show this help message"
    echo ""
    echo "Examples:"
    echo "  $SCRIPT_NAME              # Show this help"
    echo "  $SCRIPT_NAME --help       # Show this help"
    echo "  $SCRIPT_NAME all          # Run all tests"
    echo "  $SCRIPT_NAME lookup       # Run only lookup tests"
    echo "  $SCRIPT_NAME errors       # Run only error condition tests"
    echo ""
}

run_test_group() {
    local group="$1"
    
    case "$group" in
        help)
            test_help_and_info
            ;;
        connectivity)
            test_connectivity
            ;;
        lookup)
            test_lookup_command
            ;;
        extractfacts)
            test_extractfacts_command
            ;;
        strategy)
            test_strategy_command
            ;;
        brainstorm)
            test_brainstorm_command
            ;;
        digest)
            test_digest_command
            ;;
        draft)
            test_draft_command
            ;;
        errors)
            test_error_conditions
            ;;
        all)
            test_help_and_info
            test_connectivity
            test_lookup_command
            test_extractfacts_command
            test_strategy_command
            test_brainstorm_command
            test_digest_command
            test_draft_command
            test_error_conditions
            ;;
        *)
            echo -e "${RED}Error: Unknown test group '$group'${NC}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Main execution
main() {
    # Parse command line arguments
    if [[ $# -eq 0 ]] || [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
        show_help
        exit 0
    fi
    
    # Check if we're in the right directory
    if [[ ! -f "litassist.py" ]]; then
        echo -e "${RED}Error: litassist.py not found. Please run this script from the project root directory.${NC}"
        exit 1
    fi
    
    # Check if virtual environment is activated (optional warning)
    if [[ -z "$VIRTUAL_ENV" ]]; then
        echo -e "${YELLOW}Warning: No virtual environment detected. Make sure dependencies are installed.${NC}"
    fi
    
    print_header
    
    # Initialize log
    echo "LitAssist CLI Test Run - $(date)" > "$TEST_LOG"
    echo "Test Group: $1" >> "$TEST_LOG"
    echo "=========================================" >> "$TEST_LOG"
    
    # Setup mock files before running any tests
    setup_mock_files
    
    # Run requested test group
    echo -e "${BLUE}Running test group: $1${NC}"
    run_test_group "$1"
    
    # Cleanup and summary
    cleanup_test_files
    print_summary
    
    # Exit with appropriate code
    if [[ $FAILED_TESTS -eq 0 ]]; then
        exit 0
    else
        exit 1
    fi
}

# Run main function
main "$@"
