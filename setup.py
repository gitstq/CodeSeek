#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Setup script for CodeSeek."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding='utf-8') if readme_path.exists() else ""

setup(
    name="codeseek",
    version="1.0.0",
    description="Lightweight Local Semantic Code Search Engine",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="gitstq",
    author_email="",
    url="https://github.com/gitstq/CodeSeek",
    py_modules=["codeseek"],
    entry_points={
        "console_scripts": [
            "codeseek=codeseek:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",
    ],
    keywords="semantic-search code-search cli developer-tools ai coding",
    python_requires=">=3.8",
    install_requires=[
        # Pure Python, no external dependencies required
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "black>=22.0",
            "flake8>=4.0",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/gitstq/CodeSeek/issues",
        "Source": "https://github.com/gitstq/CodeSeek",
    },
)
