#!/usr/bin/env python3
"""Contract double for process-level tests; real Git is always used."""

import fcntl
import json
import os
import sys
from pathlib import Path

from config_io import load_yaml

home = Path(os.environ["WT_TEST_RUNTIME"])
# Each simulated daemon operation must update its state atomically even when
# two real CLI processes interleave commands during the concurrency scenario.
state_lock = (home / "runtime.lock").open("a+")
fcntl.flock(state_lock, fcntl.LOCK_EX)
path = home / "runtime.json"
state = json.loads(path.read_text())
args = sys.argv[1:]
program = Path(sys.argv[0]).name
with (home / "calls.jsonl").open("a") as stream:
    stream.write(json.dumps([program, str(Path.cwd()), args]) + "\n")


def finish(value="", raw=False):
    path.write_text(json.dumps(state))
    print(json.dumps({"raw": value}) if raw else value)
    raise SystemExit(0)


def fail(message):
    print(message, file=sys.stderr)
    raise SystemExit(1)


def config():
    root = Path.cwd()
    value = load_yaml((root / ".ddev/config.yaml").read_text())
    for file in sorted((root / ".ddev").glob("config.*.yaml")):
        body = "\n".join(line for line in file.read_text().splitlines() if not line.startswith("#"))
        value.update(load_yaml(body))
    return value


if program == "docker":
    if state.get("docker_failure"):
        fail("Docker unavailable")
    if args[0] == "info":
        finish("29.8.2")
    if args[:2] == ["volume", "ls"]:
        finish("\n".join(state["volumes"]))
    if args[0] == "ps":
        finish("\n".join(state.get("containers", {})))
    if args[0] == "inspect":
        finish(json.dumps([{"Config": {"Labels": state["containers"][args[1]]}}]))
    fail("unexpected docker contract: " + repr(args))

args = [a for a in args if a not in ("--json-output", "--skip-hooks")]
if args[0] == "version":
    finish({"DDEV version": state.get("version", "v1.25.4"), "global-ddev-dir": str(home)}, True)
if args[0] == "list":
    finish(list(state["projects"].values()), True)
if args[0] == "delete":
    name = args[-1]
    state["projects"].pop(name, None)
    state["volumes"] = [v for v in state["volumes"] if not v.startswith(name + "-")]
    finish()
cfg = config()
name = cfg["name"]
if args[0] == "describe":
    desc = {
        "name": name,
        "approot": str(Path.cwd()),
        "docroot": cfg.get("docroot", "web"),
        "database_type": cfg.get("database", {}).get("type", "mariadb"),
        "database_version": cfg.get("database", {}).get("version", "11.8"),
        "status": state["projects"].get(name, {}).get("status", "stopped"),
        "primary_url": f"https://{name}.{cfg.get('project_tld', 'ddev.site')}",
    }
    finish(desc, True)
if args[0] == "snapshot":
    if state.get("snapshot_failure"):
        fail("snapshot failed")
    snapshot = next(a.split("=", 1)[1] for a in args if a.startswith("--name="))
    target = Path.cwd() / ".ddev/db_snapshots"
    target.mkdir(exist_ok=True)
    database = cfg.get("database", {"type": "mariadb", "version": "11.8"})
    (target / (snapshot + "-" + database["type"] + "_" + database["version"] + ".zst")).write_text(
        "snapshot"
    )
    finish()
if args[0] == "start":
    if state.get("start_failure"):
        fail("start failed")
    # DDEV keeps the historical -mariadb volume name for both MariaDB and MySQL.
    database = cfg.get("database", {}).get("type", "mariadb")
    volume = name + ("-postgres" if database == "postgres" else "-mariadb")
    if volume not in state["volumes"]:
        state["volumes"].append(volume)
    state["projects"][name] = {"name": name, "approot": str(Path.cwd()), "status": "running"}
    finish()
if args[0] == "composer":
    if state.get("composer_failure"):
        fail("composer failed")
    container_root = next(a.split("=", 1)[1] for a in args if a.startswith("--working-dir="))
    composer_root = Path.cwd() / container_root.removeprefix("/var/www/html").lstrip("/")
    (composer_root / "composer.lock").write_text('{"packages":[]}')
    vendor = composer_root / "vendor"
    vendor.mkdir(exist_ok=True)
    (vendor / "autoload.php").write_text("<?php")
    finish()
if args[0] == "drush":
    finish()
if args[0] == "exec":
    if "mysql" in args:
        finish(state.get("table_count", "12"))
    if state.get("bootstrap_failure") or state.get("bootstrap_fail_command", "__none__") in args:
        fail("bootstrap failed")
    finish()
fail("unexpected ddev contract: " + repr(args))
