#!/usr/bin/env python3
"""
Setup script for LitAssist - AI-powered litigation support for Australian law
"""

from setuptools import setup, find_packages
import os

# Read the README file for long description
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "LitAssist - AI-powered litigation support for Australian law"

# Read requirements from requirements.txt
def read_requirements():
    req_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(req_path):
        with open(req_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    # If requirements.txt is missing from a sdist, fail loud rather than
    # drifting from the in-repo manifest. The previous fallback list went
    # stale and pinned wrong package versions.
    raise RuntimeError(
        "requirements.txt is missing from the source distribution. "
        "Ensure MANIFEST.in includes it and rebuild the sdist."
    )

setup(
    name="litassist",
    version="1.0.0",
    author="LitAssist Project",
    description="AI-powered litigation support for Australian law",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/agelastic/litassist",
    packages=find_packages(
        exclude=["tests", "tests.*", "test-scripts", "test-scripts.*"]
    ),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Legal Industry",
        "Topic :: Office/Business :: Financial :: Accounting",
        # Mark the package as proprietary / closed-source
        "License :: Other/Proprietary License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.11",
    install_requires=read_requirements(),
    entry_points={
        "console_scripts": [
            "litassist=litassist.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "litassist": ["*.yaml", "*.md"],
        # Prompt and model-config YAMLs are loaded at runtime via PROMPTS.get
        # / load_yaml; installed wheels need them or commands fail with
        # missing-key errors.
        "litassist.prompts": ["*.yaml"],
        "litassist.llm": ["*.yaml"],
        "": ["config.yaml.template", "README.md", "*.md"],
    },
    keywords="legal ai litigation australian law nlp",
    project_urls={
        "Bug Reports": "https://github.com/agelastic/litassist/issues",
        "Source": "https://github.com/agelastic/litassist",
        "Documentation": "https://github.com/agelastic/litassist/blob/master/README.md",
    },
)
