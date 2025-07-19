#!/bin/bash
set -euo pipefail

# check-release-ready.sh - Comprehensive pre-release checks
# This script runs all checks to ensure the project is ready for release

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REQUIRED_FILES=(
    "setup.py"
    "README.md"
    "INSTALLATION.md"
    "LICENSE"
    "requirements.txt"
    "litassist/__init__.py"
    "litassist/cli.py"
)
REQUIRED_DOCS=(
    "docs/user/LitAssist_User_Guide.md"
    "RELEASE_PROCESS.md"
)

# Tracking variables
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNINGS=0

# Functions
print_usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -v, --verbose  Show detailed output for all checks"
    echo "  -q, --quiet    Only show failures and final summary"
    echo ""
    echo "This script runs comprehensive checks to ensure the project"
    echo "is ready for release."
}

error() {
    echo -e "${RED}ERROR: $1${NC}" >&2
}

success() {
    echo -e "${GREEN}✓ $1${NC}"
}

info() {
    echo -e "${BLUE}→ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

section() {
    echo ""
    echo -e "${CYAN}=== $1 ===${NC}"
}

check_result() {
    local check_name=$1
    local result=$2
    local details="${3:-}"
    
    ((TOTAL_CHECKS++))
    
    if [[ "$result" == "pass" ]]; then
        ((PASSED_CHECKS++))
        if [[ "$QUIET" != "true" ]]; then
            success "$check_name"
            if [[ -n "$details" ]] && [[ "$VERBOSE" == "true" ]]; then
                echo "    $details"
            fi
        fi
    elif [[ "$result" == "warn" ]]; then
        ((WARNINGS++))
        warning "$check_name"
        if [[ -n "$details" ]]; then
            echo "    $details"
        fi
    else
        ((FAILED_CHECKS++))
        error "$check_name"
        if [[ -n "$details" ]]; then
            echo "    $details"
        fi
    fi
}

# Check functions
check_git_repository() {
    section "Git Repository"
    
    # Check if it's a git repo
    if git rev-parse --git-dir > /dev/null 2>&1; then
        check_result "Git repository" "pass"
    else
        check_result "Git repository" "fail" "Not a git repository"
        return
    fi
    
    # Check branch
    local branch=$(git branch --show-current)
    if [[ "$branch" == "main" ]] || [[ "$branch" == "master" ]]; then
        check_result "On main branch" "pass" "Current branch: $branch"
    else
        check_result "On main branch" "warn" "Current branch: $branch (should be main/master)"
    fi
    
    # Check for uncommitted changes
    if git diff-index --quiet HEAD -- 2>/dev/null; then
        check_result "No uncommitted changes" "pass"
    else
        local changes=$(git status --porcelain | wc -l)
        check_result "No uncommitted changes" "fail" "$changes uncommitted changes found"
    fi
    
    # Check if up to date with remote
    git fetch origin >/dev/null 2>&1
    local LOCAL=$(git rev-parse HEAD)
    local REMOTE=$(git rev-parse origin/$branch 2>/dev/null || echo "")
    
    if [[ -z "$REMOTE" ]]; then
        check_result "Remote tracking" "warn" "No remote tracking branch"
    elif [[ "$LOCAL" == "$REMOTE" ]]; then
        check_result "Up to date with remote" "pass"
    else
        check_result "Up to date with remote" "fail" "Local and remote branches differ"
    fi
    
    # Check for untracked files
    local untracked=$(git ls-files --others --exclude-standard | wc -l)
    if [[ $untracked -eq 0 ]]; then
        check_result "No untracked files" "pass"
    else
        check_result "No untracked files" "warn" "$untracked untracked files"
    fi
}

check_required_files() {
    section "Required Files"
    
    for file in "${REQUIRED_FILES[@]}"; do
        if [[ -f "$PROJECT_ROOT/$file" ]]; then
            check_result "File: $file" "pass"
        else
            check_result "File: $file" "fail" "Missing required file"
        fi
    done
    
    for doc in "${REQUIRED_DOCS[@]}"; do
        if [[ -f "$PROJECT_ROOT/$doc" ]]; then
            check_result "Documentation: $doc" "pass"
        else
            check_result "Documentation: $doc" "warn" "Missing documentation file"
        fi
    done
}

check_python_environment() {
    section "Python Environment"
    
    # Check Python version
    if command -v python3 &> /dev/null; then
        local python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
        local major_minor=$(echo "$python_version" | cut -d'.' -f1,2)
        if [[ $(echo "$major_minor >= 3.8" | bc) -eq 1 ]]; then
            check_result "Python version" "pass" "Python $python_version"
        else
            check_result "Python version" "fail" "Python $python_version (need >= 3.8)"
        fi
    else
        check_result "Python version" "fail" "Python3 not found"
    fi
    
    # Check pip
    if python3 -m pip --version &> /dev/null; then
        check_result "pip available" "pass"
    else
        check_result "pip available" "fail" "pip not found"
    fi
    
    # Check virtual environment
    if [[ -n "${VIRTUAL_ENV:-}" ]]; then
        check_result "Virtual environment" "warn" "Currently in venv: $VIRTUAL_ENV"
    else
        check_result "Virtual environment" "pass" "Not in a virtual environment"
    fi
}

check_code_quality() {
    section "Code Quality"
    
    # Check for pytest
    if command -v pytest &> /dev/null; then
        info "Running tests..."
        if pytest tests/unit/ --quiet > /dev/null 2>&1; then
            local test_count=$(pytest tests/unit/ --collect-only -q 2>/dev/null | grep -c "<Module" || echo "0")
            check_result "Unit tests" "pass" "$test_count tests found"
        else
            check_result "Unit tests" "fail" "Tests failed"
        fi
    else
        check_result "Unit tests" "warn" "pytest not installed"
    fi
    
    # Check for ruff
    if command -v ruff &> /dev/null; then
        info "Running linter..."
        local lint_output=$(ruff check . 2>&1 || true)
        if [[ -z "$lint_output" ]]; then
            check_result "Code linting (ruff)" "pass"
        else
            local issue_count=$(echo "$lint_output" | grep -c "^" || echo "many")
            check_result "Code linting (ruff)" "fail" "$issue_count linting issues found"
        fi
    else
        check_result "Code linting" "warn" "ruff not installed"
    fi
}

check_version_consistency() {
    section "Version Consistency"
    
    # Extract version from setup.py
    if [[ -f "$PROJECT_ROOT/setup.py" ]]; then
        local setup_version=$(grep -E "version=['\"]" "$PROJECT_ROOT/setup.py" | sed -E "s/.*version=['\"]([^'\"]+)['\"].*/\1/" | head -1)
        if [[ -n "$setup_version" ]]; then
            check_result "Version in setup.py" "pass" "v$setup_version"
            
            # Check __init__.py if it exists
            if [[ -f "$PROJECT_ROOT/litassist/__init__.py" ]]; then
                if grep -q "__version__" "$PROJECT_ROOT/litassist/__init__.py"; then
                    local init_version=$(grep "__version__" "$PROJECT_ROOT/litassist/__init__.py" | sed -E "s/.*__version__.*=['\"]([^'\"]+)['\"].*/\1/" | head -1)
                    if [[ "$init_version" == "$setup_version" ]]; then
                        check_result "Version in __init__.py" "pass" "Matches setup.py"
                    else
                        check_result "Version in __init__.py" "fail" "v$init_version doesn't match setup.py"
                    fi
                else
                    check_result "Version in __init__.py" "warn" "__version__ not defined"
                fi
            fi
        else
            check_result "Version in setup.py" "fail" "Version not found"
        fi
    else
        check_result "Version in setup.py" "fail" "setup.py not found"
    fi
}

check_dependencies() {
    section "Dependencies"
    
    # Check requirements.txt
    if [[ -f "$PROJECT_ROOT/requirements.txt" ]]; then
        local req_count=$(grep -v "^#" "$PROJECT_ROOT/requirements.txt" | grep -v "^$" | wc -l)
        check_result "requirements.txt" "pass" "$req_count dependencies"
        
        # Check for potential issues
        if grep -q "file://" "$PROJECT_ROOT/requirements.txt"; then
            check_result "No local dependencies" "fail" "Found file:// dependencies"
        else
            check_result "No local dependencies" "pass"
        fi
        
        if grep -q "git+" "$PROJECT_ROOT/requirements.txt"; then
            check_result "No git dependencies" "warn" "Found git+ dependencies"
        else
            check_result "No git dependencies" "pass"
        fi
    else
        check_result "requirements.txt" "fail" "File not found"
    fi
}

check_documentation() {
    section "Documentation"
    
    # Check README
    if [[ -f "$PROJECT_ROOT/README.md" ]]; then
        local readme_size=$(wc -c < "$PROJECT_ROOT/README.md")
        if [[ $readme_size -gt 1000 ]]; then
            check_result "README.md" "pass" "$(( readme_size / 1024 ))KB"
        else
            check_result "README.md" "warn" "Very small (${readme_size} bytes)"
        fi
    else
        check_result "README.md" "fail" "Not found"
    fi
    
    # Check for broken links in markdown files
    if command -v grep &> /dev/null; then
        local broken_links=0
        while IFS= read -r file; do
            while IFS= read -r link; do
                # Extract the link target
                local target=$(echo "$link" | sed -E 's/.*\[.*\]\((.*)\).*/\1/')
                # Skip URLs and anchors
                if [[ ! "$target" =~ ^https?:// ]] && [[ ! "$target" =~ ^# ]]; then
                    # Check if file exists
                    if [[ ! -f "$PROJECT_ROOT/$target" ]]; then
                        ((broken_links++))
                        if [[ "$VERBOSE" == "true" ]]; then
                            warning "Broken link in $(basename "$file"): $target"
                        fi
                    fi
                fi
            done < <(grep -E '\[.*\]\(.*\)' "$file" 2>/dev/null || true)
        done < <(find "$PROJECT_ROOT" -name "*.md" -type f)
        
        if [[ $broken_links -eq 0 ]]; then
            check_result "No broken internal links" "pass"
        else
            check_result "No broken internal links" "warn" "$broken_links broken links found"
        fi
    fi
}

check_changelog() {
    section "Release Preparation"
    
    # Check CHANGELOG.md
    if [[ -f "$PROJECT_ROOT/CHANGELOG.md" ]]; then
        # Check for unreleased section
        if grep -q "## \[Unreleased\]" "$PROJECT_ROOT/CHANGELOG.md"; then
            check_result "CHANGELOG.md" "warn" "Contains [Unreleased] section"
        else
            check_result "CHANGELOG.md" "pass"
        fi
        
        # Check if changelog has any version entries
        local version_count=$(grep -c "## \[[0-9]" "$PROJECT_ROOT/CHANGELOG.md" || echo "0")
        if [[ $version_count -gt 0 ]]; then
            check_result "CHANGELOG versions" "pass" "$version_count versions documented"
        else
            check_result "CHANGELOG versions" "warn" "No version entries found"
        fi
    else
        check_result "CHANGELOG.md" "warn" "Not found - will need to create"
    fi
}

# Main script
VERBOSE=false
QUIET=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            print_usage
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -q|--quiet)
            QUIET=true
            shift
            ;;
        *)
            error "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Header
if [[ "$QUIET" != "true" ]]; then
    echo -e "${CYAN}LitAssist Release Readiness Check${NC}"
    echo -e "${CYAN}=================================${NC}"
fi

# Change to project root
cd "$PROJECT_ROOT"

# Run all checks
check_git_repository
check_required_files
check_python_environment
check_code_quality
check_version_consistency
check_dependencies
check_documentation
check_changelog

# Summary
echo ""
echo -e "${CYAN}=== Summary ===${NC}"
echo ""

if [[ $FAILED_CHECKS -eq 0 ]]; then
    echo -e "${GREEN}✅ All checks passed! ($PASSED_CHECKS/$TOTAL_CHECKS)${NC}"
    if [[ $WARNINGS -gt 0 ]]; then
        echo -e "${YELLOW}   $WARNINGS warnings to review${NC}"
    fi
    echo ""
    echo "The project appears ready for release."
    echo "Run: ./scripts/release/prepare-release.sh <version>"
    exit 0
else
    echo -e "${RED}❌ Some checks failed!${NC}"
    echo ""
    echo "  Passed:   $PASSED_CHECKS"
    echo "  Failed:   $FAILED_CHECKS"
    echo "  Warnings: $WARNINGS"
    echo "  Total:    $TOTAL_CHECKS"
    echo ""
    echo "Please fix the failed checks before releasing."
    exit 1
fi