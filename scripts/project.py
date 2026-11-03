"""Shared build-time metadata; never installed into a DDEV project."""

import importlib
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "worktree-kit"))
config_io = importlib.import_module("config_io")
load_yaml, dump_yaml = config_io.load_yaml, config_io.dump_yaml
REPOSITORY = "BODYA7979/ddev-worktree-kit"
SITE_URL = "https://bodya7979.github.io/ddev-worktree-kit/"
VERSION = re.search(
    r'^VERSION = "([0-9.]+)"$', (ROOT / "worktree-kit/manager.py").read_text(), re.M
)[1]


def source_files():
    output = subprocess.check_output(
        ["git", "-C", str(ROOT), "ls-files", "--cached", "--others", "--exclude-standard", "-z"]
    )
    return sorted({ROOT / p for p in output.decode().split("\0") if p and (ROOT / p).exists()})


def check_tag(tag):
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", tag) or tag != "v" + VERSION:
        raise ValueError(f"Tag must match the runtime version: v{VERSION}")


def release_notes():
    match = re.search(
        rf"^## \[{re.escape(VERSION)}\][^\n]*\n(.*?)(?=^## \[|\Z)",
        (ROOT / "CHANGELOG.md").read_text(),
        re.M | re.S,
    )
    if not match or not match[1].strip():
        raise ValueError("CHANGELOG.md needs a non-empty entry for the runtime version")
    return match[1].strip() + "\n"
