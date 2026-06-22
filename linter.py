# Install Ruff
# %pip install ruff

import subprocess

# Root directory containing Python files and notebooks
root_dir = (
    "/Users/PaidiVibhavanRao/OneDrive - JMAN Group Ltd/vibhavan/databricks starter kit/"
)

# -----------------------------
# Linting Check
# -----------------------------
print("\nRunning Ruff Lint Check...")
subprocess.run(["ruff", "check", root_dir])

# Show proposed fixes (diff)
print("\nShowing Proposed Fixes (Diff)...")
subprocess.run(["ruff", "check", root_dir, "--fix", "--diff"])

# -----------------------------
# Auto-fix Linting Issues
# -----------------------------
# print("\nRunning Ruff Auto-Fix...")
# subprocess.run(["ruff", "check", root_dir, "--fix"])

# -----------------------------
# Format Check
# -----------------------------
print("\nRunning Ruff Format Check...")
subprocess.run(["ruff", "format", root_dir, "--check"])

# -----------------------------
# Show proposed fixes (diff)
# -----------------------------
print("\nShowing Formatting Differences...")
subprocess.run(["ruff", "format", root_dir, "--diff"])

# -----------------------------
# Auto Format
# -----------------------------
# print("\nRunning Ruff Auto-Format...")
# subprocess.run(["ruff", "format", root_dir])
