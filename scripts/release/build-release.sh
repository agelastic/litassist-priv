#!/bin/bash
set -euo pipefail

# build-release.sh - Build and test the release package
# This script builds distribution packages and runs comprehensive tests

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DIST_DIR="$PROJECT_ROOT/dist"
BUILD_DIR="$PROJECT_ROOT/build"
TEST_ENV="$PROJECT_ROOT/test_release_env"
BUILD_LOG="$PROJECT_ROOT/build_release.log"

# Functions
print_usage() {
    echo "Usage: $0 <version>"
    echo "  version: The version number to verify (e.g., 1.2.3)"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -k, --keep-env Keep test environment after completion"
    echo "  -s, --skip-tests Skip running tests"
    echo ""
    echo "Example: $0 1.2.3"
}

error() {
    echo -e "${RED}ERROR: $1${NC}" >&2
    exit 1
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

cleanup() {
    if [[ "${KEEP_ENV:-false}" == "false" ]] && [[ -d "$TEST_ENV" ]]; then
        info "Cleaning up test environment..."
        rm -rf "$TEST_ENV"
    fi
}

trap cleanup EXIT

verify_version() {
    local expected_version=$1
    local setup_py="$PROJECT_ROOT/setup.py"
    
    info "Verifying version in setup.py..."
    
    if [[ ! -f "$setup_py" ]]; then
        error "setup.py not found"
    fi
    
    local actual_version=$(grep -E "version=['\"]" "$setup_py" | sed -E "s/.*version=['\"]([^'\"]+)['\"].*/\1/")
    
    if [[ "$actual_version" != "$expected_version" ]]; then
        error "Version mismatch. Expected: $expected_version, Found: $actual_version"
    fi
    
    success "Version verified: $expected_version"
}

clean_build_artifacts() {
    info "Cleaning previous build artifacts..."
    
    rm -rf "$DIST_DIR" "$BUILD_DIR" "$PROJECT_ROOT"/*.egg-info
    rm -f "$BUILD_LOG"
    
    success "Build artifacts cleaned"
}

check_build_tools() {
    info "Checking build tools..."
    
    local missing_tools=()
    
    # Check for Python
    if ! command -v python3 &> /dev/null; then
        missing_tools+=("python3")
    fi
    
    # Check for pip
    if ! python3 -m pip --version &> /dev/null; then
        missing_tools+=("pip")
    fi
    
    # Check for build module
    if ! python3 -c "import build" &> /dev/null 2>&1; then
        warning "build module not installed. Installing..."
        python3 -m pip install --upgrade build
    fi
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        error "Missing required tools: ${missing_tools[*]}"
    fi
    
    success "All build tools available"
}

build_distribution() {
    local version=$1
    
    info "Building distribution packages..."
    
    cd "$PROJECT_ROOT"
    
    # Build both wheel and source distribution
    echo "Building wheel and source distribution..." | tee -a "$BUILD_LOG"
    if python3 -m build >> "$BUILD_LOG" 2>&1; then
        success "Distribution packages built"
    else
        error "Build failed. Check $BUILD_LOG for details"
    fi
    
    # Verify expected files exist
    local wheel_file="$DIST_DIR/litassist-${version}-py3-none-any.whl"
    local tar_file="$DIST_DIR/litassist-${version}.tar.gz"
    
    if [[ ! -f "$wheel_file" ]]; then
        error "Expected wheel file not found: $wheel_file"
    fi
    
    if [[ ! -f "$tar_file" ]]; then
        error "Expected tar.gz file not found: $tar_file"
    fi
    
    info "Built packages:"
    echo "  - $(basename "$wheel_file")"
    echo "  - $(basename "$tar_file")"
}

create_test_environment() {
    info "Creating test environment..."
    
    # Remove existing test environment
    if [[ -d "$TEST_ENV" ]]; then
        rm -rf "$TEST_ENV"
    fi
    
    # Create fresh virtual environment
    python3 -m venv "$TEST_ENV"
    
    success "Test environment created"
}

test_installation() {
    local version=$1
    local wheel_file="$DIST_DIR/litassist-${version}-py3-none-any.whl"
    
    info "Testing package installation..."
    
    # Activate virtual environment and install
    source "$TEST_ENV/bin/activate"
    
    # Upgrade pip first
    pip install --upgrade pip > /dev/null 2>&1
    
    # Install the wheel with dependencies
    if pip install "$wheel_file" > /dev/null 2>&1; then
        success "Package installed successfully"
    else
        deactivate
        error "Package installation failed"
    fi
    
    # Verify litassist command is available
    if ! command -v litassist &> /dev/null; then
        deactivate
        error "litassist command not found after installation"
    fi
    
    success "litassist command available"
    
    deactivate
}

run_smoke_tests() {
    info "Running smoke tests..."
    
    source "$TEST_ENV/bin/activate"
    
    local test_results=()
    local all_passed=true
    
    # Test 1: Version command/help
    info "Testing help command..."
    if litassist --help > /dev/null 2>&1; then
        test_results+=("✓ Help command works")
    else
        test_results+=("✗ Help command failed")
        all_passed=false
    fi
    
    # Test 2: API connectivity test
    info "Testing API connectivity..."
    if litassist test > /dev/null 2>&1; then
        test_results+=("✓ API test command works")
    else
        test_results+=("⚠ API test command failed (may need API keys)")
    fi
    
    # Test 3: Create test case_facts.txt
    local test_facts="$PROJECT_ROOT/test_case_facts.txt"
    cat > "$test_facts" << 'EOF'
Parties: John Smith (Plaintiff) v ABC Corporation (Defendant)
Background: Employment dispute regarding wrongful termination
Key Events: Termination on 2024-01-15 without notice
Legal Issues: Breach of employment contract
Evidence Available: Employment contract, termination letter
Opposing Arguments: Just cause termination
Procedural History: Initial filing 2024-02-01
Jurisdiction: State court
Applicable Law: Employment law, contract law
Client Objectives: Reinstatement or compensation
EOF
    
    # Test 4: CasePlan command (dry run)
    info "Testing caseplan command..."
    if litassist caseplan "$test_facts" > /dev/null 2>&1; then
        test_results+=("✓ CasePlan command works")
    else
        test_results+=("✗ CasePlan command failed")
        all_passed=false
    fi
    
    # Clean up test file
    rm -f "$test_facts"
    
    deactivate
    
    # Display results
    echo ""
    echo "Smoke Test Results:"
    for result in "${test_results[@]}"; do
        echo "  $result"
    done
    
    if [[ "$all_passed" == "true" ]]; then
        success "All smoke tests passed"
    else
        error "Some smoke tests failed"
    fi
}

generate_build_report() {
    local version=$1
    local report_file="$PROJECT_ROOT/build_report_${version}.txt"
    
    info "Generating build report..."
    
    cat > "$report_file" << EOF
LitAssist Build Report
Version: $version
Date: $(date)
Platform: $(uname -s)
Python: $(python3 --version)

Built Packages:
$(ls -la "$DIST_DIR")

Package Contents (wheel):
$(cd "$DIST_DIR" && unzip -l "litassist-${version}-py3-none-any.whl" | head -20)

Dependencies:
$(cd "$TEST_ENV" && source bin/activate && pip freeze | grep -v "^litassist==" && deactivate)

Build Log: $BUILD_LOG
EOF
    
    success "Build report saved to: $(basename "$report_file")"
}

# Main script
KEEP_ENV=false
SKIP_TESTS=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            print_usage
            exit 0
            ;;
        -k|--keep-env)
            KEEP_ENV=true
            shift
            ;;
        -s|--skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        -*)
            error "Unknown option: $1"
            ;;
        *)
            VERSION=$1
            shift
            ;;
    esac
done

# Check if version was provided
if [[ -z "${VERSION:-}" ]]; then
    print_usage
    error "Version number is required"
fi

echo -e "${BLUE}Building release v$VERSION${NC}"
echo ""

# Change to project root
cd "$PROJECT_ROOT"

# Run build process
verify_version "$VERSION"
check_build_tools
clean_build_artifacts
build_distribution "$VERSION"
create_test_environment
test_installation "$VERSION"

if [[ "$SKIP_TESTS" == "false" ]]; then
    run_smoke_tests
else
    warning "Skipping smoke tests"
fi

generate_build_report "$VERSION"

echo ""
echo -e "${GREEN}Build completed successfully!${NC}"
echo ""
echo "Built packages in: $DIST_DIR"
echo "  - litassist-${VERSION}-py3-none-any.whl"
echo "  - litassist-${VERSION}.tar.gz"
echo ""
echo "Next steps:"
echo "1. Review the build report: build_report_${VERSION}.txt"
echo "2. Test the package manually if needed"
echo "3. Run: ./scripts/release/finalize-release.sh $VERSION"

if [[ "$KEEP_ENV" == "true" ]]; then
    echo ""
    echo "Test environment kept at: $TEST_ENV"
    echo "To activate: source $TEST_ENV/bin/activate"
fi