import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib

PACKAGE = Path(__file__).resolve().parents[1]
MANAGER = PACKAGE / "worktree-kit/manager.py"
sys.path.insert(0, str(MANAGER.parent))
spec = importlib.util.spec_from_file_location("manager", MANAGER)
manager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manager)


class ManagerTests(unittest.TestCase):
    def test_installed_claude_template_executes_native_lifecycle(self):
        self.install_native_claude()
        template = json.loads(
            (self.main / ".ddev/worktree-kit/templates/claude.settings.json").read_text()
        )
        self.assertTrue(template.pop("#ddev-generated"))
        # The agent merges only hooks; install metadata must not become a client setting.
        (self.main / ".claude/settings.json").write_text(json.dumps(template))
        target = self.main / ".claude/worktrees/from-template"
        for event in ("WorktreeCreate", "WorktreeRemove"):
            command = template["hooks"][event][0]["hooks"][0]["command"]
            payload = {
                "hook_event_name": event,
                "cwd": str(self.main),
                "name": "from-template",
                "worktree_path": str(target),
            }
            result = subprocess.run(
                ["bash", "-c", command],
                cwd=self.target,
                env=self.env,
                input=json.dumps(payload),
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            if event == "WorktreeCreate":
                self.assertEqual(result.stdout.strip(), str(target))
                self.assertTrue((target / ".git").exists())
        self.assertFalse(target.exists())
        self.assertIn("worktree-from-template", self.git(self.main, "branch", "--list"))

    def test_installed_codex_template_uses_assigned_worktree_from_any_checkout(self):
        self.install_callbacks()
        self.configure({"cleanup": {"auto_delete": True}})
        template = tomllib.loads(
            (self.main / ".ddev/worktree-kit/templates/codex-environment.toml").read_text()
        )
        env = {**self.env, "CODEX_WORKTREE_PATH": str(self.target)}
        for event in ("setup", "cleanup"):
            result = subprocess.run(
                ["bash", "-c", template[event]["script"]],
                cwd=self.target,
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            record = json.loads(result.stdout)
            self.assertEqual(
                record.get("phase", record.get("status")),
                "ready" if event == "setup" else "deleted",
            )
        self.assertTrue((self.target / ".git").exists())

    def install_native_claude(self):
        self.install_callbacks()
        (self.main / manager.CONFIG).write_text(
            manager.dump_yaml({"cleanup": {"auto_delete": True}})
        )
        directory = self.main / ".claude"
        directory.mkdir(exist_ok=True)
        shutil.copy2(PACKAGE / "examples/claude.settings.json", directory / "settings.json")

    def native_claude(self, event, *, name=None, target=None, ok=True, cwd=None):
        payload = {"hook_event_name": event, "cwd": str(cwd or self.main)}
        if name is not None:
            payload["name"] = name
        if target is not None:
            payload["worktree_path"] = str(target)
        filename = (
            "claude-worktree-create.sh"
            if event == "WorktreeCreate"
            else "claude-worktree-remove.sh"
        )
        result = subprocess.run(
            ["bash", str(self.main / ".ddev/worktree-kit" / filename)],
            cwd=self.main,
            env=self.env,
            input=json.dumps(payload),
            text=True,
            capture_output=True,
        )
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
            return result.stdout.strip()
        self.assertNotEqual(result.returncode, 0, result.stdout)
        return result.stderr

    def test_claude_native_create_returns_only_path_and_bootstraps_hooks(self):
        self.install_native_claude()
        output = self.native_claude("WorktreeCreate", name="feature-a")
        path = self.main / ".claude/worktrees/feature-a"
        self.assertEqual(output, str(path))
        self.assertEqual(self.git(path, "branch", "--show-current"), "worktree-feature-a")
        status = self.cli("status", cwd=path)
        self.assertEqual(status[0]["phase"], "ready")
        local = json.loads((path / ".claude/settings.local.json").read_text())
        self.assertIn("WorktreeCreate", local["hooks"])
        self.assertIn("WorktreeRemove", local["hooks"])
        self.assertEqual(self.native_claude("WorktreeCreate", name="feature-a"), str(path))
        self.assertEqual(len(self.calls("snapshot")), 1)

    def test_claude_native_remove_cleans_ddev_and_owned_git_preserving_branch(self):
        self.install_native_claude()
        path = Path(self.native_claude("WorktreeCreate", name="feature-a"))
        (path / "agent-changes.txt").write_text(
            "native removal decision discards this owned checkout"
        )
        result = json.loads(self.native_claude("WorktreeRemove", target=path))
        self.assertEqual(result["status"], "removed")
        self.assertEqual(result["ddev"], "deleted")
        self.assertFalse(path.exists())
        self.assertEqual(
            self.git(self.main, "branch", "--list", "worktree-feature-a").strip(),
            "worktree-feature-a",
        )
        self.assertIn("source", json.loads(self.state.read_text())["projects"])
        self.assertEqual(
            json.loads(self.native_claude("WorktreeRemove", target=path))["status"], "skipped"
        )

    def test_claude_native_refuses_unowned_checkout_and_main(self):
        self.install_native_claude()
        unknown = self.main / ".claude/worktrees/unmanaged"
        self.git(self.main, "worktree", "add", "--detach", str(unknown))
        self.assertIn("not owned", self.native_claude("WorktreeCreate", name="unmanaged", ok=False))
        self.assertIn("not owned", self.native_claude("WorktreeRemove", target=unknown, ok=False))
        self.native_claude("WorktreeRemove", target=self.main, ok=False)
        self.assertTrue((unknown / ".git").exists())
        self.assertFalse(self.calls("delete"))

    def test_claude_native_refuses_path_traversal_and_symlink(self):
        self.install_native_claude()
        self.assertIn(
            "safe single", self.native_claude("WorktreeCreate", name="../escape", ok=False)
        )
        parent = self.main / ".claude/worktrees"
        parent.mkdir()
        (parent / "link").symlink_to(self.target, target_is_directory=True)
        self.assertIn("symlink", self.native_claude("WorktreeCreate", name="link", ok=False))
        self.native_claude("WorktreeRemove", target=parent / "link", ok=False)
        self.assertTrue(self.target.exists())
        self.assertFalse(self.calls("start"))

    def test_claude_native_preserves_checkout_when_ddev_cleanup_fails(self):
        self.install_native_claude()
        path = Path(self.native_claude("WorktreeCreate", name="feature-a"))
        self.change_state(docker_failure=True)
        self.native_claude("WorktreeRemove", target=path, ok=False)
        self.assertTrue((path / ".git").exists())
        self.change_state(docker_failure=False)
        self.native_claude("WorktreeRemove", target=path)
        self.assertFalse(path.exists())

    def test_claude_native_owner_marker_blocks_path_reuse(self):
        self.install_native_claude()
        path = Path(self.native_claude("WorktreeCreate", name="feature-a"))
        self.git(self.main, "worktree", "remove", "--force", str(path))
        self.git(self.main, "worktree", "add", "--detach", str(path))
        self.assertIn("marker", self.native_claude("WorktreeRemove", target=path, ok=False))
        self.assertTrue((path / ".git").exists())
        self.assertFalse(self.calls("delete"))

    def test_claude_native_respects_git_lock_before_ddev_cleanup(self):
        self.install_native_claude()
        path = Path(self.native_claude("WorktreeCreate", name="feature-a"))
        self.git(self.main, "worktree", "lock", str(path))
        self.assertIn("locked", self.native_claude("WorktreeRemove", target=path, ok=False))
        self.assertFalse(self.calls("delete"))

    def test_claude_native_does_not_adopt_stale_manual_ddev_path(self):
        self.install_native_claude()
        path = self.main / ".claude/worktrees/feature-a"
        self.git(self.main, "worktree", "add", "--detach", str(path))
        self.cli("init", cwd=path)
        self.git(self.main, "worktree", "remove", "--force", str(path))
        self.assertIn(
            "earlier DDEV", self.native_claude("WorktreeCreate", name="feature-a", ok=False)
        )
        self.assertFalse(path.exists())
        self.assertFalse(self.calls("delete"))

    def test_claude_native_reuses_existing_branch_without_deleting_it(self):
        self.install_native_claude()
        self.git(self.main, "branch", "worktree-review")
        path = Path(self.native_claude("WorktreeCreate", name="review"))
        self.assertEqual(self.git(path, "branch", "--show-current"), "worktree-review")
        self.native_claude("WorktreeRemove", target=path)
        self.assertEqual(
            self.git(self.main, "branch", "--list", "worktree-review"), "worktree-review"
        )

    def test_claude_native_preserves_nested_registered_worktree(self):
        self.install_native_claude()
        path = Path(self.native_claude("WorktreeCreate", name="parent"))
        child = path / "independent-child"
        self.git(self.main, "worktree", "add", "--detach", str(child))
        (child / "unsaved.txt").write_text("preserve me")
        self.assertIn("Nested", self.native_claude("WorktreeRemove", target=path, ok=False))
        self.assertEqual((child / "unsaved.txt").read_text(), "preserve me")
        self.assertFalse(self.calls("delete"))

    def test_claude_native_preserves_nested_foreign_repository(self):
        self.install_native_claude()
        path = Path(self.native_claude("WorktreeCreate", name="parent"))
        child = path / "foreign-repo"
        child.mkdir()
        self.git(child, "init")
        (child / "unsaved.txt").write_text("preserve me")
        self.assertIn("Nested", self.native_claude("WorktreeRemove", target=path, ok=False))
        self.assertTrue((child / "unsaved.txt").is_file())
        self.assertFalse(self.calls("delete"))

    def test_claude_native_setup_failure_is_visible_and_owned_checkout_retained(self):
        self.install_native_claude()
        self.change_state(snapshot_failure=True)
        self.assertIn(
            "retained for retry", self.native_claude("WorktreeCreate", name="failed", ok=False)
        )
        path = self.main / ".claude/worktrees/failed"
        self.assertTrue((path / ".git").exists())
        self.change_state(snapshot_failure=False)
        self.assertEqual(self.native_claude("WorktreeCreate", name="failed"), str(path))

    def test_claude_native_remove_cleans_prepared_without_starting(self):
        self.install_native_claude()
        (self.main / manager.CONFIG).write_text(
            manager.dump_yaml({"worktree": {"auto_start": False}, "cleanup": {"auto_delete": True}})
        )
        path = Path(self.native_claude("WorktreeCreate", name="prepared"))
        result = json.loads(self.native_claude("WorktreeRemove", target=path))
        self.assertEqual(result["status"], "removed")
        self.assertFalse(self.calls("start"))
        self.assertFalse(self.calls("delete"))

    def test_claude_native_remove_rechecks_ddev_after_cleanup_retry(self):
        self.install_native_claude()
        path = Path(self.native_claude("WorktreeCreate", name="retry"))
        self.cli("teardown", "--apply", "--yes", cwd=path)
        receipt_path = self.main / ".git/ddev-worktree-kit/claude-worktrees.json"
        state = json.loads(receipt_path.read_text())
        state["worktrees"][str(path)]["state"] = "environment_removed"
        receipt_path.write_text(json.dumps(state))
        self.cli("init", cwd=path)
        self.native_claude("WorktreeRemove", target=path)
        self.assertEqual(len(self.calls("delete")), 2)
        self.assertEqual(self.cli("status", cwd=self.main), [])

    def test_teardown_unstarted_receipt_refuses_unknown_runtime_volume(self):
        self.configure({"worktree": {"auto_start": False}})
        record = self.cli("init")
        self.change_state(volumes=[record["name"] + "-mariadb"])
        self.assertIn("ownership", self.cli("teardown", "--apply", "--yes", ok=False))
        self.assertFalse(self.calls("delete"))

    def install_callbacks(self):
        manifest = manager.load_yaml((PACKAGE / "install.yaml").read_text())
        for relative in manifest["project_files"]:
            destination = self.main / ".ddev" / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(PACKAGE / relative, destination)

    def callback(self, name, target=None, *, input=None, ok=True):
        env = {**self.env}
        env.pop("CODEX_WORKTREE_PATH", None)
        if target is not None:
            env["CODEX_WORKTREE_PATH"] = str(target)
        result = subprocess.run(
            ["bash", str(self.main / ".ddev/worktree-kit" / name)],
            cwd=self.main,
            env=env,
            input=input,
            text=True,
            capture_output=True,
        )
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        return result.stderr

    def test_teardown_preview_requires_confirmation_and_keeps_git(self):
        self.cli("init")
        self.assertEqual(self.cli("teardown")["status"], "preview")
        self.cli("teardown", "--apply", ok=False)
        self.assertFalse(self.calls("delete"))
        self.assertTrue((self.target / ".git").exists())

    def test_teardown_deletes_only_ddev_and_is_idempotent(self):
        record = self.cli("init")
        before = self.git(self.target, "rev-parse", "HEAD")
        result = self.cli("teardown", "--apply", "--yes")
        self.assertEqual(result["status"], "deleted")
        self.assertFalse(result["delete_git"])
        self.assertEqual(self.git(self.target, "rev-parse", "HEAD"), before)
        state = json.loads(self.state.read_text())
        self.assertIn("source", state["projects"])
        self.assertNotIn(record["name"], state["projects"])
        self.assertEqual(self.cli("teardown", "--apply", "--yes")["status"], "skipped")

    def test_teardown_main_and_unmanaged_are_protected(self):
        self.assertIn(
            "protected", self.cli("teardown", "--apply", "--yes", cwd=self.main, ok=False)
        )
        self.assertEqual(self.cli("teardown", "--apply", "--yes")["reason"], "not managed")
        self.assertFalse(self.calls("delete"))

    def test_teardown_refuses_wrong_ddev_registration(self):
        record = self.cli("init")
        state = json.loads(self.state.read_text())
        state["projects"][record["name"]]["approot"] = str(self.main)
        self.state.write_text(json.dumps(state))
        self.assertIn("ownership", self.cli("teardown", "--apply", "--yes", ok=False))
        self.assertFalse(self.calls("delete"))

    def test_teardown_refuses_wrong_container_owner(self):
        self.cli("init")
        self.change_state(
            containers={"container1": {"com.docker.compose.service": "db", manager.LABEL: "other"}}
        )
        self.assertIn("ownership", self.cli("teardown", "--apply", "--yes", ok=False))
        self.assertFalse(self.calls("delete"))

    def test_automatic_teardown_respects_explicit_policy(self):
        self.cli("init")
        result = self.cli("teardown", "--automatic", "--apply", "--yes")
        self.assertEqual(result["reason"], "cleanup.auto_delete is false")
        self.assertFalse(self.calls("delete"))
        self.configure({"cleanup": {"auto_delete": True}})
        self.assertEqual(
            self.cli("teardown", "--automatic", "--apply", "--yes")["status"], "deleted"
        )

    def test_codex_callbacks_use_target_env_when_cwd_is_main(self):
        self.install_callbacks()
        self.configure({"cleanup": {"auto_delete": True}})
        record = self.callback("codex-setup.sh", self.target)
        self.assertEqual(record["path"], str(self.target))
        self.assertEqual(record["phase"], "ready")
        cleanup = self.callback("codex-cleanup.sh", self.target)
        self.assertEqual(cleanup["name"], record["name"])
        self.assertEqual(cleanup["status"], "deleted")
        self.assertTrue((self.target / ".git").exists())
        self.assertIn("source", json.loads(self.state.read_text())["projects"])

    def test_codex_cleanup_missing_env_and_main_never_delete(self):
        self.install_callbacks()
        self.callback("codex-cleanup.sh", ok=False)
        self.callback("codex-cleanup.sh", self.main, ok=False)
        self.assertFalse(self.calls("delete"))

    def test_callback_repository_scope_rejects_other_repo(self):
        self.install_callbacks()
        other = self.base / "other repo"
        other.mkdir()
        self.git(other, "init", "-b", "main")
        self.assertIn("another Git", self.callback("codex-setup.sh", other, ok=False))
        self.assertFalse(self.calls("start"))

    def test_claude_callback_uses_payload_cwd_and_scope(self):
        self.install_callbacks()
        output = self.callback(
            "claude-session-start.sh",
            input=json.dumps({"hook_event_name": "SessionStart", "cwd": str(self.target)}),
        )
        context = json.loads(output["hookSpecificOutput"]["additionalContext"].split(": ", 1)[1])
        self.assertEqual(context["path"], str(self.target))
        self.assertEqual(context["phase"], "ready")
        other = self.base / "other repo"
        other.mkdir()
        self.git(other, "init", "-b", "main")
        self.assertIn(
            "another Git",
            self.callback(
                "claude-session-start.sh",
                input=json.dumps({"hook_event_name": "SessionStart", "cwd": str(other)}),
                ok=False,
            ),
        )

    def mysql_fixture(self):
        config = {**self.base_config, "database": {"type": "mysql", "version": "8.0"}}
        for root in (self.main, self.target):
            (root / ".ddev/config.yaml").write_text(manager.dump_yaml(config))

    def test_mysql_repeat_init_uses_ddev_mariadb_volume(self):
        self.mysql_fixture()
        first = self.cli("init")
        state = json.loads(self.state.read_text())
        self.assertIn(first["name"] + "-mariadb", state["volumes"])
        self.assertNotIn(first["name"] + "-mysql", state["volumes"])
        second = self.cli("init")
        self.assertEqual(second["phase"], "ready")
        self.assertEqual(second["name"], first["name"])
        self.assertEqual(len(self.calls("snapshot")), 1)
        self.assertEqual(len(self.calls("composer")), 1)

    def test_mysql_unowned_mariadb_volume_is_refused_before_snapshot(self):
        self.mysql_fixture()
        self.configure({"worktree": {"auto_start": False}})
        record = self.cli("init")
        self.change_state(volumes=["source-mariadb", record["name"] + "-mariadb"])
        self.assertIn("completed seed receipt", self.cli("init", "--start", ok=False))
        self.assertFalse(self.calls("snapshot"))
        self.assertFalse(self.calls("start"))

    def test_ddev_ownership_marker_survives_formatting(self):
        manifest = manager.load_yaml((PACKAGE / "install.yaml").read_text())
        for relative in manifest["project_files"]:
            self.assertIn("#ddev-generated", (PACKAGE / relative).read_text()[:200], relative)

    def upload_source(self, relative="web/sites/default/files"):
        source = self.main / relative
        source.mkdir(parents=True)
        (source / "image.txt").write_text("source-v1")
        (source / ".gitignore").write_text("*\n")
        return source

    def test_public_yaml_sections_and_comments(self):
        text = (PACKAGE / "examples/worktree-kit.yaml").read_text()
        (self.target / manager.CONFIG).write_text("# team configuration\n" + text)
        result = self.cli("init")
        self.assertEqual(result["phase"], "ready")
        generated = (self.target / ".ddev" / manager.OVERRIDE).read_text()
        self.assertIn("name: " + result["name"], generated)
        self.assertNotIn('"override_config"', generated)

    def test_yaml_composer_off_is_a_string(self):
        (self.target / manager.CONFIG).write_text("version: 1\ncomposer: off\n")
        self.cli("init")
        self.assertFalse(self.calls("composer"))

    def test_yaml_duplicates_and_unsafe_tags_are_rejected(self):
        for text in (
            "version: 1\nversion: 2\n",
            "!!python/object/apply:os.system ['touch unsafe-proof']",
        ):
            (self.target / manager.CONFIG).write_text(text)
            self.cli("init", ok=False)
        self.assertFalse((self.target / "unsafe-proof").exists())
        self.assertFalse(self.calls("start"))

    def test_legacy_json_works_but_dual_configs_fail(self):
        (self.target / manager.LEGACY_CONFIG).write_text('{"version":1,"composer":"off"}')
        self.cli("init")
        self.assertFalse(self.calls("composer"))
        self.configure({"version": 1})
        self.assertIn("Both YAML", self.cli("init", ok=False))

    def test_auto_start_false_and_explicit_start(self):
        self.configure({"worktree": {"auto_start": False}})
        self.assertEqual(self.cli("init")["phase"], "prepared")
        self.assertFalse(self.calls("snapshot"))
        self.assertFalse(self.calls("start"))
        self.assertEqual(self.cli("init", "--start")["phase"], "ready")

    def test_latest_snapshot_is_used_and_never_deleted(self):
        directory = self.main / ".ddev/db_snapshots"
        directory.mkdir()
        snapshot = directory / "manual-mariadb_11.8.zst"
        snapshot.write_text("manual snapshot")
        self.configure({"database": {"snapshot": "latest", "create_if_missing": False}})
        record = self.cli("init")
        self.assertFalse(record["snapshot_created_by_manager"])
        self.assertTrue(snapshot.exists())
        self.assertFalse(self.calls("snapshot"))
        self.assertIn("--seed-snapshot=" + str(snapshot), self.calls("start")[0][2])

    def test_latest_missing_and_creation_disabled(self):
        self.configure({"database": {"snapshot": "latest", "create_if_missing": False}})
        self.assertIn("No compatible", self.cli("init", ok=False))
        self.assertFalse(self.calls("snapshot"))
        self.assertFalse(self.calls("start"))

    def test_latest_can_create_when_missing(self):
        self.configure({"database": {"snapshot": "latest", "create_if_missing": True}})
        self.assertTrue(self.cli("init")["snapshot_created_by_manager"])
        self.assertEqual(len(self.calls("snapshot")), 1)

    def test_setup_ddev_command_and_name_template(self):
        self.configure(
            {"worktree": {"name": "test-{hash}"}, "setup": {"commands": ["ddev drush cr"]}}
        )
        record = self.cli("init")
        self.assertTrue(record["name"].startswith("test-"))
        self.assertEqual(len(self.calls("drush")), 1)

    def test_shared_mount_is_explicit_and_does_not_copy(self):
        source = self.upload_source()
        self.configure(
            {
                "files": {
                    "mappings": [
                        {"path": "web/sites/default/files", "strategy": "shared", "read_only": True}
                    ]
                }
            }
        )
        record = self.cli("init")
        compose = manager.load_yaml((self.target / ".ddev" / manager.COMPOSE).read_text())
        mount = next(v for v in compose["services"]["web"]["volumes"] if v["source"] == str(source))
        self.assertTrue(mount["read_only"])
        self.assertEqual(mount["target"], "/var/www/html/web/sites/default/files")
        self.assertEqual(record["files"][0]["strategy"], "shared")
        self.assertFalse((self.target / "web/sites/default/files/image.txt").exists())
        self.assertEqual((source / "image.txt").read_text(), "source-v1")

    def test_copy_and_manual_sync_preserve_source_and_extra_target_files(self):
        source = self.upload_source()
        self.configure(
            {"files": {"strategy": "copy", "mappings": [{"path": "web/sites/default/files"}]}}
        )
        self.cli("init")
        target = self.target / "web/sites/default/files"
        self.assertEqual((target / "image.txt").read_text(), "source-v1")
        self.assertTrue((target / ".gitignore").is_file())
        (target / "image.txt").write_text("target-local")
        (target / "extra.txt").write_text("keep")
        (source / "image.txt").write_text("source-v2")
        self.cli("init")
        self.assertEqual((target / "image.txt").read_text(), "target-local")
        preview = self.cli("files", "sync")
        self.assertEqual(preview[0]["files_to_copy"], 1)
        self.assertFalse(preview[0]["delete"])
        self.assertEqual((target / "image.txt").read_text(), "target-local")
        self.cli("files", "sync", "--apply")
        self.assertEqual((target / "image.txt").read_text(), "source-v2")
        self.assertEqual((target / "extra.txt").read_text(), "keep")
        self.assertEqual((source / "image.txt").read_text(), "source-v2")

    def test_files_path_escape_and_overlaps_are_rejected(self):
        for mappings in (
            [{"path": "../outside", "strategy": "copy"}],
            [{"path": "uploads"}, {"path": "uploads/child"}],
            [{"path": ".git/objects", "strategy": "shared"}],
        ):
            self.configure({"files": {"mappings": mappings}})
            self.cli("init", ok=False)
        self.assertFalse(self.calls("start"))

    def test_copy_symlink_is_rejected_without_writing_target(self):
        source = self.upload_source()
        (source / "link").symlink_to(self.main / "composer.json")
        self.configure(
            {"files": {"mappings": [{"path": "web/sites/default/files", "strategy": "copy"}]}}
        )
        self.assertIn("symlink", self.cli("init", ok=False))
        self.assertFalse((self.target / "web/sites/default/files/image.txt").exists())
        self.assertFalse(self.calls("start"))

    def test_files_sync_main_is_protected(self):
        self.assertIn(
            "main is protected", self.cli("files", "sync", "--apply", cwd=self.main, ok=False)
        )

    def test_files_sync_rejects_nested_source_without_overwriting_source(self):
        root = self.base / "overlap"
        source_root = root / "uploads/source"
        source = source_root / "uploads"
        source.mkdir(parents=True)
        (source / "a.txt").write_text("SOURCE ORIGINAL")
        nested = source / "source/uploads"
        nested.mkdir(parents=True)
        (nested / "a.txt").write_text("REPLACEMENT")
        config = {"mappings": [{"path": "uploads", "strategy": "copy"}]}
        with self.assertRaisesRegex(ValueError, "overlap"):
            manager.file_assets.sync(root, source_root, config, apply=True)
        with self.assertRaisesRegex(ValueError, "overlap"):
            manager.file_assets.prepare(root, source_root, config, [])
        self.assertEqual((source / "a.txt").read_text(), "SOURCE ORIGINAL")

    def test_prepare_only_does_not_claim_old_running_state_ready(self):
        self.cli("init")
        self.configure({"worktree": {"auto_start": False}})
        result = self.cli("init")
        self.assertEqual(result["phase"], "prepared")
        self.assertTrue(result["pending_start"])
        self.assertEqual(len(self.calls("start")), 1)
        self.assertEqual(self.cli("init", "--start")["phase"], "ready")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wtk tests ")
        self.base = Path(self.tmp.name).resolve()
        self.main = self.base / "main site"
        self.target = self.base / "detached worktree"
        self.main.mkdir()
        self.git(self.main, "init", "-b", "main")
        (self.main / ".ddev").mkdir()
        self.base_config = {
            "name": "source",
            "type": "php",
            "docroot": "web",
            "database": {"type": "mariadb", "version": "11.8"},
        }
        (self.main / ".ddev/config.yaml").write_text(json.dumps(self.base_config))
        (self.main / ".gitignore").write_text("vendor/\n.ddev/*.local.yaml\n")
        (self.main / "composer.json").write_text('{"require":{}}')
        self.git(self.main, "add", ".")
        self.git(
            self.main,
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "fixture",
        )
        self.git(self.main, "worktree", "add", "--detach", str(self.target))
        self.home = self.base / "runtime"
        self.home.mkdir()
        self.state = self.home / "runtime.json"
        self.state.write_text(
            json.dumps(
                {
                    "projects": {
                        "source": {"name": "source", "approot": str(self.main), "status": "running"}
                    },
                    "volumes": ["source-mariadb"],
                }
            )
        )
        bin_dir = self.home / "bin"
        bin_dir.mkdir()
        for name in ("ddev", "docker"):
            shutil.copyfile(PACKAGE / "tests/fake_runtime.py", bin_dir / name)
            (bin_dir / name).chmod(0o755)
        self.env = {
            **os.environ,
            "WT_TEST_RUNTIME": str(self.home),
            "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"],
            "PYTHONPATH": str(MANAGER.parent),
        }

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, root, *args):
        return subprocess.check_output(
            ["git", "-C", str(root), *args], stderr=subprocess.PIPE, text=True
        ).strip()

    def cli(self, *args, cwd=None, ok=True, input=None):
        result = subprocess.run(
            [sys.executable, str(MANAGER), *args],
            cwd=cwd or self.target,
            env=self.env,
            input=input,
            text=True,
            capture_output=True,
        )
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        return result.stderr

    def change_state(self, **values):
        state = json.loads(self.state.read_text())
        state.update(values)
        self.state.write_text(json.dumps(state))

    def calls(self, command):
        file = self.home / "calls.jsonl"
        rows = [json.loads(row) for row in file.read_text().splitlines()] if file.exists() else []
        return [row for row in rows if command in row[2]]

    def configure(self, value):
        (self.target / manager.CONFIG).write_text(manager.dump_yaml(value))

    def remove_checkout(self):
        self.git(self.main, "worktree", "remove", "--force", str(self.target))

    def test_detached_spaces_and_idempotent_seed_bootstrap(self):
        self.configure({"bootstrap": [["php", "-v"]]})
        before = (self.main / ".ddev/config.yaml").read_bytes()
        first = self.cli("init")
        second = self.cli("init")
        self.assertEqual(first["name"], second["name"])
        self.assertEqual(second["phase"], "ready")
        self.assertEqual(len(self.calls("snapshot")), 1)
        self.assertEqual(len(self.calls("composer")), 1)
        self.assertEqual(len(self.calls("php")), 1)
        self.assertFalse(list((self.main / ".ddev/db_snapshots").iterdir()))
        self.assertEqual(before, (self.main / ".ddev/config.yaml").read_bytes())
        self.assertNotIn("--reset-database", str(self.calls("start")))

    def test_main_refused_and_setup_noop(self):
        self.assertIn("main checkout", self.cli("init", cwd=self.main, ok=False))
        self.assertEqual(self.cli("setup", cwd=self.main)["status"], "skipped")
        self.assertFalse((self.main / ".git/ddev-worktree-kit").exists())

    def test_wrong_source_refused(self):
        self.assertIn(
            "different registered", self.cli("init", "--source", str(self.base), ok=False)
        )

    def test_snapshot_failure_does_not_start_or_fallback(self):
        self.change_state(snapshot_failure=True)
        self.assertIn("snapshot failed", self.cli("init", ok=False))
        self.assertFalse(self.calls("start"))

    def test_docker_failure_never_means_empty(self):
        self.change_state(docker_failure=True)
        self.assertIn("Docker unavailable", self.cli("init", ok=False))
        self.assertFalse(self.calls("snapshot"))

    def test_old_ddev_refused(self):
        self.change_state(version="v1.25.3")
        self.assertIn("1.25.4", self.cli("init", ok=False))

    def test_db_mismatch_refused_before_snapshot(self):
        config = {**self.base_config, "database": {"type": "mysql", "version": "8.4"}}
        (self.target / ".ddev/config.yaml").write_text(json.dumps(config))
        self.assertIn("match exactly", self.cli("init", ok=False))
        self.assertFalse(self.calls("snapshot"))

    def test_bootstrap_failure_resumes_without_reseed(self):
        self.configure({"bootstrap": [["php", "task.php"]]})
        self.change_state(bootstrap_failure=True)
        self.assertIn("bootstrap failed", self.cli("init", ok=False))
        self.change_state(bootstrap_failure=False)
        self.assertEqual(self.cli("init")["phase"], "ready")
        self.assertEqual(len(self.calls("snapshot")), 1)
        self.assertEqual(len(self.calls("composer")), 1)

    def test_composer_failure_resumes(self):
        self.change_state(composer_failure=True)
        self.cli("init", ok=False)
        self.change_state(composer_failure=False)
        self.cli("init")
        self.assertEqual(len(self.calls("snapshot")), 1)
        self.assertEqual(len(self.calls("composer")), 2)

    def test_missing_vendor_reinstalls(self):
        self.cli("init")
        shutil.rmtree(self.target / "vendor")
        self.cli("init")
        self.assertEqual(len(self.calls("composer")), 2)

    def test_composer_subdirectory_and_new_lock_stamp(self):
        app = self.target / "app"
        app.mkdir()
        (app / "composer.json").write_text('{"require":{}}')
        self.configure({"composer_root": "app"})
        self.cli("init")
        self.assertTrue((app / "vendor/autoload.php").is_file())
        self.assertTrue((app / "composer.lock").is_file())
        self.cli("init")
        self.assertEqual(len(self.calls("composer")), 1)

    def test_bootstrap_progress_does_not_replay_completed_commands(self):
        self.configure({"bootstrap": [["php", "first.php"], ["php", "second.php"]]})
        self.change_state(bootstrap_fail_command="second.php")
        self.cli("init", ok=False)
        self.change_state(bootstrap_fail_command="__none__")
        self.cli("init")
        self.assertEqual(len(self.calls("first.php")), 1)
        self.assertEqual(len(self.calls("second.php")), 2)

    def test_missing_seeded_volume_refused(self):
        self.cli("init")
        self.change_state(volumes=["source-mariadb"])
        self.assertIn("volume is missing", self.cli("init", ok=False))
        self.assertEqual(len(self.calls("snapshot")), 1)

    def test_incomplete_seed_never_becomes_ready(self):
        self.change_state(table_count="0")
        self.assertIn("no application tables", self.cli("init", ok=False))
        self.change_state(table_count="10")
        self.assertIn("completed seed receipt", self.cli("init", ok=False))
        self.assertFalse(self.calls("composer"))

    def test_unowned_override_refused(self):
        (self.target / ".ddev" / manager.OVERRIDE).write_text("name: somebody-else\n")
        self.assertIn("unowned file", self.cli("init", ok=False))
        self.assertFalse(self.calls("start"))

    def test_symlink_ddev_refused(self):
        shutil.rmtree(self.target / ".ddev")
        (self.target / ".ddev").symlink_to(self.main / ".ddev", target_is_directory=True)
        self.assertIn("escapes checkout", self.cli("init", ok=False))

    def test_later_override_refused(self):
        (self.target / ".ddev/config.zzzzz.yaml").write_text('{"name":"other"}')
        self.assertIn("loads after", self.cli("init", ok=False))

    def test_local_override_copied_without_source_hostname(self):
        (self.main / ".ddev/config.local.yaml").write_text(
            json.dumps(
                {
                    "name": "source-local",
                    "additional_fqdns": ["example.test"],
                    "host_db_port": "3308",
                }
            )
        )
        state = json.loads(self.state.read_text())
        state["projects"]["source-local"] = {
            "name": "source-local",
            "approot": str(self.main),
            "status": "running",
        }
        self.state.write_text(json.dumps(state))
        first = self.cli("init")
        generated = (self.target / ".ddev" / manager.OVERRIDE).read_text()
        self.assertIn(first["name"], generated)
        self.assertEqual(manager.load_yaml(generated)["additional_fqdns"], [])
        self.assertEqual(manager.load_yaml(generated)["host_db_port"], "")

    def test_no_files_copy(self):
        files = self.main / "web/sites/default/files"
        files.mkdir(parents=True)
        (files / "secret.txt").write_text("not shared")
        self.cli("init")
        self.assertFalse((self.target / "web/sites/default/files").exists())

    def test_multisite_mapping_and_settings(self):
        self.configure(
            {
                "sites": {
                    "en": {"directory": "english", "database": "db_en"},
                    "fr": {"directory": "french", "database": "db_fr"},
                }
            }
        )
        sites = self.target / "web/sites"
        sites.mkdir(parents=True)
        (sites / "sites.php").write_text("<?php // include sites.worktree-kit.php")
        for directory in ("english", "french"):
            (sites / directory).mkdir()
            (sites / directory / "settings.php").write_text(
                "<?php // include settings.worktree-kit.php"
            )
        result = self.cli("init")
        mapping = (sites / "sites.worktree-kit.php").read_text()
        self.assertIn("en." + result["name"], mapping)
        self.assertIn("'french'", mapping)
        settings = (sites / "settings.worktree-kit.php").read_text()
        self.assertIn("db_en", settings)
        self.assertIn("trusted_host_patterns", settings)

    def test_multisite_requires_explicit_include(self):
        self.configure({"sites": {"en": {"directory": "english"}}})
        self.assertIn("sites.php include", self.cli("init", ok=False))
        self.assertFalse(self.calls("snapshot"))

    def test_disabling_multisite_removes_only_our_generated_includes(self):
        self.configure({"sites": {"": {"directory": "default", "database": "db"}}})
        sites = self.target / "web/sites"
        (sites / "default").mkdir(parents=True)
        (sites / "sites.php").write_text("<?php // sites.worktree-kit.php")
        (sites / "default/settings.php").write_text("<?php // settings.worktree-kit.php")
        self.cli("init")
        self.assertTrue((sites / "sites.worktree-kit.php").exists())
        self.configure({"sites": {}})
        self.cli("init")
        self.assertFalse((sites / "sites.worktree-kit.php").exists())
        self.assertFalse((sites / "settings.worktree-kit.php").exists())
        self.assertTrue((sites / "sites.php").exists())

    def test_path_traversal_and_unknown_keys_refused(self):
        for config in ({"local_files": ["../outside"]}, {"bootstrap": "rm -rf"}, {"unknown": True}):
            with self.subTest(config=config):
                self.configure(config)
                self.cli("init", ok=False)
        self.assertFalse(self.calls("start"))

    def test_hook_payload_uses_cwd_and_valid_json(self):
        result = self.cli(
            "hook",
            "--provider",
            "claude",
            cwd=self.main,
            input=json.dumps({"hook_event_name": "SessionStart", "cwd": str(self.target)}),
        )
        self.assertEqual(result["hookSpecificOutput"]["hookEventName"], "SessionStart")
        self.assertEqual(len(self.calls("snapshot")), 1)

    def test_hook_refuses_other_events(self):
        self.assertIn(
            "SessionStart",
            self.cli(
                "hook",
                "--provider",
                "claude",
                ok=False,
                input=json.dumps({"hook_event_name": "WorktreeCreate", "cwd": str(self.target)}),
            ),
        )

    def test_gc_preview_and_confirmed_orphan_only(self):
        result = self.cli("init")
        self.assertFalse(self.cli("gc")[0]["gc_candidate"])
        self.remove_checkout()
        preview = self.cli("gc", cwd=self.main)
        self.assertTrue(preview[0]["gc_candidate"])
        self.assertFalse(self.calls("delete"))
        self.cli("gc", "--apply", cwd=self.main, ok=False)
        applied = self.cli("gc", "--apply", "--yes", cwd=self.main)
        self.assertTrue(applied[0]["deleted"])
        self.assertIn(result["name"], str(self.calls("delete")))
        self.assertEqual(self.cli("status", cwd=self.main), [])

    def test_gc_keeps_missing_but_git_registered(self):
        self.cli("init")
        shutil.rmtree(self.target)
        self.assertFalse(self.cli("gc", cwd=self.main)[0]["gc_candidate"])

    def test_gc_keeps_moved_worktree(self):
        self.cli("init")
        moved = self.base / "moved"
        self.git(self.main, "worktree", "move", str(self.target), str(moved))
        self.assertFalse(self.cli("gc", cwd=self.main)[0]["gc_candidate"])
        self.assertIn("moved", self.cli("init", cwd=moved, ok=False))

    def test_codex_setup_reuses_git_directory_with_a_separate_environment(self):
        self.install_callbacks()
        (self.main / manager.CONFIG).write_text(
            manager.dump_yaml({"cleanup": {"auto_delete": True}})
        )
        old = self.cli("init")
        self.remove_checkout()  # Simulate removal without a successful cleanup callback.
        replacement = self.base / "f7ef" / self.target.name
        replacement.parent.mkdir()
        self.git(self.main, "worktree", "add", "--detach", str(replacement))
        self.assertEqual(self.git(replacement, "rev-parse", "--absolute-git-dir"), old["git_dir"])
        env = {**self.env, "CODEX_WORKTREE_PATH": str(replacement)}

        def callback(event):
            result = subprocess.run(
                ["bash", str(self.main / f".ddev/worktree-kit/codex-{event}.sh")],
                cwd=self.main,
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)

        new = callback("setup")
        self.assertNotEqual(old["name"], new["name"])
        self.assertNotEqual(old["token"], new["token"])
        self.assertEqual(callback("setup")["token"], new["token"])
        self.assertEqual(len(self.calls("snapshot")), 2)
        registry = manager.load_registry(self.main / ".git")
        self.assertIn(old, registry["environments"].values())
        self.assertEqual(len(registry["environments"]), 2)
        rows = {row["name"]: row for row in self.cli("gc", cwd=self.main)}
        self.assertTrue(rows[old["name"]]["gc_candidate"])
        self.assertFalse(rows[new["name"]]["gc_candidate"])
        self.cli("files", "sync", cwd=replacement)
        self.assertEqual(callback("cleanup")["name"], new["name"])
        self.assertEqual(callback("cleanup")["status"], "skipped")
        self.assertTrue(replacement.exists())
        state = json.loads(self.state.read_text())
        self.assertIn(old["name"] + "-mariadb", state["volumes"])
        self.assertNotIn(new["name"] + "-mariadb", state["volumes"])
        self.assertEqual(len(self.calls("delete")), 1)
        self.assertNotIn(old["name"], str(self.calls("delete")))
        self.assertEqual(callback("setup")["phase"], "ready")

    def test_recreated_checkout_at_same_path_does_not_inherit_old_database(self):
        old = self.cli("init")
        self.remove_checkout()
        self.git(self.main, "worktree", "add", "--detach", str(self.target))
        self.assertIn("identity", self.cli("init", ok=False))
        self.assertIn("identity", self.cli("teardown", "--apply", "--yes", ok=False))
        self.assertIn("identity", self.cli("files", "sync", "--apply", ok=False))
        self.assertIn(old["name"] + "-mariadb", json.loads(self.state.read_text())["volumes"])
        self.assertEqual(len(self.calls("start")), 1)
        self.assertFalse(self.calls("delete"))

    def test_legacy_receipt_upgrades_identity_without_reseeding(self):
        old = self.cli("init")
        common = self.main / ".git"
        registry = manager.load_registry(common)
        for row in registry["environments"].values():
            row.pop("git_identity")
        manager.save_registry(common, registry)
        (Path(old["git_dir"]) / manager.IDENTITY).unlink()
        upgraded = self.cli("init")
        self.assertEqual(upgraded["token"], old["token"])
        self.assertEqual(upgraded["name"], old["name"])
        self.assertTrue(upgraded["git_identity"])
        self.assertEqual(len(self.calls("snapshot")), 1)

    def test_legacy_moved_checkout_remains_protected_without_identity_marker(self):
        old = self.cli("init")
        common = self.main / ".git"
        registry = manager.load_registry(common)
        for row in registry["environments"].values():
            row.pop("git_identity")
        manager.save_registry(common, registry)
        (Path(old["git_dir"]) / manager.IDENTITY).unlink()
        moved = self.base / "moved legacy"
        self.git(self.main, "worktree", "move", str(self.target), str(moved))
        self.assertIn("moved", self.cli("init", cwd=moved, ok=False))
        self.assertFalse(self.cli("gc", cwd=self.main)[0]["gc_candidate"])
        self.assertFalse(self.calls("delete"))

    def test_gc_keeps_moved_checkout_with_an_unknown_identity_token(self):
        old = self.cli("init")
        moved = self.base / "moved unknown identity"
        self.git(self.main, "worktree", "move", str(self.target), str(moved))
        (Path(old["git_dir"]) / manager.IDENTITY).write_text("0" * 32 + "\n")
        self.assertIn("moved", self.cli("init", cwd=moved, ok=False))
        self.assertFalse(self.cli("gc", cwd=self.main)[0]["gc_candidate"])
        self.assertFalse(self.cli("gc", "--apply", "--yes", cwd=self.main)[0]["gc_candidate"])
        self.assertFalse(self.calls("delete"))

    def test_gc_refuses_ddev_registry_reassignment(self):
        result = self.cli("init")
        self.remove_checkout()
        state = json.loads(self.state.read_text())
        state["projects"][result["name"]]["approot"] = str(self.main)
        self.state.write_text(json.dumps(state))
        self.assertIn("ownership", self.cli("gc", "--apply", "--yes", cwd=self.main, ok=False))
        self.assertFalse(self.calls("delete"))

    def test_gc_refuses_wrong_container_owner(self):
        self.cli("init")
        self.remove_checkout()
        self.change_state(
            containers={
                "container1": {"com.docker.compose.service": "web", manager.LABEL: "somebody-else"}
            }
        )
        self.assertIn("ownership", self.cli("gc", "--apply", "--yes", cwd=self.main, ok=False))
        self.assertFalse(self.calls("delete"))

    def test_gc_accepts_matching_container_owner(self):
        result = self.cli("init")
        self.remove_checkout()
        self.change_state(
            containers={
                "container1": {"com.docker.compose.service": "db", manager.LABEL: result["token"]}
            }
        )
        self.assertTrue(self.cli("gc", "--apply", "--yes", cwd=self.main)[0]["deleted"])

    def test_agent_adapters_find_main_copy_on_older_branch(self):
        self.install_callbacks()
        inside = self.target / "subdirectory"
        inside.mkdir()
        codex = subprocess.run(
            ["bash", str(PACKAGE / "examples/codex-setup.sh")],
            cwd=inside,
            env={**self.env, "CODEX_WORKTREE_PATH": str(self.target)},
            text=True,
            capture_output=True,
        )
        self.assertEqual(codex.returncode, 0, codex.stderr)
        self.assertEqual(json.loads(codex.stdout)["phase"], "ready")
        configuration = json.loads((PACKAGE / "examples/claude.settings.json").read_text())
        command = configuration["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        claude = subprocess.run(
            ["bash", "-c", command],
            cwd=inside,
            env=self.env,
            input=json.dumps({"hook_event_name": "SessionStart", "cwd": str(self.target)}),
            text=True,
            capture_output=True,
        )
        self.assertEqual(claude.returncode, 0, claude.stderr)
        self.assertEqual(
            json.loads(claude.stdout)["hookSpecificOutput"]["hookEventName"], "SessionStart"
        )
        self.assertEqual(len(self.calls("snapshot")), 1)

    def test_two_same_basename_worktrees_get_different_names(self):
        other = self.base / "other" / self.target.name
        other.parent.mkdir()
        self.git(self.main, "worktree", "add", "--detach", str(other))
        first = self.cli("init")
        second = self.cli("init", cwd=other)
        self.assertNotEqual(first["name"], second["name"])
        self.assertNotEqual(first["url"], second["url"])

    def test_concurrent_init_one_seed(self):
        args = [sys.executable, str(MANAGER), "init"]
        processes = [
            subprocess.Popen(
                args,
                cwd=self.target,
                env=self.env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for _ in range(2)
        ]
        for process in processes:
            stdout, stderr = process.communicate(timeout=30)
            self.assertEqual(process.returncode, 0, stderr)
            self.assertEqual(json.loads(stdout)["phase"], "ready")
        self.assertEqual(len(self.calls("snapshot")), 1)


if __name__ == "__main__":
    unittest.main()
