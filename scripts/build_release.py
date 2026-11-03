"""Build the DDEV payload using Git's export-ignore rules, without a commit."""

import argparse
import hashlib
import importlib
import re
import subprocess
import sys
import tarfile
from pathlib import Path

sys.dont_write_bytecode = True
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "worktree-kit"))
load_yaml = importlib.import_module("config_io").load_yaml


def git(*args, input=None):
    return subprocess.check_output(["git", "-C", str(root), *args], input=input)


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path)
args = parser.parse_args()
version = re.search(
    r'^VERSION = "([0-9.]+)"$', (root / "worktree-kit/manager.py").read_text(), re.M
)[1]
destination = args.output or root / "dist" / f"ddev-worktree-kit-v{version}.tar.gz"
candidates = [
    Path(p)
    for p in git("ls-files", "--cached", "--others", "--exclude-standard", "-z")
    .decode()
    .split("\0")
    if p and ((root / p).is_file() or (root / p).is_symlink())
]


def attribute_path(path):
    # Git directory attributes are queried with their trailing slash, just as
    # git archive does while descending the tree.
    return str(path) + ("/" if (root / path).is_dir() else "")


scopes = sorted(
    {attribute_path(p) for item in candidates for p in (item, *item.parents) if str(p) != "."}
)
attributes = (
    git("check-attr", "-z", "--stdin", "export-ignore", input=("\0".join(scopes) + "\0").encode())
    .decode()
    .split("\0")
)
excluded = {attributes[i] for i in range(0, len(attributes) - 1, 3) if attributes[i + 2] == "set"}
files = sorted(
    {
        item
        for item in candidates
        if not any(attribute_path(p) in excluded for p in (item, *item.parents))
    }
)
manifest = load_yaml((root / "install.yaml").read_text())
required = {Path(p) for p in manifest["project_files"]} | {Path("install.yaml")}
if not required.issubset(files):
    raise SystemExit("Release export excludes an install.yaml payload file")


def metadata(info):
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    return info


destination.parent.mkdir(parents=True, exist_ok=True)
with tarfile.open(destination, "w:gz") as archive:
    for item in files:
        path = root / item
        if path.is_symlink() or not path.is_file():
            raise SystemExit(f"Release requires regular source files: {item}")
        archive.add(
            path, arcname="ddev-worktree-kit/" + str(item), recursive=False, filter=metadata
        )
checksum = hashlib.sha256(destination.read_bytes()).hexdigest()
destination.with_suffix(destination.suffix + ".sha256").write_text(
    checksum + "  " + destination.name + "\n"
)
print(destination)
