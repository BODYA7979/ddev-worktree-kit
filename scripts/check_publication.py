"""Validate the local source candidate; this does not publish anything."""

import argparse
import re
import subprocess
from pathlib import Path

from project import ROOT, VERSION, check_tag, load_yaml, release_notes, source_files


def check():
    manifest = load_yaml((ROOT / "install.yaml").read_text())
    if manifest["name"] != "worktree-kit":
        raise ValueError("Unexpected add-on identity")
    for relative in manifest["project_files"]:
        path = ROOT / relative
        if (
            path.is_symlink()
            or not path.is_file()
            or "#ddev-generated" not in path.read_text()[:200]
        ):
            raise ValueError(f"Missing or unowned install payload: {relative}")
    command = ROOT / "commands/host/worktree-kit"
    if not command.stat().st_mode & 0o111 or "## Aliases: wtk" not in command.read_text():
        raise ValueError("The host command must be executable and provide the wtk alias")
    languages = {}
    for language, config_name in (("en", "mkdocs.yml"), ("uk", "mkdocs.uk.yml")):
        config = load_yaml((ROOT / config_name).read_text())
        pages = [next(iter(item.values())) for item in config["nav"]]
        languages[language] = set(pages)
        actual = {p.name for p in (ROOT / "docs" / language).glob("*.md")}
        if actual != set(pages):
            raise ValueError(f"Navigation/page coverage mismatch for {language}")
    if languages["en"] != languages["uk"]:
        raise ValueError("English and Ukrainian pages must cover the same topics")
    for path in source_files():
        if path.is_symlink():
            raise ValueError(f"Public source cannot contain a symlink: {path.relative_to(ROOT)}")
        text = path.read_text()
        if re.search(r"/(?:Users|home)/[^/\s]+/", text):
            raise ValueError(f"Personal absolute path in public source: {path.relative_to(ROOT)}")
        if path.suffix != ".md":
            continue
        for link in re.findall(r"\]\(([^)]+)\)", text):
            if "://" in link or link.startswith(("#", "mailto:")):
                continue
            target = path.parent / link.split("#", 1)[0]
            if not target.exists():
                raise ValueError(f"Broken source link in {path.relative_to(ROOT)}: {link}")
    release_notes()
    return sum(len(pages) for pages in languages.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag")
    parser.add_argument("--require-clean", action="store_true")
    parser.add_argument("--notes-output", type=Path)
    args = parser.parse_args()
    try:
        if args.tag:
            check_tag(args.tag)
        if (
            args.require_clean
            and subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain"]).strip()
        ):
            raise ValueError("Release source checkout must be clean")
        count = check()
        if args.notes_output:
            args.notes_output.parent.mkdir(parents=True, exist_ok=True)
            args.notes_output.write_text(release_notes())
    except (ValueError, OSError) as error:
        parser.exit(1, f"publication: {error}\n")
    print(f"Publication candidate v{VERSION}: PASS ({count} bilingual pages)")


if __name__ == "__main__":
    main()
