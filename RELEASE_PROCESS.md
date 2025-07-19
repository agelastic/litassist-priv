# LitAssist Release Process

## Overview
This document provides a step-by-step process for creating releases, from branch creation through GitHub release publication. Each release should follow semantic versioning (MAJOR.MINOR.PATCH).

## Pre-Release Checklist
- [ ] All tests passing (`pytest`)
- [ ] Code linted (`ruff check`)
- [ ] No uncommitted changes on main branch
- [ ] Review open issues/PRs that should be included

## Release Process

### Phase 1: Create Release Branch
```bash
# 1. Ensure you're on main and up to date
git checkout main
git pull origin main

# 2. Create release branch (replace X.Y.Z with version)
git checkout -b release/vX.Y.Z

# 3. Update version number in setup.py
# Edit setup.py and change version="X.Y.Z"
```

### Phase 2: Update Documentation

1. **Update CHANGELOG.md** (create if doesn't exist)
```markdown
# Changelog

## [X.Y.Z] - YYYY-MM-DD

### Added
- New features added in this release

### Changed
- Changes to existing functionality

### Fixed
- Bug fixes

### Removed
- Deprecated features removed
```

2. **Update README.md**
- Verify all command examples still work
- Update any version-specific information
- Ensure installation instructions are current

3. **Update User Guide**
- Review `docs/user/LitAssist_User_Guide.md` for accuracy
- Update any screenshots or examples if needed
- Verify all model configurations are current

4. **Version-specific updates**
```bash
# Update setup.py version
sed -i '' 's/version=".*"/version="X.Y.Z"/' setup.py

# Update any version references in documentation
grep -r "version" docs/ *.md
```

### Phase 3: Test Release Build

```bash
# 1. Clean previous builds
rm -rf dist/ build/ *.egg-info

# 2. Build distribution
python -m build

# 3. Test installation in fresh environment
python -m venv test_env
source test_env/bin/activate
pip install dist/litassist-X.Y.Z-py3-none-any.whl
litassist test
deactivate
rm -rf test_env

# 4. Run smoke tests on key commands
litassist test
# Create a test case_facts.txt and run:
litassist caseplan case_facts.txt
```

### Phase 4: Commit and Tag

```bash
# 1. Commit all changes
git add -A
git commit -m "Release version X.Y.Z

- Summary of major changes
- Any breaking changes noted
- Migration instructions if needed"

# 2. Create annotated tag
git tag -a vX.Y.Z -m "Release version X.Y.Z"

# 3. Push branch and tag
git push origin release/vX.Y.Z
git push origin vX.Y.Z
```

### Phase 5: Create Pull Request

1. Go to GitHub repository
2. Create PR from `release/vX.Y.Z` to `main`
3. Title: "Release vX.Y.Z"
4. Description should include:
   - Summary of changes
   - Testing performed
   - Any special deployment notes

5. Review and merge PR (squash or merge commit based on preference)

### Phase 6: Create GitHub Release

1. Go to repository's "Releases" page
2. Click "Create a new release"
3. Fill in details:
   - **Tag:** Select `vX.Y.Z`
   - **Release title:** "LitAssist vX.Y.Z"
   - **Description:** Copy from CHANGELOG.md for this version
   - **Attachments:** Upload wheel and tar.gz from `dist/`

4. Release notes template:
```markdown
## LitAssist vX.Y.Z

### Highlights
- Brief summary of major features/fixes

### What's Changed
[Copy from CHANGELOG.md]

### Installation
```bash
pip install litassist==X.Y.Z
```

### Upgrading
```bash
pip install --upgrade litassist
```

### Full Documentation
- [User Guide](docs/user/LitAssist_User_Guide.md)
- [Installation Guide](INSTALLATION.md)

### Known Issues
- Any known issues or limitations
```

### Phase 7: Post-Release

```bash
# 1. Switch back to main
git checkout main
git pull origin main

# 2. Delete local release branch
git branch -d release/vX.Y.Z

# 3. Verify PyPI release (if applicable)
# python -m twine upload dist/*

# 4. Update any external documentation/wikis
```

## Release Frequency Guidelines

- **Patch releases (X.Y.Z+1)**: Bug fixes, documentation updates
- **Minor releases (X.Y+1.0)**: New features, backwards compatible
- **Major releases (X+1.0.0)**: Breaking changes, major refactors

## Automation Opportunities

Consider creating scripts for:
1. `scripts/prepare-release.sh` - Automates version updates
2. `scripts/build-release.sh` - Builds and tests distribution
3. GitHub Actions workflow for automated releases on tag push

## Release Checklist Template

Save this checklist for each release:

```markdown
# Release Checklist for vX.Y.Z

## Pre-Release
- [ ] All tests passing
- [ ] Code linted
- [ ] Review issues/PRs for inclusion

## Documentation
- [ ] Update CHANGELOG.md
- [ ] Update version in setup.py
- [ ] Review README.md
- [ ] Review User Guide
- [ ] Update installation docs

## Build & Test
- [ ] Build distribution
- [ ] Test installation
- [ ] Run smoke tests
- [ ] Test upgrade path

## Release
- [ ] Create release branch
- [ ] Commit and tag
- [ ] Create PR
- [ ] Merge PR
- [ ] Create GitHub release
- [ ] Upload artifacts
- [ ] Verify release

## Post-Release
- [ ] Clean up branches
- [ ] Update external docs
- [ ] Announce release (if applicable)
```

This plan provides a repeatable, professional release process that ensures quality and documentation are maintained with each release.