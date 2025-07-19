#!/usr/bin/env python3
"""
generate-release-notes.py - Generate release notes from CHANGELOG.md

This script extracts version-specific release notes from CHANGELOG.md
and formats them for different outputs (GitHub releases, tags, etc.)
"""

import argparse
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List


class ReleaseNotesGenerator:
    """Generate release notes from CHANGELOG.md"""
    
    def __init__(self, changelog_path: Path):
        self.changelog_path = changelog_path
        self.sections = {
            'added': [],
            'changed': [],
            'fixed': [],
            'removed': [],
            'deprecated': [],
            'security': []
        }
        
    def parse_changelog(self, version: str) -> bool:
        """Parse CHANGELOG.md and extract notes for specific version"""
        if not self.changelog_path.exists():
            print(f"Error: {self.changelog_path} not found", file=sys.stderr)
            return False
            
        with open(self.changelog_path, 'r') as f:
            content = f.read()
            
        # Find the section for this version
        version_pattern = rf'## \[{re.escape(version)}\][^\n]*\n'
        match = re.search(version_pattern, content, re.IGNORECASE)
        
        if not match:
            print(f"Error: Version {version} not found in CHANGELOG.md", file=sys.stderr)
            return False
            
        # Extract content until next version header or end
        start = match.end()
        next_version = re.search(r'## \[[^\]]+\]', content[start:])
        end = start + next_version.start() if next_version else len(content)
        
        version_content = content[start:end].strip()
        
        # Parse sections
        current_section = None
        for line in version_content.split('\n'):
            line = line.strip()
            
            # Check for section headers
            if line.startswith('### '):
                section_name = line[4:].lower()
                if section_name in self.sections:
                    current_section = section_name
                continue
                
            # Add items to current section
            if current_section and line.startswith('- '):
                item = line[2:].strip()
                if item and item != '':
                    self.sections[current_section].append(item)
                    
        return True
        
    def format_github(self, version: str) -> str:
        """Format release notes for GitHub releases"""
        lines = [f"## LitAssist v{version}", ""]
        
        # Add highlights section if there are significant changes
        highlights = []
        if self.sections['added']:
            highlights.extend(self.sections['added'][:2])  # First 2 additions
        if self.sections['fixed']:
            highlights.extend(self.sections['fixed'][:1])  # First fix
            
        if highlights:
            lines.extend(["### Highlights", ""])
            for highlight in highlights:
                lines.append(f"- {highlight}")
            lines.append("")
            
        # Add all sections with content
        section_names = {
            'added': '### 🎯 Added',
            'changed': '### ♻️ Changed',
            'fixed': '### 🐛 Fixed',
            'removed': '### 🗑️ Removed',
            'deprecated': '### ⚠️ Deprecated',
            'security': '### 🔒 Security'
        }
        
        for section_key, section_title in section_names.items():
            if self.sections[section_key]:
                lines.append(section_title)
                for item in self.sections[section_key]:
                    lines.append(f"- {item}")
                lines.append("")
                
        # Add installation instructions
        lines.extend([
            "### Installation",
            "```bash",
            f"pip install litassist=={version}",
            "```",
            "",
            "### Upgrading",
            "```bash",
            "pip install --upgrade litassist",
            "```",
            "",
            "### Documentation",
            "- [User Guide](docs/user/LitAssist_User_Guide.md)",
            "- [Installation Guide](INSTALLATION.md)",
            "- [Release Process](RELEASE_PROCESS.md)",
            ""
        ])
        
        # Add note about changes
        total_changes = sum(len(items) for items in self.sections.values())
        if total_changes > 0:
            lines.append(f"**Full Changelog**: {total_changes} changes in this release")
            
        return '\n'.join(lines)
        
    def format_tag(self, version: str) -> str:
        """Format release notes for git tags (more concise)"""
        lines = [f"Release version {version}", ""]
        
        # Add summary of changes
        for section_name, items in self.sections.items():
            if items:
                lines.append(f"{section_name.capitalize()}:")
                for item in items[:3]:  # Limit to 3 items per section
                    lines.append(f"- {item}")
                if len(items) > 3:
                    lines.append(f"  ... and {len(items) - 3} more")
                lines.append("")
                
        if not any(self.sections.values()):
            lines.append("See CHANGELOG.md for details")
            
        return '\n'.join(lines).strip()
        
    def format_simple(self, version: str) -> str:
        """Simple format listing all changes"""
        lines = []
        
        for section_name, items in self.sections.items():
            if items:
                lines.append(f"{section_name.upper()}:")
                for item in items:
                    lines.append(f"- {item}")
                lines.append("")
                
        return '\n'.join(lines).strip()


def main():
    parser = argparse.ArgumentParser(
        description='Generate release notes from CHANGELOG.md'
    )
    parser.add_argument(
        'version',
        help='Version number to extract (e.g., 1.2.3)'
    )
    parser.add_argument(
        '--format',
        choices=['github', 'tag', 'simple'],
        default='github',
        help='Output format (default: github)'
    )
    parser.add_argument(
        '--changelog',
        type=Path,
        default=Path('CHANGELOG.md'),
        help='Path to CHANGELOG.md (default: ./CHANGELOG.md)'
    )
    
    args = parser.parse_args()
    
    # Make changelog path absolute if relative
    if not args.changelog.is_absolute():
        # Try to find project root
        current = Path.cwd()
        while current != current.parent:
            if (current / args.changelog).exists():
                args.changelog = current / args.changelog
                break
            if (current / 'setup.py').exists():
                # Found project root
                args.changelog = current / args.changelog
                break
            current = current.parent
    
    generator = ReleaseNotesGenerator(args.changelog)
    
    if not generator.parse_changelog(args.version):
        return 1
        
    # Generate output based on format
    if args.format == 'github':
        output = generator.format_github(args.version)
    elif args.format == 'tag':
        output = generator.format_tag(args.version)
    else:
        output = generator.format_simple(args.version)
        
    print(output)
    return 0


if __name__ == '__main__':
    sys.exit(main())