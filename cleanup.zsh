#!/usr/bin/env zsh

# LitAssist Cleanup Script
# Removes temporary files, test results, logs, and other generated content
# to restore the repository to a clean state
#
# Usage: ./cleanup.zsh
#
# This script safely removes:
# • Test result files (test_results_*.json, test_results_*.log, quality_results_*.json)
# • Test input directories (test_inputs/)
# • Application logs (logs/*.md - preserves logs/README.md)
# • Python cache (__pycache__, *.pyc, .pytest_cache, etc.)
# • LaTeX auxiliary files (*.aux, *.log, *.synctex.gz, etc.)
# • OS temporary files (.DS_Store, Thumbs.db, *.tmp)
# • Generated case facts, strategies, and output files
# • Build artifacts (build/, dist/, *.egg-info/)
# • Coverage reports (.coverage, htmlcov/)
#
# It preserves all source code, configuration, and essential documentation.

set -e  # Exit on any error

# Suppress "no matches found" errors globally
setopt null_glob

echo "LitAssist Cleanup Script"
echo "=========================="
echo ""

# Function to safely remove files/directories
safe_remove() {
    local target="$1"
    local description="$2"
    
    if [[ -e "$target" ]]; then
        echo "  Removing $description..."
        rm -rf "$target"
    fi
}

# Function to count and remove files matching a pattern
remove_pattern() {
    local pattern="$1"
    local description="$2"
    
    # Use nullglob to handle no matches gracefully
    setopt local_options null_glob
    local files=(${~pattern})
    if [[ ${#files[@]} -gt 0 ]]; then
        echo "  Removing ${#files[@]} $description files..."
        rm -f ${~pattern}
    fi
}

echo "Scanning for temporary and test files..."
echo ""

# Test result files
echo "Test Results & Quality Reports:"
remove_pattern "test_results_*.json" "integration test result"
remove_pattern "test_results_*.log" "CLI test result log"
remove_pattern "quality_results_*.json" "quality test result"

# Application logs (but keep logs/README.md)
echo ""
echo "Application Logs:"
if [[ -d "logs" ]]; then
    # Count markdown log files
    local log_files=(logs/*.md)
    if [[ ${#log_files[@]} -gt 0 && -e "${log_files[1]}" ]]; then
        echo "  Removing ${#log_files[@]} application log files..."
        rm -f logs/*.md
    fi
    
    # Keep the logs directory and README.md
    if [[ ! -f "logs/README.md" ]]; then
        echo "  Recreating logs/README.md..."
        cat > logs/README.md << 'EOF'
# LitAssist Logs

This directory contains audit logs from LitAssist commands in Markdown format.

Log files are automatically generated with timestamps when commands are executed:
- `command_YYYYMMDD-HHMMSS.md` - Command audit logs with inputs, outputs, and usage statistics

These files can be safely deleted and will be regenerated as needed.
EOF
    fi
fi

# Python cache and bytecode
echo ""
echo "Python Cache & Bytecode:"
safe_remove "__pycache__" "Python cache directories"
# Find and remove all __pycache__ directories
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
remove_pattern "*.pyc" "Python bytecode"
remove_pattern "*.pyo" "Python optimized bytecode"
remove_pattern "*.py[cod]" "Python compiled"
safe_remove ".mypy_cache" "MyPy cache"
safe_remove ".pytest_cache" "Pytest cache"

# Testing directories and files
echo ""
echo "Test Files & Directories:"
safe_remove "real_test" "real test directory"
safe_remove "test_inputs" "test input directory"
remove_pattern "temp_*.py" "temporary Python scripts"
remove_pattern "debug_*.txt" "debug output files"

# LaTeX auxiliary files (from article directory)
echo ""
echo "LaTeX Auxiliary Files:"
remove_pattern "article/*.aux" "LaTeX auxiliary"
remove_pattern "article/*.log" "LaTeX log"
remove_pattern "article/*.lot" "LaTeX list of tables"
remove_pattern "article/*.lof" "LaTeX list of figures"
remove_pattern "article/*.out" "LaTeX hyperref"
remove_pattern "article/*.toc" "LaTeX table of contents"
remove_pattern "article/*.fls" "LaTeX file list"
remove_pattern "article/*.fdb_latexmk" "LaTeX latexmk database"
remove_pattern "article/*.synctex.gz" "LaTeX synctex"

# Coverage reports
echo ""
echo "Coverage Reports:"
safe_remove ".coverage" "coverage database"
safe_remove "htmlcov" "HTML coverage reports"
safe_remove "coverage.xml" "XML coverage report"
safe_remove "nosetests.xml" "nose test results"

# OS and editor temporary files
echo ""
echo "OS & Editor Files:"
safe_remove ".DS_Store" "macOS metadata"
remove_pattern "*/.DS_Store" "nested macOS metadata"
remove_pattern "Thumbs.db" "Windows thumbnails"
remove_pattern "*.tmp" "temporary files"
remove_pattern "*.log" "standalone log files"

# Generated case facts and outputs
echo ""
echo "Generated Content:"
if [[ -f "case_facts.txt" && -f "examples/case_facts.txt" ]]; then
    # Only remove if it's different from the example (indicating it was generated)
    if ! cmp -s "case_facts.txt" "examples/case_facts.txt"; then
        safe_remove "case_facts.txt" "generated case facts"
    fi
elif [[ -f "case_facts.txt" ]]; then
    # Remove if example doesn't exist (likely generated)
    safe_remove "case_facts.txt" "generated case facts"
fi

# Remove generated strategies file
safe_remove "strategies.txt" "generated strategies"

# Clean outputs directory (but keep the directory itself)
if [[ -d "outputs" ]]; then
    local output_files=(outputs/*.txt outputs/*.md outputs/*.pdf)
    if [[ ${#output_files[@]} -gt 0 && -e "${output_files[1]}" ]]; then
        echo "  Removing ${#output_files[@]} output files..."
        rm -f outputs/*.txt outputs/*.md outputs/*.pdf
    fi
fi

# Build artifacts
echo ""
echo "Build Artifacts:"
safe_remove "build" "build directory"
safe_remove "dist" "distribution directory"
remove_pattern "*.egg-info" "Python package info"
safe_remove "site" "documentation site"

echo ""
echo "Cleanup completed!"
echo ""

# Show what's left (excluding common directories and key files)
echo "Remaining files (excluding common directories):"
find . -maxdepth 1 -type f \
    ! -name ".*" \
    ! -name "*.md" \
    ! -name "*.py" \
    ! -name "*.sh" \
    ! -name "*.ini" \
    ! -name "*.txt" \
    ! -name "*.yaml" \
    ! -name "*.zsh" \
    -exec basename {} \; | sort

echo ""
echo "Repository restored to clean state!"
echo "   • All temporary and test files removed"
echo "   • Logs directory preserved with README"
echo "   • Source code and configuration untouched"
echo ""