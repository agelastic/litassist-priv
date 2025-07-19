#!/bin/bash
set -euo pipefail

# prepare-release.sh - Prepare a new release of LitAssist
# This script creates a release branch and updates version numbers

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SETUP_PY="$PROJECT_ROOT/setup.py"
CHANGELOG="$PROJECT_ROOT/CHANGELOG.md"

# Functions
print_usage() {
    echo "Usage: $0 <version>"
    echo "  version: The version number (e.g., 1.2.3)"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -d, --dry-run  Show what would be done without making changes"
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

validate_version() {
    local version=$1
    if ! [[ $version =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        error "Invalid version format. Expected: X.Y.Z (e.g., 1.2.3)"
    fi
}

check_git_status() {
    info "Checking git status..."
    
    # Check if we're in a git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        error "Not in a git repository"
    fi
    
    # Check current branch
    local current_branch=$(git branch --show-current)
    if [[ "$current_branch" != "main" ]] && [[ "$current_branch" != "master" ]]; then
        error "Must be on main/master branch. Currently on: $current_branch"
    fi
    
    # Check for uncommitted changes
    if ! git diff-index --quiet HEAD --; then
        error "There are uncommitted changes. Please commit or stash them first."
    fi
    
    # Check if up to date with remote
    git fetch origin >/dev/null 2>&1
    local LOCAL=$(git rev-parse HEAD)
    local REMOTE=$(git rev-parse origin/$current_branch)
    
    if [[ "$LOCAL" != "$REMOTE" ]]; then
        error "Local branch is not up to date with origin. Please pull latest changes."
    fi
    
    success "Git status OK"
}

create_release_branch() {
    local version=$1
    local branch_name="release/v${version}"
    
    info "Creating release branch: $branch_name"
    
    if git show-ref --verify --quiet "refs/heads/$branch_name"; then
        error "Branch $branch_name already exists"
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "[DRY RUN] Would create branch: $branch_name"
    else
        git checkout -b "$branch_name"
        success "Created branch: $branch_name"
    fi
}

update_version() {
    local version=$1
    
    info "Updating version in setup.py to $version"
    
    if [[ ! -f "$SETUP_PY" ]]; then
        error "setup.py not found at: $SETUP_PY"
    fi
    
    # Check if version line exists
    if ! grep -q 'version=' "$SETUP_PY"; then
        error "No version= line found in setup.py"
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "[DRY RUN] Would update version in setup.py to $version"
    else
        # Update version - compatible with both macOS and Linux
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s/version=[\"'][^\"']*[\"']/version=\"$version\"/" "$SETUP_PY"
        else
            sed -i "s/version=[\"'][^\"']*[\"']/version=\"$version\"/" "$SETUP_PY"
        fi
        success "Updated version in setup.py"
    fi
}

create_changelog_template() {
    local version=$1
    local date=$(date +%Y-%m-%d)
    
    info "Creating CHANGELOG template for version $version"
    
    if [[ ! -f "$CHANGELOG" ]]; then
        info "CHANGELOG.md doesn't exist. Creating new file."
        if [[ "$DRY_RUN" == "true" ]]; then
            echo "[DRY RUN] Would create CHANGELOG.md"
        else
            cat > "$CHANGELOG" << EOF
# Changelog

All notable changes to LitAssist will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

EOF
        fi
    fi
    
    # Check if version already exists
    if grep -q "## \[$version\]" "$CHANGELOG" 2>/dev/null; then
        warning "Version $version already exists in CHANGELOG.md"
        return
    fi
    
    local new_entry="## [$version] - $date

### Added
- 

### Changed
- 

### Fixed
- 

### Removed
- 

"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "[DRY RUN] Would add the following to CHANGELOG.md:"
        echo "$new_entry"
    else
        # Add new version after the header
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            awk -v entry="$new_entry" '
                /^# Changelog/ { print; getline; print; print ""; print entry; next }
                { print }
            ' "$CHANGELOG" > "$CHANGELOG.tmp" && mv "$CHANGELOG.tmp" "$CHANGELOG"
        else
            # Linux
            awk -v entry="$new_entry" '
                /^# Changelog/ { print; getline; print; print ""; print entry; next }
                { print }
            ' "$CHANGELOG" > "$CHANGELOG.tmp" && mv "$CHANGELOG.tmp" "$CHANGELOG"
        fi
        success "Added version $version template to CHANGELOG.md"
        echo ""
        warning "Please edit CHANGELOG.md to add release notes"
    fi
}

run_checks() {
    info "Running pre-release checks..."
    
    # Check if pytest is available
    if command -v pytest &> /dev/null; then
        info "Running tests..."
        if [[ "$DRY_RUN" == "true" ]]; then
            echo "[DRY RUN] Would run: pytest"
        else
            if pytest > /dev/null 2>&1; then
                success "All tests passed"
            else
                error "Tests failed. Please fix before releasing."
            fi
        fi
    else
        warning "pytest not found. Skipping tests."
    fi
    
    # Check if ruff is available
    if command -v ruff &> /dev/null; then
        info "Running linter..."
        if [[ "$DRY_RUN" == "true" ]]; then
            echo "[DRY RUN] Would run: ruff check"
        else
            if ruff check . > /dev/null 2>&1; then
                success "Code passes linting"
            else
                error "Linting failed. Please fix before releasing."
            fi
        fi
    else
        warning "ruff not found. Skipping linting."
    fi
}

# Main script
DRY_RUN=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            print_usage
            exit 0
            ;;
        -d|--dry-run)
            DRY_RUN=true
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

# Validate version format
validate_version "$VERSION"

echo -e "${BLUE}Preparing release v$VERSION${NC}"
echo ""

# Change to project root
cd "$PROJECT_ROOT"

# Run all checks and preparations
check_git_status
run_checks
create_release_branch "$VERSION"
update_version "$VERSION"
create_changelog_template "$VERSION"

echo ""
echo -e "${GREEN}Release preparation complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Edit CHANGELOG.md to add release notes for v$VERSION"
echo "2. Review and test changes"
echo "3. Run: ./scripts/release/build-release.sh $VERSION"
echo ""

if [[ "$DRY_RUN" == "true" ]]; then
    echo -e "${YELLOW}This was a dry run. No changes were made.${NC}"
fi