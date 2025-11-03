#!/usr/bin/env python3
"""Extract commit message and title for GitHub Actions output."""
import os
from pathlib import Path

# Read commit message from file or use default
commit_msg_path = Path("data/commit_message.txt")
if commit_msg_path.exists():
    commit_msg = commit_msg_path.read_text().strip()
else:
    commit_msg = "chore: refresh cybersecurity brief"

# Extract title (first line)
title = commit_msg.split('\n')[0]

# Write to GitHub Actions output
with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as handle:
    handle.write("message<<'EOF'\n")
    handle.write(commit_msg + "\n")
    handle.write("EOF\n")
    handle.write("title<<'EOF'\n")
    handle.write(title + "\n")
    handle.write("EOF\n")
