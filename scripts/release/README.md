# Release Scripts

This directory contains scripts to automate the LitAssist release process.

## Overview

The release process is divided into several scripts that handle different phases:

1. **check-release-ready.sh** - Pre-flight checks before starting a release
2. **prepare-release.sh** - Create release branch and update version
3. **build-release.sh** - Build and test the distribution packages
4. **finalize-release.sh** - Create tags and push to GitHub
5. **generate-release-notes.py** - Extract release notes from CHANGELOG.md

## Quick Start

To create a new release:

```bash
# 1. Check if ready for release
./scripts/release/check-release-ready.sh

# 2. Prepare release (creates branch, updates version)
./scripts/release/prepare-release.sh 1.2.3

# 3. Edit CHANGELOG.md to add release notes

# 4. Build and test
./scripts/release/build-release.sh 1.2.3

# 5. Finalize (create tag, push)
./scripts/release/finalize-release.sh 1.2.3

# 6. Create PR and GitHub release (manual steps)
```

## Script Details

### check-release-ready.sh

Runs comprehensive checks to ensure the project is ready for release:
- Git repository status
- Required files present
- Tests passing
- Code linting clean
- Documentation complete

Options:
- `-v, --verbose` - Show detailed output
- `-q, --quiet` - Only show failures

### prepare-release.sh

Creates a release branch and updates version numbers:
- Creates branch `release/vX.Y.Z`
- Updates version in setup.py
- Creates CHANGELOG.md template entry
- Runs basic validation

Options:
- `-d, --dry-run` - Show what would be done without making changes

### build-release.sh

Builds distribution packages and runs tests:
- Builds wheel and source distributions
- Creates test virtual environment
- Installs and tests the package
- Runs smoke tests
- Generates build report

Options:
- `-k, --keep-env` - Keep test environment after completion
- `-s, --skip-tests` - Skip running tests

### finalize-release.sh

Finalizes the release with git operations:
- Creates release commit
- Creates annotated tag
- Pushes branch and tag
- Generates GitHub release notes

Options:
- `-d, --dry-run` - Show what would be done without pushing
- `-f, --force` - Force push (use with caution)

### generate-release-notes.py

Python script to extract release notes from CHANGELOG.md:
- Parses version-specific sections
- Formats for different outputs (GitHub, tag, simple)
- Adds installation instructions

Usage:
```bash
python scripts/release/generate-release-notes.py 1.2.3 --format github
```

## GitHub Actions

The `.github/workflows/release.yml` workflow automatically:
- Triggers on version tags (v*.*.*)
- Builds distribution packages
- Runs tests and linting
- Creates GitHub release with artifacts
- Optionally publishes to PyPI (requires configuration)

## Best Practices

1. Always run `check-release-ready.sh` first
2. Update CHANGELOG.md with meaningful release notes
3. Test the built package before finalizing
4. Review the PR before merging
5. Download and verify artifacts from GitHub release

## Troubleshooting

### Script won't run
Make sure scripts are executable:
```bash
chmod +x scripts/release/*.sh
```

### Version mismatch
Ensure version in setup.py matches the version you're releasing.

### Tests failing
Fix all test failures before proceeding with release.

### Can't push to GitHub
Ensure you have push permissions and correct remote configuration.

## Manual Steps

After running the scripts, manual steps are required:

1. Create Pull Request on GitHub
2. Get PR reviewed and merged
3. Create GitHub Release using the generated notes
4. Upload distribution artifacts
5. Optionally publish to PyPI

See [RELEASE_PROCESS.md](../../RELEASE_PROCESS.md) for the complete release workflow.