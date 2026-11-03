# fmt: off
#ddev-generated
# fmt: on
"""Claude's native Git lifecycle adapter; DDEV stays behind the host CLI."""

import contextlib
import fcntl
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

OWNER_FILE = "ddev-worktree-kit-claude-owner"


def execute(argv, cwd):
    result = subprocess.run([str(item) for item in argv], cwd=cwd, text=True, capture_output=True)
    if result.returncode:
        raise ValueError(
            f"Claude worktree operation failed:\n{result.stderr.strip()}\n{result.stdout.strip()}"
        )
    return result.stdout.rstrip("\n")


def git(path, *args):
    return execute(["git", "-C", path, *args], path)


def identity(path):
    root = Path(git(path, "rev-parse", "--show-toplevel")).resolve()
    common = Path(git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()
    own = Path(git(root, "rev-parse", "--absolute-git-dir")).resolve()
    records = execute(["git", "-C", root, "worktree", "list", "--porcelain", "-z"], root).split(
        "\0\0"
    )
    first = records[0].split("\0")
    if "bare" in first or not first[0].startswith("worktree "):
        raise ValueError("Claude hooks require a non-bare repository with a main checkout")
    main = Path(first[0].removeprefix("worktree ")).resolve()
    return root, common, own, main


def atomic(path, text):
    if path.is_symlink():
        raise ValueError("Refusing a symlink adapter state/config file")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".claude-wt-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextlib.contextmanager
def locked(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("Refusing symlink adapter lock")
    with path.open("a+") as stream:
        deadline = time.monotonic() + 120
        while True:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise ValueError("Timed out waiting for Claude worktree lifecycle lock")
                time.sleep(0.1)
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def receipts(common):
    path = common / "ddev-worktree-kit/claude-worktrees.json"
    if path.is_symlink():
        raise ValueError("Refusing symlink adapter receipts")
    value = json.loads(path.read_text()) if path.exists() else {"version": 1, "worktrees": {}}
    if value.get("version") != 1 or not isinstance(value.get("worktrees"), dict):
        raise ValueError("Invalid Claude worktree ownership receipts")
    return path, value


def save(path, value):
    atomic(path, json.dumps(value, indent=2) + "\n")


def validate_target(target, receipt, common, main):
    if (
        not target.is_absolute()
        or target.resolve() != target
        or target.parent != main / ".claude/worktrees"
    ):
        raise ValueError("Claude target must be a real direct child of main/.claude/worktrees")
    root, actual_common, own, _ = identity(target)
    if (
        root != target
        or actual_common != common
        or own == common
        or str(own) != receipt.get("git_dir")
    ):
        raise ValueError("Claude worktree ownership no longer matches; refusing mutation")
    marker = own / OWNER_FILE
    if (
        marker.is_symlink()
        or not marker.is_file()
        or marker.read_text().strip() != receipt.get("token")
    ):
        raise ValueError("Claude worktree ownership marker does not match")


def manager_call(manager, repository, target, *args):
    output = execute(
        [sys.executable, manager, "--repository", repository, "--path", target, *args], repository
    )
    return json.loads(output)


def reject_nested_checkouts(main, target):
    """A receipt owns this checkout, never repositories created inside it."""
    records = git(main, "worktree", "list", "--porcelain", "-z").split("\0\0")
    for record in records:
        first = record.split("\0", 1)[0]
        if first.startswith("worktree "):
            checkout = Path(first.removeprefix("worktree ")).resolve()
            if checkout != target and checkout.is_relative_to(target):
                raise ValueError("Nested registered worktree found; preserving DDEV and checkout")

    def failed(error):
        raise error

    for directory, directories, files in os.walk(target, followlinks=False, onerror=failed):
        if Path(directory) != target and ".git" in directories + files:
            raise ValueError("Nested Git checkout found; preserving DDEV and checkout")


def bootstrap_hooks(main, target, common):
    """Keep native hooks available on branches predating the uncommitted add-on."""
    source = main / ".claude/settings.json"
    if source.is_file():
        owned = {}
        for event, groups in json.loads(source.read_text()).get("hooks", {}).items():
            if event not in ("WorktreeCreate", "WorktreeRemove", "SessionStart"):
                continue
            for group in groups:
                hooks = [
                    hook
                    for hook in group.get("hooks", [])
                    if "/worktree-kit/" in hook.get("command", "")
                ]
                if hooks:
                    owned.setdefault(event, []).append({**group, "hooks": hooks})
        if owned:
            local = target / ".claude/settings.local.json"
            if local.resolve() != local:
                raise ValueError("Refusing symlink Claude local settings")
            settings = json.loads(local.read_text()) if local.exists() else {}
            events = settings.setdefault("hooks", {})
            for event, groups in owned.items():
                retained = []
                for group in events.get(event, []):
                    other = [
                        h
                        for h in group.get("hooks", [])
                        if "/worktree-kit/" not in h.get("command", "")
                    ]
                    if other:
                        retained.append({**group, "hooks": other})
                events[event] = retained + groups
            atomic(local, json.dumps(settings, indent=2) + "\n")
    with locked(common / "ddev-worktree-kit/registry.lock"):
        path = common / "info/exclude"
        previous = path.read_text() if path.exists() else ""
        entries = ["/.claude/worktrees/", "/.claude/settings.local.json"]
        missing = [entry for entry in entries if entry not in previous.splitlines()]
        if missing:
            atomic(path, previous.rstrip("\n") + "\n" + "\n".join(missing) + "\n")


def create(payload, repository, manager):
    if payload.get("hook_event_name") != "WorktreeCreate" or not isinstance(
        payload.get("cwd"), str
    ):
        raise ValueError("Expected WorktreeCreate payload with cwd/name")
    name = payload.get("name")
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", name):
        raise ValueError("Worktree name must be a safe single path component")
    origin, common, _, main = identity(Path(payload["cwd"]))
    if not repository or identity(Path(repository))[1] != common:
        raise ValueError("WorktreeCreate belongs to another repository")
    target = main / ".claude/worktrees" / name
    if target.resolve() != target:
        raise ValueError("Refusing symlink Claude worktree path")
    branch = "worktree-" + name
    git(origin, "check-ref-format", "--branch", branch)
    with locked(common / "ddev-worktree-kit/claude-adapter.lock"):
        state_path, state = receipts(common)
        row = state["worktrees"].get(str(target))
        if target.exists():
            if row is None:
                raise ValueError("Existing checkout is not owned by this Claude adapter")
            validate_target(target, row, common, main)
        else:
            if row is not None:
                raise ValueError("Owned checkout disappeared; inspect it before recreating")
            registry_path = common / "ddev-worktree-kit/registry.json"
            with locked(common / "ddev-worktree-kit/registry.lock"):
                if registry_path.is_file():
                    environments = json.loads(registry_path.read_text())["environments"]
                    if any(item["path"] == str(target) for item in environments.values()):
                        raise ValueError(
                            "An earlier DDEV environment still owns this path; inspect/gc it before reuse"
                        )
            target.parent.mkdir(parents=True, exist_ok=True)
            exists = (
                "refs/heads/" + branch
                in git(
                    origin, "for-each-ref", "--format=%(refname)", "refs/heads/" + branch
                ).splitlines()
            )
            arguments = ["worktree", "add"]
            if exists:
                arguments += [str(target), branch]
            else:
                arguments += ["-b", branch, str(target), git(origin, "rev-parse", "HEAD")]
            git(origin, *arguments)
            own = identity(target)[2]
            token = uuid.uuid4().hex
            atomic(own / OWNER_FILE, token + "\n")
            row = {
                "name": name,
                "path": str(target),
                "git_dir": str(own),
                "token": token,
                "branch": branch,
                "created_branch": not exists,
                "state": "created",
            }
            state["worktrees"][str(target)] = row
            save(state_path, state)
        try:
            bootstrap_hooks(main, target, common)
            environment = manager_call(manager, main, target, "init")
            if environment.get("phase") not in ("ready", "prepared"):
                raise ValueError("DDEV setup did not reach ready/prepared")
            row.update(state="ready", environment=environment["name"])
            save(state_path, state)
        except (ValueError, OSError) as error:
            row["state"] = "setup_failed"
            save(state_path, state)
            raise ValueError(
                f"DDEV setup failed; owned checkout retained for retry at {target}: {error}"
            ) from error
    return str(target)


def remove(payload, repository, manager):
    if payload.get("hook_event_name") != "WorktreeRemove" or not isinstance(
        payload.get("worktree_path"), str
    ):
        raise ValueError("Expected WorktreeRemove payload with worktree_path")
    if not repository:
        raise ValueError("WorktreeRemove requires the configured repository")
    _, common, _, main = identity(Path(repository))
    target = Path(payload["worktree_path"])
    if (
        not target.is_absolute()
        or target.resolve() != target
        or target.parent != main / ".claude/worktrees"
    ):
        raise ValueError("Refusing a path outside adapter-owned Claude worktrees")
    with locked(common / "ddev-worktree-kit/claude-adapter.lock"):
        state_path, state = receipts(common)
        row = state["worktrees"].get(str(target))
        if row is None:
            if not target.exists():
                return {"status": "skipped", "reason": "already removed"}
            raise ValueError("Checkout is not owned by this Claude adapter")
        if not target.exists():
            raise ValueError("Checkout disappeared before cleanup; ownership requires inspection")
        validate_target(target, row, common, main)
        if (Path(row["git_dir"]) / "locked").exists():
            raise ValueError("Claude worktree is locked; preserving its DDEV and checkout")
        reject_nested_checkouts(main, target)
        # Re-read core ownership even on retry: init may have recreated DDEV
        # while the checkout remained after an earlier Git removal failure.
        result = manager_call(manager, main, target, "teardown", "--automatic", "--apply", "--yes")
        if (
            result.get("reason") == "not managed"
            and row.get("environment")
            and row["state"] != "environment_removed"
        ):
            raise ValueError("DDEV ownership receipt is missing; preserving checkout")
        row.update(state="environment_removed", cleanup=result)
        save(state_path, state)
        validate_target(target, row, common, main)
        reject_nested_checkouts(main, target)
        # This event is Claude's committed removal decision. Only the exact
        # checkout created by this adapter is removed; all Git branches stay.
        git(main, "worktree", "remove", "--force", "--", str(target))
        del state["worktrees"][str(target)]
        save(state_path, state)
    return {
        "status": "removed",
        "path": str(target),
        "branch_preserved": row["branch"],
        "ddev": row["cleanup"]["status"],
    }
