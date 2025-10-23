# LitAssist Installation Guide

This guide provides comprehensive installation instructions for LitAssist, including multiple installation methods, configuration setup, and troubleshooting.

## Prerequisites

- **Python 3.11+**
- **Git** for cloning the repository
- **Homebrew** (macOS) or equivalent package manager
- **API Keys** for OpenAI, OpenRouter, Google CSE, and Pinecone

## Installation Methods

### Method 1: pipx Installation (Recommended)

pipx is the best way to install Python CLI applications globally while keeping them isolated.

```bash
# 1. Clone the repository
git clone https://github.com/agelastic/litassist.git
cd litassist

# 2. Install pipx (if not already installed)
brew install pipx

# 3. Install LitAssist globally
pipx install -e .

# 5. Install tiktoken for accurate token counting (required for large document handling)
pipx inject litassist tiktoken

# 4. Add pipx to PATH
pipx ensurepath

# 5. Reload shell configuration
source ~/.zshrc

# 6. Verify installation
which litassist
# Should show: /Users/USERNAME/.local/bin/litassist

litassist --help
```

**Benefits of pipx:**
- [Y] Global availability without virtual environment activation
- [Y] Isolated from system Python packages
- [Y] Easy updates with `pipx upgrade litassist`
- [Y] Clean uninstall with `pipx uninstall litassist`

### Method 2: Virtual Environment (Development)

For development work or if you prefer virtual environments:

```bash
# 1. Clone and navigate
git clone https://github.com/agelastic/litassist.git
cd litassist

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install tiktoken for accurate token counting (required for large document handling)
pip install tiktoken

# The requirements file pins OpenAI to version 0.28.1
# and includes google-api-python-client. Using these
# exact versions avoids AttributeError problems with
# newer OpenAI releases.

# 4. Install in editable mode
pip install -e .

# 5. Use locally
litassist --help
```

**Note:** With this method, you must activate the virtual environment each time you want to use LitAssist.

### Method 3: System Installation with pip

If pipx is not available:

```bash
# 1. Clone repository
git clone https://github.com/agelastic/litassist.git
cd litassist

# 2. Install system-wide (may require --break-system-packages flag)
pip3 install --user -e . --break-system-packages

# 4. Install tiktoken for accurate token counting (required for large document handling)
pip3 install --user tiktoken

# 3. Add user bin to PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# 4. Verify installation
which litassist
```

## Configuration Setup

### Required API Keys

LitAssist requires API keys for external services. Set these up in `config.yaml`:

```bash
# Navigate to LitAssist directory
cd /path/to/litassist

# Copy template to create config
cp config.yaml.template config.yaml

# Edit with your API keys
nano config.yaml
```

**Required Services:**

1. **OpenRouter** - For LLM access (Claude, Grok, etc.)
   - Get key at: https://openrouter.ai/
   - Used for: All text generation commands

2. **OpenAI** - For embeddings only
   - Get key at: https://openai.com/api/
   - Used for: Document vectorization

3. **Google Custom Search** - For case law lookup
   - Get API key: https://developers.google.com/custom-search/v1/overview
   - Create CSE: https://cse.google.com/
   - Used for: `lookup` command

4. **Pinecone** - For vector storage
   - Get key at: https://www.pinecone.io/
   - Used for: Document storage and retrieval

### Configuration Location

For global usage after pipx installation, copy your config to a standard location:

```bash
# Create config directory
mkdir -p ~/.config/litassist

# Copy your configured config.yaml
cp config.yaml ~/.config/litassist/

# Now you can use litassist from any directory!
```

LitAssist looks for config.yaml in these locations (in order):
1. `~/.config/litassist/config.yaml` (recommended for global install)
2. `~/.litassist/config.yaml` (alternative location)
3. `/etc/litassist/config.yaml` (system-wide)
4. Development directory (for editable installs)

### Verify Configuration

```bash
# Check config location
python3 -c "from litassist.config import CONFIG; print('Config location:', CONFIG.config_path)"

# Should output: Config location: /path/to/litassist/config.yaml
```

## Large Document Handling and Token Counting

**New July 2025:**  
- LitAssist now uses chunk-based processing for large documents (50k token chunks) and tiktoken for accurate token counting.
- If a research file exceeds 128k tokens, a warning is displayed and processing may be truncated or chunked.
- CLI output now includes file, word, and token counts for research/context files.
- This ensures robust handling of large legal documents and prevents API token limit errors.

## Usage Examples

Once installed, LitAssist works from any directory:

```bash
# Document analysis
cd ~/legal-projects/case-2024/
litassist digest contract.pdf --mode summary
# Creates: ./logs/digest_*.md

# Case law research
litassist lookup "adverse possession Australia"
# Creates: ./logs/lookup_*.md

# Fact extraction
litassist extractfacts witness_statement.pdf
# Creates: ./case_facts.txt

# Strategy development
litassist brainstorm case_facts.txt --mode irac
# Creates: ./logs/brainstorm_*.md

# Document drafting
litassist draft bundle.pdf "motion to dismiss"
# Creates: ./logs/draft_*.md
```

## Directory Structure

LitAssist creates this structure in your working directory:

```
your-project-directory/
├── case_facts.txt        # Generated by extractfacts
├── logs/                 # All audit logs
│   ├── digest_*.md
│   ├── lookup_*.md
│   ├── brainstorm_*.md
│   ├── draft_*.md
│   └── strategy_*.md
└── your-documents.pdf    # Your input files
```

## Updates and Maintenance

### Updating LitAssist

**With pipx:**
```bash
cd /path/to/litassist
git pull origin master
pipx install -e . --force
```

**With virtual environment:**
```bash
cd /path/to/litassist
git pull origin master
source .venv/bin/activate
pip install -e . --upgrade
```

### Managing Dependencies

LitAssist dependencies are managed in `requirements.txt`. To update:

```bash
cd /path/to/litassist
pip install -r requirements.txt --upgrade
```

## Troubleshooting

### Command Not Found

**Problem:** `litassist: command not found`

**Solutions:**
```bash
# Check if pipx PATH is set
pipx ensurepath
source ~/.zshrc

# Verify installation
which litassist
pipx list

# Reinstall if necessary
pipx uninstall litassist
pipx install -e /path/to/litassist
```

### Configuration Issues

**Problem:** "config.yaml not found" errors

**Solutions:**
```bash
# Check where LitAssist looks for config
python3 -c "from litassist.config import CONFIG; print('Config location:', CONFIG.config_path)" 2>/dev/null || echo "No config found"

# Create config in correct location
cd /path/to/litassist
cp config.yaml.template config.yaml
nano config.yaml

# Verify config loads
python3 -c "from litassist.config import CONFIG; print('[Y] Config loaded from:', CONFIG.config_path)"
```

**Common Mistake:** Creating `config.yaml` in project directories. The config must be in the LitAssist source directory.

### Permission Issues

**Problem:** Permission denied or installation failures

**Solutions:**
```bash
# For pipx installation issues
brew install pipx --force

# For pip installation issues
pip3 install --user -e . --break-system-packages

# For file permission issues (if running from source)
chmod +x litassist/cli.py
```

### Virtual Environment Issues

**Problem:** LitAssist only works when virtual environment is activated

**Solution:** Use pipx installation instead:
```bash
deactivate  # Exit virtual environment
pipx install -e /path/to/litassist
pipx ensurepath
source ~/.zshrc
```

### API Connection Issues

**Problem:** API authentication or connection failures

**Solutions:**
```bash
# Test API connectivity
litassist test

# Check API key format in config.yaml
# Ensure no extra spaces or quotes around keys

# Verify internet connection and API service status
```

## Advanced Configuration

### Environment Variables

Override config file location:
```bash
export LITASSIST_CONFIG=/path/to/custom/config.yaml
litassist lookup "test query"
```

### Shell Integration

Add helpful aliases to `~/.zshrc`:
```bash
# Shortcuts
alias lit='litassist'
alias litdig='litassist digest'
alias litlook='litassist lookup'
alias litfacts='litassist extractfacts'

# Quick project setup
legal-project() {
    mkdir -p "$1" && cd "$1"
    echo "LitAssist ready in $(pwd)"
}
```

## Uninstallation

### Remove pipx Installation
```bash
pipx uninstall litassist
```

### Remove pip Installation
```bash
pip3 uninstall litassist
```

### Clean Up Configuration
```bash
# Remove config (optional - keeps your API keys)
rm /path/to/litassist/config.yaml

# Remove logs from projects (optional)
find ~ -name "logs" -type d -exec rm -rf {} + 2>/dev/null
```

## Getting Help

- **Command help:** `litassist --help` or `litassist <command> --help`
- **User guide:** See [LitAssist_User_Guide.md](/docs/user/LitAssist_User_Guide.md)
- **Configuration:** See `config.yaml.template` for all options
- **Issues:** Report bugs at https://github.com/agelastic/litassist/issues

## Security Notes

- Keep `config.yaml` secure - it contains your API keys
- Never commit `config.yaml` to version control
- Use project-specific billing accounts if working with multiple clients
- Regularly rotate API keys for security
