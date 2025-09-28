#!/usr/bin/env python3
"""Setup script for Mainframe Copilot - AI-driven mainframe automation system"""

import os
import sys
import subprocess
from pathlib import Path
from setuptools import setup, find_packages
from setuptools.command.install import install
from setuptools.command.develop import develop

# Package metadata
NAME = "mainframe-copilot"
VERSION = "1.0.0"
DESCRIPTION = "AI-driven automation system for IBM mainframe TN3270 interaction"
LONG_DESCRIPTION = """
Mainframe Copilot enables natural language control of IBM mainframes through:
- TN3270 protocol automation
- AI-powered screen interpretation
- YAML workflow execution
- Claude Code integration

This package provides the automation framework. MVS system files must be
downloaded separately due to size constraints (1.1GB).
"""

# Python requirements
REQUIRES = [
    "fastapi>=0.104.1",
    "uvicorn[standard]>=0.24.0",
    "pydantic>=2.5.0",
    "python-multipart>=0.0.6",
    "requests>=2.31.0",
    "pyyaml>=6.0",
    "psutil>=5.9.0",
]

# Package directories
PACKAGE_DIR = Path(__file__).parent
HERC_STEP8_DIR = PACKAGE_DIR / "herc_step8"


class PostInstallCommand:
    """Post-installation setup tasks"""

    def run(self):
        """Run post-installation setup"""
        print("\n" + "="*60)
        print("Mainframe Copilot Installation")
        print("="*60 + "\n")

        # Create runtime directory structure
        self.create_runtime_structure()

        # Create symlinks
        self.create_symlinks()

        # Check for MVS files
        self.check_mvs_files()

        print("\n" + "="*60)
        print("Installation Complete!")
        print("="*60 + "\n")
        self.print_next_steps()

    def create_runtime_structure(self):
        """Create ~/herc runtime directory structure"""
        print("Creating runtime directory structure...")

        herc_home = Path.home() / "herc"
        directories = [
            herc_home,
            herc_home / "logs",
            herc_home / "logs" / "ai",
            herc_home / "logs" / "ai" / "trace",
            herc_home / "logs" / "archive",
            herc_home / "logs" / "flows",
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

        print(f"✓ Created runtime structure at {herc_home}")

    def create_symlinks(self):
        """Create symlinks from ~/herc to package directories"""
        print("Creating symlinks to package directories...")

        herc_home = Path.home() / "herc"

        # Symlink mappings
        links = {
            herc_home / "ai": HERC_STEP8_DIR / "ai",
            herc_home / "bridge": HERC_STEP8_DIR / "bridge",
            herc_home / "flows": HERC_STEP8_DIR / "flows",
            herc_home / "tools": HERC_STEP8_DIR / "tools",
            herc_home / "scripts": HERC_STEP8_DIR / "scripts",
            herc_home / "docs": HERC_STEP8_DIR / "docs",
            herc_home / "config.yaml": HERC_STEP8_DIR / "config.yaml",
            herc_home / "demo.sh": HERC_STEP8_DIR / "demo.sh",
            herc_home / "stop.sh": HERC_STEP8_DIR / "stop.sh",
        }

        for link_path, target_path in links.items():
            if target_path.exists():
                if link_path.exists() or link_path.is_symlink():
                    link_path.unlink()
                link_path.symlink_to(target_path)
                print(f"✓ Linked {link_path.name} → {target_path}")

    def check_mvs_files(self):
        """Check if MVS files are installed"""
        print("\nChecking for MVS system files...")

        mvs_dir = Path.home() / "herc" / "mvs38j" / "mvs-tk5"

        if not mvs_dir.exists():
            print("✗ MVS TK5 not found")
            print("\nMVS 3.8J system files (1.1GB) are required but not included.")
            print("They must be downloaded separately.\n")
            return False

        print(f"✓ MVS files found at {mvs_dir}")
        return True

    def print_next_steps(self):
        """Print next steps for user"""
        mvs_dir = Path.home() / "herc" / "mvs38j" / "mvs-tk5"

        if not mvs_dir.exists():
            print("Next Steps:")
            print("-----------")
            print("1. Download MVS TK5 system files:")
            print(f"   {PACKAGE_DIR}/scripts/download_mvs.sh")
            print("")
            print("2. After MVS download completes, start the system:")
            print("   cd ~/herc")
            print("   ./demo.sh")
        else:
            print("Next Steps:")
            print("-----------")
            print("1. Start the system:")
            print("   cd ~/herc")
            print("   ./demo.sh")
            print("")
            print("2. For Claude Code integration:")
            print("   python ~/herc/ai/claude_code_control.py")

        print("\nDocumentation:")
        print("  README: ~/herc/README.md")
        print("  Runbook: ~/herc/docs/RUNBOOK.md")
        print("  MVS Setup: ~/herc/docs/MVS_SETUP.md")


class CustomInstallCommand(install):
    """Custom installation command"""

    def run(self):
        install.run(self)
        self.execute(PostInstallCommand().run, [], msg="Running post-install setup...")


class CustomDevelopCommand(develop):
    """Custom develop command"""

    def run(self):
        develop.run(self)
        self.execute(PostInstallCommand().run, [], msg="Running post-install setup...")


# Main setup
setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    author="Mainframe Copilot Team",
    python_requires=">=3.8",
    packages=find_packages(exclude=["tests", "*.tests", "*.tests.*", "tests.*"]),
    package_data={
        "": ["*.yaml", "*.yml", "*.json", "*.md", "*.txt", "*.sh", "*.expect"],
    },
    include_package_data=True,
    install_requires=REQUIRES,
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-asyncio>=0.21",
            "black>=22.0",
            "flake8>=5.0",
            "mypy>=1.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "mainframe-copilot=herc_step8.ai.run_agent:main",
            "tn3270-bridge=herc_step8.bridge.tn3270_bridge.api_enhanced:main",
        ],
    },
    cmdclass={
        "install": CustomInstallCommand,
        "develop": CustomDevelopCommand,
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Emulators",
        "Topic :: Terminals :: Terminal Emulators/X Terminals",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="mainframe tn3270 automation ai mvs tso ispf",
    project_urls={
        "Documentation": "https://github.com/mainframe-copilot/docs",
        "Source": "https://github.com/mainframe-copilot/mainframe-copilot",
        "Issues": "https://github.com/mainframe-copilot/mainframe-copilot/issues",
    },
)