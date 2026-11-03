#!/usr/bin/env python3
# fmt: off
#ddev-generated
# fmt: on
"""Host-only DDEV lifecycle for existing linked Git worktrees."""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import importlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

sys.dont_write_bytecode = True
file_assets = importlib.import_module("file_assets")
config_io = importlib.import_module("config_io")
dump_yaml, load_yaml = config_io.dump_yaml, config_io.load_yaml
normalize = importlib.import_module("config_schema").normalize
claude_worktrees = importlib.import_module("claude_worktrees")

VERSION = "0.5.0"
MARKER = "# ddev-worktree-kit: managed v1"
OVERRIDE = "config.zzzz-worktree-kit.local.yaml"
COMPOSE = "docker-compose.worktree-kit.yaml"
GIT_FILE = "worktree-kit.git"
LABEL = "dev.worktree-kit.owner"
CONFIG = ".ddev/worktree-kit.yaml"
LEGACY_CONFIG = ".ddev/worktree-kit.json"
DEFAULTS = {
    "version": 1,
    "source": "main",
    "tld": "ddev.site",
    "local_files": [".ddev/config.local.yaml"],
    "composer": "auto",
    "composer_root": "",
    "bootstrap": [],
    "sites": {},
    "files": {"strategy": "none", "mappings": []},
    "name_template": "{project}-wt-{slug}-{hash}",
    "auto_start": True,
    "snapshot": "fresh",
    "create_if_missing": True,
    "orphan_detection": True,
    "auto_delete": False,
}


class Error(Exception):
    """An actionable failure; no destructive automatic recovery is attempted."""


def run(argv, cwd=None, *, input=None):
    result = subprocess.run(
        [str(a) for a in argv],
        cwd=cwd,
        input=input,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        raise Error(
            f"{argv[0]} {argv[1] if len(argv) > 1 else ''} failed "
            f"({result.returncode}):\n{result.stderr.strip()}\n{result.stdout.strip()}"
        )
    return result.stdout


def git(root, *args):
    return run(["git", "-C", root, *args]).rstrip("\n")


def raw_json(output):
    """DDEV emits JSON lines, including progress messages before the raw result."""
    found = None
    for line in output.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "raw" in value:
            found = value["raw"]
    if found is None:
        raise Error("DDEV returned no structured raw result")
    return found


def ddev_json(root, *args):
    return raw_json(run(["ddev", "--json-output", *args], root))


def within(root, relative):
    """Allow only checkout-local paths, including through existing symlinks."""
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or "\n" in str(path):
        raise Error(f"Expected a checkout-relative path: {relative}")
    result = root / path
    if not result.resolve().is_relative_to(root.resolve()):
        raise Error(f"Path escapes checkout: {relative}")
    return result


def atomic(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise Error(f"Refusing symlink: {path}")
    descriptor, temporary = tempfile.mkstemp(prefix=".wtk-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def managed(path, text):
    if path.is_symlink():
        raise Error(f"Refusing symlink: {path}")
    if path.exists() and not path.read_text().startswith(MARKER):
        # PHP must begin with <?php rather than a text marker.
        if not path.read_text().startswith("<?php\n" + MARKER):
            raise Error(f"Refusing to overwrite an unowned file: {path}")
    if not path.exists() or path.read_text() != text:
        atomic(path, text)


@contextlib.contextmanager
def lock(path, timeout=120):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise Error(f"Refusing symlink lock: {path}")
    with path.open("a+") as stream:
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise Error(f"Timed out waiting for {path}")
                time.sleep(0.1)
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def worktrees(root):
    output = run(["git", "-C", root, "worktree", "list", "--porcelain", "-z"])
    entries = []
    entry = {}
    for field in output.split("\0"):
        if not field:
            if entry:
                entries.append(entry)
                entry = {}
            continue
        key, _, value = field.partition(" ")
        entry[key] = value
    if entry:
        entries.append(entry)
    return entries


def context(path):
    root = Path(git(path, "rev-parse", "--show-toplevel")).resolve()
    common = Path(git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()
    own = Path(git(root, "rev-parse", "--absolute-git-dir")).resolve()
    entries = worktrees(root)
    if not entries or "bare" in entries[0]:
        raise Error("MVP requires a non-bare repository with a main checkout")
    main = Path(entries[0]["worktree"]).resolve()
    return root, common, own, main, entries


def configuration(root, main):
    config = dict(DEFAULTS)
    path = None
    for checkout in dict.fromkeys((root, main)):
        present = [
            within(checkout, relative)
            for relative in (CONFIG, LEGACY_CONFIG)
            if (checkout / relative).exists()
        ]
        if len(present) > 1:
            raise Error("Both YAML and legacy JSON config exist; keep only worktree-kit.yaml")
        if present:
            path = present[0]
            break
    if path is not None:
        supplied = normalize(load_yaml(path.read_text()))
        if path.name.endswith(".json"):
            print("wtk: legacy JSON config; migrate to .ddev/worktree-kit.yaml", file=sys.stderr)
        if not isinstance(supplied, dict) or set(supplied) - set(DEFAULTS):
            raise Error("Unknown configuration keys (see examples/worktree-kit.yaml)")
        config.update(supplied)
    if type(config["version"]) is not int or config["version"] != 1:
        raise Error("Unsupported configuration version")
    for key in ("auto_start", "create_if_missing", "orphan_detection", "auto_delete"):
        if type(config[key]) is not bool:
            raise Error(f"{key} must be true or false")
    if config["snapshot"] not in ("fresh", "latest"):
        raise Error("database.snapshot must be fresh or latest")
    if not isinstance(config["name_template"], str) or "{hash}" not in config["name_template"]:
        raise Error("worktree.name must contain {hash} to retain unique identities")
    file_assets.validate(config["files"])
    if not isinstance(config["source"], str):
        raise Error("source must be 'main' or an absolute checkout path")
    if not re.fullmatch(r"[a-z0-9]+(?:[.-][a-z0-9]+)*", config["tld"]):
        raise Error("Invalid tld")
    if config["composer"] not in ("auto", "off"):
        raise Error("composer must be auto or off")
    within(root, config["composer_root"])
    if not isinstance(config["local_files"], list):
        raise Error("local_files must be a list of checkout-relative files")
    for item in config["local_files"]:
        if (
            not isinstance(item, str)
            or item.startswith(".git/")
            or item in (".git", ".ddev/config.yaml")
        ):
            raise Error("local_files must not copy Git metadata or the base DDEV config")
        within(root, item)
    if not isinstance(config["bootstrap"], list):
        raise Error("bootstrap must be an array of argv arrays")
    for argv in config["bootstrap"]:
        if (
            not isinstance(argv, list)
            or not argv
            or not all(isinstance(v, str) and v for v in argv)
        ):
            raise Error("Every bootstrap command must be a non-empty argv array")
    if not isinstance(config["sites"], dict):
        raise Error("sites must map hostname aliases to site configuration")
    databases = {}
    for alias, site in config["sites"].items():
        if alias and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", alias):
            raise Error(f"Invalid site alias: {alias}")
        if not isinstance(site, dict) or set(site) - {"directory", "database"}:
            raise Error(f"Invalid site configuration: {alias}")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", site.get("directory", "")):
            raise Error("Site directory must be a direct child of Drupal sites/")
        if "database" in site and not re.fullmatch(r"[A-Za-z0-9_]+", site["database"]):
            raise Error("Invalid multisite database name")
        directory = site["directory"]
        if directory in databases and databases[directory] != site.get("database"):
            raise Error("Aliases of the same site directory must use the same database")
        databases[directory] = site.get("database")
    return config


def load_registry(common):
    path = common / "ddev-worktree-kit/registry.json"
    if not path.exists():
        return {"version": 1, "environments": {}}
    if path.is_symlink():
        raise Error("Refusing symlink registry")
    data = json.loads(path.read_text())
    if data.get("version") != 1 or not isinstance(data.get("environments"), dict):
        raise Error("Invalid environment registry; refusing to guess ownership")
    return data


def save_registry(common, registry):
    atomic(common / "ddev-worktree-kit/registry.json", json.dumps(registry, indent=2) + "\n")


def runtime(root):
    version = ddev_json(root, "version")
    match = re.match(r"v?(\d+)\.(\d+)\.(\d+)(.*)", version.get("DDEV version", ""))
    if not match or tuple(map(int, match.groups()[:3])) < (1, 25, 4) or match.group(4):
        raise Error("DDEV >= 1.25.4 stable required for fresh-volume snapshot seed")
    run(["docker", "info", "--format", "{{.ServerVersion}}"])
    return Path(version["global-ddev-dir"]) / "worktree-kit/start.lock"


def projects(root):
    data = ddev_json(root, "list")
    if not isinstance(data, list):
        raise Error("Invalid DDEV project list")
    return {item["name"]: item for item in data}


def volume_exists(name, database):
    # Listing must succeed. A Docker failure must never look like an absent DB.
    volumes = run(["docker", "volume", "ls", "--format", "{{.Name}}"])
    # DDEV's GetMariaDBVolumeName retains this suffix for MySQL as well.
    suffix = "mariadb" if database in ("mariadb", "mysql") else database
    return f"{name}-{suffix}" in volumes.splitlines()


def slug(value, length):
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:length].strip("-") or "wt"


def exclude(common, paths):
    path = common / "info/exclude"
    previous = path.read_text() if path.exists() else ""
    missing = ["/" + p for p in paths if "/" + p not in previous.splitlines()]
    if missing:
        atomic(path, previous.rstrip("\n") + "\n" + "\n".join(missing) + "\n")


def php_string(value):
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def drupal_files(root, docroot, config, name):
    if not config["sites"]:
        return []
    base = within(root, str(Path(docroot) / "sites"))
    sites_file = base / "sites.php"
    if not sites_file.is_file() or "sites.worktree-kit.php" not in sites_file.read_text():
        raise Error("Multisite requires the committed sites.php include from docs/drupal.md")
    hosts = {}
    for alias, site in config["sites"].items():
        directory = within(root, str(base.relative_to(root) / site["directory"]))
        settings = directory / "settings.php"
        if not settings.is_file() or "settings.worktree-kit.php" not in settings.read_text():
            raise Error(f"{settings} needs the committed settings include from docs/drupal.md")
        host = f"{alias + '.' if alias else ''}{name}.{config['tld']}"
        hosts[host] = site
    mapping = "<?php\n" + MARKER + "\n// Local host-to-site mapping.\n"
    for host, site in hosts.items():
        mapping += f"$sites[{php_string(host)}] = {php_string(site['directory'])};\n"
    settings = "<?php\n" + MARKER + "\n// Include LAST, after settings.ddev.php.\n"
    patterns = ["^" + re.escape(host) + "$" for host in hosts]
    settings += (
        "$settings['trusted_host_patterns'] = [" + ", ".join(map(php_string, patterns)) + "];\n"
    )
    for site in config["sites"].values():
        if "database" in site:
            settings += f"if ($site_path === {php_string('sites/' + site['directory'])}) {{\n"
            settings += f"  $databases['default']['default']['database'] = {php_string(site['database'])};\n}}\n"
    result = []
    for filename, content in [
        ("sites.worktree-kit.php", mapping),
        ("settings.worktree-kit.php", settings),
    ]:
        path = within(root, str(base.relative_to(root) / filename))
        managed(path, content)
        result.append(str(path.relative_to(root)))
    return result


def overrides(root, common, own, config, record, file_mounts=None):
    name = record["name"]
    override = {
        "override_config": True,
        "name": name,
        "project_tld": config["tld"],
        "additional_hostnames": [f"{alias}.{name}" for alias in config["sites"] if alias],
        "additional_fqdns": [],
        "host_db_port": "",
        "host_webserver_port": "",
        "host_https_port": "",
        "host_mailpit_port": "",
        "host_xhgui_port": "",
    }
    directory = within(root, ".ddev")
    for path in directory.glob("config.*.y*ml"):
        if path.name > OVERRIDE:
            raise Error(
                f"{path.name} loads after our override; refusing an ambiguous DDEV identity"
            )
    managed(within(root, ".ddev/" + OVERRIDE), MARKER + "\n" + dump_yaml(override))
    compose = {
        "services": {service: {"labels": {LABEL: record["token"]}} for service in ("web", "db")}
    }
    git_file = within(root, ".ddev/" + GIT_FILE)
    git_text = "gitdir: /mnt/worktree-kit/git/worktrees/" + own.name + "\n"
    if git_file.is_symlink():
        raise Error(f"Refusing symlink Git mount pointer: {git_file}")
    if git_file.exists() and git_file.read_text() != git_text:
        raise Error(f"Refusing an unowned Git mount pointer: {git_file}")
    if not git_file.exists():
        atomic(git_file, git_text)
    compose["services"]["web"]["volumes"] = [
        {
            "type": "bind",
            "source": str(common).replace("$", "$$"),
            "target": "/mnt/worktree-kit/git",
            "read_only": True,
            "bind": {"create_host_path": False},
        },
        {
            "type": "bind",
            "source": str(git_file).replace("$", "$$"),
            "target": "/var/www/html/.git",
            "read_only": True,
            "bind": {"create_host_path": False},
        },
    ]
    compose["services"]["web"]["volumes"].extend(file_mounts or [])
    managed(within(root, ".ddev/" + COMPOSE), MARKER + "\n" + dump_yaml(compose))


def bootstrap_stamp(config, composer_root):
    fingerprint = hashlib.sha256(json.dumps(config, sort_keys=True).encode())
    for filename in ("composer.json", "composer.lock"):
        path = composer_root / filename
        if path.is_file():
            fingerprint.update(path.read_bytes())
    return fingerprint.hexdigest()


def init(path, *, source=None, allow_main=False, start=False):
    root, common, own, main, entries = context(path)
    if own == common:
        if allow_main:
            return {"status": "skipped", "reason": "main checkout", "path": str(root)}
        raise Error("init requires an existing linked worktree; main checkout is protected")
    if not within(root, ".ddev/config.yaml").is_file():
        raise Error("Commit .ddev/config.yaml before creating worktrees")
    config = configuration(root, main)
    if start:
        config["auto_start"] = True
    selected = source or config["source"]
    if selected != "main" and not Path(selected).is_absolute():
        raise Error("source must be 'main' or an absolute checkout path")
    source_root = main if selected == "main" else Path(selected).resolve()
    if source_root == root or source_root not in {Path(e["worktree"]).resolve() for e in entries}:
        raise Error("Seed source must be a different registered checkout of this repository")
    start_lock = runtime(root)
    with lock(common / "ddev-worktree-kit/registry.lock"):
        registry = load_registry(common)
        key = own.name
        record = registry["environments"].get(key)
        current_projects = projects(root)
        if record and (record["path"] != str(root) or record["source"] != str(source_root)):
            raise Error(
                "Managed checkout moved or source changed; preserve its DB and inspect registry before reattaching"
            )
        if not record:
            digest = hashlib.sha256(f"{common}\0{own}\0{root}".encode()).hexdigest()[:12]
            name = config["name_template"].format(
                project=slug(main.name, 16), slug=slug(root.name, 20), hash=digest
            )
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,61}[a-z0-9]", name):
                raise Error("Rendered worktree name must be a DNS label of 2..63 characters")
            if name in current_projects:
                raise Error(f"DDEV name already registered: {name}; refusing adoption")
            record = {
                "name": name,
                "path": str(root),
                "git_dir": str(own),
                "source": str(source_root),
                "token": uuid.uuid4().hex,
                "phase": "planned",
                "seeded": False,
                "created": time.time(),
            }
            registry["environments"][key] = record
            save_registry(common, registry)
        name = record["name"]
        row = current_projects.get(name)
        if row and Path(row["approot"]).resolve() != root:
            raise Error("DDEV registry points this name at another checkout")
        for relative in config["local_files"]:
            original = within(source_root, relative)
            target = within(root, relative)
            if original.is_file() and not target.exists():
                if original.is_symlink() or target.is_symlink():
                    raise Error("local_files cannot copy symlinks")
                atomic(target, original.read_text())
        files, file_mounts = file_assets.prepare(
            root, source_root, config["files"], record.get("files", [])
        )
        record["files"] = files
        save_registry(common, registry)
        overrides(root, common, own, config, record, file_mounts)
        source_desc = ddev_json(source_root, "describe")
        if Path(source_desc["approot"]).resolve() != source_root or source_desc["name"] == name:
            raise Error("DDEV resolved the seed source to the wrong checkout")
        # A nested unregistered worktree resolves to the outer project until start
        # confirms it. DDEV's seed implementation validates DB type/version itself.
        nested = (
            any(
                root.is_relative_to(Path(p["approot"]).resolve())
                and root != Path(p["approot"]).resolve()
                for p in current_projects.values()
            )
            and row is None
        )
        description = source_desc if nested else ddev_json(root, "describe")
        if not nested and (
            description["name"] != name or Path(description["approot"]).resolve() != root
        ):
            raise Error("DDEV did not resolve the generated worktree identity")
        for field in ("database_type", "database_version"):
            if description[field] != source_desc[field]:
                raise Error("Source and target database type/version must match exactly")
        if description["database_type"] not in ("mariadb", "mysql"):
            raise Error("MVP snapshot verification supports MariaDB/MySQL only")
        generated = drupal_files(root, description["docroot"], config, name)
        for relative in set(record.get("drupal_paths", [])) - set(generated):
            stale = within(root, relative)
            if stale.exists():
                if stale.is_symlink() or not stale.read_text().startswith("<?php\n" + MARKER):
                    raise Error("Refusing to remove an unowned Drupal include: " + str(stale))
                stale.unlink()
        record["drupal_paths"] = generated
        save_registry(common, registry)
        exclude(
            common,
            [
                ".ddev/" + OVERRIDE,
                ".ddev/" + COMPOSE,
                ".ddev/" + GIT_FILE,
                *config["local_files"],
                *generated,
                *[mapping["path"] for mapping in files],
            ],
        )
        database = description["database_type"]
        if not config["auto_start"]:
            record["phase"] = "prepared"
            record["pending_start"] = True
            save_registry(common, registry)
            return dict(record)
        with lock(start_lock):
            exists = volume_exists(name, database)
            if exists and not record["seeded"]:
                raise Error(
                    "DB volume exists without a completed seed receipt. Inspect it; init will not reset or reseed it"
                )
            if not exists and record["seeded"]:
                raise Error(
                    "Previously seeded DB volume is missing; refusing automatic data replacement"
                )
            seed = None
            created_seed = False
            if not exists:
                directory = within(source_root, ".ddev/db_snapshots")
                if config["snapshot"] == "latest":
                    suffix = f"-{database}_{description['database_version']}."
                    candidates = [
                        p
                        for p in directory.glob("*")
                        if p.is_file()
                        and not p.is_symlink()
                        and suffix in p.name
                        and p.suffix in (".gz", ".zst", ".mbstream")
                    ]
                    if candidates:
                        seed = max(
                            candidates, key=lambda p: (p.stat().st_mtime_ns, p.name)
                        ).resolve()
                    elif not config["create_if_missing"]:
                        raise Error("No compatible latest snapshot; create_if_missing is false")
                if seed is None:
                    if source_desc["status"] != "running":
                        raise Error("Start the seed source DDEV manually before the first init")
                    snapshot_name = "wtk-" + record["token"]
                    run(
                        ["ddev", "--skip-hooks", "snapshot", "--name=" + snapshot_name], source_root
                    )
                    snapshots = list(directory.glob(snapshot_name + "-*"))
                    if (
                        len(snapshots) != 1
                        or not snapshots[0].is_file()
                        or snapshots[0].is_symlink()
                    ):
                        raise Error(
                            "Snapshot command did not produce exactly one named file; no fallback is used"
                        )
                    seed = snapshots[0].resolve()
                    created_seed = True
                record.update(
                    phase="starting", snapshot=str(seed), snapshot_created_by_manager=created_seed
                )
                save_registry(common, registry)
            arguments = ["ddev", "--skip-hooks", "start"]
            if seed:
                arguments.append("--seed-snapshot=" + str(seed))
            # Confirm only the documented nested-project prompt. stdin then closes.
            previous_noninteractive = os.environ.get("DDEV_NONINTERACTIVE")
            try:
                if nested:
                    os.environ["DDEV_NONINTERACTIVE"] = "false"
                run(arguments, root, input="y\n" if nested else "")
            finally:
                if previous_noninteractive is None:
                    os.environ.pop("DDEV_NONINTERACTIVE", None)
                else:
                    os.environ["DDEV_NONINTERACTIVE"] = previous_noninteractive
            actual = ddev_json(root, "describe")
            if actual["name"] != name or Path(actual["approot"]).resolve() != root:
                raise Error("Started DDEV identity does not match this worktree")
            if actual["docroot"] != description["docroot"]:
                raise Error(
                    "Nested worktree docroot differs from source; configure it as a sibling worktree"
                )
            # A successful process alone does not prove snapshot restore completed.
            probe = ["ddev", "exec", "--service", "db", "--raw", "--"]
            if database in ("mariadb", "mysql"):
                count = run(
                    probe
                    + [
                        "mysql",
                        "-uroot",
                        "-proot",
                        "-Nse",
                        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema NOT IN "
                        "('mysql','sys','performance_schema','information_schema')",
                    ],
                    root,
                )
                if not count.strip().isdigit() or int(count.strip()) == 0:
                    raise Error(
                        "Seeded database has no application tables; inspect it before continuing"
                    )
                for site in config["sites"].values():
                    if "database" in site:
                        site_count = run(
                            probe
                            + [
                                "mysql",
                                "-uroot",
                                "-proot",
                                "-Nse",
                                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='"
                                + site["database"]
                                + "'",
                            ],
                            root,
                        )
                        if not site_count.strip().isdigit() or int(site_count.strip()) == 0:
                            raise Error(
                                "Configured site database has no tables: " + site["database"]
                            )
            else:
                raise Error("MVP seed verification currently supports MariaDB/MySQL only")
            record.update(seeded=True, phase="started", url=actual["primary_url"])
            save_registry(common, registry)
            if seed and created_seed:
                # Delete only the exact snapshot created by this receipt, after verification.
                seed.unlink()
                record["snapshot_removed"] = True
                save_registry(common, registry)
        composer_root = within(root, config["composer_root"])
        stamp = bootstrap_stamp(config, composer_root)
        needs_bootstrap = record.get("bootstrap_stamp") != stamp
        if config["composer"] == "auto" and (composer_root / "composer.json").is_file():
            if (
                record.get("composer_stamp") != stamp
                or not (composer_root / "vendor/autoload.php").is_file()
            ):
                record["phase"] = "composer"
                save_registry(common, registry)
                container_root = "/var/www/html" + (
                    "/" + config["composer_root"] if config["composer_root"] else ""
                )
                run(
                    [
                        "ddev",
                        "composer",
                        "install",
                        "--working-dir=" + container_root,
                        "--no-interaction",
                        "--prefer-dist",
                    ],
                    root,
                )
                # Composer can create/update composer.lock during installation.
                stamp = bootstrap_stamp(config, composer_root)
                record["composer_stamp"] = stamp
                needs_bootstrap = True
                save_registry(common, registry)
        if needs_bootstrap:
            record["phase"] = "bootstrap"
            progress = record.get("bootstrap_progress", {})
            if progress.get("stamp") != stamp:
                progress = {"stamp": stamp, "next": 0}
                record["bootstrap_progress"] = progress
            save_registry(common, registry)
            for index, command in enumerate(config["bootstrap"]):
                if index < progress["next"]:
                    continue
                run(
                    command if command[0] == "ddev" else ["ddev", "exec", "--raw", "--", *command],
                    root,
                )
                progress["next"] = index + 1
                save_registry(common, registry)
            record["bootstrap_stamp"] = stamp
            record.pop("bootstrap_progress", None)
        record.update(phase="ready", updated=time.time())
        record.pop("pending_start", None)
        save_registry(common, registry)
        return dict(record)


def inventory(path):
    root, common, _, _, entries = context(path)
    registry = load_registry(common)
    registered = {Path(e["worktree"]).resolve() for e in entries}
    live_git_dirs = set()
    for entry in entries:
        checkout = Path(entry["worktree"])
        if checkout.exists():
            live_git_dirs.add(git(checkout, "rev-parse", "--absolute-git-dir"))
    rows = []
    for record in registry["environments"].values():
        location = Path(record["path"])
        retained = (
            location.exists()
            or location.resolve() in registered
            or record["git_dir"] in live_git_dirs
        )
        rows.append(
            {
                **record,
                "gc_candidate": not retained,
                "retained_reason": "checkout exists or Git still retains its worktree"
                if retained
                else None,
            }
        )
    return root, common, registry, rows


def status(path):
    root, common, _, _, _ = context(path)
    with lock(common / "ddev-worktree-kit/registry.lock"):
        _, _, _, rows = inventory(root)
        # Failure stays visible: status never turns a Docker outage into 'absent'.
        live = projects(root)
        return [
            {**row, "ddev_status": live.get(row["name"], {}).get("status", "unregistered")}
            for row in rows
        ]


def sync_files(path, apply=False):
    root, common, own, main, entries = context(path)
    if own == common:
        raise Error("Files sync requires a linked worktree; main is protected")
    config = configuration(root, main)
    with lock(common / "ddev-worktree-kit/registry.lock"):
        record = load_registry(common)["environments"].get(own.name)
        if not record or record["path"] != str(root):
            raise Error("Run init in this checkout before files sync")
        source = Path(record["source"])
        if source == root or source not in {Path(entry["worktree"]).resolve() for entry in entries}:
            raise Error("Files source is no longer a registered checkout of this repository")
        if (
            Path(git(source, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()
            != common
        ):
            raise Error("Files source now belongs to another repository")
        return file_assets.sync(root, source, config["files"], apply)


def delete_owned_project(root, row):
    """Delete only an exact DDEV registration owned by this recorded checkout."""
    project = projects(root).get(row["name"])
    containers = [
        item
        for item in run(
            [
                "docker",
                "ps",
                "-aq",
                "--filter",
                "label=com.docker.compose.project=ddev-" + row["name"],
            ]
        ).splitlines()
        if item
    ]
    if not project and not row["seeded"] and row["phase"] in ("planned", "prepared"):
        volumes = run(["docker", "volume", "ls", "--format", "{{.Name}}"])
        if not containers and not any(
            volume.startswith(row["name"] + "-") for volume in volumes.splitlines()
        ):
            # Nothing ever started: remove only our registry receipt. No Docker
            # resource or unknown/unregistered volume is touched.
            return
    if not project or Path(project["approot"]).resolve() != Path(row["path"]).resolve():
        raise Error("DDEV ownership cannot be verified; refusing deletion")
    for container in containers:
        labels = json.loads(run(["docker", "inspect", container]))[0]["Config"]["Labels"]
        if (
            labels.get("com.docker.compose.service") in ("web", "db")
            and labels.get(LABEL) != row["token"]
        ):
            raise Error("Container ownership does not match; refusing deletion")
    run(["ddev", "--skip-hooks", "delete", "--omit-snapshot", "--yes", row["name"]], root)


def teardown(path, apply=False, yes=False, automatic=False):
    """Remove DDEV resources before the host removes its Git worktree."""
    root, common, own, main, _ = context(path)
    if own == common:
        raise Error("Main checkout is protected from teardown")
    if apply and not yes:
        raise Error("Teardown requires both --apply and --yes")
    with lock(common / "ddev-worktree-kit/registry.lock"):
        registry = load_registry(common)
        row = registry["environments"].get(own.name)
        if not row:
            return {"status": "skipped", "reason": "not managed", "path": str(root)}
        if row["path"] != str(root):
            raise Error("Managed checkout moved; inspect ownership before teardown")
        if automatic and not configuration(root, main)["auto_delete"]:
            return {
                "status": "skipped",
                "reason": "cleanup.auto_delete is false",
                "name": row["name"],
            }
        if not apply:
            return {
                "status": "preview",
                "name": row["name"],
                "path": str(root),
                "delete_git": False,
            }
        with lock(runtime(root)):
            delete_owned_project(root, row)
            del registry["environments"][own.name]
            save_registry(common, registry)
        return {"status": "deleted", "name": row["name"], "path": str(root), "delete_git": False}


def require_repository(path, repository):
    if repository and context(path)[1] != context(repository)[1]:
        raise Error("Target belongs to another Git repository")


def gc(path, apply=False, yes=False):
    root, common, _, main, _ = context(path)
    if not configuration(root, main)["orphan_detection"]:
        raise Error("cleanup.orphan_detection is disabled in configuration")
    if apply and not yes:
        raise Error("Deletion requires both --apply and --yes; run gc first to review candidates")
    with lock(common / "ddev-worktree-kit/registry.lock"):
        _, _, registry, rows = inventory(root)
        if not apply:
            return rows
        start_lock = runtime(root)
        with lock(start_lock):
            for row in rows:
                if not row["gc_candidate"]:
                    continue
                # Recheck at deletion time under the same locks as init.
                _, _, _, fresh = inventory(root)
                if not next(item for item in fresh if item["token"] == row["token"])[
                    "gc_candidate"
                ]:
                    continue
                delete_owned_project(root, row)
                row["deleted"] = True
                key = next(
                    key
                    for key, value in registry["environments"].items()
                    if value["token"] == row["token"]
                )
                del registry["environments"][key]
                save_registry(common, registry)
        return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=VERSION)
    parser.add_argument("--path", default=".", help="checkout path (default: current directory)")
    parser.add_argument("--repository", help="limit callbacks to this Git repository")
    commands = parser.add_subparsers(dest="command", required=True)
    initializer = commands.add_parser("init", help="initialize an existing linked worktree")
    initializer.add_argument("--source", help="main or an absolute checkout path")
    initializer.add_argument(
        "--start", action="store_true", help="start despite worktree.auto_start=false"
    )
    hook = commands.add_parser("hook", help="Claude Code SessionStart adapter; reads JSON stdin")
    hook.add_argument("--provider", choices=["claude"], required=True)
    commands.add_parser("setup", help="Codex setup adapter; main checkout is a no-op")
    commands.add_parser("claude-create", help="native Claude WorktreeCreate adapter; JSON stdin")
    commands.add_parser("claude-remove", help="native Claude WorktreeRemove adapter; JSON stdin")
    commands.add_parser("status", help="JSON status of this repository's managed environments")
    cleanup = commands.add_parser("teardown", help="preview/remove DDEV only; keep the checkout")
    cleanup.add_argument("--apply", action="store_true")
    cleanup.add_argument("--yes", action="store_true")
    cleanup.add_argument("--automatic", action="store_true", help="respect cleanup.auto_delete")
    files_command = commands.add_parser("files", help="manage independent upload copies")
    files_commands = files_command.add_subparsers(dest="files_command", required=True)
    synchronizer = files_commands.add_parser("sync", help="preview source-to-worktree copy changes")
    synchronizer.add_argument("--apply", action="store_true")
    collector = commands.add_parser(
        "gc", help="preview orphan environments (no Git/files deletion)"
    )
    collector.add_argument("--apply", action="store_true")
    collector.add_argument("--yes", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command in ("claude-create", "claude-remove"):
            require_repository(args.path, args.repository)
            payload = json.load(sys.stdin)
            if args.command == "claude-create":
                print(claude_worktrees.create(payload, args.repository, Path(__file__).resolve()))
            else:
                print(
                    json.dumps(
                        claude_worktrees.remove(payload, args.repository, Path(__file__).resolve())
                    )
                )
        elif args.command == "hook":
            payload = json.load(sys.stdin)
            if payload.get("hook_event_name") != "SessionStart" or not isinstance(
                payload.get("cwd"), str
            ):
                raise Error("Expected Claude SessionStart payload with cwd")
            require_repository(payload["cwd"], args.repository)
            result = init(payload["cwd"], allow_main=True)
            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "SessionStart",
                            "additionalContext": "DDEV worktree environment: " + json.dumps(result),
                        }
                    }
                )
            )
        else:
            require_repository(args.path, args.repository)
            if args.command in ("init", "setup"):
                result = init(
                    args.path,
                    source=getattr(args, "source", None),
                    allow_main=args.command == "setup",
                    start=getattr(args, "start", False),
                )
            elif args.command == "status":
                result = status(args.path)
            elif args.command == "files":
                result = sync_files(args.path, args.apply)
            elif args.command == "teardown":
                result = teardown(args.path, args.apply, args.yes, args.automatic)
            else:
                result = gc(args.path, args.apply, args.yes)
            print(json.dumps(result, indent=2))
        return 0
    except (Error, OSError, ValueError, KeyError, TypeError) as error:
        print(f"wtk: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
