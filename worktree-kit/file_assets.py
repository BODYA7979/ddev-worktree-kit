# fmt: off
#ddev-generated
# fmt: on
"""Explicit shared uploads, independent copies and manual source-to-target sync."""

import filecmp
import os
import shutil
import tempfile
from pathlib import Path


def relative_path(relative, metadata=True):
    relative = Path(relative)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise ValueError(f"Files mapping must be a checkout-relative directory: {relative}")
    if metadata and (
        relative.parts[0].startswith(".git") or relative.parts[0] in (".ddev", ".codex", ".claude")
    ):
        raise ValueError("Files mappings cannot include repository/tool metadata")
    return relative


def local_path(root, relative, metadata=True):
    relative = relative_path(relative, metadata)
    path = root / relative
    if path.resolve() != path or not path.resolve().is_relative_to(root):
        raise ValueError(f"Files mappings cannot traverse symlinks: {path}")
    return path


def disjoint(source, target):
    if source == target or source.is_relative_to(target) or target.is_relative_to(source):
        raise ValueError("Source and worktree uploads directories must not overlap")


def validate(config):
    if not isinstance(config, dict) or set(config) - {"strategy", "mappings"}:
        raise ValueError("files accepts strategy and mappings")
    default = config.get("strategy", "none")
    if default not in ("none", "shared", "copy"):
        raise ValueError("files.strategy must be none, shared or copy")
    mappings = config.get("mappings", [])
    if not isinstance(mappings, list):
        raise ValueError("files.mappings must be a list")
    normalized = []
    paths = []
    for mapping in mappings:
        if not isinstance(mapping, dict) or set(mapping) - {"path", "strategy", "read_only"}:
            raise ValueError("A files mapping accepts path, strategy and read_only")
        if not isinstance(mapping.get("path"), str):
            raise ValueError("Every files mapping requires a relative path")
        path = Path(mapping["path"])
        relative_path(str(path))
        if any(
            path == other or path.is_relative_to(other) or other.is_relative_to(path)
            for other in paths
        ):
            raise ValueError("Files mappings cannot overlap")
        paths.append(path)
        strategy = mapping.get("strategy", default)
        if strategy not in ("none", "shared", "copy"):
            raise ValueError("A files mapping strategy must be none, shared or copy")
        read_only = mapping.get("read_only", False)
        if type(read_only) is not bool:
            raise ValueError("files read_only must be true or false")
        normalized.append({"path": str(path), "strategy": strategy, "read_only": read_only})
    if default != "none" and not mappings:
        raise ValueError("An explicit files mapping is required for shared/copy")
    return normalized


def changed_files(source, target, overwrite):
    """Validate the entire traversal before copying; never follow symlinks."""
    pending = []

    def inaccessible(error):
        raise error

    for directory, dirs, files in os.walk(source, followlinks=False, onerror=inaccessible):
        directory = Path(directory)
        for name in dirs + files:
            original = directory / name
            if original.is_symlink():
                raise ValueError(f"Refusing a symlink inside copied uploads: {original}")
        for filename in files:
            original = directory / filename
            if not original.is_file():
                raise ValueError(f"Refusing a special file: {original}")
            relative = original.relative_to(source)
            destination = local_path(target, str(relative), metadata=False)
            if destination.exists() and not destination.is_file():
                raise ValueError(f"Expected a regular destination file: {destination}")
            if not destination.exists() or (
                overwrite and not filecmp.cmp(original, destination, shallow=False)
            ):
                pending.append((original, destination))
    return pending


def copy_pending(pending):
    for original, destination in pending:
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Recheck paths when applying the plan, including changed symlinks.
        if original.resolve() != original or destination.resolve() != destination:
            raise ValueError("Uploads path changed after planning; refusing to copy")
        descriptor, temporary = tempfile.mkstemp(prefix=".wtk-", dir=destination.parent)
        os.close(descriptor)
        try:
            shutil.copy2(original, temporary)
            os.replace(temporary, destination)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


def prepare(root, source_root, config, previous):
    receipts = []
    mounts = []
    for mapping in validate(config):
        if mapping["strategy"] == "none":
            continue
        source = local_path(source_root, mapping["path"])
        target = local_path(root, mapping["path"])
        disjoint(source, target)
        if not source.is_dir():
            raise ValueError(f"Uploads source directory is missing: {source}")
        if target.exists() and not target.is_dir():
            raise ValueError(f"Uploads destination is not a directory: {target}")
        receipt = {**mapping, "source": str(source), "target": str(target)}
        old = next(
            (item for item in previous if all(item.get(k) == v for k, v in receipt.items())), None
        )
        if mapping["strategy"] == "shared":
            target.mkdir(parents=True, exist_ok=True)
            mounts.append(
                {
                    "type": "bind",
                    "source": str(source).replace("$", "$$"),
                    "target": "/var/www/html/" + mapping["path"],
                    "read_only": mapping["read_only"],
                    "bind": {"create_host_path": False},
                }
            )
        elif old is None:
            pending = changed_files(source, target, overwrite=False)
            copy_pending(pending)
            target.mkdir(parents=True, exist_ok=True)
            receipt["copied_files"] = len(pending)
        else:
            receipt = old
        receipts.append(receipt)
    return receipts, mounts


def sync(root, source_root, config, apply=False):
    plans = []
    all_pending = []
    for mapping in validate(config):
        if mapping["strategy"] != "copy":
            continue
        source = local_path(source_root, mapping["path"])
        target = local_path(root, mapping["path"])
        disjoint(source, target)
        if not source.is_dir():
            raise ValueError(f"Uploads source directory is missing: {source}")
        if target.exists() and not target.is_dir():
            raise ValueError("Uploads destination must be a directory")
        pending = changed_files(source, target, overwrite=True)
        all_pending.extend(pending)
        plans.append(
            {
                "path": mapping["path"],
                "files_to_copy": len(pending),
                "examples": [str(dst.relative_to(target)) for _, dst in pending[:20]],
                "applied": apply,
                "direction": "source-to-worktree",
                "delete": False,
            }
        )
    if apply:
        copy_pending(all_pending)
    return plans
