import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "worktree-kit"))
from config_io import dump_yaml, load_yaml

parser = argparse.ArgumentParser(
    description="Real DDEV smoke; only disposable fixture resources are deleted"
)
parser.add_argument("--report", type=Path)
arguments = parser.parse_args()
package = Path(__file__).resolve().parents[1]
manager = package / "worktree-kit/manager.py"
tag = uuid.uuid4().hex[:8]
base = Path(tempfile.mkdtemp(prefix="wtk-live-" + tag + "-")).resolve()
source = base / "source"
target = base / "detached worktree"
nested = source / ".claude/worktrees/nested"
name = "wtk-smoke-" + tag
names = [name]
results = []


def run(args, cwd=source, input=None, env=None):
    result = subprocess.run(
        [str(a) for a in args],
        cwd=cwd,
        input=input,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env={**os.environ, **(env or {})},
    )
    if result.returncode:
        raise RuntimeError(f"{args[:3]}: {result.stdout[-10000:]}")
    return result.stdout


def step(message):
    print(message, flush=True)
    results.append(message)


def cli(command="init", cwd=target, *args):
    output = run([sys.executable, manager, command, *args], cwd)
    return json.loads(output)


def http_json(url):
    with urllib.request.urlopen(url, timeout=20) as response:
        body = response.read().decode()
    try:
        return json.loads(body)
    except ValueError as error:
        logs = run(["ddev", "logs", "--tail=30"], target)
        raise RuntimeError(
            f"Invalid JSON at {url}: {body[:3000]}\nWeb logs: {logs[-5000:]}"
        ) from error


try:
    source.mkdir(parents=True)
    (source / ".ddev").mkdir()
    (source / "web").mkdir()
    # Executes the same include contract as Drupal; this is a small PHP routing
    # harness, not a claim of full Drupal kernel coverage.
    (source / "web/index.php").write_text("""<?php
$sites = [];
require __DIR__ . '/sites/sites.php';
$host = explode(':', $_SERVER['HTTP_HOST'])[0];
$directory = $sites[$host] ?? 'default';
$site_path = 'sites/' . $directory;
$settings = [];
$databases['default']['default'] = ['database' => 'db'];
require __DIR__ . '/' . $site_path . '/settings.php';
$trusted = false;
foreach ($settings['trusted_host_patterns'] ?? [] as $pattern) {
  $trusted = $trusted || preg_match('~' . $pattern . '~', $host) === 1;
}
$database = $databases['default']['default']['database'];
$pdo = new PDO('mysql:host=db;dbname=' . $database, 'db', 'db');
$query = $directory === 'french' ? 'SELECT id FROM multisite_proof' : 'SELECT value FROM seed_proof';
header('Content-Type: application/json');
echo json_encode(['site_path' => $site_path, 'database' => $database, 'trusted' => $trusted,
                  'proof' => $pdo->query($query)->fetchColumn()]);
""")
    sites = source / "web/sites"
    sites.mkdir()
    (sites / "sites.php").write_text("""<?php
$local = __DIR__ . '/sites.worktree-kit.php';
if (is_file($local)) { require $local; }
""")
    for directory in ("default", "french"):
        (sites / directory).mkdir()
        (sites / directory / "settings.php").write_text("""<?php
$local = __DIR__ . '/../settings.worktree-kit.php';
if (is_file($local)) { require $local; }
""")
        (sites / directory / "files").mkdir()
    (sites / "default/files/shared.txt").write_text("shared-source")
    (sites / "french/files/copy.txt").write_text("copy-source-v1")
    (source / "composer.json").write_text('{"name":"test/worktree-kit","require":{}}\n')
    (source / ".gitignore").write_text(
        "vendor/\n.claude/\n.ddev/*.local.yaml\n.ddev/.gitignore\n.ddev/db_snapshots/\nweb/sites/*/files/\n"
    )
    config = {
        "name": name,
        "type": "php",
        "docroot": "web",
        "php_version": "8.4",
        "database": {"type": "mariadb", "version": "11.8"},
        "performance_mode": "none",
        "use_dns_when_possible": True,
    }
    (source / ".ddev/config.yaml").write_text(json.dumps(config, indent=2) + "\n")
    document = load_yaml((package / "examples/worktree-kit.yaml").read_text())
    document["cleanup"]["auto_delete"] = True
    document["drupal"]["multisite"] = {
        "enabled": True,
        "sites": {
            "default": {"hostname": "", "database": "db"},
            "french": {"hostname": "fr", "database": "second_site"},
        },
    }
    document["setup"]["commands"] = [
        [
            "php",
            "-r",
            "$p='/var/www/html/bootstrap-proof'; file_put_contents($p, (int)(is_file($p) ? file_get_contents($p) : 0)+1);",
        ]
    ]
    document["files"]["mappings"] = [
        {"path": "web/sites/default/files", "strategy": "shared"},
        {"path": "web/sites/french/files", "strategy": "copy"},
    ]
    (source / ".ddev/worktree-kit.yaml").write_text(dump_yaml(document))
    run(["git", "init", "-b", "main"])
    run(["ddev", "add-on", "get", package])
    step("Local DDEV add-on installation passed")
    run(["git", "add", "."])
    run(
        [
            "git",
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ]
    )
    # Uncommitted project hooks must survive creation from an older branch.
    (source / ".claude").mkdir(exist_ok=True)
    (source / ".claude/settings.json").write_bytes(
        (package / "examples/claude.settings.json").read_bytes()
    )
    run(["ddev", "--skip-hooks", "start"])
    step("Disposable source DDEV started")
    run(
        [
            "ddev",
            "exec",
            "--service",
            "db",
            "--raw",
            "--",
            "mysql",
            "-uroot",
            "-proot",
            "-e",
            "CREATE TABLE db.seed_proof (id INT PRIMARY KEY, value VARCHAR(32)); INSERT INTO db.seed_proof VALUES (1, 'from-source'); CREATE DATABASE second_site; GRANT ALL ON second_site.* TO 'db'@'%'; GRANT ALL ON second_site.* TO 'db'@'localhost'; CREATE TABLE second_site.multisite_proof (id INT); INSERT INTO second_site.multisite_proof VALUES (42);",
        ]
    )
    original = (source / ".ddev/config.yaml").read_bytes()
    run(["git", "worktree", "add", "--detach", target])
    record = json.loads(
        run(
            ["bash", source / ".ddev/worktree-kit/codex-setup.sh"],
            env={"CODEX_WORKTREE_PATH": str(target)},
        )
    )
    names.append(record["name"])
    step("Detached worktree with spaces initialized: " + record["name"])
    seed = run(
        [
            "ddev",
            "exec",
            "--service",
            "db",
            "--raw",
            "--",
            "mysql",
            "-uroot",
            "-proot",
            "-Nse",
            "SELECT value FROM db.seed_proof WHERE id=1; SELECT id FROM second_site.multisite_proof",
        ],
        target,
    )
    assert "from-source" in seed and "42" in seed, seed
    assert (target / "vendor/autoload.php").is_file()
    assert (target / "bootstrap-proof").read_text() == "1"
    shared = "/var/www/html/web/sites/default/files/shared.txt"
    assert (
        run(
            ["ddev", "exec", "--raw", "--", "php", "-r", f"echo file_get_contents('{shared}');"],
            target,
        ).strip()
        == "shared-source"
    )
    run(
        [
            "ddev",
            "exec",
            "--raw",
            "--",
            "php",
            "-r",
            f"file_put_contents('{shared}', 'shared-worktree');",
        ],
        target,
    )
    assert (source / "web/sites/default/files/shared.txt").read_text() == "shared-worktree"
    copy = target / "web/sites/french/files/copy.txt"
    assert copy.read_text() == "copy-source-v1"
    copy.write_text("worktree-copy")
    (copy.parent / "extra.txt").write_text("keep")
    original_copy = source / "web/sites/french/files/copy.txt"
    assert original_copy.read_text() == "copy-source-v1"
    original_copy.write_text("copy-source-v2")
    step("Shared Docker bind read/write and independent initial copy passed")
    git_read = run(
        ["ddev", "exec", "--raw", "--", "git", "rev-parse", "--is-inside-work-tree"], target
    )
    assert git_read.strip() == "true", git_read
    git_write = subprocess.run(
        ["ddev", "exec", "--raw", "--", "git", "config", "--local", "wtk.test", "blocked"],
        cwd=target,
        text=True,
        capture_output=True,
    )
    assert git_write.returncode != 0, "Container must not write shared Git metadata"
    step("Read-only Git metadata works in the web container")
    assert original == (source / ".ddev/config.yaml").read_bytes()
    step("Snapshot copied both databases; Composer and bootstrap passed; source config unchanged")
    run(
        [
            "ddev",
            "exec",
            "--service",
            "db",
            "--raw",
            "--",
            "mysql",
            "-uroot",
            "-proot",
            "-e",
            "UPDATE db.seed_proof SET value='target-kept' WHERE id=1",
        ],
        target,
    )
    second = json.loads(
        run(
            ["bash", source / ".ddev/worktree-kit/codex-setup.sh"],
            env={"CODEX_WORKTREE_PATH": str(target)},
        )
    )
    assert second["name"] == record["name"]
    assert (target / "bootstrap-proof").read_text() == "1", "Bootstrap unexpectedly repeated"
    assert copy.read_text() == "worktree-copy", "init must not resync an independent copy"
    preview = cli("files", target, "sync")
    assert preview[0]["files_to_copy"] == 1 and not preview[0]["applied"], preview
    assert copy.read_text() == "worktree-copy"
    cli("files", target, "sync", "--apply")
    assert copy.read_text() == "copy-source-v2"
    assert (copy.parent / "extra.txt").read_text() == "keep"
    step("Manual file sync preview/apply updated the copy and preserved extra files")
    seed = run(
        [
            "ddev",
            "exec",
            "--service",
            "db",
            "--raw",
            "--",
            "mysql",
            "-uroot",
            "-proot",
            "-Nse",
            "SELECT value FROM db.seed_proof WHERE id=1",
        ],
        target,
    )
    assert "target-kept" in seed, seed
    source_seed = run(
        [
            "ddev",
            "exec",
            "--service",
            "db",
            "--raw",
            "--",
            "mysql",
            "-uroot",
            "-proot",
            "-Nse",
            "SELECT value FROM db.seed_proof WHERE id=1",
        ]
    )
    assert "from-source" in source_seed, source_seed
    step("Second init preserved target DB changes and source DB")
    mapping = http_json(record["url"].replace("https://", "http://"))
    assert mapping == {
        "site_path": "sites/default",
        "database": "db",
        "trusted": True,
        "proof": "target-kept",
    }, mapping
    french_url = record["url"].replace("https://", "http://fr.")
    mapping = http_json(french_url)
    assert mapping["site_path"] == "sites/french" and mapping["database"] == "second_site", mapping
    assert mapping["trusted"] and int(mapping["proof"]) == 42, mapping
    step(
        "Unique URLs and executable PHP multisite includes routed both hosts to their own site directories/databases"
    )
    installed_status = json.loads(run(["ddev", "wtk", "status"], target))
    assert installed_status[0]["name"] == record["name"]
    step("Installed DDEV host command status returned the managed environment")
    created = run(
        ["bash", source / ".ddev/worktree-kit/claude-worktree-create.sh"],
        input=json.dumps(
            {"hook_event_name": "WorktreeCreate", "cwd": str(source), "name": "nested"}
        ),
    ).strip()
    assert created == str(nested), created
    assert (nested / ".claude/settings.local.json").is_file()
    hook = json.loads(
        run(
            ["bash", source / ".ddev/worktree-kit/claude-session-start.sh"],
            input=json.dumps({"hook_event_name": "SessionStart", "cwd": str(nested)}),
        )
    )
    nested_record = json.loads(hook["hookSpecificOutput"]["additionalContext"].split(": ", 1)[1])
    names.append(nested_record["name"])
    assert nested_record["name"] != record["name"]
    step(
        "Claude WorktreeCreate created Git + DDEV, returned only its path; SessionStart resumed idempotently"
    )
    preview = cli("gc", source)
    assert not any(row["gc_candidate"] for row in preview)
    cleanup = json.loads(
        run(
            ["bash", source / ".ddev/worktree-kit/codex-cleanup.sh"],
            env={"CODEX_WORKTREE_PATH": str(target)},
        )
    )
    assert cleanup["status"] == "deleted" and not cleanup["delete_git"]
    assert (target / ".git").is_file()
    assert (source / "web/sites/default/files/shared.txt").read_text() == "shared-worktree"
    step(
        "Codex cleanup callback removed only target DDEV while checkout and shared source remained"
    )
    run(["git", "worktree", "remove", "--force", target])
    assert len(cli("status", source)) == 1
    removed = json.loads(
        run(
            ["bash", source / ".ddev/worktree-kit/claude-worktree-remove.sh"],
            input=json.dumps(
                {
                    "hook_event_name": "WorktreeRemove",
                    "cwd": str(source),
                    "worktree_path": str(nested),
                }
            ),
        )
    )
    assert removed["status"] == "removed" and removed["ddev"] == "deleted", removed
    assert not nested.exists()
    assert run(["git", "branch", "--list", "worktree-nested"]).strip() == "worktree-nested"
    assert cli("status", source) == []
    assert (source / "web/sites/default/files/shared.txt").read_text() == "shared-worktree"
    step(
        "Claude WorktreeRemove removed owned DDEV + checkout, preserved branch and shared source files"
    )
    status = "PASS"
except Exception as error:
    status = "FAIL"
    print(str(error), flush=True)
    results.append(str(error))
finally:
    # Exact names created by this fixture only; never scan/delete other projects.
    registry_file = source / ".git/ddev-worktree-kit/registry.json"
    if registry_file.is_file():
        registry = json.loads(registry_file.read_text())
        for row in registry["environments"].values():
            if Path(row["path"]).is_relative_to(base) and row["name"] not in names:
                names.append(row["name"])
    cleanup_ok = True
    for fixture_name in reversed(names):
        try:
            run(["ddev", "--skip-hooks", "delete", "--omit-snapshot", "--yes", fixture_name])
        except Exception as cleanup_error:
            cleanup_ok = False
            print("cleanup:", str(cleanup_error), flush=True)
    result = {
        "status": status,
        "fixture": str(base),
        "scenarios": results,
        "time": time.time(),
        "cleanup_ok": cleanup_ok,
    }
    if arguments.report:
        arguments.report.write_text(json.dumps(result, indent=2))
    print("Live verification: " + status, flush=True)
    if status != "PASS" or not cleanup_ok:
        raise SystemExit(1)
    import shutil

    shutil.rmtree(base)
