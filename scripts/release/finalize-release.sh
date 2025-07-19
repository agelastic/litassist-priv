#!/bin/bash
set -euo pipefail

# finalize-release.sh - Finalize the release with tags and push
# This script creates git tags, generates release notes, and pushes everything

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CHANGELOG="$PROJECT_ROOT/CHANGELOG.md"
RELEASE_NOTES_SCRIPT="$SCRIPT_DIR/generate-release-notes.py"

# Functions
print_usage() {
    echo "Usage: $0 <version>"
    echo "  version: The version number to release (e.g., 1.2.3)"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -d, --dry-run  Show what would be done without making changes"
    echo "  -f, --force    Force push (use with caution)"
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

verify_release_branch() {
    local version=$1
    local expected_branch="release/v${version}"
    local current_branch=$(git branch --show-current)
    
    info "Verifying release branch..."
    
    if [[ "$current_branch" != "$expected_branch" ]]; then
        error "Not on release branch. Expected: $expected_branch, Current: $current_branch"
    fi
    
    success "On correct release branch: $expected_branch"
}

check_changelog() {
    local version=$1
    
    info "Checking CHANGELOG.md..."
    
    if [[ ! -f "$CHANGELOG" ]]; then
        error "CHANGELOG.md not found"
    fi
    
    # Check if version exists in changelog
    if ! grep -q "## \[$version\]" "$CHANGELOG"; then
        error "Version $version not found in CHANGELOG.md"
    fi
    
    # Check if there are actual changes documented
    local changes=$(awk "/## \[$version\]/,/## \[/" "$CHANGELOG" | grep -E "^- " | wc -l)
    if [[ $changes -eq 0 ]]; then
        warning "No changes documented in CHANGELOG.md for version $version"
        echo "Please ensure CHANGELOG.md has been updated with release notes."
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    success "CHANGELOG.md contains entries for v$version"
}

check_uncommitted_changes() {
    info "Checking for uncommitted changes..."
    
    if ! git diff-index --quiet HEAD --; then
        git status --short
        error "There are uncommitted changes. Please commit them first."
    fi
    
    success "No uncommitted changes"
}

commit_release_changes() {
    local version=$1
    
    info "Creating release commit..."
    
    # Check if there are any changes to commit
    if git diff-index --quiet HEAD --; then
        info "No changes to commit"
        return
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "[DRY RUN] Would commit with message: Release version $version"
        git status --short
    else
        git add -A
        git commit -m "Release version $version

- Updated version in setup.py
- Updated CHANGELOG.md
- Prepared for v$version release"
        success "Created release commit"
    fi
}

create_tag() {
    local version=$1
    local tag_name="v${version}"
    
    info "Creating release tag: $tag_name"
    
    # Check if tag already exists
    if git rev-parse "$tag_name" >/dev/null 2>&1; then
        error "Tag $tag_name already exists"
    fi
    
    # Generate tag message
    local tag_message="Release version $version

$(generate_tag_message "$version")"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "[DRY RUN] Would create tag: $tag_name"
        echo "Tag message:"
        echo "$tag_message"
    else
        git tag -a "$tag_name" -m "$tag_message"
        success "Created tag: $tag_name"
    fi
}

generate_tag_message() {
    local version=$1
    
    # Extract changes from CHANGELOG for this version
    if [[ -f "$RELEASE_NOTES_SCRIPT" ]] && command -v python3 &> /dev/null; then
        python3 "$RELEASE_NOTES_SCRIPT" "$version" --format tag 2>/dev/null || echo "See CHANGELOG.md for details"
    else
        # Fallback: simple extraction
        awk "/## \[$version\]/,/## \[/" "$CHANGELOG" | tail -n +2 | head -n -1 || echo "See CHANGELOG.md for details"
    fi
}

push_branch_and_tag() {
    local version=$1
    local branch_name="release/v${version}"
    local tag_name="v${version}"
    local force_flag=""
    
    if [[ "${FORCE_PUSH:-false}" == "true" ]]; then
        force_flag="--force"
        warning "Force push enabled"
    fi
    
    info "Pushing branch and tag to origin..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "[DRY RUN] Would push branch: git push origin $branch_name $force_flag"
        echo "[DRY RUN] Would push tag: git push origin $tag_name"
    else
        # Push branch
        if git push origin "$branch_name" $force_flag; then
            success "Pushed branch: $branch_name"
        else
            error "Failed to push branch"
        fi
        
        # Push tag
        if git push origin "$tag_name"; then
            success "Pushed tag: $tag_name"
        else
            # Try to clean up - delete remote branch if tag push failed
            git push origin --delete "$branch_name" 2>/dev/null || true
            error "Failed to push tag"
        fi
    fi
}

generate_github_release_notes() {
    local version=$1
    local output_file="$PROJECT_ROOT/github_release_notes_${version}.md"
    
    info "Generating GitHub release notes..."
    
    if [[ -f "$RELEASE_NOTES_SCRIPT" ]] && command -v python3 &> /dev/null; then
        if python3 "$RELEASE_NOTES_SCRIPT" "$version" --format github > "$output_file" 2>/dev/null; then
            success "Generated GitHub release notes: $(basename "$output_file")"
        else
            warning "Failed to generate release notes with script, using fallback"
            generate_fallback_release_notes "$version" > "$output_file"
        fi
    else
        generate_fallback_release_notes "$version" > "$output_file"
    fi
}

generate_fallback_release_notes() {
    local version=$1
    
    cat << EOF
## LitAssist v$version

### What's Changed

$(awk "/## \[$version\]/,/## \[/" "$CHANGELOG" | tail -n +2 | head -n -1)

### Installation

\`\`\`bash
pip install litassist==$version
\`\`\`

### Upgrading

\`\`\`bash
pip install --upgrade litassist
\`\`\`

### Full Documentation
- [User Guide](docs/user/LitAssist_User_Guide.md)
- [Installation Guide](INSTALLATION.md)
EOF
}

display_next_steps() {
    local version=$1
    
    echo ""
    echo -e "${GREEN}Release finalized successfully!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Go to: https://github.com/YOUR-ORG/litassist/compare/main...release/v${version}"
    echo "2. Create Pull Request with title: 'Release v${version}'"
    echo "3. Add description from: github_release_notes_${version}.md"
    echo "4. Get PR reviewed and merged"
    echo "5. Go to: https://github.com/YOUR-ORG/litassist/releases/new"
    echo "6. Select tag: v${version}"
    echo "7. Title: 'LitAssist v${version}'"
    echo "8. Copy description from: github_release_notes_${version}.md"
    echo "9. Upload files from dist/ directory:"
    echo "   - litassist-${version}-py3-none-any.whl"
    echo "   - litassist-${version}.tar.gz"
    echo "10. Publish release"
    echo ""
    echo "Optional: Upload to PyPI"
    echo "  python -m twine upload dist/*"
}

# Main script
DRY_RUN=false
FORCE_PUSH=false

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
        -f|--force)
            FORCE_PUSH=true
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

echo -e "${BLUE}Finalizing release v$VERSION${NC}"
echo ""

# Change to project root
cd "$PROJECT_ROOT"

# Run finalization process
verify_release_branch "$VERSION"
check_changelog "$VERSION"
check_uncommitted_changes
commit_release_changes "$VERSION"
create_tag "$VERSION"
push_branch_and_tag "$VERSION"
generate_github_release_notes "$VERSION"

display_next_steps "$VERSION"

if [[ "$DRY_RUN" == "true" ]]; then
    echo -e "${YELLOW}This was a dry run. No changes were pushed.${NC}"
fi